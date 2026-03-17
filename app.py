import streamlit as st
import pandas as pd
import re

# --- 1. THE BRAIN: YOUR REFINED LOGIC ---
def process_offensive_logic(formation):
    f = str(formation).upper().strip()
    match = re.match(r'^(\d)(\d)', f)
    if match:
        pers = f"{match.group(1)}{match.group(2)}"
        raw_name = re.sub(r'^\d{2}\s*', '', f)
    else:
        if any(x in f for x in ["HEAVY", "JUMBO", "BIG"]): pers, raw_name = "23", "PRO/HEAVY"
        elif "EMPTY" in f: pers, raw_name = "00", "EMPTY"
        elif "SPREAD" in f: pers, raw_name = "11", "SPREAD"
        elif "DUBS" in f or "TRIPS" in f: pers, raw_name = "10", "TRIPS" if "TRIPS" in f else "SPREAD"
        elif "ACE" in f: pers, raw_name = "12", "ACE"
        else: pers, raw_name = "11", f 
            
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
    st.subheader("🏈 Lancer-Bot v2.33")
    st.write("Metric Profile: **PDF Replica**")
    st.info("Logic: Spread=11 | Dubs=10 | Heavy=23")

st.title("🏈 Complete Offensive Report (Player Ready)")
uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = [str(c).strip() for c in df.columns]
    
    cols = {'type': 'PLAY TYPE', 'form': 'OFF FORM', 'gain': 'GN/LS', 
            'dn': 'DN', 'dist': 'DIST', 'odk': 'ODK', 'play': 'OFF PLAY', 'field': 'YARD LN'}
    
    if all(cols[k] in df.columns for k in ['type', 'form', 'gain']):
        df[cols['type']] = df[cols['type']].str.upper().str.strip()
        df[cols['gain']] = pd.to_numeric(df[cols['gain']], errors='coerce').fillna(0)
        
        # Apply Logic
        results = df[cols['form']].apply(lambda x: process_offensive_logic(x))
        df['PERSONNEL'] = [r[0] for r in results]
        df['FAMILY'] = [r[1] for r in results]
        p_data = df[df[cols['type']].isin(['RUN', 'PASS'])].copy()

        # --- PDF PAGE 1: FORMATION & PERSONNEL USAGE ---
        st.header("1. Core Identity & Usage")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Formation Usage")
            f_counts = p_data['FAMILY'].value_counts()
            f_usage = pd.DataFrame({'Plays': f_counts, '% Usage': (f_counts/len(p_data)*100).round(0).astype(str) + '%'})
            st.table(f_usage) #
        with c2:
            st.subheader("Personnel Group Usage")
            p_counts = p_data['PERSONNEL'].value_counts()
            st.table(pd.DataFrame({'Plays': p_counts})) #

        # --- PDF PAGE 2: DISTRIBUTIONS & D&D ---
        st.markdown("---")
        st.header("2. Distributions & Situations")
        
        st.subheader("Run/Pass Distribution by Personnel")
        matrix = p_data.groupby('PERSONNEL')[cols['type']].value_counts().unstack().fillna(0)
        matrix['Run %'] = (matrix['RUN'] / (matrix['RUN'] + matrix['PASS']) * 100).round(0).astype(str) + '%'
        matrix['Pass %'] = (matrix['PASS'] / (matrix['RUN'] + matrix['PASS']) * 100).round(0).astype(str) + '%'
        st.table(matrix) #

        st.subheader("Down & Distance Run/Pass Matrix")
        def get_situation(row):
            d, dist = row[cols['dn']], row[cols['dist']]
            if dist < 4: s = "<4"
            elif 4 <= dist <= 7: s = "4-7"
            else: s = "7+"
            return f"{d}st & {s}" if d==1 else f"{d}nd & {s}" if d==2 else f"{d}rd & {s}" if d==3 else f"{d}th & {s}"
        
        p_data['Situation'] = p_data.apply(get_situation, axis=1)
        dd_matrix = p_data.groupby('Situation')[cols['type']].value_counts().unstack().fillna(0)
        dd_matrix['Run %'] = (dd_matrix['RUN'] / (dd_matrix['RUN'] + dd_matrix['PASS']) * 100).round(0).astype(str) + '%'
        dd_matrix['Pass %'] = (dd_matrix['PASS'] / (dd_matrix['RUN'] + dd_matrix['PASS']) * 100).round(0).astype(str) + '%'
        dd_matrix['Total'] = (dd_matrix['RUN'] + dd_matrix['PASS']).astype(int)
        st.table(dd_matrix) #

        # --- PDF PAGE 3: PRODUCTIVITY & ZONES ---
        st.markdown("---")
        st.header("3. Productivity & Explosives")
        
        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            st.subheader("Play Type Avg Gain")
            avg_gn = p_data.groupby(cols['type'])[cols['gain']].mean()
            st.table(avg_gn.rename("Avg Gain")) #
        with col_exp2:
            st.subheader("Explosive Rate")
            exp_run = (p_data[p_data[cols['type']] == 'RUN'][cols['gain']] >= 10).mean() * 100
            exp_pass = (p_data[p_data[cols['type']] == 'PASS'][cols['gain']] >= 20).mean() * 100
            st.write(f"Run (10+ yds): **{exp_run:.0f}%**") #
            st.write(f"Pass (20+ yds): **{exp_pass:.0f}%**") #

        st.subheader("Field Position Tendencies")
        def get_zone(yd):
            if yd <= 20: return "Own 0-20"
            elif 21 <= yd <= 50: return "Own 21-50"
            else: return "Opp 50-21"
        
        if cols['field'] in df.columns:
            p_data['Zone'] = p_data[cols['field']].apply(get_zone)
            zone_tend = p_data.groupby('Zone')[cols['type']].value_counts().unstack().fillna(0)
            st.table(zone_tend) #

        # --- PDF PAGE 4: PLAY PATTERNS ---
        st.markdown("---")
        st.header("4. Play Call Patterns")
        c3, c4 = st.columns(2)
        with c3:
            st.subheader("Most Frequent Runs (All Zones)")
            st.table(p_data[p_data[cols['type']]=='RUN'][cols['play']].value_counts().head(5)) #
        with c4:
            st.subheader("Most Frequent Passes (All Zones)")
            st.table(p_data[p_data[cols['type']]=='PASS'][cols['play']].value_counts().head(5)) #

    else:
        st.error(f"Missing columns: {list(cols.values())}")
