"""Utils for writing google sheets."""

from typing import Any, Optional

import gspread as gs
import pandas as pd

from metroloshiny.utils.common_utils import (
    check_if_sequence,
    invert_nested_dict,
)
from metroloshiny.utils.dataframe_utils import filter_by_nested_dict
from metroloshiny.utils.read_file import ensure_numeric_data

# Google spreadsheet names
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


def make_sheet_entries(
    sheet: gs.Worksheet,
    site: str,
    microscope: str,
    objective: str,
    info: str,
    date: Optional[str] = None,
    fwhm_data: Optional[dict] = None,
    power_data: Optional[Any] = None,  # FIXME to be defined & implemented
    # channel: Optional[str] = None, # FIXME currently unused
    # fwhm: Optional[str] = None, # FIXME currently unused
    line_header: Optional[str] = None,  # FIXME currently unused
    line: Optional[str] = None,  # FIXME currently unused
    power: Optional[str] = None,  # FIXME currently unused
):
    """
    Make google sheet entries.

    Marks the cells with a yellow background.
    Inputs are handled on the metrology data kind.
    Any (but not multiple) fo the data parameres must be provided, i.e.
    fwhm_data or power_data or ... FIXME more to come

    :param sheet: gs.Worksheet
    :param site: str site name
    :param microscope: str microscope name
    :param objective: str objective name
    :param info: str info column text
    :param date: Optional[str] YYYYmmdd. Default None -> gets Today
    :param fwhm_data: Optional[dict[dict]], FWHM data to be entered, e.g.:
        {"DAPI" : {'FWHM-X': 911.0, 'FWHM-Y': 852.0, 'FWHM-Z': 1260.0}, ... }
    :param power_data: Optional[Any] = None,  # FIXME to be defined

    :return: no return
    """
    # Sanity checks FIXME add more if more implemented
    if fwhm_data is None and power_data is None:
        raise RuntimeError("Cannot make entry without FWHM or Power data!")

    # Init stuff
    df = None  # dataframe of the sheet
    address_dict = None  # dict mapping cell addresses to values
    data_to_use = None  # will point to fwhm_data or power_data or ...

    # Check fwhm data
    if fwhm_data is not None:
        for ch, values in fwhm_data.items():
            # FIXME remove the conditional startwith C??
            if not ch.startswith("C") and ch not in [
                "DAPI",
                "GFP",
                "Cy3",
                "Cy5",
            ]:
                raise RuntimeError(
                    f"FWHM data channel name <{ch}> not supported"
                )
            for f in values.keys():
                if not f.startswith("FWHM-"):
                    raise RuntimeError(
                        f"FWHM label <{f}> for channel <{ch}> not supported."
                    )
        # Convert the sheet to pandas
        df = pd.DataFrame(sheet.get_all_records())
        df = ensure_numeric_data(df, first_column=6)
        # List the column headers for identifying the sheet rows
        data_headers = ["Channel", "FWHM"]
        data_to_use = fwhm_data

    # TODO same check for other data dicts
    if power_data is not None:
        data_to_use = power_data
        data_headers = ["Line x", "Power"]  # FIXME to be done
        raise NotImplementedError(
            "Data upload for Power measurements not yet implemented!"
        )

    # Identify column & the cell address for the date   ----------------------
    headers = [str(x) for x in df.columns]
    if date not in headers:
        col = len(df.columns) + 1
    else:
        col = headers.index(date) + 1

    date_cell = sheet.cell(row=1, col=col)
    col = date_cell.address.replace(str(1), "")

    # Check where to put the entries    --------------------------------------
    new_entry = False  # To remember to add full new rows
    address_dict = {}
    # Filter the dictionary by the common columns
    _df = df[
        (df["Site"] == site)
        & (df["Microscope"] == microscope)
        & (df["Objective"] == objective)
        & (df["Info"] == info)
    ]
    # Get a dict {df-row-index : value}
    entry_dict = filter_by_nested_dict(_df, data_to_use, data_headers)
    indices = list(entry_dict.keys())
    # All indicies are negative: all entries to the end of the sheet
    if any(val < 0 for val in indices):
        new_entry = True
    # All indicies are positvie: entries go to exisiting rows
    elif any(val > 0 for val in indices):
        # Create the address (offset row to 1-based index + header row)
        for k, v in entry_dict.items():
            address_dict[f"{col}{k + 2}"] = v
    else:
        raise RuntimeError(
            "The sheet does not seem to be ordered properly: "
            "some row entries exisit while others don't."
        )

    # Adding entries            ----------------------------------------------
    # Add entries to the exisiting rows
    if not new_entry:
        # Check if the addresses are continous
        if not check_if_sequence(address_dict.keys()):
            raise NotImplementedError(
                "Values to be written are not continous."
                f"Data to be entered in cells: {address_dict.keys()}"
            )
        # Check if the cells for values are empty!
        cell_addresses = list(address_dict.keys())
        start_cell = cell_addresses[0]
        end_cell = cell_addresses[-1]
        cells = sheet.get(f"{start_cell}:{end_cell}")
        if len(cells) != 0:
            filled_cells = []
            for i in range(len(cells)):
                if len(cells[i]) != 0:
                    filled_cells.append(cell_addresses[i])
            raise RuntimeError(
                f"Following cells already contain values: {filled_cells}"
            )
        # Enter the cell values
        value_block = []
        for v in address_dict.values():
            value_block.append([v])

        sheet.update(range_name=f"{start_cell}:{end_cell}", values=value_block)
        sheet.format(
            ranges=f"{start_cell}:{end_cell}", format=_updated_cell_format_
        )

    # Create new entries at the bottom of the sheet
    else:
        inverted_dict = invert_nested_dict(data_to_use)
        new_block = []  # Block for the first columns
        value_block = []  # Block for the values in the date column
        for value, path in inverted_dict.items():
            new_line = [site, microscope, objective, info]
            for p in path:
                new_line.append(p)
            new_block.append(new_line)
            value_block.append([value])
        start_row = len(df) + 2
        end_row = start_row + len(inverted_dict) - 1
        # Get column letter of the last column
        last_col_letter = chr(ord("@") + len(new_block[0]))
        # Write the common info block
        block_range = f"A{start_row}:{last_col_letter}{end_row}"
        sheet.update(range_name=block_range, values=new_block)
        sheet.format(ranges=block_range, format=_updated_cell_format_)
        # Write the values
        val_range = f"{col}{start_row}:{col}{end_row}"
        sheet.update(range_name=val_range, values=value_block)
        sheet.format(ranges=val_range, format=_updated_cell_format_)

    # Finally also add the date to the sheet if not there
    if date_cell.value is None:
        sheet.update_acell(label=date_cell.address, value=date)
        sheet.format(
            ranges=date_cell.address, format=_updated_date_cell_format_
        )


