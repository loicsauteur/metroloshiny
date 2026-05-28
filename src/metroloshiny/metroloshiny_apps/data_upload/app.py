from typing import TYPE_CHECKING, Optional

import numpy as np
import pandas as pd
from shiny import reactive
from shiny.express import input, render, ui

if TYPE_CHECKING:
    from shiny.types import FileInfo

from metroloshiny.data_objects.PSFData import PSFData
from metroloshiny.utils.common_utils import (
    check_duplicate_dict_values,
    invert_nested_dict,
)
from metroloshiny.utils.dataframe_utils import (
    convert_date_column,
    convert_power_column,
    filter_by_column_value,
)
from metroloshiny.utils.omero_utils import omero_operation
from metroloshiny.utils.read_file import (
    check_upload_password,
    get_sheet,
    load_doc,
)
from metroloshiny.utils.write_gspread import make_sheet_entries

# Load Data
use_dev_local_file = False
sheet_doc = load_doc(dev_local_file=use_dev_local_file)
# wsheet_psf, df = get_sheet(sheet_doc, "PSF", dev_local_file=use_dev_local_file)

# Reactive values       ------------------------------------------------------
sheet_reference = reactive.value(None)
dataframe = reactive.value(None)
category_list = ["Power", "PSF"]

# Entry selection UI elements       ------------------------------------------
microscope = ui.input_select("microscope", "Select a microscope", choices=[])
objective = ui.input_select("objective", "Select an objective", choices=[])
info = ui.input_select("info", "Filter by info column", choices=[])
microscope_list = reactive.value([])
objective_list = reactive.value([])
info_list = reactive.value([])
new_mic_name = ui.input_text(
    "new_mic_name",
    "* New microscope *",
    "Enter name for new microscope...",
)
new_obj_name = ui.input_text(
    "new_obj_name",
    "* New objective *",
    "Enter name for new objective...",
)
new_info_name = ui.input_text("new_info_name", "* New Info *", "Enter info...")

# OMERO data retrieve UI items      ------------------------------------------
omero_type_selector = ui.input_select(
    "omero_type_selector",
    "Select OMERO type",
    choices=["Dataset", "Image"],
    selected="Image",
)
omero_id_selector = ui.input_text(
    "omero_id_selector", "OMERO ID", "Enter OMERO ID...2861227 or 2832822"
)
check_omero_data = ui.input_action_button("check_omero_data", "Check OMERO")
upload_omero_button = ui.input_action_button(
    "upload_omero_button", "Upload the data!"
)

# CSV data upload UI items          ------------------------------------------
csv_light_selector = ui.input_select(
    "csv_light_selector",
    "Select the light source kind",
    choices=["Please choose", "Laser", "LED"],
    selected="Please choose",
)
csv_file_selector = ui.input_file(
    "csv_file_selector", "Choose a .csv file", multiple=False, accept=[".csv"]
)
upload_power_button = ui.input_action_button(
    "upload_power_button", "Upload the data!"
)

