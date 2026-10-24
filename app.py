"""FormationIQ — upload Hudl game files, click Analyze, get a scouting report."""
import io

import pandas as pd
import streamlit as st

from src.config import (ALERT_THRESHOLD_HIGH, ALERT_THRESHOLD_WATCH, MIN_ALERT_PLAYS,
                        MIN_FIRST_DRIVE_GAMES, PRE_SNAP_MODEL_FEATURES, OPPONENT_PROFILES)
from src.data_ingestion import read_uploads
from src.duplicate_check import check_uploads
from src.cleaning import clean_hudl_export
from src.feature_engineering import add_analysis_features
from src.formation_mapping import unmapped_formations
from src.alert_engine import build_run_pass_alerts, tendency_table
from src.regression import fit_run_pass_model
from src.trick_plays import build_trick_play_inventory
from src.scoring import score_timeline, final_scores
from src.report_builder import build_workbook
from src.verification import verify_alerts
from src.pass_types import (build_pass_type_alerts, pass_type_table, pass_type_results,
                            play_action_after_run, launch_vs_strength, pass_type_quality)

st.set_page_config(page_title="FormationIQ", page_icon="🏈", layout="wide")
st.title("FormationIQ")
st.caption("Upload Hudl game files (one per game). Tendencies use the team tagged ODK = O, run/pass snaps only.")

PCT_COLS = ["Run_Rate", "Pass_Rate", "Rate", "Team_Baseline", "Lift", "Share", "Comp_Pct", "Success", "Explosive",
            "PA_Movement_Pct", "Quick_Pct", "Dropback_Pct", "Screen_Pct", "Trick_Pct",
            "Quick %", "Dropback %", "Play Action / Movement %", "Screen %", "Trick Play %"]
PT_COLS = ["Passes", "Games", "Quick %", "Dropback %", "Play Action / Movement %", "Screen %", "Trick Play %",
           "Top_Type", "Rate", "Lift", "Confidence"]
PT_ALERT_COLS = ["Passes", "Games", "Top_Type", "Rate", "Lift", "Confidence", "Accuracy_Check", "Held_Up",
                 "Alert_Level", "Coaching_Implication"]
CORE_COLS = ["Plays", "Games", "Run", "Pass", "Tendency", "Rate", "Lift", "Confidence"]
ALERT_COLS = CORE_COLS + ["Accuracy_Check", "Held_Up", "Alert_Level", "Coaching_Implication"]
PROMISE = (
    "**FormationIQ Accuracy Promise**  \n"
    "Every number is counted straight from your Hudl tags, with no estimates. "
    "Every tell is tested against games it wasn't built from before it earns **✓\u00a0Verified**. "
    "If a number ever doesn't match your film, you can trace it to the exact play in the play-by-play.  \n"
    "Tendencies show what an offense has done, not a promise of what it will call."
)
DD_ORDER = [f"{d} & {k}" for d in ("1st", "2nd", "3rd", "4th") for k in ("Short", "Medium", "Long", "Extra")]

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    profile = st.selectbox("Opponent formation profile", list(OPPONENT_PROFILES), index=0)
    st.header("Alert Settings")
    high = st.slider("High-alert threshold", 0.60, 0.90, ALERT_THRESHOLD_HIGH, 0.01)
    watch = st.slider("Watch-alert threshold", 0.55, 0.85, ALERT_THRESHOLD_WATCH, 0.01)
    min_plays = st.number_input("Minimum plays per alert", 3, 30, MIN_ALERT_PLAYS)
    show_all = st.toggle("Show all table columns", value=False)
    if watch > high:
        st.warning("Watch threshold is above High; using High for both.")
        watch = high


def show(df: pd.DataFrame, group_cols=None, alert=False, empty_msg="No results clear the current thresholds.", pt=False):
    if df is None or df.empty:
        st.info(empty_msg)
        return
    if group_cols is not None and not show_all:
        if pt:
            keep = group_cols + (PT_ALERT_COLS if alert else PT_COLS)
        else:
            keep = group_cols + (ALERT_COLS if alert else CORE_COLS)
        df = df[[c for c in keep if c in df.columns]]
    fmt = {c: "{:.0%}" for c in PCT_COLS if c in df.columns}
    st.dataframe(df.style.format(fmt), width="stretch", hide_index=True)


