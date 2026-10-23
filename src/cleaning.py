"""Turn raw Hudl sheets into one clean row per offensive snap, plus a data-quality report.

Rows are flagged, not silently deleted. Only non-offensive rows (D/K) are removed,
and the count is reported.
"""
from __future__ import annotations

import re
import pandas as pd

from src.data_ingestion import normalize_columns, missing_required
from src.config import NON_SNAP_RESULTS
from src.scoring import add_score_state

NON_SNAP_PLAY_TYPES = {"PUNT", "FG", "FIELD GOAL", "PAT", "XP", "KO", "KICKOFF",
                       "KOR", "PUNT REC", "ONSIDE", "FG BLOCK", "PAT BLOCK"}
PASS_WORDS = r"\b(PASS|PA|PLAY ACTION|BOOT|SACK|SACKED|INT|INTERCEPTION|INTERCEPTED|COMPLETE|INCOMPLETE|INC|SCRAMBLE|SCREEN|RPO PASS)\b"
RUN_WORDS = r"\b(RUN|RUSH|SWEEP|JET|POWER|COUNTER|DRAW|DIVE|ISO|TRAP|QB KEEP|KEEP|OPTION|INSIDE ZONE|OUTSIDE ZONE|IZ|OZ|SNEAK|WEDGE|BUCK|BELLY)\b"
PENALTY_WORDS = r"\b(?:PENALTY|PEN|FALSE START|OFFSIDE|DELAY OF GAME|ENCROACHMENT)\b"


def _text(v) -> str:
    return "" if pd.isna(v) else str(v).upper().strip()


def derive_run_pass(play_type, off_play="", result="") -> str:
    """Label the TARGET. Uses post-snap text (result) only to label what happened —
    never as a predictor. Play_Type wins when it is an explicit Run/Pass tag."""
    pt = _text(play_type)
    if pt in {"RUN", "RUSH"}:
        return "Run"
    if pt in {"PASS"}:
        return "Pass"
    combined = f"{pt} {_text(off_play)} {_text(result)}"
    is_pass = re.search(PASS_WORDS, combined) is not None
    is_run = re.search(RUN_WORDS, combined) is not None
    if is_pass and not is_run:
        return "Pass"
    if is_run and not is_pass:
        return "Run"
    if is_pass and is_run:
        # e.g. "Jet Sweep" result "Sack" -> the snap was a pass. "Draw" with "Complete" is odd.
        return "Pass" if re.search(r"\b(SACK|SACKED|COMPLETE|INCOMPLETE|INC|INT|INTERCEPTION)\b", combined) else "Unknown"
    return "Unknown"


def _assign_game_ids(sheet: pd.DataFrame, sheet_name: str, multi_sheet: bool) -> pd.Series:
    if "Game_ID" in sheet.columns and sheet["Game_ID"].notna().any():
        return sheet["Game_ID"].ffill().astype(str)
    if multi_sheet:
        return pd.Series(str(sheet_name), index=sheet.index)
    # Single sheet, no game column: a drop in Play_Number signals a new game.
    if "Play_Number" in sheet.columns:
        pn = pd.to_numeric(sheet["Play_Number"], errors="coerce").ffill()
        new_game = pn.diff().fillna(0) < 0
        return ("G" + (new_game.cumsum() + 1).astype(str))
    return pd.Series("G1", index=sheet.index)


def _assign_drives(full: pd.DataFrame) -> pd.Series:
    """Drive = consecutive block of O rows within a game. Uses Hudl SERIES if tagged."""
    if "Series" in full.columns and full["Series"].notna().any():
        return full["Game_ID"] + "-D" + full["Series"].ffill().astype(str)
    is_o = full["_drive_o"]
    starts = is_o & ~is_o.groupby(full["Game_ID"]).shift(1, fill_value=False).astype(bool)
    drive_num = starts.groupby(full["Game_ID"]).cumsum()
    return full["Game_ID"] + "-D" + drive_num.astype(str)


