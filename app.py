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
    elif percentage >= 75: return "⭐⭐⭐⭐"
    elif percentage >= 65: return "⭐⭐⭐"
    elif percentage >= 50: return "⭐⭐"
    return "⭐"

# --- 2. UI SETUP ---
st.set_page_config(page_title="Carlsbad Football Analytics", page_icon="🏈", layout="wide")

with st.sidebar:
    logo_files = ["Logo.png", "logo.png"]
    found_logo = False
    for lf in logo_files:
        if os.path.exists(lf):
            st.image(lf, width='stretch')
            found_logo = True
            break
    if not found_logo:
        st.subheader("🏈 CARLSBAD FOOTBALL")
    st.write("---")
    st.caption("v2.69 Intelligence + Success Metrics")

st.title("🏈 Carlsbad Football Analytics")

uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = [str(c).strip() for c in df.columns]
    
    cols = {
        'type': 'PLAY TYPE', 'form': 'OFF FORM', 'gain': 'GN/LS', 
        'dn': 'DN', 'dist': 'DIST', 'play': 'OFF PLAY', 'field': 'YARD LN', 
        'odk': 'ODK', 'hash': 'HASH', 'p_dir': 'PLAY DIR', 'motion': 'MOTION DIR',
        'result': 'RESULT'
    }
    
    if all(cols[k] in df.columns for k in ['type', 'form', 'gain']):
        # --- DATA CLEANING ---
        # 1. Throw out plays with blank gains
        df = df.dropna(subset=[cols['gain']])
        
        # 2. Force Numeric Types (Prevents TypeErrors in logs)
        df[cols['gain']] = pd.to_numeric(df[cols['gain']], errors='coerce').fillna(0)
        df[cols['dn']] = pd.to_numeric(df[cols['dn']], errors='coerce').fillna(0).astype(int)
        df[cols['dist']] = pd.to_numeric(df[cols['dist']], errors='coerce').fillna(0).astype(int)
        df[cols['field']] = pd.to_numeric(df[cols['field']], errors='coerce').fillna(0)
        
        df[cols['type']] = df[cols['type']].astype(str).str.upper().str.strip()
        df['PERSONNEL'] = df[cols['form']].apply(process_offensive_logic)
        
        # Define Offensive dataset
        p_data = df[df[cols['type']].isin(['RUN', 'PASS'])].copy()

        tabs = st.tabs([
            "📊 Personnel/Formations", 
            "🎯 3rd Down Strategy", 
            "📈 Frequency & Patterns", 
            "🟢 Red/Green Zone", 
            "🔮 Potpourri & AI", 
            "🧪 Custom Pivot Lab"
        ])

        # --- TAB 1: 3RD DOWN (WITH SUCCESS RATE) ---
        with tabs[1]:
            st.header("🎯 3rd Down Situational Analysis")
            t3 = p_data[p_data[cols['dn']] == 3].copy()
            if not t3.empty:
                # Success Logic: Gain >= Distance
                t3['Success'] = t3[cols['gain']] >= t3[cols['dist']]
                overall_success = t3['Success'].mean() * 100
                st.metric("Overall 3rd Down Success Rate", f"{overall_success:.1f}%")
                
                t3['Sit'] = t3[cols['dist']].apply(lambda x: "3rd & Short (1-3)" if x <= 3 else ("3rd & Mid (4-7)" if x <= 7 else "3rd & Long (7+)"))
                
                # Success by bucket
                sit_stats = t3.groupby('Sit').agg({'Success': 'mean'}).mul(100).round(1)
                st.table(sit_stats.rename(columns={'Success': 'Success %'}))
                
                # Top Plays expanders
                for sit in ["3rd & Short (1-3)", "3rd & Mid (4-7)", "3rd & Long (7+)"]:
                    subset = t3[t3['Sit'] == sit]
                    if not subset.empty:
                        with st.expander(f"Top Plays: {sit}"):
                            st.table(subset[cols['play']].value_counts().head(3))

        # --- TAB 4: AI INTELLIGENCE (POST-SACK/PENALTY) ---
        with tabs[4]:
            st.header("🤖 AI Scouting Intelligence")
            intel_data = []
            
            # Post-Sack Response Logic
            sack_mask = (df[cols['result']].str.contains('Sack', case=False, na=False)) | \
                        ((df[cols['type']] == 'PASS') & (df[cols['gain']] <= -4))
            sack_indices = df[sack_mask].index
            post_sack_plays = df.loc[[i+1 for i in sack_indices if i+1 in df.index]]
            
            if not post_sack_plays.empty:
                run_resp = (post_sack_plays[cols['type']].str.upper() == 'RUN').mean() * 100
                intel_data.append({"Category": "Sequence", "Insight": "Post-Sack Run Resp", "Stat": f"{run_resp:.0f}%", "Strength": get_stars(run_resp)})

            # Post-Penalty Response Logic
            penalty_mask = (df[cols['type']].str.contains('PENALTY', case=False, na=False))
            pen_indices = df[penalty_mask].index
            post_pen_plays = df.loc[[i+1 for i in pen_indices if i+1 in df.index]]
            
            if not post_pen_plays.empty:
                run_resp_pen = (post_pen_plays[cols['type']].str.upper() == 'RUN').mean() * 100
                intel_data.append({"Category": "Sequence", "Insight": "Post-Penalty Run Resp", "Stat": f"{run_resp_pen:.0f}%", "Strength": get_stars(run_resp_pen)})

            if intel_data:
                st.table(pd.DataFrame(intel_data))

        # (Other tabs follow same stable structure...)
