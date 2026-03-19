import streamlit as st
import pandas as pd
import re
import os
import numpy as np
from io import BytesIO

# ============================================================
# EXCEL EXPORT
# ============================================================

def build_excel_export(export_dict):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in export_dict.items():
            if df is not None and not df.empty:
                df.reset_index().to_excel(
                    writer,
                    sheet_name=sheet_name[:31],
                    index=False
                )
    return output.getvalue()


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def classify_leverage(dn, dist, yard_ln=None):
    try:
        d, y = int(dn), int(dist)
    except (ValueError, TypeError):
        return "Unknown", 0
    if d == 1:
        if y <= 5:    base = 2
        elif y <= 10: base = 1
        else:         base = -1
    elif d == 2:
        if y <= 3:    base = 2
        elif y <= 7:  base = 1
        else:         base = -1
    elif d in (3, 4):
        if y <= 2:    base = 2
        elif y <= 6:  base = 0
        else:         base = -2
    else:
        return "Unknown", 0
    modifier = 0.0
    if yard_ln is not None:
        try:
            yl = int(yard_ln)
            if 1 <= yl <= 20:  modifier = +0.5
            elif yl <= -30:    modifier = -0.5
        except (ValueError, TypeError):
            pass
    score = base + modifier
    if score >= 1.5:    band = "High"
    elif score >= 0.5:  band = "Med"
    elif score >= -0.5: band = "Neutral"
    else:               band = "Low"
    return band, round(score, 1)


def process_offensive_logic(formation):
    f = str(formation).upper().strip()
    match = re.match(r'^(\d)(\d)', f)
    if match:
        return f"{match.group(1)}{match.group(2)}"
    if any(x in f for x in ["HEAVY", "JUMBO", "BIG"]): return "23"
    if "EMPTY" in f:                                     return "00"
    if "DOUBLE Y DOUBLE WING" in f:                      return "13"
    if "TREY" in f:                                      return "12"
    if "DUBS" in f or "TRIPS" in f:                      return "10"
    if "SPREAD" in f or "WING" in f:                     return "11"
    return "11"


def get_stars(pct):
    if pct >= 85: return "⭐⭐⭐⭐⭐"
    if pct >= 75: return "⭐⭐⭐⭐"
    if pct >= 65: return "⭐⭐⭐"
    if pct >= 50: return "⭐⭐"
    return "⭐"


def dls_grade(x):
    if x >= 1.5:  return "A"
    if x >= 0.8:  return "B"
    if x >= 0.2:  return "C"
    if x >= -0.5: return "D"
    return "F"


EXPECTED_GAIN = {
    (1,'1-5'):3.5,(1,'6-10'):4.2,(1,'11+'):3.0,
    (2,'1-3'):3.0,(2,'4-7'):4.5,(2,'8+'):5.5,
    (3,'1-2'):2.5,(3,'3-6'):5.0,(3,'7+'):7.0,
    (4,'1-2'):2.0,(4,'3+'):5.0,
}

def dist_bucket(dn, dist):
    d, y = int(dn), int(dist)
    if d == 1:
        if y <= 5: return (1,'1-5')
        elif y <= 10: return (1,'6-10')
        else: return (1,'11+')
    elif d == 2:
        if y <= 3: return (2,'1-3')
        elif y <= 7: return (2,'4-7')
        else: return (2,'8+')
    elif d == 3:
        if y <= 2: return (3,'1-2')
        elif y <= 6: return (3,'3-6')
        else: return (3,'7+')
    elif d == 4:
        if y <= 2: return (4,'1-2')
        else: return (4,'3+')
    return None


def build_sss(p_data, cols):
    df_s = p_data.copy().reset_index(drop=True)
    stress = df_s[(df_s[cols['dn']] == 3) & (df_s[cols['dist']] >= 5)]
    causes = []
    for idx in stress.index:
        if idx > 0:
            prev = df_s.loc[idx - 1]
            causes.append({
                'Stress_Situation': f"3rd & {df_s.loc[idx, cols['dist']]}",
                'Caused_By_Play':   prev[cols['play']],
                'Caused_By_Type':   prev[cols['type']],
                'Caused_By_Form':   prev[cols['form']],
                'Prior_Gain':       prev[cols['gain']],
                'Prior_Result':     prev[cols['result']],
            })
    sss_df = pd.DataFrame(causes)
    if not sss_df.empty:
        sss_summary = (
            sss_df.groupby('Caused_By_Type')
            .agg(Stress_Plays=('Caused_By_Type','count'), Avg_Prior_Gain=('Prior_Gain','mean'))
            .round(1)
        )
        sss_summary['Stress %'] = (
            sss_summary['Stress_Plays'] / sss_summary['Stress_Plays'].sum() * 100
        ).round(0).astype(int)
        sss_by_form = (
            sss_df.groupby('Caused_By_Form')
            .agg(Stress_Count=('Caused_By_Form','count'))
            .sort_values('Stress_Count', ascending=False).head(8)
        )
    else:
        sss_summary = pd.DataFrame()
        sss_by_form = pd.DataFrame()
    return sss_df, sss_summary, sss_by_form


def build_fei(p_data, cols):
    df_f = p_data.copy()
    df_f['Dist_Bucket']   = df_f.apply(lambda r: dist_bucket(r[cols['dn']], r[cols['dist']]), axis=1)
    df_f['Expected_Gain'] = df_f['Dist_Bucket'].map(EXPECTED_GAIN).fillna(4.0)
    fei_df = (
        df_f.groupby([cols['form'], cols['type']])
        .agg(Plays=(cols['gain'],'count'), Avg_Gain=(cols['gain'],'mean'), Avg_Expected=('Expected_Gain','mean'))
        .round(2)
    )
    fei_df = fei_df[fei_df['Plays'] >= 4]
    fei_df['FEI'] = (fei_df['Avg_Gain'] / fei_df['Avg_Expected']).round(2)
    fei_df['FEI_Grade'] = fei_df['FEI'].apply(
        lambda x: 'A' if x >= 1.4 else ('B' if x >= 1.1 else ('C' if x >= 0.9 else ('D' if x >= 0.7 else 'F')))
    )
    return fei_df.sort_values('FEI', ascending=False)


