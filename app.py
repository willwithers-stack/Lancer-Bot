import streamlit as st
import pandas as pd
import re

# --- 1. CORE LOGIC: PERSONNEL FIRST ---
def process_offensive_logic(formation):
    f = str(formation).upper().strip()
    # Prioritize numbers at start (e.g., "20 Wing", "11 Spread")
    match = re.match(r'^(\d)(\d)', f)
    if match:
        pers = f"{match.group(1)}{match.group(2)}"
    else:
        # Fallback keyword mapping
        if any(x in f for x in ["HEAVY", "JUMBO", "BIG"]): pers = "23"
        elif "EMPTY" in f: pers = "00"
        elif "DUBS" in f or "TRIPS" in f: pers = "10"
        elif "SPREAD" in f or "WING" in f: pers = "11"
        elif "ACE" in f: pers = "12"
        else: pers = "11"
    return pers

# --- 2. UI SETUP ---
st.set_page_config(page_title="Carlsbad Football Analytics", page_icon="🏈", layout="wide")

# Sidebar - Logo Only
with st.sidebar:
    try:
        st.image("logo.png") # Pulls from Github root
    except:
        st.subheader("🏈 CARLSBAD FOOTBALL")

st.title("🏈 Carlsbad Football Analytics")
st.subheader("Complete Offensive Report (Player Ready)")

uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = [str(c).strip() for c in df.columns]
    
    cols = {'type': 'PLAY TYPE', 'form': 'OFF FORM', 'gain': 'GN/LS', 
            'dn': 'DN', 'dist': 'DIST', 'play': 'OFF PLAY'}
    
    if all(cols[k] in df.columns for k in ['type', 'form', 'gain']):
        df[cols['type']] = df[cols['type']].str.upper().str.strip()
        df[cols['gain']] = pd.to_numeric(df[cols['gain']], errors='coerce').fillna(0)
        df['PERSONNEL'] = df[cols['form']].apply(process_offensive_logic)
        p_data = df[df[cols['type']].isin(['RUN', 'PASS'])].copy()

        tabs = st.tabs(["📋 Personnel Usage", "📈 Situational Matrix", "⚡ Productivity & Alerts", "🧪 Pivot Lab"])

        with tabs[0]: # PERSONNEL USAGE
            st.header("Personnel Group Usage")
            p_counts = p_data['PERSONNEL'].value_counts()
            p_usage = pd.DataFrame({
                'Plays': p_counts, 
                '% Usage': (p_counts / len(p_data) * 100).round(0).astype(str) + '%'
            })
            st.table(p_usage)
            st.info("Two-back sets make up more than half of all snaps.")

        with tabs[1]: # DISTRIBUTIONS
            st.header("Run/Pass Distribution")
            matrix = p_data.groupby('PERSONNEL')[cols['type']].value_counts().unstack().fillna(0)
            if not matrix.empty:
                # FIXED: numeric_only=True added to prevent TypeError
                matrix['Run %'] = (matrix['RUN'] / matrix.sum(axis=1, numeric_only=True) * 100).round(0).astype(int)
                matrix['Pass %'] = (matrix['PASS'] / matrix.sum(axis=1, numeric_only=True) * 100).round(0).astype(int)
                st.table(matrix.style.format({"Run %": "{0}%", "Pass %": "{0}%"}))

            st.subheader("Down & Distance Matrix")
            def get_sit(row):
                d, dist = row[cols['dn']], row[cols['dist']]
                s = "<4" if dist < 4 else "4-7" if dist <= 7 else "7+"
                return f"{int(d)}st & {s}" if d==1 else f"{int(d)}nd & {s}" if d==2 else f"{int(d)}rd & {s}"
            p_data['Situation'] = p_data.apply(get_sit, axis=1)
            dd = p_data.groupby('Situation')[cols['type']].value_counts().unstack().fillna(0)
            if not dd.empty:
                # FIXED: numeric_only=True added to prevent TypeError
                dd['Total'] = dd.sum(axis=1, numeric_only=True).astype(int)
                st.table(dd)

        with tabs[2]: # PRODUCTIVITY & ALERTS
            st.header("Tendency Alerts (70% Threshold)")
            if not matrix.empty:
                for pers, row in matrix.iterrows():
                    if row['Run %'] >= 70:
                        st.error(f"⚠️ **{pers} Personnel**: High Run Tendency ({row['Run %']}%)")
                    elif row['Pass %'] >= 70:
                        st.warning(f"⚠️ **{pers} Personnel**: High Pass Tendency ({row['Pass %']}%)")

            st.divider()
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Avg Gain")
                st.table(p_data.groupby(cols['type'])[cols['gain']].mean().map("{:.1f} yds".format))
            with c2:
                st.subheader("Explosive Rate")
                er = (p_data[p_data[cols['type']] == 'RUN'][cols['gain']] >= 10).mean() * 100
                ep = (p_data[p_data[cols['type']] == 'PASS'][cols['gain']] >= 20).mean() * 100
                st.write(f"Run (10+ yds): **{er:.0f}%**")
                st.write(f"Pass (20+ yds): **{ep:.0f}%**")

        with tabs[3]: # PIVOT LAB
            st.header("🧪 Personnel Pivot Lab")
            row_choice = st.selectbox("Group By:", [cols['dn'], 'Situation', cols['play']])
            metric = st.radio("Metric:", ['Run/Pass %', 'Average Gain'])
            
            if metric == 'Run/Pass %':
                res = p_data.groupby(['PERSONNEL', row_choice])[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
                st.dataframe(res.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
            else:
                # FIXED: Converted Series to Dataframe to allow styling
                res = p_data.groupby(['PERSONNEL', row_choice])[cols['gain']].mean().to_frame(name="Avg Gain")
                st.dataframe(res.style.background_gradient(cmap='Greens').format("{:.1f} yds"))
    else:
        st.error(f"Missing required columns: {list(cols.values())}")
