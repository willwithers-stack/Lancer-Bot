import streamlit as st
import pandas as pd

# --- 1. THE LOGIC ---
def get_trend_strength(count, total):
    if total < 3: return "⭐"
    pct = (count / total) * 100
    if pct >= 85 and total >= 6: return "⭐⭐⭐⭐⭐"
    if pct >= 70 and total >= 4: return "⭐⭐⭐⭐"
    return "⭐⭐⭐" if pct >= 60 else "⭐⭐"

# --- 2. THE UI & BRANDING ---
st.set_page_config(page_title="Lancer-Bot Pro", page_icon="🏈", layout="wide")

with st.sidebar:
    # Ensure 'logo.png' is uploaded to your GitHub repo
    try:
        st.image("logo.png", width=150)
    except:
        st.warning("Logo not found. Upload 'logo.png' to GitHub.")
    st.title("Lancer-Bot v2.1")
    st.info("AI Defensive Intelligence")

st.title("🏈 Offensive Identity Report")

opponent = st.text_input("Opponent Name", "Carlsbad Rival")
uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    # Mapping specific columns from your Hudl data
    gain_col = 'GN/LS'
    type_col = 'PLAY TYPE'
    down_col = 'DN'
    odk_col  = 'ODK'
    play_col = 'OFF PLAY'
    pers_col = 'PERSONNEL'
    form_col = next((c for c in df.columns if 'FORM' in c.upper()), None)

    # Data Cleaning
    df[gain_col] = pd.to_numeric(df[gain_col], errors='coerce')
    df['Prev_Play_Type'] = df[type_col].shift(1)
    df['Prev_Gain'] = df[gain_col].shift(1)

    # --- TABS ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Intelligence", "Situational", "Danger Plays", "Formations", "Personnel"])

    with tab1:
        st.header("AI Intelligence Alerts")
        intel_data = []
        # Drive 1 Analysis
        offense_only = df[df[odk_col].str.contains('O', na=False, case=False)].head(10)
        if not offense_only.empty:
            run_c = offense_only[type_col].str.contains('RUN', na=False, case=False).sum()
            intel_data.append({
                "Category": "Opening Script", 
                "Insight": "Drive 1 Run Freq", 
                "Stat": f"{(run_c/len(offense_only))*100:.0f}%", 
                "Strength": get_trend_strength(run_c, len(offense_only))
            })
        
        # Post-Sack Response
        ps = df[(df['Prev_Play_Type'].str.contains('PASS', na=False, case=False)) & (df['Prev_Gain'] <= -4)]
        if not ps.empty:
            safe = df.loc[ps.index, type_col].str.contains('RUN', na=False, case=False).sum()
            intel_data.append({
                "Category": "Sequence", 
                "Insight": "Post-Sack Safe Response", 
                "Stat": f"{(safe/len(ps))*100:.0f}%", 
                "Strength": get_trend_strength(safe, len(ps))
            })
        
        if intel_data:
            st.table(pd.DataFrame(intel_data))

    with tab2:
        st.header("Situational Heat Map") #
        dd_summary = df.groupby(down_col)[type_col].value_counts(normalize=True).unstack().fillna(0) * 100
