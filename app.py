import streamlit as st
import pandas as pd
import re

# --- 1. THE BRAIN: PERSONNEL & FORMATION LOGIC ---
def process_offensive_logic(formation):
    f = str(formation).upper().strip()
    
    # A. NUMBERS FIRST (e.g., "11 SPREAD", "23 JUMBO")
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
            pers, raw_name = "11", f # Lancer Default
            
    # C. FAMILY GROUPING
    family = "OTHER"
    if "EMPTY" in raw_name: family = "EMPTY"
    elif any(x in raw_name for x in ["TRIPS", "TREY", "BUNCH", "3X1"]): family = "TRIPS"
    elif any(x in raw_name for x in ["SPREAD", "DUBS", "2X2", "WIDE"]): family = "SPREAD"
    elif any(x in raw_name for x in ["PRO", "I-", "HEAVY", "JUMBO"]): family = "PRO/HEAVY"
    elif "ACE" in raw_name: family = "ACE"
    elif "UNBALANCED" in raw_name: family = "UNBALANCED"
    
    return pers, family

# --- 2. THE UI & DASHBOARD ---
st.set_page_config(page_title="Lancer-Bot Pro", page_icon="🏈", layout="wide")

with st.sidebar:
    try: st.image("logo.png", width=150)
    except: st.subheader("🏈 Lancer-Bot")
    st.title("v2.28")
    st.info("Logic: Spread=11 | Dubs=10 | Heavy=23")

st.title("🏈 Offensive Identity Dashboard")
uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = [str(c).strip() for c in df.columns]
    
    # Required Column Mapping
    cols = {'type': 'PLAY TYPE', 'form': 'OFF FORM', 'gain': 'GN/LS', 'dn': 'DN', 'odk': 'ODK'}
    
    if all(cols[k] in df.columns for k in ['type', 'form']):
        # Data Cleaning
        df[cols['type']] = df[cols['type']].str.upper().str.strip()
        if cols['odk'] in df.columns:
            df = df[df[cols['odk']].str.contains('O', na=False, case=False)]
        
        # Apply Master Logic
        df[['PERSONNEL', 'FAMILY']] = df[cols['form']].apply(
            lambda x: pd.Series(process_offensive_logic(x))
        )

        tabs = st.tabs(["Personnel Matrix", "Formation Families", "Intelligence", "Pivot Lab"])

        with tabs[0]: # Personnel Matrix
            st.header("Personnel Tendencies")
            p_data = df[df[cols['type']].isin(['RUN', 'PASS'])]
            matrix = p_data.groupby('PERSONNEL')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
            counts = p_data['PERSONNEL'].value_counts().rename("Plays")
            st.dataframe(pd.concat([matrix, counts], axis=1).style.background_gradient(cmap='RdYlGn_r', subset=['RUN', 'PASS']).format("{:.0f}%", subset=['RUN', 'PASS']))

        with tabs[1]: # Formation Families
            st.header("Formation Family Heat Map")
            f_data = p_data.groupby('FAMILY')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
            st.dataframe(f_data.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))

        with tabs[2]: # Intelligence
            st.header("Scouting Alerts")
            scr = df.head(10)
            run_p = (scr[cols['type']] == 'RUN').mean() * 100
            st.metric("Opening Script Run %", f"{run_p:.0f}%")
            st.subheader("Audit: Formation to Logic Mapping")
            st.table(df[[cols['form'], 'PERSONNEL', 'FAMILY']].drop_duplicates().head(15))

        with tabs[3]: # Pivot Lab
            st.header("🧪 Custom Analytics")
            group = st.selectbox("Group By:", ['FAMILY', 'PERSONNEL', cols['dn']])
            res = p_data.groupby(group)[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
            st.dataframe(res.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
    else:
        st.error(f"Missing columns. Need: {list(cols.values())}")
