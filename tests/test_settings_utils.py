"""Tests for settings_utils."""

from pathlib import Path

import pytest

import metroloshiny.utils.setting_utils as su
from metroloshiny.utils.read_file import get_private_data


def test_create_new_data_dict():
    """Test create_new_data_dict()."""
    data = su.create_new_data_dict()
    assert len(data.keys()) == 9


@pytest.mark.manual
def test_read_data_dict():
    """Test read_data_dict()."""
    with pytest.raises(FileNotFoundError, match="File does not exist"):
        su.read_data_dict("./Path-that/doesNoT/exist/69.csv")

    # Example data csv file
    path_dir = Path(__file__).parents[1] / "example_files"
    path = path_dir / "private_data_example.csv"
    d = su.read_data_dict(str(path))
    assert len(d.keys()) == 9

    # Wrong file
    path = path_dir / "metroloshiny_data_example.xlsx"
    with pytest.raises(UnicodeDecodeError):
        su.read_data_dict(str(path))

    # Wrong csv file
    path = path_dir / "example_thorlabs_powermeter_linearity-DAPI.csv"
    with pytest.raises(ValueError, match=r"File does not have 2 columns."):
        su.read_data_dict(str(path))


@pytest.mark.manual
def test_try_connect_omero():
    """Test try_connect_omero()."""
    check, _msg = su.try_connect_omero(None, None, None, None)
    assert not check
    # Wrong address
    check, msg = su.try_connect_omero("omero.dbm.unibas.ch", None, None, None)
    assert not check
    # Good address, but wrong login details
    check, msg = su.try_connect_omero(
        "demo.openmicroscopy.org", None, None, None
    )
    assert not check
    assert msg == "User name or password incorrect!"
    check, msg = su.try_connect_omero(
        "demo.openmicroscopy.org", None, "RAndomUserTest", "tEstRandomPWd"
    )
    assert not check
    assert msg == "User name or password incorrect!"

    # Check with private data details
    host = get_private_data("OMERO HOST")
    port = get_private_data("OMERO PORT")
    usr = get_private_data("OMERO USER")
    pwd = get_private_data("OMERO PASSWORD")
    omero_details = [host, port, usr, pwd]
    # But only if all the values are not None or empty strings
    if all(x is not None for x in omero_details) and all(
        x != "" for x in omero_details
    ):
        check, msg = su.try_connect_omero(host, port, usr, pwd)
        assert check
        assert msg == ""


@pytest.mark.manual
def test_try_connect_google():
    """Test try_connect_google."""
    # Get default google json saving location
    default_json_path = Path.home() / ".config/gspread/service_account.json"

    check, msg = su.try_connect_google("", "")
    assert not check
    if default_json_path.exists():
        assert msg == "URL incorrect or no access rights."
    else:
        assert msg.startswith("[Errno 2] No such file")

    check, msg = su.try_connect_google(
        "./very-wrong/path/to/random/69.json", ""
    )
    assert not check
    assert msg.startswith("[Errno 2] No such file")

    # Test with actual existing values
    path = get_private_data("PathToServiceAccountJSON")
    url = get_private_data("Sheet URL")
    google = [path, url]
    if all(x is not None for x in google) and all(x != "" for x in google):
        check, msg = su.try_connect_google(path, "")
        assert not check
        assert msg == "URL incorrect or no access rights."
        # Wrong url
        check, msg = su.try_connect_google(
            path, "https://docs.google.com/spreadsheets/aaaaa"
        )
        assert msg == "URL incorrect or no access rights."
        # Wrong document (my own spreadsheet - "public")
        check, msg = su.try_connect_google(
            path,
            "https://docs.google.com/spreadsheets/d/14gyap4_R8GX2fz8mQ2-LVDc9h8hvv2ALQOOyCxMQh_c/edit?gid=0#gid=0",
        )
        assert msg == "Wrong spread sheet / not in expected format!"
        check, msg = su.try_connect_google(path, url)
        assert check
        assert msg == ""


def test_compare_passwords():
    """Test compare_passwords()."""
    check, _msg = su.compare_passwords(None, None)
    assert not check
    check, _msg = su.compare_passwords("", "")
    assert not check
    check, _msg = su.compare_passwords("a", "b")
    assert not check
    check, _msg = su.compare_passwords("a", "a")
    assert check


# Test I should implement...
# def test_final_check_settings_pwd():
#     """Test final_check_settings_pwd()."""
#     pass

# def test_final_check_google():
#     """Test final_check_google()."""
#     pass

# def test_final_check_omero():
#     """Test final_check_omero()."""
#     pass

# def test_final_check_upload_pwd():
#     """Test final_check_upload_pwd()."""
#     pass

# def test_save_private_data():
#     """Test save_private_data()."""
#     pass


if __name__ == "__main__":
    # test_create_new_data_dict()
    # test_read_data_dict()
    # test_try_connect_omero()
    # test_try_connect_google()
    # test_compare_passwords()

    # Tests not yet implemented
    # test_final_check_settings_pwd()
    # test_final_check_google()
    # test_final_check_omero()
    # test_final_check_upload_pwd()
    # test_save_private_data()
    pass
