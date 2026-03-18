import streamlit as st
import pandas as pd
import re
import os
import numpy as np

# --- 1. CORE SCORING LOGIC ---
def process_offensive_logic(formation):
    f = str(formation).upper().strip()
    match = re.match(r'^(\d)(\d)', f)
    if match:
        pers = f"{match.group(1)}{match.group(2)}"
    else:
        if any(x in f for x in ["HEAVY", "JUMBO", "BIG"]):  pers = "23"
        elif "EMPTY" in f:                                    pers = "00"
        elif "DOUBLE Y DOUBLE WING" in f:                    pers = "13"
        elif "TREY" in f:                                     pers = "12"
        elif "DUBS" in f or "TRIPS" in f:                    pers = "10"
        elif "SPREAD" in f or "WING" in f:                   pers = "11"
        else:                                                 pers = "11"
    return pers

def get_stars(percentage):
    if percentage >= 85: return "⭐⭐⭐⭐⭐"
    elif percentage >= 75: return "⭐⭐⭐⭐"
    elif percentage >= 65: return "⭐⭐⭐"
    elif percentage >= 50: return "⭐⭐"
    return "⭐"

# --- 2. UI SETUP ---
st.set_page_config(page_title="Carlsbad Football Analytics", page_icon="🏈", layout="wide")

with st.sidebar:
    logo_files = ["Logo.png", "logo.png"]
    found_logo = False
    for lf in logo_files:
        if os.path.exists(lf):
            st.image(lf, width=150)
            found_logo = True
            break
    if not found_logo:
        st.subheader("🏈 CARLSBAD FOOTBALL")
    st.write("---")
    st.caption("v2.79 Personnel Update")

st.title("🏈 Carlsbad Football Analytics")

uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = [str(c).strip() for c in df.columns]

    cols = {
        'type': 'PLAY TYPE', 'form': 'OFF FORM', 'gain': 'GN/LS',
        'dn': 'DN', 'dist': 'DIST', 'play': 'OFF PLAY', 'field': 'YARD LN',
        'odk': 'ODK', 'hash': 'HASH', 'p_dir': 'PLAY DIR', 'motion': 'MOTION DIR',
        'result': 'RESULT'
    }

    if all(cols[k] in df.columns for k in ['type', 'form', 'gain']):

        df[cols['type']] = df[cols['type']].astype(str).str.upper().str.strip()
        df[cols['gain']] = pd.to_numeric(df[cols['gain']], errors='coerce').fillna(0).round(0).astype(int)
        df[cols['dn']] = pd.to_numeric(df[cols['dn']], errors='coerce').fillna(0).astype(int)
        df[cols['dist']] = pd.to_numeric(df[cols['dist']], errors='coerce').fillna(0).astype(int)
        df[cols['field']] = pd.to_numeric(df[cols['field']], errors='coerce').fillna(0).astype(int)

        df['Drive_ID'] = (df[cols['odk']] != df[cols['odk']].shift()).cumsum()

        p_data = df[df[cols['type']].isin(['RUN', 'PASS'])].copy()
        p_data['PERSONNEL'] = p_data[cols['form']].apply(process_offensive_logic)

        p_data['Is_FD'] = (p_data[cols['gain']] >= p_data[cols['dist']]).astype(int)
        p_data['Is_Int'] = p_data[cols['result']].str.contains('Interception', case=False, na=False).astype(int)

        def calc_succ(row):
            d, dist, g = row[cols['dn']], row[cols['dist']], row[cols['gain']]
            if d == 1: return g >= (dist * 0.45)
            if d == 2: return g >= (dist * 0.65)
            return g >= dist
        p_data['Is_Succ'] = p_data.apply(calc_succ, axis=1).astype(int)

        tabs = st.tabs([
            "📊 Personnel Identity", "🎯 3rd Down Efficiency", "📈 Chain Moving (Freq)",
            "🟢 Red/Green Zone", "🔮 Winning Probability (AI)", "🧪 Custom Pivot Lab", "🏈 Kicking Game"
        ])

        # --- TAB 0: PERSONNEL IDENTITY ---
        with tabs[0]:
            st.header("📊 Personnel Identity")

            pers_counts = p_data['PERSONNEL'].value_counts().to_frame("Plays")
            pers_counts['%'] = (pers_counts['Plays'] / pers_counts['Plays'].sum() * 100).round(0).astype(int)
            st.subheader("Overall Usage")
            st.dataframe(pers_counts, width="stretch")

            st.divider()

            c1, c2 = st.columns(2)
            with c1:
                st.subheader("🏃 Top 5 Run Personnel")
                run_pers = (
                    p_data[p_data[cols['type']] == 'RUN']
                    .groupby('PERSONNEL')
                    .agg(Plays=('PERSONNEL', 'count'), Avg_Gain=(cols['gain'], 'mean'))
                    .sort_values('Plays', ascending=False)
                    .head(5)
                )
                run_pers['Avg_Gain'] = run_pers['Avg_Gain'].round(1)
                run_pers['Run %'] = (run_pers['Plays'] / run_pers['Plays'].sum() * 100).round(0).astype(int)
                st.dataframe(run_pers.style.background_gradient(cmap='RdYlGn', subset=['Avg_Gain']), width="stretch")

            with c2:
                st.subheader("🎯 Top 5 Pass Personnel")
                pass_pers = (
                    p_data[p_data[cols['type']] == 'PASS']
                    .groupby('PERSONNEL')
                    .agg(Plays=('PERSONNEL', 'count'), Avg_Gain=(cols['gain'], 'mean'))
                    .sort_values('Plays', ascending=False)
                    .head(5)
                )
                pass_pers['Avg_Gain'] = pass_pers['Avg_Gain'].round(1)
                pass_pers['Pass %'] = (pass_pers['Plays'] / pass_pers['Plays'].sum() * 100).round(0).astype(int)
                st.dataframe(pass_pers.style.background_gradient(cmap='RdYlGn', subset=['Avg_Gain']), width="stretch")

            st.divider()

            st.subheader("Run/Pass Tendency by Personnel")
            rp_split = (
                p_data.groupby('PERSONNEL')[cols['type']]
                .value_counts(normalize=True)
                .unstack()
                .fillna(0)
                .mul(100)
                .round(0)
                .astype(int)
            )
            st.dataframe(rp_split.style.background_gradient(cmap='RdYlGn_r'), width="stretch")

        # --- TAB 1: 3RD DOWN ---
        with tabs[1]:
            st.header("🎯 3rd Down Efficiency")
            t3 = p_data[p_data[cols['dn']] == 3].copy()
            if not t3.empty:
                st.metric("3rd Down Conversion Rate", f"{round(t3['Is_FD'].mean()*100)}%")
                t3['Sit'] = t3[cols['dist']].apply(
                    lambda x: "3rd & Short (1-3)" if x <= 3 else ("3rd & Mid (4-7)" if x <= 7 else "3rd & Long (7+)")
                )
                c1, c2 = st.columns(2)
                with c1:
                    st.table(t3.groupby('Sit')['Is_FD'].mean().mul(100).round(0).astype(int).to_frame("FD Rate %"))
                with c2:
                    t3_tend = t3.groupby('Sit')[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100).round(0).astype(int)
                    st.dataframe(t3_tend.style.background_gradient(cmap='RdYlGn_r').format("{:d}%"), width="stretch")
                for sit in ["3rd & Short (1-3)", "3rd & Mid (4-7)", "3rd & Long (7+)"]:
                    with st.expander(f"Top 3rd Down Calls: {sit}"):
                        st.table(t3[t3['Sit'] == sit][cols['play']].value_counts().head(3))
            else:
                st.info("No 3rd down plays found.")

        # --- TAB 2: CHAIN MOVING ---
        with tabs[2]:
            st.header("📈 Chain Moving (Frequency)")
            chain = p_data.groupby(cols['play'])['Is_FD'].agg(['sum', 'count'])
            chain.columns = ['First Downs', 'Plays']
            chain['FD Rate %'] = (chain['First Downs'] / chain['Plays'] * 100).round(0).astype(int)
            chain = chain[chain['Plays'] >= 3].sort_values('FD Rate %', ascending=False).head(15)
            st.dataframe(chain.style.background_gradient(cmap='RdYlGn', subset=['FD Rate %']), width="stretch")

        # --- TAB 3: RED/GREEN ZONE ---
        with tabs[3]:
            st.header("🟢 Red/Green Zone")
            rz = p_data[p_data[cols['field']].between(1, 20)].copy()
            gz = p_data[p_data[cols['field']].between(21, 40)].copy()
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("🔴 Red Zone (20-11)")
                if not rz.empty:
                    st.metric("TD/FD Rate", f"{round(rz['Is_FD'].mean()*100)}%")
                    st.table(rz[cols['play']].value_counts().head(5).to_frame("Plays"))
                else:
                    st.info("No red zone plays.")
            with c2:
                st.subheader("🟢 Green Zone (10-1)")
                if not gz.empty:
                    st.metric("Success Rate", f"{round(gz['Is_Succ'].mean()*100)}%")
                    st.table(gz[cols['play']].value_counts().head(5).to_frame("Plays"))
                else:
                    st.info("No green zone plays.")

        # --- TAB 4: WINNING PROBABILITY ---
        with tabs[4]:
            st.header("🔮 Winning Probability (AI)")
            st.metric("Overall FD Rate", f"{round(p_data['Is_FD'].mean()*100)}%")
            st.metric("Overall Success Rate", f"{round(p_data['Is_Succ'].mean()*100)}%")
            st.metric("Interceptions", int(p_data['Is_Int'].sum()))
            st.divider()
            st.subheader("🤖 AI Scouting Intelligence")
            intel = []
            if cols['result'] in df.columns:
                sack_mask = (
                    df[cols['result']].str.contains('Sack', case=False, na=False) |
                    ((df[cols['type']] == 'PASS') & (df[cols['gain']] <= -4))
                )
                post_sack = df.loc[[i+1 for i in df[sack_mask].index if i+1 in df.index]]
                if not post_sack.empty:
                    rate = round((post_sack[cols['type']].str.upper() == 'RUN').mean() * 100)
                    intel.append({"Category": "Sequence", "Insight": "Post-Sack Run Response", "Stat": f"{rate}%", "Strength": get_stars(rate)})
            if intel:
                st.table(pd.DataFrame(intel))
            else:
                st.info("No intelligence signals detected yet.")

        # --- TAB 5: PIVOT LAB ---
        with tabs[5]:
            st.header("🧪 Custom Pivot Lab")
            pivot_cols = [c for c in [cols['dn'], cols['form'], cols['play'], cols['type'], 'PERSONNEL', cols['result']] if c in p_data.columns]
            selected = st.multiselect("Select columns:", options=p_data.columns.tolist(), default=pivot_cols)
            play_filter = st.selectbox("Filter by Play Type:", ["ALL", "RUN", "PASS"])
            view = p_data.copy()
            if play_filter != "ALL":
                view = view[view[cols['type']] == play_filter]
            if selected:
                st.dataframe(view[selected].reset_index(drop=True), width="stretch")

        # --- TAB 6: KICKING GAME ---
        with tabs[6]:
            st.header("🏈 Kicking & Special Teams")
            k_data = df[df[cols['odk']].isin(['K', 'S'])].copy()
            if not k_data.empty:
                st.write("**Special Teams Play Volume**")
                st.table(k_data[cols['type']].value_counts().to_frame("Volume"))
                c_k1, c_k2 = st.columns(2)
                with c_k1:
                    st.subheader("Punt Efficiency")
                    punts = k_data[k_data[cols['type']] == 'PUNT']
                    if not punts.empty:
                        st.write(f"Average Punt Result: **{punts[cols['result']].mode()[0]}**")
                        st.table(punts[cols['result']].value_counts().to_frame("Count"))
                with c_k2:
                    st.subheader("Kickoff (KO) Distribution")
                    kos = k_data[k_data[cols['type']] == 'KO']
                    if not kos.empty:
                        st.table(kos[cols['result']].value_counts().to_frame("Count"))
            else:
                st.info("No kicking/special teams data detected in ODK tags 'K' or 'S'.")

    else:
        st.error(f"Missing required columns: {list(cols.values())}")