# Build the GUI     items       ----------------------------------------------
ui.page_opts(title="Metrology Upload")
with ui.nav_panel(title="Data Upload"):
    # Sidebar
    with ui.layout_sidebar():
        # Sidebar   ----------------------------------------------------------
        with ui.sidebar():
            ui.input_select(
                "category",
                "Select a Metrology Categroy",
                choices=category_list,
                # selected="PSF",
            )
            ui.input_select("site", "Select a site", choices=[])
            ui.input_password("upload_pwd", "Password for upload")

            @render.text
            @reactive.event(input.upload_pwd)
            def password_check():
                """
                Check the password input.

                Minimal 5 character to show whether correct or wrong.
                """
                cur_input = input.upload_pwd()
                if len(cur_input) <= 5 or cur_input is None:
                    return ""
                if check_upload_password(cur_input):
                    return "Correct password"
                else:
                    return "Wrong password"

        # Microscope entry  --------------------------------------------------
        with ui.navset_card_underline():
            with ui.nav_panel(title="Microscope entry"):
                with ui.layout_column_wrap(
                    width=1 / 2, min_height="150px", max_height="1000px"
                ):
                    # Render the entry selection in 2 columns
                    # Column 1 for drop-down selection
                    @render.ui
                    def mic_col_1():
                        return microscope, objective, info

                    # Column 2 for "new" text entries
                    @render.ui
                    def mic_col_2():
                        return new_mic_name, new_obj_name, new_info_name

        # Upload Info   ------------------------------------------------------
        with ui.navset_card_underline():
            # Upload from OMERO     ------------------------------------------
            with ui.nav_panel(title="Upload from OMERO"):

                @render.ui
                @reactive.event(input.category)
                def render_omero_upload():
                    """Show OMERO input selectors only on PSF category."""
                    if input.category() != "PSF":
                        ui.notification_show(
                            f"{input.category()} upload from OMERO not implemented!",
                            type="warning",
                        )
                        return f"{input.category()} upload from OMERO not implemented!"
                    return omero_type_selector, omero_id_selector

                # Show 2 tables: Data for upload and channel naming table
                with ui.layout_column_wrap(width=1 / 2):
                    with ui.card():
                        ui.card_header("OMERO data")

                        @render.data_frame
                        @reactive.event(
                            input.omero_type_selector,
                            input.omero_id_selector,
                            input.category,
                        )
                        def omero_data():
                            # FIXME currently only for FWHM (cannot use params for reactive.calc)
                            omero_data = parse_omero_fwhm()
                            if input.category() != "PSF" or omero_data is None:
                                return render.DataGrid(
                                    pd.DataFrame(), editable=False
                                )
                            return render.DataGrid(omero_data, editable=False)

                    with ui.card():
                        ui.card_header("Provide channel names")

                        @render.data_frame
                        @reactive.event(omero_data.data)
                        def omero_channel_names():
                            data = omero_data.data()
                            if data is None or data.empty:
                                return render.DataGrid(pd.DataFrame())

                            # Create new table with unique channel identifiers (e.g. C1)
                            channels = list(
                                np.unique(np.asarray(data["Channel"]))
                            )
                            channels = {
                                "Channel": channels,
                                "Enter channel name": [""] * len(channels),
                            }
                            channels = pd.DataFrame().from_dict(channels)
                            return render.DataGrid(channels, editable=True)

                # Show the upload button
                @render.ui
                def show_omero_upload_btn():
                    return upload_omero_button

            # Upload from CSV       ------------------------------------------
            with ui.nav_panel(title="Upload from CSV"):

                @render.ui
                @reactive.event(input.category)
                def csv_upload_selections():
                    """Show LED/Laser selection only on Power category."""
                    if input.category() != "Power":
                        ui.notification_show(
                            f"{input.category()} upload from CSV not implemented!",
                            type="warning",
                        )
                        return f"{input.category()} upload from CSV not implemented!"
                    # It seems impossible to reset the selected file (even if dialog does not show it)
                    return csv_file_selector, csv_light_selector

                @render.text
                def show_csv_name():
                    """
                    Inform which csv file is being displayed.

                    When selecting a file but switching categories, the file cannot be
                    forgotten/reset. So it is for information...
                    """
                    if input.category() != "Power":
                        return ""
                    name = (
                        "None"
                        if not input.csv_file_selector()
                        else input.csv_file_selector()[0]["name"]
                    )
                    return f"Currently showing: {name}"

                @render.data_frame
                def render_csv():
                    if input.category() != "Power":
                        # I dont manage to rest the input_file selection
                        # Hence just rest the talbe.
                        return render.DataGrid(pd.DataFrame(), editable=False)

                    selected = input.csv_file_selector()
                    if selected is not None:
                        ui.update_select(
                            "csv_file_selector",
                        )

                    return render.DataGrid(parse_csv_power(), editable=True)

                # FIXME currently only the upload csv data for power measurements
                @render.ui
                def show_power_upload_btn():
                    return upload_power_button


