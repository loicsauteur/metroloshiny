"""Tests for plot_utils."""

import metroloshiny.utils.plot_utils as pu


def test_normalize_percentile():
    """Test the normalize_percentile function."""
    a = [200, 300, 600]
    b = pu.normalize_percentile(a)
    assert b[0] == 0.0
    assert b[2] == 1.0
    assert b[1] == 0.25


if __name__ == "__main__":
    pass
