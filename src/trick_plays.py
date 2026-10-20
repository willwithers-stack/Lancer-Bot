"""Trick Play Inventory: every gadget call, by opponent and play number.

Built from ALL rows (not just offensive snaps) so fake punts / fake FGs tagged
under ODK = K are not lost.
"""
from __future__ import annotations

import re
import pandas as pd

from src.config import TRICK_PLAY_PATTERNS, FAKE_KICK_PLAY_TYPES, FAKE_KICK_RESULTS


def _tok(v) -> str:
    return "" if pd.isna(v) else " " + re.sub(r"[^A-Z0-9]+", " ", str(v).upper()).strip() + " "


def classify_trick(call, result="", patterns=TRICK_PLAY_PATTERNS) -> str | None:
    text = _tok(call) + _tok(result)
    for label, pats in patterns:
        if any(f" {p} " in text for p in pats):
            return label
    return None


def build_trick_play_inventory(all_rows: pd.DataFrame, patterns=TRICK_PLAY_PATTERNS) -> pd.DataFrame:
    df = all_rows.copy()
    get = lambda c: df[c] if c in df.columns else pd.Series(pd.NA, index=df.index)
    call, result = get("Off_Play"), get("Result")
    ptype = get("Play_Type").astype("string").fillna("").str.upper().str.strip()
    res_u = result.astype("string").fillna("").str.upper().str.strip()

    trick = [classify_trick(c, r, patterns) for c, r in zip(call, result)]
    fake_kick = ptype.isin(FAKE_KICK_PLAY_TYPES) & res_u.isin(FAKE_KICK_RESULTS)
    df["Trick_Type"] = trick
    df.loc[fake_kick & df["Trick_Type"].isna(), "Trick_Type"] = (
        ptype[fake_kick].map(lambda p: "Fake Punt" if p == "PUNT" else "Fake Field Goal / PAT"))
    hits = df[df["Trick_Type"].notna()].copy()
    if hits.empty:
        return pd.DataFrame(columns=["Opponent", "Play #", "Formation", "Call", "Trick Type"])

    odk = hits.get("ODK", pd.Series("", index=hits.index)).astype("string").fillna("").str.upper()
    hits["Note"] = ""
    hits.loc[odk.eq("K"), "Note"] = "Special teams row: confirm which team ran it"
    col = lambda c: hits[c] if c in hits.columns else pd.Series(pd.NA, index=hits.index)
    dn = pd.to_numeric(col("Down"), errors="coerce")
    dist = pd.to_numeric(col("Distance"), errors="coerce")
    hits["Down & Dist"] = [f"{int(a)} & {int(b)}" if pd.notna(a) and pd.notna(b) else "" for a, b in zip(dn, dist)]

    out = pd.DataFrame({
        "Opponent": hits["Game_ID"],
        "Play #": pd.to_numeric(col("Play_Number"), errors="coerce").astype("Int64"),
        "Formation": col("Formation_Raw"),
        "Call": col("Off_Play"),
        "Trick Type": hits["Trick_Type"],
        "Qtr": col("Quarter"),
        "Down & Dist": hits["Down & Dist"],
        "Yard Ln": col("Yard_Line"),
        "Hash": col("Hash"),
        "Result": col("Result"),
        "Gain": pd.to_numeric(col("Gain"), errors="coerce"),
        "Note": hits["Note"],
    })
    return out.sort_values(["Opponent", "Play #"]).reset_index(drop=True)