# General functions     ------------------------------------------------------


def check_new_microscope_entries():
    """
    Check if new microscope entries were entered.

    Checks also if there are same or similar (no special characters,
    lower case) entries already in the available choices.

    :return: If entries good:
        tuple(True, microscope name, objective name, info name)
        Otherwise return: (False, None, None, None)
    """
    mic = input.microscope()
    obj = input.objective()
    info = input.info()
    mic_name = input.new_mic_name()
    obj_name = input.new_obj_name()
    info_name = input.new_info_name()

    if mic.startswith("*"):
        # Check if text was entered
        if mic_name.startswith("Enter"):
            ui.notification_show(
                "Please enter a name for the new microscope!", type="error"
            )
            return False, None, None, None
        # Check entry is not the same as in choices
        for m in microscope_list.get():
            # Remove special charactes an make it lower-case
            list_entry = "".join(s.lower() for s in m if s.isalnum())
            text_entry = "".join(s.lower() for s in mic_name if s.isalnum())
            if list_entry == text_entry:
                ui.notification_show(
                    f"The entered microscope name <{mic_name}> is too "
                    "similar existing entries. "
                    "Please double-check and change it.",
                    type="warning",
                )
                return False, None, None, None
        mic = input.new_mic_name()

    if obj.startswith("*"):
        if obj_name.startswith("Enter"):
            ui.notification_show(
                "Please enter a name for the new objective!", type="error"
            )
            return False, None, None, None
        # Check entry is not the same as in choices
        for o in objective_list.get():
            # Remove special charactes an make it lower-case
            list_entry = "".join(s.lower() for s in o if s.isalnum())
            text_entry = "".join(s.lower() for s in obj_name if s.isalnum())
            if list_entry == text_entry:
                ui.notification_show(
                    f"The entered objective name <{obj_name}> is too "
                    "similar existing entries. "
                    "Please double-check and change it.",
                    type="warning",
                )
                return False, None, None, None
        obj = input.new_obj_name()

    if info.startswith("*"):
        if info_name.startswith("Enter"):
            ui.notification_show(
                "Please enter a name for the new info!", type="error"
            )
            return False, None, None, None
        # Check entry is not the same as in choices
        for i in info_list.get():
            # Remove special charactes an make it lower-case
            list_entry = "".join(s.lower() for s in i if s.isalnum())
            text_entry = "".join(s.lower() for s in info_name if s.isalnum())
            if list_entry == text_entry:
                ui.notification_show(
                    f"The entered objective name <{info_name}> is too "
                    "similar existing entries. "
                    "Please double-check and change it.",
                    type="warning",
                )
                return False, None, None, None
        info = input.new_info_name()

    # Check if text was entered, but drop down was not set
    if not mic_name.startswith("Enter") and not mic.startswith("*"):
        ui.notification_show(
            "You entered a name for the microscope but forgot to select a new entry from the drop-down choices.",
            type="warning",
        )
        return False, None, None, None
    if not obj_name.startswith("Enter") and not obj.startswith("*"):
        ui.notification_show(
            "You entered a name for the objective but forgot to select a new entry from the drop-down choices.",
            type="warning",
        )
        return False, None, None, None
    if not info_name.startswith("Enter") and not info.startswith("*"):
        ui.notification_show(
            "You entered a info but forgot to select a new entry from the drop-down choices.",
            type="warning",
        )
        return False, None, None, None
    return True, mic, obj, info


