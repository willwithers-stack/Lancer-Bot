import numpy as np
import pandas as pd
import pytest

from src.cleaning import clean_hudl_export, derive_run_pass
from src.feature_engineering import (add_analysis_features, normalize_yard_line,
                                     bucket_field_zone, score_state)
from src.formation_mapping import formation_family, near_far, qb_alignment
from src.alert_engine import build_run_pass_alerts, tendency_table


def test_yard_line_hudl_convention():
    assert normalize_yard_line(-35) == 35        # own 35
    assert normalize_yard_line(25) == 75         # opp 25
    assert normalize_yard_line(50) == 50
    assert bucket_field_zone(normalize_yard_line(15)) .startswith("Red Zone")
    assert bucket_field_zone(normalize_yard_line(-5)).startswith("Backed Up")


def test_score_state_symmetric():
    assert score_state(-9) == "Trailing 9+"
    assert score_state(9) == "Leading 9+"
    assert score_state(np.nan) == "Unknown"


def test_run_pass_word_boundaries():
    assert derive_run_pass("Pass", "", "") == "Pass"
    assert derive_run_pass("", "Inside Zone", "Rush") == "Run"
    assert derive_run_pass("", "Jet Sweep", "Sack") == "Pass"
    assert derive_run_pass("", "", "Red zone note") == "Unknown"   # 'ZONE' alone is not a run


def test_formation_mapping_order():
    assert formation_family("Empty Trips Rt") == "EMPTY"
    assert formation_family("Trey Lt") == "TREY"
    assert formation_family("Bunch Rt") == "BUNCH"
    assert formation_family("Gun Trips Rt Near") == "TRIPS"
    assert near_far("Gun Trips Rt Near") == "Near"
    assert near_far("Doubles Far") == "Far"
    assert near_far("Linear") == "None"
    assert qb_alignment("Pistol Doubles") == "Pistol"


def test_missing_optional_columns_do_not_crash():
    raw = pd.DataFrame({"DN": [1, 2], "DIST": [10, 6], "YARD LN": [-30, 40], "OFF FORM": ["Trips Rt", "Doubles"],
                        "PLAY TYPE": ["Run", "Pass"]})
    clean, report, meta = clean_hudl_export({"CSV": raw})
    out = add_analysis_features(clean)
    assert out["Motion_Flag"].sum() == 0
    assert (out["Score_State"] == "Unknown").all()


def test_game_id_from_play_number_reset_and_first_drive():
    raw = pd.DataFrame({"PLAY #": [1, 2, 3, 4, 1, 2, 3], "ODK": ["K", "O", "O", "D", "O", "O", "D"],
                        "DN": [0, 1, 2, 1, 1, 2, 1], "DIST": [0, 10, 5, 10, 10, 3, 10],
                        "YARD LN": [-35, -25, -30, 30, -20, -28, 40], "OFF FORM": ["", "Trips", "Trips", "", "I", "I", ""],
                        "PLAY TYPE": ["KO", "Run", "Pass", "", "Run", "Run", ""]})
    clean, _, meta = clean_hudl_export({"CSV": raw})
    assert meta["games"] == 2
    assert clean["First_Drive_Flag"].all()


def test_alert_requires_lift_over_baseline():
    df = pd.DataFrame({"Run_Pass": ["Pass"] * 72 + ["Run"] * 28, "Game_ID": ["G1", "G2"] * 50,
                       "Formation_Family": ["TRIPS"] * 100})
    assert build_run_pass_alerts(df, ["Formation_Family"]).empty   # 72% == team baseline, no tell


def test_post_snap_grouping_blocked():
    df = pd.DataFrame({"Run_Pass": ["Run"], "Game_ID": ["G1"], "Gain": [5]})
    with pytest.raises(ValueError):
        tendency_table(df, ["Gain"])


