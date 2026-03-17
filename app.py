import streamlit as st
import pandas as pd

# --- 1. THE MAPPING LOGIC ---
def decode_personnel(backfield, formation):
    """
    Applies your Standard Numbering System.
    1st Digit = RBs (from Backfield) | 2nd Digit = TEs (from Formation)
    """
    bf = str(backfield).upper()
    form = str(formation).upper()
    rb, te = "0", "0"
    
    # RB Count (First Digit)
    if "2RB" in bf or "PRO" in bf or "SPLIT" in bf: rb = "2"
    elif "1RB" in bf or "GUN" in bf or "PISTOL" in bf: rb = "1"
    
    # TE Count (Second Digit)
    if "2TE" in form or "HEAVY" in form: te = "2"
    elif "1TE" in form or "WING" in form or "Y-TRIPS" in form: te = "1"
    elif "0TE" in form or "SPREAD" in form or "DUBS" in form: te = "0"
    
    return f"{rb}{te} Personnel"

# --- 2. THE UI ---
st.set_page_config(page_title="Lancer-Bot Pro", page_icon="🏈", layout="wide")

with st.sidebar:
    try:
        st.image("logo.png", width=150)
    except:
        st.subheader("🏈 Carlsbad Football")
    st.title("Lancer-Bot v2.14")

st.title("🏈 Offensive Identity Report")
uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    # Cleaning headers based on your specific list
    df.columns = [str(c).strip() for c in df.columns]
    
    # EXACT MAPPING
    type_col = 'PLAY TYPE'
    gain_col = 'GN/LS'
    form_col = 'OFF FORM'
    play_col = 'OFF PLAY'
    down_col = 'DN'
    bf_col   = 'BACKFIELD'
    odk_col  = 'ODK'

    if type_col in df.columns and form_col in df.columns:
        # Standardize Data
        df[type_col] = df[type_col].str.upper().str.strip()
        df[gain_col] = pd.to_numeric(df[gain_col], errors='coerce')
        
        # Filter for Offense
        if odk_col in df.columns:
            df = df[df[odk_col].str.contains('O', na=False, case=False)]

        # Generate Personnel from your Numbering Logic
        df['STANDARD_PERS'] = df.apply(lambda x: decode_personnel(x[bf_col], x[form_col]), axis=1)

        tabs = st.tabs(["Intelligence", "Situational", "Danger Plays", "Formations", "Personnel", "Pivot Lab"])

        with tabs[3]: # Formations
            st.header("Formation Breakdown")
            f_df = df[df[type_col].isin(['RUN', 'PASS'])]
            if not f_df.empty:
                # Grouping by 'OFF FORM'
                form_stats = f_df.groupby(form_col)[type_col].value_counts(normalize=True).unstack().fillna(0) * 100
                st.dataframe(form_stats.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))

        with tabs[4]: # Personnel
            st.header("Personnel Matrix (Standard Numbering)")
            st.info("Logic: 1st Digit = RBs (Backfield) | 2nd Digit = TEs (Formation)")
            p_df = df[df[type_col].isin(['RUN', 'PASS'])]
            if not p_df.empty:
                pers_stats = p_df.groupby('STANDARD_PERS')[type_col].value_counts(normalize=True).unstack().fillna(0) * 100
                st.dataframe(pers_stats.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
                st.bar_chart(p_df['STANDARD_PERS'].value_counts())

        with tabs[2]: # Danger Plays
            st.header("Top Yardage Producers")
            if play_col in df.columns:
                # Grouping by 'OFF PLAY'
                danger = df.groupby(play_col)[gain_col].agg(['mean', 'count']).sort_values(by='mean', ascending=False).head(10)
                danger.columns = ['Avg Gain', 'Times Run']
                st.table(danger)
    else:
        st.error(f"Mapping Failed. Found: {list(df.columns)}")
