"""Tests for dataframe utils."""

import os

import pandas as pd
import pytest

from metroloshiny.utils.dataframe_utils import (
    filter_by_column_value,
    filter_by_nested_dict,
    parse_dates,
)


def test_filter_by_column_value():
    """Test filter_by_column_value function."""
    # Check if the file is present
    path = "./data/metroloshiny_data.xlsx"
    assert os.path.exists(path), f"Could not find: {path}"

    df = pd.read_excel(path)
    result = len(filter_by_column_value(df, "Microscope", "Ti2 Righty"))
    assert result == 25, f"Expected 25, but got {result}"


def test_parse_dates():
    """Test parse_dates function."""
    # Check if the file is present
    path = "./data/metroloshiny_data.xlsx"
    assert os.path.exists(path), f"Could not find: {path}"

    import random

    df = pd.read_excel(path)
    # Extract dates and make sure it is all strings
    dates = [str(d) for d in df.columns[7:]]
    # Shuffle the list
    random.shuffle(dates)
    new_dates = parse_dates(dates=dates)

    # Make sure that the dates are in the correct format
    for date in new_dates:
        msg = f"Date <{date}> is not a valid date YYYYMMDD"
        assert is_valid_yyyymmdd(date), msg

    # Make sure that the dates are ordered properly
    for i in range(1, len(new_dates)):
        msg = f"{new_dates[i - 1]} is not <= {new_dates[i]}"
        assert int(new_dates[i - 1]) <= int(new_dates[i]), msg

    # Sanity tests
    assert not is_valid_yyyymmdd("20262312")
    assert not is_valid_yyyymmdd("20220210-1")


def is_valid_yyyymmdd(date: str) -> bool:
    """
    Check if a string is a date in format YYYYMMDD.

    :param date: str date

    :return: boolean whether a valid date or not.
    """
    from datetime import datetime

    try:
        datetime.strptime(date, "%Y%m%d")
        return True
    except ValueError:
        return False


def test_filter_by_nested_dict():
    """Test filter_by_nested_dict function."""
    nested_dict = {
        "C1": {"FWHM-X": 911.0, "FWHM-Y": 852.0, "FWHM-Z": 1260.0},
        "C2": {"FWHM-X": 651.0, "FWHM-Y": 643.0, "FWHM-Z": 860.0},
        "C3": {"FWHM-X": 823.0, "FWHM-Y": 876.0, "FWHM-Z": 1020.0},
        "C4": {"FWHM-X": 898.0, "FWHM-Y": 954.0, "FWHM-Z": 1142.0},
    }
    df_data = {
        "Channel": [
            "C1",
            "C1",
            "C1",
            "C2",
            "C2",
            "C2",
            "C3",
            "C3",
            "C3",
            "C4",
            "C4",
            "C4",
        ],
        "FWHM": ["FWHM-X", "FWHM-Y", "FWHM-Z"] * 4,
        "Today": list(range(12)),
    }
    df = pd.DataFrame().from_dict(df_data)
    res = filter_by_nested_dict(df, nested_dict, ["Channel", "FWHM"])
    assert len(df) == len(res)

    # Check for duplicate rows       -----------------------------------------
    df_data["Channel"].append("C1")
    df_data["FWHM"].append("FWHM-Z")
    df_data["Today"].append(99)
    df = pd.DataFrame().from_dict(df_data)
    with pytest.raises(
        ValueError, match=r"Duplicate entries in the dataframe.*"
    ):
        res = filter_by_nested_dict(df, nested_dict, ["Channel", "FWHM"])

    # Check when value is missing       --------------------------------------
    df_data_miss = {}
    for k, v in df_data.items():
        val = list(v)
        val.pop()
        val.pop()
        df_data_miss[k] = val

    df = pd.DataFrame().from_dict(df_data_miss)
    res = filter_by_nested_dict(df, nested_dict, ["Channel", "FWHM"])
    # There should be one key == -1
    ks = list(res.keys())
    assert ks.index(-1) == len(ks) - 1, "Error for missing value"
    with pytest.raises(ValueError, match="-2 is not in list"):
        # There should not be a -2 index in the list
        list(res.keys()).index(-2)

    # Check also for 3 missing values   --------------------------------------
    df_data_missing = {}
    for k, v in df_data_miss.items():
        val = list(v)
        val.pop()
        val.pop(0)
        df_data_missing[k] = val
    df = pd.DataFrame().from_dict(df_data_missing)
    res = filter_by_nested_dict(df, nested_dict, ["Channel", "FWHM"])
    # Assert that indicies -1 to -3 are present, but not -4
    assert -1 in list(res.keys())
    assert -2 in list(res.keys())
    assert -3 in list(res.keys())
    assert -4 not in list(res.keys())

    # Wrong table headers       ----------------------------------------------
    with pytest.raises(KeyError):
        res = filter_by_nested_dict(df, nested_dict, ["Channel", "Wrong"])


if __name__ == "__main__":
    test_filter_by_nested_dict()
