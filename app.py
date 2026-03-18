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
    # Handle Case Sensitivity: Logo.png vs logo.png
    logo_files = ["Logo.png", "logo.png"]
    found_logo = False
    for lf in logo_files:
        if os.path.exists(lf):
            st.image(lf, width=200)
            found_logo = True
            break
    if not found_logo:
        st.subheader("🏈 CARLSBAD FOOTBALL")
    st.write("---")
    st.write("Logic: Explosives (Run 10+ / Pass 20+)")

st.title("🏈 Carlsbad Football Analytics")

uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Identify Play Number Column (Hudl defaults)
    play_no_col = next((c for c in df.columns if c.upper() in ['PLAY #', 'PL #', 'PLAY NO']), None)
    
    cols = {'type': 'PLAY TYPE', 'form': 'OFF FORM', 'gain': 'GN/LS', 
            'dn': 'DN', 'dist': 'DIST', 'play': 'OFF PLAY', 'field': 'YARD LN', 'odk': 'ODK'}
    
    if all(cols[k] in df.columns for k in ['type', 'form', 'gain']):
        # Clean Data
        df[cols['type']] = df[cols['type']].str.upper().str.strip()
        df[cols['gain']] = pd.to_numeric(df[cols['gain']], errors='coerce').fillna(0)
        df['PERSONNEL'] = df[cols['form']].apply(process_offensive_logic)
        
        # --- FIRST DRIVE DETECTION LOGIC ---
        # Detect Game Resets (e.g., 123 -> 2)
        if play_no_col:
            df[play_no_col] = pd.to_numeric(df[play_no_col], errors='coerce').fillna(0)
            # A new game starts if the play number drops significantly
            df['Game_ID'] = (df[play_no_col].diff() < -10).cumsum()
        else:
            df['Game_ID'] = 0

        # Define 'OFF' plays and detect the first drive of each game
        p_data = df[df[cols['type']].isin(['RUN', 'PASS'])].copy()
        
        # Use SERIES if it exists, otherwise use ODK transitions to identify drives
        if 'SERIES' in df.columns:
            p_data['Drive_ID'] = p_data['SERIES']
        else:
            # Group by Game and count transitions in ODK as a proxy for drives
            p_data['Drive_ID'] = (p_data[cols['odk']] != p_data[cols['odk']].shift()).cumsum()

        # Identify First Drive plays (smallest Drive_ID for each Game_ID)
        first_drive_plays = p_data.groupby('Game_ID').apply(lambda x: x[x['Drive_ID'] == x['Drive_ID'].min()]).reset_index(drop=True)

        # TABS
        tabs = st.tabs([
            "📊 Personnel/Formations", "🎯 3rd Down", "📈 Frequency & Patterns", 
            "📍 Field Position", "🟢 Red/Green Zone", "🔥 First Drives", "🧪 Pivot Lab"
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
                st.subheader("Top 5 Personnel Breakout")
                p_top = p_data['PERSONNEL'].value_counts().head(5).index
                p_res = p_data[p_data['PERSONNEL'].isin(p_top)].groupby('PERSONNEL')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
                st.dataframe(p_res.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))

        with tabs[1]: # 3RD DOWN
            st.header("3rd Down Strategy")
            t3 = p_data[p_data[cols['dn']] == 3].copy()
            t3['Sit'] = t3[cols['dist']].apply(lambda x: "3rd & Short (1-3)" if x <= 3 else ("3rd & Mid (4-7)" if x <= 7 else "3rd & Long (7+)"))
            t3_res = t3.groupby('Sit')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
            st.dataframe(t3_res.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
            st.subheader("Specific Plays by Distance")
            st.table(t3.groupby(['Sit', cols['play']]).size().unstack(fill_value=0))

        with tabs[2]: # FREQUENCY & PATTERNS
            st.header("Play Frequency & Explosives")
            c_freq1, c_freq2 = st.columns(2)
            with c_freq1:
                st.subheader("Most Frequent Runs")
                st.table(p_data[p_data[cols['type']]=='RUN'][cols['play']].value_counts().head(10))
            with c_freq2:
                st.subheader("Most Frequent Passes")
                st.table(p_data[p_data[cols['type']]=='PASS'][cols['play']].value_counts().head(10))
            
            st.divider()
            st.subheader("Explosive Plays by Down")
            p_data['Explosive'] = np.where(
                (p_data[cols['type']] == 'RUN') & (p_data[cols['gain']] >= 10), True,
                np.where((p_data[cols['type']] == 'PASS') & (p_data[cols['gain']] >= 20), True, False)
            )
            exp_table = p_data.groupby([cols['dn'], cols['type']])['Explosive'].mean().unstack().mul(100)
            st.dataframe(exp_table.style.background_gradient(cmap='Greens').format("{:.1f}%"))

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
            # Red Zone (20-11), Green Zone (Inside 10)
            rg_data = p_data[p_data[cols['field']] <= 20].copy()
            if not rg_data.empty:
                rg_data['RG_Zone'] = rg_data[cols['field']].apply(lambda x: "🟢 Green Zone (<10)" if x <= 10 else "🔴 Red Zone (20-11)")
                st.subheader("Zone Tendencies")
                st.dataframe(rg_data.groupby('RG_Zone')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100).style.format("{:.0f}%"))
                st.subheader("Plays Inside the 20")
                st.table(rg_data.groupby(['RG_Zone', cols['play']]).size().unstack(fill_value=0))
            else:
                st.info("No plays detected inside the opponent's 20-yard line.")

        with tabs[5]: # FIRST DRIVES
            st.header("First Drive Tendencies")
            if not first_drive_plays.empty:
                for game_id in first_drive_plays['Game_ID'].unique():
                    st.subheader(f"Game {int(game_id) + 1} Opening Drive")
                    game_drive = first_drive_plays[first_drive_plays['Game_ID'] == game_id]
                    st.table(game_drive[[cols['dn'], cols['dist'], cols['play'], cols['gain']]])
            else:
                st.info("No drive data detected via play sequence.")

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
    else:
        st.error(f"Missing required columns: {list(cols.values())}")
