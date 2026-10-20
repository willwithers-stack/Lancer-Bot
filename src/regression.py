"""Penalized logistic regression to VALIDATE and RANK pre-snap tells.

Key changes vs. the starter:
- No class_weight='balanced' (it distorts predicted pass probabilities).
- Leave-one-game-out validation, so accuracy is measured on games the model never saw.
- Returns a coefficient table coaches can read, not just a fitted object.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, log_loss, roc_auc_score
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from src.config import MIN_REGRESSION_ROWS, MIN_REGRESSION_GAMES, POST_SNAP_COLUMNS


def _prep(df, features):
    data = df[df["Run_Pass"].isin(["Run", "Pass"])].copy()
    x = data[features].astype("string").fillna("Unknown").astype(object)
    y = (data["Run_Pass"] == "Pass").astype(int).to_numpy()
    return data, x, y


def _pipeline(features, C=0.5):
    pre = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=3), features)])
    clf = LogisticRegression(C=C, solver="lbfgs", max_iter=2000)
    return Pipeline([("pre", pre), ("clf", clf)])


def fit_run_pass_model(df: pd.DataFrame, feature_columns: list[str], C: float = 0.5):
    """Returns (result_dict | None, error_message | None)."""
    leaked = set(feature_columns) & POST_SNAP_COLUMNS
    if leaked:
        return None, f"Post-snap columns removed from model: {sorted(leaked)}"
    features = [f for f in feature_columns if f in df.columns and df[f].astype("string").nunique() > 1]
    data, x, y = _prep(df, features)

    if len(data) < MIN_REGRESSION_ROWS:
        return None, f"Only {len(data)} valid run/pass snaps; need {MIN_REGRESSION_ROWS} for regression validation."
    if y.min() == y.max():
        return None, "Every snap is the same play type; nothing to model."
    if not features:
        return None, "No pre-snap feature has more than one value."

    model = _pipeline(features, C).fit(x, y)
    base_rate = y.mean()

    # Held-out validation by game
    games = data["Game_ID"].astype(str).to_numpy()
    validation = {"Games": int(len(set(games))), "Snaps": int(len(y)), "Team_Pass_Rate": float(base_rate)}
    if len(set(games)) >= MIN_REGRESSION_GAMES:
        probs = np.zeros(len(y))
        for tr, te in LeaveOneGroupOut().split(x, y, games):
            if len(set(y[tr])) < 2:
                probs[te] = y[tr].mean()
                continue
            probs[te] = _pipeline(features, C).fit(x.iloc[tr], y[tr]).predict_proba(x.iloc[te])[:, 1]
        pred = (probs >= 0.5).astype(int)
        baseline_acc = max(base_rate, 1 - base_rate)
        validation.update({
            "Held_Out_Accuracy": float(accuracy_score(y, pred)),
            "Always_Guess_Majority": float(baseline_acc),
            "Accuracy_Gain": float(accuracy_score(y, pred) - baseline_acc),
            "Held_Out_AUC": float(roc_auc_score(y, probs)) if len(set(y)) > 1 else np.nan,
            "Held_Out_Log_Loss": float(log_loss(y, np.clip(probs, 1e-6, 1 - 1e-6))),
            "Verdict": ("Pre-snap tells add predictive value on unseen games"
                        if accuracy_score(y, pred) - baseline_acc >= 0.05
                        else "Tells do not clearly beat 'always guess the majority' on unseen games"),
        })
    else:
        validation["Verdict"] = (f"Only {len(set(games))} game(s): model is descriptive only. "
                                 f"Need {MIN_REGRESSION_GAMES}+ games for held-out validation.")

    # Coefficient table: odds of PASS relative to the average snap
    names = model.named_steps["pre"].get_feature_names_out()
    coefs = model.named_steps["clf"].coef_[0]
    rows = []
    for n, c in zip(names, coefs):
        raw = n.replace("cat__", "")
        feat = next((f for f in sorted(features, key=len, reverse=True) if raw.startswith(f + "_")), raw)
        level = raw[len(feat) + 1:]
        rows.append({"Feature": feat, "Value": level, "Coefficient": c, "Odds_Ratio_Pass": float(np.exp(c))})
    coef_table = pd.DataFrame(rows)
    coef_table["Lean"] = np.where(coef_table["Coefficient"] > 0, "Pass", "Run")
    coef_table["Strength"] = pd.cut(coef_table["Coefficient"].abs(), [-1, 0.25, 0.6, 99],
                                    labels=["Weak", "Moderate", "Strong"])
    coef_table = coef_table.reindex(coef_table["Coefficient"].abs().sort_values(ascending=False).index)

    data = data.assign(Model_Pass_Prob=model.predict_proba(x)[:, 1])
    return {"model": model, "features": features, "validation": validation,
            "coefficients": coef_table.reset_index(drop=True), "scored": data}, None
