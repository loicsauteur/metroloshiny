from typing import TYPE_CHECKING, Optional

import numpy as np
import pandas as pd
from shiny import reactive
from shiny.express import input, render, ui

if TYPE_CHECKING:
    from shiny.types import FileInfo

from metroloshiny.data_objects.PSFData import PSFData
from metroloshiny.utils.common_utils import (
    check_if_date,
    get_today,
    get_version,
    list_duplicates,
    set_local_file,
)
from metroloshiny.utils.dataframe_utils import (
    filter_by_column_value,
)
from metroloshiny.utils.omero_utils import (
    get_image_voxelsize_channel_names,
    get_images_for_metric,
    get_omero_dates,
)
from metroloshiny.utils.read_csv import get_power_measurement
from metroloshiny.utils.read_file import (
    check_upload_password,
    get_sheet,
    load_doc,
)
from metroloshiny.utils.write_gspread import (
    make_entries,
    prepare_data_for_entry,
)

# Load Data
use_dev_local_file = set_local_file()
sheet_doc = load_doc(dev_local_file=use_dev_local_file)
# wsheet_psf, df = get_sheet(sheet_doc, "PSF", dev_local_file=use_dev_local_file)

# TODO: maybe OMERO metrics via tags?
#   TODO: PSF/bead images have tags = beads, psf
#   TODO: Argolight images have tags = fwhm, argolight

# Reactive values       ------------------------------------------------------
sheet_reference = reactive.value(None)
dataframe = reactive.value(None)
category_list = ["Power", "PSF", "Uniformity/Distortion"]
site_list = reactive.value([])
microscope_list = reactive.value([])
objective_list = reactive.value([])
info_list = reactive.value([])

# Build the GUI     items       ----------------------------------------------
ui.page_opts(title="Metrology Upload", footer=f"Version {get_version()}")
with ui.nav_panel(title="Data Upload"):
    # Sidebar
    with ui.layout_sidebar():
        # Sidebar   ----------------------------------------------------------
        with ui.sidebar():

            @render.ui
            def add_sidebar_elements():
                """Add sidebar elements."""
                return category, site, new_site, upload_pwd

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
                        """Render microscope drop-down entry selections."""
                        return microscope, objective, info

                    # Column 2 for "new" text entries
                    @render.ui
                    def mic_col_2():
                        """Render microscope free-text elements."""
                        return new_mic_name, new_obj_name, new_info_name

        # Upload Info   ------------------------------------------------------
        with ui.navset_card_underline():
            # Upload from OMERO     ------------------------------------------
            with ui.nav_panel(title="Upload from OMERO"):

                @render.ui
                def render_omero_upload():
                    """Show OMERO input selectors only on PSF category."""
                    message = warn_omero()
                    if message != "":
                        return message
                    # For any category that doesn't give a warn_omero msg
                    return dataset_id_selector, image_id_selector

                @render.ui
                def update_omero_selections():
                    """Handle OMERO dataset ID and image ID."""
                    # Check dataset ID input
                    _out = (
                        check_dataset_id()
                    )  # Optional[(dict[id:name], dict[id:DF])]
                    # Check current image ID selection
                    msg = give_image_selection_info()
                    return msg

                # Add a spacing
                ui.div(style="margin-top: 20px;")

                # Add the date override selection
                @render.ui
                def date_override_option():
                    """Render alternative date selection."""
                    # Only render the date selection on PSF category
                    if warn_omero() != "":
                        return ""
                    return override_date_omero

                # Add a spacing
                ui.div(style="margin-top: 20px;")

                @render.ui
                def add_omero_note():
                    """Render note to check table."""
                    if create_omero_table().empty:
                        return ""
                    else:
                        note = ui.markdown(
                            """Please **check and edit** the highlighted cells:"""
                        )
                        return note

                # Add datatable
                @render.data_frame
                def omero_data():
                    """Get and show the dataframe."""
                    df = create_omero_table()
                    styles = create_omero_table_style()
                    return render.DataGrid(df, editable=True, styles=styles)

                @render.ui
                def render_omero_upload_btn():
                    """Render OMERO upload button & data check checkbox."""
                    # Only show items if there is a table
                    if omero_data.data().empty:
                        return ""
                    return omero_table_checked, omero_upload_btn

            # Upload from CSV       ------------------------------------------
            with ui.nav_panel(title="Upload from CSV"):

                @render.ui
                def render_csv_file_selector():
                    """Show CSV input selectors only on Power category."""
                    message = warn_csv()
                    if message != "":
                        return message
                    # For "all" implemented csv upload categories
                    return csv_file_selector

                @render.ui
                def render_csv_ui_elements():
                    """Show additional elements for the csv upload."""
                    # Specific for Power category
                    if input.category() == "Power":
                        file_name_info = (
                            f"Currently loaded file: {get_csv_file_name()}"
                        )
                        # Selectors for: file name info, light source, date, & objective from dataframe
                        return (
                            file_name_info,
                            ui.div(style="margin-top: 20px;"),
                            csv_light_selector,
                            override_date_csv,
                            csv_power_objective_selection,
                        )

                # Add a spacing
                ui.div(style="margin-top: 20px;")

                @render.data_frame
                def csv_data():
                    """Load and show the csv dataframe."""
                    df = create_csv_table()
                    styles = create_csv_table_style()
                    # Maybe a good warning
                    if not df.empty:
                        file_id, _ = load_csv_data()
                        if file_id == "thorlabs":
                            ui.notification_show(
                                "Enter values in table after adjusting everything else! Entries will be reverted.",
                                id="make_entries_last",
                            )
                    return render.DataGrid(df, editable=True, styles=styles)

                @render.ui
                def render_csv_upload_btn():
                    """Render CSV upload button & data check checkbox."""
                    # Only show items if there is a table
                    if csv_data.data().empty:
                        return ""
                    return csv_table_checked, csv_upload_btn


