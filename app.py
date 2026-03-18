import streamlit as st
import pandas as pd
import re
import os
import numpy as np

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def classify_leverage(dn, dist):
    try:
        d, y = int(dn), int(dist)
    except (ValueError, TypeError):
        return "Unknown", 0
    if d == 1:
        if y <= 5:  return "High", 2
        elif y <= 10: return "Med", 1
        else:         return "Low", -1
    if d == 2:
        if y <= 3:  return "High", 2
        elif y <= 7:  return "Med", 1
        else:         return "Low", -1
    if d in (3, 4):
        if y <= 2:  return "High", 2
        elif y <= 6:  return "Med", 0
        else:         return "Low", -2
    return "Unknown", 0


def process_offensive_logic(formation):
    f = str(formation).upper().strip()
    match = re.match(r'^(\d)(\d)', f)
    if match:
        return f"{match.group(1)}{match.group(2)}"
    if any(x in f for x in ["HEAVY", "JUMBO", "BIG"]):  return "23"
    if "EMPTY" in f:                                      return "00"
    if "DOUBLE Y DOUBLE WING" in f:                      return "13"
    if "TREY" in f:                                       return "12"
    if "DUBS" in f or "TRIPS" in f:                      return "10"
    if "SPREAD" in f or "WING" in f:                     return "11"
    return "11"


def get_stars(pct):
    if pct >= 85: return "⭐⭐⭐⭐⭐"
    if pct >= 75: return "⭐⭐⭐⭐"
    if pct >= 65: return "⭐⭐⭐"
    if pct >= 50: return "⭐⭐"
    return "⭐"


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
    st.caption("FormationIQ v3.0 — Drive Leverage Edition")

st.title("🏈 FormationIQ — Offensive Analytics")
uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

# Sample data download for demos
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
# MAIN APP — runs only when file is uploaded
# ============================================================

