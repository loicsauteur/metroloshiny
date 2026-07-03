"""Test for common utils.py."""

import numpy as np
import pandas as pd
import pytest
from shiny.express import ui

import metroloshiny.utils.common_utils as cu
from metroloshiny.utils.read_file import get_sheet, load_doc


def create_input_list() -> list:
    """Create mock input list."""
    input_selector = ui.input_select(
        "input_selector", "Choose", choices=["A", "B"]
    )
    input_text = ui.input_text("input_text", "Enter text", "Example entry...")
    return [input_selector, input_text]


def test_get_ui_id():
    """Test get_ui_id function."""
    input_list = create_input_list()
    assert cu.get_ui_id(input_list[0]) == "input_selector"
    assert cu.get_ui_id(input_list[1]) == "input_text"


def test_is_input_select_in_list():
    """Test is_input_select_in_list function."""
    input_list = create_input_list()
    assert cu.is_input_select_in_list(input_list, "input_selector")
    assert cu.is_input_select_in_list(input_list, "input_text")
    assert not cu.is_input_select_in_list(input_list, "something")


def test_check_duplicate_dict_values():
    """Test check_duplicate_dict_values function."""
    a = {"DAPI": "C1", "GFP": "None", "Cy3": "C2", "Cy5": "None"}
    b = {"DAPI": "C1", "GFP": "None", "Cy3": "C1", "Cy5": "None"}
    good = cu.check_duplicate_dict_values(a)
    bad1 = cu.check_duplicate_dict_values(a, exclude=None)
    bad2 = cu.check_duplicate_dict_values(b)

    assert good is None
    assert isinstance(bad1, dict)
    assert isinstance(bad2, dict)
    assert next(iter(bad2.keys())) == "C1"


def test_invert_nested_dict():
    """
    Test invert_nested_dict function.

    Deprecated function.
    """
    # d = {"C1": {"FWHM-X": 911.0, "FWHM-Y": 852.0, "FWHM-Z": 1260.0}}
    # res = cu.invert_nested_dict(d)
    # assert len(res) == 3, "Wrong number of keys."
    # for vals in res.values():
    #     assert len(vals) == 2, "Wrong number of path elements,"
    # for value, path in res.items():
    #     val = dict(d)
    #     for p in path:
    #         val = val.get(p)
    #     msg = f"Value {val} does not match expected value {value}."
    #     assert val == value, msg

    # # Test problematcit nested dict
    # d = {
    #     "C2": {"Shift-X": -1.2, "Shift-Y": -2.2, "Shift-Z": 6.2},
    #     "C3": {"Shift-X": 0.8, "Shift-Y": -3.2, "Shift-Z": 4.0},
    #     "C4": {"Shift-X": -0.8, "Shift-Y": -4.8, "Shift-Z": 4.8},
    #     "C1": {
    #         "Shift-X": "Reference",
    #         "Shift-Y": "Reference",
    #         "Shift-Z": "Reference",
    #     },
    # }
    # with pytest.raises(KeyError, match=r"Failed to invert the nested dict*"):
    #     res = cu.invert_nested_dict(d)


def test_check_if_sequence():
    """Test check_if_sequence function."""
    good = ["A1", "A2", "A3", "A4"]
    semi_good = ["A1", "A2", "B3", "Z4"]
    bad = ["A1", "A3", "B4", "B5"]
    assert cu.check_if_sequence(good)
    assert cu.check_if_sequence(semi_good)
    assert not cu.check_if_sequence(bad)


def test_list_duplicates():
    """Test list_duplicate function."""
    good = [1, 2, 3, 4]
    good2 = [1, "a", "b", 4]
    bad = [1, 2, 2, 4, 3, 5, 3]
    bad2 = [1, 5, "a", "a", "b", 6, 5]
    assert len(cu.list_duplicates(good)) == 0
    assert len(cu.list_duplicates(good2)) == 0
    bad = cu.list_duplicates(bad)
    bad2 = cu.list_duplicates(bad2)
    assert len(bad) == 2
    assert len(bad2) == 2
    assert 2 in bad
    assert 3 in bad
    assert 5 in bad2
    assert "a" in bad2


