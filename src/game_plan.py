"""Coach-facing Game Plan workbook: only the alerts that held up, plain-English columns, short key.

The full-detail workbook (every table, every column) is still built in app.py for analysts.
"""
from __future__ import annotations

import pandas as pd

GUIDE_URL = "https://github.com/willwithers-stack/Lancer-Bot/blob/main/docs/QUICK_START.md"
KEEP_CHECKS = ("✓ Verified", "Developing")
LABELS = {"Formation_Family": "Formation", "Down_Distance": "D&D", "Near_Far": "Near/Far", "Motion_Flag": "Motion",
          "Formation_Standard": "Formation Tag", "Pass_Family": "Pass Type"}
PT_SHARE = ["Quick %", "Dropback %", "Play Action / Movement %", "Screen %", "Trick Play %"]

KEY = [
    ["Look", "The pre-snap picture: formation, down & distance, or both."],
    ["Plays / Games", "How many snaps and how many different games the look showed up in."],
    ["Lean", "What they did from it, e.g. 93% pass (28 of 30). Counted straight from the Hudl tags."],
    ["Lift", "Points above the team's own average for that side. +37 = 37 points more pass-heavy than usual. "
             "Alerts need +10 or more."],
    ["Check", "✓ Verified = the lean held up on games it was not built from. Developing = passed one test. "
              "Only these two appear on Game Plan."],
    ["Held Up", "Games where the lean was true out of games with the look, e.g. 4 of 5 games."],
    ["Confidence", "High (15+ plays, 70%+), Usable (10+, 65%+), Low Volume (6+, confirm on film), "
                   "No Clear Lean (under the watch rate)."],
    ["Explosive", "Gain of 21+ yards."],
    ["Pass type", "Quick / Dropback / Play Action-Movement / Screen, among passes only. Pass-type alerts top out at Developing."],
]


def _pct(x) -> str:
    return "" if pd.isna(x) else f"{x:.0%}"


def _lift(x) -> str:
    return "" if pd.isna(x) else f"{round(x * 100):+d}"


def _look(df: pd.DataFrame, cols: list[str]) -> pd.Series:
    parts = df[cols].copy()
    if "Motion_Flag" in parts:
        parts["Motion_Flag"] = parts["Motion_Flag"].map(
            lambda v: "Motion" if v in (True, "True", "Motion") else "No Motion" if v in (False, "False", "No Motion") else v)
    return parts.astype("string").fillna("—").agg(" + ".join, axis=1)


def _rp_lean(df: pd.DataFrame) -> pd.Series:
    side = df["Tendency"].str.lower()
    k = df["Pass"].where(side == "pass", df["Run"])
    return [f"{_pct(r)} {s} ({int(n)} of {int(p)})" for r, s, n, p in zip(df["Rate"], side, k, df["Plays"])]