@st.cache_data(show_spinner="Cleaning and tagging snaps...")
def process(files: tuple, profile: str):
    bufs = []
    for name, raw in files:
        b = io.BytesIO(raw)
        b.name = name
        bufs.append(b)
    sheets, findings = check_uploads(read_uploads(bufs))
    clean, quality, meta = clean_hudl_export(sheets)
    meta["upload_findings"] = findings
    return add_analysis_features(clean, OPPONENT_PROFILES[profile]), quality, meta


@st.cache_data(show_spinner="Running regression validation...")
def run_regression(data: pd.DataFrame, features: tuple):
    return fit_run_pass_model(data, list(features))


uploaded = st.file_uploader("Upload Hudl exports (one file per game; select several at once or use +)",
                            type=["xlsx", "xls", "csv"], accept_multiple_files=True)
if not uploaded:
    st.info("Upload one or more Hudl game exports, then click Analyze.")
    st.stop()
if not st.button("Analyze", type="primary") and "analyzed" not in st.session_state:
    st.stop()
st.session_state["analyzed"] = True

try:
    data, quality, meta = process(tuple((f.name, f.getvalue()) for f in uploaded), profile)
except ValueError as e:
    st.error(str(e))
    st.stop()

rp = data[data["Run_Pass"].isin(["Run", "Pass"])]
games = meta["games"]
alert_args = dict(high_threshold=high, watch_threshold=watch, min_plays=int(min_plays))


def tagged(cols):
    """Drop columns the files never tagged (e.g. Near_Far all 'None')."""
    return [c for c in cols if c in data.columns and data[c].astype("string").nunique() > 1]


st.success(f"Processed {len(data):,} offensive snaps across {games} game(s): {', '.join(map(str, data['Game_ID'].unique()))}.")
findings = meta.get("upload_findings", pd.DataFrame())
if len(findings):
    st.warning("**Upload check found file problems.** Review before using these numbers.\n\n" + "\n".join(
        f"- **{r.Check}:** {r.Game}" + (f" matches {r.Matches} ({r.Overlap})" if r.Check != "Stacked games" else f" → {r.Matches}") + f". {r.Action}"
        for r in findings.itertuples()))

# ---------------------------------------------------------------- build tables once (used by tabs + Excel)
form_cols = tagged(["Formation_Family", "Near_Far"])
comp_cols = tagged(["Formation_Family", "Near_Far", "Motion_Flag", "Down_Distance"])
feats = tuple(f for f in PRE_SNAP_MODEL_FEATURES if f in data.columns)
reg, reg_err = run_regression(data, feats)   # runs silently; only feeds the Accuracy Check
T = {
    "formation_alerts": verify_alerts(build_run_pass_alerts(data, form_cols, **alert_args), data, form_cols, reg),
    "composite_alerts": verify_alerts(build_run_pass_alerts(data, comp_cols, **alert_args), data, comp_cols, reg),
    "formation": tendency_table(data, ["Formation_Family"]),
    "formation_std": tendency_table(data, ["Formation_Standard"]),
    "formation_mod": tendency_table(data, ["Formation_Family", "Formation_Modifier"]),
    "qb": tendency_table(data, ["QB_Alignment"]),
    "motion": tendency_table(data, ["Motion_Flag"]),
    "motion_form": tendency_table(data, ["Formation_Family", "Motion_Flag"]),
    "dd": tendency_table(data, ["Down_Distance"]),
    "field_zone": tendency_table(data, ["Field_Zone"]),
    "hash": tendency_table(data, ["Hash"]),
    "score": tendency_table(data, ["Score_State"]),
    "score_dd": tendency_table(data, ["Score_State", "Down_Distance"]),
    "boundary": tendency_table(data, ["Boundary_Field"]),
    "quarter": tendency_table(data, ["Quarter"]) if "Quarter" in data else pd.DataFrame(),
}
if not T["dd"].empty:
    T["dd"] = T["dd"].assign(_o=T["dd"]["Down_Distance"].map(lambda v: DD_ORDER.index(v) if v in DD_ORDER else 99)).sort_values("_o").drop(columns="_o")
