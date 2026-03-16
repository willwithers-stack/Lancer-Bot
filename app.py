import streamlit as st
import pandas as pd
from fpdf import FPDF
import io

# --- LANCER-BOT LOGIC ---
def get_trend_strength(count, total):
    if total < 3: return "⭐"
    pct = (count / total) * 100
    if pct >= 85 and total >= 6: return "⭐⭐⭐⭐⭐"
    if pct >= 70 and total >= 4: return "⭐⭐⭐⭐"
    return "⭐⭐⭐" if pct >= 60 else "⭐⭐"

def create_pdf(df_intel, opponent_name):
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Lancer-Bot Intelligence Report: {opponent_name}", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 10, "Confidential Scouting Data - For Internal Staff Use Only", ln=True, align='C')
    pdf.ln(10)

    # Table Header
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(40, 10, "Category", 1, 0, 'C', True)
    pdf.cell(100, 10, "Insight", 1, 0, 'C', True)
    pdf.cell(20, 10, "Freq", 1, 0, 'C', True)
    pdf.cell(30, 10, "Strength", 1, 1, 'C', True)

    # Table Rows
    pdf.set_font("Arial", size=10)
    for _, row in df_intel.iterrows():
        pdf.cell(40, 10, str(row['Category']), 1)
        pdf.cell(100, 10, str(row['Insight']), 1)
        pdf.cell(20, 10, str(row['Stat']), 1, 0, 'C')
        # Clean stars for PDF (fpdf handles standard characters better)
        pdf.cell(30, 10, str(row['Strength']), 1, 1, 'C')
    
    return pdf.output()

# --- STREAMLIT UI ---
st.title("🏈 Lancer-Bot Online")
uploaded_file = st.file_uploader("Upload Hudl CSV", type="csv")
opponent = st.text_input("Opponent Name", "Unknown Opponent")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    # (Insert your Intelligence Logic here to create 'intel_df'...)
    # For now, using a placeholder for the logic we built:
    intel_df = pd.DataFrame([
        {"Category": "Sequence", "Insight": "Post-Sack Safe Response", "Stat": "85%", "Strength": "⭐⭐⭐⭐⭐"},
        {"Category": "Opening", "Insight": "Drive 1 Run-Heavy", "Stat": "80%", "Strength": "⭐⭐⭐⭐"}
    ])

    st.subheader("Intelligence Dashboard")
    st.table(intel_df)

    # PDF Download Button
    pdf_bytes = create_pdf(intel_df, opponent)
    st.download_button(
        label="📥 Download Scouting Report (PDF)",
        data=pdf_bytes,
        file_name=f"LancerBot_{opponent}.pdf",
        mime="application/pdf"
    )
