import streamlit as st
import pandas as pd

# --- 1. THE DECODER LOGIC ---
def decode_personnel(backfield, formation):
    """Standard Numbering System: 1st Digit = RBs | 2nd Digit = TEs"""
    bf, form = str(backfield).upper().strip(), str(formation).upper().strip()
    rb, te = "1", "0" 
    # RB Logic
    if any(x in bf for x in ["2RB", "PRO", "SPLIT", "FULL", "I-FORM"]): rb = "2"
    elif any(x in bf for x in ["0RB", "EMPTY"]): rb = "0"
    # TE Logic
    if any(x in form for x in ["2TE", "HEAVY", "JUMBO", "HB"]): te = "2"
    elif any(x in form for x in ["1TE", "WING", "Y-TRIPS", "ACE", "TIGHT"]): te = "1"
    return f"{rb}{te}"

def get_trend_strength(count, total):
    if total < 3: return "⭐"
    pct = (count / total) * 100
    if pct >= 85 and total >= 6: return "⭐⭐⭐⭐⭐"
    return "⭐⭐⭐" if pct >= 60 else "⭐⭐"

# --- 2. THE UI & BRANDING ---
st.set_page_config(page_title="Lancer-Bot Pro", page_icon="🏈", layout="wide")

with st.sidebar:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            st.image("logo.png", use_container_width=True)
        except Exception:
            st.subheader("🏈 Lancer-Bot")
    st.divider()
    st.title("Lancer-Bot v2.21")
    st.info("System: Full Intelligence Active")

st.title("🏈 Offensive Identity Report")
uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    # 'latin1' handles Hudl's CSV quirks
    df = pd.read_csv(uploaded_file, encoding='latin1')
    df.columns = [str(c).strip() for c in df.columns]
    
    # Exact Mapping
    type_col, gain_col, form_col, bf_col, play_col, down_col, odk_col = \
        'PLAY TYPE', 'GN/LS', 'OFF FORM', 'BACKFIELD', 'OFF PLAY', 'DN', 'ODK'

    if all(col in df.columns for col in [type_col, gain_col, form_col, bf_col]):
        # Data Cleaning
        df[type_col] = df[type_col].astype(str).str.upper().str.strip()
        df[gain_col] = pd.to_numeric(df[gain_col], errors='coerce')
        if odk_col in df.columns:
            df = df[df[odk_col].str.contains('O', na=False, case=False)]
        
        # Apply Personnel Logic & Sequences
        df['PERS_CODE'] = df.apply(lambda x: decode_personnel(x[bf_col], x[form_col]), axis=1)
        df['Prev_Type'] = df[type_col].shift(1)
        df['Prev_Gain'] = df[gain_col].shift(1)

        tabs = st.tabs(["Intelligence", "Situational", "Danger Plays", "Formations", "Personnel", "Pivot Lab"])

        with tabs[0]: # Intelligence
            st.header("AI Intelligence Alerts")
            intel = []
            scr = df.head(10)
            if not scr.empty:
                run_c = (scr[type_col] == 'RUN').sum()
                intel.append({"Category": "Script", "Insight": "Opening Run Freq", "Stat": f"{(run_c/len(scr))*100:.0f}%", "Strength": get_trend_strength(run_c, len(scr))})
            ps = df[(df['Prev_Type'] == 'PASS') & (df['Prev_Gain'] <= -4)]
            if not ps.empty:
                safe = (df.loc[ps.index, type_col] == 'RUN').sum()
                intel.append({"Category": "Sequence", "Insight": "Post-Sack Response", "Stat": f"{(safe/len(ps))*100:.0f}%", "Strength": get_trend_strength(safe, len(ps))})
            st.table(pd.DataFrame(intel))

        with tabs[1]: # Situational
            st.header("Situational Heat Map")
            clean = df[df[type_col].isin(['RUN', 'PASS'])]
            if not clean.empty:
                st.dataframe(clean.groupby(down_col)[type_col].value_counts(normalize=True).unstack().fillna(0).mul(100).style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))

        with tabs[2]: # Danger Plays
            st.header("Top Yardage Producers")
            if play_col in df.columns:
                danger = df.groupby(play_col)[gain_col].agg(['mean', 'count']).sort_values(by='mean', ascending=False).head(5)
                danger.columns = ['Avg Gain', 'Times Run']
                st.table(danger)

        with tabs[3]: # Formations
            st.header("Formation Tells")
            f_stats = clean.groupby(form_col)[type_col].value_counts(normalize=True).unstack().fillna(0).mul(100)
            st.dataframe(f_stats.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))

        with tabs[4]: # Personnel
            st.header("Personnel Matrix")
            p_stats = clean.
