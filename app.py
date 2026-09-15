import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

st.set_page_config(page_title="FormationIQ", page_icon="🏈", layout="wide")

PURPLE = "4B2E83"
LIGHT_PURPLE = "EEE8F6"
LIGHT_GRAY = "F3F4F6"
WHITE = "FFFFFF"
DARK = "202124"
BORDER = "B9A3D0"

COLS = {
    "play_no": "PLAY #",
    "odk": "ODK",
    "quarter": "QTR",
    "down": "DN",
    "distance": "DIST",
    "yard_line": "YARD LN",
    "hash": "HASH",
    "formation": "OFF FORM",
    "strength": "OFF STR",
    "concept": "OFF PLAY",
    "play_type": "PLAY TYPE",
    "gain": "GN/LS",
    "result": "RESULT",
    "motion": "MOTION DIR",
    "play_dir": "PLAY DIR",
}


def normalize_data(df):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    for col in [COLS["play_type"], COLS["odk"], COLS["formation"], COLS["strength"],
                COLS["concept"], COLS["result"], COLS["motion"], COLS["play_dir"], COLS["hash"]]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str).str.strip()
    df[COLS["play_type"]] = df[COLS["play_type"]].str.upper()
    df[COLS["odk"]] = df[COLS["odk"]].str.upper()
    for col in [COLS["play_no"], COLS["quarter"], COLS["down"], COLS["distance"], COLS["yard_line"], COLS["gain"]]:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    return df.reset_index(drop=True)


def add_game_and_drive_ids(df):
    out = df.copy().reset_index(drop=True)
    play_reset = out[COLS["play_no"]].lt(out[COLS["play_no"]].shift(1))
    quarter_reset = (
        out[COLS["quarter"]].lt(out[COLS["quarter"]].shift(1))
        & out[COLS["quarter"]].shift(1).ge(4)
        & out[COLS["quarter"]].le(1)
    )
    new_game = (play_reset | quarter_reset).fillna(False)
    new_game.iloc[0] = True
    out["Game_ID"] = new_game.cumsum()
    out["Play_Order"] = out.groupby("Game_ID").cumcount() + 1
    new_drive = new_game | out[COLS["odk"]].ne(out[COLS["odk"]].shift())
    out["Drive_ID"] = new_drive.cumsum()
    return out


def next_scrimmage_unit(df, game_indices, position):
    future = df.loc[game_indices[position + 1:]]
    future = future[future[COLS["odk"]].isin(["O", "D"])]
    return "" if future.empty else future.iloc[0][COLS["odk"]]


