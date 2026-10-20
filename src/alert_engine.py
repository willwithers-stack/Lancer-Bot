"""Descriptive tendencies and composite alerts. Raw counts first; labels second."""
from __future__ import annotations

import pandas as pd

from src.config import (ALERT_THRESHOLD_HIGH, ALERT_THRESHOLD_WATCH, MIN_ALERT_PLAYS,
                        CONFIDENCE_TIERS, MIN_LIFT_OVER_BASELINE, POST_SNAP_COLUMNS)


def confidence_label(plays: int, rate: float, games: int = 99) -> str:
    # Enough plays but no real lean: say so, instead of calling it "low volume".
    if plays >= CONFIDENCE_TIERS[-1][1] and rate < ALERT_THRESHOLD_WATCH:
        return "No Clear Lean"
    for label, min_plays, min_rate in CONFIDENCE_TIERS:
        if plays >= min_plays and rate >= min_rate:
            # A tendency seen in only one game is a game-plan wrinkle, not a tendency.
            if games < 2 and label != "Low Volume / Confirm on Film":
                return "Low Volume / Confirm on Film"
            return label
    return "Insufficient Sample"


def _filters_text(row, group_columns) -> str:
    parts = []
    for c in group_columns:
        v = row[c]
        if isinstance(v, (bool,)) or str(v) in {"True", "False"}:
            v = "Yes" if str(v) == "True" else "No"
        parts.append(f"{c.replace('_', ' ')} = {v}")
    return " | ".join(parts)


def _implication(row) -> str:
    who = row["Filters"]
    if row["Tendency"] == "Run":
        call = "Favor run fits / extra hat in the box"
    else:
        call = "Favor pass-first coverage / rush plan"
    tag = " — confirm on film" if row["Confidence"].startswith("Low") else ""
    return f"{who}: {row['Rate']:.0%} {row['Tendency'].lower()} ({row['Plays']} plays, {row['Games']} games). {call}{tag}."


def tendency_table(df: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
    """Every group, no threshold filtering. The transparent raw table."""
    bad = set(group_columns) & POST_SNAP_COLUMNS
    if bad:
        raise ValueError(f"Post-snap columns cannot define a pre-snap tendency: {bad}")
    src = df[df["Run_Pass"].isin(["Run", "Pass"])].copy()
    if src.empty:
        return pd.DataFrame()
    for c in group_columns:
        src[c] = src[c].astype("string").fillna("Unknown")   # groupby drops NaN otherwise
    g = src.groupby(group_columns, dropna=False)
    out = g["Run_Pass"].agg(
        Run=lambda s: int((s == "Run").sum()),
        Pass=lambda s: int((s == "Pass").sum()),
    ).reset_index()
    out["Games"] = g["Game_ID"].nunique().values
    out["Plays"] = out["Run"] + out["Pass"]
    out["Run_Rate"] = out["Run"] / out["Plays"]
    out["Pass_Rate"] = out["Pass"] / out["Plays"]
    out["Tendency"] = out["Pass_Rate"].gt(out["Run_Rate"]).map({True: "Pass", False: "Run"})
    out["Rate"] = out[["Run_Rate", "Pass_Rate"]].max(axis=1)
    base_pass = (src["Run_Pass"] == "Pass").mean()
    out["Team_Baseline"] = out["Tendency"].map({"Pass": base_pass, "Run": 1 - base_pass})
    out["Lift"] = out["Rate"] - out["Team_Baseline"]
    out["Confidence"] = [confidence_label(p, r, gm) for p, r, gm in zip(out["Plays"], out["Rate"], out["Games"])]
    out["Filters"] = out.apply(lambda r: _filters_text(r, group_columns), axis=1)
    return out.sort_values("Plays", ascending=False).reset_index(drop=True)


def build_run_pass_alerts(
    df: pd.DataFrame,
    group_columns: list[str],
    high_threshold: float = ALERT_THRESHOLD_HIGH,
    watch_threshold: float = ALERT_THRESHOLD_WATCH,
    min_plays: int = MIN_ALERT_PLAYS,
    min_lift: float = MIN_LIFT_OVER_BASELINE,
) -> pd.DataFrame:
    """Alerts = groups that clear the threshold AND beat the team's own baseline.
    A 72% pass rate means nothing if the team throws 70% overall."""
    t = tendency_table(df, group_columns)
    if t.empty:
        return t
    eligible = (t["Plays"] >= min_plays) & (t["Lift"] >= min_lift)
    t["Alert_Level"] = "No Alert"
    t.loc[eligible & (t["Rate"] >= watch_threshold), "Alert_Level"] = "Watch Alert"
    t.loc[eligible & (t["Rate"] >= high_threshold), "Alert_Level"] = "High Alert"
    alerts = t[t["Alert_Level"] != "No Alert"].copy()
    if alerts.empty:
        return alerts
    alerts["Coaching_Implication"] = alerts.apply(_implication, axis=1)
    cols = group_columns + ["Plays", "Games", "Run", "Pass", "Run_Rate", "Pass_Rate", "Tendency",
                            "Rate", "Team_Baseline", "Lift", "Alert_Level", "Confidence",
                            "Filters", "Coaching_Implication"]
    return alerts[cols].sort_values(["Alert_Level", "Rate", "Plays"],
                                    ascending=[True, False, False]).reset_index(drop=True)
