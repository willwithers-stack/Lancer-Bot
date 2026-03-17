def create_pdf(df_intel, opponent_name):
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("helvetica", 'B', 16)
    pdf.cell(0, 10, f"Lancer-Bot Intelligence Report: {opponent_name}", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.set_font("helvetica", size=10)
    pdf.cell(0, 10, "Confidential Scouting Data - For Internal Staff Use Only", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(10)

    # Table Header
    pdf.set_font("helvetica", 'B', 12)
    pdf.set_fill_color(200, 200, 200)
    pdf.cell(40, 10, "Category", 1, 0, 'C', True)
    pdf.cell(100, 10, "Insight", 1, 0, 'C', True)
    pdf.cell(20, 10, "Freq", 1, 0, 'C', True)
    pdf.cell(30, 10, "Strength", 1, 1, 'C', True)

    # Table Rows
    pdf.set_font("helvetica", size=10)
    for _, row in df_intel.iterrows():
        # --- FIX STARTS HERE ---
        # Convert emoji stars to asterisks so the PDF doesn't crash
        clean_strength = str(row['Strength']).replace("⭐", "*")
        
        pdf.cell(40, 10, str(row['Category']), 1)
        pdf.cell(100, 10, str(row['Insight']), 1)
        pdf.cell(20, 10, str(row['Stat']), 1, 0, 'C')
        pdf.cell(30, 10, clean_strength, 1, 1, 'C')
        # --- FIX ENDS HERE ---
    
    return pdf.output()
