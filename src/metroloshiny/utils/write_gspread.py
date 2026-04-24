"""Utils for writing google sheets."""

from typing import Optional, Union

import gspread as gs
import pandas as pd

from metroloshiny.utils.common_utils import get_today

__gspread_names__ = {
    "Power": "laser_power_objective_measurements",
    "PSF": "psf_measurements",
}

# Google spreadsheet headers 1-based indices
__gspread_headers__ = {
    "Site": 1,
    "Microscope": 2,
    "Objective": 3,
    "Info": 4,
    "Channel": 5,  # PSF
    "FWHM": 6,  # PSF
    "Laser Line [nm]": 5,  # Power
    "LED Line [nm]": 6,  # Power
    "Power [%]": 7,  # Power
}

# Google spreadsheet headers matched to column alphapet
__gspread_h2a__ = {
    "Site": "A",
    "Microscope": "B",
    "Objective": "C",
    "Info": "D",
    "Channel": "E",  # PSF
    "FWHM": "F",  # PSF
    "Laser Line [nm]": "E",  # Power
    "LED Line [nm]": "F",  # Power
    "Power [%]": "G",  # Power
}


def identify_entry_coords(
    df: pd.DataFrame,
    microscope: str,
    objctive: str,
    info: str,
    date: Optional[str] = None,
    channel: Optional[str] = None,
    fwhm: Optional[str] = None,
    line_header: Optional[str] = None,
    line: Optional[str] = None,
    power: Optional[str] = None,
) -> tuple[int, int, bool]:
    """
    Get worksheet coordinates for entering data.

    :param microscope: str
    :param objctive: str
    :param info: str
    :param date: Optional[str] in YYYYmmdd,
    :param channel: Optional[str] for PSF sheet
    :param fwhm: Optional[str] for PSF sheet
    :param line_header: Optional[str] for power sheet
    :param line: Optional[str] for power sheet
    :param power: Optional[str] for power sheet
    FIXME: more sheets = more parameters

    :return: 1-based roww
    :return: 1-based column (may be -1 if empty sheet)
    :return: boolean, true for at the end of the sheet (row/bottom)
    """
    # Sanity check (not entries in sheet)
    if df.empty:
        return 2, -1, True
    headers = [str(x) for x in df.columns]

    # Pre-check for line & power
    if (line is None) != (line_header is None) != (power is None):
        raise RuntimeError(
            "The line_hader, line(-item) and power must be specified!"
        )

    # Sanity checks, make sure optional perameter's columns exist
    if channel is not None and "Channel" not in headers:
        raise RuntimeError(
            "Expected a Channel column in sheet but there was not."
        )
    if fwhm is not None and "FWHM" not in headers:
        raise RuntimeError(
            "Expected a FWHM column in sheet but there was not."
        )
    if line_header is not None:
        if line_header not in headers:
            raise RuntimeError(
                f"Expected a <{line_header}> column in the sheet bet there was not."
            )
        if "Power [%]" not in headers:
            raise RuntimeError(
                "Expected a <Power [%]> column in the sheet but there was not."
            )

    if date is None:
        date = get_today()

    # Check in which column to add the date
    if date not in headers:
        col_target = len(headers) + 1
    else:
        col_target = headers.index(date) + 1

    # Identify the rows, where to add data
    n_total_rows = df.shape[0]  # excluding the header row
    if n_total_rows == 0:
        # Not entries in sheet yet
        return 2, col_target, True

    # Get a list of indices where the microscope matches    ------------------
    rows = df.index[df["Microscope"] == microscope].tolist()
    if len(rows) == 0:
        # Microscope not in the sheet yet, can be put to the end
        # FYI: total rows + header + new row
        return n_total_rows + 2, col_target, True

    # Get a list of indices where the objective matches     ------------------
    _rows = df.index[df["Objective"] == objctive].tolist()
    rows = list(
        set(rows) & set(_rows)
    )  # Get the intersection of the two lists
    if len(rows) == 0:
        # Objective for entry not in sheet, can be put to the end
        return n_total_rows + 2, col_target, True

    # Get a list of indices where the info matches     -----------------------
    _rows = df.index[df["Info"] == info].tolist()
    rows = list(
        set(rows) & set(_rows)
    )  # Get the intersection of the two lists
    if len(rows) == 0:
        # Info for entry not in sheet, can be put to the end
        return n_total_rows + 2, col_target, True

    # Optional entry checks         ------------------------------------------
    # Channel
    if channel is not None:
        _rows = df.index[df["Channel"] == channel].tolist()
        rows = list(
            set(rows) & set(_rows)
        )  # Get the intersection of the two lists
        if len(rows) == 0:
            # Objective for entry not in sheet, can be put to the end
            return n_total_rows + 2, col_target, True

    # FWHM
    if fwhm is not None:
        _rows = df.index[df["FWHM"] == fwhm].tolist()
        rows = list(
            set(rows) & set(_rows)
        )  # Get the intersection of the two lists
        if len(rows) == 0:
            # Objective for entry not in sheet, can be put to the end
            return n_total_rows + 2, col_target, True

    # Line and power
    if line_header is not None:
        # Info: line & power values are not str but float (for equal check)
        _rows = df.index[df[line_header] == float(line)].tolist()
        rows = list(
            set(rows) & set(_rows)
        )  # Get the intersection of the two lists
        _rows = df.index[df["Power [%]"] == float(power)].tolist()
        rows = list(
            set(rows) & set(_rows)
        )  # Get the intersection of the two lists
        if len(rows) == 0:
            # Line/power for entry not in sheet, can be put to the end
            return n_total_rows + 2, col_target, True

    # There should only be one row entry
    if len(rows) != 1:
        raise RuntimeError(
            "Found multiple rows for data entry. Should be only one."
        )
    # Is the row at the end?
    if rows[0] + 1 == n_total_rows:
        print(
            "will add to (end of function/last row):",
            n_total_rows + 2,
            col_target,
            True,
        )
        return n_total_rows + 2, col_target, True
    # Correct to 1-based sheet index (including header row)
    return rows[0] + 2, col_target, False


