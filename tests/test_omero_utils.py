"""
Tests for OMERO utils.

Most tests will not run in pytest,
as they require login credentials and connection to an OMERO instance.
"""

import pytest

import metroloshiny.utils.omero_utils as ou


def test_get_cred():
    """Test get_cred function with example private_data.csv."""
    # Test on example file
    name, pwd, host, port = ou.get_cred(
        path_private_data="./example_files/private_data_example.csv"
    )
    assert name == "user"
    assert pwd == "password"
    assert host == "omero.idr.com"
    assert isinstance(port, int)
    assert port == 4064

    # Test on file that does not exisist
    with pytest.raises(FileExistsError, match=r"File does not *"):
        ou.get_cred(path_private_data="example_files/example.csv")

    # Test on wrong file
    with pytest.raises(ValueError, match=r"Wrong private_data.csv file*"):
        ou.get_cred(
            path_private_data="./example_files/example_thorlabs_powermeter_linearity-DAPI.csv"
        )


if __name__ == "__main__":
    pass
