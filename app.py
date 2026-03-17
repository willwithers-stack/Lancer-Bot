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

    # Table Header
    pdf.set_font("helvetica", 'B', 11)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(40, 10, "Category", 1, 0, 'C', True)
    pdf.cell(90, 10, "Insight", 1, 0, 'C', True)
    pdf.cell(20, 10, "Freq", 1, 0, 'C', True)
    pdf.cell(30, 10, "Strength", 1, 1, 'C', True)

    # Table Rows
    pdf.set_font("helvetica", size=10)
    for _, row in df_intel.iterrows():
        # Replace Emojis with * for PDF safety
        clean_strength = str(row['Strength']).replace("⭐", "*")
        pdf.cell(40, 10, str(row['Category']), 1)
        pdf.cell(90, 10, str(row['Insight']), 1)
        pdf.cell(20, 10, str(row['Stat']), 1, 0, 'C')
        pdf.cell(30, 10, clean_strength, 1, 1, 'C')
    
    return pdf.output()

# --- 2. THE UI ---
st.set_page_config(page_title="Lancer-Bot Online", page_icon="🏈")
st.title("🏈 Lancer-Bot Intelligence")
st.write("Upload a Hudl CSV to see non-obvious tendencies.")

opponent = st.text_input("Opponent Name", "Carlsbad Rival")
uploaded_file = st.file_uploader("Drop Hudl CSV here", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    # Simple Sequence Tracker logic for testing
    df['Prev_Play_Type'] = df['PLAY TYPE'].shift(1)
    df['Prev_Gain'] = df['GN'].shift(1)
    
    intel_data = []
    
    # Sample logic for Post-Sack (Testing)
    ps = df[(df['Prev_Play_Type'] == 'PASS') & (df['Prev_Gain'] <= -5)]
    if not ps.empty:
        safe = len(ps[ps['PLAY TYPE'] == 'RUN'])
        intel_data.append({
            "Category": "Sequence",
            "Insight": "Post-Sack Safe Response",
            "Stat": f"{(safe/len(ps))*100:.0f}%",
            "Strength": get_trend_strength(safe, len(ps))
        })

    if intel_data:
        intel_df = pd.DataFrame(intel_data)
        st.subheader("Results")
        st.table(intel_df)
        
        # PDF Button
        pdf_out = create_pdf(intel_df, opponent)
        st.download_button("📥 Download PDF Report", data=pdf_out, file_name="ScoutReport.pdf")
    else:
        st.warning("No specific sequences found in this data yet.")
