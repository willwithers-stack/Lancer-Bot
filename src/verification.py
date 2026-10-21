"""Behind-the-scenes accuracy check. Coaches never see regression output; they see a
Verified / Developing / Film Only stamp on each alert.

An alert earns VERIFIED only if BOTH:
  1. Consistency: the lean held in most games where the look appeared (2+ plays).
  2. Held-out test: a model trained WITHOUT each game still predicted that lean for
     those snaps in the game it never saw (penalized logistic regression, leave-one-game-out).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import MIN_REGRESSION_GAMES

VERIFIED, DEVELOPING, FILM_ONLY, PENDING = "✓ Verified", "Developing", "Film Only", "Pending (needs 3+ games)"
MODEL_MARGIN = 0.05   # held-out prediction must lean 5+ pts past team baseline


def _key(df, cols):
    return df[cols].astype("string").fillna("Unknown").agg(" | ".join, axis=1)


def verify_alerts(alerts: pd.DataFrame, data: pd.DataFrame, group_cols: list[str], reg: dict | None) -> pd.DataFrame:
    if alerts is None or alerts.empty:
        return alerts
    out = alerts.copy()
    rp = data[data["Run_Pass"].isin(["Run", "Pass"])].copy()
    rp["_k"] = _key(rp, group_cols)
    out["_k"] = _key(out, group_cols)
    games_total = rp["Game_ID"].nunique()

    held = pd.Series(np.nan, index=rp.index)
    if reg and "scored" in reg and "Held_Out_Pass_Prob" in reg["scored"]:
        held = reg["scored"]["Held_Out_Pass_Prob"].reindex(rp.index)
    base_pass = (rp["Run_Pass"] == "Pass").mean()

    held_in, appeared, status = [], [], []
    for _, row in out.iterrows():
        g = rp[rp["_k"] == row["_k"]]
        want = row["Tendency"]
        per_game = g.groupby("Game_ID")["Run_Pass"].agg(lambda s: ((s == want).mean(), len(s)))
        eligible = [r for r, n in per_game if n >= 2]
        ok = sum(r > 0.5 for r in eligible)
        held_in.append(ok)
        appeared.append(len(eligible))
        consistent = len(eligible) >= 2 and ok / len(eligible) >= 0.67

        if games_total < MIN_REGRESSION_GAMES or held.loc[g.index].isna().all():
            status.append(PENDING if consistent else FILM_ONLY)
            continue
        p = held.loc[g.index].mean()
        model_agrees = (p - base_pass >= MODEL_MARGIN) if want == "Pass" else (base_pass - p >= MODEL_MARGIN)
        if consistent and model_agrees:
            status.append(VERIFIED)
        elif consistent or model_agrees:
            status.append(DEVELOPING)
        else:
            status.append(FILM_ONLY)
    out["Held_Up"] = [f"{a} of {b} game{'' if b == 1 else 's'}" if b else "—" for a, b in zip(held_in, appeared)]
    out["Accuracy_Check"] = status
    return out.drop(columns="_k")