def build_fpar(p_data, cols):
    df_p = p_data.copy()
    def field_zone(yl):
        y = int(yl)
        if y <= -30:  return "Backed Up (own 30-)"
        elif y <= 0:  return "Own Territory (30-50)"
        elif y <= 20: return "Opp Territory (50-opp30)"
        else:         return "Scoring Zone (opp 20+)"
    df_p['Field_Zone'] = df_p[cols['field']].apply(field_zone)
    df_p['Is_Pass']    = (df_p[cols['type']] == 'PASS').astype(int)
    fpar_df = (
        df_p.groupby(['Field_Zone', cols['dn']])
        .agg(Plays=('Is_Pass','count'), Pass_Rate=('Is_Pass','mean'),
             Avg_Gain=(cols['gain'],'mean'), Success_Rate=('Is_Succ','mean'), FD_Rate=('Is_FD','mean'))
        .round(3)
    )
    fpar_df['Pass_Rate']    = (fpar_df['Pass_Rate']    * 100).round(0).astype(int)
    fpar_df['Success_Rate'] = (fpar_df['Success_Rate'] * 100).round(0).astype(int)
    fpar_df['FD_Rate']      = (fpar_df['FD_Rate']      * 100).round(0).astype(int)
    fpar_df['Avg_Gain']     = fpar_df['Avg_Gain'].round(1)
    zone_order = {
        "Backed Up (own 30-)":1,"Own Territory (30-50)":2,
        "Opp Territory (50-opp30)":3,"Scoring Zone (opp 20+)":4
    }
    fpar_df['Zone_Order'] = fpar_df.index.get_level_values('Field_Zone').map(zone_order)
    return fpar_df.sort_values(['Zone_Order', cols['dn']]).drop(columns='Zone_Order')


def build_intel(p_data, df, cols):
    intel = []
    total = len(p_data)

    # 1. Post-sack tendency
    if cols['result'] in df.columns:
        sack_mask = (
            df[cols['result']].str.contains('Sack', case=False, na=False) |
            ((df[cols['type']] == 'PASS') & (df[cols['gain']] <= -4))
        )
        post_sack = df.loc[[i+1 for i in df[sack_mask].index if i+1 in df.index]]
        if not post_sack.empty:
            rate = round((post_sack[cols['type']].str.upper() == 'RUN').mean() * 100)
            intel.append({
                "Category": "Sequence",
                "Signal": "Post-Sack Play Call",
                "Stat": f"{rate}% RUN",
                "Coaching Note": "They run to get back on schedule after a sack — apply run blitz immediately after pressure" if rate >= 60 else "They keep passing after a sack — bring pressure again, they won't adjust",
            })

    # 2. 1st down pass rate
    first_downs = p_data[p_data[cols['dn']] == 1]
    if not first_downs.empty:
        fd_pass_rate = round((first_downs[cols['type']] == 'PASS').mean() * 100)
        intel.append({
            "Category": "Tendency",
            "Signal": "1st Down Pass Rate",
            "Stat": f"{fd_pass_rate}%",
            "Coaching Note": "Pass-first on early downs — show two-high shell to bait short completions, then rally" if fd_pass_rate >= 55 else "Run-first on 1st down — load the box, force them to prove they can pass",
        })

    # 3. 3rd & short conversion
    third_short = p_data[(p_data[cols['dn']] == 3) & (p_data[cols['dist']] <= 3)]
    if len(third_short) >= 3:
        conv_rate = round(third_short['Is_FD'].mean() * 100)
        intel.append({
            "Category": "Efficiency",
            "Signal": "3rd & Short Conversion (1–3 yds)",
            "Stat": f"{conv_rate}%",
            "Coaching Note": "Dangerous in short-yardage — commit extra defender at line of scrimmage" if conv_rate >= 70 else "Stoppable in short-yardage — they struggle to get the tough yards when it matters",
        })

    # 4. Motion rate and delta
    if cols['motion'] in p_data.columns:
        motion_plays = p_data[
            p_data[cols['motion']].notna() &
            (p_data[cols['motion']].astype(str).str.strip() != '')
        ]
        motion_rate = round(len(motion_plays) / total * 100) if total else 0
        if not motion_plays.empty:
            motion_succ    = round(motion_plays['Is_Succ'].mean() * 100)
            no_motion_succ = round(p_data[~p_data.index.isin(motion_plays.index)]['Is_Succ'].mean() * 100)
            delta = motion_succ - no_motion_succ
            intel.append({
                "Category": "Scheme",
                "Signal": "Pre-Snap Motion Rate",
                "Stat": f"{motion_rate}% of plays",
                "Coaching Note": f"Motion adds +{delta}% success — disrupt at the snap, don't let them get free releases" if delta >= 5 else f"Motion not meaningfully helping (Δ{delta}%) — don't overreact to motion keys",
            })

    # 5. Explosive dependency
    exp_rate    = round(p_data['Is_Explosive'].mean() * 100)
    non_exp_avg = round(p_data[p_data['Is_Explosive'] == 0][cols['gain']].mean(), 1)
    intel.append({
        "Category": "Identity",
        "Signal": "Explosive Play Dependency",
        "Stat": f"{exp_rate}% of plays ≥15 yds",
        "Coaching Note": f"Big-play dependent — eliminate explosives and their non-explosive avg drops to {non_exp_avg} yds/play" if exp_rate >= 12 else f"Not big-play dependent — they grind consistently ({non_exp_avg} yds/play without explosives)",
    })

    # 6. Red/green zone pass rate
    rz = p_data[p_data[cols['field']].between(1, 20)]
    if len(rz) >= 4:
        rz_pass_rate = round((rz[cols['type']] == 'PASS').mean() * 100)
        rz_succ      = round(rz['Is_Succ'].mean() * 100)
        intel.append({
            "Category": "Red Zone",
            "Signal": "Scoring Zone Pass Rate (inside 20)",
            "Stat": f"{rz_pass_rate}% PASS | {rz_succ}% success",
            "Coaching Note": "Pass-heavy in scoring position — play press man, disrupt route timing" if rz_pass_rate >= 55 else "Run-heavy in scoring position — stack the box, force them to throw it in",
        })

    # 7. 1st down plays creating 2nd & long
    if not first_downs.empty:
        created_2nd_long = round((first_downs[cols['gain']] <= 2).mean() * 100)
        intel.append({
            "Category": "Self-Scout",
            "Signal": "1st Downs Ending in ≤2 Yd Gain",
            "Stat": f"{created_2nd_long}%",
            "Coaching Note": "They frequently strand themselves — win 1st down and the drive often stalls on its own" if created_2nd_long >= 35 else "Efficient on 1st down — don't give them easy early-down gains",
        })

    # 8. Interception rate
    pass_plays = len(p_data[p_data[cols['type']] == 'PASS'])
    if pass_plays >= 5:
        int_per_pass = round(p_data['Is_Int'].sum() / pass_plays * 100, 1)
        intel.append({
            "Category": "Turnover",
            "Signal": "Interception Rate (per pass attempt)",
            "Stat": f"{int_per_pass}%",
            "Coaching Note": "Turnover-prone passer — force obvious passing situations and play the sticks" if int_per_pass >= 5 else "Ball-secure passer — don't gamble on picks, play assignment defense",
        })

    return pd.DataFrame(intel) if intel else pd.DataFrame()


