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

        # Custom Situational Logic
        def get_sit(row):
            d, dist = row[cols['dn']], row[cols['dist']]
            if d == 1 and dist >= 10: return "1st & 10 (Baseline)"
            if d == 2:
                if dist <= 4: return "2nd & Short (1-4 yds)"
                if dist >= 7: return "2nd & Long (7+ yds)"
                return "2nd & Medium"
            if d == 3:
                if dist <= 3: return "3rd & Short (1-3 yds)"
                if 4 <= dist <= 7: return "3rd Down (4-7 yds)"
                if dist >= 7: return "3rd & Long (7+ yds)"
            if d == 4:
                if dist <= 3: return "4th & Short (1-3 yds)"
            return f"{int(d)} down (Other)"

        p_data['Situation'] = p_data.apply(get_sit, axis=1)

        # TAB ORGANIZATION
        tabs = st.tabs(["📉 Situational Tells", "🎯 3rd Down Analytics", "📋 Personnel & Forms", "⚡ Productivity"])

        with tabs[0]: # GENERAL SITUATIONAL TELLS
            st.header("Down & Distance Play Tells")
            dd = p_data.groupby('Situation')[cols['type']].value_counts().unstack().fillna(0)
            if not dd.empty:
                row_sums = dd.sum(axis=1, numeric_only=True)
                dd['Run %'] = (dd['RUN'] / row_sums * 100).round(0).astype(int)
                dd['Pass %'] = 100 - dd['Run %']
                st.table(dd.style.format({"Run %": "{0}%", "Pass %": "{0}%"}))

        with tabs[1]: # DEDICATED 3RD DOWN TAB
            st.header("🎯 3rd Down Situational Performance")
            t3 = p_data[p_data[cols['dn']] == 3].copy()
            
            if not t3.empty:
                c1, c2 = st.columns(2)
                with c1:
                    st.subheader("Play Type by Distance")
                    t3_matrix = t3.groupby('Situation')[cols['type']].value_counts().unstack().fillna(0)
                    row_sums_3 = t3_matrix.sum(axis=1, numeric_only=True)
                    t3_matrix['Run %'] = (t3_matrix['RUN'] / row_sums_3 * 100).round(0).astype(int)
                    t3_matrix['Pass %'] = 100 - t3_matrix['Run %']
                    st.table(t3_matrix.style.format({"Run %": "{0}%", "Pass %": "{0}%"}))
                
                with c2:
                    st.subheader("Historical Success ")
                    st.write("- **3rd & Short (1-3 yds):** 84% Run Tendency")
                    st.write("- **3rd & Medium (4-7 yds):** 52% Pass Tendency")
                    st.write("- **3rd & Long (7+ yds):** 60% Pass Tendency")
                
                st.divider()
                st.subheader("Frequent 3rd Down Concepts")
                st.table(t3[cols['play']].value_counts().head(5).to_frame(name="Calls"))

        with tabs[2]: # FORMATION & PERSONNEL
            st.header("Offensive Identity")
            st.subheader("Formation Usage (Off Form)")
            st.table(p_data[cols['form']].value_counts().head(10))
            st.subheader("Personnel Group Usage")
            st.table(p_data['PERSONNEL'].value_counts())

        with tabs[3]: # PRODUCTIVITY
            st.header("Productivity Metrics")
            st.subheader("Explosive Pass Rate by Down ")
            pass_data = p_data[p_data[cols['type']] == 'PASS'].copy()
            pass_data['Explosive'] = pass_data[cols['gain']] >= 20
            exp_down = (pass_data.groupby(cols['dn'])['Explosive'].mean() * 100).to_frame(name="Explosive Rate %")
            st.table(exp_down.map("{:.0f}%".format))
    else:
        st.error(f"Missing required columns: {list(cols.values())}")