def add_score_state(df):
    out = df.copy().reset_index(drop=True)
    out["TP Points Added"] = 0
    out["Opponent Points Added"] = 0
    out["Scoring Team"] = ""
    out["Scoring Logic Note"] = ""

    for _, game in out.groupby("Game_ID", sort=False):
        pending_td_team = ""
        last_scrimmage_unit = ""
        game_indices = list(game.index)

        for position, idx in enumerate(game_indices):
            unit = out.at[idx, COLS["odk"]]
            result = out.at[idx, COLS["result"]].upper()
            play_type = out.at[idx, COLS["play_type"]].upper()
            tp, opp, scorer, note = 0, 0, "", ""

            if unit == "O" and "TD" in result:
                tp, scorer, pending_td_team, note = 6, "Torrey Pines", "Torrey Pines", "Offensive TD"
            elif unit == "D":
                if "DEF TD" in result:
                    tp, scorer, pending_td_team, note = 6, "Torrey Pines", "Torrey Pines", "Defensive TD"
                elif "SAFETY" in result:
                    tp, scorer, note = 2, "Torrey Pines", "Safety by defense"
                elif "TD" in result:
                    opp, scorer, pending_td_team, note = 6, "Opponent", "Opponent", "Opponent offensive TD"
            elif unit in {"K", "S"}:
                conversion = "EXTRA PT" in play_type or "2 PT" in play_type
                if conversion and result == "GOOD" and pending_td_team:
                    points = 1 if "EXTRA PT" in play_type else 2
                    tp = points if pending_td_team == "Torrey Pines" else 0
                    opp = points if pending_td_team == "Opponent" else 0
                    scorer, note = pending_td_team, "Conversion good"
                elif play_type == "FG" and result == "GOOD":
                    if last_scrimmage_unit == "O":
                        tp, scorer = 3, "Torrey Pines"
                    elif last_scrimmage_unit == "D":
                        opp, scorer = 3, "Opponent"
                    note = "Field goal good"
                elif "TD" in result and ("KO REC" in play_type or "PUNT REC" in play_type):
                    if "PUNT REC" in play_type:
                        receiver = "Opponent" if last_scrimmage_unit == "O" else "Torrey Pines"
                    elif pending_td_team:
                        receiver = "Opponent" if pending_td_team == "Torrey Pines" else "Torrey Pines"
                    else:
                        receiver = "Torrey Pines" if next_scrimmage_unit(out, game_indices, position) == "O" else "Opponent"
                    tp = 6 if receiver == "Torrey Pines" else 0
                    opp = 6 if receiver == "Opponent" else 0
                    scorer, pending_td_team, note = receiver, receiver, "Return TD inferred from flow"
                elif "SAFETY" in result:
                    if "PUNT REC" in play_type and last_scrimmage_unit == "D":
                        opp, scorer, note = 2, "Opponent", "Punt-return safety"
                    else:
                        tp, scorer, note = 2, "Torrey Pines", "Special-teams safety"

            if unit in {"O", "D"}:
                last_scrimmage_unit = unit
            out.at[idx, "TP Points Added"] = tp
            out.at[idx, "Opponent Points Added"] = opp
            out.at[idx, "Scoring Team"] = scorer
            out.at[idx, "Scoring Logic Note"] = note

    out["TP Score Before"] = out.groupby("Game_ID")["TP Points Added"].cumsum() - out["TP Points Added"]
    out["Opponent Score Before"] = out.groupby("Game_ID")["Opponent Points Added"].cumsum() - out["Opponent Points Added"]
    out["Score Differential Before"] = out["TP Score Before"] - out["Opponent Score Before"]

    def bucket(value):
        if value <= -15: return "Trailing 15+"
        if value <= -8: return "Trailing 8-14"
        if value <= -1: return "Trailing 1-7"
        if value == 0: return "Tied"
        if value <= 7: return "Leading 1-7"
        if value <= 14: return "Leading 8-14"
        return "Leading 15+"

    out["Score State"] = out["Score Differential Before"].apply(bucket)
    return out


def prepare_offense(df):
    p = df[(df[COLS["odk"]] == "O") & df[COLS["play_type"]].isin(["RUN", "PASS"])].copy()
    p["Formation"] = p[COLS["formation"]].replace("", "UNLISTED").str.upper()
    p["Motion"] = np.where(p[COLS["motion"]].eq(""), "No Motion", "Motion " + p[COLS["motion"]].str.upper())
    p["Explosive"] = (p[COLS["gain"]] >= 15).astype(int)
    p["Is_FD"] = (p[COLS["gain"]] >= p[COLS["distance"]]).astype(int)

    def success(row):
        if row[COLS["down"]] == 1:
            return int(row[COLS["gain"]] >= row[COLS["distance"]] * .45)
        if row[COLS["down"]] == 2:
            return int(row[COLS["gain"]] >= row[COLS["distance"]] * .65)
        return int(row[COLS["gain"]] >= row[COLS["distance"]])

    p["Is_Succ"] = p.apply(success, axis=1)
    p["Situation"] = np.select(
        [p[COLS["down"]].eq(1),
         p[COLS["down"]].eq(2) & p[COLS["distance"]].le(5),
         p[COLS["down"]].eq(2) & p[COLS["distance"]].between(6, 9),
         p[COLS["down"]].eq(2) & p[COLS["distance"]].ge(10),
         p[COLS["down"]].eq(3) & p[COLS["distance"]].le(3),
         p[COLS["down"]].eq(3) & p[COLS["distance"]].between(4, 6),
         p[COLS["down"]].eq(3) & p[COLS["distance"]].ge(7),
         p[COLS["down"]].eq(4)],
        ["1st Down", "2nd Short (1-5)", "2nd Medium (6-9)", "2nd Long (10+)",
         "3rd Short (1-3)", "3rd Medium (4-6)", "3rd Long (7+)", "4th Down"],
        default="Other",
    )
    return p


