"""Pass Type IQ: Quick vs Dropback vs Play Action / Movement vs Screen.

Two levels:
  Pass_Family -> Quick | Dropback | Play Action / Movement | Screen  (what coaches see)
  Pass_Type   -> Quick, RPO, Dropback, PA Pocket, Boot, Naked, Sprint / Rollout, Screen

Pass type is what HAPPENED after the snap, so it is a target (like Run/Pass), never a
predictor. Group by pre-snap columns only (formation, down & distance, hash, score...).

Source of every label is kept in Pass_Type_Source:
  "Tagged"                  - from the PASS TYPE column (most reliable)
  "Inferred from play name" - matched in OFF PLAY (staff terms / protection series)
  "Not Tagged"              - a pass we couldn't classify; excluded from pass-type math
"""
from __future__ import annotations

import re

import pandas as pd

from src.alert_engine import confidence_label, _filters_text
from src.config import (PASS_TYPE_RULES, PASS_PROTECTION_SERIES, PASS_FAMILIES, POST_SNAP_COLUMNS,
                        PASS_TYPE_IMPLICATIONS, ALERT_THRESHOLD_HIGH, ALERT_THRESHOLD_WATCH,
                        MIN_ALERT_PLAYS, MIN_LIFT_OVER_BASELINE, MIN_REGRESSION_GAMES)

TAGGED, INFERRED, NOT_TAGGED = "Tagged", "Inferred from play name", "Not Tagged"
TYPE_TO_FAMILY = {t: f for t, f, _ in PASS_TYPE_RULES}
FAMILY_NAMES = {f.upper(): f for f in PASS_FAMILIES} | {"PA": "Play Action / Movement",
                                                         "MOVEMENT": "Play Action / Movement",
                                                         "PLAY ACTION": "Play Action / Movement"}


def _tok(v) -> str:
    if v is None or (not isinstance(v, str) and pd.isna(v)):
        return ""
    return " " + re.sub(r"[^A-Z0-9]+", " ", str(v).upper()).strip() + " "


def classify_pass_type(text, series=None, rules=PASS_TYPE_RULES) -> str | None:
    """Return a Pass_Type for a piece of text, or None."""
    t = _tok(text)
    if not t.strip():
        return None
    series = PASS_PROTECTION_SERIES if series is None else series
    for code, ptype in series.items():
        if f" {_tok(code).strip()} " in t:
            return ptype
    for ptype, _family, pats in rules:
        if any(f" {p} " in t for p in pats):
            return ptype
    return None


def _from_tag(raw) -> str | None:
    """A hand tag can be the family name itself ("Quick", "Dropback", "PA") or a detail."""
    t = _tok(raw).strip()
    if not t:
        return None
    if t in {f.upper() for f in PASS_FAMILIES}:
        fam = FAMILY_NAMES[t]
        return {"Play Action / Movement": "PA Pocket"}.get(fam, fam)
    return classify_pass_type(raw)


def add_pass_types(df: pd.DataFrame) -> pd.DataFrame:
    """Adds Pass_Type, Pass_Family, Pass_Type_Source. Non-pass snaps get blank labels."""
    data = df.copy()
    is_pass = data["Run_Pass"].eq("Pass") if "Run_Pass" in data else pd.Series(False, index=data.index)
    raw = data["Pass_Type_Raw"] if "Pass_Type_Raw" in data else pd.Series(pd.NA, index=data.index)
    call = data["Off_Play"] if "Off_Play" in data else pd.Series(pd.NA, index=data.index)

    types, sources = [], []
    for p, r, c in zip(is_pass, raw, call):
        if not p:
            types.append(pd.NA)
            sources.append(pd.NA)
            continue
        tagged = _from_tag(r)
        if tagged:
            types.append(tagged); sources.append(TAGGED); continue
        inferred = classify_pass_type(c)
        if inferred:
            types.append(inferred); sources.append(INFERRED); continue
        types.append(NOT_TAGGED); sources.append(NOT_TAGGED)
    data["Pass_Type"] = pd.array(types, dtype="string")
    data["Pass_Family"] = data["Pass_Type"].map(lambda t: TYPE_TO_FAMILY.get(t, NOT_TAGGED) if pd.notna(t) else pd.NA).astype("string")
    data["Pass_Type_Source"] = pd.array(sources, dtype="string")
    for col in ["Launch_Side", "Protection"]:
        if col in data:
            data[col] = data[col].astype("string").str.strip().str.upper().replace({"LEFT": "L", "RIGHT": "R", "MIDDLE": "M", "MID": "M"})
    return data