def make_sheet_entry(
    sheet: gs.Worksheet,
    value: Union[float, str],
    site: str,
    microscope: str,
    objctive: str,
    info: str,
    date: Optional[str] = None,
    channel: Optional[str] = None,
    fwhm: Optional[str] = None,
    line_header: Optional[str] = None,
    line: Optional[str] = None,
    power: Optional[str] = None,
) -> str:
    """
    Make an entry to the google sheet.

    Marks updated cells in the google sheet with a
    yellow background.

    raises mostly RuntimeErrors if something is wrong.

    :param site: str
    :param microscope: str
    :param objctive: str
    :param info: str
    :param date: Optional[str] in YYYYmmdd,
    :param channel: Optional[str] for PSF sheet
    :param fwhm: Optional[str] for PSF sheet
    :param line_header: Optional[str] for power sheet
    :param line: Optional[str] for power sheet
    :param power: Optional[str] for power sheet
    FIXME: more sheets = more parameters

    :return: str = f"Sucessfully entered <{value}> into cell: {cur_cell_address}"
    """
    # Define the cell formating for updated cells
    updated_date_cell_format = {
        "backgroundColor": {"red": 1.0, "green": 1.0, "blue": 0.0},
        "horizontalAlignment": "RIGHT",
        "textFormat": {
            "foregroundColor": {"red": 0.0, "green": 0.0, "blue": 0.0},
            "bold": False,  # Does not work...
        },
    }
    updated_cell_format = updated_date_cell_format.copy()
    updated_cell_format["horizontalAlignment"] = "LEFT"
    # updated_cell_format["textFormat"]["bold"] = False # Not working...

    # Get the date if it is None
    if date is None:
        date = get_today()

    # Convert the sheet to a dataframe
    df = pd.DataFrame(sheet.get_all_records())

    # Identify where to put the data (1-based indices)
    row, col, end_of_sheet = identify_entry_coords(
        df=df,
        microscope=microscope,
        objctive=objctive,
        info=info,
        date=date,
        channel=channel,
        fwhm=fwhm,
        line_header=line_header,
        line=line,
        power=power,
    )

    # if sheet empty (col == -1), identify correct column
    if col == -1:
        headers = sheet.row_values(1)
        if date not in headers:
            col = len(headers) + 1
        else:
            col = headers.index(date) + 1
    # Enter date in sheet
    date_cell = sheet.cell(row=1, col=col)
    if date_cell.value is None:
        update_value_format(
            sheet=sheet,
            label=date_cell.address,
            value=str(date),
            format=updated_date_cell_format,
        )
    elif str(date_cell) == date_cell.value:
        raise RuntimeError(
            "Could not enter date to sheet. "
            + f"Contains <{date_cell.value}>, expected <{date}>"
        )

    # Enter value       ------------------------------------------------------
    if not end_of_sheet:
        # Only need to enter the value
        value_cell = sheet.cell(row=row, col=col)
        if value_cell.value is not None:
            raise RuntimeError(
                "The cell to enter the new value is not empty! "
                + f"Existing value = {value_cell.value}. "
                + f"Value to be entered = {value}."
            )
        update_value_format(
            sheet=sheet,
            label=value_cell.address,
            value=value,
            format=updated_cell_format,
        )
        sheet.update_acell(label=value_cell.address, value=value)
        sheet.format(ranges=value_cell.address, format=updated_cell_format)
    else:
        # New entry at the end of the sheet
        # Enter the common row entries
        constant_range = f"A{row}:D{row}"
        sheet.update(
            values=[[site, microscope, objctive, info]],
            range_name=constant_range,
        )
        sheet.format(ranges=constant_range, format=updated_cell_format)

        # Enter the sheet specific row entries      --------------------------
        if channel is not None:
            cur_cell_address = f"{__gspread_h2a__.get('Channel')}{row}"
            update_value_format(
                sheet=sheet,
                label=cur_cell_address,
                value=channel,
                format=updated_cell_format,
            )

        if fwhm is not None:
            cur_cell_address = f"{__gspread_h2a__.get('FWHM')}{row}"
            update_value_format(
                sheet=sheet,
                label=cur_cell_address,
                value=fwhm,
                format=updated_cell_format,
            )

        if line_header is not None:
            # Checks for line stuff already
            # done in identify_entry_coords function
            cur_cell_address = f"{__gspread_h2a__.get(line_header)}{row}"
            update_value_format(
                sheet=sheet,
                label=cur_cell_address,
                value=line,
                format=updated_cell_format,
            )
            cur_cell_address = f"{__gspread_h2a__.get('Power [%]')}{row}"
            update_value_format(
                sheet=sheet,
                label=cur_cell_address,
                value=power,
                format=updated_cell_format,
            )

        # Finally enter also the value
        cur_cell_address = sheet.cell(row=row, col=col).address
        update_value_format(
            sheet=sheet,
            label=cur_cell_address,
            value=value,
            format=updated_cell_format,
        )
    return f"Sucessfully entered <{value}> into cell: {cur_cell_address}"


def update_value_format(
    sheet: gs.Worksheet,
    label: str,
    value: Union[float, str],
    format: dict,
):
    """
    Update a gspread sheet with value and cell format.

    :param sheet: gspread Worksheet
    :param label: A1 notation for the gspread cell, e.g. A1 (no ranges)
    :param value: Value to enter
    :param format: dict for the cell foramt
    """
    sheet.update_acell(label=label, value=value)
    sheet.format(ranges=label, format=format)


if __name__ == "__main__":
    # sheet = get_gspread(sheet_name=__gspread_names__.get("PSF"))
    # #sheet = get_gspread(sheet_name="testing")

    # df = pd.DataFrame(sheet.get_all_records())
    # df = ensure_numeric_data(df, first_column=4) # 4 for power, 6 for psf

    # make_sheet_entry(
    #     sheet=sheet, value=123.4, site="Hebelstrasse", microscope="BSL2", objctive="11x/0.3", info="fake"
    # )
    pass