if __name__ == "__main__":
    pass
    # sheet = get_gspread(sheet_name=__gspread_names__.get("PSF"))
    # # #sheet = get_gspread(sheet_name="testing")

    # # FIXME need to change the keys to e.g. DAPI...
    # data1 = {
    #     "C1" : {'FWHM-X': 911.0, 'FWHM-Y': 852.0, 'FWHM-Z': 1260.0},
    #     "C2" : {'FWHM-X': 651.0, 'FWHM-Y': 643.0, 'FWHM-Z': 860.0},
    #     "C3" : {'FWHM-X': 823.0, 'FWHM-Y': 876.0, 'FWHM-Z': 1020.0},
    #     "C4" : {'FWHM-X': 898.0, 'FWHM-Y': 954.0, 'FWHM-Z': 1142.0},
    # }
    # data = {
    #     "DAPI" : {'FWHM-X': 911.0, 'FWHM-Y': 852.0, 'FWHM-Z': 1260.0},
    #     "GFP" : {'FWHM-X': 651.0, 'FWHM-Y': 643.0, 'FWHM-Z': 860.0},
    #     "Cy3" : {'FWHM-X': 823.0, 'FWHM-Y': 876.0, 'FWHM-Z': 1020.0},
    #     "Cy5" : {'FWHM-X': 898.0, 'FWHM-Y': 954.0, 'FWHM-Z': 1142.0},
    # }

    # make_sheet_entries(
    #     sheet=sheet,
    #     site="TestSite",
    #     microscope="TestMic",
    #     objective="TestObj",
    #     info="TestInfo",
    #     date="19991212",
    #     fwhm_data=data
    # )
    # print(">>>>done!")

    # # df = pd.DataFrame(sheet.get_all_records())
    # # df = ensure_numeric_data(df, first_column=4) # 4 for power, 6 for psf

    # # make_sheet_entry(
    # #     sheet=sheet, value=123.4, site="Hebelstrasse", microscope="BSL2", objctive="11x/0.3", info="fake"
    # # )
