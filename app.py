import streamlit as st
import pandas as pd

# --- 1. THE LOGIC ---
def get_trend_strength(count, total):
    if total < 3: return "⭐"
    pct = (count / total) * 100
    if pct >= 85 and total >= 6: return "⭐⭐⭐⭐⭐"
    if pct >= 70 and total >= 4: return "⭐⭐⭐⭐"
    return "⭐⭐⭐" if pct >= 60 else "⭐⭐"

# --- 2. THE UI ---
st.set_page_config(page_title="Lancer-Bot Pro", page_icon="🏈", layout="wide")
st.title("🏈 Lancer-Bot: Full Scout Breakdown")

opponent = st.text_input("Opponent Name", "Carlsbad Rival")
uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    # DYNAMIC MAPPING
    col_map = {col.upper().strip(): col for col in df.columns}
    
    gain_col = col_map.get('GN/LS')
    type_col = col_map.get('PLAY TYPE')
    down_col = col_map.get('DN')
    odk_col  = col_map.get('ODK')
    play_col = col_map.get('OFF PLAY')
    
    # Flexible Formation Lookup
    form_col = next((c for c in df.columns if 'FORM' in c.upper()), None)

    if not gain_col or not type_col:
        st.error(f"Required columns missing. Found: {list(df.columns)}")
        st.stop()

    # Clean Data
    df[gain_col] = pd.to_numeric(df[gain_col], errors='coerce')
    df['Prev_Play_Type'] = df[type_col].shift(1)
    df['Prev_Gain'] = df[gain_col].shift(1)

    # --- TABS FOR MOBILE NAVIGATION ---
    tab1, tab2, tab3, tab4 = st.tabs(["Intelligence", "Situational", "Danger Plays", "Formations"])

    with tab1:
        st.header("AI Intelligence Alerts")
        intel_data = []
        offense_only = df[df[odk_col].str.contains('O', na=False, case=False)].head(10)
        if not offense_only.empty:
            run_c = offense_only[type_col].str.contains('RUN', na=False, case=False).sum()
            intel_data.append({"Category": "Opening Script", "Insight": "Drive 1 Run Freq", "Stat": f"{(run_c/len(offense_only))*100:.0f}%", "Strength": get_trend_strength(run_c, len(offense_only))})
        
        ps = df[(df['Prev_Play_Type'].str.contains('PASS', na=False, case=False)) & (df['Prev_Gain'] <= -4)]
        if not ps.empty:
            safe = df.loc[ps.index, type_col].str.contains('RUN', na=False, case=False).sum()
            intel_data.append({"Category": "Sequence", "Insight": "Post-Sack Safe Response", "Stat": f"{(safe/len(ps))*100:.0f}%", "Strength": get_trend_strength(safe, len(ps))})
        
        if intel_data:
            st.table(pd.DataFrame(intel_data))

    with tab2:
        st.header("Down & Distance Tendencies")
        dd_summary = df.groupby(down_col)[type_col].value_counts(normalize=True).unstack().fillna(0) * 100
        st.dataframe(dd_summary.style.format("{:.0f}%"))

    with tab3:
        st.header("Top Yardage Producers")
        if play_col:
            danger_plays = df.groupby(play_col)[gain_col].agg(['mean', 'count']).sort_values(by='mean', ascending=False).head(5)
            danger_plays.columns = ['Avg Gain', 'Times Run']
            st.table(danger_plays)

    with tab4:
        st.header("Formation Analysis")
        if form_col:
            # Group by formation and calculate Run/Pass splits
            form_analysis = df.groupby(form_col)[type_col].value_counts(normalize=True).unstack().fillna(0) * 100
            st.dataframe(form_analysis.style.format("{:.0f}%"))
        else:
            st.warning("No formation column found in this file.")

else:
    st.info("Please upload a file to see the full breakdown.")
