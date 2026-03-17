import streamlit as st
import pandas as pd

# --- 1. CORE LOGIC & DECODERS ---
def decode_personnel(backfield, formation):
    """Standard Numbering System: 1st Digit = RBs | 2nd Digit = TEs"""
    bf, form = str(backfield).upper().strip(), str(formation).upper().strip()
    rb, te = "?", "?"
    if any(x in bf for x in ["2RB", "PRO", "SPLIT", "FULL", "I-FORM"]): rb = "2"
    elif any(x in bf for x in ["1RB", "GUN", "PISTOL", "SINGLEBACK"]): rb = "1"
    elif any(x in bf for x in ["0RB", "EMPTY"]): rb = "0"
    
    if any(x in form for x in ["2TE", "HEAVY", "JUMBO", "HB"]): te = "2"
    elif any(x in form for x in ["1TE", "WING", "Y-TRIPS", "ACE"]): te = "1"
    elif any(x in form for x in ["0TE", "SPREAD", "DUBS", "EMPTY", "4WR"]): te = "0"
    return f"{rb}{te}"

def get_trend_strength(count, total):
    if total < 3: return "⭐"
    pct = (count / total) * 100
    if pct >= 85 and total >= 6: return "⭐⭐⭐⭐⭐"
    return "⭐⭐⭐" if pct >= 60 else "⭐⭐"

# --- 2. UI SETUP ---
st.set_page_config(page_title="Lancer-Bot Pro", page_icon="🏈", layout="wide")
with st.sidebar:
    try: st.image("logo.png", width=150)
    except: st.subheader("🏈 Carlsbad Football")
    st.title("Lancer-Bot v2.18")

st.title("🏈 Offensive Identity Report")
uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = [str(c).strip() for c in df.columns]
    
    # --- EXACT HUDL MAPPING  ---
    map = {'TYPE': 'PLAY TYPE', 'GAIN': 'GN/LS', 'FORM': 'OFF FORM', 
           'PLAY': 'OFF PLAY', 'DN': 'DN', 'BF': 'BACKFIELD', 'ODK': 'ODK'}

    if all(map[k] in df.columns for k in ['TYPE', 'GAIN', 'FORM', 'BF']):
        # Clean Data
        df[map['TYPE']] = df[map['TYPE']].str.upper().str.strip()
        df[map['GAIN']] = pd.to_numeric(df[map['GAIN']], errors='coerce')
        if map['ODK'] in df.columns:
            df = df[df[map['ODK']].str.contains('O', na=False, case=False)]
        
        # Apply Personnel Logic
        df['PERS_CODE'] = df.apply(lambda x: decode_personnel(x[map['BF']], x[map['FORM']]), axis=1)
        df['Prev_Type'] = df[map['TYPE']].shift(1)
        df['Prev_Gain'] = df[map['GAIN']].shift(1)

        tabs = st.tabs(["Intelligence", "Situational", "Danger Plays", "Formations", "Personnel", "Pivot Lab"])

        with tabs[0]: # Intelligence
            st.header("AI Intelligence Alerts")
            intel = []
            scr = df.head(10)
            if not scr.empty:
                run_c = (scr[map['TYPE']] == 'RUN').sum()
                intel.append({"Category": "Script", "Insight": "Opening Run Freq", "Stat": f"{(run_c/len(scr))*100:.0f}%", "Strength": get_trend_strength(run_c, len(scr))})
            
            ps = df[(df['Prev_Type'] == 'PASS') & (df['Prev_Gain'] <= -4)]
            if not ps.empty:
                safe = (df.loc[ps.index, map['TYPE']] == 'RUN').sum()
                intel.append({"Category": "Sequence", "Insight": "Post-Sack Safe Response", "Stat": f"{(safe/len(ps))*100:.0f}%", "Strength": get_trend_strength(safe, len(ps))})
            st.table(pd.DataFrame(intel))

        with tabs[1]: # Situational
            st.header("Situational Heat Map")
            clean = df[df[map['TYPE']].isin(['RUN', 'PASS'])]
            st.dataframe(clean.groupby(map['DN'])[map['TYPE']].value_counts(normalize=True).unstack().fillna(0).mul(100).style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))

        with tabs[2]: # Danger Plays
            st.header("Top Yardage Producers")
            danger = df.groupby(map['PLAY'])[map['GAIN']].agg(['mean', 'count']).sort_values(by='mean', ascending=False).head(5)
            danger.columns = ['Avg Gain', 'Times Run']
            st.table(danger)

        with tabs[3]: # Formations
            st.header("Formation Tells")
            f_stats = clean.groupby(map['FORM'])[map['TYPE']].value_counts(normalize=True).unstack().fillna(0).mul(100)
            st.dataframe(f_stats.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))

        with tabs[4]: # Personnel
            st.header("Personnel Matrix (Standard System)")
            p_stats = clean.groupby('PERS_CODE')[map['TYPE']].value_counts(normalize=True).unstack().fillna(0).mul(100)
            counts = clean['PERS_CODE'].value_counts().rename("Plays")
            st.dataframe(pd.concat([p_stats, counts], axis=1).style.background_gradient(subset=['RUN', 'PASS'], cmap='RdYlGn_r').format({'RUN':'{:.0f}%', 'PASS':'{:.0f}%', 'Plays':'{:.0f}'}))

        with tabs[5]: # Pivot Lab
            st.header("🧪 Custom Pivot Lab")
            group = st.selectbox("Breakdown:", ['PERS_CODE', map['FORM'], map['DN'], map['PLAY']])
            metric = st.selectbox("Metric:", [map['GAIN'], map['TYPE']])
            if metric == map['GAIN']:
                piv = df.groupby(group)[map['GAIN']].agg(['mean', 'count']).sort_values(by='mean', ascending=False)
                st.dataframe(piv.style.format({'mean': '{:.1f} yds', 'count': '{:.0f}'}).background_gradient(subset=['mean'], cmap='Greens'))
            else:
                piv = df.groupby(group)[map['TYPE']].value_counts(normalize=True).unstack().fillna(0).mul(100)
                st.dataframe(piv.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
    else:
        st.error(f"Missing columns. Found: {list(df.columns)}")
