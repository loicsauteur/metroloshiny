# for upload: table with omero IDs per date
#     (ie. upload check if the rois are available/ 'Field_Uniformity_avg', 'Field_Distortion_avg__um' != 1)
# for app: load ROIS and visualise them?
# Distortion based on point coordinates vs ideal position
# Uniformity based on point mean intensity
# analysis based on: https://github.com/BIOP/ArgoLight_analysis_tool/blob/988c4147822562c25c53a04ad20fad577798aeed/scripts/ARGO-SIM_analysis_code.groovy
# check also this for adding ROI uploads: https://github.com/BIOP/ArgoLight_analysis_tool/blob/988c4147822562c25c53a04ad20fad577798aeed/src/main/java/ch/epfl/biop/processing/ArgoSlideProcessing.java
# ---------
# user Image ID = 3021627


import numpy as np
import pandas as pd
from shiny import reactive
from shiny.express import input, render, ui

from metroloshiny.utils.common_utils import (
    get_objective_mag,
    get_objective_na,
    get_version,
    set_local_file,
)
from metroloshiny.utils.dataframe_utils import (
    filter_by_column_value,
)
from metroloshiny.utils.read_file import get_sheet, load_doc

# Load Data
use_dev_local_file = set_local_file()
sheet_doc = load_doc(dev_local_file=use_dev_local_file)
wsheet_psf, dataframe = get_sheet(
    sheet_doc, "Uniformity/Distortion", dev_local_file=use_dev_local_file
)
# Load objectives dataframe conditionally
objective_df = None
if dataframe["Objective"].str.startswith("ID").any():
    _, objective_df = get_sheet(
        sheet_doc, "Objectives", dev_local_file=use_dev_local_file
    )

# Global variable       ------------------------------------------------------
sites = np.unique(np.asarray(dataframe["Site"]))


# Reactive variables              --------------------------------------------
# Remember choices for objectives (to maybe create an objective_db table)
objective_choices = reactive.value(None)

# Create UI         ----------------------------------------------------------
ui.page_opts(
    title="Metrology: Field Uniformity and Distortion",
    footer=f"Version {get_version()}",
)
with ui.nav_panel(title=""):
    # Sidebar          -------------------------------------------------------
    with ui.layout_sidebar():
        with ui.sidebar():
            ui.input_select("site", "Select the site", choices=list(sites))
            ui.input_select("microscope", "Select a microscope", choices=[])
            ui.input_select("objective", "Select an objective", choices=[])
            ui.input_select("info", "Filter by info column", choices=[])

        with ui.navset_card_underline(title="Plotting options"):
            with ui.nav_panel(title="Options"):

                @render.ui
                def test_1():
                    """Construction in progress."""
                    return "under construction"

            with ui.nav_panel(title="Objective information"):

                @render.text
                def show_objective_table_message():
                    """Show info if no database objective available."""
                    df, _ = create_objective_db_table()
                    if df.empty:
                        return "No objective information available."
                    else:
                        return ""

                @render.data_frame
                def show_objective_table():
                    """Render the available objective table."""
                    df, styles = create_objective_db_table()
                    return render.DataGrid(df, styles=styles)

        with ui.navset_card_underline(title="Some plot title"):  # FIXME
            with ui.nav_panel(title="Plot"):

                @render.ui
                def test_2():
                    """Construction in progress."""
                    # FIXME
                    get_omero_data()
                    return "under construction"

            with ui.nav_panel(title="Table"):

                @render.ui
                def test_3():
                    """Construction in progress."""
                    return "under construction"


# Reactive calcs            --------------------------------------------------


@reactive.calc
def get_omero_data():  # FIXME define output type
    """
    Load all the data from OMERO, but only once selections are ready.

    TODO describe output
    """
    print("get omero data executed")
    df = get_sidebar_filtered_dataframe()
    if df.empty:
        return None

    # Drop nan columns (cols may not be nan but empty str...)
    df = df.replace("", np.nan)
    df = df.dropna(axis="columns")

    print("--> df")
    print(df)
    # TODO
    # - drop nan columns
    # - identify unique OMERO IDs
    # - if they do not start with omero -> not implemented
    # - create omero_utils function to load all image IDs,
    #   and associate the channel with the OMERO channel

    # Reminder distortion values are actually um (if gotten from tables)


