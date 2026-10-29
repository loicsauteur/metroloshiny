"""Utils for settings app."""

import csv
import os
from pathlib import Path
from typing import Optional

import gspread
from omero.gateway import BlitzGateway


def create_new_data_dict() -> dict:
    """Create 'empty' dictionary for the private data."""
    data = {
        "GoogleServiceEmail": None,
        "PathToServiceAccountJSON": None,
        "Sheet URL": None,
        "Upload password": None,
        "OMERO HOST": None,
        "OMERO PORT": 4064,
        "OMERO USER": None,
        "OMERO PASSWORD": None,
        "Settings password": None,
    }
    return data


def read_data_dict(path: str) -> dict:
    """Read the private data from file.

    Parameters
    ----------
    path : str
        Path to csv file to read.

    Returns
    -------
    dict
        Of data (non-empty version of create_new_data_dict)
    """
    # Sanity check
    if not os.path.exists(path):
        raise FileNotFoundError(f"File does not exist: {path}")

    keys = create_new_data_dict().keys()
    dict_out = {}
    with open(path, mode="r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            # Header
            if i == 0:
                if len(row) != 2:
                    raise ValueError("File does not have 2 columns.")
                elif row[0].strip(" ") != "Key":
                    raise ValueError("First columns is not 'Key'.")
                elif row[1].strip(" ") != "Value":
                    raise ValueError("Second columns is not 'Value'.")
            # All the other data rows
            else:
                k, v = row
                # Make sure that the key is known
                if k not in keys:
                    raise KeyError(f"Unknown key: <{k}>")
                dict_out[k] = v
    f.close()
    return dict_out


def try_connect_omero(
    host: str, port: int, usr: str, pwd: str
) -> tuple[bool, str]:
    """Check OMERO connection.

    Parameters
    ----------
    host : str
        OMERO host address
    port    : int
        OMERO port
    usr : str
        OMERO user name
    pwd : str
        OMERO user password

    Returns
    -------
    bool
        For successful connection
    str
        Message for error
    """
    msg = ""
    success = False
    try:
        conn = BlitzGateway(
            username=usr, passwd=pwd, host=host, port=port, secure=True
        )
        success = conn.connect()
        if not success:
            msg = "User name or password incorrect!"
        conn.c.closeSession()
    except Exception as ex:
        msg = str(ex)
    return success, msg


def try_connect_google(path: str, url: str) -> tuple[bool, str]:
    """Check the google service account settings.

    FYI: the email address is actually not so important,
        since it is gotten from the JSON.

    Parameters
    ----------
    path : str
        Path to the Service Account JSON file
    url : str
        Of the spread sheet document

    Returns
    -------
    bool
        For successful connection
    str
        Message for error
    """
    success = False
    # Try getting the google client
    try:
        if path == "":
            gc = gspread.service_account()
        else:
            path = str(Path(path).absolute())
            gc = gspread.service_account(path)
    except Exception as ex:
        return success, str(ex)

    # Try loading the spread sheet
    try:
        doc = gc.open_by_url(url=url)
    except Exception:
        return success, "URL incorrect or no access rights."

    # Fully public URLs can be opened
    try:
        # Check if expected sheet is available
        _sheet = doc.worksheet("laser_power_measurements")
    except Exception:
        return success, "Wrong spread sheet / not in expected format!"

    # All fine
    return True, ""


def compare_passwords(pwd_1: str, pwd_2: str) -> tuple[bool, str]:
    """Check if 2 strings are the same.

    Parameters
    ----------
    pwd_1 : str
        First string
    pwd_2 : str
        Second string

    Returns
    -------
    bool
        If they match (returns false if it is an empty string)
    str
        Message
    """
    if pwd_1 is None or pwd_2 is None:
        return False, "Passwords cannot be of None-type!"
    if pwd_1 == pwd_2 == "":
        return False, "Passwords need to be set."
    if pwd_1 == "" or pwd_2 == "":
        return False, "Password cannot be empty."
    if pwd_1 != pwd_2:
        return False, "Passwords do not match."
    else:
        return True, ""


def final_check_pwd(
    new_pwd: Optional[str],
    input_pwd_1: str,
    input_pwd_2: str,
) -> tuple[bool, str]:
    """Check if setting a password is valid.

    Info: Ignores the from file loaded password...

    Parameters
    ----------
    new_pwd : str
        Currently remembered pwd (reactive value)
    input_pwd_1 : str
        User input for the new pwd
    input_pwd_2 : str
        User input for the new pwd (repeated entry)

    Returns
    -------
    bool
        If everything is correct
    str
        Message what is wrong
    """
    if new_pwd is None:
        # Fail if reactive variable is not set.
        return False, "Password has not been set/checked!"
    if new_pwd == input_pwd_1 == input_pwd_2:
        return True, ""
    if input_pwd_1 == input_pwd_2 == "":
        # Allow keepting the same password
        return True, ""
    else:
        return False, "Password has not been set/checked!"


def final_check_google(
    final_mail: Optional[str],
    final_json: Optional[str],
    final_url: Optional[str],
) -> tuple[bool, str]:
    """Check if google settings are valid.

    Tries also to connect.
    Info: mail is actually not necessary...

    Parameters
    ----------
    final_mail : str
        Remembered mail (reactive value)
    final_json : str
        Remembered JSON file path (reactive value)
    final_url : str
        Remembred google sheet URL (reactive value)

    Returns
    -------
    bool
        If everything is correct
    str
        Message what is wrong
    """
    # Fail message: always the same (except connection error)
    msg = "Google are not set/checked!!"
    variables = (final_mail, final_json, final_url)
    if any(x is None for x in variables):
        return False, msg

    # Check if it can connect to Google
    _mail = "" if final_mail is None else final_mail
    _json = "" if final_json is None else final_json
    check, msg = try_connect_google(_json, final_url)
    if not check:
        return False, "[Error Google Connect]: " + msg

    # All is fine
    return check, ""


def final_check_omero(
    final_host: Optional[str],
    final_port: Optional[int],
    final_usr: Optional[str],
    final_pwd: Optional[str],
) -> tuple[bool, str]:
    """Check if OMERO settings are valid.

    Tries also to connect, but allow OMERO connection to be unset.

    Parameters
    ----------
    final_host : str
        Remembered OMERO host (reactive value)
    final_port : int
        Remembered OMERO port (reactive value)
    final_usr : str
        Remembered OMERO user (reactive value)
    final_pwd : str
        Remembered OMERO pwd (reactive value)

    Returns
    -------
    bool
        If everything is correct
    str
        Message what is wrong
    """
    # Allow OMERO not to be set
    optional_vars = (final_host, final_usr, final_pwd)
    if all(x == "" for x in optional_vars):
        return True, "No OMERO settings provided"

    # Have the settings been checked?
    msg = "OMERO settings are not set/checked!"
    if any(x is None for x in optional_vars):
        return False, msg

    # Try to check if OMERO connection works
    return try_connect_omero(
        final_host,
        final_port,
        final_usr,
        final_pwd,
    )


def save_private_data(data: dict, path: str):
    """Save the data to a csv file.

    data : dict
        Data dict with the same keys as return from create_new_data_dict()
    path : str
        Path to saving location
    """
    # Sanity check (all keys present?)
    keys = create_new_data_dict().keys()
    for k in keys:
        if k not in data.keys():
            raise KeyError(f"Missing <{k}> for saving data.")
    # Sanity check (no additional keys?)
    for k in data.keys():
        if k not in keys:
            raise KeyError(f"Unknown entry <{k}> for saving data.")

    # Write csv file
    with open(path, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Key", "Value"])
        writer.writerows(data.items())
    csvfile.close()
