"""Tests for YAML utils."""

from pathlib import Path

import pytest

import metroloshiny.utils.yaml_utils as yu
from metroloshiny.utils.read_csv import (
    get_long_term_power_measurement_thorlabs,
)


def test_power_dataframe_to_yaml():
    """Test the power_dataframe_to_yaml() function."""
    # Temporary output file
    save_dir = "./tests/test_files/"

    # Get some data
    dir = (
        Path(__file__).parents[1]
        / "example_files/power_long_short_term_thorlabs_examples/"
    )
    path = dir / "example_Short_Stability_355nm_d20261007.csv"

    df, date, wave, interval = get_long_term_power_measurement_thorlabs(
        str(path)
    )

    try:
        # Test writing a file
        out_file = yu.power_dataframe_to_yaml(
            path=save_dir,
            df=df,
            site="Hebelstrasse",
            microscope="Ti2",
            objective="10x0.75",
            interval=interval,
            wavelength=wave,
            date=date,
        )
        assert Path(out_file).exists()

        # Test error for overwriting an existing file
        with pytest.raises(
            IOError, match=r"The measurement file already exists."
        ):
            yu.power_dataframe_to_yaml(
                path=save_dir,
                df=df,
                site="Hebelstrasse",
                microscope="Ti2",
                objective="10x0.75",
                interval=interval,
                wavelength=wave,
                date=date,
            )
        new_out_file = yu.power_dataframe_to_yaml(
            path=save_dir,
            df=df,
            site="Hebelstrasse",
            microscope="Ti2",
            objective="10x0.75",
            interval=interval,
            wavelength=wave,
            date=date,
            overwrite=True,
        )
        assert Path(new_out_file).exists()
        assert out_file == new_out_file
    finally:
        # Delete the created (temporary) file
        if Path(out_file).exists():
            Path(out_file).unlink()


def test_create_long_term_power_file_path():
    """Test the create_long_term_power_file_path() function."""
    file = yu.create_long_term_power_file_path(
        "./data", "Basel", "Ti2", "10x0.75", 2, 355, "20261105"
    )
    expected = Path("./data").absolute()
    expected = (
        str(expected) + "/Basel__Ti2__o10x0.75__i2__w355__d20261105.yaml"
    )
    assert file == expected, f"Path was {file}, not {expected}"

    # Check for error - if path is not a directory
    with pytest.raises(IOError, match=r"Path is not a directory*"):
        yu.create_long_term_power_file_path(
            "./data/somefile.txt",
            "Basel",
            "Ti2",
            "10x0.75",
            2,
            355,
            "20261105",
        )


def test_read_long_term_power_yaml():
    """Test the read_long_term_power_yaml() function."""
    # Temporary output file
    save_dir = "./tests/test_files/"

    # Get some data
    dir = (
        Path(__file__).parents[1]
        / "example_files/power_long_short_term_thorlabs_examples/"
    )
    path = dir / "example_Short_Stability_355nm_d20261007.csv"

    df_ori, date, wave, interval = get_long_term_power_measurement_thorlabs(
        str(path)
    )

    # Test reading the same file that was just created
    try:
        # Create a file
        out_file = yu.power_dataframe_to_yaml(
            path=save_dir,
            df=df_ori,
            site="Hebelstrasse",
            microscope="Ti2",
            objective="10x0.75",
            interval=interval,
            wavelength=wave,
            date=date,
        )
        df = yu.read_long_term_power_yaml(
            save_dir,
            site="Hebelstrasse",
            microscope="Ti2",
            objective="10x0.75",
            interval=interval,
            wavelength=wave,
            date=date,
        )
        assert len(df) == len(df_ori)
        assert len(df.columns) == len(df_ori.columns)
        for col in df.columns:
            assert col in df_ori.columns

    finally:
        # Delete the written file
        if Path(out_file).exists():
            Path(out_file).unlink()

    # Test reading non-existing files
    with pytest.raises(FileNotFoundError):
        yu.read_long_term_power_yaml(
            save_dir,
            site="Hebelstrasse",
            microscope="Ti2",
            objective="10x0.75",
            interval=interval,
            wavelength=wave,
            date=date,
        )


if __name__ == "__main__":
    pass
