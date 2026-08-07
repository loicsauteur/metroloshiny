"""Utils for reading files."""

import os
from typing import Optional, Union

import gspread
import pandas as pd

# Path of the private_data.csv file on the linux server
__linux_private_data_path__ = "/absolute/path/to/private_data.csv"

# Worksheet names
__sheet_names__ = {
    "Power": "laser_power_measurements",
    "PSF": "psf_measurements",
    "Objectives": "objective_db",
    "Uniformity/Distortion": "field_dist_uni",
    "Test": "test_sheet",
}


def get_private_data(key: str, data_path: Optional[str] = None) -> str:
    """
    Load 'private data' saved from a csv file.

    If data_path is not provided, will check:
        - "./data/private_data.csv"
        - same path relative to this file
        - if neither of these 2 paths exist, will check the
          path defined in __linux_private_data_path__ (global variable)

    :param key: str key to look for value
    :param data_path: str path to the csv file
    :return: str value for the key
    """
    # To read 'private' data (csv with key value pairs)
    # excepts the file ./data/private_data.csv, if not specified with data_path

    # Use hard-coded path if data_path not supplied
    if data_path is None:
        data_path = "./data/private_data.csv"
        if not os.path.exists(data_path):
            import platform
            from pathlib import Path

            # Check path relative to this file
            data_path = str(
                Path(Path(__file__).parents[3], "data/private_data.csv")
            )
            if os.path.exists(data_path):
                pass
                # FIXME print("found file relative to this file")

            if not os.path.exists(data_path) and platform.system() == "Linux":
                # Check if is running on the server and set
                # the path absolute path
                data_path = __linux_private_data_path__

    # Only allow csv files
    if not data_path.endswith(".csv"):
        raise IOError("Only .csv files are allowed.")
    # Ensure the file exists
    if not os.path.exists(data_path):
        raise FileExistsError(f"File does not exist: {data_path}")
    # Check that the csv file is in expected format (first row= "Key, Value")
    with open(data_path, "r", encoding="utf-8") as f:
        header = f.readline().strip().replace(" ", "")
        if header != "Key,Value":
            raise ValueError("Wrong private_data.csv file format.")

    # Load csv with Key column as index column
    df = pd.read_csv(data_path, index_col="Key")

    # Get the value row, and take the first (Value) column
    try:
        value = df.loc[key].iloc[0]
    except KeyError as err:
        raise KeyError(
            f"Could not find key <{key}> in file: {data_path}"
        ) from err
    # Return a string
    return str(value).strip()


def load_doc(
    gsheet_url: Optional[str] = None,
    path_service_account: Optional[str] = None,
    data_path: Optional[str] = None,
    dev_local_file: bool = False,
) -> Optional[gspread.Spreadsheet]:
    """
    Get the google spreadsheet document.

    Needs a service account, see here: https://docs.gspread.org/en/latest/oauth2.html#for-bots-using-service-account

    :param gsheet_url: optional, str url to the google sheet.
        Default = None -> gets the url from private data.
    :param path_service_account: optional, str path to google-service-account JSON file.
        Default = None -> gets the JSON file path from private data.
        If "", will use the 'default' location of the JSON file:
        `~/.config/gspread/service_account.json`
    :param data_path: optional, str path to the private_data.csv.
        Default = None -> uses default path.
    :param dev_local_file: bool. Default = False, if True returns None.

    :return: Spreadsheet
    """
    if dev_local_file:
        return None
    if path_service_account == "":
        gc = gspread.service_account()
    elif path_service_account is None:
        # FIXME? since relative path to JSON, exec must be in repo-base dir
        gc = gspread.service_account(
            get_private_data("PathToServiceAccountJSON", data_path=data_path)
        )
    else:
        gc = gspread.service_account(path_service_account)

    if gsheet_url is None:
        gsheet_url = get_private_data("Sheet URL", data_path=data_path)
    return gc.open_by_url(gsheet_url)


def get_sheet(
    doc: Optional[gspread.Spreadsheet], kind: str, dev_local_file: bool = False
) -> tuple[Optional[gspread.Worksheet], pd.DataFrame]:
    """
    Get a specific Worksheet from a google spreadsheet document.

    :param doc: gspread.Spreadsheet
    :param kind: str, key to get the name from __sheet_names__
    :param dev_local_file: bool, to use local excel file.
        Default False. If true, returns (None, pd.DataFrame)

    :return: gspread.Worksheet, pd.DataFrame
    """
    # Check if the kind is implemented
    if kind not in __sheet_names__.keys():
        raise NotImplementedError(f"{kind} is not implemented.")
    # Get the data from the excel sheet
    sheet = None
    if dev_local_file:
        df = pd.read_excel(
            "./example_files/metroloshiny_data_example.xlsx",
            sheet_name=__sheet_names__.get(kind),
        )
    else:
        # Load the sheet and convert it to a dataframe
        try:
            sheet = doc.worksheet(__sheet_names__.get(kind))
        except gspread.exceptions.WorksheetNotFound as err:
            raise RuntimeError(f"The Worksheet doesn't exist: {err}") from err
        # Get all records and explicitly specify columns, allowing empty dataframe
        df = pd.DataFrame(sheet.get_all_records(), columns=sheet.row_values(1))
    # Ensure numeric data
    if kind == "Power":
        df = ensure_numeric_data(df, first_column=4)
    elif kind == "PSF":
        df = ensure_numeric_data(df, first_column=6)
    elif kind in ["Objectives", "Uniformity/Distortion", "Test"]:
        # Do not ensure numeric data (just make the dataframe as is)
        df = pd.DataFrame(df)
    else:
        raise NotImplementedError(
            f"Reading sheet <{kind}> is not implemented."
        )
    return sheet, df


