from typing import Union

import numpy as np
import pandas as pd
from shiny import reactive
from shiny.express import input, render, ui

from metroloshiny.utils.dataframe_utils import filter_by_column_value
from metroloshiny.utils.omero_utils import omero_operation, render_dict
from metroloshiny.utils.read_file import check_upload_password, get_gspread

g_spreadsheet = get_gspread(dev_local_file="./data/metroloshiny_data.xlsx")
dataframe = reactive.value(None)
sites_list = ["Hebelstrasse", "Mattenstrasse"]
category_list = ["Please choose", "Power at objective", "PSF"]
# Dictionary to map category to OMERO metric "key-word"
category_to_metric = {
    "Please choose": "not implemented",
    "Power at objective": "not implemented",
    "PSF": "FWHM",
}

ui.page_opts(title="Metrology Upload")


# Reactive stuff here
card_selectors = reactive.value([])
microscope_choices = reactive.value([])

# Optional selections
# Common selectors
microscope_selector = ui.input_select(
    "microscope", "Select a microscope", choices=[]
)
objective_selector = ui.input_select(
    "objective", "Select an objective", choices=[]
)
info_selector = ui.input_select("info", "Filter by info column", choices=[])
new_mic_name = ui.input_text(
    "new_mic_name",
    "Enter a name for a new Microscope entry",
    "Enter name for new microscope...",
)
new_obj_name = ui.input_text(
    "new_obj_name",
    "Enter a name for a new Objective",
    "Enter name for new objective...",
)
new_info_name = ui.input_text(
    "new_info_name", "Enter additional information", "Enter info..."
)
# date_selector for measurement date (set to today! parse in proper format)

# Power at objective selecotrs
# FIXME probably not all needed
kind_selector = ui.input_select("kind", "Select light source kind", choices=[])
line_selector = ui.input_select("line", "Select a wavelength [nm]", choices=[])
power_selector = ui.input_select("power", "Select power [%]", choices=[])

# OMERO data retrive ui items
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

# PSF channel selection (provided for 4)
psf_dapi_selector = ui.input_select(
    "psf_dapi_selector", "Please confirm the DAPI channel", choices=[]
)
psf_gfp_selector = ui.input_select(
    "psf_gfp_selector", "Please confirm the GFP channel", choices=[]
)
psf_cy3_selector = ui.input_select(
    "psf_cy3_selector", "Please confirm the Cy3 channel", choices=[]
)
psf_cy5_selector = ui.input_select(
    "psf_cy5_selector", "Please confirm the Cy5 channel", choices=[]
)

upload_psf_button = ui.input_action_button(
    "upload_psf_button", "Upload the data!"
)