# Table edit & style functions  ----------------------------------------------


@reactive.calc
def create_csv_table_style() -> Optional[list[dict]]:
    """
    Create styles for highlighting cells in a DataGrid.

    This is depending on the category.

    :return: Optional, list[dict]
    """
    # Get csv dataframe (not the shown data since it may not be there yet)
    df = create_csv_table()
    # If there is none, return None
    if df.empty:
        return None

    # Get also the csv file identity
    file_id, _ = load_csv_data()
    if input.category() == "Power":
        style = []  # init list of style dict
        # Highlight columns that need to be specified
        for i in range(len(list(df.columns[:4]))):
            col = df.columns[i]
            if df[col].astype(str).str.startswith("Please", na=False).any():
                style.append(
                    {
                        "cols": [i],
                        "style": {"background-color": "yellow"},
                    }
                )

        # Highlight cells that requires input (for thorlabs files)
        if file_id == "thorlabs":
            # Highlight the column 5
            # Unfortunately can't check dynamically if values were changed
            style.append(
                {
                    # No 'row' = all rows
                    "cols": [5],
                    "style": {
                        "background-color": "yellow",
                        "font-weight": "bold",
                    },
                }
            )
        # Highlight light source col if not specified (cannot highlight the header...)
        if df.columns[4].startswith("Please specify"):
            style.append(
                {
                    "cols": [4],
                    "style": {"background-color": "yellow"},
                }
            )
        return style if len(style) > 0 else None
    else:
        # TODO implement for other categories
        return None  # Currently return None


@csv_data.set_patches_fn
def update_csv_table(
    *, patches: list[render.CellPatch]
) -> list[render.CellPatch]:
    """
    Specify how chells in the csv table change.

    Depends on the category and kind of loaded csv file.

    :param patches: list[render.CellPatch]

    :return: list[render.CellPatch]
    """
    # Reset the check-box for csv data check
    ui.update_checkbox("csv_table_checked", value=False)

    # Get the (initially) shown data
    df = csv_data.data()
    # Create a list of unmodified patches (to reset illegal entries)
    ori_patches = []
    for p in patches:
        row = p["row_index"]
        col = p["column_index"]
        ori_val = df.iloc[row, col]
        # Convert numpy number types to conventional types
        #   to avoid TypeError: Object of type int64 is not JSON serializable
        if isinstance(ori_val, np.int64):
            ori_val = int(ori_val)
        if isinstance(ori_val, np.float64):
            ori_val = float(ori_val)
        ori_patches.append(
            render.CellPatch(row_index=row, column_index=col, value=ori_val)
        )

    # Do not allow multi-cell value changes (copy paste)
    if len(patches) > 1:
        ui.notification_show(
            "You cannot multiple values at once.",
            type="warning",
        )
        return ori_patches

    # Check the only patch
    row = patches[0]["row_index"]
    col = patches[0]["column_index"]
    val = patches[0]["value"]

    # Handle cell value changes according to category
    if input.category() == "Power":
        # Identify the kind of file that was loaded
        file_id, _ = load_csv_data()
        if file_id == "thorlabs":
            # Allow changes in second last col (Power)
            # Sanity check
            if df.columns[5] != "Power [%]":
                raise RuntimeError(
                    "Expected the 6th column to be 'Power [%]' "
                    f"but was: <{df.columns[5]}>",
                )

            # Allow changes only in column 4 (=Power [%])
            if col != 5:
                ui.notification_show(
                    "You can only change channel names in the 'Power [%]' column.",
                    type="warning",
                )
                return ori_patches
            # Allow only int entries
            try:
                val = int(val)
                # And only valid percentages
                if val < 1 or val > 100:
                    ui.notification_show(
                        "Values must be between 0-101!", type="warning"
                    )
                    return ori_patches
                # However, dataframe entries MUST be str
                return [
                    render.CellPatch(
                        row_index=row, column_index=col, value=str(val)
                    )
                ]
            except ValueError:
                ui.notification_show(
                    "Only integer entries allowed!", type="warning"
                )
                return ori_patches
        else:
            # e.g. "nis_job", or not yet implemented file_id's
            ui.notification_show(
                "You cannot change any values.",
                type="warning",
            )
            return ori_patches

    # TODO implement for other cases/categoreies
    else:
        # Do not allow any changes
        ui.notification_show(
            "You cannot change any values.",
            type="warning",
        )
        return ori_patches


