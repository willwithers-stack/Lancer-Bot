import streamlit as st
import pandas as pd
import re

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
        elif "SPREAD" in f or "WING" in f: pers = "11"
        elif "ACE" in f: pers = "12"
        else: pers = "11"
    return pers

# --- 2. UI SETUP ---
st.set_page_config(page_title="Carlsbad Football Analytics", page_icon="🏈", layout="wide")

with st.sidebar:
    try:
        st.image("logo.png") 
    except:
        st.subheader("🏈 CARLSBAD FOOTBALL")

st.title("🏈 Carlsbad Football Analytics")

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

        tabs = st.tabs(["📉 Situational Tells", "📋 Personnel Usage", "⚡ Productivity", "🧪 Pivot Lab"])

        with tabs[0]: # SITUATIONAL TELLS
            st.header("Down & Distance Play Tells")
            
            # Custom Situational Logic
            def get_sit(row):
                d, dist = row[cols['dn']], row[cols['dist']]
                if d == 1 and dist >= 10: return "1st & 10 (Baseline)"
                if d == 2:
                    if dist <= 4: return "2nd & Short (1-4 yds)"
                    if dist >= 7: return "2nd & Long (7+ yds)"
                    return "2nd & Medium (5-6 yds)"
                if d == 3:
                    if dist <= 3: return "3rd & Short (1-3 yds)"
                    if dist >= 7: return "3rd & Long (7+ yds)"
                    return "3rd & Medium (4-6 yds)"
                if d == 4:
                    if dist <= 3: return "4th & Short (1-3 yds)"
                    return "4th & Long (4+ yds)"
                return f"{int(d)} down (Other)"

            p_data['Situation'] = p_data.apply(get_sit, axis=1)
            dd = p_data.groupby('Situation')[cols['type']].value_counts().unstack().fillna(0)
            
            if not dd.empty:
                # Ensure 100% Distribution
                # numeric_only=True added to prevent mixed-type addition errors
                row_sums = dd.sum(axis=1, numeric_only=True)
                dd['Run %'] = (dd['RUN'] / row_sums * 100).round(0).astype(int)
                dd['Pass %'] = 100 - dd['Run %'] # Guarantees 100% total
                dd['Total Plays'] = row_sums.astype(int)
                
                st.table(dd.style.format({"Run %": "{0}%", "Pass %": "{0}%"}))
                
                st.info("""
                **Analytics Baseline:** * 1st & 10 success is defined as a 4-6 yard gain.  
                * 2nd & Short (1-4) is high-efficiency for two-down planning.  
                * 3rd & Short (1-3) carries high conversion probability for runs.
                """)

        with tabs[1]: # PERSONNEL USAGE
            st.header("Personnel Group Usage")
            matrix = p_data.groupby('PERSONNEL')[cols['type']].value_counts().unstack().fillna(0)
            if not matrix.empty:
                p_sums = matrix.sum(axis=1, numeric_only=True)
                matrix['Run %'] = (matrix['RUN'] / p_sums * 100).round(0).astype(int)
                matrix['Pass %'] = 100 - matrix['Run %']
                st.table(matrix.style.format({"Run %": "{0}%", "Pass %": "{0}%"}))

        with tabs[2]: # PRODUCTIVITY
            st.header("Productivity & Explosives")
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
            row_choice = st.selectbox("Group By:", ['Situation', cols['play']])
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
