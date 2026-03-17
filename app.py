import streamlit as st
import pandas as pd

# --- 1. THE DECODER (Optimized for your Hudl Headers) ---
def decode_personnel(backfield, formation):
    bf = str(backfield).upper().strip()
    form = str(formation).upper().strip()

    # RB Count (1st Digit)
    if any(x in bf for x in ["2RB", "PRO", "SPLIT", "FULL", "I-FORM"]):
        rb = "2"
    elif any(x in bf for x in ["1RB", "GUN", "PISTOL", "SINGLEBACK"]):
        rb = "1"
    elif any(x in bf for x in ["0RB", "EMPTY", "TRIPS EMPTY"]):
        rb = "0"
    else:
        rb = "?" 

    # TE Count (2nd Digit)
    if any(x in form for x in ["2TE", "HEAVY", "JUMBO", "HB"]):
        te = "2"
    elif any(x in form for x in ["1TE", "WING", "Y-TRIPS", "ACE"]):
        te = "1"
    elif any(x in form for x in ["0TE", "SPREAD", "DUBS", "EMPTY", "4WR", "5WR"]):
        te = "0"
    else:
        te = "?" 

    label = f"{rb}{te} Personnel"
    return label if "?" not in label else f"{rb}{te} (Review Required)"

# --- 2. THE UI & DASHBOARD ---
st.set_page_config(page_title="Lancer-Bot Pro", page_icon="🏈", layout="wide")

with st.sidebar:
    try:
        st.image("logo.png", width=150)
    except:
        st.subheader("🏈 Carlsbad Football")
    st.title("Lancer-Bot v2.16")

st.title("🏈 Personnel Identity Breakdown")
uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = [str(c).strip() for c in df.columns] # Clean headers 
    
    # Map your exact Hudl columns 
    type_col = 'PLAY TYPE'
    form_col = 'OFF FORM'
    bf_col   = 'BACKFIELD'
    odk_col  = 'ODK'

    if all(col in df.columns for col in [type_col, form_col, bf_col]):
        # Filter for Offense Only
        if odk_col in df.columns:
            df = df[df[odk_col].str.contains('O', na=False, case=False)]
        
        # Apply the logic you got from Perplexity
        df['STANDARD_PERS'] = df.apply(lambda x: decode_personnel(x[bf_col], x[form_col]), axis=1)

        tab1, tab2 = st.tabs(["Personnel Matrix", "Decoder Audit"])

        with tab1:
            st.header("Personnel Matrix")
            # Filter for Run/Pass to calculate tendencies
            p_df = df[df[type_col].str.contains('RUN|PASS', na=False, case=False)]
            
            if not p_df.empty:
                # Group by our new 10/11/20 codes
                matrix = p_df.groupby('STANDARD_PERS')[type_col].value_counts(normalize=True).unstack().fillna(0) * 100
                st.dataframe(matrix.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
                
                st.subheader("Personnel Usage Volume")
                st.bar_chart(p_df['STANDARD_PERS'].value_counts())
            else:
                st.warning("No Run/Pass plays detected.")

        with tab2:
            st.header("Decoder Audit")
            st.write("Check how the bot is translating your Hudl data:")
            st.table(df[[bf_col, form_col, 'STANDARD_PERS']].head(15))
    else:
        st.error(f"Missing Columns. Bot found: {list(df.columns)}")
