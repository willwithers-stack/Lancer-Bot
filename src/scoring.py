"""Rebuild the running score from Hudl results so Score State is pre-snap.

Ported from the original Lancer-Bot app, generalized: the team tagged ODK = O is
the "Scouted Team". Hudl play-type convention used:
  FG / Extra Pt. / 2 Pt.            -> scouted team kicking
  FG Block / Extra Pt. Block        -> opponent kicking (scouted team defending)
  KO Rec / Punt Rec + TD            -> scouted team return TD
  KO / Punt + TD                    -> opponent return TD
"""
from __future__ import annotations

import re

import pandas as pd

SCOUTED, OPP = "Scouted Team", "Opponent"


def _u(v) -> str:
    return "" if pd.isna(v) else str(v).upper().strip()


def add_score_state(full: pd.DataFrame) -> pd.DataFrame:
    out = full.copy()
    odk = out["ODK"].map(_u) if "ODK" in out.columns else pd.Series("O", index=out.index)
    res = out["Result"].map(_u) if "Result" in out.columns else pd.Series("", index=out.index)
    pt = out["Play_Type"].map(_u) if "Play_Type" in out.columns else pd.Series("", index=out.index)

    sc_add = pd.Series(0, index=out.index)
    op_add = pd.Series(0, index=out.index)
    scorer = pd.Series("", index=out.index, dtype=object)
    note = pd.Series("", index=out.index, dtype=object)

    for _, game in out.groupby("Game_ID", sort=False):
        pending = ""
        for idx in game.sort_values("_row_order").index:
            u, r, p = odk[idx], res[idx], pt[idx]
            s = o = 0
            who, why = "", ""
            is_td = re.search(r"\bTD\b", r) is not None
            blocked_side = "BLOCK" in p          # opponent is kicking
            if u == "O":
                if "SAFETY" in r:
                    o, who, why = 2, OPP, "Safety against offense"
                elif is_td and not any(k in r for k in ("INT", "FUMBLE")):
                    s, who, pending, why = 6, SCOUTED, SCOUTED, "Offensive TD"
                elif is_td:
                    o, who, pending, why = 6, OPP, OPP, "Turnover returned for TD"
            elif u == "D":
                if "SAFETY" in r:
                    s, who, why = 2, SCOUTED, "Safety by defense"
                elif "DEF TD" in r or (is_td and any(k in r for k in ("INT", "FUMBLE"))):
                    s, who, pending, why = 6, SCOUTED, SCOUTED, "Defensive TD"
                elif is_td:
                    o, who, pending, why = 6, OPP, OPP, "Opponent offensive TD"
            else:
                good = r.startswith("GOOD")
                if ("EXTRA PT" in p or "2 PT" in p) and good:
                    pts = 2 if "2 PT" in p else 1
                    team = pending or (OPP if blocked_side else SCOUTED)
                    s, o = (pts, 0) if team == SCOUTED else (0, pts)
                    who, why = team, "Conversion good"
                    pending = ""
                elif p.startswith("FG") and good:
                    team = OPP if blocked_side else SCOUTED
                    s, o = (3, 0) if team == SCOUTED else (0, 3)
                    who, why = team, "Field goal good"
                elif is_td and ("REC" in p):
                    s, who, pending, why = 6, SCOUTED, SCOUTED, "Return TD"
                elif is_td and (p.startswith("KO") or p.startswith("PUNT") or "ONSIDE" in p):
                    o, who, pending, why = 6, OPP, OPP, "Opponent return TD"
            sc_add[idx], op_add[idx], scorer[idx], note[idx] = s, o, who, why

    out["Scouted_Points_Added"] = sc_add
    out["Opp_Points_Added"] = op_add
    out["Scoring_Team"] = scorer
    out["Scoring_Note"] = note
    order = out.sort_values("_row_order")
    out["Scouted_Score_Before"] = (order.groupby("Game_ID")["Scouted_Points_Added"].cumsum()
                                   - order["Scouted_Points_Added"]).reindex(out.index)
    out["Opp_Score_Before"] = (order.groupby("Game_ID")["Opp_Points_Added"].cumsum()
                               - order["Opp_Points_Added"]).reindex(out.index)
    out["Score_Differential"] = out["Scouted_Score_Before"] - out["Opp_Score_Before"]
    return out


def score_timeline(full: pd.DataFrame) -> pd.DataFrame:
    ev = full[(full["Scouted_Points_Added"] > 0) | (full["Opp_Points_Added"] > 0)]
    cols = ["Game_ID", "Play_Number", "Quarter", "ODK", "Play_Type", "Result", "Scoring_Team",
            "Scouted_Points_Added", "Opp_Points_Added", "Scouted_Score_Before", "Opp_Score_Before", "Scoring_Note"]
    return ev[[c for c in cols if c in ev.columns]].reset_index(drop=True)


def final_scores(full: pd.DataFrame) -> pd.DataFrame:
    return (full.groupby("Game_ID", sort=False)
            .agg(Scouted_Final=("Scouted_Points_Added", "sum"), Opponent_Final=("Opp_Points_Added", "sum"))
            .reset_index())