def load_gspread(
    gsheet_url: str,
    sheet_name: str,
    path_service_account: Optional[str] = None,
    whole_document: bool = False,
) -> Union[gspread.Worksheet, gspread.Spreadsheet]:
    """
    Load a worksheet from a google sheet document.

    Needs a service account, see here: https://docs.gspread.org/en/latest/oauth2.html#for-bots-using-service-account
    Optionally, allows getting the full document instead of just a sheet.

    :param gsheet_url: str url to the google sheet.
    :param sheet_name: str name of the google worksheet to load.
    :param path_service_account: str path to google-service-account JSON file.
                                 Can be None if the JSON is installed in the
                                 intended folder:
                                `~/.config/gspread/service_account.json`
    :param whole_document: boolean, whether to return the whole document
                           or just a sheet.

    :return: gspread.Worksheet or gspread.Spreadsheet
    """
    if path_service_account is None:
        gc = gspread.service_account()
    else:
        gc = gspread.service_account(path_service_account)
    # gc = gc.api_key(api_key) # currently not used...

    # Open the sheet with URL
    sh = gc.open_by_url(gsheet_url)

    if whole_document:
        return sh

    # print("worksheet names:", sh.worksheets())
    return sh.worksheet(sheet_name)


def get_gspread(
    sheet_name: Optional[str] = None,
    data_path: Optional[str] = None,
    dev_local_file: Optional[str] = None,
) -> Union[gspread.Spreadsheet, gspread.Worksheet, pd.DataFrame]:
    """
    Get a whole gspread document.

    Uses information provided in private_data.csv.

    :param sheet_name: str name of the google sheet.
    :param data_path: str path to csv file with key-value to access sheet.
    :param dev_local_file: str, for testing using a local excel file (path).

    :return: gspread.Spreadsheet or DataFrame for dev_local_file
    """
    if dev_local_file is not None:
        return pd.read_excel(dev_local_file)
    url = get_private_data("Sheet URL", data_path=data_path)
    path_sa = get_private_data("PathToServiceAccountJSON", data_path=data_path)
    doc = load_gspread(
        gsheet_url=url,
        sheet_name="" if sheet_name is None else sheet_name,
        path_service_account=path_sa,
        whole_document=True if sheet_name is None else False,
    )
    return doc


def get_laser_power_objective_data(
    data_path: Optional[str] = None, dev_local_file: bool = False
) -> tuple[
    Optional[Union[gspread.Worksheet, gspread.Spreadsheet]], pd.DataFrame
]:
    """
    Load google spread sheet & return it + DataFrame of it.

    :param data_path: str path to csv file with key-value to access sheet.
    :param dev_local_file: boolean to load from excel instead of
                           google (hard-coded).

    :return: gspread.worksheet (or None for dev_local_file = True).
    :return: gspread.Worksheet, pd.DataFrame
    """
    # For testing on local file
    if dev_local_file:
        return None, ensure_numeric_data(
            pd.read_excel("./data/metroloshiny_data.xlsx")
        )

    # Load google sheet with laser power at objective data
    url = get_private_data("Sheet URL", data_path=data_path)
    path_sa = get_private_data("PathToServiceAccountJSON", data_path=data_path)
    sheet = load_gspread(
        gsheet_url=url,
        sheet_name="laser_power_measurements",
        path_service_account=path_sa,
    )
    df = pd.DataFrame(sheet.get_all_records())
    # Make sure only numeric data for measurement columns
    #   (including lines & power)
    df = ensure_numeric_data(df, first_column=4)
    return sheet, df


def ensure_numeric_data(
    df: pd.DataFrame, first_column: int = 7, verbose: bool = False
) -> pd.DataFrame:
    """
    Make sure / parse dataframe values to numeric.

    My data frames my contain non-numeric entries.
    This will try to separate string from numbers, and make empty cells NaNs.
    It will not work for values e.g. `(SW=333) 4.05`,
    where it will yield 333.0.

    :param df: pd.DataFrame
    :param first_column: int start index for parsing.
                         (Default = 7 > first date column).

    :return: pd.DataFrame
    """
    # Make all column names strings
    df.columns = [str(c) for c in df.columns]

    # Convert column values to numeric (doesn't work for e.g. `(SW=333) 4.05`)
    for col in df.columns[first_column:]:
        extracted = df[col].astype(str).str.extract(r"([-+]?\d*\.?\d+)")[0]
        converted = pd.to_numeric(extracted, errors="coerce")
        # Find failures: original not null but converted is null
        mask = df[col].notna() & converted.isna()

        if verbose and mask.any():
            print(f"\nColumn '{col}' - failed to convert:")
            print(df.loc[mask, col])

        df[col] = converted
    return df


def check_upload_password(pwd: str, data_path: Optional[str] = None) -> bool:
    """
    Check if password for data upload matches.

    :param pwd: str input password
    :param data_path: str path to private_data.csv
                      containing the key/value for "Upload password"

    :return: boolean
    """
    return pwd == get_private_data("Upload password", data_path=data_path)


if __name__ == "__main__":
    pass
