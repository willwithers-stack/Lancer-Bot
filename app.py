import streamlit as st
import pandas as pd
import re
import os

# --- 1. CORE LOGIC ---
def process_offensive_logic(formation):
    f = str(formation).upper().strip()
    match = re.match(r'^(\d)(\d)', f)
    if match:
        pers = f"{match.group(1)}{match.group(2)}"
    else:
        if any(x in f for x in ["HEAVY", "JUMBO", "BIG"]): pers = "23"
        elif "EMPTY" in f: pers = "00"
        elif "DUBS" in f or "TRIPS" in f: pers = "10"
        else: pers = "11"
    return pers

# --- 2. UI SETUP ---
st.set_page_config(page_title="Carlsbad Football Analytics", page_icon="🏈", layout="wide")

with st.sidebar:
    # Handle Case Sensitivity for Logo.png vs logo.png
    logo_files = ["Logo.png", "logo.png"]
    found_logo = False
    for lf in logo_files:
        if os.path.exists(lf):
            st.image(lf, use_container_width=True)
            found_logo = True
            break
    if not found_logo:
        st.subheader("🏈 CARLSBAD FOOTBALL")

st.title("🏈 Carlsbad Football Analytics")

uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = [str(c).strip() for c in df.columns]
    
    cols = {'type': 'PLAY TYPE', 'form': 'OFF FORM', 'gain': 'GN/LS', 
            'dn': 'DN', 'dist': 'DIST', 'play': 'OFF PLAY', 'field': 'YARD LN', 'series': 'SERIES'}
    
    if all(cols[k] in df.columns for k in ['type', 'form', 'gain']):
        df[cols['type']] = df[cols['type']].str.upper().str.strip()
        df[cols['gain']] = pd.to_numeric(df[cols['gain']], errors='coerce').fillna(0)
        df['PERSONNEL'] = df[cols['form']].apply(process_offensive_logic)
        p_data = df[df[cols['type']].isin(['RUN', 'PASS'])].copy()

        # Custom Foundation Tabs
        tabs = st.tabs([
            "📊 Personnel/Formations", "🎯 3rd Down", "📈 Frequency & Patterns", 
            "📍 Field Position", "🥅 Goal Line", "🔥 First Drive", "🧪 Custom Pivot Lab"
        ])

        with tabs[0]: # PERSONNEL/FORMATIONS
            st.header("Formation & Personnel Identity")
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Top 5 Formations")
                f_top = p_data[cols['form']].value_counts().head(5).index
                f_df = p_data[p_data[cols['form']].isin(f_top)]
                f_res = f_df.groupby(cols['form'])[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
                st.dataframe(f_res.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
            with c2:
                st.subheader("Top 5 Personnel")
                p_top = p_data['PERSONNEL'].value_counts().head(5).index
                p_res = p_data[p_data['PERSONNEL'].isin(p_top)].groupby('PERSONNEL')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
                st.dataframe(p_res.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))

        with tabs[1]: # 3RD DOWN
            st.header("3rd Down Efficiency")
            t3 = p_data[p_data[cols['dn']] == 3].copy()
            t3['Situation'] = t3[cols['dist']].apply(lambda x: "3rd & Short (1-3)" if x <= 3 else ("3rd & Mid (4-7)" if x <= 7 else "3rd & Long (7+)"))
            t3_res = t3.groupby('Situation')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
            st.dataframe(t3_res.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
            st.subheader("Specific Play Concepts")
            st.table(t3.groupby(['Situation', cols['play']]).size().unstack(fill_value=0))

        with tabs[2]: # FREQUENCY & PATTERNS
            st.header("Frequency & Play Patterns")
            col_r, col_p = st.columns(2)
            with col_r:
                st.subheader("Most Frequent Runs")
                st.table(p_data[p_data[cols['type']]=='RUN'][cols['play']].value_counts().head(5))
            with col_p:
                st.subheader("Most Frequent Passes")
                st.table(p_data[p_data[cols['type']]=='PASS'][cols['play']].value_counts().head(5))
            st.divider()
            st.subheader("Explosive Plays (Pass 20+, Run 10+)")
            er = (p_data[p_data[cols['type']] == 'RUN'][cols['gain']] >= 10).mean() * 100
            ep = (p_data[p_data[cols['type']] == 'PASS'][cols['gain']] >= 20).mean() * 100
            st.write(f"Run Explosive Rate: **{er:.1f}%** | Pass Explosive Rate: **{ep:.1f}%**")

        with tabs[3]: # FIELD POSITION
            st.header("Field Zone Tendencies")
            def get_zone(yd):
                if yd <= 20: return "Own 0-20"
                if yd <= 50: return "Own 21-50"
                return "Opp 49-21"
            p_data['Zone'] = p_data[cols['field']].apply(get_zone)
            zone_res = p_data.groupby('Zone')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
            st.dataframe(zone_res.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))

        with tabs[4]: # GOAL LINE
            st.header("Goal Line Analytics (Inside the 10)")
            gl = p_data[p_data[cols['field']] >= 90].copy()
            if not gl.empty:
                st.subheader("Personnel Distribution")
                st.table(gl['PERSONNEL'].value_counts())
                st.subheader("Specific Plays by Yards to Go")
                st.table(gl.groupby([cols['dist'], cols['play']]).size().unstack(fill_value=0))
            else:
                st.info("No goal-line plays detected.")

        with tabs[5]: # FIRST DRIVE
            st.header("First Drive Tendencies")
            first = p_data[p_data[cols['series']] == 1]
            if not first.empty:
                st.write(f"Opening Concept: **{first.iloc[0][cols['play']]}**")
                st.table(first[[cols['dn'], cols['dist'], cols['play'], cols['gain']]])

        with tabs[6]: # CUSTOM PIVOT LAB
            st.header("🧪 Custom Pivot Lab")
            row_choice = st.selectbox("Analyze By:", ['Situation', 'PERSONNEL', cols['form'], cols['dn']])
            metric = st.radio("Metric Selection:", ['Run/Pass %', 'Average Gain'])
            if metric == 'Run/Pass %':
                res = p_data.groupby(row_choice)[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
                st.dataframe(res.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
            else:
                # FIXED: Converted to Frame to ensure .style availability
                res = p_data.groupby(row_choice)[cols['gain']].mean().to_frame(name="Avg Gain")
                st.dataframe(res.style.background_gradient(cmap='Greens').format("{:.1f} yds"))
    else:
        st.error(f"Required columns missing: {list(cols.values())}")
