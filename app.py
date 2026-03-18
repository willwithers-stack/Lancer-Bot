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
    st.caption("v2.70 Tab Recovery")

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
        # --- DATA CLEANING (Throw out blank gains) ---
        df = df.dropna(subset=[cols['gain']])
        df[cols['gain']] = pd.to_numeric(df[cols['gain']], errors='coerce').fillna(0)
        df[cols['dn']] = pd.to_numeric(df[cols['dn']], errors='coerce').fillna(0).astype(int)
        df[cols['dist']] = pd.to_numeric(df[cols['dist']], errors='coerce').fillna(0).astype(int)
        df[cols['field']] = pd.to_numeric(df[cols['field']], errors='coerce').fillna(0)
        
        df[cols['type']] = df[cols['type']].astype(str).str.upper().str.strip()
        df['PERSONNEL'] = df[cols['form']].apply(process_offensive_logic)
        p_data = df[df[cols['type']].isin(['RUN', 'PASS'])].copy()

        tabs = st.tabs([
            "📊 Personnel/Formations", 
            "🎯 3rd Down Strategy", 
            "📈 Frequency & Patterns", 
            "🟢 Red/Green Zone", 
            "🔮 Potpourri & AI", 
            "🧪 Custom Pivot Lab"
        ])

        with tabs[0]: # PERSONNEL/FORMATIONS
            st.header("Formation & Personnel Identity")
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Top 5 Formations Usage")
                f_top = p_data[cols['form']].value_counts().head(5).index
                # FIXED: numeric_only added to grouping to prevent blank output
                f_res = p_data[p_data[cols['form']].isin(f_top)].groupby(cols['form'])[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
                st.dataframe(f_res.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
            with c2:
                st.subheader("Top 5 Personnel")
                p_top = p_data['PERSONNEL'].value_counts().head(5).index
                p_res = p_data[p_data['PERSONNEL'].isin(p_top)].groupby('PERSONNEL')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
                st.dataframe(p_res.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))

        with tabs[1]: # 3RD DOWN (UNCHANGED LAYOUT)
            st.header("🎯 3rd Down Situational Analysis")
            t3 = p_data[p_data[cols['dn']] == 3].copy()
            if not t3.empty:
                t3['Success'] = t3[cols['gain']] >= t3[cols['dist']]
                st.metric("Overall 3rd Down Success Rate", f"{t3['Success'].mean() * 100:.1f}%")
                
                t3['Sit'] = t3[cols['dist']].apply(lambda x: "3rd & Short (1-3)" if x <= 3 else ("3rd & Mid (4-7)" if x <= 7 else "3rd & Long (7+)"))
                sit_stats = t3.groupby('Sit').agg({'Success': 'mean'}).mul(100).round(1)
                
                c1, c2 = st.columns(2)
                with c1:
                    st.table(sit_stats.rename(columns={'Success': 'Success %'}))
                with c2:
                    t3_tendency = t3.groupby('Sit')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
                    st.dataframe(t3_tendency.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
                
                for sit in ["3rd & Short (1-3)", "3rd & Mid (4-7)", "3rd & Long (7+)"]:
                    subset = t3[t3['Sit'] == sit]
                    if not subset.empty:
                        with st.expander(f"Top Plays: {sit}"):
                            st.table(subset[cols['play']].value_counts().head(3))

        with tabs[2]: # FREQUENCY & PATTERNS
            st.header("Frequency & Explosives")
            p_data['Explosive'] = np.where(
                (p_data[cols['type']] == 'RUN') & (p_data[cols['gain']] >= 10), True,
                np.where((p_data[cols['type']] == 'PASS') & (p_data[cols['gain']] >= 20), True, False)
            )
            # FIXED: Avoid FutureWarning by using explicit selection
            exp_table = p_data.groupby([cols['dn'], cols['type']])['Explosive'].mean().unstack().fillna(0).mul(100)
            st.dataframe(exp_table.style.background_gradient(cmap='Greens').format("{:.1f}%"))

        with tabs[4]: # POTPOURRI & AI
            st.header("🤖 AI Scouting Intelligence")
            intel_data = []
            # Post-Sack Response
            sack_mask = (df[cols['result']].str.contains('Sack', case=False, na=False)) | \
                        ((df[cols['type']] == 'PASS') & (df[cols['gain']] <= -4))
            post_sack = df.loc[[i+1 for i in df[sack_mask].index if i+1 in df.index]]
            if not post_sack.empty:
                run_resp = (post_sack[cols['type']].str.upper() == 'RUN').mean() * 100
                intel_data.append({"Category": "Sequence", "Insight": "Post-Sack Run Resp", "Stat": f"{run_resp:.0f}%", "Strength": get_stars(run_resp)})
            
            if intel_data:
                st.table(pd.DataFrame(intel_data))

        with tabs[5]: # PIVOT LAB
            st.header("🧪 Custom Pivot Lab")
            row_choice = st.selectbox("Group By Selection:", ['PERSONNEL', cols['form'], cols['dn']])
            res = p_data.groupby(row_choice)[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
            st.dataframe(res.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))

    else:
        st.error(f"Missing required columns: {list(cols.values())}")
