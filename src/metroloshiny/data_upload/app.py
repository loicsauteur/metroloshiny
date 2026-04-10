import numpy as np
import pandas as pd
from shiny import reactive
from shiny.express import input, render, ui

from metroloshiny.utils.dataframe_utils import filter_by_column_value
from metroloshiny.utils.omero_utils import omero_operation, render_dict
from metroloshiny.utils.read_file import get_gspread

g_spreadsheet = get_gspread(dev_local_file="./data/metroloshiny_data.xlsx")
dataframe = reactive.value(None)
category_list = ["Power at objective", "PSF"]
sites_list = ["Hebelstrasse", "Mattenstrasse"]

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

# PSF upload ui items
omero_type_selector = ui.input_select(
    "omero_datatype", "Select OMERO type", choices=["Dataset", "Image"]
)
omero_id_selector = ui.input_text(
    "omero_id", "OMERO ID", "Enter OMERO ID...2861227 or 2832822"
)
check_psf_values = ui.input_action_button("check_psf_values", "Check OMERO")
upload_psf_button = ui.input_action_button("upload_psf", "Upload the data!")


# Build the GUI
with ui.nav_panel(title="Data Upload"):
    # Sidebar
    with ui.layout_sidebar():
        with ui.sidebar():
            ui.input_select(
                "category",
                "Select a Metrology Categroy",
                choices=category_list,
                selected="PSF",
            )
            ui.input_select("site", "Select a site", choices=sites_list)
            ui.input_password("upload_pwd", "Password for upload")

        with ui.navset_card_underline():
            with ui.nav_panel(title="Test"):

                @render.ui
                def dynamic_selectors():
                    return card_selectors.get()

                # Add selectors
                # card_selectors
                # @render.ui
                # def dynamic_selectors():
                #     return card_selectors
        with ui.navset_card_underline():
            with ui.nav_panel("Upload info"):
                # @render.text
                @render.ui
                def upload_info():
                    """Create ui depending on Metrology category."""
                    # PSF
                    if input.category() == category_list[1]:
                        return (
                            omero_type_selector,
                            omero_id_selector,
                            check_psf_values,
                        )
                    # Power at objective
                    elif input.category() == category_list[0]:
                        return "Power upload stuff to come..."
                    else:
                        return "should never be seen"

                @render.ui
                @reactive.event(input.check_psf_values)
                def check_omero_input_psf():
                    """Get PSF data from OMERO."""
                    cur_omero_dataset = input.omero_datatype()
                    cur_omero_id = None
                    try:
                        cur_omero_id = int(input.omero_id())
                    except ValueError as err:
                        print("Could not parse OMERO ID", err)
                        return f"Error: Could not parse OMERO ID = {input.omero_id()}"

                    try:
                        data = omero_operation(
                            operation=None,
                            omero_type=cur_omero_dataset,
                            omero_id=cur_omero_id,
                            metric_id="FWHM",
                        )
                    except Exception as err:
                        return f"Error: {err}"
                    # TODO handle data
                    render_dict(data)
                    # IDea here: need to check which channels have FWHM data
                    # crate inputs for DAPI/GFP/ect. with selection for the channels
                    # return them here
                    import random  # FIXME temp test

                    c1 = random.randint(0, 11)
                    c2 = random.randint(0, 11)
                    input_dapi = ui.input_select(
                        "ch_dapi", "DAPI channel", choices=[c1, c2]
                    )
                    return input_dapi, upload_psf_button

                @render.text
                @reactive.event(input.upload_psf)
                def upload_omero_psf():
                    c1 = None
                    try:
                        c1 = int(input.ch_dapi())
                    except ValueError as err:
                        return f"Error: {err}"

                    if c1 == 5:
                        return "it succeeded!"
                    else:
                        return "was not 5 => fail!"

        # @render.ui
        # def dynamic_card():
        #     return ui.navset_card_underline()
        # with ui.nav_panel(title="test"):
        #     pass


# Reactive functions    ------------------------------------------------------
@reactive.effect
@reactive.event(input.category)
def update_on_cat_choice():
    """Update dataframe (sheet selection) and card selectors."""
    # Power at objective
    if input.category() == category_list[0]:
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
    elif input.category() == category_list[1]:
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
@reactive.event(input.site)
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
