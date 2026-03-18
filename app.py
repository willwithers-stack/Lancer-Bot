import streamlit as st
import pandas as pd
import re
import os
import numpy as np

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
    # Robust Logo Search (Handles Case Sensitivity for Logo.png)
    logo_files = ["Logo.png", "logo.png"]
    found_logo = False
    for lf in logo_files:
        if os.path.exists(lf):
            st.image(lf, use_container_width=True)
            found_logo = True
            break
    if not found_logo:
        st.subheader("🏈 CARLSBAD FOOTBALL")
    st.write("---")
    st.caption("v2.62 AI Intelligence Edition")

st.title("🏈 Carlsbad Football Analytics")

uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = [str(c).strip() for c in df.columns]
    
    play_no_col = next((c for c in df.columns if c.upper() in ['PLAY #', 'PL #', 'PLAY NO']), None)
    cols = {
        'type': 'PLAY TYPE', 'form': 'OFF FORM', 'gain': 'GN/LS', 
        'dn': 'DN', 'dist': 'DIST', 'play': 'OFF PLAY', 'field': 'YARD LN', 
        'odk': 'ODK', 'hash': 'HASH', 'p_dir': 'PLAY DIR', 'motion': 'MOTION DIR'
    }
    
    if all(cols[k] in df.columns for k in ['type', 'form', 'gain']):
        # Data Cleaning
        df[cols['type']] = df[cols['type']].astype(str).str.upper().str.strip()
        df[cols['gain']] = pd.to_numeric(df[cols['gain']], errors='coerce').fillna(0)
        df['PERSONNEL'] = df[cols['form']].apply(process_offensive_logic)
        
        # Drive detection
        st_keywords = ['PUNT', 'FG', 'KICK', 'PAT', 'FIELD GOAL']
        df['Is_ST'] = df[cols['type']].apply(lambda x: any(kw in x for kw in st_keywords))
        df['Drive_ID'] = ((df[cols['odk']] != df[cols['odk']].shift()) | (df['Is_ST'] == True)).cumsum()
        p_data = df[df[cols['type']].isin(['RUN', 'PASS'])].copy()

        tabs = st.tabs([
            "📊 Personnel/Formations", "🎯 3rd Down", "📈 Frequency & Patterns", 
            "📍 Field Position", "🟢 Red/Green Zone", "🔮 Potpourri & AI", "🧪 Pivot Lab", "🔥 First Drives"
        ])

        # ... (Previous Tabs 0-4 are stable) ...

        with tabs[5]: # POTPOURRI & AI INTELLIGENCE
            st.header("🤖 AI Scouting Intelligence")
            
            # 1. Automatic Personnel Tendency Alerts (70% Threshold)
            matrix = p_data.groupby('PERSONNEL')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
            if not matrix.empty:
                st.subheader("High Tendency Alerts")
                for pers, row in matrix.iterrows():
                    if row['RUN'] >= 70:
                        st.error(f"⚠️ **{pers} Personnel**: High Run Tell ({row['RUN']:.0f}%)")
                    elif row['PASS'] >= 70:
                        st.warning(f"⚠️ **{pers} Personnel**: High Pass Tell ({row['PASS']:.0f}%)")

            # 2. Mid-Field Confidence Meter (Own 21-50)
            mid_field = p_data[(p_data[cols['field']] >= 21) & (p_data[cols['field']] <= 50)]
            if not mid_field.empty:
                run_rate = (mid_field[cols['type']] == 'RUN').mean() * 100
                st.divider()
                st.subheader("Zone Intelligence: Mid-Field")
                st.write(f"Offense runs the ball **{run_rate:.0f}%** of the time from their own 21-50.")
                st.select_slider("AI Confidence Meter", options=["Low", "Medium", "High", "Lock"], 
                                 value="Lock" if run_rate > 80 else ("High" if run_rate > 70 else "Medium"), disabled=True)

            # 3. Correlation Check: Motion vs Direction
            st.divider()
            if cols['motion'] in p_data.columns and cols['p_dir'] in p_data.columns:
                st.subheader("Motion Direction Correlation")
                def check_corr(row):
                    m, p = str(row[cols['motion']]).upper(), str(row[cols['p_dir']]).upper()
                    if m[0:1] == p[0:1] and m[0:1] in ['L','R']: return 'With Motion'
                    if m[0:1] != p[0:1] and m[0:1] in ['L','R']: return 'Away from Motion'
                    return 'Static'
                p_data['M_Corr'] = p_data.apply(check_corr, axis=1)
                st.table(p_data[p_data['M_Corr'] != 'Static']['M_Corr'].value_counts(normalize=True).mul(100).round(1).astype(str) + '%')

        # ... (Remaining tabs remain stable) ...

    else:
        st.error(f"Missing required columns: {list(cols.values())}")
