import streamlit as st
import pandas as pd
import os

# --- 1. EXPANDED DECODER (Scanning for all variations) ---
def decode_personnel(backfield, formation):
    bf, form = str(backfield).upper().strip(), str(formation).upper().strip()
    
    # --- RB Count (1st Digit) ---
    if any(x in bf for x in ["2RB", "PRO", "SPLIT", "FULL", "I-FORM", "TWIN"]):
        rb = "2"
    elif any(x in bf for x in ["1RB", "GUN", "PISTOL", "SING", "S-BACK", "OFFSET"]):
        rb = "1"
    elif any(x in bf for x in ["0RB", "EMPTY", "MT", "NO BACK"]):
        rb = "0"
    else:
        rb = "1" # Default to 1RB for standard sets

    # --- TE Count (2nd Digit) ---
    if any(x in form for x in ["2TE", "HEAVY", "JUMBO", "DBL TIGHT", "12", "22"]):
        te = "2"
    elif any(x in form for x in ["1TE", "WING", "Y-TRIPS", "ACE", "TIGHT", "Y-", "11", "21"]):
        te = "1"
    elif any(x in form for x in ["0TE", "SPREAD", "DUBS", "DBLS", "EMPTY", "4WR", "5WR", "10", "20"]):
        te = "0"
    else:
        te = "0" # Default to 0TE for spread-looking names
        
    return f"{rb}{te} Personnel"

# --- 2. THE UI & BRANDING ---
st.set_page_config(page_title="Lancer-Bot Pro", page_icon="🏈", layout="wide")

with st.sidebar:
    logo_file = next((f for f in ["logo.png", "Logo.png", "logo.PNG"] if os.path.exists(f)), None)
    col1, col2, col3 = st.columns([0.5, 3, 0.5])
    with col2:
        if logo_file: st.image(logo_file, use_container_width=True)
        else: st.subheader("🏈 Lancer-Bot")
    st.divider()
    st.title("Lancer-Bot v2.26")
    st.info("System: Multi-Personnel Scan")

st.title("🏈 Offensive Identity Report")
uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, encoding='latin1')
        df.columns = [str(c).strip() for c in df.columns]
        
        # Mapping
        map_cols = {'type': 'PLAY TYPE', 'gain': 'GN/LS', 'form': 'OFF FORM', 'bf': 'BACKFIELD'}

        if all(map_cols[k] in df.columns for k in ['type', 'gain', 'form', 'bf']):
            df[map_cols['type']] = df[map_cols['type']].astype(str).str.upper().str.strip()
            df[map_cols['gain']] = pd.to_numeric(df[map_cols['gain']], errors='coerce')
            
            # Apply Expanded Logic
            df['PERS_CODE'] = df.apply(lambda x: decode_personnel(x[map_cols['bf']], x[map_cols['form']]), axis=1)

            tabs = st.tabs(["Personnel Matrix", "Situational", "Danger Plays", "Formations"])

            with tabs[0]: # Personnel Matrix
                st.header("Personnel Tendencies & Volume")
                p_df = df[df[map_cols['type']].isin(['RUN', 'PASS'])]
                
                if not p_df.empty:
                    # Calculate stats for all detected groups
                    stats = p_df.groupby('PERS_CODE')[map_cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
                    counts = p_df['PERS_CODE'].value_counts().rename("Plays")
                    
                    # Merge and Sort by Usage (showing top groupings first)
                    final_matrix = pd.concat([stats, counts], axis=1).sort_values(by="Plays", ascending=False)
                    
                    st.dataframe(final_matrix.style.background_gradient(subset=['RUN', 'PASS'], cmap='RdYlGn_r').format({
                        'RUN':'{:.0f}%', 'PASS':'{:.0f}%', 'Plays':'{:.0f}'
                    }))
                    
                    st.subheader("Personnel Usage Distribution")
                    st.bar_chart(counts)
                else:
                    st.warning("No Run/Pass data found.")

            # [Other tabs follow the same expanded logic...]
    except Exception as e:
        st.error(f"Error: {e}")