if uploaded_file:
    df = pd.read_csv(uploaded_file)
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

        # ── CLEAN ──────────────────────────────────────────
        df[cols['type']]  = df[cols['type']].astype(str).str.upper().str.strip()
        df[cols['gain']]  = pd.to_numeric(df[cols['gain']],  errors='coerce').fillna(0).round(0).astype(int)
        df[cols['dn']]    = pd.to_numeric(df[cols['dn']],    errors='coerce').fillna(0).astype(int)
        df[cols['dist']]  = pd.to_numeric(df[cols['dist']],  errors='coerce').fillna(0).astype(int)
        df[cols['field']] = pd.to_numeric(df[cols['field']], errors='coerce').fillna(0).astype(int)
        df['Drive_ID']    = (df[cols['odk']] != df[cols['odk']].shift()).cumsum()

        # ── BUILD p_data ────────────────────────────────────
        p_data = df[df[cols['type']].isin(['RUN', 'PASS'])].copy()
        p_data['PERSONNEL'] = p_data[cols['form']].apply(process_offensive_logic)

        p_data['Is_FD']  = (p_data[cols['gain']] >= p_data[cols['dist']]).astype(int)
        p_data['Is_Int'] = p_data[cols['result']].str.contains('Interception', case=False, na=False).astype(int)

        def calc_succ(row):
            d, dist, g = row[cols['dn']], row[cols['dist']], row[cols['gain']]
            if d == 1: return g >= (dist * 0.45)
            if d == 2: return g >= (dist * 0.65)
            return g >= dist

        p_data['Is_Succ']     = p_data.apply(calc_succ, axis=1).astype(int)
        p_data['Is_Explosive'] = (p_data[cols['gain']] >= 15).astype(int)

        # ── DLA FIELDS ──────────────────────────────────────
        leva = p_data.apply(
            lambda r: classify_leverage(r[cols['dn']], r[cols['dist']]), axis=1
        )
        p_data['Leverage_Band']  = leva.apply(lambda x: x[0])
        p_data['Leverage_Score'] = leva.apply(lambda x: x[1])

        # Merge Drive_ID into p_data
        if 'Drive_ID' in df.columns and 'Drive_ID' not in p_data.columns:
            p_data = p_data.merge(df[['PLAY #', 'Drive_ID']], on='PLAY #', how='left')

        # ── DLA AGGREGATIONS ────────────────────────────────

        # Per-drive
        drive_view = p_data.dropna(subset=['Drive_ID']).copy()
        drive_dla = (
            drive_view.groupby('Drive_ID')
            .agg(
                Plays        = ('Leverage_Score', 'count'),
                Avg_Leverage = ('Leverage_Score', 'mean'),
                High_Lev_Pct = ('Leverage_Score', lambda x: round((x >= 2).mean() * 100)),
                Low_Lev_Pct  = ('Leverage_Score', lambda x: round((x <= -1).mean() * 100)),
                FD_Rate      = ('Is_FD',          lambda x: round(x.mean() * 100)),
                Success_Rate = ('Is_Succ',        lambda x: round(x.mean() * 100)),
                Explosive_Rt = ('Is_Explosive',   lambda x: round(x.mean() * 100)),
            )
        )
        drive_dla['Avg_Leverage'] = drive_dla['Avg_Leverage'].round(2)

        # Per-personnel
        pers_dla = (
            p_data.groupby('PERSONNEL')
            .agg(
                Plays        = ('Leverage_Score', 'count'),
                Avg_Leverage = ('Leverage_Score', 'mean'),
                High_Lev_Pct = ('Leverage_Score', lambda x: round((x >= 2).mean() * 100)),
                Low_Lev_Pct  = ('Leverage_Score', lambda x: round((x <= -1).mean() * 100)),
                FD_Rate      = ('Is_FD',          lambda x: round(x.mean() * 100)),
                Success_Rate = ('Is_Succ',        lambda x: round(x.mean() * 100)),
                Explosive_Rt = ('Is_Explosive',   lambda x: round(x.mean() * 100)),
                Run_Pct      = (cols['type'],     lambda x: round((x == 'RUN').mean() * 100)),
                Pass_Pct     = (cols['type'],     lambda x: round((x == 'PASS').mean() * 100)),
            )
        )
        pers_dla['Avg_Leverage'] = pers_dla['Avg_Leverage'].round(2)

        # Per-personnel + formation
        pf_dla = (
            p_data.groupby(['PERSONNEL', cols['form']])
            .agg(
                Plays        = ('Leverage_Score', 'count'),
                Avg_Leverage = ('Leverage_Score', 'mean'),
                High_Lev_Pct = ('Leverage_Score', lambda x: round((x >= 2).mean() * 100)),
                Low_Lev_Pct  = ('Leverage_Score', lambda x: round((x <= -1).mean() * 100)),
                FD_Rate      = ('Is_FD',          lambda x: round(x.mean() * 100)),
                Success_Rate = ('Is_Succ',        lambda x: round(x.mean() * 100)),
                Explosive_Rt = ('Is_Explosive',   lambda x: round(x.mean() * 100)),
            )
            .query('Plays >= 5')
        )
        pf_dla['Avg_Leverage'] = pf_dla['Avg_Leverage'].round(2)

        # ── SIDEBAR STATS ───────────────────────────────────
        with st.sidebar:
            st.markdown("### 📊 Game Summary")
            st.metric("Total Plays", len(p_data))
            st.metric("Run Plays",  len(p_data[p_data[cols['type']] == 'RUN']))
            st.metric("Pass Plays", len(p_data[p_data[cols['type']] == 'PASS']))
            st.metric("Avg Gain",   f"{p_data[cols['gain']].mean():.1f} yds")
            st.metric("FD Rate",    f"{round(p_data['Is_FD'].mean()*100)}%")

        # ── TABS ────────────────────────────────────────────
        tabs = st.tabs([
            "📊 Personnel Identity",
            "🎯 3rd Down Efficiency",
            "📈 Chain Moving",
            "🟢 Red/Green Zone",
            "🔮 Winning Probability",
            "🧪 Pivot Lab",
            "🏈 Kicking Game",
            "📐 Drive Leverage (DLA)",
        ])

        #