@omero_data.set_patches_fn
def update_patches_omero(
    *, patches: list[render.CellPatch]
) -> list[render.CellPatch]:
    """
    Specify how cells in the OMERO table change.

    Only supports single patch input (e.g. pasting multiple cells is not supported).
    Allowed changes are dependent on the input.category.

    :param patches: list[render.CellPatch]

    :return: list[render.CellPatch]
    """
    # Reset the "OMERO data checked" checkbox
    ui.update_checkbox("omero_table_checked", value=False)

    df = omero_data.data()
    # Create a list of original patches
    ori_patches = []
    for p in patches:
        row = p["row_index"]
        col = p["column_index"]
        ori_val = df.iloc[row, col]
        # Convert numpy number types to conventional types
        #   to avoid TypeError: Object of type int64 is not JSON serializable
        if isinstance(ori_val, np.int64):
            ori_val = int(ori_val)
        if isinstance(ori_val, np.float64):
            ori_val = float(ori_val)
        ori_patches.append(
            render.CellPatch(row_index=row, column_index=col, value=ori_val)
        )

    # Implement only single cell value changes
    if len(patches) > 1:
        ui.notification_show(
            "Modification of multiple cells at once is not supported.",
            type="error",
        )
        return ori_patches

    # Specific actions for PSF data only
    if input.category() in ["PSF", "Uniformity/Distortion"]:
        # Check the only patch
        row = patches[0]["row_index"]
        col = patches[0]["column_index"]
        val = patches[0]["value"]

        # Allow changes in the Channel column
        try:
            # Get the "Channel" column index
            col_ch = df.columns.get_loc("Channel")
        except KeyError:
            # KeyError if "Channel" in columns
            col_ch = None

        # Allow changes only in the "Channel" column
        if col != col_ch:
            ui.notification_show(
                "You can only change channel names in the 'Channel' column.",
                type="warning",
            )
            return ori_patches

        # Get a list of patches for the same channel names
        ori_channel_name = df.iloc[row, col]
        out_patches = []
        for idx, r in df.iterrows():
            if r["Channel"] == ori_channel_name:
                out_patches.append(
                    render.CellPatch(
                        row_index=idx, column_index=col, value=val
                    )
                )
        return out_patches
    else:
        # TODO implement also for other categories?
        return ori_patches  # Currently just return the original patches


@reactive.calc
def create_omero_table_style() -> Optional[list[dict]]:
    """
    Create styles for highlighting cells in a DataGrid.

    This is depending on the category.

    :return: Optional, list[dict]
    """
    # Get omero dataframe (not the shown data since it may not be there yet)
    df = create_omero_table()
    # If there is none, return None
    if df.empty:
        return None

    style = []  # Init list of style dicts
    # Highlight columns that need to be specified (cells starting with 'Please')
    for i in range(len(list(df.columns[:4]))):
        col = df.columns[i]
        if df[col].astype(str).str.startswith("Please", na=False).any():
            style.append(
                {
                    "cols": [i],
                    "style": {"background-color": "yellow"},
                }
            )

    # Highlight the "Channel" column
    if input.category() in ["PSF", "Uniformity/Distortion"]:
        style.append(
            {
                # No 'row' = all rows
                "cols": [df.columns.get_loc("Channel")],
                "style": {"background-color": "yellow", "font-weight": "bold"},
            }
        )
    else:
        # TODO implement for other categories
        return None  # Currently return None
    # Finally return the style
    return style


# Reactive functions    ------------------------------------------------------


@reactive.calc
def load_csv_data() -> tuple[str, pd.DataFrame]:
    """
    Load and try parse a csv file.

    Parsing is category dependent
    :return: tuple[str, pd.DataFrame]
        - str, file type output identifier
            - "nis_job" for Tom's file
            - "thorlabs" for Simone's file
            - TODO others to be implemented
        - DataFrame for Power measurements: columns = ? Line [nm] ?|Power [%]|'Date'
            - For Tom's file there is an additional column "Objective" at the beginning
    """
    # Reset the "CSV data checked" checkbox
    ui.update_checkbox("csv_table_checked", value=False)

    # Init dataframe place holder and file_id str (source of the read dataframe)
    df = pd.DataFrame()
    file_id = ""

    # Get file reference
    csv: Optional[list[FileInfo]] = input.csv_file_selector()
    if csv is None:
        return file_id, df

    # Get the csv path (from the list of dicts in csv)
    path = csv[0]["datapath"]

    # Handle data according to the upload category
    if input.category() == "Power":
        try:
            file_id, df = get_power_measurement(path)
        except Exception as err:
            ui.notification_show(f"Could not read file: {err}", type="error")
    else:
        # TODO implement also other categories
        # Currently give only a warning
        ui.notification_show(
            f"CSV upload for {input.category()} is not implemented!",
            type="error",
        )
    return file_id, df


