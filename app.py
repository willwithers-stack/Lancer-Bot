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
    st.caption("v2.73 Whole Number Edition")

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
        df = df.dropna(subset=[cols['gain']])
        df[cols['gain']] = pd.to_numeric(df[cols['gain']], errors='coerce').fillna(0)
        df[cols['dn']] = pd.to_numeric(df[cols['dn']], errors='coerce').fillna(0).astype(int)
        df[cols['dist']] = pd.to_numeric(df[cols['dist']], errors='coerce').fillna(0).astype(int)
        df[cols['field']] = pd.to_numeric(df[cols['field']], errors='coerce').fillna(0)
        df[cols['type']] = df[cols['type']].astype(str).str.upper().str.strip()
        df['PERSONNEL'] = df[cols['form']].apply(process_offensive_logic)
        
        # --- REFINED SUCCESS LOGIC ---
        def calculate_success(row):
            dn = row[cols['dn']]
            dist = row[cols['dist']]
            gain = row[cols['gain']]
            if dn == 1: return gain >= (dist * 0.45) # Midpoint of 40-50%
            if dn == 2: return gain >= (dist * 0.65) # Midpoint of 60-70%
            if dn in [3, 4]: return gain >= dist    # 100% required
            return False

        df['Is_Successful'] = df.apply(calculate_success, axis=1)
        p_data = df[df[cols['type']].isin(['RUN', 'PASS'])].copy()

        tabs = st.tabs([
            "📊 Personnel/Formations", "🎯 3rd Down Strategy", "📈 Frequency & Patterns", 
            "🟢 Red/Green Zone", "🔮 Potpourri & AI", "🧪 Custom Pivot Lab"
        ])

        # --- TAB 1: 3RD DOWN (Whole Numbers) ---
        with tabs[1]:
            st.header("🎯 3rd Down Strategy")
            t3 = p_data[p_data[cols['dn']] == 3].copy()
            if not t3.empty:
                st.metric("Overall 3rd Down Success", f"{round(t3['Is_Successful'].mean()*100)}%")
                t3['Sit'] = t3[cols['dist']].apply(lambda x: "3rd & Short (1-3)" if x <= 3 else ("3rd & Mid (4-7)" if x <= 7 else "3rd & Long (7+)"))
                c1, c2 = st.columns(2)
                with c1:
                    sit_succ = t3.groupby('Sit')['Is_Successful'].mean().mul(100).round(0).astype(int).to_frame(name="Success %")
                    st.table(sit_succ)
                with c2:
                    t3_res = t3.groupby('Sit')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100).round(0).astype(int)
                    st.dataframe(t3_res.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))

        # --- TAB 2: FREQUENCY (Whole Numbers) ---
        with tabs[2]:
            st.header("📈 Frequency & Patterns")
            p_data['Exp'] = np.where((p_data[cols['type']] == 'RUN') & (p_data[cols['gain']] >= 10), True,
                            np.where((p_data[cols['type']] == 'PASS') & (p_data[cols['gain']] >= 20), True, False))
            st.metric("Overall Explosive Rate", f"{round(p_data['Exp'].mean()*100)}%")
            exp_res = p_data.groupby([cols['dn'], cols['type']])['Exp'].mean().unstack().fillna(0).mul(100).round(0).astype(int)
            st.dataframe(exp_res.style.background_gradient(cmap='Greens').format("{:.0f}%"))

        # --- TAB 4: POTPOURRI & AI (NEW SUCCESS METRIC) ---
        with tabs[4]:
            st.header("🔮 Potpourri: Sequence & Success")
            # 1. Total Success Rate Metric
            total_success = round(p_data['Is_Successful'].mean() * 100)
            st.metric("Total Offensive Success Rate", f"{total_success}%")
            st.caption("Success = 1D: 45% dist | 2D: 65% dist | 3D/4D: 100% dist")
            
            # 2. Success by Down Heatmap
            dn_success = p_data.groupby(cols['dn'])['Is_Successful'].mean().mul(100).round(0).astype(int).to_frame(name="Success %")
            st.table(dn_success)

            # 3. AI Intelligence
            st.divider()
            intel = []
            sack_mask = (df[cols['result']].str.contains('Sack', case=False, na=False)) | ((df[cols['type']] == 'PASS') & (df[cols['gain']] <= -4))
            post_sack = df.loc[[i+1 for i in df[sack_mask].index if i+1 in df.index]]
            if not post_sack.empty:
                rate = round((post_sack[cols['type']].str.upper() == 'RUN').mean() * 100)
                intel.append({"Category": "Sequence", "Insight": "Post-Sack Run Resp", "Stat": f"{rate}%", "Strength": get_stars(rate)})
            if intel: st.table(pd.DataFrame(intel))

        # --- TAB 5: PIVOT LAB ---
        with tabs[5]:
            st.header("🧪 Custom Pivot Lab")
            row = st.selectbox("Group By:", ['PERSONNEL', cols['form'], cols['dn']])
            metric = st.radio("Metric:", ['Run/Pass %', 'Average Gain'])
            if metric == 'Run/Pass %':
                res = p_data.groupby(row)[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100).round(0).astype(int)
                st.dataframe(res.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
            else:
                res = p_data.groupby(row)[cols['gain']].mean().round(0).astype(int).to_frame(name="Avg Gain")
                st.dataframe(res.style.background_gradient(cmap='Greens').format("{:d} yds"))

    else:
        st.error(f"Missing required columns: {list(cols.values())}")