def tendency(grouped):
    x = grouped.agg(
        Pass=(COLS["play_type"], lambda s: (s == "PASS").sum()),
        Run=(COLS["play_type"], lambda s: (s == "RUN").sum()),
        Plays=(COLS["play_type"], "size"),
        Yards=(COLS["gain"], "sum"),
        Avg_Gain=(COLS["gain"], "mean"),
        Explosives=("Explosive", "sum"),
        Success_Rate=("Is_Succ", "mean"),
    )
    x["Pass %"] = (x["Pass"] / x["Plays"] * 100).round(1)
    x["Run %"] = (x["Run"] / x["Plays"] * 100).round(1)
    x["Tendency"] = np.where(x["Pass"] >= x["Run"], x["Pass %"].map(lambda v: f"{v:.1f}% PASS"), x["Run %"].map(lambda v: f"{v:.1f}% RUN"))
    x["Avg Gain"] = x.pop("Avg_Gain").round(1)
    x["Success %"] = (x.pop("Success_Rate") * 100).round(1)
    return x.reset_index()


def call_sheet(p):
    rows = []
    def add(priority, alert, expected, sub, confidence, response):
        if not sub.empty:
            rows.append([priority, alert, expected,
                         f"{int((sub[COLS['play_type']] == 'PASS').sum())} P / {int((sub[COLS['play_type']] == 'RUN').sum())} R",
                         confidence, response])
    add(1, "3rd-and-long (7+)", "Pass", p[p["Situation"] == "3rd Long (7+)"], "High", "Pressure with sticks coverage.")
    add(2, "2nd-and-short (1-5)", "Run", p[p["Situation"] == "2nd Short (1-5)"], "High", "Win interior gaps; set the edge and force.")
    q2 = p[(p[COLS["quarter"]] == 2) & (p["Formation"] == "SPREAD")]
    add(3, "Q2 + Spread", "Pass first", q2, "Medium-high", "Pass-oriented call; protect sweep/counter edge.")
    add(4, "Q2 + Spread + right strength", "Pass", q2[q2[COLS["strength"]].str.upper() == "R"], "Medium", "Pressure with coverage integrity and QB contain.")
    add(5, "Motion left", "Run", p[p["Motion"] == "Motion L"], "Medium", "Reset force; fit sweep, power, and split-zone action.")
    left = p[p[COLS["hash"]].str.upper() == "L"]
    if not left.empty:
        rows.append([6, "Left hash", "Explosive alert", f"{int(left['Explosive'].sum())} explosives", "Medium", "Protect explosive; not a run/pass key."])
    return pd.DataFrame(rows, columns=["Priority", "Pre-Snap Alert", "Expected", "Sample", "Confidence", "Defensive Response"])


def write_sheet(ws, title, data):
    ws.sheet_view.showGridLines = False
    ncols = max(1, len(data.columns))
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncols)
    ws["A1"] = title
    ws["A1"].fill = PatternFill("solid", fgColor=PURPLE)
    ws["A1"].font = Font(name="Calibri", size=14, bold=True, color=WHITE)
    ws["A1"].alignment = Alignment(horizontal="center")
    border = Border(*(Side(style="thin", color=BORDER) for _ in range(4)))
    for col, value in enumerate(data.columns, 1):
        cell = ws.cell(3, col, str(value))
        cell.fill = PatternFill("solid", fgColor=PURPLE)
        cell.font = Font(name="Calibri", size=10, bold=True, color=WHITE)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border
    for row_num, row in enumerate(data.itertuples(index=False, name=None), 4):
        for col_num, value in enumerate(row, 1):
            cell = ws.cell(row_num, col_num, None if pd.isna(value) else value)
            cell.fill = PatternFill("solid", fgColor=LIGHT_GRAY if row_num % 2 == 0 else WHITE)
            cell.font = Font(name="Calibri", size=9, color=DARK)
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            cell.border = border
    ws.freeze_panes = "A4"
    ws.auto_filter.ref = f"A3:{get_column_letter(ncols)}{max(3, ws.max_row)}"
    ws.row_dimensions[3].height = 30
    for col_num in range(1, ncols + 1):
        values = [str(ws.cell(r, col_num).value or "") for r in range(3, min(ws.max_row, 103) + 1)]
        ws.column_dimensions[get_column_letter(col_num)].width = min(max(11, max(map(len, values)) + 2), 34)