@reactive.calc
def cpt_select_objective() -> pd.DataFrame:
    """
    First part to create the power measurement data part of the table.

    cpt = create_power_table
    Check if the dataframe contains measurements for multiple objectes &
    selects only one

    1. element in chained reactive calcs
    """
    # Load the raw csv dataframe
    _, _df = load_csv_data()
    df = _df.copy()
    if df.empty:
        return pd.DataFrame()

    # Filter the dataframe according to the csv objective selection
    cur_objective = input.csv_power_objective_selection()
    if "Objective" in df.columns:
        df = filter_by_column_value(df, "Objective", cur_objective)
        # Drop also NaN columns (-> axis=1)
        df = df.dropna(axis=1)

    return df


@reactive.calc
def cpt_check_date() -> pd.DataFrame:
    """
    Check if there is a measurement date available.

    cpt = create_power_table
    If not get today and set it for the override date.

    2. element in chained reactive calcs
    """
    df = cpt_select_objective()
    if df.empty:
        return pd.DataFrame()
    # Check if date is known and update the override date
    date_df = df.columns[-1]
    msg = "The measurement date could not be identified and was set to today!"
    if not check_if_date(date_df):
        # Warn - only show one notification (with param id)
        ui.notification_show(msg, id="date_is_today", type="error")
        date_df = get_today()
    ui.update_date("override_date_csv", value=date_df)

    return df


@reactive.calc
def create_power_table() -> pd.DataFrame:
    """
    Set the table headers for the light source.

    cpt = create_power_table
    Also renames the last column to "Value" instead of the date.

    3. element in chained reactive calcs -> the function to be called
    """
    df = cpt_check_date()
    if df.empty:
        return pd.DataFrame()

    # TODO maybe FIXME: if line change after entries in power: then entries are reset (because I dont get the csv_data.patched())

    headers = list(df.columns)
    light_source = input.csv_light_selector()
    if light_source.startswith("Please ch"):
        headers[0] = "Please specify light source"
    elif light_source == "Laser":
        headers[0] = "Laser Line [nm]"
    else:
        headers[0] = "LED Line [nm]"

    # Set the headers (& rename the date column)
    _df = df.copy()  # Copying is important!
    headers[-1] = "Value"
    _df.columns = headers
    return _df


@reactive.calc
def create_csv_table() -> pd.DataFrame:
    """Create the csv data table for display."""
    # Get the raw data table. Loading the csv is the first step
    _, df = load_csv_data()

    # Reset the csv data checked checkbox
    ui.update_checkbox("csv_table_checked", value=False)

    # For power measurements
    if input.category() == "Power":
        _date = input.override_date_csv()

        # Create the power table (chain multiple reactive calcs to create it)
        df = create_power_table()

        # Only continue if the dataframe has data
        if df.empty:
            return pd.DataFrame()

        # Create the DataFrame with the common columns
        _site, _mic, _obj, _info = get_common_column_values()
        df = prepare_data_for_entry(
            data=df,
            data_headers=list(df.columns[:-1]),
            site=_site,
            microscope=_mic,
            objective=_obj,
            info=_info,
            # Date column should be "Value", this function sets the date into the df
            date=_date.strftime("%Y%m%d"),
        )
        return df

    else:
        # TODO implement also for other categories
        # Currently return empty dataframe
        return pd.DataFrame()


@reactive.effect
def update_csv_objective_choices():
    """
    Update the objecive choices from the csv file.

    The effect seems/will execute on load_csv_data.

    For power measurements read from Tom's xlsx file,
    update the objective from "csv" file selection.
    """
    # Get the csv data
    file_id, df = load_csv_data()
    # Actions on "nis_job" dataframes (multi-objective)
    if file_id == "nis_job":
        # Get a list of unique objectives
        csv_objectives = list(np.unique(np.asarray(df["Objective"])))
        csv_objectives.insert(0, "Please choose an objective measurement")
        # Update the choices for multi objective tables
        # If only one objective available, selected it
        if len(csv_objectives) == 2:
            ui.update_select(
                "csv_power_objective_selection",
                choices=csv_objectives,
                selected=csv_objectives[-1],
            )
        else:
            # More than one objective: user has to actively select one
            ui.update_select(
                "csv_power_objective_selection",
                choices=csv_objectives,
                selected=csv_objectives[0],
            )
    # Reset choices to "n/a" for non-"nis_job" csv's
    else:
        ui.update_select(
            "csv_power_objective_selection", choices=["No selection available"]
        )


@reactive.calc
def get_csv_file_name() -> str:
    """Return the loaded csv file name."""
    if not input.csv_file_selector():
        return "No file loaded"
    return input.csv_file_selector()[0]["name"]


