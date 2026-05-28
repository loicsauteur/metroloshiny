from typing import TYPE_CHECKING, Optional

import numpy as np
import pandas as pd
from shiny import reactive
from shiny.express import input, render, ui

if TYPE_CHECKING:
    from shiny.types import FileInfo

from metroloshiny.utils.dataframe_utils import (
    convert_date_column,
    convert_power_column,
)

# Build the GUI
ui.page_opts(title="Metrology Upload")
with ui.nav_panel(title="Data Upload"):
    # Sidebar
    with ui.layout_sidebar():
        # Sidebar   ----------------------------------------------------------
        with ui.sidebar():
            ui.input_select(
                "category",
                "Select a Metrology Categroy",
                choices=["Test PSF", "Test Power"],
                # selected="PSF",
            )

        with ui.navset_card_underline():
            with ui.nav_panel(title="Test CSV upload"):
                ui.input_file(
                    "csv_selection",
                    "Choose a .csv file",
                    multiple=False,
                    accept=[".csv"],
                )

        with ui.navset_underline():
            with ui.nav_panel("CSV data"):

                @render.data_frame
                def render_csv():
                    # print("The selected file is:", input.csv_selection())
                    return render.DataGrid(parse_csv(), editable=True)


# Reactive functions        --------------------------------------------------


# Add custom behaviour to the table rendered in 'render_csv'
@render_csv.set_patch_fn
def update_patch(
    *,
    patch,
):
    """Validate and prevent wrong entries..."""
    ori_data = render_csv.data()
    row = patch["row_index"]
    col = patch["column_index"]
    new_value = patch["value"]
    ori_value = ori_data.iloc[row, col]

    # Make sure that only the last column is edited
    if col != len(ori_data.columns) - 1:
        ui.notification_show(
            f"You can only edit values in the column: {ori_data.columns[-1]}",
            type="warning",
        )
        return ori_value

    # Make sure the entry is an integer between 1-100
    try:
        new_value = int(new_value)
        if new_value > 0 and new_value <= 100:
            return new_value
    except ValueError:
        pass
    # Inform about invalid entries
    ui.notification_show(
        f"Invalid entry: {new_value}\n"
        "Please use integer [%] values between 1-100.",
        type="error",
    )
    return


@reactive.calc
def parse_csv():
    csv: Optional[list[FileInfo]] = input.csv_selection()
    if csv is None:
        return pd.DataFrame()

    # Parse csv (is a list of dicts)
    path = csv[0]["datapath"]

    delimiter, first_line, wavelength = identify_csv(path)

    df = pd.read_csv(csv[0]["datapath"], sep=delimiter, header=first_line)
    # Remove "unnamed" columns
    unnamed_cols = [x for x in df.columns if x.startswith("Unnamed")]
    df = df.drop(columns=unnamed_cols)
    # Remove the "Time..." column
    cols = [x for x in df.columns if x.startswith("Time")]
    df = df.drop(columns=cols)

    # Convert the date to YYYYmmdd
    df = convert_date_column(df)

    # Convert power measurements to mW
    df = convert_power_column(df)

    # Add column for entries of power %
    df[f"Enter the intensity (%) for {wavelength}nm"] = np.nan
    return df


# General functions        ---------------------------------------------------


def identify_csv(path: str) -> tuple[str, int, Optional[int]]:
    """
    Identify the csv file.

    :param path: str, path to file

    :return: tuple with:
        str, csv delimiter (e.g. ";")
        int, first line of data (for loading into DataFrame)
        int, wavelength used for the measurement
    """
    delimiter = None
    first_line = None
    wavelength = None
    with open(path, mode="r", encoding="utf-8") as file:
        for i, line in enumerate(file):
            # Find the file delimiter
            if line.startswith("Delimiter Used"):
                delimiter = line.split("'")[1]
            # Find the first data line
            if line.startswith("Samples"):
                first_line = i
            # Find the wavelength used
            if line.startswith("Wavelength"):
                wavelength = line.split(" ")[-2]
                try:
                    wavelength = int(wavelength)
                except ValueError as err:
                    raise RuntimeError(
                        "Could not identify the used Wavelength from: "
                        f"{line}, using <{' '.join(line.split(' ')[-2:])}>"
                    ) from err

    if delimiter is None or first_line is None:
        raise RuntimeError("Could not parse the uplaoded csv file!")

    # Correct the header position?? not sure why minus 2...
    return delimiter, first_line - 2, wavelength
