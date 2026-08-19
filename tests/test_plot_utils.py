"""Tests for plot_utils."""

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

import metroloshiny.utils.plot_utils as pu


def test_normalize_percentile():
    """Test the normalize_percentile function."""
    a = [200, 300, 600]
    b = pu.normalize_percentile(a)
    assert b[0] == 0.0
    assert b[2] == 1.0
    assert b[1] == 0.25


def test_normalize_df():
    """Test the normalize_df function."""
    df = {
        "ID": list(range(1, 6)),
        "x": list(range(0, -5, -1)),
        "val1": list(range(10, 60, 10)),
        "val2": list(range(0, -50, -10)),
        "val3": list(range(0, 50, 10)),
        "val4": [15, 39, -10, 90, -5],
        "val5": [10, 10, 10, 10, 10],
        "val6": [0, 0, 0, 0, 0],
    }
    df = pd.DataFrame().from_dict(df)
    out = pu.normalize_df(df, start_col=0, end_col=-1)
    assert len(out) == len(df)
    assert len(out.columns) == len(df.columns)

    out = pu.normalize_df(df, start_col=3, end_col=-1)
    assert len(out) == len(df)
    assert len(out.columns) == len(df.columns)
    assert_frame_equal(df.iloc[:, 0:3], out.iloc[:, 0:3])
    assert 1.0 in out.iloc[:, 3:].values
    assert 0.0 in out.iloc[:, 3:].values
    assert 2.0 not in out.iloc[:, 3:].values

    with pytest.raises(
        ValueError, match=r"start_col cannot be bigger than end*"
    ):
        pu.normalize_df(df, start_col=3, end_col=2)
    # Check behaviours on columns with same values
    out = pu.normalize_df(df, start_col=6, end_col=6)
    assert out.iloc[:, 6].all() == 1
    out = pu.normalize_df(df, start_col=7, end_col=7)
    assert out.iloc[:, 7].all() == 0
    assert_frame_equal(df, out)


if __name__ == "__main__":
    pass
