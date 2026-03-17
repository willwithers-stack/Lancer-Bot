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
st.set_page_config(page_title="Lancer-Bot Full Suite", page_icon="🏈", layout="wide")
st.title("🏈 Lancer-Bot: Full Scout Breakdown")

opponent = st.text_input("Opponent Name", "Carlsbad Rival")
uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    # Specific Hudl Mappings
    gain_col = 'GN/LS'
    type_col = 'PLAY TYPE'
    down_col = 'DN'
    dist_col = 'DIST'
    form_col = 'OFF FORM-offensive formation'
    play_col = 'OFF PLAY'
    odk_col  = 'ODK'

    # Clean data
    df[gain_col] = pd.to_numeric(df[gain_col], errors='coerce')
    df['Prev_Play_Type'] = df[type_col].shift(1)
    df['Prev_Gain'] = df[gain_col].shift(1)
    
    # --- TAB 1: AI INTELLIGENCE ---
    st.header("1. AI Intelligence Alerts")
    intel_data = []
    
    # Opening Drive
    offense_only = df[df[odk_col].str.contains('O', na=False, case=False)].head(10)
    if not offense_only.empty:
        run_c = offense_only[type_col].str.contains('RUN', na=False, case=False).sum()
        intel_data.append({"Category": "Opening Script", "Insight": f"Drive 1 Run Freq", "Stat": f"{(run_c/len(offense_only))*100:.0f}%", "Strength": get_trend_strength(run_c, len(offense_only))})

    # Post-Sack
    ps = df[(df['Prev_Play_Type'].str.contains('PASS', na=False, case=False)) & (df['Prev_Gain'] <= -4)]
    if not ps.empty:
        safe = df.loc[ps.index, type_col].str.contains('RUN', na=False, case=False).sum()
        intel_data.append({"Category": "Sequence", "Insight": "Post-Sack Safe Response", "Stat": f"{(safe/len(ps))*100:.0f}%", "Strength": get_trend_strength(safe, len(ps))})

    st.table(pd.DataFrame(intel_data))

    # --- TAB 2: SITUATIONAL BREAKDOWN ---
    st.header("2. Down & Distance Tendencies")
    dd_summary = df.groupby(down_col)[type_col].value_counts(normalize=True).unstack().fillna(0) * 100
    st.dataframe(dd_summary.style.format("{:.0f}%"))

    # --- TAB 3: DANGER PLAYS ---
    st.header("3. Top Yardage Producers (Danger Plays)")
    danger_plays = df.groupby(play_col)[gain_col].agg(['mean', 'count']).sort_values(by='mean', ascending=False).head(5)
    danger_plays.columns = ['Avg Gain', 'Times Run']
    st.table(danger_plays)

    # --- TAB 4: FORMATION TELLS ---
    st.header("4. Formation Analysis")
    form_analysis = df.groupby(form_col)[type_col].value_counts(normalize=True).unstack().fillna(0) * 100
    st.dataframe(form_analysis.style.format("{:.0f}%"))

else:
    st.info("Please upload a file to see situational, formation, and danger play breakdowns.")
