"""Test for common utils.py."""

from shiny.express import ui

import metroloshiny.utils.common_utils as cu


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
    """Test invert_nested_dict function."""
    d = {"C1": {"FWHM-X": 911.0, "FWHM-Y": 852.0, "FWHM-Z": 1260.0}}
    res = cu.invert_nested_dict(d)
    assert len(res) == 3, "Wrong number of keys."
    for vals in res.values():
        assert len(vals) == 2, "Wrong number of path elements,"
    for value, path in res.items():
        val = dict(d)
        for p in path:
            val = val.get(p)
        msg = f"Value {val} does not match expected value {value}."
        assert val == value, msg


def test_check_if_sequence():
    """Test check_if_sequence function."""
    good = ["A1", "A2", "A3", "A4"]
    semi_good = ["A1", "A2", "B3", "Z4"]
    bad = ["A1", "A3", "B4", "B5"]
    assert cu.check_if_sequence(good)
    assert cu.check_if_sequence(semi_good)
    assert not cu.check_if_sequence(bad)


if __name__ == "__main__":
    test_check_if_sequence()
    # test_get_ui_id()
    # test_is_input_select_in_list()
    # print("success")
