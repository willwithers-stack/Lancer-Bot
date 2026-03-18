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

def get_stars(percentage):
    if percentage >= 85: return "⭐⭐⭐⭐⭐"
    if percentage >= 75: return "⭐⭐⭐⭐"
    if percentage >= 65: return "⭐⭐⭐"
    if percentage >= 50: return "⭐⭐"
    return "⭐"

# --- 2. UI SETUP ---
st.set_page_config(page_title="Carlsbad Football Analytics", page_icon="🏈", layout="wide")

with st.sidebar:
    # Logo Handling (Case Sensitive check for Logo.png)
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
    st.caption("v2.63 AI Intelligence & Alerts")

st.title("🏈 Carlsbad Football Analytics")

uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Identify Play Number and ODK
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
        
        # Drive detection logic
        st_keywords = ['PUNT', 'FG', 'KICK', 'PAT', 'FIELD GOAL']
        df['Is_ST'] = df[cols['type']].apply(lambda x: any(kw in x for kw in st_keywords))
        df['Drive_ID'] = ((df[cols['odk']] != df[cols['odk']].shift()) | (df['Is_ST'] == True)).cumsum()
        
        p_data = df[df[cols['type']].isin(['RUN', 'PASS'])].copy()
        
        # Game Detection
        if play_no_col:
            p_data['Game_ID'] = (p_data[play_no_col].diff() < -10).cumsum()
        else:
            p_data['Game_ID'] = 0

        tabs = st.tabs([
            "📊 Personnel/Formations", "🎯 3rd Down", "📈 Frequency & Patterns", 
            "📍 Field Position", "🟢 Red/Green Zone", "🔮 Potpourri & AI", "🧪 Pivot Lab", "🔥 First Drives"
        ])

        # ... (Previous Tabs 0-4 are stable) ...

        with tabs[5]: # POTPOURRI & AI INTELLIGENCE
            st.header("🤖 AI Intelligence Alerts")
            
            intel_data = []

            # 1. Opening Run Frequency
            first_drive = p_data.groupby('Game_ID').apply(lambda x: x[x['Drive_ID'] == x['Drive_ID'].min()]).reset_index(drop=True)
            if not first_drive.empty:
                run_freq = (first_drive[cols['type']] == 'RUN').mean() * 100
                intel_data.append({"Category": "Script", "Insight": "Opening Run Freq", "Stat": f"{run_freq:.0f}%", "Strength": get_stars(run_freq)})

            # 2. Post-Sack Response
            # Identify sacks (Pass play with loss of 4+)
            sacks = p_data[(p_data[cols['type']] == 'PASS') & (p_data[cols['gain']] <= -4)].index
            post_sack_plays = p_data.loc[[i+1 for i in sacks if i+1 in p_data.index]]
            if not post_sack_plays.empty:
                # Check for run vs pass on the next play
                run_response = (post_sack_plays[cols['type']] == 'RUN').mean() * 100
                intel_data.append({"Category": "Sequence", "Insight": "Post-Sack Run Resp", "Stat": f"{run_response:.0f}%", "Strength": get_stars(run_response)})

            # 3. Mid-Field Run Tendency
            mid = p_data[(p_data[cols['field']] >= 21) & (p_data[cols['field']] <= 50)]
            if not mid.empty:
                mid_run = (mid[cols['type']] == 'RUN').mean() * 100
                intel_data.append({"Category": "Zone", "Insight": "Mid-Field Run", "Stat": f"{mid_run:.0f}%", "Strength": get_stars(mid_run)})

            # Display Table
            if intel_data:
                st.table(pd.DataFrame(intel_data))
            
            st.divider()
            
            # 4. Motion/Play Direction Correlation
            if cols['motion'] in p_data.columns and cols['p_dir'] in p_data.columns:
                st.subheader("Motion Direction Analysis")
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
