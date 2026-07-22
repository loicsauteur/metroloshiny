"""Utils for writing google sheets."""

from itertools import pairwise
from typing import Union

import gspread as gs
import pandas as pd

from metroloshiny.utils.dataframe_utils import (
    nested_dict_to_table,
)
from metroloshiny.utils.read_file import ensure_numeric_data

# Google spreadsheet names
__gspread_names__ = {
    "Power": "laser_power_measurements",
    "PSF": "psf_measurements",
    "Objectives": "objective_db",
    "Uniformity": "field_dist_uni",
    "Test": "test_sheet",
}

# Cell formatting dictionaries
_updated_date_cell_format_ = {  # For date entries
    "backgroundColor": {"red": 1.0, "green": 1.0, "blue": 0.0},  # Yellow
    "horizontalAlignment": "RIGHT",
    "textFormat": {
        "foregroundColor": {"red": 0.0, "green": 0.0, "blue": 0.0},  # Black
        "bold": False,  # Does not work...
    },
}
_updated_cell_format_ = _updated_date_cell_format_.copy()  # For all entries
_updated_cell_format_["horizontalAlignment"] = "LEFT"
# updated_cell_format["textFormat"]["bold"] = False # Not working...


def make_entries(
    sheet: gs.Worksheet,
    data: pd.DataFrame,
):
    """
    Upload data to a google spread sheet.

    Note: I ran into an error (Range ('psf_measurements!U1) exceeds grid limits.'),
        when I deleted the last column and retried upload (it did not add, a new
        column as expected). Restarting the app, made it work...

    :param sheet: gs.Worksheet reference
    :param data: pd.DataFrame, should have the same columns as in the sheet.
    """
    # Get the sheet dataframe
    df = pd.DataFrame(sheet.get_all_records())

    # Check that all data columns (except last) are also in the sheet cols
    for c in data.columns[:-2]:
        if c not in df.columns:
            raise RuntimeError(
                f"Columns mismatch: <{c}> not found in gspread sheet."
            )

    # Get a list of the headers that are common
    merge_headers = list(data.columns[:-1])

    # Make sure the new data df is sorted
    data = data.sort_values(by=merge_headers)

    # Ensure numeric data for specific sheet dataframes     ------------------
    # For power data
    if "Power [%]" in df.columns:
        df = ensure_numeric_data(df, first_column=4)
        # Add missing column to new data dataframe
        if "Laser Line [nm]" in data.columns:
            # Insert empty LED Line.. columns
            data.insert(5, "LED Line [nm]", [""] * len(data))
        else:
            # Insert empty Laser Line.. columns
            data.insert(4, "Laser Line [nm]", [""] * len(data))
    # For PSF data
    if "FWHM" in df.columns:
        df = ensure_numeric_data(df, first_column=6)
    # TODO ensure numeric data also for other sheets

    # Identify column & cell address for the date       ----------------------
    headers = [str(x) for x in df.columns]
    date = str(data.columns[-1])
    if date not in headers:
        col = len(df.columns) + 1
    else:
        col = headers.index(date) + 1
    # Add new column if necessary
    if sheet.column_count < col:
        # Note: I get a google error if I delete last col I just added...
        sheet.add_cols(cols=1)
    date_cell = sheet.cell(row=1, col=col)
    col = date_cell.address.replace(str(1), "")  # get col letter(s)

    # Match the sheet table with the new data           ----------------------
    # (Copy and) rename the index of the sheet (database)
    dest_df = df.copy()[merge_headers].reset_index(names="match_index")
    # "Merge" the 2 dataframes (keeps the new data df, adds match_index col)
    dest_df = data.merge(dest_df, on=merge_headers, how="left")
    # FIXME: possible `ValueError: You are trying to merge on str and int64 columns for key 'Power [%]'.`
    #       when sheet and data dataframe columns not of the same type...

    # Decrementally index rows that were not found
    mask = dest_df["match_index"].isna()
    dest_df.loc[mask, "match_index"] = -pd.RangeIndex(1, mask.sum() + 1)
    # Make sure the matched index is integer
    dest_df["match_index"] = dest_df["match_index"].astype(int)

    # Get the list of target indices
    indices = list(dest_df["match_index"])

    # Check if new entries or not or mix        ------------------------------
    new_entries = False
    # All indices negative: entries go to end of the sheet
    if all(i < 0 for i in indices):
        new_entries = True
    # All indices positive: entries go to existing rows
    elif all(i >= 0 for i in indices):
        pass
    else:
        missing_entries = dest_df[dest_df["match_index"] < 0]
        missing_entries = missing_entries.drop("match_index", axis=1)
        raise RuntimeError(
            "Error: Not all the data could be matched to existing entries.\n"
            "Manual curration in the google sheet is needed to add following "
            f"missing rows. I.e.:\n\n{missing_entries}"
        )

    # Adding entries                ------------------------------------------
    # Add entries to existing rows
    if not new_entries:
        # Set indices off by 2 for the spread sheet
        indices = [i + 2 for i in indices]
        # Check if the indices are continuous (to write as a block)
        if any(a + 1 != b for a, b in pairwise(indices)):
            # if not check_if_sequence(indices): # old version using cell-addresses list
            raise NotImplementedError(
                "Values cannot be uploaded: Value upload is supported only "
                "if they can be added as a 'block'.\n"
                f"Your values would end up in spreadsheet rows: {indices}, "
                "which has gaps/missing rows."
            )
        # Create a list of value addresses
        value_addresses = [f"{col}{i}" for i in indices]
        start_cell = value_addresses[0]
        end_cell = value_addresses[-1]
        # Check if the cells for values are empty
        cells = sheet.get(f"{start_cell}:{end_cell}")
        if len(cells) != 0:
            filled_cells = []
            for i in range(len(cells)):
                if len(cells[i]) != 0:
                    filled_cells.append(value_addresses[i])
            raise RuntimeError(
                f"Following cells already contain values: {filled_cells}"
            )
        # Enter the values
        value_block = [[i] for i in dest_df[date]]  # 2D array
        sheet.update(range_name=f"{start_cell}:{end_cell}", values=value_block)
        sheet.format(
            ranges=f"{start_cell}:{end_cell}", format=_updated_cell_format_
        )

    # Create new entries at the bottom of the sheet
    else:
        # Create 3D arrays for the "common block" and value block
        common_block = dest_df[dest_df.columns[:-2]].to_numpy().tolist()
        value_block = [[i] for i in dest_df[date]]

        # Get start and end rows
        start_row = len(df) + 2
        end_row = start_row + len(common_block) - 1
        # Add additional rows if necessary # TODO not checked...
        if sheet.row_count < end_row:
            sheet.add_rows(rows=end_row - sheet.row_count)
        # Create cell addresses
        last_col_letter = chr(ord("@") + len(common_block[0]))
        block_range = f"A{start_row}:{last_col_letter}{end_row}"
        # Write the common block
        sheet.update(range_name=block_range, values=common_block)
        sheet.format(ranges=block_range, format=_updated_cell_format_)
        # Write the values
        val_range = f"{col}{start_row}:{col}{end_row}"
        sheet.update(range_name=val_range, values=value_block)
        sheet.format(ranges=val_range, format=_updated_cell_format_)

    # Add date if necessary
    if date_cell.value is None:
        sheet.update_acell(label=date_cell.address, value=date)
        sheet.format(
            ranges=date_cell.address, format=_updated_date_cell_format_
        )


