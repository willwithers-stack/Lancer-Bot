"""FormationIQ configuration. Edit thresholds and mappings here, not in the logic files."""

ALERT_THRESHOLD_HIGH = 0.70
ALERT_THRESHOLD_WATCH = 0.65
MIN_ALERT_PLAYS = 6
MIN_FIRST_DRIVE_GAMES = 3
MIN_REGRESSION_ROWS = 50
MIN_REGRESSION_GAMES = 3          # needed for leave-one-game-out validation
EXPLOSIVE_GAIN_YARDS = 15         # explosive = gain of this many yards or more (15+)
MIN_LIFT_OVER_BASELINE = 0.10     # a tell must beat the team's overall rate by 10 pts

# Confidence tiers (plays, rate) — evaluated top to bottom
CONFIDENCE_TIERS = [
    ("High Confidence", 15, 0.70),
    ("Usable Tendency", 10, 0.65),
    ("Low Volume / Confirm on Film", 6, 0.0),
]

# Pre-snap only. Never add Gain, Result, Success, Explosive, or Play_Direction.
PRE_SNAP_MODEL_FEATURES = [
    "Formation_Family",
    "QB_Alignment",
    "Personnel",
    "Near_Far",
    "Motion_Flag",
    "Shift_Flag",
    "Down_Bucket",
    "Distance_Bucket",
    "Field_Zone",
    "Hash",
    "Boundary_Field",
    "Score_State",
]
POST_SNAP_COLUMNS = {
    "Gain", "Result", "Success_Flag", "Explosive_Flag", "Play_Direction",
    "Concept_Family", "Run_Family", "Pass_Family",
    "Pass_Type", "Pass_Type_Raw", "Pass_Type_Source", "Launch_Side", "Protection",
}

# Hudl header -> FormationIQ column. Keys are compared after upper-casing and
# stripping spaces/punctuation, so "YARD LN", "Yard Ln", "YARD_LN" all match.
HUDL_COLUMN_ALIASES = {
    "PLAY": "Play_Number", "PLAYNUMBER": "Play_Number", "PLAYNO": "Play_Number",
    "ODK": "ODK",
    "QTR": "Quarter", "QUARTER": "Quarter",
    "SERIES": "Series", "DRIVE": "Series",
    "DN": "Down", "DOWN": "Down",
    "DIST": "Distance", "DISTANCE": "Distance",
    "YARDLN": "Yard_Line", "YARDLINE": "Yard_Line", "YDLN": "Yard_Line",
    "HASH": "Hash",
    "OFFFORM": "Formation_Raw", "FORMATION": "Formation_Raw", "OFFFORMATION": "Formation_Raw",
    "PERSONNEL": "Personnel", "OFFPERSONNEL": "Personnel", "PERS": "Personnel",
    "BACKFIELD": "Backfield", "OFFBACKFIELD": "Backfield",
    "MOTION": "Motion", "OFFMOTION": "Motion", "MOTIONDIR": "Motion", "MOTIONDIRECTION": "Motion",
    "SHIFT": "Shift", "OFFSHIFT": "Shift",
    "OFFSTR": "Strength", "STRENGTH": "Strength", "OFFSTRENGTH": "Strength",
    "PLAYTYPE": "Play_Type",
    "OFFPLAY": "Off_Play", "PLAYNAME": "Off_Play",
    "PLAYDIR": "Play_Direction", "DIRECTION": "Play_Direction",
    "GNLS": "Gain", "GAIN": "Gain", "GAINLOSS": "Gain", "YARDS": "Gain",
    "RESULT": "Result",
    "SCOREDIFF": "Score_Differential", "SCOREDIFFERENTIAL": "Score_Differential",
    "OURSCORE": "Team_Score", "OPPSCORE": "Opp_Score", "THEIRSCORE": "Opp_Score",
    "GAME": "Game_ID", "GAMEID": "Game_ID", "OPPONENT": "Game_ID",
    "CONCEPT": "Concept_Family",
    # Pass type (Quick / Dropback / Play Action-Movement / Screen). Add a PASS TYPE column in Hudl.
    "PASSTYPE": "Pass_Type_Raw", "PASSFAMILY": "Pass_Type_Raw", "DROP": "Pass_Type_Raw",
    "DROPTYPE": "Pass_Type_Raw", "QBDROP": "Pass_Type_Raw", "PASSSTYLE": "Pass_Type_Raw",
    "LAUNCH": "Launch_Side", "LAUNCHPOINT": "Launch_Side", "LAUNCHSIDE": "Launch_Side",
    "PROTECTION": "Protection", "PROT": "Protection", "PASSPRO": "Protection",
}
REQUIRED_COLUMNS = ["Down", "Distance", "Yard_Line", "Formation_Raw"]

