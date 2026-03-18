import streamlit as st
import pandas as pd
import re
import os

# --- 1. CORE LOGIC ---
def process_offensive_logic(formation):
    f = str(formation).upper().strip()
    match = re.match(r'^(\d)(\d)', f)
    if match:
        pers = f"{match.group(1)}{match.group(2)}"
    else:
        # Standard Fallback
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

st.title("🏈 Carlsbad Football Analytics")

uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Updated column mapping based on your latest logs
    cols = {'type': 'PLAY TYPE', 'form': 'OFF FORM', 'gain': 'GN/LS', 
            'dn': 'DN', 'dist': 'DIST', 'play': 'OFF PLAY', 'field': 'YARD LN'}
    
    if all(cols[k] in df.columns for k in ['type', 'form', 'gain']):
        df[cols['type']] = df[cols['type']].str.upper().str.strip()
        df[cols['gain']] = pd.to_numeric(df[cols['gain']], errors='coerce').fillna(0)
        df['PERSONNEL'] = df[cols['form']].apply(process_offensive_logic)
        p_data = df[df[cols['type']].isin(['RUN', 'PASS'])].copy()

        # Tabs Foundation
        tabs = st.tabs([
            "📊 Personnel/Formations", "🎯 3rd Down", "📈 Frequency & patterns", 
            "📍 Field position", "🟢 Red/Green Zone", "🔥 First drive patterns", "🧪 Custom Pivot Lab"
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
            st.header("3rd Down Strategy & Success")
            t3 = p_data[p_data[cols['dn']] == 3].copy()
            t3['Sit'] = t3[cols['dist']].apply(lambda x: "3rd & Short (1-3)" if x <= 3 else ("3rd & Mid (4-7)" if x <= 7 else "3rd & Long (7+)"))
            t3_res = t3.groupby('Sit')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
            st.dataframe(t3_res.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
            st.subheader("Play Types by Yards to Go")
            st.table(t3.groupby(['Sit', cols['play']]).size().unstack(fill_value=0))

        with tabs[2]: # FREQUENCY & PATTERNS
            st.header("Play Call Patterns & Explosives")
            col_r, col_p = st.columns(2)
            with col_r:
                st.subheader("Frequent Runs")
                st.table(p_data[p_data[cols['type']]=='RUN'][cols['play']].value_counts().head(5))
            with col_p:
                st.subheader("Frequent Passes")
                st.table(p_data[p_data[cols['type']]=='PASS'][cols['play']].value_counts().head(5))
            st.divider()
            st.subheader("Explosive Plays (20+ Pass, 10+ Run)")
            er = (p_data[p_data[cols['type']] == 'RUN'][cols['gain']] >= 10).mean() * 100
            ep = (p_data[p_data[cols['type']] == 'PASS'][cols['gain']] >= 20).mean() * 100
            st.write(f"Run Explosive Rate: **{er:.1f}%** | Pass Explosive Rate: **{ep:.1f}%**")

        with tabs[3]: # FIELD POSITION
            st.header("Field Position Tendencies")
            def get_zone(yd):
                if yd <= 20: return "0-20 (Own)"
                if yd <= 50: return "21-50 (Midfield)"
                return "49-21 (Opponent)"
            p_data['Zone'] = p_data[cols['field']].apply(get_zone)
            z_res = p_data.groupby('Zone')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
            st.dataframe(z_res.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))

        with tabs[4]: # RED/GREEN ZONE
            st.header("Red & Green Zone Analytics")
            # Logic: Red Zone is 20 to 11 yard line. Green Zone is inside 10
            # Assuming Hudl "YARD LN" represents distance from goal line in this logic
            rg_data = p_data[p_data[cols['field']] <= 20].copy()
            if not rg_data.empty:
                rg_data['RG_Zone'] = rg_data[cols['field']].apply(lambda x: "🟢 Green Zone (Inside 10)" if x <= 10 else "🔴 Red Zone (20-11)")
                
                st.subheader("Zone Personnel")
                st.table(rg_data.groupby('RG_Zone')['PERSONNEL'].value_counts().unstack(fill_value=0))
                
                st.subheader("Play Types by Yards to Go")
                st_res = rg_data.groupby(['RG_Zone', cols['type']]).size().unstack(fill_value=0)
                st.dataframe(st_res)

                st.subheader("Specific Plays")
                st.table(rg_data.groupby(['RG_Zone', cols['play']]).size().unstack(fill_value=0))
            else:
                st.info("No plays detected inside the 20-yard line.")

        with tabs[5]: # FIRST DRIVE
            st.header("First Drive Tendencies/Patterns")
            # Handle missing 'SERIES' column from logs
            if 'SERIES' in df.columns:
                first = p_data[p_data['SERIES'] == 1]
                if not first.empty:
                    st.write(f"Opening Drive Play-call Pattern:")
                    st.table(first[[cols['dn'], cols['dist'], cols['play'], cols['gain']]])
                else:
                    st.info("First series data not found.")
            else:
                st.warning("Series tracking ('SERIES' column) not found in the uploaded file.")

        with tabs[6]: # CUSTOM PIVOT LAB
            st.header("🧪 Custom Pivot Lab")
            row_choice = st.selectbox("Group By Selection:", ['RG_Zone' if 'RG_Zone' in p_data.columns else 'Zone', 'PERSONNEL', cols['form'], cols['dn']])
            metric = st.radio("Metric:", ['Run/Pass %', 'Average Gain'])
            if metric == 'Run/Pass %':
                res = p_data.groupby(row_choice)[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
                st.dataframe(res.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
            else:
                # FIXED: Converted Series to Dataframe for .style
                res = p_data.groupby(row_choice)[cols['gain']].mean().to_frame(name="Avg Gain")
                st.dataframe(res.style.background_gradient(cmap='Greens').format("{:.1f} yds"))
    else:
        st.error(f"Missing required columns: {list(cols.values())}")
