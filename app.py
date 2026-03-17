import streamlit as st
import pandas as pd
import re

# --- 1. THE BRAIN: REFINED LOGIC ---
def process_offensive_logic(formation):
    f = str(formation).upper().strip()
    
    # A. NUMBERS FIRST
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
            
    # C. FAMILY GROUPING (Logic based on your session)
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
    try: st.image("logo.png", width=150)
    except: st.subheader("🏈 Lancer-Bot")
    st.title("v2.29")
    st.info("Logic: Spread=11 | Dubs=10 | Heavy=23")

st.title("🏈 Offensive Identity & Explosive Plays")
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
        if cols['odk'] in df.columns:
            df = df[df[cols['odk']].str.contains('O', na=False, case=False)]
        
        # Apply Logic
        df[['PERSONNEL', 'FAMILY']] = df[cols['form']].apply(lambda x: pd.Series(process_offensive_logic(x)))

        tabs = st.tabs(["Personnel Matrix", "Formation Families", "Danger Plays", "Pivot Lab", "Audit"])

        with tabs[0]: # Personnel Matrix
            st.header("Personnel Tendencies")
            p_data = df[df
