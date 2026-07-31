"""Read_file tests."""

import pytest

import metroloshiny.utils.read_file as refi


def test_get_private_data():
    """Test get_private_data function."""
    val = refi.get_private_data(
        key="OMERO PORT", data_path="./example_files/private_data_example.csv"
    )
    assert val == "4064"

    # Non-existing key
    with pytest.raises(
        KeyError, match=r"Could not find key <MagicKey> in fi*"
    ):
        refi.get_private_data(
            key="MagicKey",
            data_path="./example_files/private_data_example.csv",
        )

    # Test non-existing data_path
    with pytest.raises(FileExistsError, match=r"File does not exist: *"):
        refi.get_private_data(
            key="OMERO PORT", data_path="example_files/example.csv"
        )

    # Test non-csv file
    with pytest.raises(IOError, match=r"Only .csv files are *"):
        refi.get_private_data(
            key="OMERO PORT", data_path="example_files/example.txt"
        )

    # Test wrong csv file
    with pytest.raises(ValueError, match=r"Wrong private_data.csv file*"):
        refi.get_private_data(
            key="OMERO PORT",
            data_path="./example_files/example_thorlabs_powermeter_linearity-DAPI.csv",
        )


def test_check_upload_password():
    """Test check_upload_password function."""
    assert refi.check_upload_password(
        "password", data_path="./example_files/private_data_example.csv"
    )


if __name__ == "__main__":
    pass
