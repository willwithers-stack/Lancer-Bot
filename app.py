import streamlit as st
import pandas as pd
import re
import os
import numpy as np

# --- 1. CORE SCORING LOGIC ---
def process_offensive_logic(formation):
    f = str(formation).upper().strip()
    match = re.match(r'^(\d)(\d)', f)
    if match:
        pers = f"{match.group(1)}{match.group(2)}"
    else:
        # Standard fallback for Carlsbad's common sets
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
    # Branding consistent with user preference
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
    st.caption("v2.77 Kicking & Stability Build")

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
        # --- DATA CLEANING & RECOVERY ---
        # 1. Handle Kicking: Keep ODK='O' for offense but use 'K'/'S' for drive tracking
        df[cols['type']] = df[cols['type']].astype(str).str.upper().str.strip()
        
        # 2. Coerce numeric types to whole numbers
        # We fill NA with 0 here but will drop rows with blank GAIN later for offense only
        df[cols['gain']] = pd.to_numeric(df[cols['gain']], errors='coerce').fillna(0).round(0).astype(int)
        df[cols['dn']] = pd.to_numeric(df[cols['dn']], errors='coerce').fillna(0).astype(int)
        df[cols['dist']] = pd.to_numeric(df[cols['dist']], errors='coerce').fillna(0).astype(int)
        df[cols['field']] = pd.to_numeric(df[cols['field']], errors='coerce').fillna(0).astype(int)
        
        # 3. Drive Tracking using ODK transitions
        df['Drive_ID'] = (df[cols['odk']] != df[cols['odk']].shift()).cumsum()
        
        # Filter for Run/Pass Offense (excluding kicking for core tabs)
        p_data = df[df[cols['type']].isin(['RUN', 'PASS'])].copy()
        p_data['PERSONNEL'] = p_data[cols['form']].apply(process_offensive_logic)

        # 4. Winning Probability Metrics
        p_data['Is_FD'] = (p_data[cols['gain']] >= p_data[cols['dist']]).astype(int)
        p_data['Is_Int'] = p_data[cols['result']].str.contains('Interception', case=False, na=False).astype(int)
        
        def calc_succ(row):
            d, dist, g = row[cols['dn']], row[cols['dist']], row[cols['gain']]
            if d == 1: return g >= (dist * 0.45)
            if d == 2: return g >= (dist * 0.65)
            return g >= dist
        p_data['Is_Succ'] = p_data.apply(calc_succ, axis=1).astype(int)

        # TAB SYSTEM
        tabs = st.tabs([
            "📊 Personnel Identity", "🎯 3rd Down Efficiency", "📈 Chain Moving (Freq)", 
            "🟢 Red/Green Zone", "🔮 Winning Probability (AI)", "🧪 Custom Pivot Lab", "🏈 Kicking Game"
        ])

        # --- TAB 1: 3RD DOWN (The Gold Standard Layout) ---
        with tabs[1]:
            st.header("🎯 3rd Down Efficiency")
            t3 = p_data[p_data[cols['dn']] == 3].copy()
            if not t3.empty:
                st.metric("3rd Down Conversion Rate", f"{round(t3['Is_FD'].mean()*100)}%")
                t3['Sit'] = t3[cols['dist']].apply(lambda x: "3rd & Short (1-3)" if x <= 3 else ("3rd & Mid (4-7)" if x <= 7 else "3rd & Long (7+)"))
                c1, c2 = st.columns(2)
                with c1:
                    st.table(t3.groupby('Sit')['Is_FD'].mean().mul(100).round(0).astype(int).to_frame("FD Rate %"))
                with c2:
                    t3_tend = t3.groupby('Sit')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100).round(0).astype(int)
                    st.dataframe(t3_tend.style.background_gradient(cmap='RdYlGn_r').format("{:d}%"), width="stretch")
                for sit in ["3rd & Short (1-3)", "3rd & Mid (4-7)", "3rd & Long (7+)"]:
                    with st.expander(f"Top 3rd Down Calls: {sit}"):
                        st.table(t3[t3['Sit'] == sit][cols['play']].value_counts().head(3))

        # --- TAB 6: KICKING GAME (NEW) ---
        with tabs[6]:
            st.header("🏈 Kicking & Special Teams")
            k_data = df[df[cols['odk']].isin(['K', 'S'])].copy()
            if not k_data.empty:
                st.write("**Special Teams Play Volume**")
                st.table(k_data[cols['type']].value_counts().to_frame("Volume"))
                
                c_k1, c_k2 = st.columns(2)
                with c_k1:
                    st.subheader("Punt Efficiency")
                    punts = k_data[k_data[cols['type']] == 'PUNT']
                    if not punts.empty:
                        st.write(f"Average Punt Result: **{punts[cols['result']].mode()[0]}**")
                        st.table(punts[cols['result']].value_counts().to_frame("Count"))
                with c_k2:
                    st.subheader("Kickoff (KO) Distribution")
                    kos = k_data[k_data[cols['type']] == 'KO']
                    if not kos.empty:
                        st.table(kos[cols['result']].value_counts().to_frame("Count"))
            else:
                st.info("No kicking/special teams data detected in ODK tags 'K' or 'S'.")

        # --- TAB 4: WINNING PROBABILITY (STABLE) ---
        with tabs[4]:
            st.header("🔮 Winning Probability (AI)")
            st.metric("Overall FD Rate", f"{round(p_data['Is_FD'].mean()*100)}%")
            st.divider()
            st.subheader("🤖 AI Scouting Intelligence")
            intel = []
            sack_mask = (df[cols['result']].str.contains('Sack', case=False, na=False)) | ((df[cols['type']] == 'PASS') & (df[cols['gain']] <= -4))
            post_sack = df.loc[[i+1 for i in df[sack_mask].index if i+1 in df.index]]
            if not post_sack.empty:
                rate = round((post_sack[cols['type']].str.upper() == 'RUN').mean() * 100)
                intel.append({"Category": "Sequence", "Insight": "Post-Sack Run Resp", "Stat": f"{rate}%", "Strength": get_stars(rate)})
            if intel: st.table(pd.DataFrame(intel))

    else:
        st.error(f"Missing required columns: {list(cols.values())}")
