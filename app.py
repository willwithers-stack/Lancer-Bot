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
    try:
        st.image("logo.png", width=150)
    except:
        st.subheader("🏈 Carlsbad Football")
    st.title("Lancer-Bot v2.5")

st.title("🏈 Offensive Identity Report")
uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    # IMPROVED FUZZY MAPPING [cite: 4, 7]
    def find_col(possible_names):
        for col in df.columns:
            # Check for exact matches or common Hudl substrings
            if any(name.upper() in col.upper() for name in possible_names):
                return col
        return None

    gain_col = find_col(['GN/LS', 'GAIN', 'GN'])
    type_col = find_col(['PLAY TYPE', 'TYPE'])
    down_col = find_col(['DN', 'DOWN'])
    pers_col = find_col(['PERSONNEL', 'PERS'])
    form_col = find_col(['OFF FORM', 'FORMATION', 'FORM'])
    odk_col  = find_col(['ODK'])
    play_col = find_col(['OFF PLAY', 'PLAY'])

    if type_col and gain_col:
        # Standardize Data [cite: 10, 11]
        df[type_col] = df[type_col].str.upper().str.strip()
        df[gain_col] = pd.to_numeric(df[gain_col], errors='coerce')
        df['Prev_Play_Type'] = df[type_col].shift(1)
        df['Prev_Gain'] = df[gain_col].shift(1)

        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "Intelligence", "Situational", "Danger Plays", "Formations", "Personnel", "Pivot Lab"
        ])

        with tab1:
            st.header("AI Intelligence Alerts")
            intel_data = []
            offense_only = df[df[odk_col].str.contains('O', na=False, case=False)].head(10) if odk_col else pd.DataFrame()
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
            st.header("Situational Heat Map [cite: 13]")
            clean_df = df[df[type_col].isin(['RUN', 'PASS'])]
            if down_col and not clean_df.empty:
                dd_summary = clean_df.groupby(down_col)[type_col].value_counts(normalize=True).unstack().fillna(0) * 100
                st.dataframe(dd_summary.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))

        with tab3:
            st.header("Top Yardage Producers [cite: 16]")
            if play_col:
                danger = df.groupby(play_col)[gain_col].agg(['mean', 'count']).sort_values(by='mean', ascending=False).head(5)
                danger.columns = ['Avg Gain', 'Times Run']
                st.table(danger)

        with tab4:
            st.header("Formation Tells [cite: 4, 25]")
            if form_col:
                f_df = df[df[type_col].isin(['RUN', 'PASS'])]
                form_analysis = f_df.groupby(form_col)[type_col].value_counts(normalize=True).unstack().fillna(0) * 100
                st.dataframe(form_analysis.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))

        with tab5:
            st.header("Personnel Matrix [cite: 7, 9]")
            if pers_col:
                p_df = df[df[type_col].isin(['RUN', 'PASS'])]
                pers_analysis = p_df.groupby(pers_col)[type_col].value_counts(normalize=True).unstack().fillna(0) * 100
                st.dataframe(pers_analysis.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))

        with tab6:
            st.header("🧪 Custom Pivot Lab")
            # Remove Play # from choices to keep analysis clean [cite: 55-64]
            breakdown_options = [c for c in [pers_col, form_col, down_col, play_col] if c and "PLAY #" not in c.upper()]
            group_choice = st.selectbox("Breakdown by:", breakdown_options)
            metric_choice = st.selectbox("Analyze this metric:", [gain_col, type_col])
            
            if group_choice and metric_choice:
                if metric_choice == gain_col:
                    pivot_data = df.groupby(group_choice)[gain_col].agg(['mean', 'count']).sort_values(by='mean', ascending=False)
                    # Correct labels to avoid "Play count in yards" 
                    st.write(f"### {group_choice} Performance")
                    st.dataframe(
                        pivot_data.style.format({'mean': '{:.1f} yds', 'count': '{:.0f} plays'})
                        .background_gradient(subset=['mean'], cmap='Greens')
                    )
                else:
                    pivot_data = df.groupby(group_choice)[type_col].value_counts(normalize=True).unstack().fillna(0) * 100
                    st.dataframe(pivot_data.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
    else:
        st.error("Could not find 'Play Type' or 'Gain' columns. Check your CSV headers.")

else:
    st.info("Upload a Hudl CSV to begin.")
