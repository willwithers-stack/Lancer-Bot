"""Standardize raw Hudl formation tags into family, QB alignment, and Near/Far.

Near/Far and QB alignment are read from the RAW tag. Standardizing first would
strip those tokens and every play would come out Near_Far = 'None'.
"""
from __future__ import annotations

import re
import pandas as pd

from src.config import FORMATION_FAMILY_RULES, QB_ALIGNMENT_RULES, FORMATION_MODIFIERS


def _tokens(text: str) -> str:
    # Pad with spaces so whole-word matching is a simple substring test.
    return " " + re.sub(r"[^A-Z0-9]+", " ", str(text).upper()).strip() + " "


def _match(text: str, rules) -> str | None:
    padded = _tokens(text)
    for label, patterns in rules:
        for p in patterns:
            if f" {p} " in padded:
                return label
    return None


def formation_family(raw, rules=FORMATION_FAMILY_RULES) -> str:
    if pd.isna(raw) or not str(raw).strip():
        return "Unknown"
    return _match(raw, rules) or "Other"


def qb_alignment(raw, backfield="", rules=QB_ALIGNMENT_RULES) -> str:
    """Hudl BACKFIELD (GUN / Pistol U / EMPTY) wins over the formation tag."""
    for text in (backfield, raw):
        if not pd.isna(text) and str(text).strip():
            hit = _match(text, rules)
            if hit:
                return hit
    return "Unknown"


def formation_modifiers(raw) -> str:
    if pd.isna(raw):
        return "None"
    padded = _tokens(raw)
    found = []
    for pat, label in sorted(FORMATION_MODIFIERS.items(), key=lambda kv: -len(kv[0])):
        if f" {pat} " in padded:
            padded = padded.replace(f" {pat} ", " ")
            found.append(label)
    return ", ".join(sorted(found)) or "None"


def near_far(*texts) -> str:
    padded = " ".join(_tokens(t) for t in texts if not pd.isna(t))
    if " NEAR " in padded or " NR " in padded:
        return "Near"
    if " FAR " in padded:
        return "Far"
    return "None"


def formation_standard(raw) -> str:
    """Raw tag cleaned for display: upper case, single spaces, Near/Far kept,
    side words (RT/LT/RIGHT/LEFT) removed so Trips Rt and Trips Lt pool together."""
    if pd.isna(raw) or not str(raw).strip():
        return "UNKNOWN"
    t = _tokens(raw)
    original = re.sub(r"\s+", " ", t).strip()
    for side in (" RIGHT ", " LEFT ", " RT ", " LT ", " R ", " L "):
        t = t.replace(side, " ")
    # Some taggers use the side word AS the formation ("Right" = Trips Right). Keep it then.
    return re.sub(r"\s+", " ", t).strip() or original


def apply_formation_mapping(df: pd.DataFrame, family_rules=FORMATION_FAMILY_RULES) -> pd.DataFrame:
    data = df.copy()
    raw = data.get("Formation_Raw", pd.Series("", index=data.index))
    backfield = data.get("Backfield", pd.Series("", index=data.index))
    strength = data.get("Strength", pd.Series("", index=data.index))
    data["Formation_Standard"] = raw.map(formation_standard)
    data["Formation_Family"] = raw.map(lambda r: formation_family(r, family_rules))
    data["QB_Alignment"] = [qb_alignment(r, b) for r, b in zip(raw, backfield)]
    data["Formation_Modifier"] = raw.map(formation_modifiers)
    data["Near_Far"] = [near_far(r, b, s) for r, b, s in zip(raw, backfield, strength)]
    return data


def unmapped_formations(df: pd.DataFrame) -> pd.DataFrame:
    """Raw tags that fell into 'Other' — show these to the coach so the dictionary can grow."""
    other = df[df["Formation_Family"] == "Other"]
    return (other.groupby("Formation_Raw").size().rename("Plays")
            .sort_values(ascending=False).reset_index())
