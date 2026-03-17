def decode_personnel(backfield, formation):
    bf = str(backfield).upper().strip()
    form = str(formation).upper().strip()

    # --- RB Count ---
    if any(x in bf for x in ["2RB", "PRO", "SPLIT", "FULL", "I-FORM"]):
        rb = "2"
    elif any(x in bf for x in ["1RB", "GUN", "PISTOL", "SINGLEBACK"]):
        rb = "1"
    elif any(x in bf for x in ["0RB", "EMPTY", "TRIPS EMPTY"]):
        rb = "0"
    else:
        rb = "?"  # Flag unknown instead of silently defaulting

    # --- TE Count ---
    if any(x in form for x in ["2TE", "HEAVY", "JUMBO", "HB"]):
        te = "2"
    elif any(x in form for x in ["1TE", "WING", "Y-TRIPS", "ACE"]):
        te = "1"
    elif any(x in form for x in ["0TE", "SPREAD", "DUBS", "EMPTY", "4WR", "5WR"]):
        te = "0"
    else:
        te = "?"  # Flag unknown

    label = f"{rb}{te} Personnel"
    
    # Tag unknowns for review
    if "?" in label:
        label += " (REVIEW)"
    
    return label