# ============================================================
# SCOUT REPORT GENERATOR
# ============================================================

def generate_scout_report(p_data, drive_dla, pers_dla, fei_df,
                           fpar_df, sss_summary, sss_by_form,
                           chain, cols):
    lines = []
    total    = len(p_data)
    runs     = (p_data[cols['type']] == 'RUN').sum()
    passes   = (p_data[cols['type']] == 'PASS').sum()
    run_pct  = round(runs / total * 100) if total else 0
    pass_pct = round(passes / total * 100) if total else 0
    avg_gain = round(p_data[cols['gain']].mean(), 1)
    fd_rate  = round(p_data['Is_FD'].mean() * 100)
    succ_rt  = round(p_data['Is_Succ'].mean() * 100)
    exp_rt   = round(p_data['Is_Explosive'].mean() * 100)
    avg_dls  = round(drive_dla['DLS'].mean(), 2) if not drive_dla.empty else 0
    dls_g    = dls_grade(avg_dls)

    if run_pct >= 60:
        identity = f"a **run-heavy offense** ({run_pct}% run rate)"
    elif pass_pct >= 60:
        identity = f"a **pass-heavy offense** ({pass_pct}% pass rate)"
    else:
        identity = f"a **balanced offense** ({run_pct}% run / {pass_pct}% pass)"

    lines.append(("🏈 Offensive Identity", f"""
This opponent runs {identity} averaging **{avg_gain} yards per play**.
Their overall **First Down Rate is {fd_rate}%** and **Success Rate is {succ_rt}%**,
meaning they {'consistently stay ahead of the chains' if succ_rt >= 55 else 'frequently fall behind the chains and rely on conversions'}.
Explosive plays (15+ yards) account for **{exp_rt}%** of their offense —
{'a dangerous big-play threat that can score from anywhere on the field.' if exp_rt >= 15 else "not a significant big-play threat, so bend-don't-break schemes can be effective."}
"""))

    if not drive_dla.empty:
        best_drive  = drive_dla['DLS'].max()
        worst_drive = drive_dla['DLS'].min()
        pct_a_b = round((drive_dla['DLS_Grade'].isin(['A','B'])).mean() * 100)
        pct_d_f = round((drive_dla['DLS_Grade'].isin(['D','F'])).mean() * 100)
        lines.append(("📐 Drive Control (DLS)", f"""
Their average **Drive Leverage Score is {avg_dls} (Grade: {dls_g})**.
**{pct_a_b}% of drives** graded A or B — they maintained favorable situations.
**{pct_d_f}% of drives** graded D or F — constant stress, behind the chains.
Best single-drive DLS: **{best_drive}** | Worst: **{worst_drive}**.

{'⚠️ **Exploit:** Force early negative plays. This offense struggles when taken out of rhythm — their low-leverage drives collapse quickly.' if avg_dls < 0.8 else '⚠️ **Caution:** This offense controls drives well. Stopping them requires consistent TFLs on first down.'}
"""))

    if not pers_dla.empty:
        top_pers       = pers_dla.sort_values('Plays', ascending=False)
        primary        = top_pers.index[0] if len(top_pers) > 0 else "N/A"
        primary_pct    = round(int(top_pers.iloc[0]['Plays']) / total * 100) if total else 0
        primary_dls    = top_pers.iloc[0]['DLS']
        primary_run    = top_pers.iloc[0]['Run%']
        primary_pass   = top_pers.iloc[0]['Pass%']
        qual           = pers_dla[pers_dla['Plays'] >= 5]
        worst_pers_row = qual.sort_values('DLS').iloc[0] if len(qual) > 0 else None
        best_pers_row  = qual.sort_values('DLS', ascending=False).iloc[0] if len(qual) > 0 else None
        worst_note = f"Their **{worst_pers_row.name} personnel** has the lowest DLS ({worst_pers_row['DLS']}) — when they align here, stress situations follow." if worst_pers_row is not None else ""
        best_note  = f"Their **{best_pers_row.name} personnel** is their most controlled grouping (DLS: {best_pers_row['DLS']}) — expect this on critical downs." if best_pers_row is not None else ""
        lines.append(("👥 Personnel Tendencies", f"""
Primary group: **{primary}** ({primary_pct}% of plays, {primary_run}% run / {primary_pass}% pass, DLS: {primary_dls}).

{best_note}

{worst_note}

⚠️ **Exploit:** When their low-DLS personnel aligns, they are already in a self-created stress situation — apply pressure, don't give up the conversion.
"""))

    if not fei_df.empty:
        top_fei = fei_df[fei_df['FEI_Grade'].isin(['A','B'])].head(3)
        bot_fei = fei_df[fei_df['FEI_Grade'].isin(['D','F'])].tail(3)
        top_text = "\n".join([f"- **{idx[0]} ({idx[1]})** — FEI: {row['FEI']} ({row['FEI_Grade']}), Avg Gain: {row['Avg_Gain']}" for idx, row in top_fei.iterrows()]) if not top_fei.empty else "- None detected."
        bot_text = "\n".join([f"- **{idx[0]} ({idx[1]})** — FEI: {row['FEI']} ({row['FEI_Grade']}), Avg Gain: {row['Avg_Gain']}" for idx, row in bot_fei.iterrows()]) if not bot_fei.empty else "- None detected."
        lines.append(("📊 Formation Efficiency (FEI)", f"""
**Danger formations (outperforming their situation):**
{top_text}

**Exploitable formations (underperforming their situation):**
{bot_text}

⚠️ **Exploit:** When they align in their low-FEI formations, the data says they do not execute — even when down/distance appears manageable.
"""))

    if not sss_summary.empty:
        top_cause  = sss_summary.sort_values('Stress %', ascending=False).iloc[0]
        cause_type = top_cause.name
        cause_pct  = int(top_cause['Stress %'])
        cause_gain = round(top_cause['Avg_Prior_Gain'], 1)
        form_note  = ""
        if not sss_by_form.empty:
            tsf = sss_by_form.index[0]
            tsc = int(sss_by_form.iloc[0]['Stress_Count'])
            form_note = f"Formation most responsible: **{tsf}** ({tsc} stress situations generated)."
        lines.append(("🔥 Stress Pattern Analysis (SSS)", f"""
**{cause_pct}% of their 3rd & long situations are created by {cause_type} plays**,
averaging only **{cause_gain} yards** on the prior snap.

{form_note}

⚠️ **Exploit:** Stop their {cause_type.lower()} game on early downs. Hold them below {cause_gain + 1} yards on 1st and 2nd down consistently and you force exactly the stress situations they struggle in. This is the highest-leverage defensive adjustment available.
"""))

    if not fpar_df.empty:
        fpar_reset  = fpar_df.reset_index()
        bu_1st      = fpar_reset[(fpar_reset['Field_Zone'] == 'Backed Up (own 30-)') & (fpar_reset[cols['dn']] == 1)]
        sc_1st      = fpar_reset[(fpar_reset['Field_Zone'] == 'Scoring Zone (opp 20+)') & (fpar_reset[cols['dn']] == 1)]
        backed_note = ""
        if not bu_1st.empty:
            bu_pass = int(bu_1st.iloc[0]['Pass_Rate'])
            bu_succ = int(bu_1st.iloc[0]['Success_Rate'])
            backed_note = f"When **backed up on their own 30 or deeper**, they pass **{bu_pass}%** on 1st down ({bu_succ}% success) — {'predictable and stoppable' if bu_pass >= 55 else 'they run it safe — limit your risk in this zone too'}."
        scoring_note = ""
        if not sc_1st.empty:
            sc_pass = int(sc_1st.iloc[0]['Pass_Rate'])
            sc_succ = int(sc_1st.iloc[0]['Success_Rate'])
            scoring_note = f"Inside your **scoring zone**, they pass **{sc_pass}%** on 1st down ({sc_succ}% success) — {'get physical at the line, disrupt route timing' if sc_pass >= 55 else 'stack the box, they want to run it in from here'}."
        lines.append(("🗺️ Field Position Tendencies", f"""
{backed_note}

{scoring_note}

⚠️ **Exploit:** Zone-by-zone tendencies let you call the right front BEFORE the snap.
"""))

    if not chain.empty:
        top_plays_text = "\n".join([f"- **{play}** — {row['Plays']} plays, {row['FD Rate %']}% FD, {row['Success Rate %']}% success" for play, row in chain.head(5).iterrows()])
        bot_plays_text = "\n".join([f"- **{play}** — {row['Plays']} plays, {row['FD Rate %']}% FD" for play, row in chain.sort_values('FD Rate %').head(3).iterrows()])
        lines.append(("📈 Chain-Moving Plays to Stop", f"""
**Most dangerous chain-movers:**
{top_plays_text}

**Frequent calls with low conversion (let them run these):**
{bot_plays_text}

⚠️ **Exploit:** When you take away their top chain-movers they fall back on low-conversion habits. Take away the top plays, invite the bad ones, capitalize on the punt.
"""))

    verdict_score = 0

    if fd_rate >= 43:   verdict_score += 1
    if fd_rate >= 50:   verdict_score += 1
    if succ_rt >= 45:   verdict_score += 1
    if succ_rt >= 52:   verdict_score += 1
    if exp_rt >= 10:    verdict_score += 1
    if exp_rt >= 18:    verdict_score += 1
    if avg_dls >= 0.6:  verdict_score += 1
    if avg_dls >= 1.0:  verdict_score += 1
    if avg_gain >= 5.0: verdict_score += 1
    if avg_gain >= 6.5: verdict_score += 1

    if verdict_score >= 7:
        verdict = "🔴 **High-Threat Offense.** This team is executing well across multiple dimensions. No single silver bullet — must stop them consistently on every snap."
    elif verdict_score >= 4:
        verdict = "🟡 **Moderate-Threat Offense.** Real weapons but exploitable weaknesses. Attack their stress patterns and low-FEI formations early."
    else:
        verdict = "🟢 **Manageable Offense.** Struggles to stay on schedule. Force early-down stops, play assignment football, and let their tendencies beat them."

    lines.append(("🎯 Overall Scouting Verdict", verdict))
    return lines


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(page_title="FormationIQ", page_icon="🏈", layout="wide")

