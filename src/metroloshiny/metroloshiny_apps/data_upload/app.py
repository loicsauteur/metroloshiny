from typing import Optional

import numpy as np
import pandas as pd
from shiny import reactive
from shiny.express import input, render, ui

from metroloshiny.data_objects.PSFData import PSFData
from metroloshiny.utils.common_utils import (
    get_today,
    get_version,
    set_local_file,
)
from metroloshiny.utils.dataframe_utils import (
    filter_by_column_value,
)
from metroloshiny.utils.omero_utils import (
    get_image_voxelsize_channel_names,
    get_images_for_metric,
)
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

# TODO-DONE: Choose dataset ID then have choices of IMAGE ID with needed metrics
# TODO: Maybe a lucky shot multi objective table with single dataset ID??
#   TODO: PSF/bead images have tags = beads, psf
#   TODO: Argolight images have tags = fwhm, argolight
# TODO-DONE: Implement new site option
# TODO: upload different power csvs!

# Reactive values       ------------------------------------------------------
sheet_reference = reactive.value(None)
dataframe = reactive.value(None)
category_list = ["Power", "PSF"]  # "Uniformity" TODO once implemented
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
                def render_omero_upload():
                    """Show OMERO input selectors only on PSF category."""
                    message = warn_omero()
                    if message != "":
                        return message
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
                    return override_date

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
                def render_csv_upload():
                    """Show OMERO input selectors only on PSF category."""
                    message = warn_csv()
                    if message != "":
                        return message
                    else:
                        return "TODO"


# Table edit functions  ------------------------------------------------------


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
    if input.category() == "PSF":
        # Check the only patch
        row = patches[0]["row_index"]
        col = patches[0]["column_index"]
        val = patches[0]["value"]

        # Sanity check
        if df.columns[4] != "Channel":
            raise RuntimeError(
                "Expected the 5th column to be 'Channel' "
                f"but was: <{df.columns[4]}>",
            )

        # Allow changes only in column 4 (=Channel)
        if col != 4:
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


# Reactive functions    ------------------------------------------------------


@reactive.effect
@reactive.event(input.omero_upload_btn)
def upload_omero_data():
    """
    Check, then upload the OMERO data.

    Performs the check and upload based on input.category.
    """
    # Prevent upload for working with local file            ##################
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

    # For PSF upload
    if input.category() == "PSF":
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
                "Please check the highlighted channel names and make sure to "
                "check the checkbox above the upload button!",
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

    if input.category() == "PSF":
        # Sanity check
        if df.columns[4] != "Channel":
            # Currently no notification warning
            return None
        # Highlight the column 4
        style = [
            {
                # No 'row' = all rows
                "cols": [4],
                "style": {"background-color": "yellow", "font-weight": "bold"},
            }
        ]
        return style
    else:
        # TODO implement for other categories
        return None  # Currently return None


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
        acquisition_date = get_today()
        ui.notification_show(
            "Could not identify the data acquisition date! Set to today!",
            type="warning",
            duration=10,
        )
    # Update the date override selector
    ui.update_date("override_date", value=acquisition_date)
    return df


@reactive.calc
def get_common_column_values() -> tuple[str, str, str, str]:
    """
    Get the values for the common columns.

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
        # If df.empty, then wrong inputs -> return empty df FIXME??
        if df.empty:
            return df
        override_date = input.override_date()

        # Get the values for the common columns
        _site, _mic, _obj, _info = get_common_column_values()
        # Create the dataframe to be uploaded
        df = prepare_data_for_entry(
            data=df,
            data_headers=list(df.columns)[:2],
            site=_site,
            microscope=_mic,
            objective=_obj,
            info=_info,
            date=override_date.strftime("%Y%m%d"),
        )
    else:
        # TODO implement also other categories
        pass
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
        if cat == "PSF":
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
    """Warn if csv upload for selected category is not implemented."""
    cat = input.category()
    if cat not in ["Power"]:
        message = f"{cat} upload from CSV is not implemented!"
        ui.notification_show(message, type="warning")
        return message
    return ""


@reactive.calc
def warn_omero() -> str:
    """Warn if OMERO upload for selected category is not implemented."""
    cat = input.category()
    if cat not in ["PSF", "Uniformity"]:
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
    # if df is None or df.empty: # FIXME probably not needed here
    #     print("df is none or empty")
    #     return
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
    ori_ch_names = list(np.unique(np.asarray(ori_df["Channel"])))
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
    selected="PSF",
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
override_date = ui.input_date(
    "override_date", "Override the date from OMERO?", format="yyyymmdd"
)
omero_table_checked = ui.input_checkbox(
    "omero_table_checked", "Checked and ready for upload?", False
)
omero_upload_btn = ui.input_action_button(
    "omero_upload_btn", "Upload OMERO data"
)
