import streamlit as st
import pandas as pd
import re

# --- 1. THE BRAIN: YOUR REFINED LOGIC ---
def process_offensive_logic(formation):
    f = str(formation).upper().strip()
    # A. NUMBERS FIRST check
    match = re.match(r'^(\d)(\d)', f)
    if match:
        pers = f"{match.group(1)}{match.group(2)}"
        raw_name = re.sub(r'^\d{2}\s*', '', f)
    else:
        # B. KEYWORD DECODING (Spread=11, Dubs=10, Heavy=23)
        if any(x in f for x in ["HEAVY", "JUMBO", "BIG"]): pers, raw_name = "23", "PRO/HEAVY"
        elif "EMPTY" in f: pers, raw_name = "00", "EMPTY"
        elif "SPREAD" in f: pers, raw_name = "11", "SPREAD"
        elif "DUBS" in f or "TRIPS" in f: pers, raw_name = "10", "TRIPS" if "TRIPS" in f else "SPREAD"
        elif "ACE" in f: pers, raw_name = "12", "ACE"
        else: pers, raw_name = "11", f 
            
    # C. FAMILY GROUPING
    family = "OTHER"
    if "EMPTY" in raw_name: family = "EMPTY"
    elif any(x in raw_name for x in ["TRIPS", "TREY", "BUNCH", "3X1"]): family = "TRIPS"
    elif any(x in raw_name for x in ["SPREAD", "DUBS", "2X2", "WIDE"]): family = "SPREAD"
    elif any(x in raw_name for x in ["PRO", "I-", "HEAVY", "JUMBO"]): family = "PRO/HEAVY"
    elif "ACE" in raw_name: family = "ACE"
    
    return pers, family

# --- 2. UI SETUP ---
st.set_page_config(page_title="Lancer-Bot Pro", page_icon="🏈", layout="wide")

with st.sidebar:
    st.subheader("🏈 Lancer-Bot v2.32")
    st.write("Metric Profile: **Complete Offensive Report**")
    st.info("Logic: Spread=11 | Dubs=10 | Heavy=23")

st.title("🏈 Complete Offensive Report (Player Ready)")
uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Original Stable Column Mapping [cite: 13, 16, 35]
    cols = {'type': 'PLAY TYPE', 'form': 'OFF FORM', 'gain': 'GN/LS', 
            'dn': 'DN', 'dist': 'DIST', 'odk': 'ODK', 'play': 'OFF PLAY', 'field': 'YARD LN'}
    
    if all(cols[k] in df.columns for k in ['type', 'form', 'gain']):
        df[cols['type']] = df[cols['type']].str.upper().str.strip()
        df[cols['gain']] = pd.to_numeric(df[cols['gain']], errors='coerce').fillna(0)
        
        # Apply Logic
        results = df[cols['form']].apply(lambda x: process_offensive_logic(x))
        df['PERSONNEL'] = [r[0] for r in results]
        df['FAMILY'] = [r[1] for r in results]
        
        # Original Filtering [cite: 10]
        p_data = df[df[cols['type']].isin(['RUN', 'PASS'])].copy()

        tabs = st.tabs(["Formation Usage", "Personnel Matrix", "D&D Matrix", "Explosive Rates", "Field Zones"])

        with tabs[0]: # Formation Usage [cite: 4]
            st.header("Formation Usage")
            f_counts = p_data['FAMILY'].value_counts()
            f_usage = (f_counts / len(p_data) * 100).round(1)
            usage_df = pd.DataFrame({'Plays': f_counts, '% Usage': f_usage})
            st.table(usage_df)

        with tabs[1]: # Personnel Matrix [cite: 10]
            st.header("Run/Pass Distribution by Personnel")
            matrix = p_data.groupby('PERSONNEL')[cols['type']].value_counts().unstack().fillna(0)
            matrix['Run %'] = (matrix['RUN'] / (matrix['RUN'] + matrix['PASS']) * 100).round(0).astype(str) + '%'
            matrix['Pass %'] = (matrix['PASS'] / (matrix['RUN'] + matrix['PASS']) * 100).round(0).astype(str) + '%'
            st.table(matrix)

        with tabs[2]: # Down & Distance Matrix 
            st.header("Down & Distance Run/Pass Matrix")
            # Create situational groupings [cite: 13, 14]
            def get_situation(row):
                d, dist = row[cols['dn']], row[cols['dist']]
                if dist < 4: s = "<4"
                elif 4 <= dist <= 7: s = "4-7"
                else: s = "7+"
                return f"{d} & {s}"
            
            p_data['Situation'] = p_data.apply(get_situation, axis=1)
            dd_matrix = p_data.groupby('Situation')[cols['type']].value_counts().unstack().fillna(0)
            dd_matrix['Run %'] = (dd_matrix['RUN'] / (dd_matrix['RUN'] + dd_matrix['PASS']) * 100).round(0).astype(str) + '%'
            st.table(dd_matrix)

        with tabs[3]: # Explosive Rates [cite: 16, 17]
            st.header("Play Type Productivity")
            exp_run = (p_data[p_data[cols['type']] == 'RUN'][cols['gain']] >= 10).mean() * 100
            exp_pass = (p_data[p_data[cols['type']] == 'PASS'][cols['gain']] >= 20).mean() * 100
            
            c1, c2 = st.columns(2)
            c1.metric("Run Explosive Rate (10+)", f"{exp_run:.0f}%")
            c2.metric("Pass Explosive Rate (20+)", f"{exp_pass:.0f}%")
            
            st.subheader("Avg Gain by Family [cite: 26]")
            st.dataframe(p_data.groupby('FAMILY')[cols['gain']].mean().sort_values(ascending=False).rename("Avg Gain"))

        with tabs[4]: # Field Zones [cite: 34, 35]
            st.header("Field Position Tendencies")
            # Simplified zone logic [cite: 35]
            def get_zone(yd):
                if yd <= 20: return "Own 0-20"
                if 21 <= yd <= 50: return "Own 21-50"
                return "Opp 50-21"
            
            if cols['field'] in df.columns:
                p_data['Zone'] = p_data[cols['field']].apply(get_zone)
                zone_tend = p_data.groupby('Zone')[cols['type']].value_counts().unstack().fillna(0)
                st.table(zone_tend)
    else:
        st.error(f"Required columns missing: {list(cols.values())}")
