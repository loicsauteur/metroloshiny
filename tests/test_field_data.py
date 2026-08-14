"""Test for the FieldData class."""

import pandas as pd
import pytest

from metroloshiny.data_objects.field_data import FieldData
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


def test_fielddata_pytest():
    """
    Test basic functionality of the FieldData object.

    Does not rely on OMERO and runs in pytest.
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


@pytest.mark.manual
def test_fielddata():
    """
    Test the FieldData object with OMERO connection.

    Does only run in "pytest -m manual"
    Repeats test also from test_fielddata_pytest function.
    """
    # Create mock data
    df = _create_mock_omero_df_()
    # Create data object WITH loading from OMERO
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

    # Load the OMERO data to the object         ##############################
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
    mean_488 = df.loc[df["Date"] == "20260101", "488-AVG"].iloc[0]
    std_dapi = df.loc[df["Date"] == "20260101", "DAPI-STD"].iloc[0]
    assert round(mean_488, 3) == 0.507
    assert round(std_dapi, 3) == 0.181

    # Melted dataframe
    df_melt = data.get_distortion_over_time_melt()
    # len(melt) should be number of dates * n-channels (channel columns / 2)
    assert len(df_melt) == len(df) * (len(df.columns) - 1) / 2

    df = data.get_uniformity_over_time()
    mean_561 = df.loc[df["Date"] == "20260101", "561-AVG"].iloc[0]
    std_647 = df.loc[df["Date"] == "20260101", "Alexa 647-STD"].iloc[0]
    assert round(mean_561, 1) == 1167.2
    assert round(std_647, 1) == 76.7

    # Melted dataframe
    df_melt = data.get_uniformity_over_time_melt()
    assert len(df_melt) == len(df) * (len(df.columns) - 1) / 2

    # Test grid size of field of rings
    with pytest.raises(
        ValueError, match=r"There is no ROI information for date*"
    ):
        data.get_field_of_rings_grid_size(date="19991212")
    x, y = data.get_field_of_rings_grid_size(date="20260101")
    assert x == 13
    assert y == 13
    # There should be XY tiles - the center tile of detected ROIs
    assert x * y - 1 == len(data.get_detected_rois().get("20260101"))


def test_heat_mapping():
    """Test function related to heat map creation."""
    _df = _create_mock_omero_df_()

    fake_range = [x * x // 5 for x in range(1, 26)]
    # Array:
    # 0    0    1    3    5
    # 7    9    12   16   20
    # 24   28   33   39   45
    # 51   57   64   72   80
    # 88   96   105  115  125
    # Remove the middle element
    fake_range.remove(33)
    # 4-connected average of the middle would be 35.75

    df_fake_uniformity = pd.DataFrame().from_dict(
        {"Ring_ID": [x + 1 for x in range(len(fake_range))], "GFP": fake_range}
    )
    # print(df_fake_uniformity)
    fake_uniformity_table = {"20260101": df_fake_uniformity}
    data = FieldData(_df, retrieve_omero=False)

    # Test with fake data dict
    # Wrong date (not present)
    with pytest.raises(
        ValueError, match=r"There is no data associated with the date*"
    ):
        data.get_heat_map_dataframe(
            date="19991212", data_dict=fake_uniformity_table
        )
    # Roi data has no match for date
    with pytest.raises(
        RuntimeError, match=r"There is no ROI information for date*"
    ):
        data.get_heat_map_dataframe(
            date="20260101", data_dict=fake_uniformity_table
        )
    # Data not yet retrieved from OMERO yet
    with pytest.raises(
        RuntimeError, match="The OMERO data seems not to be loaded yet\\."
    ):
        data.get_heat_map_dataframe(
            date="20260101", data_dict=data.uniformity_tables
        )

    df = data.get_heat_map_dataframe(
        date="20260101", data_dict=fake_uniformity_table, test=True
    )
    assert len(df.columns) == 4
    # Assert row 13 (remember 0-based index) col GFP expected average value
    assert df.iloc[len(df) // 2, 1] == 35.75

    # TODO move this section to pytest.mark.manual decorated function
    # Test relying on OMERO data            ##################################
    if set_local_file():
        # Skip tests on local file (i.e. when in pytest)
        return

    # Test get_distortion_dataframe (for arrows and magnitude)
    # Load data for real tests
    # TODO not finished yet
    data._set_data_()
    data.get_distortion_dataframe("20260101")


if __name__ == "__main__":
    # test_basics()
    # test_heat_mapping()
    pass