def _passes(df: pd.DataFrame) -> pd.DataFrame:
    if "Pass_Family" not in df:
        return df.iloc[0:0]
    return df[df["Run_Pass"].eq("Pass") & df["Pass_Family"].notna() & df["Pass_Family"].ne(NOT_TAGGED)].copy()


def pass_type_table(df: pd.DataFrame, group_columns: list[str], level: str = "Pass_Family") -> pd.DataFrame:
    """For each pre-snap group: count of each pass family, the leading one, its rate,
    and lift over the team's own mix. Only classified passes are counted."""
    bad = set(group_columns) & POST_SNAP_COLUMNS
    if bad:
        raise ValueError(f"Post-snap columns cannot define a pre-snap tendency: {bad}")
    src = _passes(df)
    if src.empty:
        return pd.DataFrame()
    for c in group_columns:
        src[c] = src[c].astype("string").fillna("Unknown")
    cats = [c for c in (PASS_FAMILIES if level == "Pass_Family" else
                        [t for t, _, _ in PASS_TYPE_RULES]) if c in set(src[level])]
    counts = pd.crosstab([src[c] for c in group_columns], src[level]).reindex(columns=cats, fill_value=0)
    out = counts.reset_index()
    out.columns.name = None
    games = src.groupby(group_columns)["Game_ID"].nunique().rename("Games").reset_index()
    out = out.merge(games, on=group_columns, how="left")
    out["Passes"] = out[cats].sum(axis=1)
    out["Top_Type"] = out[cats].idxmax(axis=1)
    out["Rate"] = out[cats].max(axis=1) / out["Passes"]
    base = src[level].value_counts(normalize=True)
    out["Team_Baseline"] = out["Top_Type"].map(base)
    out["Lift"] = out["Rate"] - out["Team_Baseline"]
    for c in cats:
        out[f"{c} %"] = out[c] / out["Passes"]
    out["Confidence"] = [confidence_label(p, r, gm) for p, r, gm in zip(out["Passes"], out["Rate"], out["Games"])]
    out["Filters"] = out.apply(lambda r: _filters_text(r, group_columns), axis=1)
    return out.sort_values("Passes", ascending=False).reset_index(drop=True)


def _consistency_check(row, src, group_columns, level, games_total):
    """No regression here (yet). Lean must hold in 2/3 of games where the look appeared
    with 2+ passes. Never stamps Verified; the best a pass-type tell earns is Developing."""
    mask = pd.Series(True, index=src.index)
    for c in group_columns:
        mask &= src[c].astype("string").fillna("Unknown").eq(str(row[c]))
    g = src[mask]
    per_game = [((s == row["Top_Type"]).mean(), len(s)) for _, s in g.groupby("Game_ID")[level]]
    eligible = [r for r, n in per_game if n >= 2]
    ok = sum(r > 0.5 for r in eligible)
    held = f"{ok} of {len(eligible)} game{'' if len(eligible) == 1 else 's'}" if eligible else "—"
    consistent = len(eligible) >= 2 and ok / len(eligible) >= 0.67
    if games_total < MIN_REGRESSION_GAMES:
        status = "Pending (needs 3+ games)" if consistent else "Film Only"
    else:
        status = "Developing" if consistent else "Film Only"
    return held, status


