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
    st.caption("v2.75 Winning Probability Edition")

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

        # --- ADVANCED WINNING METRICS ---
        # 1. First Down (FD) Rate: Gain >= Distance
        df['Is_FD'] = df[cols['gain']] >= df[cols['dist']]
        
        # 2. Success Rate: (1D: 45%, 2D: 65%, 3D+: 100%)
        def calc_succ(row):
            d, dist, g = row[cols['dn']], row[cols['dist']], row[cols['gain']]
            if d == 1: return g >= (dist * 0.45)
            if d == 2: return g >= (dist * 0.65)
            return g >= dist
        df['Is_Succ'] = df.apply(calc_succ, axis=1)

        # 3. Interception (Int) Rate: (Ints / Total Pass Plays)
        df['Is_Int'] = df[cols['result']].str.contains('Interception', case=False, na=False)
        
        p_data = df[df[cols['type']].isin(['RUN', 'PASS'])].copy()

        tabs = st.tabs([
            "📊 Personnel Identity", "🎯 3rd Down Efficiency", "📈 Chain Moving Patterns", 
            "🟢 Red/Green Zone", "🔮 Winning Probability (AI)", "🧪 Custom Pivot Lab"
        ])

        # --- TAB 0: PERSONNEL (Integrated FD Rate) ---
        with tabs[0]:
            st.header("📊 Personnel FD & Efficiency")
            p_stats = p_data.groupby('PERSONNEL').agg({cols['gain']: 'mean', 'Is_FD': 'mean'}).mul({'Is_FD': 100}).round(0).astype(int)
            st.metric("Top FD Rate Personnel", f"{p_stats['Is_FD'].max()}%")
            c1, c2 = st.columns(2)
            with c1: st.table(p_stats.rename(columns={cols['gain']: 'Avg Gain', 'Is_FD': 'FD Rate %'}))
            with c2: st.dataframe(p_data.groupby('PERSONNEL')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100).round(0).astype(int).style.background_gradient(cmap='RdYlGn_r').format("{:d}%"))
            for p in p_data['PERSONNEL'].unique():
                with st.expander(f"Top Play-Callers for {p} Personnel"):
                    st.table(p_data[p_data['PERSONNEL'] == p][cols['play']].value_counts().head(3))

        # --- TAB 1: 3RD DOWN (Stable FD Strategy) ---
        with tabs[1]:
            st.header("🎯 3rd Down Chain-Moving Strategy")
            t3 = p_data[p_data[cols['dn']] == 3].copy()
            if not t3.empty:
                st.metric("3rd Down Conversion Rate", f"{round(t3['Is_FD'].mean()*100)}%")
                t3['Sit'] = t3[cols['dist']].apply(lambda x: "3rd & Short (1-3)" if x <= 3 else ("3rd & Mid (4-7)" if x <= 7 else "3rd & Long (7+)"))
                ca, cb = st.columns(2)
                with ca: st.table(t3.groupby('Sit')['Is_FD'].mean().mul(100).round(0).astype(int).to_frame(name="FD Rate %"))
                with cb: st.dataframe(t3.groupby('Sit')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100).round(0).astype(int).style.background_gradient(cmap='RdYlGn_r').format("{:d}%"))
                for sit in ["3rd & Short (1-3)", "3rd & Mid (4-7)", "3rd & Long (7+)"]:
                    sub = t3[t3['Sit'] == sit]
                    if not sub.empty:
                        with st.expander(f"Top 3rd Down Calls: {sit}"): st.table(sub[cols['play']].value_counts().head(3))

        # --- TAB 3: RED/GREEN ZONE (Integrated Int Rate) ---
        with tabs[3]:
            st.header("🟢 Red/Green Zone Turnover Risk")
            rg_data = p_data[p_data[cols['field']] > 0].copy()
            if not rg_data.empty:
                # Calculate Interception Rate specifically for Red Zone
                passes = rg_data[rg_data[cols['type']] == 'PASS']
                int_rate = round(passes['Is_Int'].mean() * 100) if not passes.empty else 0
                st.metric("Red Zone Interception Rate", f"{int_rate}%")
                
                rg_data['Zone'] = rg_data[cols['field']].apply(lambda x: "🟢 Green Zone (<10)" if x <= 10 else "🔴 Red Zone (20-11)")
                c1, c2 = st.columns(2)
                with c1: st.table(rg_data.groupby('Zone')['Is_FD'].mean().mul(100).round(0).astype(int).to_frame(name="FD Rate %"))
                with c2: st.dataframe(rg_data.groupby('Zone')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100).round(0).astype(int).style.background_gradient(cmap='RdYlGn_r').format("{:d}%"))
                for z in ["🔴 Red Zone (20-11)", "🟢 Green Zone (<10)"]:
                    sub = rg_data[rg_data['Zone'] == z]
                    if not sub.empty:
                        with st.expander(f"Scoring Playbook: {z}"): st.table(sub[cols['play']].value_counts().head(3))

        # --- TAB 4: WINNING PROBABILITY & AI ---
        with tabs[4]:
            st.header("🔮 Winning Probability & Intelligence")
            total_fd = round(p_data['Is_FD'].mean() * 100)
            overall_passes = p_data[p_data[cols['type']] == 'PASS']
            total_int = round(overall_passes['Is_Int'].mean() * 100) if not overall_passes.empty else 0
            
            col_x, col_y = st.columns(2)
            with col_x:
                st.metric("Overall First Down Rate", f"{total_fd}%")
                st.caption("A key predictor of victory per high-school research.")
            with col_y:
                st.metric("Total Interception Rate", f"{total_int}%")
                st.caption("Game-disruptor metric.")

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
