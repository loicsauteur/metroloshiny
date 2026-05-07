"""Utils for DataFrame manipulation."""

import warnings
from typing import Optional, Union

import pandas as pd

from metroloshiny.utils.common_utils import invert_nested_dict


@DeprecationWarning
def get_linearity(
    df: pd.DataFrame, date: str, rename_cols: bool = False
) -> pd.DataFrame:
    """# FIXME unused."""
    df = df.pivot(index=df.columns[1], columns=df.columns[0], values=date)
    # ensure that the header are all strings
    if rename_cols:
        df.columns = [str(x) + "nm" for x in df.columns]
    return df


@DeprecationWarning
def wavelength_to_color(w: Union[int, str]):
    """# FIXME unused.

    # Make sure to work with a number (remove 'nm')
    """
    if isinstance(w, str):
        w = w.split("nm")[0].strip()
        try:
            w = int(w)
        except Exception as e:
            print("Could not convert str to int:", e)

    print(w, type(w))
    # Convert wavelength to RGB
    w = int(w)
    if 380 <= w <= 440:
        r, g, b = -(w - 440) / (440 - 380), 0.0, 1.0
    elif 440 < w <= 490:
        r, g, b = 0.0, (w - 440) / (490 - 440), 1.0
    elif 490 < w <= 530:
        r, g, b = 0.0, 1.0, -(w - 530) / (530 - 490)
    elif 530 < w <= 580:
        r, g, b = (w - 510) / (580 - 530), 1.0, 0.0
    elif 580 < w <= 645:
        r, g, b = 1.0, -(w - 645) / (645 - 580), 0.0
    elif 645 < w <= 750:
        r, g, b = 1.0, 0.0, 0.0
    else:
        r, g, b = 0.0, 0.0, 0.0

    # intensity correction
    if 380 <= w <= 420:
        factor = 0.3 + 0.7 * (w - 380) / (420 - 380)
    elif 420 < w <= 645:
        factor = 1.0
    elif 645 < w <= 750:
        factor = 0.3 + 0.7 * (750 - w) / (750 - 645)
    else:
        factor = 0.0

    gamma = 0.8
    r = (r * factor) ** gamma
    g = (g * factor) ** gamma
    b = (b * factor) ** gamma
    return (r, g, b)


def get_power_over_time_data(
    df: pd.DataFrame,
    line: Optional[int] = None,
    power_prct: Optional[int] = None,
) -> pd.DataFrame:
    """
    Create a table of power measurements over time.

    Keeps only rows for specified wavelength (line), and or
    power_percentage. Combines these column values into a new column.

    The DataFrame will be "pivoted", giving a mW column with
    measurements per date/line/power.

    :param df: pd.DataFrame with columns = ["Line", "Power", "Date"]
               only one date.
    :param line: int of single line too keep.
    :param power_prct: int of single power to keep.

    :result: pd.DataFrame
    """
    # Sanity checks
    if line is None and power_prct is None:
        raise ValueError("Either line or power_prct must be specified!")
    # if len(df.columns) == 3:
    #    print(df.head())
    #    raise RuntimeError("Provided DataFrame does not have 3 columns!")
    # Select only a specific laser line
    if line:
        df = df[df[df.columns[0]] == line]

    # Select only a specifc percentage
    if power_prct:
        df = df[df[df.columns[1]] == power_prct]

    # Merge the Line and Power columns
    df["Line [nm] @ [%]"] = (
        df[df.columns[0]].astype(str) + " @ " + df[df.columns[1]].astype(str)
    )

    # Drop the two columns that were merged
    # df = df.drop(columns=df.columns[:2])

    # Reorder columns (last to first)
    cols = list(df)
    cols.insert(0, cols.pop(cols.index(cols[-1])))
    df = df.loc[:, cols]

    # Pivot the table
    df = df.melt(id_vars=df.columns[:3], var_name="Date", value_name="mW")
    return df


def filter_by_column_value(
    df: pd.DataFrame,
    column_name: str,
    value: Union[str, float],
    drop_column: bool = True,
) -> pd.DataFrame:
    """
    Filter a dataframe for rows according to column entry.

    e.g. keeps only the rows which have `value` in column of interest.

    :param df: pd.DataFrame.
    :param column_name: str name of the column.
    :param value: str or float column entries to keeps rows.
    :param drop_column: boolean, wether to keep the column or remove it.

    :return: pd.DataFrame (new)
    """
    # Filter rows where column contains search value
    df_filtered = df[df[column_name] == value]
    # Remove the column from the dataframe
    if drop_column:
        df_filtered = df_filtered.drop(columns=[column_name])
    return df_filtered