with st.sidebar:
    logo_files = ["Logo.png", "logo.png"]
    found_logo = False
    for lf in logo_files:
        if os.path.exists(lf):
            st.image(lf, width=150)
            found_logo = True
            break
    if not found_logo:
        st.subheader("🏈 CARLSBAD FOOTBALL")
    st.write("---")
    st.caption("FormationIQ v9.0 — Final Build")

st.title("🏈 FormationIQ — Offensive Scouting Analytics")
uploaded_file = st.file_uploader("Upload Hudl file (CSV or Excel)", type=["csv", "xlsx"])

with st.expander("📂 No file? Download sample data"):
    sample_csv = """PLAY #,ODK,DN,DIST,YARD LN,HASH,OFF FORM,OFF STR,OFF PLAY,PLAY TYPE,GN/LS,RESULT,BACKFIELD,EFF,TARGET,MOTION DIR,PLAY DIR
1,O,1,10,35,M,20 Wing,R,QUICK PASS,PASS,7,Complete,,Y,,,R
2,O,2,3,28,R,20 Wing,L,ZONE,RUN,4,Rush,,Y,,,L
3,O,1,10,24,L,DUBS,BAL,DROP BACK PASS,PASS,0,Incomplete,,N,,,R
4,O,2,10,24,L,DUBS,BAL,QB BLAST,RUN,12,Rush,,Y,,,L
5,O,1,10,12,R,11 spread,R,PLAY ACTION PASS,PASS,12,Complete,,Y,,,R
6,O,1,10,38,M,20 Wing,L,WIDE ZONE,RUN,34,Rush,,Y,,,R
7,O,3,5,20,R,DUBS,BAL,QUICK PASS,PASS,0,Incomplete,,N,,,L
8,O,3,5,20,R,20 Wing,L,COUNTER H,RUN,8,Rush,,Y,,,R
9,O,1,10,8,L,20 Wing,R,DIVE,RUN,8,Rush TD,,Y,,,L
10,O,1,10,-22,R,10 trips,R,BUBBLE,PASS,50,Complete TD,,Y,,,R
11,O,2,7,-36,R,11 spread wing,R,LONG TRAP,RUN,1,Rush,,N,,,L
12,O,3,6,-37,M,20 Wing,L,DROP BACK PASS,PASS,0,Incomplete,,N,,,R"""
    st.download_button(
        label="⬇️ Download Sample CSV",
        data=sample_csv,
        file_name="sample_hudl_data.csv",
        mime="text/csv"
    )

# ============================================================
# MAIN APP
# ============================================================

