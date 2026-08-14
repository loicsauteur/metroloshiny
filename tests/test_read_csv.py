"""Test functions for reading csv and similar files."""

from pathlib import Path

import numpy as np
import pytest

import metroloshiny.utils.read_csv as rc


def test_read_thorlabs_csv():
    """Test reading Simone's thorlabs power measurement file."""
    # Get the example file relative from this file
    example_dir = Path(__file__).parent.parent / "example_files"
    path = example_dir / "example_thorlabs_powermeter_linearity-DAPI.csv"

    # Make sure that the file exists
    assert path.exists(), f"Could not find the test file: {path}"

    # Read the file
    df = rc.read_thorlabs_csv(path=str(path))
    # Simple checks
    assert len(df.columns) == 3  # cols
    assert len(df) == 5  # rows

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
        example_dir / "SoRa_SCF_TLPM_PowerCalibrationOutputFile_20260715.xlsx"
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
    path = example_dir / "SCF_TLPM_PowerCalibrationOutputFile_test_file.xlsx"
    df = rc.read_nis_job_xlsx(path=str(path))

    # There should be 4 sheets (objectives)
    objectives = np.unique(np.asarray(df["Objective"]))
    assert len(list(objectives)) == 4

    # Check the number of rows (for 4 objectives)
    assert len(df) == n_power_steps * n_lines * 4

    # Columns should be usual + 2 ('date-missing' + 1 additional date)
    assert len(df.columns) == 6
    assert "date-missing" in df.columns


if __name__ == "__main__":
    pass