# Formation families. Matched as whole words against the raw tag, in this order,
# so put the most specific patterns first (EMPTY TRIPS before TRIPS, TREY before TRIPS).
# Override per opponent in the app if their tagging differs.
FORMATION_FAMILY_RULES = [
    ("EMPTY", ["EMPTY", "5 WIDE", "EMPTY TRIPS", "QUADS"]),
    ("TREY", ["TREY"]),
    ("BUNCH", ["BUNCH", "STACK BUNCH"]),
    ("TRIPS", ["TRIPS", "TRIO", "TRIP", "3X1"]),
    ("FRITO", ["FRITO"]),
    ("DOUBLES", ["DOUBLES", "DUBS", "DBLS", "2X2", "SPREAD"]),
    ("WIDE", ["WIDE"]),
    ("CONDENSED", ["CONDENSED", "NASTY", "TIGHT", "TITE"]),
    ("I_FORM", ["I", "I FORM", "IFORM", "PRO", "TWINS I", "POWER I"]),
    ("WISHBONE", ["WISHBONE", "BONE", "FLEXBONE", "WING T", "WINGT"]),
    ("ACE", ["ACE", "SINGLEBACK", "DEUCE"]),
    ("HEAVY", ["HEAVY", "JUMBO", "GOAL LINE", "GOALLINE"]),
]
QB_ALIGNMENT_RULES = [
    ("Pistol", ["PISTOL"]),
    ("Gun", ["GUN", "SHOTGUN", "SG", "EMPTY"]),
    ("Under Center", ["UC", "UNDER", "UNDER CENTER", "I", "I FORM", "PRO", "WING T", "WINGT"]),
]

# Opponent-specific formation profiles. Each opponent's tagger names things differently,
# so families are defined per opponent. Order matters: first match wins.
OPPONENT_PROFILES = {
    "Default": FORMATION_FAMILY_RULES,
    "Mission Hills": [
        # Per coach: Right/Left = Trips; Trey = Trips + attached TE opposite; Bunch kept separate.
        ("EMPTY", ["EMPTY", "EMPTY WING"]),
        ("BUNCH", ["BUNCH", "TREY BUNCH"]),
        ("TREY", ["TREY"]),
        ("FRITO", ["FRITO"]),
        ("DUBS", ["DUBS", "DOUBLES"]),
        ("WIDE", ["WIDE"]),
        ("SPREAD", ["SPREAD"]),
        ("I", ["I", "PRO"]),
        ("TRIPS", ["TRIPS", "TRIPLE", "RIGHT", "LEFT"]),
    ],
}

# Tokens kept as formation modifiers (shown alongside the family).
FORMATION_MODIFIERS = {
    "STACK": "Stack", "ONE STACK": "One Stack", "TIGHT": "Tight", "TITE": "Tight",
    "DOUBLE TIGHT": "Double Tight", "ONE TIGHT": "One Tight", "WING": "Wing", "SLOT": "Slot",
    "INTO BOUNDARY": "Into Boundary", "2 RBS": "2 RBs", "LOU": "Lou", "NUB": "Nub",
}

# Non-snap rows tagged O in Hudl (timeouts, dead-ball pre-snap penalties with no play).
NON_SNAP_RESULTS = {"TIMEOUT", "TIME OUT", "END OF QUARTER", "END OF HALF"}

# Trick-play detection: whole-word patterns matched against OFF PLAY (and RESULT).
# First match wins, so specific names go first. Edit per opponent's tagging.
TRICK_PLAY_PATTERNS = [
    ("Fake Punt", ["FAKE PUNT"]),
    ("Fake Field Goal", ["FAKE FG", "FAKE FIELD GOAL", "FAKE KICK"]),
    ("Flea Flicker", ["FLEA FLICKER", "FLEA", "FLICKER"]),
    ("Double Pass", ["DOUBLE PASS", "THROWBACK", "THROW BACK", "QB THROWBACK", "PHILLY SPECIAL", "PHILLY"]),
    ("Halfback / WR Pass", ["HB PASS", "RB PASS", "WR PASS", "HALFBACK PASS", "OPTION PASS", "JET PASS", "SWEEP PASS"]),
    ("Hook and Lateral", ["HOOK AND LATERAL", "HOOK LATERAL", "HOOK N LADDER", "HOOK AND LADDER", "HOOK LADDER"]),
    ("Fake Reverse", ["FAKE REVERSE"]),
    ("Reverse", ["REVERSE", "DOUBLE REVERSE", "END AROUND"]),
    ("Statue of Liberty", ["STATUE", "STATUE OF LIBERTY"]),
    ("Swinging Gate", ["SWINGING GATE", "GATE"]),
    ("Fumblerooski / Gadget", ["FUMBLEROOSKI", "TRICK", "GADGET", "SPECIAL", "WILDCAT PASS"]),
    ("Onside / Surprise Kick", ["ONSIDE", "SURPRISE ONSIDE", "SKY KICK"]),
]
# Kicking plays that ended as a run or pass = fake, even if the tagger never named it.
FAKE_KICK_PLAY_TYPES = {"PUNT", "FG", "FIELD GOAL", "PAT"}
FAKE_KICK_RESULTS = {"RUSH", "COMPLETE", "INCOMPLETE", "INTERCEPTION", "FIRST DOWN", "1ST DN", "TD", "TOUCHDOWN", "SACK"}

