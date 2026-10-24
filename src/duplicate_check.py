"""Catch upload mistakes before any tendency math runs.

Two problems seen in real Hudl exports:
  1. Stacked games - one file holds two games back to back (PLAY # restarts at 1).
  2. Duplicate games - the same game uploaded twice, often under a different file name.

Stacked games are split into separate games. Exact duplicates are dropped (the first upload
is kept) because counting a game twice inflates Games, sample sizes, and the Accuracy Check.
Partial overlaps are kept but flagged so the coach can check the files.
"""
from __future__ import annotations

from collections import Counter

import pandas as pd

from src.data_ingestion import normalize_columns

# Play content that identifies a snap. PLAY # and Game are left out on purpose:
# a re-export or a renamed file can renumber plays.
FINGERPRINT_COLS = ["ODK", "Quarter", "Down", "Distance", "Yard_Line", "Hash", "Formation_Raw",
                    "Play_Type", "Off_Play", "Play_Direction", "Gain", "Result"]
MIN_GAME_ROWS = 20          # a stacked-game split must leave at least this many rows on each side
OVERLAP_FLAG = 0.50         # share of the smaller game's snaps found in the other game

FINDING_COLS = ["Check", "Game", "Matches", "Overlap", "Action"]


def _norm(v) -> str:
    if pd.isna(v):
        return ""
    s = str(v).strip().upper()
    try:
        f = float(s)
        return str(int(f)) if f == int(f) else str(f)
    except ValueError:
        return " ".join(s.split())


def _fingerprints(raw: pd.DataFrame) -> list[tuple]:
    df, _ = normalize_columns(raw.dropna(how="all"))
    cols = [c for c in FINGERPRINT_COLS if c in df.columns]
    if not cols:
        return []
    rows = df[cols].map(_norm)
    keep = rows.apply(lambda r: any(r[c] for c in cols if c not in ("ODK", "Quarter")), axis=1)
    return [tuple(r) for r in rows[keep].itertuples(index=False)]


def split_stacked_games(sheets: dict[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], list[list]]:
    """Split any sheet whose PLAY # restarts (e.g. ...118, 1, 2, 3...) into separate games."""
    out, findings = {}, []
    for name, raw in sheets.items():
        raw = raw.dropna(how="all")
        df, _ = normalize_columns(raw)
        # Hudl pads some exports with numbered rows that carry no play data; drop them.
        content = df.drop(columns=[c for c in ("Play_Number",) if c in df.columns]).notna().any(axis=1)
        raw, df = raw[content.values], df[content.values]
        if "Play_Number" not in df.columns or ("Game_ID" in df.columns and df["Game_ID"].notna().any()):
            out[name] = raw
            continue
        pn = pd.to_numeric(df["Play_Number"], errors="coerce").ffill()
        running_max = pn.cummax().shift(1)
        resets = pn.index[(pn <= 3) & (running_max >= MIN_GAME_ROWS)].tolist()
        # keep only resets that leave a real game on both sides
        cuts, last = [], 0
        positions = [raw.index.get_loc(i) for i in resets]
        for p in positions:
            if p - last >= MIN_GAME_ROWS and len(raw) - p >= MIN_GAME_ROWS:
                cuts.append(p)
                last = p
        if not cuts:
            out[name] = raw
            continue
        bounds = [0] + cuts + [len(raw)]
        parts = [f"{name} (game {i + 1})" for i in range(len(bounds) - 1)]
        for part, a, b in zip(parts, bounds[:-1], bounds[1:]):
            out[part] = raw.iloc[a:b]
        findings.append(["Stacked games", name, ", ".join(parts), "",
                         f"PLAY # restarts {len(cuts)} time(s); split into {len(parts)} games. Check which one is the opponent you meant."])
    return out, findings


def find_duplicate_games(sheets: dict[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], list[list]]:
    """Drop exact duplicate games; flag heavy overlaps. Upload order decides which copy is kept."""
    fps = {name: _fingerprints(raw) for name, raw in sheets.items()}
    kept, dropped, findings = [], set(), []
    for name in sheets:
        fp = fps[name]
        twin = next((k for k in kept if fp and fps[k] == fp), None)
        if twin is not None:
            dropped.add(name)
            findings.append(["Duplicate game", name, twin, "100%",
                             f"Same snaps as '{twin}'. Dropped '{name}' so the game is not counted twice. "
                             "If the file names point to different opponents, one of them is the wrong export."])
            continue
        for k in kept:
            a, b = Counter(fp), Counter(fps[k])
            small = min(len(fp), len(fps[k]))
            if not small:
                continue
            share = sum((a & b).values()) / small
            if share >= OVERLAP_FLAG:
                findings.append(["Possible duplicate", name, k, f"{share:.0%}",
                                 "Kept both. Most snaps match another upload; check that these are different games."])
        kept.append(name)
    return {k: v for k, v in sheets.items() if k not in dropped}, findings


def check_uploads(sheets: dict[str, pd.DataFrame]) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    """Split stacked games, then remove duplicates. Returns (sheets_to_analyze, findings)."""
    split, f1 = split_stacked_games(sheets)
    kept, f2 = find_duplicate_games(split)
    return kept, pd.DataFrame(f1 + f2, columns=FINDING_COLS)
