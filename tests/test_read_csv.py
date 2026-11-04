"""Test functions for reading csv and similar files."""

from datetime import datetime
from pathlib import Path

import numpy as np
import pytest

import metroloshiny.utils.read_csv as rc


def test_read_thorlabs_csv():
    """Test reading Simone's thorlabs power measurement file."""
    # Get the example file relative from this file
    example_dir = Path(__file__).parent.parent / "example_files"
    path = (
        example_dir
        / "power_at_objective_examples"
        / "example_thorlabs_powermeter_linearity-DAPI.csv"
    )

    # Make sure that the file exists
    assert path.exists(), f"Could not find the test file: {path}"

    # Read the file
    df = rc.read_thorlabs_csv(path=str(path))
    # Simple checks
    assert len(df.columns) == 3  # cols
    assert len(df) == 5  # rows
    assert "20260506" in df.columns

    # Check wrong file-type input
    path = example_dir / "metroloshiny_data_example.xlsx"
    with pytest.raises(
        NotImplementedError,
        match="Reading Thorlabs only implemented for CSV files\\.",
    ):
        rc.read_thorlabs_csv(str(path))

    # Check wrong csv file input:
    path = example_dir / "private_data_example.csv"
    with pytest.raises(
        NotImplementedError,
        match="File does not seem to be the expected Thorlabs file\\.",
    ):
        rc.read_thorlabs_csv(str(path))

    # Check non-string paths
    with pytest.raises(IOError, match="Only string paths are supported\\."):
        rc.read_thorlabs_csv(path)


def test_read_nis_job_xlsx():
    """Test reading Tom's NIS JOB excel file."""
    # Get the example file relative from this file
    example_dir = Path(__file__).parent.parent / "example_files"
    # Path to single objective measurement      ##############################
    path = (
        example_dir
        / "power_at_objective_examples"
        / "SoRa_SCF_TLPM_PowerCalibrationOutputFile_20260715.xlsx"
    )

    # Read the file
    df = rc.read_nis_job_xlsx(path=str(path))

    # Check the number of rows
    n_power_steps = len(list(range(5, 101, 5)))
    n_lines = 6
    assert len(df) == n_power_steps * n_lines, "Expected n rows is wrong."
    # There should be 4 columns
    assert len(df.columns) == 4
    assert "Objective" in df.columns
    # Only one objective
    objectives = np.unique(np.asarray(df["Objective"]))
    assert len(list(objectives)) == 1

    # Path to multi objective test file         ##############################
    path = (
        example_dir
        / "power_at_objective_examples"
        / "SCF_TLPM_PowerCalibrationOutputFile_test_file.xlsx"
    )
    df = rc.read_nis_job_xlsx(path=str(path))

    # There should be 4 sheets (objectives)
    objectives = np.unique(np.asarray(df["Objective"]))
    assert len(list(objectives)) == 4

    # Check the number of rows (for 4 objectives)
    assert len(df) == n_power_steps * n_lines * 4

    # Columns should be usual + 2 ('date-missing' + 1 additional date)
    assert len(df.columns) == 6
    assert "date-missing" in df.columns


def test_read_simple_xlsx():
    """Test reading a simple power measurement xlsx file."""
    # Get the example file relative from this file
    example_dir = Path(__file__).parent.parent / "example_files"
    path = (
        example_dir
        / "power_at_objective_examples"
        / "example_simple_power_measurement.xlsx"
    )

    df = rc.read_simple_xlsx(path=str(path))
    assert len(df) == 8

    # Test file with wrong measurement unit
    test_dir = Path(__file__).parent.parent / "tests" / "test_files"
    path = test_dir / "simple_power_measurement_1.xlsx"
    with pytest.raises(NotImplementedError, match=r"Measurement unit *"):
        rc.read_simple_xlsx(path=str(path))

    # Test file with missing value
    path = test_dir / "simple_power_measurement_2.xlsx"
    with pytest.raises(
        NotImplementedError, match=r"Data contains missing val*"
    ):
        rc.read_simple_xlsx(path=str(path))


def test_read_thorlabs_metadata():
    """Test read_thorlabs_metadata() function."""
    dir = (
        Path(__file__).parents[1]
        / "example_files/power_long_short_term_thorlabs_examples/"
    )
    path = dir / "example_Short_Stability_355nm_d20261007.csv"

    # Check non-str input
    with pytest.raises(IOError, match=r"Only string paths are supported."):
        rc.read_thorlabs_metadata(path)
    # Check non-csv file
    with pytest.raises(
        NotImplementedError,
        match=r"Reading Thorlabs only implemented for CSV files.",
    ):
        rc.read_thorlabs_metadata(
            str(dir.parent / "metroloshiny_data_example.xlsx")
        )
    # Check non-existing file
    with pytest.raises(FileNotFoundError, match=r"File does not exist*"):
        rc.read_thorlabs_metadata(str(dir / "someFile.txt"))

    delimiter, line, wavelength, start, interval, d_format, t_format = (
        rc.read_thorlabs_metadata(str(path))
    )
    assert delimiter == ";"
    assert line == 12, f"Startline was {line} instead of 12."
    assert wavelength == 355
    assert start == datetime(2026, 10, 7, 6, 40, 48)
    assert interval == 2.0, f"Interval was {interval} instead of '2.0'"
    assert d_format == "%m/%d/%Y"
    assert t_format == "%H:%M:%S"

    # Different valid file
    path = dir / "example_Long_Stability_560nm_d20261022.csv"
    delimiter, line, wavelength, start, interval, d_format, t_format = (
        rc.read_thorlabs_metadata(str(path))
    )
    assert delimiter == ";"
    assert line == 12, f"Startline was {line} instead of 12."
    assert wavelength == 560
    assert start == datetime(2026, 10, 22, 6, 18, 34)
    assert interval == 30.0, f"Interval was {interval} instead of '2.0'"
    assert d_format == "%m/%d/%Y"
    assert t_format == "%H:%M:%S"

    # TODO add more test to check parsing errors (-> requires faked csv files)
    #       - parsing wavelength
    #       - parsing interval
    #       - missing delimiter, wavelength and/or missing data (/header -rows)
    # TODO try reading from wrong csv file (as on line 45 here in other test)


def test_get_long_term_power_measurement_thorlabs():
    """Test the get_long_term_power_measurement_thorlabs() function."""
    dir = (
        Path(__file__).parents[1]
        / "example_files/power_long_short_term_thorlabs_examples/"
    )
    path = dir / "example_Short_Stability_355nm_d20261007.csv"

    df, date, wave, inter = rc.get_long_term_power_measurement_thorlabs(
        str(path)
    )
    assert "Time (s)" in df.columns
    assert "Power (mW)" in df.columns
    assert len(df) == 299
    assert date == "20261007"
    assert wave == 355
    assert inter == 2.0

    # Different valid file
    path = dir / "example_Long_Stability_560nm_d20261022.csv"
    df, date, wave, inter = rc.get_long_term_power_measurement_thorlabs(
        str(path)
    )
    assert "Time (s)" in df.columns
    assert "Power (mW)" in df.columns
    assert len(df) == 241
    assert date == "20261022"
    assert wave == 560
    assert inter == 30


if __name__ == "__main__":
    pass
