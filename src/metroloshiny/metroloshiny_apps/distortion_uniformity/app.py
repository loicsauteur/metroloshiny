# for upload: table with omero IDs per date
#     (ie. upload check if the rois are available/ 'Field_Uniformity_avg', 'Field_Distortion_avg__um' != 1)
# for app: load ROIS and visualise them?
# Distortion based on point coordinates vs ideal position
# Uniformity based on point mean intensity
# analysis based on: https://github.com/BIOP/ArgoLight_analysis_tool/blob/988c4147822562c25c53a04ad20fad577798aeed/scripts/ARGO-SIM_analysis_code.groovy
# check also this for adding ROI uploads: https://github.com/BIOP/ArgoLight_analysis_tool/blob/988c4147822562c25c53a04ad20fad577798aeed/src/main/java/ch/epfl/biop/processing/ArgoSlideProcessing.java
# ---------
# user Image ID = 3021627 FIXME

from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_widget

from metroloshiny.data_objects.FieldData import FieldData
from metroloshiny.utils.common_utils import (
    get_nice_objective_name,
    get_version,
    set_local_file,
)
from metroloshiny.utils.dataframe_utils import (
    filter_by_column_value,
)
from metroloshiny.utils.plot_utils import (
    no_data_plotly,
    no_data_seaborn,
    normalize_percentile,
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
                def render_plotting_options():
                    """FIXME: Construction in progress."""
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

        #   Field Distortion and Uniformity - average metrics   ##############
        with ui.navset_card_underline(
            title="Average Field Distortion & Uniformity"
        ):
            with ui.nav_panel(title="Plot Field Uniformity"):

                @render_widget
                def show_field_uniformity_over_time_plot():
                    """Show field uniformity average over time plot."""
                    data = get_omero_data()
                    if data is None:
                        return no_data_plotly()
                    df_unif = data.get_uniformity_over_time_melt()
                    # TODO check for "problems" and give some warnings!
                    return create_plot_over_time(df_unif)

            with ui.nav_panel(title="Plot Field Distortion"):

                @render_widget
                def show_field_distortion_over_time_plot():
                    """Show field distortion average over time plot."""
                    data = get_omero_data()
                    if data is None:
                        return no_data_plotly()
                    df_dist = data.get_distortion_over_time_melt()
                    # TODO check for "problems" and give some warnings!
                    return create_plot_over_time(df_dist)

            with ui.nav_panel(title="Table"):

                @render.data_frame
                def show_uni_dist_avg_over_time_table():
                    """Show table of distortion/uniformity average over time."""
                    # TODO date_range_selector (setting min/max in get_omero_data function)
                    data = get_omero_data()
                    # Show no dataframe if no data loaded yet
                    if data is None:
                        return pd.DataFrame()
                    # Merge uniformity and distortion dataframes
                    df_dist = data.get_distortion_over_time_melt()
                    df_unif = data.get_uniformity_over_time_melt()
                    df = df_dist.merge(df_unif, on=["Date", "Channel"])
                    # Sort the dataframe properly
                    df = df.sort_values(by=["Date", "Channel"])
                    return df

        # Distortion & Uniformity - Heat-map like plots     ##################
        # TODO Next create fake images?!
        with ui.navset_card_underline(title="Field Uniformity"):
            with ui.nav_panel(title="Plot"):
                # Add 2 columns for date comparison selections
                with ui.layout_column_wrap(width=1 / 2):

                    @render.ui
                    def uni_date_sel_1():
                        data = get_omero_data()
                        if data is None:
                            choices = []
                        else:
                            choices = data.get_uniformity().keys()
                        uni_date_selector_1 = ui.input_select(
                            "uni_date_selector_1",
                            "Select a date",
                            choices=list(choices),
                        )
                        return uni_date_selector_1

                    @render.ui
                    def uni_date_sel_2():
                        data = get_omero_data()
                        if data is None:
                            choices = []
                        else:
                            choices = data.get_uniformity().keys()
                            choices = list(choices)
                        uni_date_selector_2 = ui.input_select(
                            "uni_date_selector_2",
                            "Select a date",
                            choices=choices,
                            selected=(
                                None if len(choices) == 0 else choices[-1]
                            ),
                        )
                        # FIXME maybe I can set selected to the last date already??
                        return uni_date_selector_2

                @render.ui
                def uniformity_channel_selector():
                    """Show a channel selector."""
                    channels = get_common_uniformity_channels()
                    uni_ch_selector = ui.input_select(
                        "uni_ch_selector", "Display channel", choices=channels
                    )
                    return uni_ch_selector

                # How to plot
                # Drop down channel selector
                # layout_column_warp with 2 drop-down date selectors
                # Plot with 2 figures to compare side by side (per channel only)

                @render.plot
                def plot_field_uniformity():
                    """Plot field uniformity of 2 dates side by side."""
                    return create_uniformity_plot()


# Ideas:
# Uniformity        --------------
# heat map: normalised -- DONE!
# Line profiles (averages?) in different directions (also diagonal?) ???


# Distortion        ------------
# Heat-map showing strongest ∆
# Arrow w/ length map, using matplotlib quiver function (should be possible for different colors)
# From Chat
# ------->if df ~:
# x     y     channel    dx      dy
# 100   100   red        0.4    -0.2
# 200   100   red        0.7    -0.3
# 100   100   green      0.1     0.2
# 200   100   green      0.3     0.1
# ...
# -------> Code:
# colors = {
#     "red": "red",
#     "green": "limegreen",
#     "blue": "blue",
# }

# fig, ax = plt.subplots(figsize=(8, 8))

# scale = 50

# for channel, color in colors.items():

#     d = df[df["channel"] == channel]

#     ax.quiver(
#         d["x"],
#         d["y"],
#         d["dx"] * scale,
#         d["dy"] * scale,
#         color=color,
#         angles="xy",
#         scale_units="xy",
#         scale=1,
#         width=0.003,
#         alpha=0.8,
#         label=channel
#     )

# ax.set_aspect("equal")
# ax.legend()
# plt.show()


# Plot creation             --------------------------------------------------


@reactive.calc
def create_uniformity_plot():
    """
    Create a heat-map like plot for the Filed Uniformity between 2 dates.

    :return: matplotlib plot
    """
    # Get the date selections and channel selection
    channel = input.uni_ch_selector()
    date1 = input.uni_date_selector_1()
    date2 = input.uni_date_selector_2()
    omero_data = get_omero_data()
    if channel is None or date1 is None or date2 is None or omero_data is None:
        return no_data_seaborn()

    # Get the data (convert unidata for heatmap)
    uni_data = omero_data.get_uniformity()
    df_1 = omero_data.get_heat_map_dataframe(date=date1, data_dict=uni_data)
    df_2 = omero_data.get_heat_map_dataframe(date=date2, data_dict=uni_data)

    # Pivot the dfs for given channel (-> XY-table)
    df_1 = df_1.pivot(index="Y", columns="X", values=channel)
    df_2 = df_2.pivot(index="Y", columns="X", values=channel)
    # Normalise the values (individually for each df)
    df_1 = normalize_percentile(df_1).to_numpy()
    df_2 = normalize_percentile(df_2).to_numpy()

    # Create plot
    fig, axes = plt.subplots(1, 2)
    # Interpolation = bicubic for smooth interpolation
    axes[0].imshow(
        df_1, interpolation="bicubic", origin="upper", cmap="viridis"
    )
    axes[0].set_title(f"{date1} - {channel}")
    axes[1].imshow(
        df_2, interpolation="bicubic", origin="upper", cmap="viridis"
    )
    axes[1].set_title(f"{date2} - {channel}")

    for ax in axes:
        ax.axis("off")

    mic = input.microscope()
    obj = input.objective()
    obj = get_nice_objective_name(objective_df, obj)
    info = input.info()
    fig.suptitle(f"Field Uniformity: {mic} {obj} ({info})")

    return fig


def create_plot_over_time(df: pd.DataFrame):
    """
    Create plot for average metrics over time.

    Line of the column that contains "Average",
    with STD of column that contains "STD"

    :param df: pd.DataFrame with columns:
        Date, Channel, Average**, STD**

    :return: plotly.express plot (use in @render_widget)
    """
    if df.empty:
        return no_data_plotly()

    # Create line plot for Average with STD
    average = next(x for x in df.columns if "Average" in x)
    std = next(x for x in df.columns if "STD" in x)
    plot = px.line(
        data_frame=df,
        x="Date",
        y=average,
        color="Channel",
        error_y=std,
        markers=True,
        # hover_data={
        #     "Date": True,
        #     average: ":.f ± :.2f"
        # }
    )
    # Update the layout
    plot.update_layout(
        template="simple_white",
        margin={"r": 200},
        # legend={ # not really necessary
        #     "yanchor": "top",
        #     "y": 1,
        #     "xanchor": "left",
        #     "x": 1.02,
        # },
    )
    # Rotate x-axis labels
    plot.update_xaxes(
        tickangle=45,
        # Reduce number of displayed ticks
        nticks=10,
        showgrid=False,
        title="",
    )
    # Update y-axis
    plot.update_yaxes(showgrid=True, gridcolor="lightgrey")
    return plot


# Reactive calcs            --------------------------------------------------


@reactive.calc
def get_valid_uniformity_dataframes() -> dict[str, pd.DataFrame]:
    """
    Get the uniformity tables, excluding the dates are None.

    :return: dict, same as get_uniformity() but date always has a pd.DataFrame
    """
    uni = get_omero_data().get_uniformity()
    return {k: v for k, v in uni.items() if v is not None}


@reactive.calc
def get_common_uniformity_channels() -> list[str]:
    """
    Get a list of common uniformity channels (between 2 dats).

    Reacts on inputs uni_date_selector_1 & uni_date_selector_2

    :return: list[str] of channels or empty list
    """
    # Get the date strings
    date1 = input.uni_date_selector_1()
    date2 = input.uni_date_selector_2()
    # Return empty list if there is no selection
    if date1 is None or date2 is None:
        return []
    # Get the data
    data = get_omero_data()
    # Sanity check
    if data is None:
        return []
    # Column headers to exclude
    default_cols = ["Ring_ID", "X", "Y"]
    # Get channel names for date 1 & 2
    date1_chs = get_valid_uniformity_dataframes().get(date1)
    date1_chs = [x for x in date1_chs.columns if x not in default_cols]
    date2_chs = get_valid_uniformity_dataframes().get(date2)
    date2_chs = [x for x in date2_chs.columns if x not in default_cols]
    # Get the common channels
    common_chs = list(set(date1_chs).intersection(date2_chs))
    # Warn if some channels are not available for both dates
    if len(common_chs) != len(date1_chs) or len(common_chs) != len(date2_chs):
        ui.notification_show(
            "Some channels are not available for both dates",
            type="warning",
            id="uni_ch_warn",
        )
    return common_chs


@reactive.calc
def get_omero_data() -> Optional[FieldData]:
    """
    Load all the data from OMERO, but only once selections are ready.

    Reminder distortion values are actually um (if gotten from tables)

    :return: FieldData object, with metrics loaded from OMERO
    """
    df = get_sidebar_filtered_dataframe()
    if df.empty:
        return None

    # Drop nan columns (cols may not be nan but empty str...)
    df = df.replace("", np.nan)
    df = df.dropna(axis="columns")

    # Create and load data
    data = FieldData(df, retrieve_omero=True)

    # Check if there is really data associated
    try:
        data.get_distortion()
        data.get_uniformity()
        data.get_detected_rois()
    except RuntimeError:
        # If RuntimeError -> no data associated -> warn
        ui.notification_show(
            "There is no Field Uniformity/Distortion data for the current selection!",
            type="warning",
            id="no_data",
        )
        data = None

    return data


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
    o_dict = {i: get_nice_objective_name(objective_df, i) for i in o}

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