# Pass Type IQ: Quick / Dropback / Play Action-Movement / Screen, among classified passes.
pt_args = dict(high_threshold=high, watch_threshold=watch, min_plays=int(min_plays))
PT = {
    "alerts_form": build_pass_type_alerts(data, form_cols or ["Formation_Family"], **pt_args),
    "alerts_dd": build_pass_type_alerts(data, ["Down_Distance"], **pt_args),
    "alerts_comp": build_pass_type_alerts(data, tagged(["Formation_Family", "Down_Distance"]) or ["Formation_Family"], **pt_args),
    "formation": pass_type_table(data, ["Formation_Family"]),
    "dd": pass_type_table(data, ["Down_Distance"]),
    "form_dd": pass_type_table(data, ["Formation_Family", "Down_Distance"]),
    "qb": pass_type_table(data, ["QB_Alignment"]),
    "field_zone": pass_type_table(data, ["Field_Zone"]),
    "hash": pass_type_table(data, ["Hash"]),
    "score": pass_type_table(data, ["Score_State"]),
    "detail": pass_type_table(data, ["Formation_Family"], level="Pass_Type"),
    "results": pass_type_results(data),
    "results_detail": pass_type_results(data, level="Pass_Type"),
    "pa_after_run": play_action_after_run(data),
    "launch": launch_vs_strength(data),
}
quality = pd.concat([quality, pd.DataFrame(pass_type_quality(data), columns=quality.columns)], ignore_index=True)
_f = meta.get("upload_findings", pd.DataFrame())
quality = pd.concat([quality, pd.DataFrame([
    ("Duplicate games dropped", int((_f["Check"] == "Duplicate game").sum()) if len(_f) else 0, "Same snaps uploaded twice; first upload kept"),
    ("Possible duplicates (kept)", int((_f["Check"] == "Possible duplicate").sum()) if len(_f) else 0, "Most snaps match another upload; check the files"),
    ("Stacked-game files split", int((_f["Check"] == "Stacked games").sum()) if len(_f) else 0, "PLAY # restarted inside one file"),
], columns=quality.columns)], ignore_index=True)
classified = data["Pass_Type_Source"].isin(["Tagged", "Inferred from play name"]) if "Pass_Type_Source" in data else pd.Series(False, index=data.index)
tricks = build_trick_play_inventory(meta["trick_source"])
ex_cols = [c for c in ["Game_ID", "Play_Number", "Quarter", "Down", "Distance", "Yard_Line", "Hash", "Formation_Raw",
                       "Formation_Family", "Motion", "Run_Pass", "Pass_Type", "Off_Play", "Play_Direction", "Gain", "Result"] if c in data.columns]
explosives = data[data["Explosive_Flag"]][ex_cols]
timeline = score_timeline(meta["score_rows"]) if meta.get("score_rows") is not None else pd.DataFrame()
finals = final_scores(meta["score_rows"]) if meta.get("score_rows") is not None else pd.DataFrame()
first_drive = data[data["First_Drive_Flag"]]