def build_excel(full_data, p_data):
    formation = tendency(p_data.groupby("Formation")).sort_values("Plays", ascending=False)
    situation = tendency(p_data.groupby(["Score State", "Situation"])).sort_values(["Score State", "Plays"], ascending=[True, False])
    modifiers = tendency(p_data.groupby(["Formation", COLS["strength"], "Motion", "Score State"]))
    modifiers = modifiers[modifiers["Plays"] >= 3].sort_values("Plays", ascending=False)
    quarter = tendency(p_data.groupby([COLS["quarter"], "Score State"])).sort_values([COLS["quarter"], "Plays"], ascending=[True, False])
    motion = tendency(p_data.groupby(["Motion", "Formation"])).sort_values("Plays", ascending=False)
    field_hash = tendency(p_data.groupby(COLS["hash"])).sort_values("Plays", ascending=False)
    attack = tendency(p_data.groupby(["Formation", COLS["play_type"], COLS["concept"], COLS["play_dir"]])).sort_values("Plays", ascending=False)
    explosive = p_data.groupby(["Formation", "Score State"]).agg(Plays=(COLS["play_no"], "size"), Explosives=("Explosive", "sum"), Avg_Gain=(COLS["gain"], "mean")).reset_index()
    explosive["Explosive Rate %"] = (explosive["Explosives"] / explosive["Plays"] * 100).round(1)
    explosive["Avg Gain"] = explosive.pop("Avg_Gain").round(1)
    explosive = explosive.sort_values(["Explosives", "Plays"], ascending=False)
    special = full_data[full_data[COLS["odk"]].isin(["K", "S"])].groupby([COLS["odk"], COLS["play_type"], COLS["result"]]).agg(Plays=(COLS["play_no"], "size"), Avg_Yards=(COLS["gain"], "mean")).reset_index().sort_values("Plays", ascending=False)
    special["Avg_Yards"] = special["Avg_Yards"].round(1)
    score = full_data[(full_data["TP Points Added"] > 0) | (full_data["Opponent Points Added"] > 0)][["Game_ID", "Play_Order", COLS["play_no"], COLS["quarter"], COLS["odk"], COLS["play_type"], COLS["result"], "Scoring Team", "TP Points Added", "Opponent Points Added", "TP Score Before", "Opponent Score Before", "Score Differential Before", "Scoring Logic Note"]]
    validation = full_data.groupby("Game_ID").agg(TP_Final=("TP Points Added", "sum"), Opponent_Final=("Opponent Points Added", "sum"), Rows=(COLS["play_no"], "size")).reset_index()
    readme = pd.DataFrame([
        ["Purpose", "Score-adjusted FormationIQ workbook built from a full O/D/K/S export."],
        ["Offensive sample", "Formation, situation, motion, and call-sheet tabs use only ODK = O plus RUN/PASS plays."],
        ["Score timing", "All score fields are calculated before the snap."],
        ["Game boundaries", "A Game_ID begins when PLAY # resets or QTR returns from Q4 to Q1."],
        ["Pre-snap rule", "Use formation, strength, motion, hash, down/distance, score state, and quarter. PLAY DIR is post-snap only."],
        ["Excel compatibility", "This workbook uses normal worksheet filters, not Excel Table objects."],
    ], columns=["Item", "Instruction"])
    sheets = [
        ("Read Me", "FORMATION IQ — SCORE-ADJUSTED WORKBOOK", readme),
        ("Defensive Call Sheet", "PRINT / GAME-PLAN ALERTS", call_sheet(p_data)),
        ("Situation + Score IQ", "OFFENSIVE TENDENCIES BY SCORE STATE + DOWN/DISTANCE", situation),
        ("Formation IQ", "BASE OFFENSIVE FORMATION TENDENCIES", formation),
        ("Form + Modifiers", "PRE-SNAP FORMATION + STRENGTH + MOTION + SCORE STATE", modifiers),
        ("Quarter IQ", "QUARTER TENDENCIES — FILTER BY SCORE STATE", quarter),
        ("Motion IQ", "MOTION BY FORMATION", motion),
        ("Explosive IQ", "EXPLOSIVE-PLAY RISK", explosive),
        ("Field + Hash IQ", "HASH TENDENCIES", field_hash),
        ("Post-Snap Attack", "POST-SNAP ONLY — PLAY DIRECTION IS NOT A PRE-SNAP TELL", attack),
        ("Special Teams IQ", "KICKING / SPECIAL-TEAMS SUMMARY", special),
        ("Score Timeline", "SCORING EVENTS AND VALIDATION", score),
        ("Score Validation", "CALCULATED FINAL-SCORE CHECK", validation),
        ("All Plays", "MASTER CHRONOLOGICAL LOG", full_data),
    ]
    wb = Workbook()
    wb.remove(wb.active)
    for name, title, data in sheets:
        write_sheet(wb.create_sheet(name), title, data)
    output = BytesIO()
    wb.save(output)
    return output.getvalue()