@reactive.calc
def get_sidebar_filtered_dataframe() -> pd.DataFrame:
    """Filter the google sheet data by the sidebar selection."""
    df = dataframe.copy()
    _site = input.site()
    df = filter_by_column_value(df, "Site", _site)
    _mic = input.microscope()
    df = filter_by_column_value(df, "Microscope", _mic)
    _obj = input.objective()
    df = filter_by_column_value(df, "Objective", _obj)
    _info = input.info()
    df = filter_by_column_value(df, "Info", _info)
    if df.empty:
        return pd.DataFrame()
    return df


@reactive.calc
def create_objective_db_table() -> tuple[pd.DataFrame, list[dict]]:
    """
    Create a table of objectives in database for the selected microscope.

    Creates also styles to highlight the selected objective

    :return:
        pd.DataFrame, of available objectives
        list[dict], of styles to highlight row of the DataGrid
    """
    # Filter the dataframe by site & microscope
    _site = input.site()
    _mic = input.microscope()
    df = dataframe.copy()
    df = filter_by_column_value(df, "Site", _site)
    df = filter_by_column_value(df, "Microscope", _mic)
    # Get a list of objective IDs
    db_objectives = [x for x in df["Objective"] if x.startswith("ID")]
    # Return empty dataframe & list if no ID objectives
    if len(db_objectives) == 0:
        return pd.DataFrame(), []

    # Create dataframe subset from objective_db
    subset = objective_df.copy()
    subset = subset[subset["ID"].isin(db_objectives)]
    subset = subset.reset_index(drop=True)
    # Create a style to highlight the selection
    cur_objective = input.objective()
    selected = subset[subset["ID"] == cur_objective].index
    styles = [
        {
            # Rows are re-indexed (NOT df.index)
            "rows": list(selected),
            "style": {"background-color": "yellow", "font-weight": "bold"},
        }
    ]
    return subset, styles


# Reactive functions - Sidebar      ------------------------------------------


@reactive.effect
@reactive.event(input.site)
def update_microscope_choices():
    """Update microscope choices based on site selection."""
    # Filter the data frame (always the original) and
    # set the reactive result dataframe
    df_filtered = filter_by_column_value(
        dataframe.copy(), "Site", input.site()
    )
    # Get a list of microscopes and set the reactive result
    m_filtered = np.unique(np.asarray(df_filtered["Microscope"]))
    # Update the ui selection (using the reactive variable)
    ui.update_select("microscope", choices=list(m_filtered))


@reactive.effect
@reactive.event(input.microscope, input.site)
def update_objective_choices():
    """Update objective choices based on microscope selection."""
    # Filter original df from start
    df_filtered = filter_by_column_value(
        dataframe.copy(), "Site", input.site()
    )
    df_filtered = filter_by_column_value(
        df_filtered, "Microscope", input.microscope()
    )
    # Get a list of unique objective choices
    o = np.unique(np.asarray(df_filtered["Objective"]))
    # Create a dictionary with adapted names for IDs
    o_dict = {}
    for i in o:
        # keys=input values, values=shown to user
        if i.startswith("ID"):
            try:
                na = get_objective_na(objective_df, i)
                if na is None:
                    # in case of parsing error
                    na = "?"
            except RuntimeError:
                # in case not in objective_db
                na = "?"
            try:
                mag = get_objective_mag(objective_df, i)
                if mag is None:
                    mag = "?"
            except RuntimeError:
                mag = "?"
            o_dict[i] = f"{mag!s}x/{na} ({i})"
        else:
            o_dict[i] = i
    # Update the ui selection
    ui.update_select("objective", choices=o_dict)
    # Update the objective choices
    objective_choices.set(o_dict.keys())


@reactive.effect
@reactive.event(input.objective, input.microscope, input.site)
def update_info_choices():
    """Update info choices based on microscope & objective selection."""
    # Filter original df from start
    df_filtered = filter_by_column_value(
        dataframe.copy(), "Site", input.site()
    )
    df_filtered = filter_by_column_value(
        df_filtered, "Microscope", input.microscope()
    )
    df_filtered = filter_by_column_value(
        df_filtered, "Objective", input.objective()
    )
    # Get a list of unique info items
    i = np.unique(np.asarray(df_filtered["Info"]))
    # Update the ui selection
    ui.update_select("info", choices=list(i))
