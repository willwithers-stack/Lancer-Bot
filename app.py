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
    st.caption("v2.60 Sequence Analysis")

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
        
        # Game/Session Detection (Play # resets)
        if play_no_col:
            df[play_no_col] = pd.to_numeric(df[play_no_col], errors='coerce').fillna(0)
            df['Game_ID'] = (df[play_no_col].diff() < -10).cumsum()
        else:
            df['Game_ID'] = 0

        # --- DRIVE DETECTION (Including Special Teams as Markers) ---
        # Identify non-offensive markers
        st_keywords = ['PUNT', 'FG', 'KICK', 'PAT', 'FIELD GOAL']
        df['Is_ST'] = df[cols['type']].apply(lambda x: any(kw in x for kw in st_keywords))
        
        # Drive ID: Increments on ODK change OR Special Teams play
        df['Drive_ID'] = ((df[cols['odk']] != df[cols['odk']].shift()) | (df['Is_ST'] == True)).cumsum()

        # p_data for offensive analysis (but markers helped set the IDs)
        p_data = df[df[cols['type']].isin(['RUN', 'PASS'])].copy()

        tabs = st.tabs([
            "📊 Personnel/Formations", "🎯 3rd Down", "📈 Frequency & Patterns", 
            "📍 Field Position", "🟢 Red/Green Zone", "🔮 Potpourri", "🧪 Pivot Lab", "🔥 First Drives"
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
            st.subheader("3rd Down Concepts")
            st.table(t3.groupby(['Sit', cols['play']]).size().unstack(fill_value=0))

        with tabs[2]: # FREQUENCY & PATTERNS
            st.header("Frequency & Explosives")
            p_data['Explosive'] = np.where(
                (p_data[cols['type']] == 'RUN') & (p_data[cols['gain']] >= 10), True,
                np.where((p_data[cols['type']] == 'PASS') & (p_data[cols['gain']] >= 20), True, False)
            )
            c_exp1, c_exp2 = st.columns([1, 2])
            with c_exp1:
                st.write("**Explosive Rate by Down**")
                exp_table = p_data.groupby([cols['dn'], cols['type']])['Explosive'].mean().unstack().mul(100)
                st.dataframe(exp_table.style.background_gradient(cmap='Greens').format("{:.1f}%"))
            with c_exp2:
                st.write("**Top Explosive Plays**")
                st.table(p_data[p_data['Explosive'] == True][[cols['dn'], cols['dist'], cols['play'], cols['gain']]].sort_values(by=cols['gain'], ascending=False).head(10))

        with tabs[3]: # FIELD POSITION
            st.header("Field Zone Tendencies")
            def get_zone(yd):
                if yd <= 20: return "0-20 (Own)"
                if yd <= 50: return "21-50 (Midfield)"
                return "49-21 (Opponent)"
            p_data['Zone'] = p_data[cols['field']].apply(get_zone)
            z_res = p_data.groupby('Zone')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
            st.dataframe(z_res.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))

        with tabs[4]: # RED/GREEN ZONE
            st.header("Red & Green Zone Analytics")
            rg_data = p_data[p_data[cols['field']] <= 20].copy()
            if not rg_data.empty:
                rg_data['RG_Zone'] = rg_data[cols['field']].apply(lambda x: "🟢 Green Zone (<10)" if x <= 10 else "🔴 Red Zone (20-11)")
                st.table(rg_data.groupby(['RG_Zone', cols['play']]).size().unstack(fill_value=0))
            else:
                st.info("No plays detected inside the opponent's 20.")

        with tabs[5]: # POTPOURRI
            st.header("🔮 Potpourri: Sequence & Hash Analysis")
            
            # Sequence Analysis (3-5 Play Patterns)
            st.subheader("Offensive Play Sequences (3-Play Windows)")
            sequences = []
            for (g_id, d_id), group in p_data.groupby(['Game_ID', 'Drive_ID']):
                types = group[cols['type']].tolist()
                if len(types) >= 3:
                    for i in range(len(types)-2):
                        sequences.append("-".join(types[i:i+3]))
            
            if sequences:
                seq_counts = pd.Series(sequences).value_counts().head(10).to_frame(name="Occurrences")
                st.table(seq_counts)
                st.caption("Common patterns: RUN-RUN-PASS, RUN-PASS-RUN, etc.")
            
            # Hash & Side Tendencies
            if cols['hash'] in p_data.columns and cols['p_dir'] in p_data.columns:
                st.subheader("Boundary vs Field Tendencies")
                def identify_side(row):
                    h, d = str(row[cols['hash']]).upper(), str(row[cols['p_dir']]).upper()
                    if h == 'L' and d == 'R': return 'Field'
                    if h == 'L' and d == 'L': return 'Boundary'
                    if h == 'R' and d == 'L': return 'Field'
                    if h == 'R' and d == 'R': return 'Boundary'
                    return 'Middle'
                p_data['Side'] = p_data.apply(identify_side, axis=1)
                st.dataframe(p_data[p_data['Side'] != 'Middle'].groupby([cols['hash'], 'Side']).size().unstack(fill_value=0))

            # Motion Correlation
            if cols['motion'] in p_data.columns and cols['p_dir'] in p_data.columns:
                st.subheader("Motion Direction & Play Direction")
                st.dataframe(p_data.groupby([cols['motion'], cols['p_dir']]).size().unstack(fill_value=0).style.background_gradient(cmap='Purples'))

        with tabs[6]: # PIVOT LAB
            st.header("🧪 Custom Pivot Lab")
            row_choice = st.selectbox("Group By:", ['PERSONNEL', cols['form'], cols['dn'], 'Zone'])
            metric = st.radio("Metric:", ['Run/Pass %', 'Average Gain'])
            if metric == 'Run/Pass %':
                res = p_data.groupby(row_choice)[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
                st.dataframe(res.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
            else:
                res = p_data.groupby(row_choice)[cols['gain']].mean().to_frame(name="Avg Gain")
                st.dataframe(res.style.background_gradient(cmap='Greens').format("{:.1f} yds"))

        with tabs[7]: # FIRST DRIVES
            st.header("🔥 First Drive Analysis")
            first_drive_plays = p_data.groupby('Game_ID').apply(lambda x: x[x['Drive_ID'] == x['Drive_ID'].min()]).reset_index(drop=True)
            if not first_drive_plays.empty:
                for gid in first_drive_plays['Game_ID'].unique():
                    st.subheader(f"Game {int(gid) + 1} Opening Drive")
                    st.table(first_drive_plays[first_drive_plays['Game_ID'] == gid][[cols['dn'], cols['dist'], cols['play'], cols['gain']]])

    else:
        st.error(f"Missing required columns: {list(cols.values())}")
