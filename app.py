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
    # Improved safety check for the logo
    try:
        st.image("logo.png", width=150)
    except:
        st.subheader("🏈 Carlsbad Football")
    
    st.title("Lancer-Bot v2.2")
    st.info("AI Defensive Intelligence")

st.title("🏈 Offensive Identity Report")
uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    # Mapping
    gain_col = 'GN/LS'
    type_col = 'PLAY TYPE'
    down_col = 'DN'
    odk_col  = 'ODK'
    play_col = 'OFF PLAY'
    pers_col = 'PERSONNEL'
    form_col = 'OFF FORM-offensive formation'

    # Cleaning
    df[type_col] = df[type_col].str.upper().str.strip()
    df[gain_col] = pd.to_numeric(df[gain_col], errors='coerce')
    df['Prev_Play_Type'] = df[type_col].shift(1)
    df['Prev_Gain'] = df[gain_col].shift(1)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Intelligence", "Situational", "Danger Plays", "Formations", "Personnel"])

    with tab1:
        st.header("AI Intelligence Alerts")
        intel_data = []
        offense_only = df[df[odk_col].str.contains('O', na=False, case=False)].head(10)
        if not offense_only.empty:
            run_c = (offense_only[type_col] == 'RUN').sum()
            intel_data.append({"Category": "Opening Script", "Insight": "Drive 1 Run Freq", "Stat": f"{(run_c/len(offense_only))*100:.0f}%", "Strength": get_trend_strength(run_c, len(offense_only))})
        
        ps = df[(df['Prev_Play_Type'] == 'PASS') & (df['Prev_Gain'] <= -4)]
        if not ps.empty:
            safe = (df.loc[ps.index, type_col] == 'RUN').sum()
            intel_data.append({"Category": "Sequence", "Insight": "Post-Sack Safe Response", "Stat": f"{(safe/len(ps))*100:.0f}%", "Strength": get_trend_strength(safe, len(ps))})
        
        if intel_data:
            st.table(pd.DataFrame(intel_data))

    with tab2:
        st.header("Situational Heat Map")
        clean_df = df[df[type_col].isin(['RUN', 'PASS'])]
        if not clean_df.empty:
            dd_summary = clean_df.groupby(down_col)[type_col].value_counts(normalize=True).unstack().fillna(0) * 100
            try:
                st.dataframe(dd_summary.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
            except ImportError:
                st.dataframe(dd_summary.format("{:.0f}%"))
                st.warning("Install 'matplotlib' to enable heat map colors.")

    with tab3:
        st.header("Top Yardage Producers")
        if play_col in df.columns:
            danger = df.groupby(play_col)[gain_col].agg(['mean', 'count']).sort_values(by='mean', ascending=False).head(5)
            danger.columns = ['Avg Gain', 'Times Run']
            st.table(danger)

    with tab4:
        st.header("Formation Tells")
        if form_col in df.columns:
            f_df = df[df[type_col].isin(['RUN', 'PASS'])]
            form_analysis = f_df.groupby(form_col)[type_col].value_counts(normalize=True).unstack().fillna(0) * 100
            try:
                st.dataframe(form_analysis.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
            except:
                st.dataframe(form_analysis)

    with tab5:
        st.header("Personnel Matrix")
        if pers_col in df.columns:
            p_df = df[df[type_col].isin(['RUN', 'PASS'])]
            pers_analysis = p_df.groupby(pers_col)[type_col].value_counts(normalize=True).unstack().fillna(0) * 100
            try:
                st.dataframe(pers_analysis.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
            except:
                st.dataframe(pers_analysis)
            st.bar_chart(df[pers_col].value_counts())
else:
    st.info("Upload a Hudl CSV to see your full Lancer-Bot report.")
    