def check_channel_names_provided(df: pd.DataFrame) -> bool:
    """
    Check if channel names were entered in a shiny table.

    Also checks:
        - if there are duplicate entries
        - check if the names correspond to the
          channel names of previous measurement entries

    :param df: pd.DataFrame with 2 columns: 'Channel' & '..names entered'.

    :return: bool, True if no empty str in cells.
    """
    # Sanity check
    if len(df.columns) != 2:
        raise RuntimeError(
            f"Expected a dataframe with 2 columns, got: {list(df.columns)}"
        )
    # Convert the columns into a dict {"C1": "name", ...}
    ch_dict = {}
    names = []
    for _i, row in df.iterrows():
        n = row[df.columns[-1]]
        ch_dict[row["Channel"]] = n
        names.append(n)

    # Check for entries in all cells        #########################
    for n in names:
        if n is None or n == "":
            ui.notification_show(
                "Please <Provide channel names> for all the channels!",
                type="error",
            )
            return False
    # Check for duplicate names             #########################
    ch_dict = check_duplicate_dict_values(ch_dict)
    if ch_dict is not None:
        ui.notification_show(
            f"You entered the same channel name: {ch_dict}.", type="error"
        )
        return False

    # Check with the data table itself      #########################
    # Filter the DF
    df = dataframe.get().copy()
    # Filter dataframe
    df = filter_by_column_value(df, "Site", input.site())
    df = filter_by_column_value(df, "Microscope", input.microscope())
    df = filter_by_column_value(df, "Objective", input.objective())
    # Get the unique channel names
    df_ch_names = list(np.unique(np.asarray(df["Channel"])))
    # No df ch names = new entry
    if len(df_ch_names) == 0:
        return True
    # Check for "wrong" entries: ch names not in df
    wrong_names = []
    for n in names:
        if n not in df_ch_names:
            wrong_names.append(n)
    if len(wrong_names) != 0:
        if len(names) > len(df_ch_names):
            # FIXME implement this??
            ui.notification_show(
                "Not supported: There are new channels, "
                "which have not been measured previously.",
                type="error",
            )
        else:
            ui.notification_show(
                f"You entered channel names ({wrong_names}), which are unknown. "
                f"Pleae use following ones: {df_ch_names}.",
                type="error",
            )
        return False
    return True


def match_fwhm_channel_names(
    ori_df: pd.DataFrame, name_df: pd.DataFrame
) -> dict:
    """
    Create a dict for upload by matchin entered names to OMERO channels.

    :param ori_df: pd.DataFrame, of the OMERO FWHM key values
        with columns: "Channel", "FWHM", "*Acquistion_date_number*"
    :param name_df: pd.DataFrame, of the manually entered channel names.
        with columns: "Channel", "Enter channel name"

    :returns: dict of dict, e.g.:
        {"DAPI" : {'FWHM-X': 911.0, 'FWHM-Y': 852.0, 'FWHM-Z': 1260.0}, ... }
    """
    result_dict = {}
    # should be: {"DAPI" : {'FWHM-X': 911.0, 'FWHM-Y': 852.0, 'FWHM-Z': 1260.0}, ... }

    for _i, row in ori_df.iterrows():
        ch = row["Channel"]  # e.g. C4
        name = name_df.loc[name_df["Channel"] == ch, name_df.columns[-1]].iloc[
            0
        ]
        if name in result_dict.keys():
            result_dict[name][row["FWHM"]] = row[ori_df.columns[-1]]
        else:
            result_dict[name] = {row["FWHM"]: row[ori_df.columns[-1]]}
    return result_dict


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


# Reactive functions    ------------------------------------------------------

# CSV upload        #######################################


@render_csv.set_patch_fn
def update_patch_csv_power(
    *,
    patch,
):
    """Allow only entries into the last column (csv upload table)."""
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
        # Convert the value to str, to avoid
        # "TypeError: Object of type int64 is not JSON serializable"
        return str(ori_value)

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
@reactive.event(input.csv_file_selector, input.category)
def parse_csv_power():
    """
    Convert the uploaded csv to a DataFrame.

    Currently hard-coded specifically for one type of laser power meausrement csv file.
    """
    # FIXME here: reset the csv_file_selector when switching between categories!

    csv: Optional[list[FileInfo]] = input.csv_file_selector()
    if csv is None:
        return pd.DataFrame()

    # Get the csv path (from the list of dicts in csv)
    path = csv[0]["datapath"]

    # FIXME should have this function throwing an error if csv not compatible
    # FIXME     catch the error here to return an empty dataframe
    delimiter, first_line, wavelength = identify_csv(path)

    df = pd.read_csv(path, sep=delimiter, header=first_line)
    # Remove "unnamed columns"
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