@reactive.effect
@reactive.event(input.csv_upload_btn)
def upload_csv_data():
    """
    Check, then upload the CSV data.

    Performs the check and upload based on input.category.
    """
    # Prevent upload when working with local file
    if sheet_reference.get() is None:
        ui.notification_show(
            "Can't upload data when working with local file", type="error"
        )
        return

    # Get the patched data
    df = csv_data.data_patched()
    # Sanity check
    if df.empty:
        # This should not happen as the upload button is only shown when there is a table
        raise RuntimeError("There is no patched table data for upload")

    # Category based upload
    if input.category() == "Power":
        # Ensure that the common columns have valid values  ##################
        common_df = df[df.columns[0:4]]
        faulty_cols = common_df.columns[
            common_df.astype(str).apply(
                lambda col: col.str.startswith("Please", na=False).any()
            )
        ].tolist()
        if len(faulty_cols) > 0:
            ui.notification_show(
                f"Please make sure to define {' & '.join(faulty_cols)}!",
                type="error",
            )
            return

        # Check if light source has been specified      ######################
        if df.columns[4].startswith("Please"):
            ui.notification_show(
                "Please select the light source kind.", type="error"
            )
            return
        # Check if data has been entered (for thorlabs files)       ##########
        file_id, _ = load_csv_data()
        if file_id == "thorlabs":
            if df["Power [%]"].str.startswith("Sample").any():
                ui.notification_show(
                    "Please provide the Power percentage for all rows!",
                    type="error",
                )
                return
            # Check if percentage entries are correct
            if not check_power_prct_entries(df):
                return
        # Is the checkbox checked               ##############################
        if not input.csv_table_checked():
            ui.notification_show(
                "Please check the inputs of any of highlighted cells. "
                "Then check the checkbox above the upload button!",
                type="error",
            )
            return
        # Check the upload password                  #########################
        pwd = input.upload_pwd()
        if pwd == "" or not check_upload_password(pwd):
            ui.notification_show(
                "Please provide the correct password for upload!", type="error"
            )
            return

        # Convert the Power [%] column type to int64 (as it may be string)
        upload_df = df.copy()
        upload_df["Power [%]"] = upload_df["Power [%]"].astype(np.int64)

        # Upload                                    ##########################
        try:
            make_entries(sheet=sheet_reference.get(), data=upload_df)
            ui.notification_show(
                "Successfully uploaded the data!", type="message"
            )
        except Exception as err:
            ui.notification_show(f"Upload error:\n{err!s}", type="error")

    else:
        raise RuntimeError(
            f"Upload for {input.category()} is not implemented!"
        )
    return


@reactive.effect
@reactive.event(input.omero_upload_btn)
def upload_omero_data():
    """
    Check, then upload the OMERO data.

    Performs the check and upload based on input.category.
    """
    # Prevent upload when working with local file            ##################
    if sheet_reference.get() is None:
        ui.notification_show(
            "Can't upload data when working with local file", type="error"
        )
        return

    # Get the patched data
    # ori_data = omero_data.data()  # un-patched dataframe
    # view_data = omero_data.data_view()  # patched and user-sorted dataframe
    df = omero_data.data_patched()  # patched dataframe
    # Sanity check
    if df.empty:
        # This should not happen as the upload button is only shown when there is a table
        raise RuntimeError("There is no patched table data for upload")

    # For PSF & Uniformity upload
    if input.category() in ["PSF", "Uniformity/Distortion"]:
        # Ensure that the common columns have valid values  ##################
        common_df = df[df.columns[0:4]]
        faulty_cols = common_df.columns[
            common_df.astype(str).apply(
                lambda col: col.str.startswith("Please", na=False).any()
            )
        ].tolist()
        if len(faulty_cols) > 0:
            ui.notification_show(
                f"Please make sure to define {' & '.join(faulty_cols)}!",
                type="error",
            )
            return

        # Check the provided channel names (are they in the list)
        if not check_channel_names_provided(df=df):
            return

        # Check box checked?                         #########################
        ckb = input.omero_table_checked()
        if not ckb:
            ui.notification_show(
                "Please check the inputs of any of highlighted cells."
                "Then check the checkbox above the upload button!",
                type="error",
            )
            return

        # Check the upload password                  #########################
        pwd = input.upload_pwd()
        if pwd == "" or not check_upload_password(pwd):
            ui.notification_show(
                "Please provide the correct password for upload!", type="error"
            )
            return

        # Upload                                    ##########################
        try:
            make_entries(sheet=sheet_reference.get(), data=df)
            ui.notification_show(
                "Successfully uploaded the data!", type="message"
            )
        except Exception as err:
            ui.notification_show(f"Upload error:\n{err!s}", type="error")

    else:
        raise RuntimeError(
            f"Upload for {input.category()} is not implemented!"
        )


@reactive.calc
def create_uniformity_omero_dataframe() -> pd.DataFrame:
    """Create dataframe part for field distortion/uniformity."""
    # Get the dataframe associated with the image ID
    cur_id = input.image_id_selector()
    the_check = check_dataset_id()
    if the_check is None:
        return pd.DataFrame()
    # Get the channel names
    _, ch_names = get_image_voxelsize_channel_names(int(cur_id))
    # Get the acquisition date!
    acqui_date, import_date = get_omero_dates(int(cur_id))
    if acqui_date is None:
        ui.notification_show(
            "Could not identify the data acquisition date! Set to OMERO import date!",
            type="warning",
            duration=10,
        )
        acqui_date = import_date
    # Update the date override selector
    ui.update_date("override_date_omero", value=acqui_date)

    # create date frame (very simple, only "Channel" & "Date" columns)
    df = {
        "Channel": ch_names,
        # Include the omero-channel names, as this may be lost # FIXME check how omero table looks like for ND2 file (i.e. ch0 = ???)
        "Value": [f"omero{cur_id}_ch-{ch}" for ch in ch_names],
    }
    return pd.DataFrame().from_dict(df)


