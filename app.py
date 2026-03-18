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
    st.caption("v2.72 Unified Master Layout")

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
        # --- DATA CLEANING & DRIVE DETECTION ---
        df = df.dropna(subset=[cols['gain']])
        df[cols['gain']] = pd.to_numeric(df[cols['gain']], errors='coerce').fillna(0)
        df[cols['dn']] = pd.to_numeric(df[cols['dn']], errors='coerce').fillna(0).astype(int)
        df[cols['dist']] = pd.to_numeric(df[cols['dist']], errors='coerce').fillna(0).astype(int)
        df[cols['field']] = pd.to_numeric(df[cols['field']], errors='coerce').fillna(0)
        df[cols['type']] = df[cols['type']].astype(str).str.upper().str.strip()
        df['PERSONNEL'] = df[cols['form']].apply(process_offensive_logic)
        
        # Drive detection (Heuristic)
        st_keywords = ['PUNT', 'FG', 'KICK', 'PAT', 'FIELD GOAL']
        df['Is_ST'] = df[cols['type']].apply(lambda x: any(kw in x for kw in st_keywords))
        df['Drive_ID'] = ((df[cols['odk']] != df[cols['odk']].shift()) | (df['Is_ST'] == True)).cumsum()
        
        p_data = df[df[cols['type']].isin(['RUN', 'PASS'])].copy()

        # CENTRALIZED TAB DEFINITION
        tabs = st.tabs([
            "📊 Personnel/Formations", "🎯 3rd Down Strategy", "📈 Frequency & Patterns", 
            "🟢 Red/Green Zone", "🔮 Potpourri & AI", "🧪 Custom Pivot Lab"
        ])

        # --- TAB 0: PERSONNEL ---
        with tabs[0]:
            st.header("📊 Personnel Identity")
            eff = p_data.groupby('PERSONNEL')[cols['gain']].mean().to_frame(name="Avg Gain")
            st.metric("Top Personnel Efficiency", f"{eff['Avg Gain'].max():.1f} yds")
            c1, c2 = st.columns(2)
            with c1: st.table(eff.style.background_gradient(cmap='Greens').format("{:.1f}"))
            with c2: st.dataframe(p_data.groupby('PERSONNEL')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100).style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
            for p in p_data['PERSONNEL'].unique():
                with st.expander(f"Top Plays: {p} Personnel"):
                    st.table(p_data[p_data['PERSONNEL'] == p][cols['play']].value_counts().head(3))

        # --- TAB 1: 3RD DOWN ---
        with tabs[1]:
            st.header("🎯 3rd Down Strategy")
            t3 = p_data[p_data[cols['dn']] == 3].copy()
            if not t3.empty:
                t3['Success'] = t3[cols['gain']] >= t3[cols['dist']]
                st.metric("Overall 3rd Down Success", f"{t3['Success'].mean()*100:.1f}%")
                t3['Sit'] = t3[cols['dist']].apply(lambda x: "3rd & Short (1-3)" if x <= 3 else ("3rd & Mid (4-7)" if x <= 7 else "3rd & Long (7+)"))
                c1, c2 = st.columns(2)
                with c1: st.table(t3.groupby('Sit').agg({'Success': 'mean'}).mul(100).round(1).rename(columns={'Success':'Success %'}))
                with c2: st.dataframe(t3.groupby('Sit')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100).style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
                for sit in ["3rd & Short (1-3)", "3rd & Mid (4-7)", "3rd & Long (7+)"]:
                    sub = t3[t3['Sit'] == sit]
                    if not sub.empty:
                        with st.expander(f"Top Plays: {sit}"): st.table(sub[cols['play']].value_counts().head(3))

        # --- TAB 2: FREQUENCY & PATTERNS (RESTORED) ---
        with tabs[2]:
            st.header("📈 Frequency & Explosives")
            p_data['Exp'] = np.where((p_data[cols['type']] == 'RUN') & (p_data[cols['gain']] >= 10), True,
                            np.where((p_data[cols['type']] == 'PASS') & (p_data[cols['gain']] >= 20), True, False))
            st.metric("Overall Explosive Rate", f"{p_data['Exp'].mean()*100:.1f}%")
            c1, c2 = st.columns(2)
            with c1:
                st.write("**Top Plays (by Volume)**")
                st.table(p_data[cols['play']].value_counts().head(5))
            with c2:
                st.write("**Explosive Rate by Down**")
                exp_res = p_data.groupby([cols['dn'], cols['type']])['Exp'].mean().unstack().fillna(0).mul(100)
                st.dataframe(exp_res.style.background_gradient(cmap='Greens').format("{:.1f}%"))
            with st.expander("List of Home Run Plays (Yardage)"):
                st.table(p_data[p_data['Exp'] == True][[cols['dn'], cols['dist'], cols['play'], cols['gain']]].sort_values(by=cols['gain'], ascending=False).head(10))

        # --- TAB 3: RED/GREEN ZONE ---
        with tabs[3]:
            st.header("🟢 Red & Green Zone Strategy")
            rg_data = p_data[p_data[cols['field']] > 0].copy()
            if not rg_data.empty:
                rg_data['Zone'] = rg_data[cols['field']].apply(lambda x: "🟢 Green Zone (<10)" if x <= 10 else "🔴 Red Zone (20-11)")
                st.metric("RZ Efficiency (3+ Yds)", f"{(rg_data[cols['gain']] >= 3).mean()*100:.1f}%")
                c1, c2 = st.columns(2)
                with c1: st.table(rg_data['Zone'].value_counts())
                with c2: st.dataframe(rg_data.groupby('Zone')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100).style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
                for z in ["🔴 Red Zone (20-11)", "🟢 Green Zone (<10)"]:
                    sub = rg_data[rg_data['Zone'] == z]
                    if not sub.empty:
                        with st.expander(f"Top Plays: {z}"): st.table(sub[cols['play']].value_counts().head(3))

        # --- TAB 4: POTPOURRI & AI (RESTORED) ---
        with tabs[4]:
            st.header("🔮 AI Scouting Intelligence")
            intel = []
            sack_mask = (df[cols['result']].str.contains('Sack', case=False, na=False)) | ((df[cols['type']] == 'PASS') & (df[cols['gain']] <= -4))
            post_sack = df.loc[[i+1 for i in df[sack_mask].index if i+1 in df.index]]
            if not post_sack.empty:
                rate = (post_sack[cols['type']].str.upper() == 'RUN').mean() * 100
                intel.append({"Category": "Sequence", "Insight": "Post-Sack Run Resp", "Stat": f"{rate:.0f}%", "Strength": get_stars(rate)})
            
            if intel: st.table(pd.DataFrame(intel))
            
            if cols['motion'] in p_data.columns and cols['p_dir'] in p_data.columns:
                st.divider()
                st.subheader("Motion Correlation Heatmap")
                def check_c(row):
                    m, p = str(row[cols['motion']]).upper(), str(row[cols['p_dir']]).upper()
                    if m[0:1] == p[0:1] and m[0:1] in ['L','R']: return 'With Motion'
                    if m[0:1] != p[0:1] and m[0:1] in ['L','R']: return 'Away from Motion'
                    return 'Static'
                p_data['M_Corr'] = p_data.apply(check_c, axis=1)
                st.dataframe(p_data.groupby(['M_Corr', cols['type']]).size().unstack(fill_value=0).style.background_gradient(cmap='Purples'))

        # --- TAB 5: PIVOT LAB ---
        with tabs[5]:
            st.header("🧪 Custom Pivot Lab")
            row = st.selectbox("Group By:", ['PERSONNEL', cols['form'], cols['dn']])
            res = p_data.groupby(row)[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
            st.dataframe(res.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))

    else:
        st.error(f"Missing required columns: {list(cols.values())}")