def build_pass_type_alerts(df: pd.DataFrame, group_columns: list[str], level: str = "Pass_Family",
                           high_threshold: float = ALERT_THRESHOLD_HIGH, watch_threshold: float = ALERT_THRESHOLD_WATCH,
                           min_plays: int = MIN_ALERT_PLAYS, min_lift: float = MIN_LIFT_OVER_BASELINE) -> pd.DataFrame:
    """Same rules as run/pass alerts: clear the threshold, have the plays, beat the team's own mix."""
    t = pass_type_table(df, group_columns, level)
    if t.empty:
        return t
    eligible = (t["Passes"] >= min_plays) & (t["Lift"] >= min_lift)
    t["Alert_Level"] = "No Alert"
    t.loc[eligible & (t["Rate"] >= watch_threshold), "Alert_Level"] = "Watch Alert"
    t.loc[eligible & (t["Rate"] >= high_threshold), "Alert_Level"] = "High Alert"
    cols = group_columns + ["Passes", "Games", "Top_Type", "Rate", "Team_Baseline", "Lift", "Confidence",
                            "Accuracy_Check", "Held_Up", "Alert_Level", "Coaching_Implication"]
    a = t[t["Alert_Level"] != "No Alert"].copy()
    if a.empty:
        return pd.DataFrame(columns=cols)
    src = _passes(df)
    games_total = src["Game_ID"].nunique()
    checks = [_consistency_check(r, src, group_columns, level, games_total) for _, r in a.iterrows()]
    a["Held_Up"] = [c[0] for c in checks]
    a["Accuracy_Check"] = [c[1] for c in checks]

    def _imp(r):
        fam = TYPE_TO_FAMILY.get(r["Top_Type"], r["Top_Type"])
        tag = " — confirm on film" if r["Confidence"].startswith("Low") else ""
        return (f"{r['Filters']}: {r['Rate']:.0%} {r['Top_Type']} ({r['Passes']} passes, {r['Games']} games). "
                f"{PASS_TYPE_IMPLICATIONS.get(fam, '')}{tag}.")
    a["Coaching_Implication"] = a.apply(_imp, axis=1)
    return a[cols].sort_values(["Alert_Level", "Rate", "Passes"], ascending=[True, False, False]).reset_index(drop=True)


def _result_flags(src: pd.DataFrame) -> pd.DataFrame:
    res = src["Result"].map(_tok) if "Result" in src else pd.Series("", index=src.index)
    src = src.copy()
    src["_sack"] = res.str.contains(r" SACK(?:ED)? ", regex=True)
    src["_int"] = res.str.contains(r" (?:INT|INTERCEPTION|INTERCEPTED|PICK) ", regex=True)
    src["_inc"] = res.str.contains(r" (?:INCOMPLETE|INC|INCOMP) ", regex=True)
    src["_comp"] = res.str.contains(r" (?:COMPLETE|COMP|COMPLETION|CATCH) ", regex=True) & ~src["_inc"]
    src["_att"] = ~src["_sack"] & (src["_comp"] | src["_inc"] | src["_int"])
    return src


def pass_type_results(df: pd.DataFrame, level: str = "Pass_Family") -> pd.DataFrame:
    """Descriptive results by pass type: what each type actually produces (post-snap, film review)."""
    src = _passes(df)
    if src.empty:
        return pd.DataFrame()
    src = _result_flags(src)
    g = src.groupby(level)
    out = pd.DataFrame({
        "Passes": g.size(),
        "Games": g["Game_ID"].nunique(),
        "Share": g.size() / len(src),
        "Comp_Pct": g.apply(lambda s: s["_comp"].sum() / s["_att"].sum() if s["_att"].sum() else float("nan")),
        "Avg_Gain": g["Gain"].mean() if "Gain" in src else float("nan"),
        "Success": g["Success_Flag"].mean() if "Success_Flag" in src else float("nan"),
        "Explosive": g["Explosive_Flag"].mean() if "Explosive_Flag" in src else float("nan"),
        "Sacks": g["_sack"].sum().astype(int),
        "INTs": g["_int"].sum().astype(int),
    }).reset_index()
    return out.sort_values("Passes", ascending=False).reset_index(drop=True)