@reactive.calc
def create_pfs_dataframe() -> pd.DataFrame:
    """Load and calibrate the PSF data."""
    # Get the dataframe associated with the image ID
    cur_id = input.image_id_selector()
    the_check = check_dataset_id()
    if the_check is None:
        return pd.DataFrame()
    _, id_metric_df = the_check
    df = id_metric_df.get(int(cur_id))

    # Get voxel calibration and channel names
    voxel_size, ch_names = get_image_voxelsize_channel_names(int(cur_id))

    # Create the dataframe from PSFData object
    psfdata = PSFData.from_dataframe(df)
    psfdata.inject_channel_names(ch_names)
    psfdata.inject_voxel_size(voxel_size)
    fwhm = psfdata.get_fwhm_dataframe()
    shift = psfdata.get_shift_dataframe()
    df = pd.concat([fwhm, shift])
    # Change the "Value" column to the date
    acquisition_date = psfdata.get_acquisition_date()
    if acquisition_date is None:
        # FIXME could get the import date instead??
        acquisition_date = get_today()
        ui.notification_show(
            "Could not identify the data acquisition date! Set to today!",
            type="warning",
            duration=10,
        )
    # Update the date override selector
    ui.update_date("override_date_omero", value=acquisition_date)
    return df


@reactive.calc
def get_common_column_values() -> tuple[str, str, str, str]:
    """
    Get the values for the common columns.

    Shows warnings if something is wrong.

    :return: tuple[4xstr]:
        - site name
        - microscope name
        - objective name
        - info text
    """
    # Get the variables to be checked
    cur_site = input.site()
    cur_mic = input.microscope()
    cur_obj = input.objective()
    cur_info = input.info()
    site_name = input.new_site()
    mic_name = input.new_mic_name()
    obj_name = input.new_obj_name()
    info_name = input.new_info_name()

    # Check new site            ################################
    site_name = check_new_text_entry(
        cur_sel=cur_site,
        cur_entry=site_name,
        existing=site_list.get(),
        id="site",
    )
    # Check new microscope      ################################
    mic_name = check_new_text_entry(
        cur_sel=cur_mic,
        cur_entry=mic_name,
        existing=microscope_list.get(),
        id="microscope",
    )
    # Check new objective       ################################
    obj_name = check_new_text_entry(
        cur_sel=cur_obj,
        cur_entry=obj_name,
        existing=objective_list.get(),
        id="objective",
    )
    # Check new info            ################################
    info_name = check_new_text_entry(
        cur_sel=cur_info,
        cur_entry=info_name,
        existing=info_list.get(),
        id="info",
    )
    # Return variables
    return site_name, mic_name, obj_name, info_name


@reactive.calc
def create_omero_table() -> pd.DataFrame:
    """
    Return the dataframe of the selected Image ID.

    Adjusts the dataframe according to the upload category.
    """
    # Reset the "OMERO data checked" checkbox
    ui.update_checkbox("omero_table_checked", value=False)
    # Init dataframe place holder
    df = pd.DataFrame()
    cur_id = input.image_id_selector()
    if cur_id.startswith("No images "):
        return df

    # Handle data according to the upload category
    if input.category() == "PSF":
        # Create the dataframe from the OMERO values
        df = create_pfs_dataframe()
    elif input.category() == "Uniformity/Distortion":
        # Create the dataframe from the OMERO values
        df = create_uniformity_omero_dataframe()
    else:
        # TODO implement also other categories
        pass

    # Create full dataframe: common columns + data columns      ##############
    # If df.empty, then wrong inputs -> return empty df
    if df.empty:
        return pd.DataFrame()
    override_date_omero = input.override_date_omero()

    # Get the values for the common columns
    _site, _mic, _obj, _info = get_common_column_values()
    # Create the dataframe to be uploaded
    df = prepare_data_for_entry(
        data=df,
        # Exclude the last column (Value) for data_headers
        data_headers=list(df.columns)[:-1],
        site=_site,
        microscope=_mic,
        objective=_obj,
        info=_info,
        date=override_date_omero.strftime("%Y%m%d"),
    )
    return df


@reactive.calc
def give_image_selection_info() -> str:
    """Return the selected image name."""
    cur_id = input.image_id_selector()
    if cur_id.startswith("No images "):
        return ""
    the_check = check_dataset_id()
    if the_check is None:
        return ""
    # Otherwise get the image name
    id_name_dict, _ = the_check
    image_name = id_name_dict.get(int(cur_id))
    image_name = image_name.replace(f"{cur_id}: ", "")
    return str(image_name)