def _rp_rows(alerts: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    if alerts is None or alerts.empty:
        return pd.DataFrame()
    a = alerts[alerts["Accuracy_Check"].isin(KEEP_CHECKS)]
    if a.empty:
        return pd.DataFrame()
    return pd.DataFrame({
        "Category": "Run/Pass by " + " + ".join(LABELS.get(c, c.replace("_", " ")) for c in cols),
        "Look": _look(a, cols), "Plays": a["Plays"], "Games": a["Games"], "Lean": _rp_lean(a),
        "Lift": a["Lift"].map(_lift), "Check": a["Accuracy_Check"], "Held Up": a["Held_Up"],
        "_lift": a["Lift"],
    })


def _pt_rows(alerts: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    if alerts is None or alerts.empty:
        return pd.DataFrame()
    a = alerts[alerts["Accuracy_Check"].isin(KEEP_CHECKS)]
    if a.empty:
        return pd.DataFrame()
    lean = [f"{_pct(r)} {t} ({round(r * n)} of {int(n)} passes)" for r, t, n in zip(a["Rate"], a["Top_Type"], a["Passes"])]
    return pd.DataFrame({
        "Category": "Pass Type by " + " + ".join(LABELS.get(c, c.replace("_", " ")) for c in cols),
        "Look": _look(a, cols), "Plays": a["Passes"], "Games": a["Games"], "Lean": lean,
        "Lift": a["Lift"].map(_lift), "Check": a["Accuracy_Check"], "Held Up": a["Held_Up"],
        "_lift": a["Lift"],
    })


def game_plan_table(rp_alerts: list[tuple[pd.DataFrame, list[str]]],
                    pt_alerts: list[tuple[pd.DataFrame, list[str]]]) -> pd.DataFrame:
    """One list of every Verified/Developing alert. Verified first, then biggest Lift, then most plays."""
    parts = [_rp_rows(a, c) for a, c in rp_alerts] + [_pt_rows(a, c) for a, c in pt_alerts]
    parts = [p for p in parts if not p.empty]
    if not parts:
        return pd.DataFrame()
    out = pd.concat(parts, ignore_index=True)
    out["_v"] = (out["Check"] != "✓ Verified").astype(int)
    out = out.sort_values(["_v", "_lift", "Plays"], ascending=[True, False, False])
    return out.drop(columns=["_v", "_lift"]).reset_index(drop=True)


def plain_tendency(t: pd.DataFrame, col: str) -> pd.DataFrame:
    if t is None or t.empty:
        return pd.DataFrame()
    return pd.DataFrame({LABELS.get(col, col.replace("_", " ")): t[col], "Plays": t["Plays"], "Games": t["Games"],
                         "Lean": _rp_lean(t), "Lift": t["Lift"].map(_lift), "Confidence": t["Confidence"]})


def plain_pass_type(t: pd.DataFrame, col: str) -> pd.DataFrame:
    if t is None or t.empty:
        return pd.DataFrame()
    out = pd.DataFrame({LABELS.get(col, col.replace("_", " ")): t[col], "Passes": t["Passes"], "Games": t["Games"]})
    for c in PT_SHARE:
        if c in t:
            out[c.replace(" %", "")] = t[c].map(_pct)
    out["Most Common"] = t["Top_Type"]
    return out


PBP = {"Game_ID": "Game", "Play_Number": "Play #", "Quarter": "Qtr", "Down": "Down", "Distance": "Dist",
       "Yard_Line": "Yard Line", "Hash": "Hash", "Formation_Raw": "Formation", "Motion": "Motion",
       "Run_Pass": "Run/Pass", "Pass_Family": "Pass Type", "Off_Play": "Play", "Play_Direction": "Direction",
       "Gain": "Gain", "Result": "Result"}


def plain_plays(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    cols = [c for c in PBP if c in df.columns]
    return df[cols].rename(columns=PBP)


def build_game_plan_sections(*, games: list, n_snaps: int, pass_rate: float, upload_note: str, alert_rule: str,
                             plan: pd.DataFrame, formation: pd.DataFrame, dd: pd.DataFrame,
                             pass_type: pd.DataFrame, explosives: pd.DataFrame, tricks: pd.DataFrame,
                             plays: pd.DataFrame) -> list[tuple[str, str, pd.DataFrame]]:
    n_ver = int((plan["Check"] == "✓ Verified").sum()) if len(plan) else 0
    n_dev = int((plan["Check"] == "Developing").sum()) if len(plan) else 0
    readme = pd.DataFrame(
        [["Games", ", ".join(map(str, games))],
         ["Sample", f"{n_snaps:,} run/pass snaps, {pass_rate:.0%} pass. Team tagged ODK = O."],
         ["Game Plan sheet", f"{n_ver} Verified and {n_dev} Developing alerts. Sorted Verified first, then biggest Lift."],
         ["Alert rule", alert_rule],
         ["Upload check", upload_note],
         ["", ""],
         ["COLUMN KEY", ""]] + KEY +
        [["", ""],
         ["Full guide", GUIDE_URL],
         ["Note", "Tendencies show what an offense has done, not a promise of what it will call. "
                  "Every number traces to a play on the Play by Play sheet."]],
        columns=["Item", "Detail"])
    if plan.empty:
        plan = pd.DataFrame({"Note": ["No alerts reached Verified or Developing. "
                                      "Alerts need 3+ games; see the Formations and Down & Distance sheets."]})
    sections = [
        ("Read Me", "FORMATIONIQ — GAME PLAN", readme),
        ("Game Plan", "GAME PLAN — ALERTS THAT HELD UP", plan),
        ("Formations", "RUN / PASS BY FORMATION", formation),
        ("Down & Distance", "RUN / PASS BY DOWN & DISTANCE", dd),
        ("Pass Type", "PASS TYPE BY FORMATION", pass_type),
        ("Explosive Plays", "EVERY GAIN OF 21+ YARDS", explosives),
    ]
    if tricks is not None and not tricks.empty:
        sections.append(("Trick Plays", "TRICK PLAYS", tricks))
    sections.append(("Play by Play", "EVERY OFFENSIVE SNAP", plays))
    return sections
