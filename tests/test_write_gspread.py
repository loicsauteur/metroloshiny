"""Write_gspread tests."""

import pytest

import metroloshiny.utils.write_gspread as wg
from metroloshiny.utils.common_utils import (
    set_local_file,
)
from metroloshiny.utils.read_file import get_sheet, load_doc


def test_make_entries():
    """
    Test the make_entries function.

    Will never run in pytest.
    """
    local_file = set_local_file()
    if local_file:
        # Prevent running on local file
        return

    doc = load_doc(dev_local_file=local_file)
    sheet, _dataframe = get_sheet(doc, "Test", dev_local_file=local_file)
    # data1 = {
    #     "C1": {"FWHM-X": 911.0, "FWHM-Y": 852.0, "FWHM-Z": 1260.0},
    #     "C2": {"FWHM-X": 800.0, "FWHM-Y": 810.0, "FWHM-Z": 1000.0},
    # }
    data2 = {
        488: {90: 1.1, 10: 2.2, 5: 3.3},
        # 555: {50: 10.1, 10: 20.2, 5: 30.3},
    }
    h2 = ["LED Line [nm]", "Power [%]"]
    # h1 = ["Channel", "FWHM"]
    date = "20260713"
    data = wg.prepare_data_for_entry(
        data=data2,
        data_headers=h2,
        site="Hebelstrasse",
        microscope="Ti2 Righty",
        objective="10x/0,45",
        info="Multibandpass",
        date=date,
    )
    wg.make_entries(sheet=sheet, data=data)


def test_prepare_data_for_entry():
    """Test prepare_data_for_entry function."""
    data = {
        "C1": {"FWHM-X": 911.0, "FWHM-Y": 852.0, "FWHM-Z": 1260.0},
        "C2": {"FWHM-X": 800.0, "FWHM-Y": 810.0, "FWHM-Z": 1000.0},
    }
    h1 = ["Channel", "FWHM"]
    date = "20260713"
    # Create dataframe from dict
    df1 = wg.prepare_data_for_entry(
        data=data,
        data_headers=h1,
        site="MySite",
        microscope="Microscope1",
        objective="10x/0.5",
        info="no info",
        date=date,
    )
    assert len(df1) == 6

    # Create a dataframe from a dataframe
    data_df = df1[df1.columns[4:]]
    df2 = wg.prepare_data_for_entry(
        data=data_df,
        data_headers=["Channel", "FWHM"],
        site="MySite",
        microscope="Microscope1",
        objective="10x/0.5",
        info="no info",
        date=date,
    )
    assert len(df2) == 6

    # Check that errors are raised if input dataframe is bad    ##############
    # If value header is not the date but "Value" -> no error
    data_df_2 = data_df.copy()
    data_df_2.columns = ["Channel", "FWHM", "Value"]
    # pd.DataFrame(data_df, columns=["Channel", "FWHM", "Value"])
    df3 = wg.prepare_data_for_entry(
        data=data_df_2,
        data_headers=["Channel", "FWHM"],
        site="MySite",
        microscope="Microscope1",
        objective="10x/0.5",
        info="no info",
        date=date,
    )
    assert len(df3) == 6
    assert df3.columns[-1] == date
    assert df1.equals(df3)

    # Value column with wrong header
    data_df_3 = data_df.copy()
    data_df_3.columns = ["Channel", "FWHM", "19991212"]
    with pytest.raises(
        RuntimeError,
        match=r"Provided data value column header is not recognised: *",
    ):
        wg.prepare_data_for_entry(
            data=data_df_3,
            data_headers=["Channel", "FWHM"],
            site="MySite",
            microscope="Microscope1",
            objective="10x/0.5",
            info="no info",
            date=date,
        )

    # Wrong number of columns
    data_df_4 = data_df.copy()
    data_df_4.insert(1, "newCol", [1, 2, 3, 4, 5, 6])
    with pytest.raises(RuntimeError, match=r"Expected a dataframe with *"):
        wg.prepare_data_for_entry(
            data=data_df_4,
            data_headers=["Channel", "FWHM"],
            site="MySite",
            microscope="Microscope1",
            objective="10x/0.5",
            info="no info",
            date=date,
        )

    # Columns do not match the expected columns
    data_df_5 = data_df.copy()
    data_df_5.columns = ["Line", "FWHM", "Value"]
    with pytest.raises(
        RuntimeError, match=r"The current data is missing a needed header: *"
    ):
        wg.prepare_data_for_entry(
            data=data_df_5,
            data_headers=["Channel", "FWHM"],
            site="MySite",
            microscope="Microscope1",
            objective="10x/0.5",
            info="no info",
            date=date,
        )


if __name__ == "__main__":
    test_make_entries()
