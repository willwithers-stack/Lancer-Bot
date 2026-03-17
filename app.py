import streamlit as st
import pandas as pd
import os

# --- 1. THE REFINED DECODER (Strict 3-Group Logic) ---
def decode_personnel(backfield, formation):
    bf, form = str(backfield).upper().strip(), str(formation).upper().strip()
    
    # 1st Digit: RBs | 2nd Digit: TEs
    # Identify the "Big Three" groupings specifically
    
    # Example: 20 Personnel (2 RBs, 0 TEs) - Core Identity
    if any(x in bf for x in ["2RB", "PRO", "SPLIT"]) and any(x in form for x in ["0TE", "SPREAD", "DUBS"]):
        return "20 Personnel"
    
    # Example: 11 Personnel (1 RB, 1 TE)
    elif any(x in bf for x in ["1RB", "GUN", "PISTOL"]) and any(x in form for x in ["1TE", "WING", "ACE"]):
        return "11 Personnel"
    
    # Example: 10 Personnel (1 RB, 0 TEs)
    elif any(x in bf for x in ["1RB", "GUN", "PISTOL"]) and any(x in form for x in ["0TE", "SPREAD", "DUBS"]):
        return "10 Personnel"
    
    # Catch-all for anything outside the "Big Three"
    return "Other/Specialty"

# --- 2. THE UI & BRANDING ---
st.set_page_config(page_title="Lancer-Bot Pro", page_icon="🏈", layout="wide")

with st.sidebar:
    logo_file = next((f for f in ["logo.png", "Logo.png", "logo.PNG"] if os.path.exists(f)), None)
    col1, col2, col3 = st.columns([0.5, 3, 0.5])
    with col2:
        if logo_file: st.image(logo_file, use_container_width=True)
        else: st.subheader("🏈 Lancer-Bot")
    st.divider()
    st.title("Lancer-Bot v2.23")
    st.info("Status: Big Three Logic Active")

st.title("🏈 Offensive Identity Report")
uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, encoding='latin1')
        df.columns = [str(c).strip() for c in df.columns]
        
        # Mapping
        map_cols = {'type': 'PLAY TYPE', 'gain': 'GN/LS', 'form': 'OFF FORM', 'bf': 'BACKFIELD', 'dn': 'DN', 'odk': 'ODK'}

        if all(map_cols[k] in df.columns for k in ['type', 'gain', 'form', 'bf']):
            df[map_cols['type']] = df[map_cols['type']].astype(str).str.upper().str.strip()
            df[map_cols['gain']] = pd.to_numeric(df[map_cols['gain']], errors='coerce')
            
            # Apply Strict 3-Group Logic
            df['PERS_CODE'] = df.apply(lambda x: decode_personnel(x[map_cols['bf']], x[map_cols['form']]), axis=1)

            tabs = st.tabs(["Personnel Matrix", "Situational", "Formations", "Danger Plays"])

            with tabs[0]:
                st.header("The Big Three Personnel Matrix")
                p_df = df[df[map_cols['type']].isin(['RUN', 'PASS'])]
                if not p_df.empty:
                    # Filter for only the 3 main groups to keep the chart clean
                    p_df = p_df[p_df['PERS_CODE'] != "Other/Specialty"]
                    stats = p_df.groupby('PERS_CODE')[map_cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
                    counts = p_df['PERS_CODE'].value_counts().rename("Plays")
                    st.dataframe(pd.concat([stats, counts], axis=1).style.background_gradient(subset=['RUN', 'PASS'], cmap='RdYlGn_r').format({'RUN':'{:.0f}%', 'PASS':'{:.0f}%', 'Plays':'{:.0f}'}))
                else:
                    st.warning("No data found.")

            # [Other tabs Situational, Formations, Danger Plays follow same logic...]
    except Exception as e:
        st.error(f"Error: {e}")
