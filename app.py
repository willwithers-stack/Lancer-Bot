def decode_personnel(backfield, formation):
    """
    Broadened Decoder: 1st Digit = RBs | 2nd Digit = TEs
    """
    bf = str(backfield).upper().strip()
    form = str(formation).upper().strip()
    
    # --- RB Count (1st Digit) ---
    # Catching 2-back sets
    if any(x in bf for x in ["2RB", "PRO", "SPL", "FULL", "I-FORM", "TWIN"]):
        rb = "2"
    # Catching 1-back sets
    elif any(x in bf for x in ["1RB", "GUN", "PISTOL", "SING", "S-BACK", "OFFSET"]):
        rb = "1"
    # Catching 0-back sets
    elif any(x in bf for x in ["0RB", "EMPTY", "TRIPS EMPTY", "MT"]):
        rb = "0"
    else:
        rb = "1" # Default to 1RB if it's unclear but not empty

    # --- TE Count (2nd Digit) ---
    # Catching Heavy sets
    if any(x in form for x in ["2TE", "HEAVY", "JUMBO", "HB", "DBL TIGHT"]):
        te = "2"
    # Catching 1-TE sets
    elif any(x in form for x in ["1TE", "WING", "Y-TRIPS", "ACE", "TIGHT", "Y-"]):
        te = "1"
    # Catching 0-TE/Spread sets
    elif any(x in form for x in ["0TE", "SPREAD", "DUBS", "DBLS", "EMPTY", "4WR", "5WR", "TRI"]):
        te = "0"
    else:
        te = "0" # Default to 0TE if it's a spread-looking name
        
    return f"{rb}{te}"
