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
    st.caption("v2.71 Unified Layout Edition")

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
        p_data = df[df[cols['type']].isin(['RUN', 'PASS'])].copy()

        # Define Tabs centrally to prevent NameErrors
        tabs = st.tabs([
            "📊 Personnel/Formations", "🎯 3rd Down Strategy", "📈 Frequency & Patterns", 
            "🟢 Red/Green Zone", "🔮 Potpourri & AI", "🧪 Custom Pivot Lab"
        ])

        # --- TAB 0: PERSONNEL (Unified Layout) ---
        with tabs[0]:
            st.header("📊 Personnel Identity")
            avg_p_gain = p_data.groupby('PERSONNEL')[cols['gain']].mean().to_frame(name="Avg Gain")
            st.metric("Top Personnel Efficiency", f"{avg_p_gain['Avg Gain'].max():.1f} yds")
            
            c1, c2 = st.columns(2)
            with c1:
                st.table(avg_p_gain.style.background_gradient(cmap='Greens'))
            with c2:
                p_res = p_data.groupby('PERSONNEL')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
                st.dataframe(p_res.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
            
            for p_group in p_data['PERSONNEL'].unique():
                with st.expander(f"Top Plays: {p_group} Personnel"):
                    st.table(p_data[p_data['PERSONNEL'] == p_group][cols['play']].value_counts().head(3))

        # --- TAB 1: 3RD DOWN (Stable Unchanged Layout) ---
        with tabs[1]:
            st.header("🎯 3rd Down Strategy")
            t3 = p_data[p_data[cols['dn']] == 3].copy()
            if not t3.empty:
                t3['Success'] = t3[cols['gain']] >= t3[cols['dist']]
                st.metric("Overall 3rd Down Success Rate", f"{t3['Success'].mean() * 100:.1f}%")
                t3['Sit'] = t3[cols['dist']].apply(lambda x: "3rd & Short (1-3)" if x <= 3 else ("3rd & Mid (4-7)" if x <= 7 else "3rd & Long (7+)"))
                c1, c2 = st.columns(2)
                with c1: st.table(t3.groupby('Sit').agg({'Success': 'mean'}).mul(100).round(1))
                with c2: st.dataframe(t3.groupby('Sit')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100).style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
                for sit in ["3rd & Short (1-3)", "3rd & Mid (4-7)", "3rd & Long (7+)"]:
                    s_sub = t3[t3['Sit'] == sit]
                    if not s_sub.empty:
                        with st.expander(f"Top Plays: {sit}"): st.table(s_sub[cols['play']].value_counts().head(3))

        # --- TAB 3: RED/GREEN ZONE (Unified Layout) ---
        with tabs[3]:
            st.header("🟢 Red & Green Zone Strategy")
            rg_data = p_data[p_data[cols['field']] > 0].copy()
            if not rg_data.empty:
                rg_data['RG_Zone'] = rg_data[cols['field']].apply(lambda x: "🟢 Green Zone (Inside 10)" if x <= 10 else "🔴 Red Zone (20-11)")
                rz_eff = (rg_data[cols['gain']] >= 3).mean() * 100
                st.metric("Red Zone Efficiency (Plays 3+ yds)", f"{rz_eff:.1f}%")
                c1, c2 = st.columns(2)
                with c1: st.table(rg_data['RG_Zone'].value_counts())
                with c2: st.dataframe(rg_data.groupby('RG_Zone')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100).style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
                for zone in ["🔴 Red Zone (20-11)", "🟢 Green Zone (Inside 10)"]:
                    z_sub = rg_data[rg_data['RG_Zone'] == zone]
                    if not z_sub.empty:
                        with st.expander(f"Top Plays: {zone}"): st.table(z_sub[cols['play']].value_counts().head(3))

        # --- TAB 5: PIVOT LAB ---
        with tabs[5]:
            st.header("🧪 Custom Pivot Lab")
            row_opt = st.selectbox("Group By:", ['PERSONNEL', cols['form'], cols['dn']])
            res = p_data.groupby(row_opt)[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
            st.dataframe(res.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))

    else:
        st.error(f"Missing required columns: {list(cols.values())}")