# Build the GUI
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
            ui.input_select("site", "Select a site", choices=sites_list)
            ui.input_select(
                "upload_type", "Select data source", choices=["OMERO", "CSV"]
            )
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

                @render.ui
                @reactive.event(card_selectors)
                def dynamic_selectors():
                    print("updated dynamic card selecotrs")
                    return card_selectors.get()

                # Add selectors
                # card_selectors
                # @render.ui
                # def dynamic_selectors():
                #     return card_selectors

        # Upload Data   ------------------------------------------------------
        with ui.navset_card_underline():
            with ui.nav_panel("Upload info"):
                # FIXME maybe better to have either CSV data or OMERO data

                @render.ui
                @reactive.event(input.upload_type, input.category)
                def render_upload_info():
                    """
                    Populate the upload info based on data source selection.

                    Also resets when category is changed.
                    """
                    if input.upload_type() == "OMERO":
                        return (
                            omero_type_selector,
                            omero_id_selector,
                            check_omero_data,
                        )
                    elif input.upload_type() == "CSV":
                        return "CSV upload data fields"
                    else:
                        return

                @render.ui
                @reactive.event(input.check_omero_data)
                def check_omero_input():
                    """Validate the OMERO input data."""
                    # Ensure category is selected
                    if input.category() == category_list[0]:
                        return "Please select a metrology category!"
                    # Do not allow OMERO data for power measurements
                    if input.category() == category_list[1]:
                        return "Power measurements from OMERO not supported!"

                    _metric = category_to_metric.get(input.category())
                    if _metric == "not implemented":
                        return f"Not implemented: Getting data from OMERO for {input.category()}"
                    if _metric is None:
                        raise RuntimeError(
                            f"Could not find metric for: {input.category()}"
                        )

                    # Check on OMERO
                    data = validate_omero_input(
                        omero_type=input.omero_type_selector(),
                        omero_id=input.omero_id_selector(),
                        metric=_metric,
                    )

                    # If errors data will be of type string
                    if isinstance(data, str):
                        return data

                    render_dict(data)

                    # Create subsequent ui items depending on the updload data type
                    if _metric == "FWHM":
                        ui_elements = list(update_confrim_psf_selection(data))
                        # Add upload FWHM button
                        ui_elements.append(upload_psf_button)
                        return ui_elements
                    else:
                        raise NotImplementedError(
                            f"The metric {_metric} in not implemented yet!"
                        )

                    return "found a dict"

                @render.text
                @reactive.event(input.upload_psf_button)
                def uplaod_psf():
                    # Checks before uplaod
                    # No upload password
                    if input.upload_pwd() == "":
                        return "Error: Please provide the upload password!"
                    # Wrong upload password
                    if not check_upload_password(input.upload_pwd()):
                        return "Error: wrong upload password!"

                    # Get the Microscope entries (& "validate")
                    microscope = input.microscope_selector()
                    if microscope.startswith("*"):
                        microscope = input.new_mic_name()
                        if microscope.startswith("Enter"):
                            return (
                                "Please enter a name for the new microscope!"
                            )

                    objective = input.objective_selector()
                    if objective.startswith("*"):
                        objective = input.new_obj_name()
                        if objective.startswith("Enter"):
                            return "Please enter a name for the new objective!"

                    info = input.info_selector()
                    if info.startswith("*"):
                        info = input.new_info_name()
                        if info.startswith("Enter"):
                            return "Please enter a name for the new objective!"
                    # Get the site
                    site = input.site()
                    site = site.strip()  # FIXME temporary ruff fix

                    return "Button Pressed!"

                # # @render.text
                # @render.ui
                # def upload_info():
                #     # FIXME see above
                #     """Create ui depending on Metrology category."""
                #     # PSF
                #     if input.category() == category_list[2]:
                #         return (
                #             omero_type_selector,
                #             omero_id_selector,
                #             check_psf_values,
                #         )
                #     # Power at objective
                #     elif input.category() == category_list[1]:
                #         return "Power upload stuff to come..."
                #     else:
                #         return "should never be seen"

                # @render.ui
                # @reactive.event(input.check_psf_values)
                # def check_omero_input_psf():
                #     """Get PSF data from OMERO."""
                #     cur_omero_dataset = input.omero_datatype()
                #     cur_omero_id = None
                #     try:
                #         cur_omero_id = int(input.omero_id())
                #     except ValueError as err:
                #         print("Could not parse OMERO ID", err)
                #         return f"Error: Could not parse OMERO ID = {input.omero_id()}"

                #     try:
                #         data = omero_operation(
                #             operation=None,
                #             omero_type=cur_omero_dataset,
                #             omero_id=cur_omero_id,
                #             metric_id="FWHM",
                #         )
                #     except Exception as err:
                #         return f"Error: {err}"
                #     # TODO handle data
                #     render_dict(data)
                #     # IDea here: need to check which channels have FWHM data
                #     # crate inputs for DAPI/GFP/ect. with selection for the channels
                #     # return them here
                #     import random  # FIXME temp test

                #     c1 = random.randint(0, 11)
                #     c2 = random.randint(0, 11)
                #     input_dapi = ui.input_select(
                #         "ch_dapi", "DAPI channel", choices=[c1, c2]
                #     )
                #     return input_dapi, upload_psf_button

                # @render.text
                # @reactive.event(input.upload_psf)
                # def upload_omero_psf():
                #     c1 = None
                #     try:
                #         c1 = int(input.ch_dapi())
                #     except ValueError as err:
                #         return f"Error: {err}"

                #     if c1 == 5:
                #         return "it succeeded!"
                #     else:
                #         return "was not 5 => fail!"

        # @render.ui
        # def dynamic_card():
        #     return ui.navset_card_underline()
        # with ui.nav_panel(title="test"):
        #     pass

# General functions     ------------------------------------------------------


def temp_fix_ui_panel():
    return ui.input_text("temp_fix", label="temp fix")


