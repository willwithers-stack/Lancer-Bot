import streamlit as st
import pandas as pd

# --- 1. THE LOGIC ---
def get_trend_strength(count, total):
    if total < 3: return "⭐"
    pct = (count / total) * 100
    if pct >= 85 and total >= 6: return "⭐⭐⭐⭐⭐"
    if pct >= 70 and total >= 4: return "⭐⭐⭐⭐"
    return "⭐⭐⭐" if pct >= 60 else "⭐⭐"

def decode_personnel(text):
    """Translates Hudl tags to Standard Numbering (e.g., 2RB 1TE -> 21)"""
    text = str(text).upper()
    rb = "0"
    te = "0"
    if "1RB" in text: rb = "1"
    if "2RB" in text: rb = "2"
    if "0TE" in text: te = "0"
    if "1TE" in text: te = "1"
    if "2TE" in text: te = "2"
    # Fallback for OTE/OTE cases
    if "OTE" in text and te == "0": te = "0"
    return f"{rb}{te} Personnel"

# --- 2. THE UI ---
st.set_page_config(page_title="Lancer-Bot Pro", page_icon="🏈", layout="wide")

with st.sidebar:
    try:
        st.image("logo.png", width=150)
    except:
        st.subheader("🏈 Carlsbad Football")
    st.title("Lancer-Bot v2.7")

st.title("🏈 Offensive Identity Report")
uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = [str(c).strip().upper() for c in df.columns]
    
    # Mapping [cite: 4, 38]
    mapping = {'GN/LS': 'GAIN', 'PLAY TYPE': 'TYPE', 'DN': 'DOWN', 
               'PERSONNEL': 'PERS_GRP', 'OFF FORM-OFFENSIVE FORMATION': 'FORM_GRP', 
               'ODK': 'ODK', 'OFF PLAY': 'PLAY_NAME'}
    
    for hudl_name, clean_name in mapping.items():
        if hudl_name in df.columns:
            df = df.rename(columns={hudl_name: clean_name})

    if 'TYPE' in df.columns and 'GAIN' in df.columns:
        df['TYPE'] = df['TYPE'].str.upper().str.strip()
        df['GAIN'] = pd.to_numeric(df['GAIN'], errors='coerce')
        
        # New: Decode the Personnel column for the Matrix [cite: 9, 11]
        if 'PERS_GRP' in df.columns:
            df['PERS_CODE'] = df['PERS_GRP'].apply(decode_personnel)

        tabs = st.tabs(["Intelligence", "Situational", "Danger Plays", "Formations", "Personnel", "Pivot Lab"])

        with tabs[4]: # Personnel Matrix
            st.header("Personnel Matrix (Standard Numbering)")
            p_df = df[df['TYPE'].isin(['RUN', 'PASS'])]
            if 'PERS_CODE' in p_df.columns:
                # Group by decoded codes (11, 21, etc.) 
                pers_analysis = p_df.groupby('PERS_CODE')['TYPE'].value_counts(normalize=True).unstack().fillna(0) * 100
                st.dataframe(pers_analysis.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
                
                st.subheader("Volume by Grouping")
                st.bar_chart(df['PERS_CODE'].value_counts())
            else:
                st.warning("Could not decode personnel. Check Hudl tags.")

        # [Other tabs remain with the same stabilized logic...]
