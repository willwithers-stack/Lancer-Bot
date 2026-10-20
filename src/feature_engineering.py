"""Situation buckets and flags. Every function tolerates missing columns and text values."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import EXPLOSIVE_GAIN_YARDS
from src.formation_mapping import apply_formation_mapping


def _col(df: pd.DataFrame, name: str, default="") -> pd.Series:
    """Safe column getter. df.get(name, '') returns a plain str when the column is
    missing, which breaks .fillna() — this always returns a Series."""
    if name in df.columns:
        return df[name]
    return pd.Series(default, index=df.index)


def _num(df, name) -> pd.Series:
    return pd.to_numeric(_col(df, name, np.nan), errors="coerce")


def normalize_yard_line(value) -> float:
    """Hudl YARD LN: negative = own side (-35 = own 35), positive = opponent side
    (+25 = opp 25), 50 = midfield. Returns distance from OWN goal line (0-100)."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return np.nan
    if np.isnan(v):
        return np.nan
    if v < 0:
        return abs(v)
    if v == 50 or v == 0:
        return 50.0 if v == 50 else np.nan
    return 100 - v


def bucket_down(down) -> str:
    try:
        d = int(float(down))
    except (TypeError, ValueError):
        return "Unknown"
    return {1: "1st Down", 2: "2nd Down", 3: "3rd Down", 4: "4th Down"}.get(d, "Unknown")


def bucket_distance(distance) -> str:
    try:
        d = float(distance)
    except (TypeError, ValueError):
        return "Unknown"
    if np.isnan(d) or d <= 0:
        return "Unknown"
    if d <= 3:
        return "Short (1-3)"
    if d <= 6:
        return "Medium (4-6)"
    if d <= 10:
        return "Long (7-10)"
    return "Extra Long (11+)"


def bucket_field_zone(own_yard_line) -> str:
    """Input is distance from own goal line (use normalize_yard_line first)."""
    if pd.isna(own_yard_line):
        return "Unknown"
    y = float(own_yard_line)
    if y <= 10:
        return "Backed Up (own 1-10)"
    if y <= 39:
        return "Own Territory"
    if y <= 60:
        return "Midfield (own 40 - opp 40)"
    if y < 80:
        return "Plus Territory (opp 39-21)"
    if y < 90:
        return "Red Zone (opp 20-11)"
    return "Goal-to-Go Zone (opp 10-1)"


def score_state(diff) -> str:
    """Symmetric buckets. Two-score game in HS = 9+."""
    if pd.isna(diff):
        return "Unknown"
    d = float(diff)
    if d <= -9:
        return "Trailing 9+"
    if d < 0:
        return "Trailing 1-8"
    if d == 0:
        return "Tied"
    if d < 9:
        return "Leading 1-8"
    return "Leading 9+"


def success_flag(down, distance, gain) -> bool | float:
    """Standard success rate: 40% of distance on 1st, 60% on 2nd, 100% on 3rd/4th.
    Post-snap — descriptive use only."""
    if pd.isna(down) or pd.isna(distance) or pd.isna(gain):
        return np.nan
    need = {1: 0.4, 2: 0.6}.get(int(down), 1.0) * float(distance)
    return bool(gain >= need)


def _flag_from_text(series: pd.Series) -> pd.Series:
    t = series.astype("string").fillna("").str.strip().str.upper()
    return ~t.isin(["", "NO", "N", "NONE", "0", "FALSE", "NAN"])


def add_analysis_features(df: pd.DataFrame, family_rules=None) -> pd.DataFrame:
    data = apply_formation_mapping(df, family_rules) if family_rules else apply_formation_mapping(df)

    data["Down_Bucket"] = _col(data, "Down", np.nan).map(bucket_down)
    data["Distance_Bucket"] = _col(data, "Distance", np.nan).map(bucket_distance)
    data["Down_Distance"] = data["Down_Bucket"].str[:3] + " & " + data["Distance_Bucket"].str.split(" ").str[0]
    data["Own_Yard_Line"] = _col(data, "Yard_Line", np.nan).map(normalize_yard_line)
    data["Field_Zone"] = data["Own_Yard_Line"].map(bucket_field_zone)
    data["Red_Zone_Flag"] = data["Own_Yard_Line"] >= 80
    data["Score_State"] = _num(data, "Score_Differential").map(score_state)

    for col in ["Hash", "Personnel", "Strength", "Boundary_Field"]:
        data[col] = _col(data, col, "Unknown").astype("string").fillna("Unknown").str.strip().str.upper().replace("", "UNKNOWN")
    data["Hash"] = data["Hash"].replace({"LEFT": "L", "LH": "L", "RIGHT": "R", "RH": "R", "MIDDLE": "M", "MID": "M"})

    # Boundary/Field: if not tagged, derive strength-to-field from hash + strength.
    if (data["Boundary_Field"] == "UNKNOWN").all():
        side = data["Strength"].str[0]
        data["Boundary_Field"] = np.select(
            [data["Hash"].eq("M"), data["Hash"].isin(["L", "R"]) & side.isin(["L", "R"]) & (data["Hash"] != side),
             data["Hash"].isin(["L", "R"]) & side.isin(["L", "R"]) & (data["Hash"] == side)],
            ["Middle", "Strength to Field", "Strength to Boundary"],
            default=np.where(data["Strength"].isin(["BAL", "BALANCED"]), "Balanced", "Unknown"))

    data["Motion_Flag"] = _flag_from_text(_col(data, "Motion"))
    data["Shift_Flag"] = _flag_from_text(_col(data, "Shift"))

    data["Gain"] = _num(data, "Gain")
    data["Success_Flag"] = [success_flag(d, t, g) for d, t, g in zip(data["Down"], data["Distance"], data["Gain"])]
    data["Explosive_Flag"] = data["Gain"] > EXPLOSIVE_GAIN_YARDS
    return data
