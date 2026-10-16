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
    """
    Read the private data from file.

    :param path: path to csv file to read.

    :return: dict of data (non-empty version of create_new_data_dict)
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
    """
    Check OMERO connection.

    :param host: str, OMERO host address
    :param port: int, OMERO port
    :param usr: str, OMERO user name
    :param pwd: str, OMERO user password

    :return:
        - bool, for successful connection
        - str, message for error
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
    """
    Check the google service account settings.

    FYI: the email address is actually not so important,
        since it is gotten from the JSON.

    :param path: str, path to the Service Account JSON file
    :param url: str, of the spread sheet document

    :return:
        - bool, for successful connection
        - str, message for error
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
    """
    Check if 2 strings are the same.

    :param pwd_1: str, first string
    :param pwd_2: str, second string

    :return:
        - bool, if they match (returns false if it is an empty string)
        - str, message
    """
    if pwd_1 is None or pwd_2 is None:
        return False, "Passwords cannot be of None-type!"
    if pwd_1 == "" or pwd_2 == "":
        return False, "Password cannot be empty."
    if pwd_1 != pwd_2:
        return False, "Passwords do not match."
    else:
        return True, ""


def final_check_settings_pwd(
    file_path: str,
    final_pwd: Optional[str],
    input_cur_pwd: str,
    input_new_pwd_1: str,
    input_new_pwd_2: str,
) -> tuple[bool, str]:
    """
    Check if setting the settings password is valid.

    :file_path: str, path to private_data.csv
    :final_pwd: str, currently remembered pwd (reactive value)
    :input_cur_pwd: str, user input for the current pwd
    :input_new_pwd_1: str, user input for the new pwd
    :input_new_pwd_2: str, user input for the new pwd (repeated entry)

    :return:
        - bool, if everything is correct
        - str, message what is wrong
    """
    # No private_data.csv file yet
    if not os.path.exists(file_path):
        if final_pwd is None:
            return (
                False,
                "New 'Settings password' has not been set/checked!",
            )
        elif input_new_pwd_1 == input_new_pwd_2 == final_pwd:
            return True, ""
        else:
            # Should not get here...
            return False, "New 'Settings password' has not been checked!"

    else:
        # Check if input_cur_pwd is correct
        # Allow empty new password fields
        #   --> make sure final_pwd == input_cur_pwd
        # TODO implement
        return False, "NOT IMPLEMENTED YET!"


def final_check_google(
    final_mail: Optional[str],
    input_mail: str,
    final_json: Optional[str],
    input_json: str,
    final_url: Optional[str],
    input_url: str,
) -> tuple[bool, str]:
    """
    Check if google settings are valid.

    Tries also to connect.

    :final_mail: str, remembered mail (reactive value)
    :input_mail: str, user input mail
    :final_json: str, remembered JSON file path (reactive value)
    :input_json: str, user input JSON file path
    :final_url: str, remembred google sheet URL (reactive value)
    :input_url: str, user input google sheet URL

    :return:
        - bool, if everything is correct
        - str, message what is wrong
    """
    # Allow mail to be unset
    msg = "Google Service Email is not set/checked!!"
    if final_mail is not None and final_mail != input_mail:
        return False, msg
    if final_mail is None and input_mail != "":
        return False, msg

    # Allow JSON path to be unset
    msg = "Path to Service Account JSON file is not set/checked!!"
    if final_json is not None and final_json != input_json:
        return False, msg
    if final_json is None and input_json != "":
        return False, msg

    # Check if URL is good
    if final_url != input_url:
        return False, "Google spreadsheet URL is not set/checked!!"

    # Check if it can connect to Google
    _mail = "" if final_mail is None else final_mail
    _json = "" if final_json is None else final_json
    check, msg = try_connect_google(_json, final_url)
    if not check:
        return False, "[Error Google Connect]: " + msg

    # All is fine
    return True, ""


def final_check_omero(
    final_host: Optional[str],
    input_host: str,
    final_port: Optional[int],
    input_port: int,
    final_usr: Optional[str],
    input_usr: str,
    final_pwd: Optional[str],
    input_pwd: str,
) -> tuple[bool, str]:
    """
    Check if OMERO settings are valid.

    Tries also to connect, but allow OMERO connection to be unset.

    :final_host: str, remembered OMERO host (reactive value)
    :input_host: str, user input OMERO host
    :final_port: int, remembered OMERO port (reactive value)
    :input_port: int, user input OMERO port
    :final_usr: str, remembered OMERO user (reactive value)
    :input_usr: str, user input OMERO user
    :final_pwd: str, remembered OMERO pwd (reactive value)
    :input_pwd: str, user input OMERO pwd

    :return:
        - bool, if everything is correct
        - str, message what is wrong
    """
    # Allow OMERO not to be set
    optional_vars = (final_host, final_usr, final_pwd)
    if all(x is None for x in optional_vars) or all(
        x == "" for x in optional_vars
    ):
        return True, "No OMERO settings provided"

    # Check the host
    msg = "OMERO HOST is not set/checked!"
    if final_host is None and input_host != "":
        return False, msg
    if final_host != input_host:
        return False, msg

    # Check the Port (can never be None/empty string)
    msg = "OMERO port is not set/checked!"
    if final_port is None:
        # This should always be set (defaults to 4064)
        return False, msg
    if final_port != input_port:
        return False, msg

    # Check user
    msg = "OMERO User is not set/checked!"
    if final_usr is None and input_usr != "":
        return False, msg
    if final_usr != input_usr:
        return False, msg

    # Check pwd
    msg = "OMERO Password is not set/checked!"
    if final_pwd is None and input_pwd != "":
        return False, msg
    if final_pwd != input_pwd:
        return False, msg

    # Try to check if OMERO connection works
    return try_connect_omero(
        final_host,
        final_port,
        final_usr,
        final_pwd,
    )


def final_check_upload_pwd(
    pwd_from_file: Optional[str],
    final_pwd: Optional[str],
    input_pwd_1: str,
    input_pwd_2: str,
) -> tuple[bool, str]:
    """
    Check if setting the settings password is valid.

    :pwd_from_file: str
        password that was loaded from the file
    :final_pwd: str
        currently remembered pwd (reactive value)
    :input_new_pwd_1: str
        user input for the new pwd
    :input_new_pwd_2: str
        user input for the new pwd (repeated entry)

    :return:
    bool
        if everything is correct
    str
        message what is wrong
    """
    # Require the password to be set
    if final_pwd is None:
        return False, "Please set/check an upload password!"
    elif (
        input_pwd_1 == "" or input_pwd_2 == ""
    ) and pwd_from_file is not None:
        # Allow to not set a new password
        return True, "No upload password change."
    elif input_pwd_1 != input_pwd_2:
        return False, "The two upload passwords are not the same."
    else:
        return True, "New upload password set!"


def save_private_data(data: dict, path: str):
    """
    Save the data to a csv file.

    :param data: dict
        Data dict with the same keys as return from create_new_data_dict()
    :param path: str
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
