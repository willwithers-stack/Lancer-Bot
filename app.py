import streamlit as st
import pandas as pd
from fpdf import FPDF
import io

# --- 1. THE LOGIC ---
def get_trend_strength(count, total):
    if total < 3: return "⭐"
    pct = (count / total) * 100
    if pct >= 85 and total >= 6: return "⭐⭐⭐⭐⭐"
    if pct >= 70 and total >= 4: return "⭐⭐⭐⭐"
    return "⭐⭐⭐" if pct >= 60 else "⭐⭐"

def create_pdf(df_intel, opponent_name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", 'B', 16)
    pdf.cell(0, 10, f"Lancer-Bot Intelligence: {opponent_name}", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.set_font("helvetica", size=10)
    pdf.cell(0, 10, "Confidential Scouting Data", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(10)

    pdf.set_font("helvetica", 'B', 11)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(40, 10, "Category", 1, 0, 'C', True)
    pdf.cell(90, 10, "Insight", 1, 0, 'C', True)
    pdf.cell(20, 10, "Freq", 1, 0, 'C', True)
    pdf.cell(30, 10, "Strength", 1, 1, 'C', True)

    pdf.set_font("helvetica", size=10)
    for _, row in df_intel.iterrows():
        clean_strength = str(row['Strength']).replace("⭐", "*")
        pdf.cell(40, 10, str(row['Category']), 1)
        pdf.cell(90, 10, str(row['Insight']), 1)
        pdf.cell(20, 10, str(row['Stat']), 1, 0, 'C')
        pdf.cell(30, 10, clean_strength, 1, 1, 'C')
    
    return pdf.output()

# --- 2. THE UI ---
st.set_page_config(page_title="Lancer-Bot Online", page_icon="🏈")
st.title("🏈 Lancer-Bot Intelligence")

opponent = st.text_input("Opponent Name", "Carlsbad Rival")
uploaded_file = st.file_uploader("Drop Hudl CSV here", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    # --- MAPPING YOUR SPECIFIC COLUMNS ---
    # We use .get() to find your exact Hudl headers
    gain_col = 'GN/LS'
    type_col = 'PLAY TYPE'
    down_col = 'DN'
    dist_col = 'DIST'
    odk_col  = 'ODK'

    # Verify columns exist
    if gain_col not in df.columns or type_col not in df.columns:
        st.error(f"Could not find '{gain_col}' or '{type_col}'. Please check your Hudl Export.")
        st.stop()

    # Create sequence memory
    df['Prev_Play_Type'] = df[type_col].shift(1)
    df['Prev_Gain'] = pd.to_numeric(df[gain_col], errors='coerce').shift(1)
    
    intel_data = []

    # 1. Opening Drive Logic (First 10 plays of ODK='O')
    offense_only = df[df[odk_col].str.contains('O', na=False, case=False)].head(10)
    if not offense_only.empty:
        run_count = offense_only[type_col].str.contains('RUN', na=False, case=False).sum()
        total = len(offense_only)
        intel_data.append({
            "Category": "Opening Script",
            "Insight": f"First 10 Plays Run Freq ({run_count}/{total})",
            "Stat": f"{(run_count/total)*100:.0f}%",
            "Strength": get_trend_strength(run_count, total)
        })

    # 2. Post-Sack Logic (PASS with loss of 4+)
    ps = df[(df['Prev_Play_Type'].str.contains('PASS', na=False, case=False)) & (df['Prev_Gain'] <= -4)]
    if not ps.empty:
        safe_plays = df.loc[ps.index, type_col].str.contains('RUN', na=False, case=False).sum()
        total = len(ps)
        intel_data.append({
            "Category": "Sequence",
            "Insight": "Post-Sack Safe Response",
            "Stat": f"{(safe_plays/total)*100:.0f}%",
            "Strength": get_trend_strength(safe_plays, total)
        })

    # 3. Stalled Run (1st Down Run for 0 or less)
    stalled = df[(df[down_col] == 1) & (df['Prev_Play_Type'].str.contains('RUN', na=False, case=False)) & (df['Prev_Gain'] <= 0)]
    if not stalled.empty:
        pass_plays = df.loc[stalled.index, type_col].str.contains('PASS', na=False, case=False).sum()
        total = len(stalled)
        intel_data.append({
            "Category": "Sequence",
            "Insight": "2nd Down Pass after 0yd Run",
            "Stat": f"{(pass_plays/total)*100:.0f}%",
            "Strength": get_trend_strength(pass_plays, total)
        })

    if intel_data:
        intel_df = pd.DataFrame(intel_data)
        st.subheader("Results")
        st.table(intel_df)
        
        pdf_out = create_pdf(intel_df, opponent)
        st.download_button("📥 Download PDF Report", data=pdf_out, file_name=f"{opponent}_Scout.pdf")
    else:
        st.info("No clear tendencies found in this specific data yet.")