def update_confrim_psf_selection(channel_dict: dict) -> tuple:
    """
    Update the PSF channel confirmation selection choices.

    Choices are updated based on the channel_dict keys

    :param: channel_dict: dict as returned by the validte_omero_input function.

    :return: tuple of ui elements
    """
    chs = channel_dict.keys()
    choices = list(chs).copy()
    choices.append("None")
    ui.update_select(
        "psf_dapi_selector",
        choices=choices,
        selected="C1" if "C1" in choices else "None",
    )
    ui.update_select(
        "psf_gfp_selector",
        choices=choices,
        selected="C2" if "C2" in choices else "None",
    )
    ui.update_select(
        "psf_cy3_selector",
        choices=choices,
        selected="C3" if "C3" in choices else "None",
    )
    ui.update_select(
        "psf_cy5_selector",
        choices=choices,
        selected="C4" if "C4" in choices else "None",
    )
    return (
        psf_dapi_selector,
        psf_gfp_selector,
        psf_cy3_selector,
        psf_cy5_selector,
    )


def validate_omero_input(
    omero_type: str, omero_id: Union[str, int], metric: str
) -> Union[str, dict]:
    """
    Validate the OMERO input selection.

    Tries to retrieve the associated OMERO data (key-value or table.)

    :param omero_type: str "Project", "Dataset" or "Image"
    :param omero_id: str or int OMERO ID (str will be parsed to int)
    :param metric: str metric keyword to search for in the OMERO object.

    :return: str for errors or dict with data ??? or other FIXME ???
    """
    # Parse OMERO ID
    try:
        omero_id = int(omero_id)
    except ValueError:
        return f"Error: Could not parse OMERO ID = <{omero_id}>"
    # Get the data from OMERO
    try:
        data = omero_operation(
            operation=None,
            omero_type=omero_type,
            omero_id=omero_id,
            metric_id=metric,
        )
    except Exception as err:
        return f"Error: {err}"

    # Get the specific metrics
    if metric == "FWHM":
        return validate_psf_data(data)

    else:
        # FIXME needs implementation to validate other metric categories
        return f"NotImplementedError: {metric} is not yet implemented!"


def validate_psf_data(data_dict: dict) -> dict:
    """
    Parse the OMERO FWHM data to a dict per channel.

    :param data_dict: dictionary as returned from the omero_operation function

    :return: dict with keys = channel identifies (e.g. C1)
        values = dict{FWHM-X:value, FWHM-Y:value, FWHM-Z:value}
    """
    results = {}
    for key, value in data_dict.items():
        if "FWHM" in key:
            ch = key.split("_")[0]
            if not ch.startswith("C"):
                raise RuntimeError(
                    f"Channel not could not be identified for {key}"
                )
            if ch not in results.keys():
                results[ch] = {}
            if "X" in key:
                if "FWHM-X" in results[ch].keys():
                    raise RuntimeError(
                        f"Found multiple entries for {ch} 'Axial-X' FWHM."
                    )
                results[ch]["FWHM-X"] = value
            if "Y" in key:
                if "FWHM-Y" in results[ch].keys():
                    raise RuntimeError(
                        f"Found multiple entries for {ch} 'Axial-Y' FWHM."
                    )
                results[ch]["FWHM-Y"] = value
            if "Z" in key:
                if "FWHM-Z" in results[ch].keys():
                    raise RuntimeError(
                        f"Found multiple entries for {ch} 'Z' FWHM."
                    )
                results[ch]["FWHM-Z"] = value
    return results


# Reactive functions    ------------------------------------------------------
@reactive.effect
@reactive.event(input.category)
def update_on_cat_choice():
    """Update dataframe (sheet selection) and card selectors."""
    print("updating card selectors...")
    if input.category() == category_list[0]:
        card_selectors.set([])
    # Power at objective
    elif input.category() == category_list[1]:
        card_selectors.set(
            [
                microscope_selector,
                new_mic_name,
                objective_selector,
                new_obj_name,
                info_selector,
                new_info_name,
                kind_selector,
                line_selector,
                power_selector,
            ]
        )
        if isinstance(g_spreadsheet, pd.DataFrame):
            # For local file testing
            print("dataframe already loaded from excel")
            dataframe.set(g_spreadsheet)
        else:
            sheet = g_spreadsheet.worksheet("psf_measurements")
            df = pd.DataFrame(sheet.get_all_records())
            dataframe.set(df)
    # PSF
    elif input.category() == category_list[2]:
        card_selectors.set(
            [
                microscope_selector,
                new_mic_name,
                objective_selector,
                new_obj_name,
                info_selector,
                new_info_name,
            ]
        )
        if isinstance(g_spreadsheet, pd.DataFrame):
            # For local file testing
            print("dataframe already loaded from excel")
            dataframe.set(g_spreadsheet)
        else:
            sheet = g_spreadsheet.worksheet(
                "laser_power_objective_measurements"
            )
            df = pd.DataFrame(sheet.get_all_records())
            dataframe.set(df)
    else:
        raise RuntimeWarning("No category selected")