@reactive.calc
def check_dataset_id() -> Optional[tuple[dict, dict]]:
    """
    Check entered dataset ID.

    Updates the "Available images" selection.
    Returns None if there wrong input or no images with metrics.

    :return: dict, "image ID":image name
    :return: dict, "image ID":metrics-dataframe
    """
    # Reset the "OMERO data checked" checkbox
    ui.update_checkbox("omero_table_checked", value=False)
    # Do not do anything if wrong category selected
    if warn_omero() != "":
        return None

    dataset_id = input.dataset_id_selector()
    # Check if the str is unchanged
    if dataset_id.startswith("Please enter") or dataset_id == "":
        ui.update_select("image_id_selector", choices=["No images available"])
        return None
    # Is the ID a number
    try:
        dataset_id = int(dataset_id)
    except Exception:
        ui.notification_show(
            f"<{dataset_id}> is not a valid number.", type="error"
        )
        ui.update_select("image_id_selector", choices=["No images available"])
        return None

    else:
        cat = input.category()
        if cat in ["PSF", "Uniformity/Distortion"]:
            try:
                img_id_name_dict, img_id_metric_df = get_images_for_metric(
                    dataset_id=dataset_id,
                    metric_id=cat,
                )
            except Exception as err:
                ui.notification_show(f"{err}", type="error")
                ui.update_select(
                    "image_id_selector", choices=["No images available"]
                )
                return None
            # If there is no images for the dataset
            if not img_id_name_dict:
                ui.update_select(
                    "image_id_selector", choices=["No images available"]
                )
                ui.notification_show(
                    "No images with PSF metrics could be found for the dataset.",
                    type="warning",
                )
            else:
                # Update the image selection drop-down
                ui.update_select("image_id_selector", choices=img_id_name_dict)
                # FYI: for "Uniformity/Distortion" the img_id_metric_df is empty
                return img_id_name_dict, img_id_metric_df
        else:
            ui.notification_show(
                f"OMERO for metric <{cat}> not implemented!", type="error"
            )
            ui.update_select(
                "image_id_selector", choices=["No images available"]
            )


@reactive.calc
def warn_csv() -> str:
    """
    Warn if csv upload for selected category is not implemented.

    :return: str, message if warning; empty str if no warning
    """
    cat = input.category()
    if cat not in ["Power"]:
        message = f"{cat} upload from CSV is not implemented!"
        ui.notification_show(message, type="warning")
        return message
    return ""


@reactive.calc
def warn_omero() -> str:
    """
    Warn if OMERO upload for selected category is not implemented.

    :return: str, message if warning; empty str if no warning
    """
    cat = input.category()
    if cat not in ["PSF", "Uniformity/Distortion"]:
        message = f"{cat} upload from OMERO is not implemented!"
        ui.notification_show(message, type="warning")
        return message
    return ""


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
    # Get unique sites and remove "" entries
    sites_ = list(np.unique(np.asarray(df["Site"])))
    sites = [s for s in sites_ if s != ""]
    sites.append("* New site *")
    site_list.set(sites)
    # if len(sites) == 0:
    #     raise RuntimeError("There are no site in the table!")
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


# General functions     ------------------------------------------------------


def check_power_prct_entries(df: pd.DataFrame) -> bool:
    """
    Check power percentage values.

    If entries are between 0-100, and if there are duplicate entries.

    :returns: bool, True if all fine
        otherwise (False) and shows notifications.
    """
    # Sanity test
    if "Power [%]" not in df.columns:
        raise RuntimeError("Expected a header column with 'Power [%]'.")

    # Get the unique values
    prct = np.unique(np.asarray(df["Power [%]"]))
    try:
        prct = [int(x) for x in prct]
    except ValueError as err:
        # Should not happen
        raise RuntimeError("Power [%] values are not integer") from err
    _min = min(prct)
    _max = max(prct)
    if _min <= 0 or _max > 100:
        ui.notification_show(
            "Power [%] values must be between 0-101!",
            id="prct_range",
            type="error",
        )
        return False
    # Check if there are repeated entries
    duplicates = list_duplicates(list(df["Power [%]"]))
    if len(duplicates) > 0:
        msg = f"You entered the same Power [%] multiple times: {', '.join(duplicates)}."
        ui.notification_show(msg, id="duplicate_prct", type="error")
        return False
    # Return True if all is fine
    return True


def check_channel_names_provided(df: pd.DataFrame) -> bool:
    """
    Check if provided channel names match existing sheet entries.

    :param df: DataFrame of the shown OMERO data, i.e.:
        *.data_patched()

    :return: bool, True if all fine
    """
    # Get the original dataframe (from the sheet)
    ori_df = dataframe.get().copy()

    # Get the common column values for filtering on ori_df
    _site = df["Site"][0]
    _mic = df["Microscope"][0]
    _obj = df["Objective"][0]
    _info = df["Info"][0]

    # Filter ori_df by common values
    ori_df = filter_by_column_value(ori_df, "Site", _site)
    ori_df = filter_by_column_value(ori_df, "Microscope", _mic)
    ori_df = filter_by_column_value(ori_df, "Objective", _obj)
    ori_df = filter_by_column_value(ori_df, "Info", _info)

    if ori_df.empty:
        # New entries = all fine
        return True

    # Get the ori_df channel names and the entered ones
    ori_ch_names = list(np.unique(np.asarray(ori_df["Channel"].astype(str))))
    entered_ch_names = list(np.unique(np.asarray(df["Channel"])))

    # Intermediate check if channel name was entere twice
    occurrence = {}
    for ch in entered_ch_names:
        occurrence[ch] = list(np.asarray(df["Channel"])).count(ch)
    if len(np.unique(list(occurrence.values()))) > 1:
        msg = ", ".join([f"{k} on {v} rows" for k, v in occurrence.items()])
        ui.notification_show(
            "Looks like you entered the same channel name multiple "
            f"times.\n{msg}.",
            type="error",
        )
        return False

    # Error if there are more new entries than existing ones
    if len(entered_ch_names) > len(ori_ch_names):
        ui.notification_show(
            "You try to upload more entries (channels = "
            f"{len(entered_ch_names)}) than there are in the database "
            f"({len(ori_ch_names)} known channels). This is not supported "
            "and requires manual editing of the google spreadsheet.",
            type="error",
        )
        return False

    # Check if entered channel names are in the existing ones
    unknown_ch = []
    for ch in entered_ch_names:
        if ch not in ori_ch_names:
            unknown_ch.append(ch)

    if len(unknown_ch) > 0:
        ui.notification_show(
            "You entered channel name(s) that are not in the database: "
            f"{' & '.join(unknown_ch)}. You should match them to existing "
            f"ones: {' or '.join(ori_ch_names)}",
            type="error",
        )
        return False
    # Otherwise all is fine
    return True