@reactive.effect
@reactive.event(input.upload_power_button)
def upload_power_data():
    """
    Perform checks before uploading the csv (power) data.

    FIXME: Currently only for Power measurements,
           this button is currently also "specific" for this...
    """
    # Prevent upload for working with local file    #######
    if sheet_reference.get() is None:
        ui.notification_show(
            "Can't uplaod data when working with local file", type="error"
        )
        return

    # Check microscope entries      #######################
    valid_entries, cur_mic, cur_obj, cur_info = check_new_microscope_entries()
    if not valid_entries:
        return

    # Check if there is data for upload     ###############
    data = render_csv.data_view()
    if data is None or data.empty:
        ui.notification_show("No data for upload yet!", type="warning")
        return

    # FIXME temp usage of unused variables
    a = [cur_mic, cur_obj, cur_info]
    a.sort()

    # TODO: Check if all values have been provided

    print("All good so far")


# OMERO upload      #######################################
@reactive.effect
@reactive.event(input.upload_omero_button)
def uplaod_omero_data():
    """
    Peform checks then upload omero data.

    FIXME: Currently for FWHM.
    """
    # Prevent upload for working with local file    #######
    if sheet_reference.get() is None:
        ui.notification_show(
            "Can't uplaod data when working with local file", type="error"
        )
        return

    # Check microscope entries      #######################
    valid_entries, cur_mic, cur_obj, cur_info = check_new_microscope_entries()
    if not valid_entries:
        return

    # Check if there is data for upload     ###############
    data = omero_data.data()
    ch_names = omero_channel_names.data_view()  # get the user modified df
    if data is None or data.empty:
        ui.notification_show("No data for uplaod yet!", type="warning")
        return

    # Check if all channel names were provided correctly ##
    if not check_channel_names_provided(ch_names):
        return

    # Check the upload password     #######################
    if not check_upload_password(input.upload_pwd()):
        ui.notification_show(
            "Please provide the correct <Password for upload>!", type="error"
        )
        return

    # Upload the data
    # FIXME shift Reference-XYZ -> should it be 0 or nan? -> PSFdata object
    #       how does it visualise once the visualisation is implemented?
    try:
        make_sheet_entries(
            sheet=sheet_reference.get(),
            site=input.site(),
            microscope=cur_mic,
            objective=cur_obj,
            info=cur_info,
            date=data.columns[-1],
            fwhm_data=match_fwhm_channel_names(data, ch_names),
        )
        ui.notification_show("Successfully uploaded the data!", type="message")
    except Exception as err:
        ui.notification_show(
            f"Could not upload the data:\n{err}", type="error"
        )
    # FIXME test notification
    # ui.notification_show("default", type="default") # white
    # ui.notification_show("error", type="error") # red
    # ui.notification_show("message", type="message") # blue
    # ui.notification_show("warning", type="warning") # yellow


@omero_channel_names.set_patch_fn
def update_patch_omero(
    *,
    patch,
):
    """Allow only changing of the last column (OMERO channe name entry)."""
    data = omero_channel_names.data()
    row = patch["row_index"]
    col = patch["column_index"]
    old_value = data.iloc[row, col]
    new_value = patch["value"]

    # Only last row can be edited!
    if col != len(data.columns) - 1:
        ui.notification_show(
            f"You can only edit values in the column: {data.columns[-1]}",
            type="warning",
        )
        return old_value
    else:
        return new_value