def get_light_source_kinds(df: pd.DataFrame) -> list:
    """
    Check if the data frame columsn for Laser and LED contain values.

    :param df: pd.DataFrame

    :return: list of column names with values
    """
    kinds = []
    if not df["Laser Line [nm]"].isna().all():
        kinds.append("Laser Line [nm]")
    if not df["LED Line [nm]"].isna().all():
        kinds.append("LED Line [nm]")
    return kinds


def keep_non_nan_rows(df: pd.DataFrame, column_name: str) -> pd.DataFrame:
    """
    Keep only rows with non NaNs for the specified column.

    :param df: pd.DataFrame
    :param column_name: str name of column

    :return: pd.DataFrame
    """
    if column_name not in df.columns:
        raise RuntimeError(f"Column <{column_name}> not found.")
    return df.dropna(subset=[column_name])


def parse_dates(dates: list[str]) -> list[str]:
    """
    Sort and ensure a list of yyyymmdd dates.

    :param dates: list of str dates (yyyymmddx*)

    :return: list of sorted str dates all in yyyymmdd
    """
    new_dates = [d[0:8] for d in dates]
    new_dates.sort()
    return new_dates


def filter_by_nested_dict(
    df: pd.DataFrame, nested_dict: dict, headers: list[str]
) -> dict:
    """
    Get indexes of the dataframe for values in a nested_dict.

    Used to idientify the rows where to put data into a table.
    The nested_dict contains keys to idientify specific row values,
    e.g. "C1" and "FWHM-Y", and the last level of the nested dict
    contains the value for entering into the talbe.

    The result is a dictionary with {index:value}.
    Indices are 0-based and excluding the header row.
    If an entry form the nested dict cannot be matched into the table,
    the index will be negative (decreasing by unmatched counts).

    :param df: pd.DataFrame
    :param nested_dict: e.g. {
            "C1" : {'FWHM-X': 911.0, 'FWHM-Y': 852.0, 'FWHM-Z': 1260.0}
        }
    :param headers: list for matching the df columns with
        the nested_dict keys.
    :return: dict {pd.DataFrame index : value of nested_dict}
    """
    # Enuser there is no duplicate entries
    try:
        _df = df.duplicated(subset=headers, keep=False)
        if _df.any():
            duplicates = df.loc[_df, headers]
            raise ValueError(
                f"Duplicate entries in the dataframe:\n{duplicates}"
            )
    except KeyError as err:
        raise KeyError(
            f"Selected headers do not matcht the table headers: {err}"
        ) from err

    # Create invered nested dict = {value: path of keys}
    inverted_dict = invert_nested_dict(nested_dict)

    # Create the result dict = {index: value}
    result = {}
    neg_idx = 0

    for value, key_list in inverted_dict.items():
        if len(headers) != len(key_list):
            raise RuntimeError(
                f"Number of specified headers ({len(headers)}) "
                f"does not match the number of row items {len(key_list)} "
                f"for the value."
            )
        _df = df.copy()
        for i in range(len(headers)):
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message="Boolean Series key will be reindexed to match DataFrame index",
                )
                _df = _df[df[headers[i]] == key_list[i]]
        index_list = _df.index.to_list()
        # print("index_list =", index_list)
        if len(index_list) == 0:
            neg_idx = neg_idx - 1
            result[neg_idx] = value
        elif len(index_list) > 1:
            raise RuntimeError(
                f"I expected here a dataframe with only one entry but got:\n{_df}"
            )
        else:
            result[index_list[0]] = value
    return result


if __name__ == "__main__":
    # # from metroloshiny.utils.read_file import read_xlsx
    # from metroloshiny.utils.read_file import get_laser_power_objective_data

    # # raw_df = read_xlsx()
    # # print(get_power_over_time_data(raw_df, 405, 100))
    # # df = get_linearity(raw_df, str(20240109))

    # # new tests
    # _, df = get_laser_power_objective_data(dev_local_file=True)
    # mic = "Ti CSU-W1"
    # # mic = "Ti2 Righty"
    # df = filter_by_column_value(df, "Site", "Hebelstrasse")
    # df = filter_by_column_value(df, "Microscope", mic)
    # df = filter_by_column_value(df, "Objective", "20x/0,75")
    # # skipping info sorting for testing
    # print(df)
    # df = keep_non_nan_rows(df, "LED Line [nm]")
    # print(df)
    pass