def play_action_after_run(df: pd.DataFrame) -> pd.DataFrame:
    """Do they go to play action / movement after the run is working? Previous snap in the
    same drive, classified passes only. Context comes from the PRIOR play, so it's pre-snap."""
    if "Pass_Family" not in df:
        return pd.DataFrame()
    d = df.sort_values("_row_order") if "_row_order" in df else df
    d = d.copy()
    prev_rp = d.groupby("Drive_ID")["Run_Pass"].shift(1) if "Drive_ID" in d else d["Run_Pass"].shift(1)
    prev_ok = d.groupby("Drive_ID")["Success_Flag"].shift(1) if "Drive_ID" in d else d["Success_Flag"].shift(1)
    d["Previous_Snap"] = "First play of drive"
    d.loc[prev_rp.eq("Run") & prev_ok.eq(True), "Previous_Snap"] = "After successful run"
    d.loc[prev_rp.eq("Run") & prev_ok.eq(False), "Previous_Snap"] = "After unsuccessful run"
    d.loc[prev_rp.eq("Pass"), "Previous_Snap"] = "After pass"
    d.loc[prev_rp.eq("Run") & prev_ok.isna(), "Previous_Snap"] = "After run (no gain tagged)"
    src = _passes(d)
    if src.empty:
        return pd.DataFrame()
    g = src.groupby("Previous_Snap")
    out = pd.DataFrame({
        "Passes": g.size(),
        "Games": g["Game_ID"].nunique(),
        "PA_Movement_Pct": g["Pass_Family"].apply(lambda s: (s == "Play Action / Movement").mean()),
        "Quick_Pct": g["Pass_Family"].apply(lambda s: (s == "Quick").mean()),
        "Dropback_Pct": g["Pass_Family"].apply(lambda s: (s == "Dropback").mean()),
        "Screen_Pct": g["Pass_Family"].apply(lambda s: (s == "Screen").mean()),
    }).reset_index()
    order = ["After successful run", "After unsuccessful run", "After run (no gain tagged)", "After pass", "First play of drive"]
    return out.assign(_o=out["Previous_Snap"].map(order.index)).sort_values("_o").drop(columns="_o").reset_index(drop=True)


def launch_vs_strength(df: pd.DataFrame) -> pd.DataFrame:
    """Boot / naked / sprint: do they roll to or away from the declared strength? Needs LAUNCH tagged."""
    if "Launch_Side" not in df or "Strength" not in df:
        return pd.DataFrame()
    src = _passes(df)
    src = src[src["Pass_Type"].isin(["Boot", "Naked", "Sprint / Rollout"]) & src["Launch_Side"].isin(["L", "R"])]
    if src.empty:
        return pd.DataFrame()
    side = src["Strength"].astype("string").str[0]
    src["Launch_vs_Strength"] = "Strength not L/R"
    src.loc[side.isin(["L", "R"]) & side.eq(src["Launch_Side"]), "Launch_vs_Strength"] = "Toward strength"
    src.loc[side.isin(["L", "R"]) & side.ne(src["Launch_Side"]), "Launch_vs_Strength"] = "Away from strength"
    return (src.groupby(["Pass_Type", "Launch_vs_Strength"]).agg(Passes=("Game_ID", "size"), Games=("Game_ID", "nunique"))
            .reset_index().sort_values(["Pass_Type", "Passes"], ascending=[True, False]))


def pass_type_quality(df: pd.DataFrame) -> list[tuple[str, int, str]]:
    if "Pass_Type_Source" not in df:
        return []
    s = df["Pass_Type_Source"]
    return [
        ("Passes with pass type tagged", int(s.eq(TAGGED).sum()), "From the PASS TYPE column"),
        ("Passes with pass type inferred", int(s.eq(INFERRED).sum()), "Matched in the play name; add a PASS TYPE column to confirm"),
        ("Passes with no pass type", int(s.eq(NOT_TAGGED).sum()), "Left out of Pass Type IQ; tag PASS TYPE to fix"),
    ]
