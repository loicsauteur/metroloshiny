"""Test for the FieldData class."""

import pandas as pd
import pytest

from metroloshiny.data_objects.FieldData import FieldData
from metroloshiny.utils.common_utils import set_local_file


def _create_mock_omero_df_() -> pd.DataFrame:
    """Create a mock dataframe to feed to the FieldData object."""
    _df = {
        "Channel": [488, 561, "Alexa 647", "DAPI"],
        "20260101": [
            "omero3454869_ch-1",
            "omero3454869_ch-2",
            "omero3454869_ch-3",
            "omero3454869_ch-0",
        ],
        # Not existing OMERO image IDs
        "20260102": [
            "omero000001_ch-1",
            "omero000001_ch-0",
            "omero000001_ch-2",
            "omero000001_ch-3",
        ],
        # Same IDs as for first date
        "20260103": [
            "omero3454869_ch-1",
            "omero3454869_ch-2",
            "omero3454869_ch-3",
            "omero3454869_ch-0",
        ],
        # Date with different IDs (should not happen in real)
        "20260104": [
            "omero3454869_ch-1",
            "omero222222_ch-0",
            "omero3454869_ch-2",
            "omero222222_ch-3",
        ],
        # Date with file ids
        "20260105": [
            "file000001_ch-1",
            "file000001_ch-0",
            "file000001_ch-2",
            "file000001_ch-3",
        ],
        # Date with NAN entries
        "20260106": ["", None, "", None],
    }
    return pd.DataFrame().from_dict(_df)


def test_basics():
    """
    Do some basic tests on the FieldData object.

    Tests that depend on getting OMERO data are skipped in pytest.
    """
    # Create mock data
    df = _create_mock_omero_df_()
    # Create data object without loading from OMERO
    data = FieldData(base_df=df, retrieve_omero=False)

    # Basic tests without OMERO data
    assert len(data.base_df) == 4
    assert len(data.base_df.columns) == 6
    # Check the channel map function
    ch_map = data._map_channel_names_(date="20260101")
    assert ch_map.get("ch0") == "DAPI"
    assert ch_map.get("ch1") == "488"
    assert ch_map.get("ch2") == "561"
    assert ch_map.get("ch3") == "Alexa 647"

    # Sanity test
    for ch_name in data.channel_names:
        msg = f"{ch_name} not in {list(df['Channel'])}"
        assert df["Channel"].astype(str).eq(ch_name).any(), msg

    pytest_match = r".* data is not set yet."
    with pytest.raises(RuntimeError, match=pytest_match):
        data.get_distortion()
    with pytest.raises(RuntimeError, match=pytest_match):
        data.get_uniformity()
    with pytest.raises(RuntimeError, match=pytest_match):
        data.get_detected_rois()
    with pytest.raises(RuntimeError, match=pytest_match):
        data.get_ideal_rois()

    # Test relying on OMERO data            ##################################
    if set_local_file():
        # Skip tests on local file (i.e. when in pytest)
        return

    # Load the OMERO data to the object
    data._set_data_()

    # Check data
    distortion = data.get_distortion()
    for date in data.base_df.columns[1:]:
        # All dates should be present, since nan columns were removed
        msg = f"Missing date <{date}> in distortion data."
        assert date in distortion.keys(), msg

    good_1 = distortion.get("20260101")
    assert isinstance(good_1, pd.DataFrame)
    bad_1 = distortion.get("20260102")
    assert bad_1 is None
    good_2 = distortion.get("20260103")
    assert isinstance(good_2, pd.DataFrame)
    bad_2 = distortion.get("20260104")
    assert bad_2 is None
    to_implement = distortion.get("20260105")
    assert to_implement is None, "File reading not implemented yet"

    # Check channel names
    df = data.get_uniformity().get("20260101")
    assert "DAPI" in df.columns
    assert "488" in df.columns
    assert "561" in df.columns
    assert "Alexa 647" in df.columns

    # Check dataframe create for visualisation
    df = data.get_distortion_over_time()
    mean_488 = df.loc[df["Date"] == "20260101", "488"].iloc[0]
    std_dapi = df.loc[df["Date"] == "20260101", "DAPI-STD"].iloc[0]
    assert round(mean_488, 3) == 0.507
    assert round(std_dapi, 3) == 0.181

    df = data.get_uniformity_over_time()
    mean_561 = df.loc[df["Date"] == "20260101", "561"].iloc[0]
    std_647 = df.loc[df["Date"] == "20260101", "Alexa 647-STD"].iloc[0]
    assert round(mean_561, 1) == 1167.2
    assert round(std_647, 1) == 76.7


if __name__ == "__main__":
    # test_basics()
    pass
