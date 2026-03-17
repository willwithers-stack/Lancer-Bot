import streamlit as st
import pandas as pd

# --- 1. THE MAPPING LOGIC ---
def extract_personnel_from_form(form_text):
    """
    Extracts Standard Personnel (RB/TE) from Formation names.
    Logic based on your provided core identity[cite: 4, 5].
    """
    form = str(form_text).upper()
    
    # 20 Personnel: 2 RBs, 0 TEs (Core Lancer Identity) [cite: 4, 5]
    if any(x in form for x in ["20", "WING", "SPREAD WING"]):
        return "20 Personnel"
    
    # 11 Personnel: 1 RB, 1 TE
    if any(x in form for x in ["11", "SPREAD", "BUNCH"]):
        return "11 Personnel"
    
    # 12 Personnel: 1 RB, 2 TEs [cite: 4]
    if "12" in form:
        return "12 Personnel"
    
    # 10 Personnel: 1 RB, 0 TEs (Pure Spread)
    if "10" in form or "DUBS" in form:
        return "10 Personnel"
        
    # 21 Personnel: 2 RBs, 1 TE [cite: 26]
    if "21" in form:
        return "21 Personnel"

    return "Other/Unknown"

# --- 2. THE UI ---
st.set_page_config(page_title="Lancer-Bot Pro", page_icon="🏈", layout="wide")

with st.sidebar:
    try:
        st.image("logo.png", width=150)
    except:
        st.subheader("🏈 Carlsbad Football")
    st.title("Lancer-Bot v2.13")

st.title("🏈 Offensive Identity Report")
uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = [str(c).strip() for c in df.columns]
    
    # MAP HEADERS 
    type_col = 'PLAY TYPE'
    gain_col = 'GN/LS'
    form_col = 'OFF FORM-offensive formation'
    play_col = 'OFF PLAY'
    down_col = 'DN'

    if type_col in df.columns and form_col in df.columns:
        # Standardize
        df[type_col] = df[type_col].str.upper().str.strip()
        df[gain_col] = pd.to_numeric(df[gain_col], errors='coerce')
        
        # CREATE PERSONNEL FROM FORMATION
        df['DERIVED_PERS'] = df[form_col].apply(extract_personnel_from_form)

        tabs = st.tabs(["Intelligence", "Situational", "Danger Plays", "Formations", "Personnel", "Pivot Lab"])

        with tabs[3]: # Formations [cite: 25]
            st.header("Formation Breakdown")
            f_df = df[df[type_col].isin(['RUN', 'PASS'])]
            if not f_df.empty:
                form_stats = f_df.groupby(form_col)[type_col].value_counts(normalize=True).unstack().fillna(0) * 100
                st.dataframe(form_stats.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))

        with tabs[4]: # Personnel [cite: 9, 11]
            st.header("Personnel Matrix (Extracted from Formations)")
            st.info("Logic: Mapping formation keywords to RB/TE counts.")
            p_df = df[df[type_col].isin(['RUN', 'PASS'])]
            if not p_df.empty:
                pers_stats = p_df.groupby('DERIVED_PERS')[type_col].value_counts(normalize=True).unstack().fillna(0) * 100
                st.dataframe(pers_stats.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
                st.bar_chart(p_df['DERIVED_PERS'].value_counts())

        with tabs[2]: # Danger Plays [cite: 15]
            st.header("Top Yardage Producers")
            if play_col in df.columns:
                danger = df.groupby(play_col)[gain_col].agg(['mean', 'count']).sort_values(by='mean', ascending=False).head(10)
                danger.columns = ['Avg Gain', 'Times Run']
                st.table(danger)
    else:
        st.error(f"Missing Columns. Found: {list(df.columns)}")
