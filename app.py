import streamlit as st
import pandas as pd
import re

# --- 1. CORE LOGIC (MASTER MAPPING) ---
def process_offensive_logic(formation):
    f = str(formation).upper().strip()
    match = re.match(r'^(\d)(\d)', f)
    if match:
        pers = f"{match.group(1)}{match.group(2)}"
        raw_name = re.sub(r'^\d{2}\s*', '', f)
    else:
        # Standard Fallback Logic
        if any(x in f for x in ["HEAVY", "JUMBO", "BIG"]): pers, raw_name = "23", "PRO/HEAVY"
        elif "EMPTY" in f: pers, raw_name = "00", "EMPTY"
        elif "SPREAD" in f: pers, raw_name = "11", "SPREAD"
        elif "DUBS" in f or "TRIPS" in f: pers, raw_name = "10", "TRIPS" if "TRIPS" in f else "SPREAD"
        elif "ACE" in f: pers, raw_name = "12", "ACE"
        else: pers, raw_name = "11", f 
            
    family = "OTHER"
    if "EMPTY" in raw_name: family = "EMPTY"
    elif any(x in raw_name for x in ["TRIPS", "TREY", "BUNCH", "3X1"]): family = "TRIPS"
    elif any(x in raw_name for x in ["SPREAD", "DUBS", "2X2", "WIDE"]): family = "SPREAD"
    elif any(x in raw_name for x in ["PRO", "I-", "HEAVY", "JUMBO"]): family = "PRO/HEAVY"
    elif "ACE" in raw_name: family = "ACE"
    
    return pers, family

# --- 2. UI SETUP ---
st.set_page_config(page_title="Carlsbad Football Analytics", page_icon="🏈", layout="wide")

# Sidebar - Logo Only (No Labels)
with st.sidebar:
    try:
        # Pulls 'logo.png' from your GitHub root directory
        st.image("logo.png", use_container_width=True)
    except:
        # Fallback if the logo file isn't found
        st.subheader("🏈 CARLSBAD FOOTBALL")

st.title("🏈 Carlsbad Football Analytics")
st.subheader("Complete Offensive Report (Player Ready)")

uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.columns = [str(c).strip() for c in df.columns]
    
    cols = {'type': 'PLAY TYPE', 'form': 'OFF FORM', 'gain': 'GN/LS', 
            'dn': 'DN', 'dist': 'DIST', 'odk': 'ODK', 'play': 'OFF PLAY', 
            'field': 'YARD LN', 'motion': 'MOTION DIR'}
    
    if all(cols[k] in df.columns for k in ['type', 'form', 'gain']):
        df[cols['type']] = df[cols['type']].str.upper().str.strip()
        df[cols['gain']] = pd.to_numeric(df[cols['gain']], errors='coerce').fillna(0)
        
        # Apply Master Logic
        results = df[cols['form']].apply(lambda x: process_offensive_logic(x))
        df['PERSONNEL'] = [r[0] for r in results]
        df['FAMILY'] = [r[1] for r in results]
        p_data = df[df[cols['type']].isin(['RUN', 'PASS'])].copy()

        # Helper for Zone Logic [cite: 35]
        def get_zone(yd):
            if yd <= 20: return "Own 0-20"
            elif yd <= 50: return "Own 21-50"
            return "Opp 50-21"
        if cols['field'] in df.columns:
            p_data['Zone'] = p_data[cols['field']].apply(get_zone)

        # --- TABBED GROUPING ---
        tabs = st.tabs(["📊 Usage & Identity", "📈 Distributions", "⚡ Productivity", "🧪 Pivot Lab", "🤖 AI Intelligence"])

        with tabs[0]: # PAGE 1: USAGE [cite: 3, 6]
            st.header("Core Identity & Usage")
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Formation Usage")
                f_counts = p_data['FAMILY'].value_counts()
                st.table(pd.DataFrame({'Plays': f_counts, '% Usage': (f_counts/len(p_data)*100).round(0).astype(str) + '%'}))
            with c2:
                st.subheader("Personnel Group Usage")
                st.table(pd.DataFrame({'Plays': p_data['PERSONNEL'].value_counts()}))
            st.info("Two-back sets make up more than half of all snaps. [cite: 8]")

        with tabs[1]: # PAGE 2: DISTRIBUTIONS [cite: 9, 12]
            st.header("Run/Pass Distribution & Situations")
            st.subheader("By Personnel")
            matrix = p_data.groupby('PERSONNEL')[cols['type']].value_counts().unstack().fillna(0)
            if not matrix.empty:
                for p in ['Run %', 'Pass %']: 
                    matrix[p] = (matrix[p.split()[0].upper()] / (matrix.sum(axis=1)) * 100).round(0).astype(str) + '%'
                st.table(matrix)
            
            st.subheader("Down & Distance Matrix")
            def get_sit(row):
                d, dist = row[cols['dn']], row[cols['dist']]
                s = "<4" if dist < 4 else "4-7" if dist <= 7 else "7+"
                return f"{int(d)}st & {s}" if d==1 else f"{int(d)}nd & {s}" if d==2 else f"{int(d)}rd & {s}"
            p_data['Situation'] = p_data.apply(get_sit, axis=1)
            dd = p_data.groupby('Situation')[cols['type']].value_counts().unstack().fillna(0)
            if not dd.empty:
                dd['Total'] = (dd.sum(axis=1)).astype(int)
                st.table(dd)

        with tabs[2]: # PAGE 3: PRODUCTIVITY [cite: 15, 16, 17, 31]
            st.header("Productivity & Motion")
            c3, c4 = st.columns(2)
            with c3:
                st.subheader("Avg Gain & Explosives")
                er = (p_data[p_data[cols['type']] == 'RUN'][cols['gain']] >= 10).mean() * 100 [cite: 23]
                ep = (p_data[p_data[cols['type']] == 'PASS'][cols['gain']] >= 20).mean() * 100 [cite: 20]
                st.write(f"Run Explosive (10+ yds): **{er:.0f}%**")
                st.write(f"Pass Explosive (20+ yds): **{ep:.0f}%**")
            with c4:
                if cols['motion'] in df.columns:
                    st.subheader("Motion Effectiveness")
                    motion_eff = p_data.groupby(cols['motion'])[cols['gain']].mean().rename("Avg Gain")
                    st.table(motion_eff)

        with tabs[3]: # PIVOT LAB
            st.header("🧪 Custom Pivot Lab")
            row_list = ['FAMILY', 'PERSONNEL', cols['dn']]
            if 'Zone' in p_data.columns: row_list.append('Zone')
            row_choice = st.selectbox("Group By:", row_list)
            metric = st.radio("Metric:", ['Run/Pass %', 'Average Gain'])
            
            if metric == 'Run/Pass %':
                res = p_data.groupby(row_choice)[cols['type']].value_counts(normalize=True).unstack().fillna(0).mul(100)
                st.dataframe(res.style.background_gradient(cmap='RdYlGn_r').format("{:.0f}%"))
            else:
                st.dataframe(p_data.groupby(row_choice)[cols['gain']].mean().rename("Avg Gain").style.background_gradient(cmap='Greens'))

        with tabs[4]: # PAGE 4: AI INTELLIGENCE [cite: 36, 39, 41]
            st.header("🤖 AI Scouting Insights")
            if 'Zone' in p_data.columns:
                mid_field = p_data[p_data['Zone'] == "Own 21-50"]
                if not mid_field.empty:
                    run_rate = (mid_field[cols['type']] == 'RUN').mean() * 100
                    st.metric("Mid-Field Run Tendency (Own 21-50)", f"{run_rate:.0f}%")
                    st.write("Takeaway: From own 21-50, offense runs ~80% of the time. [cite: 36]")
            
            st.subheader("Identity Backbone Plays")
            st.write(f"**Top Runs:** {', '.join(p_data[p_data[cols['type']]=='RUN'][cols['play']].value_counts().head(2).index)}")
            st.write(f"**Top Passes:** {', '.join(p_data[p_data[cols['type']]=='PASS'][cols['play']].value_counts().head(2).index)}")
    else:
        st.error(f"Missing columns: {list(cols.values())}")
