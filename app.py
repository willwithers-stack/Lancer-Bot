import streamlit as st
import pandas as pd

# --- 1. THE LOGIC ---
def get_trend_strength(count, total):
    if total < 3: return "⭐"
    pct = (count / total) * 100
    if pct >= 85 and total >= 6: return "⭐⭐⭐⭐⭐"
    if pct >= 70 and total >= 4: return "⭐⭐⭐⭐"
    return "⭐⭐⭐" if pct >= 60 else "⭐⭐"

def decode_personnel(text):
    text = str(text).upper()
    rb, te = "0", "0"
    if "1RB" in text: rb = "1"
    elif "2RB" in text: rb = "2"
    if "1TE" in text: te = "1"
    elif "2TE" in text: te = "2"
    elif "0TE" in text or "OTE" in text: te = "0"
    return f"{rb}{te} Personnel"

# --- 2. THE UI & BRANDING ---
st.set_page_config(page_title="Lancer-Bot Pro", page_icon="🏈", layout="wide")

with st.sidebar:
    try:
        st.image("logo.png", width=150)
    except:
        st.subheader("🏈 Carlsbad Football")
    st.title("Lancer-Bot v2.9")
    st.divider()
    st.write("### 🔍 System Diagnostics")

st.title("🏈 Offensive Identity Report")
uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    # Clean column names for search
    raw_cols = df.columns.tolist()
    
    # --- BULLETPROOF MAPPING ---
    def find_best_col(keywords):
        for col in raw_cols:
            if any(k.upper() in col.upper() for k in keywords):
                return col
        return None

    # Mapping to your specific Hudl export style [cite: 4, 7, 10]
    gain_col = find_best_col(['GN/LS', 'GAIN', 'GN'])
    type_col = find_best_col(['PLAY TYPE', 'TYPE'])
    down_col = find_best_col(['DN', 'DOWN'])
    pers_col = find_best_col(['PERSONNEL', 'PERS'])
    form_col = find_best_col(['FORM', 'FORMATION'])
    odk_col  = find_best_col(['ODK'])
    play_col = find_best_col(['OFF PLAY', 'PLAY'])

    # Log found columns in sidebar for troubleshooting
    with st.sidebar:
        st.write(f"✅ Gain: `{gain_col}`")
        st.write(f"✅ Type: `{type_col}`")
        st.write(f"✅ Personnel: `{pers_col}`")
        st.write(f"✅ Formation: `{form_col}`")

    if type_col and gain_col:
        # Standardize Data [cite: 10, 21]
        df[type_col] = df[type_col].str.upper().str.strip()
        df[gain_col] = pd.to_numeric(df[gain_col], errors='coerce')
        
        # Filter for ODK = 'O' to ensure we only analyze offense 
        if odk_col:
            df = df[df[odk_col].str.contains('O', na=False, case=False)]

        df['Prev_Play_Type'] = df[type_col].shift(1)
        df['Prev_Gain'] = df[gain_col].shift(1)

        tabs = st.tabs(["Intelligence", "Situational", "Danger Plays", "Formations", "Personnel", "Pivot Lab"])

        with tabs[0]: # Intelligence
            intel_data = []
            offense_only = df.head(10)
            if not offense_only.empty:
                run_c = (offense_only[type_col] == 'RUN').sum()
                intel_data.append({"Category": "Opening Script", "Insight": "Drive 1 Run Freq", "Stat": f"{(run_c/len(offense_only))*100:.0f}%", "Strength": get_trend_strength(run_c, len(offense_only))})
            
            ps = df[(df['Prev_Play_Type'] == 'PASS') & (df['Prev_Gain'] <= -4)]
            if not ps.empty:
                safe = (df.loc[ps.index, type_col] == 'RUN').sum()
                intel_data.append({"Category": "Sequence", "Insight": "Post-Sack Safe Response", "Stat": f"{(safe/len(ps))*100:.0f}%", "Strength": get_trend_strength(safe, len(ps))})
            
            if intel_data:
                st.table(pd.DataFrame(intel_data))

        with tabs[4]: # Personnel Tab
            st.header("Personnel Matrix & Tendency Alerts")
            if pers_col:
                df['PERS_CODE'] = df[pers_col].apply(decode_personnel)
                p_df = df[df[type_col].isin(['RUN', 'PASS'])]
                
                pers_stats = p_df.groupby('PERS_CODE')[type_col].value_counts(normalize=True).unstack().fillna(0) * 100
                counts = p_df['PERS_CODE'].value_counts()

                for group in pers_stats.index:
                    if counts[group] >= 5: # 
                        run_pct = pers_stats.loc[group, 'RUN'] if 'RUN' in pers_stats.columns else 0
                        pass_pct = pers_stats.loc[group, 'PASS'] if 'PASS' in pers_stats.columns else 0
                        if run_pct >= 90: st.error(f"🚨 **RED FLAG:** {group} is {run_pct:.0f}% RUN")
                        elif pass_pct >= 90: st.error(f"🚨 **RED FLAG:** {group} is {pass_pct:.0f}% PASS")

                st.dataframe(pers_stats.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
                st.bar_chart(counts)
            else:
                st.warning("No Personnel column found in CSV.")

        # [Other tabs Situational, Danger Plays, Formations follow the same find_best_col logic]
        with tabs[1]:
            st.header("Situational Heat Map")
            if down_col:
                dd_df = df[df[type_col].isin(['RUN', 'PASS'])]
                dd_summary = dd_df.groupby(down_col)[type_col].value_counts(normalize=True).unstack().fillna(0) * 100
                st.dataframe(dd_summary.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))

        with tabs[3]:
            st.header("Formation Tells")
            if form_col:
                f_df = df[df[type_col].isin(['RUN', 'PASS'])]
                form_stats = f_df.groupby(form_col)[type_col].value_counts(normalize=True).unstack().fillna(0) * 100
                st.dataframe(form_stats.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))

else:
    st.info("Upload a Hudl CSV to see your full scout breakdown.")
