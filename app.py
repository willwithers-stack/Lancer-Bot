import streamlit as st
import pandas as pd
import re

# --- 1. THE BRAIN: YOUR REFINED LOGIC ---
def process_offensive_logic(formation):
    f = str(formation).upper().strip()
    match = re.match(r'^(\d)(\d)', f)
    if match:
        pers = f"{match.group(1)}{match.group(2)}"
        raw_name = re.sub(r'^\d{2}\s*', '', f)
    else:
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
st.set_page_config(page_title="Lancer-Bot Pro", page_icon="🏈", layout="wide")

with st.sidebar:
    st.subheader("🏈 Lancer-Bot v2.37")
    st.write("Metric Profile: **PDF Replica + Pivot**")
    st.info("Logic: Spread=11 | Dubs=10 | Heavy=23")

st.title("🏈 Complete Offensive Report (Player Ready)")
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

        # --- TABBED GROUPING ---
        tabs = st.tabs(["📊 Usage & Identity", "📈 Distributions", "⚡ Productivity", "🧪 Pivot Lab", "🤖 AI Intelligence"])

        with tabs[0]: # PAGE 1: USAGE
            st.header("Core Identity & Usage")
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Formation Usage")
                f_counts = p_data['FAMILY'].value_counts()
                st.table(pd.DataFrame({'Plays': f_counts, '% Usage': (f_counts/len(p_data)*100).round(0).astype(str) + '%'}))
            with c2:
                st.subheader("Personnel Group Usage")
                st.table(pd.DataFrame({'Plays': p_data['PERSONNEL'].value_counts()}))
            st.info("Two-back sets make up more than half of all snaps.")

        with tabs[1]: # PAGE 2: DISTRIBUTIONS
            st.header("Run/Pass Distribution & Situations")
            st.subheader("By Personnel")
            matrix = p_data.groupby('PERSONNEL')[cols['type']].value_counts().unstack().fillna(0)
            for p in ['Run %', 'Pass %']: 
                matrix[p] = (matrix[p.split()[0].upper()] / (matrix['RUN'] + matrix['PASS']) * 100).round(0).astype(str) + '%'
            st.table(matrix)
            
            st.subheader("Down & Distance Matrix")
            def get_sit(row):
                d, dist = row[cols['dn']], row[cols['dist']]
                s = "<4" if dist < 4 else "4-7" if dist <= 7 else "7+"
                return f"{int(d)}st & {s}" if d==1 else f"{int(d)}nd & {s}" if d==2 else f"{int(d)}rd & {s}"
            p_data['Situation'] = p_data.apply(get_sit, axis=1)
            dd = p_data.groupby('Situation')[cols['type']].value_counts().unstack().fillna(0)
            dd['Total'] = (dd['RUN'] + dd['PASS']).astype(int)
            st.table(dd)

        with tabs[2]: # PAGE 3: PRODUCTIVITY
            st.header("Productivity & Motion")
            c3, c4 = st.columns(2)
            with c3:
                st.subheader("Avg Gain & Explosives")
                er = (p_data[p_data[cols['type']] == 'RUN'][cols['gain']] >= 10).mean() * 100
                ep = (p_data[p_data[cols['type']] == 'PASS'][cols['gain']] >= 20).mean() * 100
                st.write(f"Run Explosive (10+): **{er:.0f}%**")
                st.write(f"Pass Explosive (20+): **{ep:.0f}%**")
            with c4:
                if cols['motion'] in df.columns:
                    st.subheader("Motion Effectiveness")
                    st.table(p_data.groupby(cols['motion'])[cols['gain']].mean().rename("Avg Gain"))

        with tabs[3]: # PIVOT LAB
            st.header("🧪 Custom Pivot Lab")
            row_choice = st.selectbox("Group By:", ['FAMILY', 'PERSONNEL', cols['dn'], 'Zone'
