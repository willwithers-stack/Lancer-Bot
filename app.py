import streamlit as st
import pandas as pd
import re
import os

# --- 1. CORE LOGIC ---
def process_offensive_logic(formation):
    f = str(formation).upper().strip()
    match = re.match(r'^(\d)(\d)', f)
    if match:
        pers = f"{match.group(1)}{match.group(2)}"
    else:
        if any(x in f for x in ["HEAVY", "JUMBO", "BIG"]): pers = "23"
        elif "EMPTY" in f: pers = "00"
        elif "DUBS" in f or "TRIPS" in f: pers = "10"
        else: pers = "11"
    return pers

# --- 2. UI SETUP ---
st.set_page_config(page_title="Carlsbad Football Analytics", page_icon="🏈", layout="wide")

# Sidebar - Logo Robust Pathing
with st.sidebar:
    logo_path = os.path.join(os.getcwd(), "logo.png")
    if os.path.exists(logo_path):
        st.image(logo_path, use_container_width=True)
    else:
        try:
            st.image("logo.png", use_container_width=True)
        except:
            st.subheader("🏈 CARLSBAD FOOTBALL")

st.title("🏈 Carlsbad Football Analytics")

uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = [str(c).strip() for c in df.columns]
    
    cols = {'type': 'PLAY TYPE', 'form': 'OFF FORM', 'gain': 'GN/LS', 
            'dn': 'DN', 'dist': 'DIST', 'play': 'OFF PLAY', 'field': 'YARD LN'}
    
    if all(cols[k] in df.columns for k in ['type', 'form', 'gain']):
        df[cols['type']] = df[cols['type']].str.upper().str.strip()
        df[cols['gain']] = pd.to_numeric(df[cols['gain']], errors='coerce').fillna(0)
        df['PERSONNEL'] = df[cols['form']].apply(process_offensive_logic)
        p_data = df[df[cols['type']].isin(['RUN', 'PASS'])].copy()

        # Situational Logic
        def get_sit(row):
            d, dist = row[cols['dn']], row[cols['dist']]
            if d == 1: return "1st & 10 (Baseline)" if dist >= 10 else "1st & <10"
            if d == 2:
                if dist <= 4: return "2nd & Short (1-4)"
                if dist >= 7: return "2nd & Long (7+)"
                return "2nd & Mid"
            if d == 3:
                if dist <= 3: return "3rd & Short (1-3)"
                if 4 <= dist <= 7: return "3rd Down (4-7)"
                if dist >= 7: return "3rd & Long (7+)"
            if d == 4:
                return "4th & Short (1-3)" if dist <= 3 else "4th & Long"
            return f"{int(d)} Down Other"

        p_data['Situation'] = p_data.apply(get_sit, axis=1)

        # TAB LAYOUT
        tabs = st.tabs(["📉 Situational Tells", "🎯 3rd Down Analytics", "🧪 Identity Pivot", "🤖 AI Intelligence"])

        with tabs[0]: # SITUATIONAL TELLS (HEAT MAPS)
            st.header("Down & Distance Play Tells")
            dd = p_data.groupby('Situation')[cols['type']].value_counts().unstack().fillna(0)
            if not dd.empty:
                row_sums = dd.sum(axis=1, numeric_only=True)
                dd['Run %'] = (dd['RUN'] / row_sums * 100).round(0).astype(int)
                dd['Pass %'] = 100 - dd['Run %']
                st.dataframe(dd.style.background_gradient(cmap='RdYlGn_r', subset=['Run %', 'Pass %']).format("{0}%", subset=['Run %', 'Pass %']))

        with tabs[1]: # 3RD DOWN ANALYTICS
            st.header("3rd Down Play Calls & Efficiency")
            t3 = p_data[p_data[cols['dn']] == 3].copy()
            if not t3.empty:
                c1, c2 = st.columns(2)
                with c1:
                    t3_mat = t3.groupby('Situation')[cols['type']].value_counts().unstack().fillna(0)
                    r3_sum = t3_mat.sum(axis=1, numeric_only=True)
                    t3_mat['Run %'] = (t3_mat['RUN'] / r3_sum * 100).round(0).astype(int)
                    t3_mat['Pass %'] = 100 - t3_mat['Run %']
                    st.table(t3_mat.style.format({"Run %": "{0}%", "Pass %": "{0}%"}))
                with c2:
                    st.subheader("3rd Down Concept Usage")
                    st.table(t3[cols['play']].value_counts().head(5))

        with tabs[2]: # IDENTITY PIVOT [cite: 1014, 1020]
            st.header("Personnel & Full Formation Usage")
            st.subheader("Formation Usage (Off Form)")
            st.table(p_data[cols['form']].value_counts().head(10).to_frame(name="Plays"))
            
            st.subheader("Personnel Group Distribution")
            pers_dist = p_data.groupby('PERSONNEL')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
            st.dataframe(pers_dist.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))

        with tabs[3]: # AI INTELLIGENCE (CONFIDENCE METER)
            st.header("🤖 AI Scouting Intelligence")
            
            # Mid-Field Insight
            if cols['field'] in df.columns:
                mid = p_data[(p_data[cols['field']] >= 21) & (p_data[cols['field']] <= 50)]
                if not mid.empty:
                    rate = (mid[cols['type']] == 'RUN').mean() * 100
                    st.subheader("Mid-Field Tendency (Own 21-50)")
                    st.write(f"Offense runs the ball **{rate:.0f}%** of the time in this zone.")
                    st.select_slider("Confidence Meter", options=["Low", "Medium", "High", "Lock"], value="High" if rate > 75 else "Medium", disabled=True)

            st.divider()
            st.subheader("First Down Pass Efficiency")
            fd_pass = p_data[(p_data[cols['dn']] == 1) & (p_data[cols['type']] == 'PASS')]
            if not fd_pass.empty:
                st.metric("1st Down Pass Avg", f"{fd_pass[cols['gain']].mean():.1f} yds", help="Target Efficiency: 12.6 yds")
                st.write(f"Backbone Passes: **Quick Pass, Play Action**")

            st.subheader("Explosive Pass Rate by Down")
            pass_data = p_data[p_data[cols['type']] == 'PASS'].copy()
            pass_data['Explosive'] = pass_data[cols['gain']] >= 20
            st.table(pass_data.groupby(cols['dn'])['Explosive'].mean().mul(100).to_frame("% Explosive Rate").map("{:.0f}%".format))

    else:
        st.error(f"Missing required columns: {list(cols.values())}")
