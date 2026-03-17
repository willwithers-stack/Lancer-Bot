import streamlit as st
import pandas as pd
import os

# --- 1. THE EXPANDED DECODER (Identifies 5+ Groupings) ---
def decode_personnel(backfield, formation):
    bf, form = str(backfield).upper().strip(), str(formation).upper().strip()
    
    # 1st Digit: RBs | 2nd Digit: TEs
    
    # 22 Personnel (2 RB, 2 TE) - Heavy/Goal Line
    if ("2RB" in bf or "PRO" in bf) and ("2TE" in form or "HEAVY" in form):
        return "22 Personnel"
    # 21 Personnel (2 RB, 1 TE) - Standard Power
    elif ("2RB" in bf or "PRO" in bf) and ("1TE" in form or "WING" in form):
        return "21 Personnel"
    # 20 Personnel (2 RB, 0 TE) - Lancer Core
    elif ("2RB" in bf or "PRO" in bf) and ("0TE" in form or "SPREAD" in form):
        return "20 Personnel"
    # 12 Personnel (1 RB, 2 TE) - Double Tight
    elif ("1RB" in bf or "GUN" in bf) and ("2TE" in form or "HEAVY" in form):
        return "12 Personnel"
    # 11 Personnel (1 RB, 1 TE) - Universal Spread
    elif ("1RB" in bf or "GUN" in bf) and ("1TE" in form or "WING" in form):
        return "11 Personnel"
    # 10 Personnel (1 RB, 0 TE) - Pure Spread
    elif ("1RB" in bf or "GUN" in bf) and ("0TE" in form or "SPREAD" in form):
        return "10 Personnel"
    # 00/01 Personnel (Empty sets)
    elif "EMPTY" in bf or "EMPTY" in form:
        return "0x Personnel (Empty)"
    
    return "Other/Specialty"

# --- 2. THE UI ---
st.set_page_config(page_title="Lancer-Bot Pro", page_icon="🏈", layout="wide")

with st.sidebar:
    logo_file = next((f for f in ["logo.png", "Logo.png", "logo.PNG"] if os.path.exists(f)), None)
    col1, col2, col3 = st.columns([0.5, 3, 0.5])
    with col2:
        if logo_file: st.image(logo_file, use_container_width=True)
        else: st.subheader("🏈 Lancer-Bot")
    st.divider()
    st.title("Lancer-Bot v2.25")

st.title("🏈 Offensive Identity Report")
uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file, encoding='latin1')
    df.columns = [str(c).strip() for c in df.columns]
    
    # Mapping
    type_col, gain_col, form_col, bf_col = 'PLAY TYPE', 'GN/LS', 'OFF FORM', 'BACKFIELD'

    if all(col in df.columns for col in [type_col, gain_col, form_col, bf_col]):
        df[type_col] = df[type_col].astype(str).str.upper().str.strip()
        df[gain_col] = pd.to_numeric(df[gain_col], errors='coerce')
        
        # Apply Logic
        df['PERS_CODE'] = df.apply(lambda x: decode_personnel(x[bf_col], x[form_col]), axis=1)

        tabs = st.tabs(["Personnel Matrix", "Situational", "Danger Plays", "Formations", "Pivot Lab"])
        
        with tabs[0]:
            st.header("Extended Personnel Matrix")
            st.info("Showing all detected groupings with Run/Pass tendencies.")
            
            p_df = df[df[type_col].isin(['RUN', 'PASS'])]
            
            if not p_df.empty:
                # Group and calculate
                stats = p_df.groupby('PERS_CODE')[type_col].value_counts(normalize=True).unstack().fillna(0).mul(100)
                counts = p_df['PERS_CODE'].value_counts().rename("Plays")
                
                # Merge stats and counts
                final_matrix = pd.concat([stats, counts], axis=1).sort_values(by="Plays", ascending=False)
                
                # Ensure the display is clean
                st.dataframe(final_matrix.style.background_gradient(subset=['RUN', 'PASS'], cmap='RdYlGn_r').format({
                    'RUN':'{:.0f}%', 'PASS':'{:.0f}%', 'Plays':'{:.0f}'
                }))
                
                st.subheader("Personnel Volume")
                st.bar_chart(counts)
            else:
                st.warning("No Run/Pass plays detected in the CSV.")

        # [Other tabs Situational, Danger Plays, Formations follow established logic]
