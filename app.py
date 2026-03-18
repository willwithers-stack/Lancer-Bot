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
    # Robust Logo Search
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
    st.caption("v2.66 Metric Recovery")

st.title("🏈 Carlsbad Football Analytics")

uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = [str(c).strip() for c in df.columns]
    
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
        
        # --- STABLE DRIVE DETECTION ---
        st_keywords = ['PUNT', 'FG', 'KICK', 'PAT', 'FIELD GOAL']
        df['Is_ST'] = df[cols['type']].apply(lambda x: any(kw in x for kw in st_keywords))
        df['Drive_ID'] = ((df[cols['odk']] != df[cols['odk']].shift()) | (df['Is_ST'] == True)).cumsum()
        
        p_data = df[df[cols['type']].isin(['RUN', 'PASS'])].copy()

        tabs = st.tabs([
            "📊 Personnel/Formations", "🎯 3rd Down", "📈 Frequency & Patterns", 
            "📍 Field Position", "🟢 Red/Green Zone", "🔮 Potpourri & AI", "🧪 Pivot Lab"
        ])

        with tabs[0]: # PERSONNEL/FORMATIONS
            st.header("Formation & Personnel Identity")
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Top 5 Formations Usage")
                f_top = p_data[cols['form']].value_counts().head(5).index
                f_res = p_data[p_data[cols['form']].isin(f_top)].groupby(cols['form'])[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
                st.dataframe(f_res.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
            with c2:
                st.subheader("Top 5 Personnel")
                p_top = p_data['PERSONNEL'].value_counts().head(5).index
                p_res = p_data[p_data['PERSONNEL'].isin(p_top)].groupby('PERSONNEL')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
                st.dataframe(p_res.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))

        with tabs[1]: # 3RD DOWN
            st.header("3rd Down Strategy")
            t3 = p_data[p_data[cols['dn']] == 3].copy()
            t3['Sit'] = t3[cols['dist']].apply(lambda x: "3rd & Short (1-3)" if x <= 3 else ("3rd & Mid (4-7)" if x <= 7 else "3rd & Long (7+)"))
            t3_res = t3.groupby('Sit')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
            st.dataframe(t3_res.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))

        with tabs[2]: # FREQUENCY & PATTERNS
            st.header("Play Frequency & Explosives")
            p_data['Explosive'] = np.where(
                (p_data[cols['type']] == 'RUN') & (p_data[cols['gain']] >= 10), True,
                np.where((p_data[cols['type']] == 'PASS') & (p_data[cols['gain']] >= 20), True, False)
            )
            # Restored Actual Play Names for Explosives
            st.subheader("Recent Explosive Plays")
            st.table(p_data[p_data['Explosive'] == True][[cols['dn'], cols['dist'], cols['play'], cols['gain']]].sort_values(by=cols['gain'], ascending=False).head(5))
            
            st.subheader("Explosive Rate by Down")
            exp_table = p_data.groupby([cols['dn'], cols['type']], as_index=False)['Explosive'].mean()
            exp_pivot = exp_table.pivot(index=cols['dn'], columns=cols['type'], values='Explosive').mul(100)
            st.dataframe(exp_pivot.style.background_gradient(cmap='Greens').format("{:.1f}%"))

        with tabs[5]: # POTPOURRI & AI
            st.header("🤖 AI Scouting Intelligence")
            intel_data = []
            
            # Post-Sack Response
            sacks = p_data[(p_data[cols['type']] == 'PASS') & (p_data[cols['gain']] <= -4)].index
            post_sack = p_data.loc[[i+1 for i in sacks if i+1 in p_data.index]]
            if not post_sack.empty:
                run_resp = (post_sack[cols['type']] == 'RUN').mean() * 100
                intel_data.append({"Category": "Sequence", "Insight": "Post-Sack Run Resp", "Stat": f"{run_resp:.0f}%", "Strength": get_stars(run_resp)})

            # Mid-Field Tendency
            mid = p_data[(p_data[cols['field']] >= 21) & (p_data[cols['field']] <= 50)]
            if not mid.empty:
                rate = (mid[cols['type']] == 'RUN').mean() * 100
                intel_data.append({"Category": "Zone", "Insight": "Mid-Field Run", "Stat": f"{rate:.0f}%", "Strength": get_stars(rate)})

            if intel_data:
                st.table(pd.DataFrame(intel_data))

        with tabs[6]: # PIVOT LAB
            st.header("🧪 Custom Pivot Lab")
            row_choice = st.selectbox("Group By:", ['PERSONNEL', cols['form'], cols['dn']])
            metric = st.radio("Metric:", ['Run/Pass %', 'Average Gain'])
            if metric == 'Run/Pass %':
                res = p_data.groupby(row_choice)[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
                st.dataframe(res.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
            else:
                res = p_data.groupby(row_choice)[cols['gain']].mean().to_frame(name="Avg Gain")
                st.dataframe(res.style.background_gradient(cmap='Greens').format("{:.1f} yds"))
    else:
        st.error(f"Missing required columns: {list(cols.values())}")
