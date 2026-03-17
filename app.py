import streamlit as st
import pandas as pd

# --- 1. THE DECODER LOGIC ---
def decode_personnel(backfield, formation):
    """
    Standard Numbering System:
    1st Digit = # of RBs (from Backfield)
    2nd Digit = # of TEs (from Formation)
    """
    bf = str(backfield).upper().strip()
    form = str(formation).upper().strip()
    
    # --- RB Count (1st Digit) ---
    if any(x in bf for x in ["2RB", "PRO", "SPL", "FULL", "I-FORM", "TWIN"]):
        rb = "2"
    elif any(x in bf for x in ["1RB", "GUN", "PISTOL", "SING", "S-BACK", "OFFSET"]):
        rb = "1"
    elif any(x in bf for x in ["0RB", "EMPTY", "MT"]):
        rb = "0"
    else:
        rb = "1" # Logical default for your spread-heavy identity [cite: 13]

    # --- TE Count (2nd Digit) ---
    if any(x in form for x in ["2TE", "HEAVY", "JUMBO", "HB", "DBL TIGHT"]):
        te = "2"
    elif any(x in form for x in ["1TE", "WING", "Y-TRIPS", "ACE", "TIGHT", "Y-"]):
        te = "1"
    elif any(x in form for x in ["0TE", "SPREAD", "DUBS", "DBLS", "EMPTY", "4WR", "5WR", "TRI"]):
        te = "0"
    else:
        te = "0" # Logical default for your spread-heavy identity [cite: 13]
        
    return f"{rb}{te}"

def get_trend_strength(count, total):
    if total < 3: return "⭐"
    pct = (count / total) * 100
    if pct >= 85 and total >= 6: return "⭐⭐⭐⭐⭐"
    return "⭐⭐⭐" if pct >= 60 else "⭐⭐"

# --- 2. THE UI & BRANDING ---
st.set_page_config(page_title="Lancer-Bot Pro", page_icon="🏈", layout="wide")

with st.sidebar:
    try:
        st.image("logo.png", width=150)
    except:
        st.subheader("🏈 Carlsbad Football")
    st.title("Lancer-Bot v2.19")
    st.info("System Status: Logic Optimized")

st.title("🏈 Offensive Identity Report")
uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    # Exact column cleaning for your Hudl export [cite: 48]
    df.columns = [str(c).strip() for c in df.columns]
    
    # Mapping exact headers [cite: 48]
    map_cols = {
        'type': 'PLAY TYPE',
        'gain': 'GN/LS',
        'form': 'OFF FORM',
        'play': 'OFF PLAY',
        'dn': 'DN',
        'bf': 'BACKFIELD',
        'odk': 'ODK'
    }

    if all(map_cols[k] in df.columns for k in ['type', 'gain', 'form', 'bf']):
        # Clean and Filter Data
        df[map_cols['type']] = df[map_cols['type']].str.upper().str.strip()
        df[map_cols['gain']] = pd.to_numeric(df[map_cols['gain']], errors='coerce')
        if map_cols['odk'] in df.columns:
            df = df[df[map_cols['odk']].str.contains('O', na=False, case=False)]
        
        # Apply Personnel Logic
        df['PERS_CODE'] = df.apply(lambda x: decode_personnel(x[map_cols['bf']], x[map_cols['form']]), axis=1)
        df['Prev_Type'] = df[map_cols['type']].shift(1)
        df['Prev_Gain'] = df[map_cols['gain']].shift(1)

        tabs = st.tabs(["Intelligence", "Situational", "Danger Plays", "Formations", "Personnel Matrix", "Pivot Lab"])

        with tabs[0]: # Intelligence
            st.header("AI Intelligence Alerts")
            intel = []
            scr = df.head(10)
            if not scr.empty:
                run_c = (scr[map_cols['type']] == 'RUN').sum()
                intel.append({"Category": "Script", "Insight": "Opening Run Freq", "Stat": f"{(run_c/len(scr))*100:.0f}%", "Strength": get_trend_strength(run_c, len(scr))})
            st.table(pd.DataFrame(intel))

        with tabs[1]: # Situational Heat Map
            st.header("Situational Heat Map")
            clean = df[df[map_cols['type']].isin(['RUN', 'PASS'])]
            if not clean.empty:
                st.dataframe(clean.groupby(map_cols['dn'])[map_cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100).style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))

        with tabs[2]: # Danger Plays
            st.header("Top Yardage Producers")
            danger = df.groupby(map_cols['play'])[map_cols['gain']].agg(['mean', 'count']).sort_values(by='mean', ascending=False).head(5)
            danger.columns = ['Avg Gain', 'Times Run']
            st.table(danger)

        with tabs[3]: # Formations
            st.header("Formation Tells")
            f_stats = clean.groupby(map_cols['form'])[map_cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
            st.dataframe(f_stats.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))

        with tabs[4]: # Personnel Matrix
            st.header("Personnel Matrix (1st Digit: RBs | 2nd Digit: TEs)")
            p_stats = clean.groupby('PERS_CODE')[map_cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
            counts = clean['PERS_CODE'].value_counts().rename("Plays")
            st.dataframe(pd.concat([p_stats, counts], axis=1).style.background_gradient(subset=['RUN', 'PASS'], cmap='RdYlGn_r').format({'RUN':'{:.0f}%', 'PASS':'{:.0f}%', 'Plays':'{:.0f}'}))
            st.subheader("Decoder Audit (Top 10 Plays)")
            st.table(df[[map_cols['bf'], map_cols['form'], 'PERS_CODE']].head(10))

        with tabs[5]: # Pivot Lab
            st.header("🧪 Custom Pivot Lab")
            group = st.selectbox("Breakdown:", ['PERS_CODE', map_cols['form'], map_cols['dn'], map_cols['play']])
            metric = st.selectbox("Metric:", [map_cols['gain'], map_cols['type']])
            if metric == map_cols['gain']:
                piv = df.groupby(group)[map_cols['gain']].agg(['mean', 'count']).sort_values(by='mean', ascending=False)
                st.dataframe(piv.style.format({'mean': '{:.1f} yds', 'count': '{:.0f}'}).background_gradient(subset=['mean'], cmap='Greens'))
            else:
                piv = df.groupby(group)[map_cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
                st.dataframe(piv.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
    else:
        st.error(f"Missing columns. Found: {list(df.columns)}")