def check_similar_entries(existing: list[str], cur: str) -> bool:
    """
    Check if a string i similar to ones in a list.

    Removes special characters from the strings (incl. " "),
    and makes lower case.

    :param existing: list[str], to be checked
    :param cur: str, to check against the list

    :return: bool, True if similar entry found
    """
    for e in existing:
        # Remove special characters & make lower case
        list_entry = "".join(s.lower() for s in e if s.isalnum())
        text_entry = "".join(s.lower() for s in cur if s.isalnum())
        if list_entry == text_entry:
            return True
    return False


def check_new_text_entry(
    cur_sel: str, cur_entry: str, existing: list[str], id: str
) -> str:
    """
    Check new text entries.

    :param cur_sel: str, of the drop-down selection
    :param cur_entry: str, of the text field
    :param existing: list[str], list of drop-down choices
    :param id: str, drop-down category (e.g. site, microscope, ...) for notifications

    :return: str, "final choice" or what needs to be entered into the table.
    """
    # Check if drop-down requires text entry
    if cur_sel.startswith("*"):
        # Check if text was entered
        if cur_entry.startswith("Enter") or cur_entry.strip() == "":
            msg = f"Please enter a name for the new {id}."
            # Make sure the notification is shown only once, with param id
            ui.notification_show(msg, id=id, type="warning")
            return "Please define!"
        # Check if entry is similar to existing choices
        elif check_similar_entries(existing=existing, cur=cur_entry):
            msg = (
                f"The entered {id} name <{cur_entry}> is too similar "
                "to existing entries. Please change it."
            )
            # Make sure the notification is shown only once, with param id
            ui.notification_show(msg, id=id, type="warning")
            return "Please change!"
        else:
            # Text entry is good
            return cur_entry
    else:
        # Return text from the drop-down selection
        return cur_sel


# UI input/selection item creation      --------------------------------------
# Sidebar elements              #################
category = ui.input_select(
    "category",
    "Select a Metrology Category",
    choices=category_list,
    selected="Power",
)
site = ui.input_select("site", "Select a site", choices=[])
new_site = ui.input_text(
    "new_site", "* New site *", "Enter name for a new site"
)
upload_pwd = ui.input_password("upload_pwd", "Password for upload")

# Microscope entry elements     #################
microscope = ui.input_select("microscope", "Select a microscope", choices=[])
objective = ui.input_select("objective", "Select an objective", choices=[])
info = ui.input_select("info", "Filter by info column", choices=[])
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

# OMERO upload elements         #################

dataset_id_selector = ui.input_text(
    "dataset_id_selector", "Dataset ID", "Please enter an OMERO Dataset ID"
)
image_id_selector = ui.input_select(
    "image_id_selector",
    "Available images (ID: Name)",
    choices=["No images available"],
)
override_date_omero = ui.input_date(
    "override_date_omero", "Override the date from OMERO?", format="yyyymmdd"
)
omero_table_checked = ui.input_checkbox(
    "omero_table_checked", "Checked and ready for upload?", False
)
omero_upload_btn = ui.input_action_button(
    "omero_upload_btn", "Upload OMERO data"
)

# CSV data upload elements      #################
csv_file_selector = ui.input_file(
    "csv_file_selector",
    "Choose a .csv or .xlsx file",
    multiple=False,
    accept=[".csv", ".xlsx"],
)
csv_light_selector = ui.input_select(
    "csv_light_selector",
    "Select the light source kind",
    choices=["Please choose", "Laser", "LED"],
    selected="Please choose",
)
override_date_csv = ui.input_date(
    "override_date_csv", "Override the date?", format="yyyymmdd"
)
csv_power_objective_selection = ui.input_select(
    "csv_power_objective_selection",
    "Select an objective measurement",
    choices=["No selection available"],
)
csv_table_checked = ui.input_checkbox(
    "csv_table_checked", "Checked and ready for upload?", False
)
csv_upload_btn = ui.input_action_button("csv_upload_btn", "Upload CSV data")