def clean_hudl_export(sheets: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Returns (clean_offense_df, quality_report_df, meta)."""
    frames, unmapped_cols = [], set()
    multi = len(sheets) > 1
    for name, raw in sheets.items():
        sheet, unmapped = normalize_columns(raw.dropna(how="all"))
        unmapped_cols.update(unmapped)
        sheet = sheet.copy()
        sheet["Game_ID"] = _assign_game_ids(sheet, name, multi)
        sheet["_source_sheet"] = name
        frames.append(sheet)
    full = pd.concat(frames, ignore_index=True)
    full["_row_order"] = range(len(full))

    missing = missing_required(full)
    if missing:
        raise ValueError(
            "Upload is missing required columns: " + ", ".join(missing)
            + ". Check the Hudl export includes DN, DIST, YARD LN, and OFF FORM."
        )

    # Offensive snap filter: ODK == O when present, else drop explicit special-teams play types.
    pt = full.get("Play_Type", pd.Series("", index=full.index)).map(_text)
    if "ODK" in full.columns:
        full["_is_offense"] = full["ODK"].map(_text).eq("O")
    else:
        full["_is_offense"] = True
    full["_is_offense"] &= ~pt.isin(NON_SNAP_PLAY_TYPES)
    full["_drive_o"] = full["_is_offense"].copy()   # timeouts inside a drive must not split it
    res = full.get("Result", pd.Series("", index=full.index)).map(_text)
    no_play = pt.eq("") & full["Formation_Raw"].isna()
    full["_non_snap"] = full["_is_offense"] & (res.isin(NON_SNAP_RESULTS) | (no_play & res.str.contains("PENALTY")))
    non_snap_count = int(full["_non_snap"].sum())
    full["_is_offense"] &= ~full["_non_snap"]

    full["Drive_ID"] = _assign_drives(full)
    # Rebuild pre-snap score from TDs / FGs / PATs unless the export already has it.
    score_rebuilt = "Score_Differential" not in full.columns and "Result" in full.columns
    if score_rebuilt:
        full = add_score_state(full)
    full["Quarter"] = pd.to_numeric(full.get("Quarter"), errors="coerce") if "Quarter" in full else pd.NA

    data = full[full["_is_offense"]].copy()
    removed_non_offense = len(full) - len(data)

    # First drive = drive containing the first O row of each game.
    first_drive = data.sort_values("_row_order").groupby("Game_ID")["Drive_ID"].first()
    data["First_Drive_Flag"] = data["Drive_ID"].isin(first_drive.values)
    data["Play_In_Drive"] = data.groupby("Drive_ID").cumcount() + 1

    for col in ["Down", "Distance", "Yard_Line", "Gain"]:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce")

    data["Run_Pass"] = [
        derive_run_pass(a, b, c) for a, b, c in zip(
            data.get("Play_Type", pd.Series("", index=data.index)),
            data.get("Off_Play", pd.Series("", index=data.index)),
            data.get("Result", pd.Series("", index=data.index)),
        )
    ]
    # A hand-tagged PASS TYPE means the snap was a pass, even if PLAY TYPE was left blank.
    if "Pass_Type_Raw" in data.columns:
        has_pt = data["Pass_Type_Raw"].map(_text).ne("")
        data.loc[has_pt & data["Run_Pass"].eq("Unknown"), "Run_Pass"] = "Pass"
    result_text = data.get("Result", pd.Series("", index=data.index)).map(_text)
    data["Penalty_Flag"] = result_text.str.contains(PENALTY_WORDS, regex=True)

    # Score differential must be the score BEFORE the snap (rebuilt above when possible).
    if "Score_Differential" not in data.columns and {"Team_Score", "Opp_Score"} <= set(data.columns):
        data["Score_Differential"] = (pd.to_numeric(data["Team_Score"], errors="coerce")
                                      - pd.to_numeric(data["Opp_Score"], errors="coerce"))

    data = data.sort_values("_row_order").reset_index(drop=True)

    checks = [
        ("Rows uploaded", len(full), "All sheets combined"),
        ("Non-offensive rows removed", removed_non_offense, "ODK not O, or kick/punt play type"),
        ("Timeouts / dead-ball penalties removed", non_snap_count, "Tagged O but no snap (no formation or play type)"),
        ("Offensive snaps kept", len(data), ""),
        ("Games identified", data["Game_ID"].nunique(), "From Game column, sheet names, or Play # resets"),
        ("Drives identified", data["Drive_ID"].nunique(), ""),
        ("Run/Pass = Unknown", int((data["Run_Pass"] == "Unknown").sum()), "Excluded from run/pass math; tag PLAY TYPE to fix"),
        ("Penalty snaps (flagged, kept)", int(data["Penalty_Flag"].sum()), "Review on film"),
        ("Missing Down", int(data["Down"].isna().sum()), ""),
        ("Missing Distance", int(data["Distance"].isna().sum()), ""),
        ("Missing Yard Line", int(data["Yard_Line"].isna().sum()), ""),
        ("Missing Formation", int(data["Formation_Raw"].isna().sum()), ""),
        ("Missing Score Differential", int(data["Score_Differential"].isna().sum()) if "Score_Differential" in data else len(data), "Score State will be Unknown"),
    ]
    report = pd.DataFrame(checks, columns=["Check", "Count", "Note"])
    # Rows kept for the trick-play inventory: scouted offense + kicking rows (fake punts/FGs).
    odk = full["ODK"].map(_text) if "ODK" in full.columns else pd.Series("O", index=full.index)
    trick_source = full[odk.isin(["O", "K", ""])].drop(columns=["_is_offense", "_non_snap", "_drive_o"], errors="ignore")
    meta = {"unmapped_columns": sorted(unmapped_cols), "games": data["Game_ID"].nunique(),
            "trick_source": trick_source.reset_index(drop=True),
            "score_rows": full.drop(columns=["_is_offense", "_non_snap", "_drive_o"], errors="ignore") if score_rebuilt else None}
    return data.drop(columns=["_is_offense", "_non_snap", "_drive_o"]), report, meta