@reactive.calc
def parse_omero_fwhm():
    """
    Create a table from OMERO FWHM data.

    reactive.calc function cannot take any parameters.

    :return: None for errors (shown as notification), else pd.DataFrame
    """
    omero_id = input.omero_id_selector()
    # If nothing entered yet, do not do anything
    if omero_id.startswith("Enter OMERO ID") or omero_id == "":
        return None
    # Parse OMERO ID
    try:
        omero_id = int(input.omero_id_selector())
    except ValueError:
        ui.notification_show(
            f"Could not parse OMERO ID: {omero_id}", type="error"
        )
        return None
    # Get the data from OMERO
    try:
        data = omero_operation(
            operation=None,
            omero_type=input.omero_type_selector(),
            omero_id=omero_id,
            metric_id="FWHM",
        )
    except Exception as err:
        ui.notification_show(str(err), type="error")
        return None
    # Manage the PSF data
    data = PSFData(data)
    # Create a table for FWHM entries
    psf_table = []
    for k, v in invert_nested_dict(data.get_fwhm_data()).items():
        entry = v.copy()
        entry.append(k)
        psf_table.append(entry)
    psf_table = pd.DataFrame(
        psf_table, columns=["Channel", "FWHM", data.get_acquisition_date()]
    )
    # Create tale for shift between channel entreis
    if len(data.get_shift_data()) != 0:
        shift_table_part = []
        for k, v in invert_nested_dict(data.get_shift_data()).items():
            entry = v.copy()
            entry.append(k)
            shift_table_part.append(entry)
        shift_table_part = pd.DataFrame(
            shift_table_part,
            columns=["Channel", "FWHM", data.get_acquisition_date()],
        )
        psf_table = pd.concat([psf_table, shift_table_part])
    return psf_table


# Microscope selection      ###############################
@reactive.effect
@reactive.event(input.category)
def get_data():
    """Get the worksheet data from the sheet."""
    wsheet, df = get_sheet(
        sheet_doc, input.category(), dev_local_file=use_dev_local_file
    )
    sheet_reference.set(wsheet)
    dataframe.set(df)


@reactive.effect
@reactive.event(dataframe)
def get_sites():
    """Update site selection when dataframe changes."""
    df = dataframe.get().copy()
    if df is None or df.empty:
        print("df is none or empty")
        return
    # Get unique sites and remove "" entries
    sites_ = list(np.unique(np.asarray(df["Site"])))
    sites = [s for s in sites_ if s != ""]
    if len(sites) == 0:
        raise RuntimeError("There are no site in the table!")
    ui.update_select("site", choices=sites, selected=sites[0])


@reactive.effect
@reactive.event(dataframe, input.site)
def update_mic_selection():
    """Update microscope selection."""
    df = dataframe.get().copy()
    # Filter dataframe
    df = filter_by_column_value(df, "Site", input.site())
    # Update selection choices
    mics = list(np.unique(np.asarray(df["Microscope"])))
    mics.append("* New microscope *")
    microscope_list.set(mics)
    ui.update_select("microscope", choices=microscope_list.get())


@reactive.effect
@reactive.event(dataframe, input.site, input.microscope)
def update_objectives_selection():
    """Update objective selection."""
    df = dataframe.get().copy()
    # Filter dataframe
    df = filter_by_column_value(df, "Site", input.site())
    df = filter_by_column_value(df, "Microscope", input.microscope())
    # Update selection choices
    objs = list(np.unique(np.asarray(df["Objective"])))
    objs.append("* New objective *")
    objective_list.set(objs)
    ui.update_select("objective", choices=objective_list.get())


@reactive.effect
@reactive.event(dataframe, input.site, input.microscope, input.objective)
def update_info_selection():
    """Update info selection."""
    df = dataframe.get().copy()
    # Filter dataframe
    df = filter_by_column_value(df, "Site", input.site())
    df = filter_by_column_value(df, "Microscope", input.microscope())
    df = filter_by_column_value(df, "Objective", input.objective())
    # Update selection choices
    infos = list(np.unique(np.asarray(df["Info"])))
    infos.append("* New info *")
    info_list.set(infos)
    ui.update_select("info", choices=info_list.get())
