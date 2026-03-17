import streamlit as st
import pandas as pd
import re

# --- 1. THE BRAIN: REFINED LOGIC ---
def process_offensive_logic(formation):
    f = str(formation).upper().strip()
    
    # A. NUMBERS FIRST check
    match = re.match(r'^(\d)(\d)', f)
    if match:
        pers = f"{match.group(1)}{match.group(2)}"
        raw_name = re.sub(r'^\d{2}\s*', '', f)
    else:
        # B. KEYWORD DECODING (Spread=11, Dubs=10, Heavy=23)
        if any(x in f for x in ["HEAVY", "JUMBO", "BIG"]):
            pers, raw_name = "23", "PRO/HEAVY"
        elif "EMPTY" in f:
            pers, raw_name = "00", "EMPTY"
        elif "SPREAD" in f:
            pers, raw_name = "11", "SPREAD"
        elif "DUBS" in f or "TRIPS" in f:
            pers, raw_name = "10", "TRIPS" if "TRIPS" in f else "SPREAD"
        elif "ACE" in f:
            pers, raw_name = "12", "ACE"
        else:
            pers, raw_name = "11", f 
            
    # C. FAMILY GROUPING
    family = "OTHER"
    if "EMPTY" in raw_name: family = "EMPTY"
    elif any(x in raw_name for x in ["TRIPS", "TREY", "BUNCH", "3X1"]): family = "TRIPS"
    elif any(x in raw_name for x in ["SPREAD", "DUBS", "2X2", "WIDE"]): family = "SPREAD"
    elif any(x in raw_name for x in ["PRO", "I-", "HEAVY", "JUMBO"]): family = "PRO/HEAVY"
    elif "ACE" in raw_name: family = "ACE"
    elif "UNBALANCED" in raw_name: family = "UNBALANCED"
    
    return pers, family

# --- 2. UI SETUP ---
st.set_page_config(page_title="Lancer-Bot Pro", page_icon="🏈", layout="wide")

with st.sidebar:
    try: 
        st.image("logo.png", use_container_width=True)
    except: 
        st.subheader("🏈 Lancer-Bot")
    st.title("v2.30")
    st.info("Logic: Spread=11 | Dubs=10 | Heavy=23")

st.title("🏈 Offensive Identity Dashboard")
uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Column Mapping
    cols = {'type': 'PLAY TYPE', 'form': 'OFF FORM', 'gain': 'GN/LS', 
            'dn': 'DN', 'odk': 'ODK', 'play': 'OFF PLAY'}
    
    if all(cols[k] in df.columns for k in ['type', 'form', 'gain']):
        # Clean Data
        df[cols['type']] = df[cols['type']].str.upper().str.strip()
        df[cols['gain']] = pd.to_numeric(df[cols['gain']], errors='coerce').fillna(0)
        
        # Filter for Offense only
        if cols['odk'] in df.columns:
            df = df[df[cols['odk']].str.contains('O', na=False, case=False)]
        
        # Apply Logic
        results = df[cols['form']].apply(lambda x: process_offensive_logic(x))
        df['PERSONNEL'] = [r[0] for r in results]
        df['FAMILY'] = [r[1] for r in results]

        tabs = st.tabs(["Personnel Matrix", "Formation Families", "Danger Plays", "Pivot Lab", "Audit"])

        # Filter for actual Run/Pass plays for tendencies
        p_data = df[df[cols['type']].isin(['RUN', 'PASS'])].copy()

        with tabs[0]: 
            st.header("Personnel Tendencies")
            if not p_data.empty:
                matrix = p_data.groupby('PERSONNEL')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
                avg_gn = p_data.groupby('PERSONNEL')[cols['gain']].mean().rename("Avg Gain")
                counts = p_data['PERSONNEL'].value_counts().rename("Plays")
                st.dataframe(pd.concat([matrix, avg_gn, counts], axis=1).style.background_gradient(cmap='RdYlGn_r', subset=['RUN', 'PASS']).format("{:.1f} yds", subset=['Avg Gain']).format("{:.0f}%", subset=['RUN', 'PASS']))

        with tabs[1]:
            st.header("Family Heat Map")
            if not p_data.empty:
                f_data = p_data.groupby('FAMILY')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
                f_gain = p_data.groupby('FAMILY')[cols['gain']].mean