def test_side_word_as_formation_and_mh_profile():
    from src.formation_mapping import formation_standard, formation_family
    from src.config import OPPONENT_PROFILES
    mh = OPPONENT_PROFILES["Mission Hills"]
    assert formation_standard("Right") == "RIGHT"
    assert formation_family("Right", mh) == "TRIPS"
    assert formation_family("RIGHT FRITO", mh) == "FRITO"
    assert formation_family("I Right Slot Right", mh) == "I"
    assert formation_family("TREY BUNCH", mh) == "BUNCH"
    assert formation_family("dubs ONE STACK", mh) == "DUBS"


def test_timeouts_removed_without_splitting_drive():
    raw = pd.DataFrame({"PLAY #": [1, 2, 3, 4], "ODK": ["O", "O", "O", "D"], "DN": [1, 2, 2, 1], "DIST": [10, 6, 6, 10],
                        "YARD LN": [-30, -34, -34, 30], "OFF FORM": ["DUBS", None, "WIDE", None],
                        "PLAY TYPE": ["Run", None, "Pass", None], "RESULT": ["Rush", "Timeout", "Complete", None]})
    clean, _, _ = clean_hudl_export({"G1": raw})
    assert len(clean) == 2 and clean["Drive_ID"].nunique() == 1


def test_trick_play_inventory():
    from src.trick_plays import build_trick_play_inventory, classify_trick
    assert classify_trick("FAKE REVERSE") == "Fake Reverse"
    assert classify_trick("JET REVERSE") == "Reverse"
    assert classify_trick("FAKE FLY INSIDE FOLD") is None
    assert classify_trick("POWER") is None
    rows = pd.DataFrame({"Game_ID": ["Oside", "Oside", "Quartz"], "Play_Number": [40, 12, 77], "ODK": ["O", "O", "K"],
                         "Formation_Raw": ["WIDE", "DUBS", None], "Off_Play": ["FAKE REVERSE", "POWER", None],
                         "Play_Type": ["Run", "Run", "Punt"], "Result": ["Rush", "Rush", "Rush"], "Gain": [4, 3, 12]})
    inv = build_trick_play_inventory(rows)
    assert list(inv["Trick Type"]) == ["Fake Reverse", "Fake Punt"]
    assert list(inv.columns[:5]) == ["Opponent", "Play #", "Formation", "Call", "Trick Type"]


def test_score_rebuild_and_no_clear_lean():
    from src.alert_engine import confidence_label
    assert confidence_label(28, 0.57, 2) == "No Clear Lean"
    raw = pd.DataFrame({"PLAY #": [1, 2, 3, 4, 5, 6], "ODK": ["O", "K", "D", "K", "O", "K"], "QTR": [1] * 6,
                        "DN": [1, None, 1, None, 1, None], "DIST": [10, None, 10, None, 10, None],
                        "YARD LN": [-30, None, 30, None, -25, None], "OFF FORM": ["DUBS", None, "X", None, "WIDE", None],
                        "PLAY TYPE": ["Run", "Extra Pt.", "Pass", "Extra Pt. Block", "Pass", "FG Block"],
                        "RESULT": ["Rush, TD", "Good", "Complete, TD", "Good", "Complete", "Good"]})
    clean, _, meta = clean_hudl_export({"G1": raw})
    from src.scoring import final_scores
    f = final_scores(meta["score_rows"]).iloc[0]
    assert (f["Scouted_Final"], f["Opponent_Final"]) == (7, 10)
    assert list(clean["Score_Differential"]) == [0, 0]   # 2nd snap: 7-7 before the snap


def test_family_never_other():
    from src.formation_mapping import formation_family
    for tag in ["Wildcat Rt", "Swinging Gate", "Unbalanced Lt", "Q", "Diamond"]:
        assert formation_family(tag) != "Other"
    assert formation_family("Wildcat Rt") == formation_family("Wildcat Lt") == "WILDCAT"
    assert formation_family(None) == "Not Tagged"


def test_accuracy_check_pending_under_three_games():
    from src.verification import verify_alerts, PENDING
    df = pd.DataFrame({"Run_Pass": ["Run"] * 9 + ["Pass"] * 1 + ["Pass"] * 10, "Game_ID": ["G1", "G2"] * 10,
                       "Formation_Family": ["I"] * 10 + ["DUBS"] * 10})
    a = build_run_pass_alerts(df, ["Formation_Family"])
    v = verify_alerts(a, df, ["Formation_Family"], None)
    assert set(v["Accuracy_Check"]) <= {PENDING, "Film Only"}
    assert "Held_Up" in v.columns