def prepare_data_for_entry(
    data: Union[dict, pd.DataFrame],
    data_headers: list[str],
    site: str,
    microscope: str,
    objective: str,
    info: str,
    date: str,
) -> pd.DataFrame:
    """
    Create a dataframe similar to spreadsheet table.

    :param data: dict, (nested) e.g. {
            "C1" : {'FWHM-X': 911.0, 'FWHM-Y': 852.0, 'FWHM-Z': 1260.0},
            ...
        }
        if it is a DF...
    :param data_headers: list[str], nested dict headers, excluding value column.
        e.g. ["Channel", "FWHM"]
    """
    # Sainity check
    if not isinstance(data_headers, list):
        raise RuntimeError("Data headers are not a list!")
    if isinstance(data, dict):
        # Convert the nested (data) dict to a table
        df = nested_dict_to_table(data, data_headers, date)
    else:
        # Check if headers are OK
        df = pd.DataFrame(data)
        cur_headers = list(df.columns)
        # Check that the number of columns is correct
        if len(cur_headers) != len(data_headers) + 1:
            raise RuntimeError(
                f"Expected a dataframe with {len(data_headers) + 1} columns, "
                f"but got {len(cur_headers)} columns."
            )
        # Check if the needed headers are in the current dataframe
        for h in data_headers:
            if h not in cur_headers:
                raise RuntimeError(
                    f"The current data is missing a needed header: {h}."
                )
        # Check the value header
        if str(cur_headers[-1]) != date:
            if str(cur_headers[-1]) == "Value":
                # Replace value with the date
                new_headers = data_headers.copy()
                new_headers.append(date)
                df.columns = new_headers
            else:
                raise RuntimeError(
                    "Provided data value column header is not recognised: "
                    f"{cur_headers[-1]}"
                )
    # Reset the df index
    df = df.reset_index(drop=True)

    # Create the common columns
    common_df = {
        "Site": [site] * len(df),
        "Microscope": [microscope] * len(df),
        "Objective": [objective] * len(df),
        "Info": [info] * len(df),
    }
    common_df = pd.DataFrame.from_dict(common_df)
    # Join the dataframes
    return pd.concat([common_df, df], axis=1)


if __name__ == "__main__":
    pass
