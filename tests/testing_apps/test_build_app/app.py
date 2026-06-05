from shiny import reactive
from shiny.express import input, render, ui

from metroloshiny.utils.read_file import (
    check_upload_password,
    get_sheet,
    load_doc,
)

# Load Data
use_dev_local_file = False
sheet_doc = load_doc(dev_local_file=use_dev_local_file)

# wsheet, df = get_sheet(
#     sheet_doc,
#     kind="PSF",
#     dev_local_file=use_dev_local_file
# )

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

# Build the GUI     items       ----------------------------------------------
ui.page_opts(title="Metrology Upload")
with ui.nav_panel(title="Data Upload"):
    # Sidebar
    with ui.layout_sidebar():
        # Sidebar   ----------------------------------------------------------
        with ui.sidebar():
            ui.input_select(
                "category",
                "Select a Metrology Category",
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
                        # return ui.input_select("test", "test", choices=["a", "b"])

                    # Column 2 for "new" text entries
                    @render.ui
                    def mic_col_2():
                        return new_mic_name, new_obj_name, new_info_name
                        # return ui.input_text("test2", "test2", value="test-val")


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
    print(df.head())


def set_to_local_for_test():
    """
    Set the global variable to True.

    Initially thought for testing, to switch to local file for
    more precise testing. But I cannot import functions from an
    app to the tests, as it would build build the app...
    """
    use_dev_local_file = True
    print(use_dev_local_file)
