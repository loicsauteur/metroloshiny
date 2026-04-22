"""Utils for reading files."""

import math
import os
from typing import Optional, Union

import gspread
import pandas as pd

# Path of the private_data.csv file on the linux server
__linux_private_data_path__ = (
    "/users/stud/s/sautlo01/metroloshiny/data/private_data.csv"
)


def read_xlsx(file: str):
    """
    Read an excel file.

    Deprecated!
    """
    # Read the xlsx
    df = pd.read_excel(file)
    # Ensue that it is a laser powerment meausrement
    # loc_line = None

    # Loop over rows as simple tuples
    for row in df.itertuples(name=None):
        for _i, element in enumerate(row):
            if isinstance(element, str) and "Laser" in element:
                # print("col=", i, "==", row)
                # row index can be found at the first position of the row-tuple
                # add 1 to the row,
                #   since it is excluding the current header line...
                df = read_laserpower_xlsx_hebel(df=df, header_row=row[0])
                return df

    # loc_line = xlsx_df.str.contains(r'Line', na=True)
    # print(xlsx_df[1])
    # print(loc_line)
    # print(df)


def read_laserpower_xlsx_hebel(
    df: pd.DataFrame, header_row: int
) -> pd.DataFrame:
    """
    Reorders a DataFrame.

    Deprecated!
    """
    # Used to reorder the dataframe -
    #   basically to skip the unnecessary first rows...

    # print("Before df reorganization...")
    # print(df.head(7))
    # print("--------------------")

    # copy "Line..." and "Power..." to the future header line
    # print("header row =", header_row)
    # print("replacing:", df.iloc[header_row, 0],
    #   "with", df.iloc[header_row + 1, 0])
    # print("replacing:", df.iloc[header_row, 1],
    #   "with", df.iloc[header_row + 1, 1])
    df.iloc[header_row, 0] = df.iloc[header_row + 1, 0]
    df.iloc[header_row, 1] = df.iloc[header_row + 1, 1]

    # Reset the column index
    df.columns = df.iloc[header_row]
    # drop rows above (and including header row and the row after it)
    df = df[header_row + 2 :]
    df.reset_index(drop=True, inplace=True)

    # print("--------------------")
    # Fill empty laser power entries
    cur_laser = None
    for row in df.itertuples():
        if math.isnan(row[1]):
            if cur_laser is None:
                raise RuntimeError(
                    "Could not specify laser line for row {row[0]}"
                )
            else:
                df.iloc[row[0], 0] = cur_laser

        else:
            cur_laser = row[1]

    # Drop all Nan columns
    df.dropna(axis=1, how="all", inplace=True)

    # Make sure we work with numeric values
    #   (when errors, leave as is ('ignore'))
    for col in df.columns[2:]:
        extracted = df[col].astype(str).str.extract(r"([-+]?\d*\.?\d+)")[0]
        converted = pd.to_numeric(extracted, errors="coerce")
        # Find failures: original not null but converted is null
        mask = df[col].notna() & converted.isna()

        if mask.any():
            print(f"\nColumn '{col}' - failed to convert:")
            print(df.loc[mask, col])

        df[col] = converted

    # Rename the df columns (header)
    df.columns = [str(x) for x in list(df.columns)]

    # print("--------------------")
    # print(df)
    return df


def get_private_data(key: str, data_path: Optional[str] = None) -> str:
    """
    Load 'private data' saved from a csv file.

    Todo: provide example..

    :param key: str key to look for value
    :param data_path: str path to the csv file, if not provided will look for:
                      "./data/private_data.csv"
    :return: str value for the key
    """
    # To read 'private' data (csv with key value pairs)
    # excepts the file ./data/private_data.csv, if not specified with data_path

    # Use hard-coded path if data_path not supplied
    if data_path is None:
        data_path = "./data/private_data.csv"
        if not os.path.exists(data_path):
            # Check if is running on the server and set the path absolute path
            import platform

            print(
                f"<{data_path}> does not exist. platform.system =",
                platform.system(),
            )
            if platform.system() == "Linux":
                data_path = __linux_private_data_path__
    # Ensure the file exists
    if not os.path.exists(data_path):
        raise FileExistsError(f"File does not exist: {data_path}")
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


def load_gspread(
    gsheet_url: str,
    sheet_name: str,
    path_service_account: Optional[str] = None,
    whole_document: bool = False,
) -> Union[gspread.Worksheet, gspread.Spreadsheet]:
    """
    Load a worksheet from a google sheet document.

    Nees a service account, see here: https://docs.gspread.org/en/latest/oauth2.html#for-bots-using-service-account
    Optionally, allows getting the full document instad of just a sheet.

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
):
    """
    Load google spread sheet & return it + DataFrame of it.

    :param data_path: str path to csv file with key-value to access sheet.
    :param dev_local_file: boolean to load from excel instead of
                           google (hard-coded).

    :return: gspread.worksheet (or None for dev_local_file = True).
    :return: pd.DataFrame
    """
    # For testing on local file
    if dev_local_file:
        return None, ensure_numeric_data(
            pd.read_excel("./data/metroloshiny_data.xlsx")
        )

    # Load laod google sheet with laser power at objective data
    url = get_private_data("Sheet URL", data_path=data_path)
    path_sa = get_private_data("PathToServiceAccountJSON", data_path=data_path)
    sheet = load_gspread(
        gsheet_url=url,
        sheet_name="laser_power_objective_measurements",
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
