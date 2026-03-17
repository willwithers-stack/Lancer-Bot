import streamlit as st
import pandas as pd

# --- 1. THE LOGIC ---
def get_trend_strength(count, total):
    if total < 3: return "⭐"
    pct = (count / total) * 100
    if pct >= 85 and total >= 6: return "⭐⭐⭐⭐⭐"
    if pct >= 70 and total >= 4: return "⭐⭐⭐⭐"
    return "⭐⭐⭐" if pct >= 60 else "⭐⭐"

def decode_to_standard(text):
    """
    Implements the User's Standard Numbering System:
    1st Digit = # of RBs | 2nd Digit = # of TEs
    """
    text = str(text).upper()
    rb = "0"
    te = "0"
    
    # Check for RBs
    if "2RB" in text: rb = "2"
    elif "1RB" in text: rb = "1"
    
    # Check for TEs
    if "2TE" in text: te = "2"
    elif "1TE" in text: te = "1"
    elif "0TE" in text or "OTE" in text: te = "0"
    
    return f"{rb}{te} Personnel"

# --- 2. THE UI ---
st.set_page_config(page_title="Lancer-Bot Pro", page_icon="🏈", layout="wide")

with st.sidebar:
    try:
        st.image("logo.png", width=150)
    except:
        st.subheader("🏈 Carlsbad Football")
    st.title("Lancer-Bot v2.11")

st.title("🏈 Offensive Identity Report")
uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Mapping exact headers [cite: 4, 10, 13]
    gain_col = 'GN/LS'
    type_col = 'PLAY TYPE'
    down_col = 'DN'
    pers_col = 'PERSONNEL'
    form_col = 'OFF FORM-offensive formation'
    play_col = 'OFF PLAY'
    odk_col  = 'ODK'

    if type_col in df.columns and gain_col in df.columns:
        df[type_col] = df[type_col].str.upper().str.strip()
        df[gain_col] = pd.to_numeric(df[gain_col], errors='coerce')
        
        # Apply the Standard Numbering System
        if pers_col in df.columns:
            df['STANDARD_PERS'] = df[pers_col].apply(decode_to_standard)

        # Tabs
        tabs = st.tabs(["Intelligence", "Situational", "Danger Plays", "Formations", "Personnel", "Pivot Lab"])

        with tabs[4]: # Personnel Matrix
            st.header("Personnel Groupings (Standard System)")
            st.write("First Digit: RBs | Second Digit: TEs")
            
            p_df = df[df[type_col].isin(['RUN', 'PASS'])]
            if 'STANDARD_PERS' in p_df.columns:
                # Calculate tendencies based on your numbering system [cite: 10, 11]
                pers_stats = p_df.groupby('STANDARD_PERS')[type_col].value_counts(normalize=True).unstack().fillna(0) * 100
                st.dataframe(pers_stats.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
                
                # Volume Chart
                st.bar_chart(p_df['STANDARD_PERS'].value_counts())
            else:
                st.error("Personnel column missing or unreadable.")

        with tabs[2]: # Danger Plays
            st.header("Top Yardage Producers")
            if play_col in df.columns:
                danger = df.groupby(play_col)[gain_col].agg(['mean', 'count']).sort_values(by='mean', ascending=False).head(5)
                danger.columns = ['Avg Gain', 'Times Run']
                st.table(danger)

        with tabs[5]: # Pivot Lab
            st.header("🧪 Custom Pivot Lab")
            opts = [c for c in ['STANDARD_PERS', form_col, down_col, play_col] if c in df.columns]
            group_choice = st.selectbox("Breakdown by:", opts)
            metric_choice = st.selectbox("Metric:", [gain_col, type_col])
            
            if group_choice and metric_choice:
                if metric_choice == gain_col:
                    pivot = df.groupby(group_choice)[gain_col].agg(['mean', 'count']).sort_values(by='mean', ascending=False)
                    st.dataframe(pivot.style.format({'mean': '{:.1f} yds', 'count': '{:.0f} plays'}).background_gradient(subset=['mean'], cmap='Greens'))
                else:
                    pivot = df.groupby(group_choice)[type_col].value_counts(normalize=True).unstack().fillna(0) * 100
                    st.dataframe(pivot.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))

# Other tabs (Intelligence, Situational, Formations) follow established logic.