def test_pass_type_classification():
    from src.pass_types import classify_pass_type, add_pass_types
    assert classify_pass_type("Naked Boot Rt") == "Naked"
    assert classify_pass_type("Boot Lt Flood") == "Boot"
    assert classify_pass_type("PA Post") == "PA Pocket"
    assert classify_pass_type("Bubble Rt") == "Screen"
    assert classify_pass_type("Quick Slants") == "Quick"
    assert classify_pass_type("Power") is None
    assert classify_pass_type("Fake Punt") is None                     # FAKE is not play action
    assert classify_pass_type("FAKE WR SCREEN DEEP PASS") == "PA Pocket"
    assert classify_pass_type("MOTION FAKE FLY PASS") == "PA Pocket"
    assert classify_pass_type("FAKE HALO") == "PA Pocket" and classify_pass_type("WR HALO") == "Quick"
    assert classify_pass_type("TB SWING") == "Quick" and classify_pass_type("SWING") == "Dropback"
    assert classify_pass_type("MOTION SPACING") == "Quick" and classify_pass_type("MESH") == "Dropback"
    assert classify_pass_type("MOTION FLY SWEEP") == "Quick"
    assert derive_run_pass("Pass", "TOSS CRACK", "Rush") == "Pass"   # override happens in cleaning, not here
    assert classify_pass_type("62 Hitch", series={"60": "Quick"}) is None  # whole word only
    assert classify_pass_type("60 Hitch", series={"60": "Quick"}) == "Quick"
    df = pd.DataFrame({"Run_Pass": ["Pass", "Pass", "Pass", "Run"], "Pass_Type_Raw": ["Dropback", None, None, None],
                       "Off_Play": ["Boot Lt", "Sprint Out", "Y Cross", "Power"]})
    out = add_pass_types(df)
    assert list(out["Pass_Family"].fillna("-")) == ["Dropback", "Play Action / Movement", "Not Tagged", "-"]
    assert list(out["Pass_Type_Source"].fillna("-")) == ["Tagged", "Inferred from play name", "Not Tagged", "-"]


def test_pass_type_tag_makes_snap_a_pass():
    raw = pd.DataFrame({"DN": [1, 2], "DIST": [10, 6], "YARD LN": [-30, 40], "OFF FORM": ["Trips Rt", "Doubles"],
                        "PLAY TYPE": [None, "Run"], "PASS TYPE": ["Quick", None]})
    clean, _, _ = clean_hudl_export({"CSV": raw})
    out = add_analysis_features(clean)
    assert list(out["Run_Pass"]) == ["Pass", "Run"]
    assert out["Pass_Family"].iloc[0] == "Quick"


def test_pass_type_alerts_need_lift_and_block_post_snap():
    from src.pass_types import build_pass_type_alerts, pass_type_table
    n = 12
    df = pd.DataFrame({"Run_Pass": ["Pass"] * (2 * n), "Game_ID": ["G1", "G2", "G3"] * 8,
                       "Formation_Family": ["TRIPS"] * n + ["DUBS"] * n,
                       "Pass_Type": ["Quick"] * 11 + ["Dropback"] + ["Dropback"] * 10 + ["Quick"] * 2})
    from src.pass_types import TYPE_TO_FAMILY
    df["Pass_Family"] = df["Pass_Type"].map(TYPE_TO_FAMILY)
    a = build_pass_type_alerts(df, ["Formation_Family"])
    assert set(a["Top_Type"]) == {"Quick", "Dropback"}
    trips = a[a["Formation_Family"] == "TRIPS"].iloc[0]
    assert trips["Passes"] == 12 and abs(trips["Rate"] - 11 / 12) < 1e-9
    assert trips["Accuracy_Check"] in {"Developing", "Film Only"}       # never Verified without a model
    with pytest.raises(ValueError):
        pass_type_table(df, ["Pass_Type"])
