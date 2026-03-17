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
st.set_page_config(page_title="Lancer-Bot Intelligence", page_icon="🏈")
st.title("🏈 Lancer-Bot Intelligence")
st.write("Upload a Hudl CSV to analyze opponent tendencies.")

opponent = st.text_input("Opponent Name", "Carlsbad Rival")
uploaded_file = st.file_uploader("Drop Hudl CSV here", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    # Mapping your specific columns from the logs
    gain_col = 'GN/LS'
    type_col = 'PLAY TYPE'
    down_col = 'DN'
    odk_col  = 'ODK'

    # Check for required columns
    if gain_col not in df.columns or type_col not in df.columns:
        st.error(f"Missing '{gain_col}' or '{type_col}'. Found: {list(df.columns)}")
        st.stop()

    # Create sequence memory
    df['Prev_Play_Type'] = df[type_col].shift(1)
    df['Prev_Gain'] = pd.to_numeric(df[gain_col], errors='coerce').shift(1)
    
    intel_data = []

    # A. Opening Drive (First 10 plays where ODK is 'O')
    offense_only = df[df[odk_col].str.contains('O', na=False, case=False)].head(10)
    if not offense_only.empty:
        run_count = offense_only[type_col].str.contains('RUN', na=False, case=False).sum()
        total = len(offense_only)
        intel_data.append({
            "Category": "Opening Script",
            "Insight": f"Drive 1 Run Frequency ({run_count}/{total})",
            "Stat": f"{(run_count/total)*100:.0f}%",
            "Strength": get_trend_strength(run_count, total)
        })

    # B. Post-Sack Sequence (Pass for loss of 4+)
    ps = df[(df['Prev_Play_Type'].str.contains('PASS', na=False, case=False)) & (df['Prev_Gain'] <= -4)]
    if not ps.empty:
        safe_plays = df.loc[ps.index, type_col].str.contains('RUN', na=False, case=False).sum()
        intel_data.append({
            "Category": "Sequence",
            "Insight": "Post-Sack Safe Response",
            "Stat": f"{(safe_plays/len(ps))*100:.0f}%",
            "Strength": get_trend_strength(safe_plays, len(ps))
        })

    # C. Stalled Run (1st Down Run for 0 or less)
    stalled = df[(df[down_col] == 1) & (df['Prev_Play_Type'].str.contains('RUN', na=False, case=False)) & (df['Prev_Gain'] <= 0)]
    if not stalled.empty:
        pass_plays = df.loc[stalled.index, type_col].str.contains('PASS', na=False, case=False).sum()
        intel_data.append({
            "Category": "Sequence",
            "Insight": "2nd Down Pass after 0yd Run",
            "Stat": f"{(pass_plays/len(stalled))*100:.0f}%",
            "Strength": get_trend_strength(pass_plays, len(stalled))
        })

    # Display Results
    if intel_data:
        st.subheader(f"Intelligence Dashboard: {opponent}")
        st.table(pd.DataFrame(intel_data))
    else:
        st.info("No clear tendencies found in this specific file yet.")