st.title("🏈 FormationIQ — Score-Adjusted Offensive Scouting")
st.caption("Upload a complete O/D/K/S Hudl export. Formation and tendency analysis uses offensive RUN/PASS snaps only.")
uploaded = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"])

if uploaded is None:
    st.info("Upload a Hudl export to generate the score-adjusted FormationIQ workbook.")
    st.stop()

try:
    raw = pd.read_csv(uploaded) if uploaded.name.lower().endswith(".csv") else pd.read_excel(uploaded)
    missing = [COLS[key] for key in ["play_no", "odk", "quarter", "down", "distance", "formation", "play_type", "gain", "result"] if COLS[key] not in raw.columns]
    if missing:
        st.error("Missing required columns: " + ", ".join(missing))
        st.stop()
    full_data = add_score_state(add_game_and_drive_ids(normalize_data(raw)))
    p_data = prepare_offense(full_data)
except Exception as exc:
    st.exception(exc)
    st.stop()

with st.sidebar:
    st.header("Game Summary")
    st.metric("Offensive Snaps", len(p_data))
    st.metric("Runs", int((p_data[COLS["play_type"]] == "RUN").sum()))
    st.metric("Passes", int((p_data[COLS["play_type"]] == "PASS").sum()))
    st.metric("Games Detected", int(full_data["Game_ID"].nunique()))
    st.metric("Avg Gain", f"{p_data[COLS['gain']].mean():.1f} yds")
    st.divider()
    st.header("Download")
    st.download_button(
        "📥 Download Score-Adjusted FormationIQ Workbook",
        data=build_excel(full_data, p_data),
        file_name="FormationIQ_Score_Adjusted.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

tabs = st.tabs(["Overview", "Formation IQ", "Down & Distance", "Situation + Score", "Motion IQ", "Score Timeline", "Pivot Lab"])

with tabs[0]:
    st.subheader("Defensive Call Sheet")
    st.dataframe(call_sheet(p_data), use_container_width=True, hide_index=True)
    st.subheader("Overall Offensive Profile")
    summary = tendency(p_data.groupby(lambda _: "Overall"))
    st.dataframe(summary, use_container_width=True, hide_index=True)

with tabs[1]:
    st.subheader("Base Formation Tendencies")
    st.dataframe(tendency(p_data.groupby("Formation")).sort_values("Plays", ascending=False), use_container_width=True, hide_index=True)

with tabs[2]:
    st.subheader("Down / Distance by Score State")
    st.dataframe(tendency(p_data.groupby(["Score State", "Situation"])).sort_values(["Score State", "Plays"], ascending=[True, False]), use_container_width=True, hide_index=True)

with tabs[3]:
        st.subheader("Down & Distance Report")
    st.caption(
        "Run/pass tendency, production, and concept detail by offensive "
        "down-and-distance situation."
    )

    dd_report = down_distance_report(p_data)

    st.dataframe(
        dd_report,
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    st.subheader("Formation Detail by Situation")

    situation_options = [
        value for value in dd_report["Situation"].astype(str).tolist()
        if value != "nan"
    ]

    selected_situation = st.selectbox(
        "Choose down-and-distance situation",
        situation_options,
        key="dd_situation",
    )

    dd_plays = p_data[p_data["Situation"] == selected_situation].copy()

    if dd_plays.empty:
        st.info("No offensive run/pass plays are available for this situation.")
    else:
        formation_detail = tendency(
            dd_plays.groupby("Formation")
        ).sort_values("Plays", ascending=False)

        st.dataframe(
            formation_detail,
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("Top Concepts")

        concept_detail = (
            dd_plays.groupby([COLS["play_type"], COLS["concept"]])
            .agg(
                Plays=(COLS["play_no"], "size"),
                Avg_Gain=(COLS["gain"], "mean"),
                First_Down_Rate=("Is_FD", "mean"),
                Success_Rate=("Is_Succ", "mean"),
                Explosives=("Explosive", "sum"),
            )
            .reset_index()
            .sort_values(["Plays", "Avg_Gain"], ascending=[False, False])
        )

        concept_detail["Avg_Gain"] = concept_detail["Avg_Gain"].round(1)
        concept_detail["First_Down_Rate"] = (
            concept_detail["First_Down_Rate"] * 100
        ).round(1)
        concept_detail["Success_Rate"] = (
            concept_detail["Success_Rate"] * 100
        ).round(1)

        st.dataframe(
            concept_detail,
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("Play-by-Play Drill Down")

        drill_columns = [
            COLS["play_no"],
            COLS["quarter"],
            COLS["down"],
            COLS["distance"],
            COLS["yard_line"],
            "Formation",
            COLS["strength"],
            "Motion",
            COLS["play_type"],
            COLS["concept"],
            COLS["play_dir"],
            COLS["gain"],
            COLS["result"],
        ]

        st.dataframe(
            dd_plays[drill_columns].sort_values(
                [COLS["quarter"], COLS["play_no"]]
            ),
            use_container_width=True,
            hide_index=True,
        )
with tabs[4]: st.subheader("Motion by Formation")
    st.dataframe(tendency(p_data.groupby(["Motion", "Formation"])).sort_values("Plays", ascending=False), use_container_width=True, hide_index=True)

with tabs[5]:
    st.subheader("Scoring Events")
    scoring = full_data[(full_data["TP Points Added"] > 0) | (full_data["Opponent Points Added"] > 0)]
    st.dataframe(scoring[["Game_ID", "Play_Order", COLS["quarter"], COLS["result"], "Scoring Team", "TP Points Added", "Opponent Points Added", "TP Score Before", "Opponent Score Before", "Score Differential Before"]], use_container_width=True, hide_index=True)
    st.subheader("Calculated Finals")
    st.dataframe(full_data.groupby("Game_ID").agg(TP_Final=("TP Points Added", "sum"), Opponent_Final=("Opponent Points Added", "sum")).reset_index(), use_container_width=True, hide_index=True)

with tabs[6]:
    st.subheader("Custom Pivot")
    available = ["Formation", "Motion", "Situation", "Score State", COLS["strength"], COLS["hash"], COLS["quarter"], COLS["concept"]]
    group = st.selectbox("Group by", available)
    metric = st.selectbox("Metric", ["Run/Pass Tendency", "Avg Gain", "Success %", "Explosive %", "Play Count"])
    if metric == "Run/Pass Tendency":
        result = tendency(p_data.groupby(group)).sort_values("Plays", ascending=False)
    elif metric == "Avg Gain":
        result = p_data.groupby(group).agg(Plays=(COLS["play_no"], "size"), Avg_Gain=(COLS["gain"], "mean")).reset_index().sort_values("Plays", ascending=False)
        result["Avg_Gain"] = result["Avg_Gain"].round(1)
    elif metric == "Success %":
        result = p_data.groupby(group).agg(Plays=(COLS["play_no"], "size"), Success_Percent=("Is_Succ", "mean")).reset_index().sort_values("Plays", ascending=False)
        result["Success_Percent"] = (result["Success_Percent"] * 100).round(1)
    elif metric == "Explosive %":
        result = p_data.groupby(group).agg(Plays=(COLS["play_no"], "size"), Explosive_Percent=("Explosive", "mean")).reset_index().sort_values("Plays", ascending=False)
        result["Explosive_Percent"] = (result["Explosive_Percent"] * 100).round(1)
    else:
        result = p_data.groupby(group).size().reset_index(name="Plays").sort_values("Plays", ascending=False)
    st.dataframe(result, use_container_width=True, hide_index=True)
