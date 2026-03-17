import streamlit as st
import pandas as pd
import os

# --- 1. THE STABLE DECODER ---
def decode_personnel(backfield, formation):
    """Standard Numbering: 1st Digit = RBs | 2nd Digit = TEs"""
    bf, form = str(backfield).upper().strip(), str(formation).upper().strip()
    rb, te = "1", "0" 
    
    # RB Logic
    if any(x in bf for x in ["2RB", "PRO", "SPLIT", "FULL", "I-FORM"]): rb = "2"
    elif any(x in bf for x in ["0RB", "EMPTY", "MT"]): rb = "0"
    
    # TE Logic
    if any(x in form for x in ["2TE", "HEAVY", "JUMBO", "HB"]): te = "2"
    elif any(x in form for x in ["1TE", "WING", "Y-TRIPS", "ACE", "TIGHT"]): te = "1"
    
    return f"{rb}{te} Personnel"

def get_trend_strength(count, total):
    if total < 3: return "⭐"
    pct = (count / total) * 100
    if pct >= 85 and total >= 6: return "⭐⭐⭐⭐⭐"
    return "⭐⭐⭐" if pct >= 60 else "⭐⭐"

# --- 2. THE UI & BRANDING ---
st.set_page_config(page_title="Lancer-Bot Pro", page_icon="🏈", layout="wide")

with st.sidebar:
    logo_file = next((f for f in ["logo.png", "Logo.png", "logo.PNG"] if os.path.exists(f)), None)
    col1, col2, col3 = st.columns([0.5, 3, 0.5])
    with col2:
        if logo_file: st.image(logo_file, use_container_width=True)
        else: st.subheader("🏈 Lancer-Bot")
    st.divider()
    st.title("Lancer-Bot v2.28")
    st.info("System: Full Feature Restoration")

st.title("🏈 Offensive Identity Report")
uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, encoding='latin1')
        df.columns = [str(c).strip() for c in df.columns]
        
        # Exact Mapping for your Hudl Export
        map_cols = {
            'type': 'PLAY TYPE', 'gain': 'GN/LS', 'form': 'OFF FORM', 
            'bf': 'BACKFIELD', 'play': 'OFF PLAY', 'dn': 'DN', 'odk': 'ODK'
        }

        if all(map_cols[k] in df.columns for k in ['type', 'gain', 'form', 'bf']):
            df[map_cols['type']] = df[map_cols['type']].astype(str).str.upper().str.strip()
            df[map_cols['gain']] = pd.to_numeric(df[map_cols['gain']], errors='coerce')
            
            if map_cols['odk'] in df.columns:
                df = df[df[map_cols['odk']].str.contains('O', na=False, case=False)]
            
            # Re-apply Personnel Logic
            df['PERS_CODE'] = df.apply(lambda x: decode_personnel(x[map_cols['bf']], x[map_cols['form']]), axis=1)
            df['Prev_Type'] = df[map_cols['type']].shift(1)
            df['Prev_Gain'] = df[map_cols['gain']].shift(1)

            tabs = st.tabs(["Intelligence", "Situational", "Danger Plays", "Formations", "Personnel", "Pivot Lab"])

            with tabs[0]: # Intelligence
                st.header("AI Intelligence Alerts")
                intel = []
                scr = df.head(10)
                if not scr.empty:
                    run_c = (scr[map_cols['type']] == 'RUN').sum()
                    intel.append({"Category": "Script", "Insight": "Opening Run Freq", "Stat": f"{(run_c/len(scr))*1
