import streamlit as st
import pandas as pd
import re

# --- 1. CORE LOGIC (MASTER MAPPING) ---
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
st.set_page_config(page_title="Carlsbad Football Analytics", page_icon="🏈", layout="wide")

# Sidebar - Logo & Application Identity
with st.sidebar:
    try:
        # This will pull 'logo.png' from your GitHub root directory
        st.image("logo.png", use_container_width=True)
    except:
        st.subheader("🏈 CARLSBAD FOOTBALL")
    
    st.markdown("---")
    st.write("Metric Profile: **PDF Replica**")
    st.write("Logic: Spread=11 | Dubs=10 | Heavy=23")

st.title("🏈 Carlsbad Football Analytics")
st.subheader("Complete Offensive Report (Player Ready)")

uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Column mapping based on stable PDF metrics
    cols = {'type': 'PLAY TYPE', 'form': 'OFF FORM', 'gain': 'GN/LS', 
            'dn': 'DN', 'dist': 'DIST', 'odk': 'ODK', 'play': 'OFF PLAY', 
            'field': 'YARD LN', 'motion': 'MOTION DIR'}
    
    if all(cols[k] in df.columns for k in ['type', 'form', 'gain']):
        df[cols['type']] = df[cols['type']].str.upper().str.strip()
        df[cols['gain']] = pd.to_numeric(df[cols['gain']], errors='coerce').fillna(0)
        
        # Apply Logic
        results = df[cols['form']].apply(lambda x: process_offensive_logic(x))
        df['PERSONNEL'] = [r[0] for r in results]
        df['FAMILY'] = [r[1] for r in results]
        p_data = df[df[cols['type']].isin(['RUN', 'PASS'])].copy()

        # Zone Logic
        def get_zone(yd):
            if yd <= 20: return "Own 0-20"
            elif yd <= 50: return "Own 21-50"
            return "Opp 50-21"
        if cols['field'] in df.columns:
            p_data['Zone'] = p_data[cols['field']].apply(get_zone)

        # --- TABBED GROUPING ---
        tabs = st.tabs(["📊 Usage & Identity", "📈 Distributions", "⚡ Productivity", "🧪 Pivot Lab", "🤖 AI Intelligence"])

        with tabs[0]: # PAGE 1: USAGE
            st.header("Core Identity & Usage")
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Formation Usage")
                f_counts = p_data['FAMILY'].value_counts()
                st.table(pd.DataFrame({
                    'Plays': f_counts, 
                    '% Usage': (f_counts/len(p_counts)*100).round(0).astype(str) + '%' if not p_data.empty else "0%"
                }))
            with c2:
                st.subheader("Personnel Group Usage")
                st.table(pd.DataFrame({'Plays': p_data['PERSONNEL'].value_counts()}))
            st.info("Two-back sets make up more than half of all snaps.")

        with tabs[1]: # PAGE 2: DISTRIBUTIONS
            st.header("Run/Pass Distribution & Situations")
            st.subheader("By Personnel")
            matrix = p_data.groupby('PERSONNEL')[cols['type']].value_counts().unstack().fillna(0)
            if not matrix.empty:
                for p in ['Run %', 'Pass %']: 
                    matrix[p] = (matrix[p.split()[0].upper()] / (matrix.sum(axis=1)) * 100).round(0).astype(str) + '%'
                st.table(matrix)
            
            st.subheader("Down & Distance Matrix")
            def get_sit(row):
                d, dist = row[cols['dn']], row[cols['dist']]
                s = "<4" if dist < 4 else "4-7" if dist <= 7 else "7+"
                return f"{int(d)}st & {s}" if d==1 else f"{int(d)}nd & {s}" if d==2 else f"{int(d)}rd & {s}"
            p_data['Situation'] = p_data.apply(get_sit, axis=1)
            dd = p_data.groupby('