def test_create_css_color_dict():
    """Test create_css_color_dict function."""
    wave = [350, 405, 445, 488, 515, 561, 594, 647, 669, 750, 800]
    prct = [5, 10, 25, 50, 75, 90, 100]

    # Test wrong min max input
    with pytest.raises(
        ValueError, match=r"Min <500> must be smaller than max <500>!"
    ):
        cu.create_css_color_dict(wave, min_val=500, max_val=500)
    with pytest.raises(
        ValueError, match=r"Min <500> must be smaller than max <450>!"
    ):
        cu.create_css_color_dict(wave, min_val=500, max_val=450)

    # Check normal usage
    wave_dict = cu.create_css_color_dict(wave, min_val=380, max_val=700)
    assert len(wave_dict) == len(wave)
    unique_colors = np.unique(np.asarray(list(wave_dict.values())))
    # Darkred is not unique (twice in list)
    assert len(unique_colors) == len(wave) - 1
    for k, v in wave_dict.items():
        if k <= 380:
            assert v == "indigo"
        if k >= 700:
            assert v == "darkred"

    # Test wrong usage
    prct_dict = cu.create_css_color_dict(prct)
    for col in prct_dict.values():
        assert col == "indigo"

    # Test proper usage
    prct_dict = cu.create_css_color_dict(prct, min_val=5, max_val=100)
    unique_colors = np.unique(np.asarray(list(prct_dict.values())))
    assert len(unique_colors) == len(prct_dict) == len(prct)

    # Test too many colors (returns an empty dict)
    out = cu.create_css_color_dict(list(range(50)), min_val=0, max_val=50)
    assert not out
    # Same, but min/max not specified gives valid dict output
    out = cu.create_css_color_dict(list(range(50)))
    assert out

    # Check that the input are all numbers
    wrong_list = [450, "500", "600", "text"]
    good_list = [455.5, "300", "833", 600, "561"]
    with pytest.raises(ValueError, match=r"Range values must be numbers*"):
        cu.create_css_color_dict(wrong_list)
    assert cu.create_css_color_dict(good_list)


def test_objective_db_functions():
    """Test functions to getting data from the objective sheet."""
    # Get local objective data (xlsx)
    doc = load_doc(dev_local_file=True)
    _, df = get_sheet(doc=doc, kind="Objectives", dev_local_file=True)

    # Check for error with wrong dataframe
    df_wrong = pd.DataFrame([], columns=["1", "2"])
    with pytest.raises(
        RuntimeError,
        match=r"The dataframe does not seem to be the objecive database\.",
    ):
        cu.get_objective_info(df_wrong, "ID1", "NA")

    # Check for error when column header not present
    with pytest.raises(
        KeyError, match=r".*is not a valid key for the objective database\."
    ):
        cu.get_objective_info(df, "ID1", "NameX")

    assert cu.get_objective_info(df, "ID2", "ID") == "ID2"
    assert cu.get_objective_info(df, "ID2", "Magnification") == "10x"
    assert cu.get_objective_info(df, "ID3", "Manufacturer") == "Nikon"

    # Check non-existent ID
    with pytest.raises(
        ValueError, match=r"The .*is not present in the objective database."
    ):
        cu.get_objective_info(df, "ID666.9", "NA")

    # Check "sub-functions"
    assert cu.get_objective_na(df, "ID1") == 0.2
    assert cu.get_objective_ri(df, "ID19") == 1.518
    assert cu.get_objective_mag(df, "ID4") == 40
    with pytest.raises(
        RuntimeError, match=r"The .*is not present in the objective database."
    ):
        cu.get_objective_na(df, "ID47-88")
    with pytest.raises(
        RuntimeError, match=r"The .*is not present in the objective database."
    ):
        cu.get_objective_na(df, "ID1-YZ")


if __name__ == "__main__":
    pass