with st.sidebar:
    st.divider()
    st.header("Summary")
    st.metric("Run/Pass Snaps", len(rp))
    st.metric("Pass Rate", f"{(rp['Run_Pass'] == 'Pass').mean():.0%}" if len(rp) else "—")
    st.metric("Games", games)
    st.divider()
    readme = pd.DataFrame([
        ["Games", ", ".join(map(str, data["Game_ID"].unique()))],
        ["Upload check", "; ".join(f"{r.Check}: {r.Game} ({r.Matches})" for r in _f.itertuples()) if len(_f) else "No duplicate or stacked games found."],
        ["Sample", "Team tagged ODK = O, run/pass snaps only. Timeouts and dead-ball penalties removed."],
        ["Pre-snap rule", "Alerts and regression use only pre-snap info. Gain, result, and play direction are post-snap."],
        ["Score state", "Rebuilt from TD/FG/PAT results; score is BEFORE the snap."],
        ["Alert rule", f"High ≥ {high:.0%}, Watch ≥ {watch:.0%}, min {int(min_plays)} plays, and ≥10 pts above team baseline."],
        ["Confidence", "High (15+ plays, 70%+), Usable (10+, 65%+), Low Volume (6+), No Clear Lean (6+ but under watch rate)."],
        ["Pass Type", "Quick / Dropback / Play Action-Movement / Screen, among passes only. From the PASS TYPE column when tagged; "
                      "otherwise inferred from the play name (marked in Pass_Type_Source). Pass-type alerts are checked game by game "
                      "and top out at Developing; no regression model sits behind them yet."],
        ["Accuracy Promise", "Every number is counted directly from the Hudl tags. Every alert is tested against games it was not built from; "
                             "only tells that hold up earn ✓ Verified. Developing = passed one test. Film Only = confirm on film. "
                             "Pending = needs 3+ games. Tendencies describe what an offense has done, not a promise of what it will call."],
    ], columns=["Item", "Detail"])
    sections = [
        ("Read Me", "FORMATIONIQ — SCOUTING WORKBOOK", readme),
        ("Formation Alerts", "FORMATION ALERTS", T["formation_alerts"]),
        ("Composite Alerts", "COMPOSITE ALERTS", T["composite_alerts"]),
        ("Formation IQ", "FORMATION FAMILY TENDENCIES", T["formation"]),
        ("Formation Detail", "FORMATION (STANDARDIZED TAG) TENDENCIES", T["formation_std"]),
        ("Motion IQ", "MOTION BY FORMATION", T["motion_form"]),
        ("Down & Distance", "DOWN & DISTANCE TENDENCIES", T["dd"]),
        ("Score + D&D", "SCORE STATE + DOWN & DISTANCE", T["score_dd"]),
        ("Pass Type Alerts", "PASS TYPE ALERTS (FORMATION, D&D, FORMATION + D&D)",
         pd.concat([PT["alerts_form"], PT["alerts_dd"], PT["alerts_comp"]], ignore_index=True)),
        ("Pass Type IQ", "PASS TYPE BY FORMATION", PT["formation"]),
        ("Pass Type D&D", "PASS TYPE BY DOWN & DISTANCE", PT["dd"]),
        ("Pass Type Detail", "PASS TYPE DETAIL (BOOT, NAKED, RPO...) BY FORMATION", PT["detail"]),
        ("Pass Type Results", "RESULTS BY PASS TYPE", pd.concat([PT["results"], PT["results_detail"]], ignore_index=True)),
        ("PA After Run", "PLAY ACTION / MOVEMENT BY PREVIOUS SNAP", PT["pa_after_run"]),
        ("Field Zone", "FIELD ZONE TENDENCIES", T["field_zone"]),
        ("Hash", "HASH TENDENCIES", T["hash"]),
        ("Field-Boundary", "STRENGTH TO FIELD / BOUNDARY", T["boundary"]),
        ("Explosive Plays", "EVERY GAIN OVER 20 YARDS", explosives),
        ("Trick Plays", "TRICK PLAY INVENTORY", tricks),
        ("Score Timeline", "SCORING EVENTS", timeline),
        ("Data Quality", "DATA QUALITY CHECKS", quality),
        ("All Plays", "CLEAN OFFENSIVE PLAY LOG", data),
    ]
    if games >= MIN_FIRST_DRIVE_GAMES:
        sections.insert(6, ("First Drive", "FIRST DRIVE — BY PLAY IN DRIVE", tendency_table(first_drive, ["Play_In_Drive"])))
    st.download_button("Download Excel scouting workbook", data=build_workbook(sections),
                       file_name="FormationIQ_Scouting_Report.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ---------------------------------------------------------------- tabs
tabs = st.tabs(["Executive Summary", "First Drive IQ", "Formation IQ", "Motion IQ", "Down & Distance",
                "Situation IQ", "Explosive Plays", "Trick Plays", "Score Timeline", "Pivot Lab", "Data Quality",
                "Pass Type IQ"])

with tabs[0]:
    with st.container(border=True):
        st.markdown(PROMISE)
        if games < 3:
            st.caption(f"{games} game(s) loaded. Alerts show **Pending** until 3+ games are uploaded and the held-out test can run.")
        else:
            n_ver = int((T["formation_alerts"].get("Accuracy_Check", pd.Series(dtype=str)) == "✓ Verified").sum()
                        + (T["composite_alerts"].get("Accuracy_Check", pd.Series(dtype=str)) == "✓ Verified").sum())
            st.caption(f"{n_ver} alert(s) Verified across {games} games.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Run/Pass Snaps", f"{len(rp):,}")
    c2.metric("Pass Rate", f"{(rp['Run_Pass'] == 'Pass').mean():.0%}" if len(rp) else "—")
    c3.metric("Games", games)
    st.subheader("Formation Alerts")
    show(T["formation_alerts"], form_cols, alert=True)
    st.subheader("Composite Alerts (" + " + ".join(c.replace("_", " ") for c in comp_cols) + ")")
    show(T["composite_alerts"], comp_cols, alert=True)
    hidden = [c for c in ["Near_Far", "Motion_Flag", "Personnel", "Score_State"] if not tagged([c])]
    if hidden:
        st.caption("Not tagged in these files, so left out: " + ", ".join(h.replace("_", " ") for h in hidden))

with tabs[1]:
    if games < MIN_FIRST_DRIVE_GAMES:
        st.warning(f"First Drive IQ needs {MIN_FIRST_DRIVE_GAMES}+ games; these files have {games}.")
    else:
        st.caption(f"{len(first_drive)} first-drive snaps across {first_drive['Game_ID'].nunique()} games.")
        t = tendency_table(first_drive, ["Play_In_Drive"])
        show(t.sort_values("Play_In_Drive", key=lambda s: s.astype(int)) if not t.empty else t, ["Play_In_Drive"])
        show(tendency_table(first_drive, ["Formation_Family"]), ["Formation_Family"])
        fd_cols = [c for c in ["Game_ID", "Play_In_Drive", "Down", "Distance", "Yard_Line", "Formation_Raw", "Run_Pass", "Off_Play", "Gain"] if c in first_drive]
        st.dataframe(first_drive[fd_cols], width="stretch", hide_index=True)

with tabs[2]:
    st.subheader("By Formation Family")
    show(T["formation"], ["Formation_Family"])
    st.subheader("By Standardized Formation Tag")
    show(T["formation_std"], ["Formation_Standard"])
    st.subheader("Family + Modifier (Stack, Tight, Wing...)")
    show(T["formation_mod"], ["Formation_Family", "Formation_Modifier"])
    st.subheader("QB Alignment")
    show(T["qb"], ["QB_Alignment"])
    if tagged(["Personnel"]):
        show(tendency_table(data, ["Personnel", "Formation_Family"]), ["Personnel", "Formation_Family"])
    st.subheader("Tags standing as their own family")
    st.caption("These matched no family rule, so they keep their own name. Add them to a family in config.py if they belong with one.")
    show(unmapped_formations(data), empty_msg="Every formation tag matched a family rule.")

with tabs[3]:
    if not tagged(["Motion_Flag"]):
        st.info("No motion tagged in these files.")
    else:
        show(T["motion"], ["Motion_Flag"])
        st.subheader("Motion by Formation")
        show(T["motion_form"], ["Formation_Family", "Motion_Flag"])
        if "Motion" in data:
            st.subheader("By Motion Direction")
            show(tendency_table(data, ["Motion"]), ["Motion"])

with tabs[4]:
    st.subheader("Overall Tendency by Down & Distance")
    show(T["dd"], ["Down_Distance"])
    st.divider()
    opts = [d for d in DD_ORDER if d in set(data["Down_Distance"])]
    pick = st.selectbox("Drill into a down & distance", opts) if opts else None
    if pick:
        dd = data[data["Down_Distance"] == pick]
        st.subheader(f"Formations on {pick}")
        show(tendency_table(dd, ["Formation_Family"]), ["Formation_Family"])
        if "Off_Play" in dd:
            st.subheader("Calls")
            calls = (dd[dd["Run_Pass"].isin(["Run", "Pass"])].groupby(["Run_Pass", "Off_Play"], dropna=False)
                     .agg(Plays=("Gain", "size"), Avg_Gain=("Gain", "mean"), Success=("Success_Flag", "mean"))
                     .reset_index().sort_values("Plays", ascending=False))
            st.dataframe(calls.style.format({"Avg_Gain": "{:.1f}", "Success": "{:.0%}"}), width="stretch", hide_index=True)
        st.subheader("Play-by-Play")
        pbp = [c for c in ["Game_ID", "Play_Number", "Quarter", "Down", "Distance", "Yard_Line", "Hash", "Formation_Raw",
                           "Strength", "Motion", "Run_Pass", "Off_Play", "Play_Direction", "Gain", "Result"] if c in dd]
        st.dataframe(dd[pbp], width="stretch", hide_index=True)

with tabs[5]:
    for title, key, cols in [("Field Zone", "field_zone", ["Field_Zone"]), ("Hash", "hash", ["Hash"]),
                             ("Score State (before the snap)", "score", ["Score_State"]),
                             ("Score State + Down & Distance", "score_dd", ["Score_State", "Down_Distance"]),
                             ("Strength to Field / Boundary", "boundary", ["Boundary_Field"]),
                             ("Quarter", "quarter", ["Quarter"])]:
        st.subheader(title)
        show(T[key], cols)

with tabs[6]:
    st.caption(f"{len(explosives)} plays gained more than 20 yards.")
    if len(explosives):
        st.dataframe(explosives, width="stretch", hide_index=True)
    else:
        st.info("No explosive plays.")

with tabs[7]:
    st.caption("Reverses, fake reverses, double passes, HB/WR passes, flea flickers, hook-and-laterals, fake punts/FGs, "
               "and other gadget calls, found from the play name. Kick plays that ended in a run or pass are flagged as fakes.")
    if tricks.empty:
        st.info("No trick plays found in these files.")
    else:
        c1, c2 = st.columns(2)
        c1.metric("Trick plays", len(tricks))
        c2.metric("Games with a trick play", tricks["Opponent"].nunique())
        st.dataframe(tricks, width="stretch", hide_index=True)

with tabs[8]:
    if timeline.empty and finals.empty:
        st.info("Score could not be rebuilt (no RESULT column, or a score column was supplied).")
    else:
        st.subheader("Calculated Finals")
        st.dataframe(finals, width="stretch", hide_index=True)
        st.caption("Check these against the real finals. If one is off, a scoring play is mis-tagged in Hudl.")
        st.subheader("Scoring Events")
        st.dataframe(timeline, width="stretch", hide_index=True)

with tabs[9]:
    st.subheader("Custom Pivot")
    group_opts = [c for c in ["Formation_Family", "Formation_Standard", "Formation_Modifier", "QB_Alignment", "Motion",
                              "Down_Distance", "Down_Bucket", "Distance_Bucket", "Field_Zone", "Hash", "Strength",
                              "Boundary_Field", "Score_State", "Quarter", "Game_ID", "Off_Play"] if c in data.columns]
    g = st.multiselect("Group by (1-3)", group_opts, default=["Formation_Family"], max_selections=3)
    metric = st.selectbox("Metric", ["Run/Pass Tendency", "Pass Type Mix", "Pass Type Detail", "Avg Gain", "Success %",
                                     "Explosive %", "Play Count"])
    if g:
        if metric == "Run/Pass Tendency":
            show(tendency_table(data, g), g)
        elif metric.startswith("Pass Type"):
            lvl = "Pass_Family" if metric == "Pass Type Mix" else "Pass_Type"
            show(pass_type_table(data, g, level=lvl), g, pt=(lvl == "Pass_Family"), empty_msg="No classified passes.")
        else:
            src = rp.copy()
            for c in g:
                src[c] = src[c].astype("string").fillna("Unknown")
            agg = src.groupby(g).agg(Plays=("Run_Pass", "size"), Avg_Gain=("Gain", "mean"),
                                     Success=("Success_Flag", "mean"), Explosive=("Explosive_Flag", "mean")).reset_index()
            keep = g + ["Plays"] + {"Avg Gain": ["Avg_Gain"], "Success %": ["Success"], "Explosive %": ["Explosive"], "Play Count": []}[metric]
            st.dataframe(agg[keep].sort_values("Plays", ascending=False).style.format(
                {"Avg_Gain": "{:.1f}", "Success": "{:.0%}", "Explosive": "{:.0%}"}), width="stretch", hide_index=True)

with tabs[10]:
    show(quality)
    if len(_f):
        st.subheader("Upload Check")
        st.dataframe(_f, width="stretch", hide_index=True)
    if meta["unmapped_columns"]:
        st.caption("Columns not used: " + ", ".join(meta["unmapped_columns"]))
    st.download_button("Download clean play table (CSV)", data.to_csv(index=False), "formationiq_clean.csv")

with tabs[11]:
    n_pass = int(data["Run_Pass"].eq("Pass").sum())
    n_cls = int(classified.sum())
    n_tag = int(data.get("Pass_Type_Source", pd.Series(dtype=str)).eq("Tagged").sum())
    st.caption("Quick (1/3-step, rhythm, RPO throws) · Dropback (QB sets and reads) · Play Action / Movement "
               "(PA, boot, naked, sprint) · Screen · Trick Play (double pass, reverse pass, flea flicker...). Pass type is what happened, so it is only grouped by pre-snap looks.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Pass snaps", n_pass)
    c2.metric("Pass type known", f"{n_cls} ({n_cls / n_pass:.0%})" if n_pass else "—")
    c3.metric("Hand-tagged", n_tag)
    if n_cls == 0:
        st.info("No pass types found. Add a PASS TYPE column in Hudl (Quick, Dropback, PA, Boot, Naked, Sprint, Screen), "
                "or add the staff's protection numbers to PASS_PROTECTION_SERIES in config.py.")
    else:
        if n_cls > n_tag:
            st.caption(f"{n_cls - n_tag} pass type(s) inferred from the play name. Confirm on film or tag PASS TYPE.")
        st.subheader("Team Pass-Type Mix")
        res = PT["results"]
        st.dataframe(res.style.format({"Share": "{:.0%}", "Comp_Pct": "{:.0%}", "Avg_Gain": "{:.1f}",
                                       "Success": "{:.0%}", "Explosive": "{:.0%}"}, na_rep="—"),
                     width="stretch", hide_index=True)
        st.subheader("Pass Type Alerts")
        st.caption("Same rules as run/pass alerts: threshold, minimum passes, and 10+ pts above the team's own mix. "
                   "Checked game by game; tops out at Developing.")
        show(PT["alerts_form"], form_cols or ["Formation_Family"], alert=True, pt=True)
        show(PT["alerts_dd"], ["Down_Distance"], alert=True, pt=True, empty_msg="No down & distance pass-type alerts.")
        comp_pt = tagged(["Formation_Family", "Down_Distance"]) or ["Formation_Family"]
        show(PT["alerts_comp"], comp_pt, alert=True, pt=True, empty_msg="No formation + down & distance pass-type alerts.")
        for title, key, cols in [("By Formation Family", "formation", ["Formation_Family"]),
                                 ("By Down & Distance", "dd", ["Down_Distance"]),
                                 ("Formation + Down & Distance", "form_dd", ["Formation_Family", "Down_Distance"]),
                                 ("By QB Alignment", "qb", ["QB_Alignment"]),
                                 ("By Field Zone", "field_zone", ["Field_Zone"]),
                                 ("By Hash", "hash", ["Hash"]),
                                 ("By Score State", "score", ["Score_State"])]:
            st.subheader(title)
            show(PT[key], cols, pt=True)
        st.subheader("Play Action / Movement After the Run")
        st.caption("Pass-type mix by what happened on the previous snap of the same drive.")
        pa = PT["pa_after_run"]
        if pa.empty:
            st.info("Not enough classified passes.")
        else:
            st.dataframe(pa.style.format({c: "{:.0%}" for c in pa.columns if c.endswith("_Pct")}),
                         width="stretch", hide_index=True)
        st.subheader("Detail: Boot, Naked, Sprint, RPO...")
        show(PT["detail"], ["Formation_Family"], pt=True)
        st.dataframe(PT["results_detail"].style.format({"Share": "{:.0%}", "Comp_Pct": "{:.0%}", "Avg_Gain": "{:.1f}",
                                                         "Success": "{:.0%}", "Explosive": "{:.0%}"}, na_rep="—"),
                     width="stretch", hide_index=True)
        if not PT["launch"].empty:
            st.subheader("Launch Point vs Strength (Boot / Naked / Sprint)")
            st.dataframe(PT["launch"], width="stretch", hide_index=True)
        st.subheader("Every Classified Pass")
        pcols = [c for c in ["Game_ID", "Play_Number", "Quarter", "Down", "Distance", "Yard_Line", "Hash", "Formation_Raw",
                             "Pass_Family", "Pass_Type", "Pass_Type_Source", "Off_Play", "Gain", "Result"] if c in data]
        st.dataframe(data[classified][pcols], width="stretch", hide_index=True)