# ---------------------------------------------------------------- pass type
# Two levels: Pass_Family (what coaches see) and Pass_Type (the detail).
# Rules are (Pass_Type, Pass_Family, [whole-word patterns]). First match wins, so the
# specific ones go first (NAKED before BOOT, SCREEN before everything).
# Matched against the PASS TYPE column when it is tagged; otherwise against OFF PLAY
# (labeled "Inferred from play name" so nobody mistakes it for a hand tag).
PASS_FAMILIES = ["Quick", "Dropback", "Play Action / Movement", "Screen", "Trick Play"]
# Trick plays (double pass, reverse pass, flea flicker...) get their own bucket, found with
# TRICK_PLAY_PATTERNS (same list as the Trick Play Inventory). They are checked before every rule below.
PASS_TYPE_RULES = [
    # Fakes first: "FAKE WR SCREEN DEEP PASS" is a shot off a screen look, not a screen.
    ("PA Pocket", "Play Action / Movement", ["FAKE WR SCREEN", "FAKE SCREEN", "FAKE BUBBLE", "FAKE FLY", "FAKE JET",
                                             "FAKE SWEEP", "FAKE HALO"]),
    ("Screen", "Screen", ["SCREEN", "BUBBLE", "TUNNEL", "SLIP", "JAILBREAK", "RB SCREEN", "WR SCREEN", "SCR"]),
    ("Naked", "Play Action / Movement", ["NAKED", "NAKED BOOT"]),
    ("Boot", "Play Action / Movement", ["BOOT", "BOOTLEG", "WAGGLE", "KEEP PASS"]),
    ("Sprint / Rollout", "Play Action / Movement", ["SPRINT", "SPRINT OUT", "ROLLOUT", "ROLL OUT", "ROLL", "MOVE", "MOVEMENT", "SPRINTOUT"]),
    ("PA Pocket", "Play Action / Movement", ["PA", "PLAY ACTION", "PLAYACTION", "PLAY ACT", "P A"]),
    ("RPO", "Quick", ["RPO", "RPO PASS"]),
    # LCC staff terms (per coach): these concepts are quick game. TB SWING is quick, plain SWING is dropback.
    ("Quick", "Quick", ["SPACING", "TB RAIL", "RAIL", "TB SWING", "SEAM", "SEAM PASS", "HALO", "WR HALO", "FLY SWEEP"]),
    ("Quick", "Quick", ["QUICK", "QUICK GAME", "QK", "1 STEP", "3 STEP", "ONE STEP", "THREE STEP", "SNAP THROW", "RHYTHM"]),
    ("Dropback", "Dropback", ["MESH", "SWING",  # LCC staff terms (per coach)
                              "DROPBACK", "DROP BACK", "DROP", "DB", "5 STEP", "7 STEP", "FIVE STEP", "SEVEN STEP", "POCKET"]),
]
# Staff protection-series numbers that encode the pass type inside the play name.
# Whole-word match on OFF PLAY, checked before the word rules above. Example:
#   {"60": "Quick", "90": "Dropback", "70": "PA Pocket", "BOOT": "Boot"}
# Values must be a Pass_Type from PASS_TYPE_RULES. Leave empty if the staff doesn't use them.
PASS_PROTECTION_SERIES: dict[str, str] = {}
# Play names that are always runs, even if PLAY TYPE was tagged Pass (whole-word match on OFF PLAY).
RUN_CALL_OVERRIDES = ["TOSS CRACK"]
PASS_TYPE_IMPLICATIONS = {
    "Quick": "Ball comes out fast: squat / press, get hands up in throwing lanes, rush lanes over depth",
    "Dropback": "QB sets and reads: rush has time to get home, pressure or sim pressure pays",
    "Play Action / Movement": "Run fake or moved launch point: second-level eye discipline, set the edge vs boot",
    "Screen": "Screen alert: disciplined rush, DL peel, perimeter defenders beat blocks",
    "Trick Play": "Gadget look: eyes on your keys, plaster receivers, someone stays home on the throwback",
}
