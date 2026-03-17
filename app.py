import streamlit as st
import pandas as pd
import re

# --- 1. CORE LOGIC: PERSONNEL & FORMATION ---
def process_offensive_logic(formation):
    f = str(formation).upper().strip()
    match = re.match(r'^(\d)(\d)', f)
    if match:
        pers = f"{match.group(1)}{match.group(2)}"
    else:
        if any(x in f for x in ["HEAVY", "JUMBO", "BIG"]): pers = "23"
        elif "EMPTY" in f: pers = "00"
        elif "DUBS" in f or "TRIPS" in f: pers = "10"
        elif "SPREAD" in f or "WING" in f: pers = "11"
        else: pers = "11"
    return pers

# --- 2. UI SETUP ---
st.set_page_config(page_title="Carlsbad Football Analytics", page_icon="🏈", layout="wide")

with st.sidebar:
    try:
        st.image("logo.png") 
    except:
        st.subheader("🏈 CARLSBAD FOOTBALL")

st.title("🏈 Carlsbad Football Analytics")

uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = [str(c).strip() for c in df.columns]
    
    cols = {'type': 'PLAY TYPE', 'form': 'OFF FORM', 'gain': 'GN/LS', 
            'dn': 'DN', 'dist': 'DIST', 'play': 'OFF PLAY', 'field': 'YARD LN',
            'motion': 'MOTION DIR', 'p_dir': 'PLAY DIR', 'series': 'SERIES'}
    
    if all(cols[k] in df.columns for k in ['type', 'form', 'gain']):
        df[cols['type']] = df[cols['type']].str.upper().str.strip()
        df[cols['gain']] = pd.to_numeric(df[cols['gain']], errors='coerce').fillna(0)
        df['PERSONNEL'] = df[cols['form']].apply(process_offensive_logic)
        p_data = df[df[cols['type']].isin(['RUN', 'PASS'])].copy()

        # Helper for Zone Logic [cite: 35]
        def get_zone(yd):
            if yd <= 20: return "Own 0-20"
            elif yd <= 50: return "Own 21-50"
            return "Opp 50-21"
        if cols['field'] in df.columns:
            p_data['Zone'] = p_data[cols['field']].apply(get_zone)

        tabs = st.tabs(["📊 Usage & Formations", "🎯 Situational Telling", "⚡ Explosives & Motion", "🔥 First Drive & Patterns"])

        with tabs[0]: # FORMATION & PERSONNEL USAGE
            st.header("Offensive Identity")
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Formation Usage (Off Form)")
                f_usage = p_data[cols['form']].value_counts().to_frame(name="Plays")
                f_usage['% Usage'] = (f_usage['Plays'] / len(p_data) * 100).round(0).astype(int).astype(str) + '%'
                st.table(f_usage) # 
            with c2:
                st.subheader("Personnel Group Usage")
                p_usage = p_data['PERSONNEL'].value_counts().to_frame(name="Plays")
                st.table(p_usage) # [cite: 7]
            st.info("20 Wing and DUBS form the core identity of the offense. [cite: 5]")

        with tabs[1]: # SITUATIONAL TELLING
            st.header("Down & Distance Tells")
            # Custom Logic for 3rd/4th Down Specifics
            def get_sit(row):
                d, dist = row[cols['dn']], row[cols['dist']]
                if d == 1 and dist >= 10: return "1st & 10 (Baseline)"
                if d == 2:
                    if dist <= 4: return "2nd & Short (1-4 yds)"
                    if dist >= 7: return "2nd & Long (7+ yds)"
                    return "2nd & Med (5-6 yds)"
                if d == 3:
                    if 4 <= dist <= 7: return "3rd Down (4-7 yds)"
                    if dist >= 7: return "3rd & Long (7+ yds)"
                    if dist <= 3: return "3rd & Short (1-3 yds)"
                if d == 4:
                    if dist <= 3: return "4th & Short (1-3 yds)"
                return f"{int(d)} down (Other)"

            p_data['Situation'] = p_data.apply(get_sit, axis=1)
            dd = p_data.groupby('Situation')[cols['type']].value_counts().unstack().fillna(0)
            if not dd.empty:
                row_sums = dd.sum(axis=1, numeric_only=True)
                dd['Run %'] = (dd['RUN'] / row_sums * 100).round(0).astype(int)
                dd['Pass %'] = 100 - dd['Run %']
                st.table(dd.style.format({"Run %": "{0}%", "Pass %": "{0}%"}))
            
            if 'Zone' in p_data.columns:
                st.subheader("Field Position Tendencies")
                zone_tend = p_data.groupby('Zone')[cols['type']].value_counts().unstack().fillna(0)
                st.table(zone_tend) # [cite: 35]
                st.write("Takeaway: From own 21-50, offense runs 80% of the time. [cite: 36]")

        with tabs[2]: # EXPLOSIVES & MOTION
            st.header("Productivity & Motion Correlation")
            c3, c4 = st.columns(2)
            with c3:
                st.subheader("Explosive Pass Rate by Down")
                pass_data = p_data[p_data[cols['type']] == 'PASS'].copy()
                pass_data['Explosive'] = pass_data[cols['gain']] >= 20
                exp_down = pass_data.groupby(cols['dn'])['Explosive'].mean() * 100
                st.table(exp_down.to_frame(name="Explosive Rate %").map("{:.0f}%".format)) # [cite: 29]
            with c4:
                if cols['motion'] in df.columns and cols['p_dir'] in df.columns:
                    st.subheader("Motion & Play Direction Correlation")
                    motion_corr = p_data.groupby([cols['motion'], cols['p_dir']]).size().unstack().fillna(0)
                    st.table(motion_corr) # 

        with tabs[3]: # DRIVE PATTERNS
            st.header("Drive Patterns & Frequent Concepts")
            
            # First Down/Drive Passing [cite: 44, 46]
            st.subheader("First Down Pass Efficiency")
            fd_pass = p_data[(p_data[cols['dn']] == 1) & (p_data[cols['type']] == 'PASS')]
            if not fd_pass.empty:
                st.metric("1st Down Pass Avg", f"{fd_pass[cols['gain']].mean():.1f} yds")
                st.write(f"Most Common 1st Down Passes: {', '.join(fd_pass[cols['play']].value_counts().head(3).index)}")

            c5, c6 = st.columns(2)
            with c5:
                st.subheader("Most Frequent Runs")
                st.table(p_data[p_data[cols['type']] == 'RUN'][cols['play']].value_counts().head(5)) # [cite: 38]
            with c6:
                st.subheader("Most Frequent Passes")
                st.table(p_data[p_data[cols['type']] == 'PASS'][cols['play']].value_counts().head(5))

            st.write("**Play Call Patterns:** Quick Pass, Play Action, and Dropback are most frequent. [cite: 41]")
    else:
        st.error(f"Missing required columns: {list(cols.values())}")