@reactive.effect
@reactive.event(input.category, input.site)
def update_microscope_selections():
    if dataframe.get() is None:
        return
    df_filtered = dataframe.get().copy()
    # Common choices
    df_filtered = filter_by_column_value(df_filtered, "Site", input.site())
    # Update microscope choices
    mics = list(np.unique(np.asarray(df_filtered["Microscope"])))
    mics.append("* New microscope *")
    print("microcsopes:", mics)
    microscope_choices.set(mics)
    ui.update_select("microscope", choices=microscope_choices.get())

    ## FIXME Maybe do not filter by "*new..."


@reactive.effect
@reactive.event(input.site, input.microscope)
def update_objective_selections():
    if dataframe.get() is None:
        return
    df_filtered = dataframe.get().copy()
    # Common choices
    df_filtered = filter_by_column_value(df_filtered, "Site", input.site())
    # Filter by microscope
    df_filtered = filter_by_column_value(
        df_filtered, "Microscope", input.microscope()
    )
    # Update objective choices
    objectives = list(np.unique(np.asarray(df_filtered["Objective"])))
    objectives.append("* New objective *")
    ui.update_select("objective", choices=objectives)


@reactive.effect
@reactive.event(input.site, input.microscope, input.objective)
def update_info_selections():
    if dataframe.get() is None:
        return
    df_filtered = dataframe.get().copy()
    # Common choices
    df_filtered = filter_by_column_value(df_filtered, "Site", input.site())
    # Filter by microscope
    df_filtered = filter_by_column_value(
        df_filtered, "Microscope", input.microscope()
    )
    # DO NOT Filter by objective - to keep available options
    # df_filtered = filter_by_column_value(
    #      df_filtered, "Objective", input.objective()
    # )
    # Update info choices
    infos = list(np.unique(np.asarray(df_filtered["Info"])))
    infos.append("* New info *")
    ui.update_select("info", choices=infos)


@reactive.effect
@reactive.event(input.microscope)
def test_add_name_field():
    """
    Make new microscope name field.

    TODO only visible when "* New microscope *" selected.

    FIXME probably not really possible to do it this way
    """
    # print("on input microscope the mic is:", input.microscope())
    # # Add name field entry for new microscope entry
    # if input.microscope() == "* New microscope *":
    #     # Check if card_selectors does not yet contain it yet
    #     if not is_input_select_in_list(card_selectors.get(), "new_mic_name"):
    #         l = card_selectors.get()
    #         l.insert(1, new_mic_name)
    #         card_selectors.set(l)
    #         print("****")
    #         for i in card_selectors.get():
    #             print(get_ui_id(i))
    #         print("****")
    #         #card_selectors.set(list(cur_list))
    #         #ui.update_select(
    #               "microscope", choices=microscope_choices.get()
    #          )
    # else:
    #     # Make sure to remove it if an exisiting microscope is selected
    #     if is_input_select_in_list(card_selectors.get(), "new_mic_name"):
    #         card_selectors.get().pop(1)
    #         card_selectors.set(card_selectors.get())
    #         print("****")
    #         for i in card_selectors.get():
    #             print(get_ui_id(i))
    #         print("****")
    #         # card_selectors.set(list(cur_list))
    #         # ui.update_select(
    #               "microscope", choices=microscope_choices.get()
    #           )

    # if card_selectors.get() and is_input_select_in_list(
    #      card_selectors.get(), "line"
    #   ):
    #         print("card_selectors contains the line selector")
    # else:
    #     print("card_selectors does NOT contain the line selector")

    # if card_selectors.get() and any(
    #           x.id == "line" for x in card_selectors.get()
    #   ):
    #     print("power because it contains the line_selector")
    # else:
    #     print("contains something else")