if uploaded_file:
    if uploaded_file.name.lower().endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    df.columns = [str(c).strip() for c in df.columns]

    cols = {
        'type':   'PLAY TYPE',
        'form':   'OFF FORM',
        'gain':   'GN/LS',
        'dn':     'DN',
        'dist':   'DIST',
        'play':   'OFF PLAY',
        'field':  'YARD LN',
        'odk':    'ODK',
        'hash':   'HASH',
        'p_dir':  'PLAY DIR',
        'motion': 'MOTION DIR',
        'result': 'RESULT',
    }

    if all(cols[k] in df.columns for k in ['type', 'form', 'gain']):

        df[cols['type']]  = df[cols['type']].astype(str).str.upper().str.strip()
        df[cols['gain']]  = pd.to_numeric(df[cols['gain']],  errors='coerce').fillna(0).round(0).astype(int)
        df[cols['dn']]    = pd.to_numeric(df[cols['dn']],    errors='coerce').fillna(0).astype(int)
        df[cols['dist']]  = pd.to_numeric(df[cols['dist']],  errors='coerce').fillna(0).astype(int)
        df[cols['field']] = pd.to_numeric(df[cols['field']], errors='coerce').fillna(0).astype(int)
        df['Drive_ID']    = (df[cols['odk']] != df[cols['odk']].shift()).cumsum()

        p_data = df[df[cols['type']].isin(['RUN', 'PASS'])].copy()
        p_data['PERSONNEL'] = p_data[cols['form']].apply(process_offensive_logic)
        p_data['Is_FD']     = (p_data[cols['gain']] >= p_data[cols['dist']]).astype(int)
        p_data['Is_Int']    = p_data[cols['result']].str.contains('Interception', case=False, na=False).astype(int)

        def calc_succ(row):
            d, dist, g = row[cols['dn']], row[cols['dist']], row[cols['gain']]
            if d == 1: return g >= (dist * 0.45)
            if d == 2: return g >= (dist * 0.65)
            return g >= dist

        p_data['Is_Succ']      = p_data.apply(calc_succ, axis=1).astype(int)
        p_data['Is_Explosive'] = (p_data[cols['gain']] >= 15).astype(int)

        leva = p_data.apply(
            lambda r: classify_leverage(r[cols['dn']], r[cols['dist']], r[cols['field']]), axis=1
        )
        p_data['Leverage_Band']  = leva.apply(lambda x: x[0])
        p_data['Leverage_Score'] = leva.apply(lambda x: x[1])

        if 'Drive_ID' in df.columns and 'Drive_ID' not in p_data.columns:
            p_data = p_data.merge(df[['PLAY #', 'Drive_ID']], on='PLAY #', how='left')

        drive_view = p_data.dropna(subset=['Drive_ID']).copy()

        drive_dla = drive_view.groupby('Drive_ID').agg(
            Plays=('Leverage_Score','count'), DLS=('Leverage_Score','mean'),
            FD_Rate=('Is_FD','mean'), Success_Rate=('Is_Succ','mean'), Explosive_Rt=('Is_Explosive','mean'),
        ).round(2)
        drive_dla['High_Lev%']    = drive_view.groupby('Drive_ID')['Leverage_Score'].apply(lambda x: round((x >= 1.5).mean() * 100))
        drive_dla['Low_Lev%']     = drive_view.groupby('Drive_ID')['Leverage_Score'].apply(lambda x: round((x <= -1).mean() * 100))
        drive_dla['FD_Rate']      = (drive_dla['FD_Rate'] * 100).round(0).astype(int)
        drive_dla['Success_Rate'] = (drive_dla['Success_Rate'] * 100).round(0).astype(int)
        drive_dla['Explosive_Rt'] = (drive_dla['Explosive_Rt'] * 100).round(0).astype(int)
        drive_dla['DLS_Grade']    = drive_dla['DLS'].apply(dls_grade)

        pers_dla = p_data.groupby('PERSONNEL').agg(
            Plays=('Leverage_Score','count'), DLS=('Leverage_Score','mean'),
            Avg_Gain=(cols['gain'],'mean'), FD_Rate=('Is_FD','mean'),
            Success_Rate=('Is_Succ','mean'), Explosive_Rt=('Is_Explosive','mean'),
        ).round(2)
        pers_dla['High_Lev%']    = p_data.groupby('PERSONNEL')['Leverage_Score'].apply(lambda x: round((x >= 1.5).mean() * 100))
        pers_dla['Low_Lev%']     = p_data.groupby('PERSONNEL')['Leverage_Score'].apply(lambda x: round((x <= -1).mean() * 100))
        pers_dla['Run%']         = p_data.groupby('PERSONNEL')[cols['type']].apply(lambda x: round((x == 'RUN').mean() * 100))
        pers_dla['Pass%']        = p_data.groupby('PERSONNEL')[cols['type']].apply(lambda x: round((x == 'PASS').mean() * 100))
        pers_dla['FD_Rate']      = (pers_dla['FD_Rate'] * 100).round(0).astype(int)
        pers_dla['Success_Rate'] = (pers_dla['Success_Rate'] * 100).round(0).astype(int)
        pers_dla['Explosive_Rt'] = (pers_dla['Explosive_Rt'] * 100).round(0).astype(int)
        pers_dla['Avg_Gain']     = pers_dla['Avg_Gain'].round(1)
        pers_dla['DLS_Grade']    = pers_dla['DLS'].apply(dls_grade)

        pf_dla = p_data.groupby(['PERSONNEL', cols['form']]).agg(
            Plays=('Leverage_Score','count'), DLS=('Leverage_Score','mean'),
            Avg_Gain=(cols['gain'],'mean'), FD_Rate=('Is_FD','mean'),
            Success_Rate=('Is_Succ','mean'), Explosive_Rt=('Is_Explosive','mean'),
        ).round(2)
        pf_dla['High_Lev%']    = p_data.groupby(['PERSONNEL', cols['form']])['Leverage_Score'].apply(lambda x: round((x >= 1.5).mean() * 100))
        pf_dla['Low_Lev%']     = p_data.groupby(['PERSONNEL', cols['form']])['Leverage_Score'].apply(lambda x: round((x <= -1).mean() * 100))
        pf_dla['FD_Rate']      = (pf_dla['FD_Rate'] * 100).round(0).astype(int)
        pf_dla['Success_Rate'] = (pf_dla['Success_Rate'] * 100).round(0).astype(int)
        pf_dla['Explosive_Rt'] = (pf_dla['Explosive_Rt'] * 100).round(0).astype(int)
        pf_dla['Avg_Gain']     = pf_dla['Avg_Gain'].round(1)
        pf_dla['DLS_Grade']    = pf_dla['DLS'].apply(dls_grade)
        pf_dla = pf_dla[pf_dla['Plays'] >= 5]

        sss_df, sss_summary, sss_by_form = build_sss(p_data, cols)
        fei_df  = build_fei(p_data, cols)
        fpar_df = build_fpar(p_data, cols)
        intel_df = build_intel(p_data, df, cols)

        chain = p_data.groupby(cols['play'])['Is_FD'].agg(['sum','count'])
        chain.columns = ['First Downs','Plays']
        chain['FD Rate %']      = (chain['First Downs'] / chain['Plays'] * 100).round(0).astype(int)
        chain['Success Rate %'] = p_data.groupby(cols['play'])['Is_Succ'].mean().mul(100).round(0).astype(int)
        chain = chain[chain['Plays'] >= 3].sort_values('FD Rate %', ascending=False).head(15)

        pers_counts = p_data['PERSONNEL'].value_counts().to_frame("Plays")
        pers_counts['%'] = (pers_counts['Plays'] / pers_counts['Plays'].sum() * 100).round(0).astype(int)

        t3 = p_data[p_data[cols['dn']] == 3].copy()
        if not t3.empty:
            t3['Sit'] = t3[cols['dist']].apply(
                lambda x: "3rd & Short (1-3)" if x <= 3 else ("3rd & Mid (4-7)" if x <= 7 else "3rd & Long (7+)")
            )
            t3_summary = t3.groupby('Sit')['Is_FD'].mean().mul(100).round(0).astype(int).to_frame("FD Rate %")
        else:
            t3_summary = pd.DataFrame()

        scout_sections = generate_scout_report(
            p_data, drive_dla, pers_dla, fei_df,
            fpar_df, sss_summary, sss_by_form, chain, cols
        )

        export_options = {
            "Personnel Identity":         pers_counts,
            "3rd Down Summary":           t3_summary,
            "Chain Moving":               chain,
            "Drive Leverage-Per Drive":   drive_dla,
            "Drive Leverage-Personnel":   pers_dla,
            "Drive Leverage-Pers+Form":   pf_dla,
            "Sequence Stress Score":      sss_summary,
            "Stress by Formation":        sss_by_form,
            "Formation Efficiency Index": fei_df.reset_index(),
            "Field Position Aggression":  fpar_df.reset_index(),
            "AI Scouting Intelligence":   intel_df,
        }

        # ── SIDEBAR ─────────────────────────────────────────
        with st.sidebar:
            st.markdown("### 📊 Game Summary")
            st.metric("Total Plays",  len(p_data))
            st.metric("Run Plays",    len(p_data[p_data[cols['type']] == 'RUN']))
            st.metric("Pass Plays",   len(p_data[p_data[cols['type']] == 'PASS']))
            st.metric("Avg Gain",     f"{p_data[cols['gain']].mean():.1f} yds")
            st.metric("FD Rate",      f"{round(p_data['Is_FD'].mean()*100)}%")
            st.metric("Success Rate", f"{round(p_data['Is_Succ'].mean()*100)}%")
            st.write("---")
            st.subheader("⬇️ Download Full Report")
            excel_data = build_excel_export(export_options)
            st.download_button(
                label="📥 Download FormationIQ Report",
                data=excel_data,
                file_name="FormationIQ_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # ── TABS ────────────────────────────────────────────
        tabs = st.tabs([
            "📖 Definitions",
            "📊 Personnel Identity",
            "🎯 3rd Down Efficiency",
            "📈 Chain Moving",
            "🟢 Red/Green Zone",
            "🔮 Winning Probability",
            "🧪 Pivot Lab",
            "📐 Drive Leverage (DLA)",
            "🕵️ Scout Report",
        ])

        # ── TAB 0: DEFINITIONS ───────────────────────────────
        with tabs[0]:
            st.header("📖 Metric Definitions")
            st.caption("Reference guide for every metric used in FormationIQ.")

            st.subheader("📌 First Down Rate (FD Rate)")
            st.markdown("""
How often this offense picks up the first down marker — gain equals or exceeds the distance needed.

**Examples:**
- 2nd & 7 → gain of 8 yards ✅ First down counted
- 2nd & 7 → gain of 6 yards ❌ Not counted
- 3rd & 4 → gain of 4 yards ✅ First down counted

> Below **35%** = chains rarely moving. Above **50%** = very difficult to get off the field.
""")
            st.divider()

            st.subheader("📌 Success Rate")
            st.markdown("""
A more precise measure than FD Rate. A play is "successful" if it gained
enough for the situation — not just whether it converted.

| Down | Threshold | Example |
|---|---|---|
| 1st | ≥ 45% of distance | 1st & 10 → need 4.5 yds → 5 yd gain ✅ |
| 1st | ≥ 45% of distance | 1st & 10 → need 4.5 yds → 3 yd gain ❌ |
| 2nd | ≥ 65% of distance | 2nd & 8 → need 5.2 yds → 6 yd gain ✅ |
| 2nd | ≥ 65% of distance | 2nd & 8 → need 5.2 yds → 4 yd gain ❌ |
| 3rd/4th | Full conversion | 3rd & 6 → need 6 yds → 5 yd gain ❌ |

**Why it matters more than FD Rate:**
A team can have a **42% FD Rate but 38% Success Rate** — they converted
first downs but were constantly behind the chains before doing so.
Success Rate exposes that they're surviving on 3rd down luck rather than
building drives consistently.

> Above **50%** = disciplined chain-moving offense. Below **40%** = living and dying by big plays.
""")
            st.divider()

            st.subheader("📐 Drive Leverage Score (DLS)")
            st.markdown("""
Measures how much control the offense had at every snap.

| Situation | Score |
|---|---|
| 1st & ≤5, 2nd & ≤3, 3rd/4th & 1-2 | +2 (High) |
| Normal 1st & 10, 2nd & 4-7 | +1 (Med) |
| 1st/2nd behind chains | -1 (Low) |
| 3rd/4th & 7+ | -2 (Stress) |

**Field position modifier:** Red zone +0.5 | Backed up own 30 -0.5

**Grade:** A ≥ 1.5 | B ≥ 0.8 | C ≥ 0.2 | D ≥ -0.5 | F < -0.5

**Example:** A drive with plays on 1st & 10 (+1), 2nd & 3 (+2), 3rd & 1 (+2) = avg DLS of 1.67 → Grade A.
A drive with 1st & 10 (+1), incomplete pass → 2nd & 10 (-1), 3rd & 10 (-2) = avg DLS of -0.67 → Grade F.
""")
            st.divider()

            st.subheader("🔥 Sequence Stress Score (SSS)")
            st.markdown("""
Tracks how often the offense enters **3rd & 5+** situations and identifies
which prior play type or formation caused the stress.

**Example:**
- 1st & 10 → incomplete pass (0 yds) → 2nd & 10 → run for 2 yds → **3rd & 8** ← stress situation
- SSS tags the 2nd down run as the cause of the 3rd & 8
> Use this to find the **root cause** of drive breakdowns — not just the symptom.
""")
            st.divider()

            st.subheader("📐 Formation Efficiency Index (FEI)")
            st.markdown("""
Compares actual average gain to the **expected gain** for the down/distance
situation that formation was used in — removing the bias of easy situations.

**How expected gain is calculated:**
Each play is bucketed by down and distance. Each bucket has a baseline
expected gain from typical high school production:

| Down | Distance | Expected Gain |
|---|---|---|
| 1st | 1–5 yds | 3.5 yds |
| 1st | 6–10 yds | 4.2 yds |
| 1st | 11+ yds | 3.0 yds |
| 2nd | 1–3 yds | 3.0 yds |
| 2nd | 4–7 yds | 4.5 yds |
| 2nd | 8+ yds | 5.5 yds |
| 3rd | 1–2 yds | 2.5 yds |
| 3rd | 3–6 yds | 5.0 yds |
| 3rd | 7+ yds | 7.0 yds |
| 4th | 1–2 yds | 2.0 yds |
| 4th | 3+ yds | 5.0 yds |

**FEI = Actual Avg Gain ÷ Expected Avg Gain**

**Example:**
Formation used 10 times — 6 on 1st & 10 (expected 4.2) and 4 on 2nd & 4 (expected 4.5).
Weighted avg expected = 4.3 yds. Actual avg = 6.1 yds. **FEI = 6.1 ÷ 4.3 = 1.42 → Grade A.**

**Why raw yardage misleads:**
A formation averaging 5.0 yds on 1st & 5 situations (expected 3.5) = **FEI 1.43 → Elite.**
The same 5.0 yds on 3rd & 7+ (expected 7.0) = **FEI 0.71 → Failing.**
Same number. Completely different story.

**Grade:** A ≥ 1.4 | B ≥ 1.1 | C ≥ 0.9 | D ≥ 0.7 | F < 0.7
""")
            st.divider()

            st.subheader("🗺️ Field Position Aggression Rating (FPAR)")
            st.markdown("""
Pass rate, success rate, and avg gain by field zone and down.

| Zone | Description |
|---|---|
| Backed Up | Own 30 or deeper |
| Own Territory | Own 30 to midfield |
| Opp Territory | Midfield to opp 30 |
| Scoring Zone | Inside opp 20 |

**Example:** If they pass 70% on 1st down when backed up but only convert at 32%,
that is aggressive but ineffective — a defensive opportunity.
""")
            st.divider()

            st.subheader("💥 Explosive Play")
            st.markdown("Any play gaining **15 or more yards.** If an offense gains 500 yards but 200 come from 3 explosive plays, they are big-play dependent — stop those and the offense stalls.")
            st.divider()

            st.subheader("🏃 Personnel Group")
            st.markdown("""
Two-digit code: **RBs + TEs** on the field. Remaining skill players = WRs.

| Code | RBs | TEs | WRs | Common Name |
|---|---|---|---|---|
| 00 | 0 | 0 | 5 | Empty |
| 10 | 1 | 0 | 4 | Trips/Quads |
| 11 | 1 | 1 | 3 | Standard Spread |
| 12 | 1 | 2 | 2 | Pro Set |
| 13 | 1 | 3 | 1 | Double Y |
| 20 | 2 | 0 | 3 | Wing |
| 21 | 2 | 1 | 2 | Power Spread |
| 22 | 2 | 2 | 1 | Heavy/I-Form |
""")

        # ── TAB 1: PERSONNEL ────────────────────────────────
        with tabs[1]:
            st.header("📊 Personnel Identity")
            st.subheader("Overall Usage")
            st.dataframe(pers_counts, use_container_width=False)
            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("🏃 Top 5 Run Personnel")
                run_pers = (
                    p_data[p_data[cols['type']] == 'RUN']
                    .groupby('PERSONNEL')
                    .agg(Plays=('PERSONNEL','count'), Avg_Gain=(cols['gain'],'mean'))
                    .sort_values('Plays', ascending=False).head(5)
                )
                run_pers['Avg_Gain'] = run_pers['Avg_Gain'].round(1)
                run_pers['Run %'] = (run_pers['Plays'] / run_pers['Plays'].sum() * 100).round(0).astype(int)
                st.dataframe(run_pers.style.background_gradient(cmap='RdYlGn', subset=['Avg_Gain']), use_container_width=False)
            with c2:
                st.subheader("🎯 Top 5 Pass Personnel")
                pass_pers = (
                    p_data[p_data[cols['type']] == 'PASS']
                    .groupby('PERSONNEL')
                    .agg(Plays=('PERSONNEL','count'), Avg_Gain=(cols['gain'],'mean'))
                    .sort_values('Plays', ascending=False).head(5)
                )
                pass_pers['Avg_Gain'] = pass_pers['Avg_Gain'].round(1)
                pass_pers['Pass %'] = (pass_pers['Plays'] / pass_pers['Plays'].sum() * 100).round(0).astype(int)
                st.dataframe(pass_pers.style.background_gradient(cmap='RdYlGn', subset=['Avg_Gain']), use_container_width=False)
            st.divider()
            st.subheader("Run/Pass Tendency by Personnel")
            rp_split = (
                p_data.groupby('PERSONNEL')[cols['type']]
                .value_counts(normalize=True).unstack().fillna(0).mul(100).round(0).astype(int)
            )
            st.dataframe(rp_split.style.background_gradient(cmap='RdYlGn_r'), use_container_width=False)

        # ── TAB 2: 3RD DOWN ─────────────────────────────────
        with tabs[2]:
            st.header("🎯 3rd Down Efficiency")
            if not t3.empty:
                st.metric("3rd Down Conversion Rate", f"{round(t3['Is_FD'].mean()*100)}%")
                c1, c2 = st.columns(2)
                with c1:
                    st.table(t3_summary)
                with c2:
                    t3_tend = t3.groupby('Sit')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100).round(0).astype(int)
                    st.dataframe(t3_tend.style.background_gradient(cmap='RdYlGn_r').format("{:d}%"), use_container_width=False)
                for sit in ["3rd & Short (1-3)", "3rd & Mid (4-7)", "3rd & Long (7+)"]:
                    with st.expander(f"Top Calls: {sit}"):
                        st.table(t3[t3['Sit'] == sit][cols['play']].value_counts().head(3))
            else:
                st.info("No 3rd down plays found.")

        # ── TAB 3: CHAIN MOVING ──────────────────────────────
        with tabs[3]:
            st.header("📈 Chain Moving (Frequency)")
            m1, m2 = st.columns(2)
            m1.metric("Overall FD Rate",      f"{round(p_data['Is_FD'].mean()*100)}%")
            m2.metric("Overall Success Rate", f"{round(p_data['Is_Succ'].mean()*100)}%")
            st.divider()
            st.dataframe(
                chain.style.background_gradient(cmap='RdYlGn', subset=['FD Rate %','Success Rate %']),
                use_container_width=False
            )

        # ── TAB 4: RED/GREEN ZONE ────────────────────────────
        with tabs[4]:
            st.header("🟢 Red/Green Zone")
            rz = p_data[p_data[cols['field']].between(1, 10)].copy()
            gz = p_data[p_data[cols['field']].between(11, 20)].copy()
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("🔴 Red Zone (1-10)")
                if not rz.empty:
                    st.metric("TD/FD Rate", f"{round(rz['Is_FD'].mean()*100)}%")
                    st.table(rz[cols['play']].value_counts().head(5).to_frame("Plays"))
                else:
                    st.info("No red zone plays.")
            with c2:
                st.subheader("🟢 Green Zone (11-20)")
                if not gz.empty:
                    st.metric("Success Rate", f"{round(gz['Is_Succ'].mean()*100)}%")
                    st.table(gz[cols['play']].value_counts().head(5).to_frame("Plays"))
                else:
                    st.info("No green zone plays.")

        # ── TAB 5: WINNING PROBABILITY ───────────────────────
        with tabs[5]:
            st.header("🔮 Winning Probability (AI)")

            st.subheader("🤖 AI Scouting Intelligence")
            st.caption("Auto-detected behavioral patterns and tendencies from play-by-play data.")
            if not intel_df.empty:
                st.dataframe(
                    intel_df.set_index('Category'),
                    use_container_width=True,
                    column_config={
                        "Signal":        st.column_config.TextColumn("Signal",        width=200),
                        "Stat":          st.column_config.TextColumn("Stat",          width=160),
                        "Coaching Note": st.column_config.TextColumn("Coaching Note", width=500),
                    }
                )
            else:
                st.info("No intelligence signals detected yet.")

            st.divider()
            st.subheader("🔥 Sequence Stress Score (SSS)")
            st.caption("What play types and formations are creating 3rd & long situations.")
            if not sss_summary.empty:
                c1, c2 = st.columns(2)
                with c1:
                    st.write("**By Play Type**")
                    st.dataframe(sss_summary.style.background_gradient(cmap='RdYlGn_r', subset=['Stress %']), use_container_width=False)
                with c2:
                    st.write("**Top Formations Creating Stress**")
                    st.dataframe(sss_by_form.style.background_gradient(cmap='RdYlGn_r', subset=['Stress_Count']), use_container_width=False)
                with st.expander("📋 Full Stress Play Log"):
                    st.dataframe(sss_df.reset_index(drop=True), use_container_width=False)
            else:
                st.info("No 3rd & long stress situations found.")

            st.divider()
            st.subheader("📐 Formation Efficiency Index (FEI)")
            st.caption("FEI > 1.0 = outperforming situation. FEI < 1.0 = underperforming.")
            if not fei_df.empty:
                c1, c2 = st.columns(2)
                with c1:
                    st.write("**🏃 Run FEI**")
                    run_fei = fei_df.xs('RUN', level=1) if 'RUN' in fei_df.index.get_level_values(1) else pd.DataFrame()
                    if not run_fei.empty:
                        st.dataframe(run_fei.head(8).style.background_gradient(cmap='RdYlGn', subset=['FEI']), use_container_width=False)
                with c2:
                    st.write("**🎯 Pass FEI**")
                    pass_fei = fei_df.xs('PASS', level=1) if 'PASS' in fei_df.index.get_level_values(1) else pd.DataFrame()
                    if not pass_fei.empty:
                        st.dataframe(pass_fei.head(8).style.background_gradient(cmap='RdYlGn', subset=['FEI']), use_container_width=False)
            else:
                st.info("Not enough play volume for FEI (min 4 plays per formation/type).")

            st.divider()
            st.subheader("🗺️ Field Position Aggression Rating (FPAR)")
            st.caption("Pass rate, success rate, and avg gain by field zone and down.")
            if not fpar_df.empty:
                st.dataframe(fpar_df.style.background_gradient(cmap='RdYlGn', subset=['Success_Rate']), use_container_width=False)
                st.write("**1st Down Pass Rate by Zone**")
                zone_1st = fpar_df.reset_index()
                zone_1st = zone_1st[zone_1st[cols['dn']] == 1][['Field_Zone','Pass_Rate','Success_Rate','Avg_Gain']]
                if not zone_1st.empty:
                    st.dataframe(zone_1st.set_index('Field_Zone').style.background_gradient(cmap='RdYlGn', subset=['Success_Rate']), use_container_width=False)
            else:
                st.info("Not enough data for field position analysis.")

        # ── TAB 6: PIVOT LAB ─────────────────────────────────
        with tabs[6]:
            st.header("🧪 Custom Pivot Lab")
            pivot_cols = [c for c in [cols['dn'], cols['form'], cols['play'], cols['type'], 'PERSONNEL', cols['result']] if c in p_data.columns]
            selected = st.multiselect("Select columns:", options=p_data.columns.tolist(), default=pivot_cols)
            play_filter = st.selectbox("Filter by Play Type:", ["ALL", "RUN", "PASS"])
            view = p_data.copy()
            if play_filter != "ALL":
                view = view[view[cols['type']] == play_filter]
            if selected:
                st.dataframe(view[selected].reset_index(drop=True), use_container_width=True)

        # ── TAB 7: DRIVE LEVERAGE ────────────────────────────
        with tabs[7]:
            st.header("📐 Drive Leverage Score (DLS)")
            st.subheader("Per-Drive Summary")
            st.dataframe(drive_dla.style.background_gradient(cmap='RdYlGn', subset=['DLS']), use_container_width=False)
            st.divider()
            st.subheader("Personnel Leverage Profile")
            st.dataframe(pers_dla.sort_values('DLS', ascending=False).style.background_gradient(cmap='RdYlGn', subset=['DLS']), use_container_width=False)
            st.divider()
            with st.expander("📋 Personnel + Formation Leverage (min 5 plays)"):
                st.dataframe(pf_dla.sort_values('DLS', ascending=False).style.background_gradient(cmap='RdYlGn', subset=['DLS']), use_container_width=False)

        # ── TAB 8: SCOUT REPORT ──────────────────────────────
        with tabs[8]:
            st.header("🕵️ Opponent Scout Report")
    
    # TEMP DEBUG — remove after fixing
    st.write({
        "fd_rate": round(p_data['Is_FD'].mean()*100),
        "succ_rt": round(p_data['Is_Succ'].mean()*100),
        "exp_rt":  round(p_data['Is_Explosive'].mean()*100),
        "avg_dls": round(drive_dla['DLS'].mean(), 2) if not drive_dla.empty else 0,
        "avg_gain": round(p_data[cols['gain']].mean(), 1),
    })
    # END TEMP DEBUG
    
    st.caption("Auto-generated executive overview...")

    else:
        st.error(f"Missing required columns: {list(cols.values())}")
