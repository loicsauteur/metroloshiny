from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.figure_factory as pff
import plotly.graph_objects as go
import seaborn as sns
from matplotlib.figure import Figure
from matplotlib.quiver import Quiver
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_widget

from metroloshiny.data_objects.field_data import FieldData
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
    normalize_df,
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

        # Uniformity - Heat-map like plots                  ##################
        with ui.navset_card_underline(title="Field Uniformity"):
            with ui.nav_panel(title="Plot"):
                # Add 2 columns for date comparison selections
                with ui.layout_column_wrap(width=1 / 2):

                    @render.ui
                    def uni_date_sel_1():
                        """Show date selection for 1st unifomrity figure."""
                        data = get_omero_data()
                        if data is None:
                            choices = []
                        else:
                            choices = data.get_uniformity().keys()
                        # Unfortunately a slider does not work nicely
                        uni_date_selector_1 = ui.input_select(
                            "uni_date_selector_1",
                            "Select a date",
                            choices=list(choices),
                        )
                        return uni_date_selector_1

                    @render.ui
                    def uni_date_sel_2():
                        """Show date selection for 2nd unifomrity figure."""
                        data = get_omero_data()
                        if data is None:
                            choices = []
                        else:
                            choices = data.get_uniformity().keys()
                            choices = list(choices)
                        # Unfortunately a slider does not work nicely
                        uni_date_selector_2 = ui.input_select(
                            "uni_date_selector_2",
                            "Select a date",
                            choices=choices,
                            selected=(
                                None if len(choices) == 0 else choices[-1]
                            ),
                        )
                        return uni_date_selector_2

                @render.ui
                def uniformity_channel_selector():
                    """Show a channel selector."""
                    channels = get_common_uniformity_channels()
                    uni_ch_selector = ui.input_select(
                        "uni_ch_selector", "Display channel", choices=channels
                    )
                    return uni_ch_selector

                @render.plot
                def plot_field_uniformity():
                    """Plot field uniformity of 2 dates side by side."""
                    return create_uniformity_plot()

        # Distortion - Heat-map like plots                  ##################
        with ui.navset_card_underline(title="Field Distortion"):
            with ui.nav_panel(title="Plot"):

                @render.ui
                def dist_date_sel_1():
                    """Show date selection for 2nd unifomrity figure."""
                    data = get_omero_data()
                    if data is None:
                        choices = []
                    else:
                        choices = data.get_distortion().keys()
                        choices = list(choices)
                    dist_date_selector_1 = ui.input_select(
                        "dist_date_selector_1",
                        "Select a date",
                        choices=choices,
                        selected=None if len(choices) == 0 else choices[0],
                    )
                    return dist_date_selector_1

                @render_widget
                def show_distortion_from_rois():
                    """
                    Plot distortion calculated from ROIs.

                    # TODO will be replaced by table data, to show distortion for each channel
                    """
                    return create_distortion_plot()

            with ui.nav_panel(title="Table"):
                # FIXME not sure if there will be a table

                @render.text
                def temp_2():
                    """Show temp message."""
                    return "Under construction"


# Ideas:
# Uniformity        --------------
# heat map: normalised -- DONE!
# Line profiles (averages?) in different directions (also diagonal?) ?? TODO?


# Plot creation             --------------------------------------------------


@reactive.calc
def create_distortion_plot():
    """
    Create a distortion (quiver) plot with plotly.

    :return: plotly plot
    """
    # Get the data and necessary inputs
    omero_data = get_omero_data()
    date1 = input.dist_date_selector_1()
    if omero_data is None or date1 is None:
        return no_data_plotly()

    # Get the plotting data
    df = omero_data.get_distortion_dataframe_from_rois(date1).copy()

    # Create magnitude heat-map data (no normalization)
    heat = df.pivot(index="y", columns="x", values="Magnitude").to_numpy()

    # Create normalized distortion vectors
    df_norm = normalize_df(df, start_col=3)
    x = df_norm["x"].to_numpy()
    y = df_norm["y"].to_numpy()
    dx = df_norm["dx"].to_numpy()
    dy = df_norm["dy"].to_numpy()

    df["angle"] = (np.degrees(np.arctan2(df["dx"], df["dy"])) * -1 + 180) % 360
    angle = df.pivot(index="y", columns="x", values="angle").to_numpy()

    # Create the heatmap figure             ##################################
    fig = go.Figure()
    fig.add_trace(
        go.Heatmap(
            z=heat,
            x=np.arange(1, heat.shape[1] + 1),
            y=np.arange(1, heat.shape[0] + 1),
            colorscale="Viridis",
            colorbar={
                "title": {
                    "text": "Magnitude<br>(currently in pixels)",
                    "side": "right",
                },
                # Position relative to whole figure
                "x": 1.0,
                "xanchor": "left",
                "xpad": 0,
                # Make height as tall asa heatmap
                # "len": 1.0,
                # "y": 0.5,
                # "yanchor": "middle",
            },
            zsmooth="best",
            customdata=angle,
            hovertemplate=(
                "x=%{x}<br>"
                "y=%{y}<br>"
                "Magnitude=%{z:.3f}<br>"
                "Angle=%{customdata:.1f}°<extra></extra>"
            ),
        )
    )

    quiv = pff.create_quiver(
        x,
        y,
        dx,
        dy,
        scale=2,
        arrow_scale=0.3,
        hoverinfo="skip",
        showlegend=False,
        # fill="white",
    )
    # Add the quiver to the figure
    for trace in quiv.data:
        # Define arrow color and line width
        trace.line.color = "white"
        trace.line.width = 1.0
        fig.add_trace(trace)

    # Layout                                ##################################
    mic = input.microscope()
    obj = input.objective()
    obj = get_nice_objective_name(objective_df, obj)
    info = input.info()

    fig.update_layout(
        title=(f"Field Distortion (from OMERO ROIs):<br>{mic} {obj} ({info})"),
        plot_bgcolor="white",
        xaxis={
            # "domain": [0, 0.88],  # Space for the heatmap
            "showgrid": False,
            "zeroline": False,
            "showticklabels": False,
            "constrain": "domain",
        },
        yaxis={
            "showgrid": False,
            "zeroline": False,
            "showticklabels": False,
            # "constrain": "domain",
            "scaleanchor": "x",
            "scaleratio": 1,
            "autorange": "reversed",
        },
        margin={
            "l": 0,
            "r": 80,
            "t": 60,
            "b": 0,
        },
        # Define the size of the figure - Don't use that
        # width=900,
        # height=600,
        autosize=True,
    )
    return fig


@reactive.calc
def create_distortion_plot_old_mpl() -> tuple[
    Figure,
    Optional[Quiver],
    Optional[pd.Series],
    Optional[pd.Series],
]:
    """
    Create a distortion quiver plot.

    FIXME deprecated matplotlib version of the plot

    Create a heat-map background for the magnitude.
    Add arrows for the distortion direction (+ magnitude.)
    Returns plotting relevant variables for the arrows,
    which allows modification on the fly (within the plot UI function).
    However, animated plots do not work on the VM.

    TODO for comparing 2 dates, the coloring should be the same for the 2 plots,
        i.e. normalise the 2 dataframes together?


    :return: plt.Figure, if no data figure, other values are None
    :return: Optional[plt.Quiver]
    :return: Optional[pd.Series], dx values (aka U)
    :return: Optional[pd.Series], dy values (aka V)
    """
    omero_data = get_omero_data()
    date1 = input.dist_date_selector_1()
    if omero_data is None or date1 is None:
        return no_data_seaborn(), None, None, None

    # Get the plotting data
    df = omero_data.get_distortion_dataframe_from_rois(date1)
    # Set the XY tiles to 0-based index
    df["x"] = df["x"] - 1
    df["y"] = df["y"] - 1

    # Create magnitude heat-map
    df_heat = df.pivot(index="y", columns="x", values="Magnitude")

    df_heat = df_heat.to_numpy()

    # Create quiver plot
    fig, axes = plt.subplots()
    heat_map = axes.imshow(
        df_heat, interpolation="bicubic", origin="upper", cmap="viridis"
    )

    # Quiver = arrows with long shaft...
    # Normalize the dataframe values (for arrow lengths)
    df = normalize_df(df, start_col=3)
    quiver = axes.quiver(
        df["x"],
        df["y"],
        df["dx"],
        df["dy"],
        # df["Magnitude"], # for coloring arrows in viridis
        color="white",
        angles="xy",
        scale_units="xy",
        scale=0.5,  # inversly scales the length of arrows (2 looks not bad)
        # Need a way to scale more dynamically!
        pivot="tail",  # default = "tail", arrow anchoring part to xy tile
        # width=0.003,  # default
        alpha=1,
        # label="test-label",
        headwidth=5,  # default 3, Head width as multiple of shaft width.
        headlength=7,  # default 5, Head length as multiple of shaft width.
        headaxislength=5,  # default 4.5, Head length at shaft intersection as multiple of shaft width
        minshaft=0.5,  # default 1, Length below which arrow scales, in units of head length - DONT use
        # minlength=0.0001,  # doesnt really do anything
        # width=0.0001,
    )

    axes.set_aspect("equal")
    axes.axis("off")

    # Add colorbar
    cbar = plt.colorbar(heat_map)
    # FIXME currently pixel units
    cbar.set_label("Magnitude (currently in pixels)")
    # ax.legend() # not needed
    mic = input.microscope()
    obj = input.objective()
    obj = get_nice_objective_name(objective_df, obj)
    info = input.info()
    # FIXME currently from OMERO ROIs
    fig.suptitle(f"Field Distortion (from OMERO ROIs):\n{mic} {obj} ({info})")
    return fig, quiver, df["dx"], df["dy"]


@reactive.calc
def create_uniformity_plot_sns():
    """
    Create a heat-map like plot for the Filed Uniformity between 2 dates.

    FIXME seaborn heatmaps cannot have interpolation...

    :return: matplotlib Figure with seaborn plots
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

    # Create an image with the difference of the two (in %)
    diff = (df_1 - df_2) * 100

    # Create plot
    fig, axes = plt.subplots(
        nrows=1,
        ncols=4,
        figsize=(12, 4),
        gridspec_kw={"width_ratios": [1, 1, 1, 0.2]},
    )

    # Common Seaborn settings
    heatmap_kwargs = {
        "cmap": "viridis",
        "xticklabels": False,
        "yticklabels": False,
        "cbar": False,
        "ax": axes[0],
    }

    # First date
    sns.heatmap(
        df_1,
        **heatmap_kwargs,
    )
    axes[0].set_title(f"{date1} - {channel}")
    axes[0].set_xlabel("")
    axes[0].set_ylabel("")

    # Second date
    sns.heatmap(
        df_2,
        **{**heatmap_kwargs, "ax": axes[1]},
    )
    axes[1].set_title(f"{date2} - {channel}")
    axes[1].set_xlabel("")
    axes[1].set_ylabel("")

    # Difference plot
    sns.heatmap(
        diff,
        ax=axes[2],
        cmap="bwr",
        vmin=-100,
        vmax=100,
        xticklabels=False,
        yticklabels=False,
        cbar=False,
    )
    axes[2].set_title("Difference")
    axes[2].set_xlabel("")
    axes[2].set_ylabel("")

    # Dedicated colorbar axis
    norm = plt.Normalize(vmin=-100, vmax=100)
    sm = plt.cm.ScalarMappable(norm=norm, cmap="bwr")
    sm.set_array([])

    cbar = fig.colorbar(sm, cax=axes[3])
    cbar.set_label("Difference [%]")

    # Hide the unused axis frames
    for ax in axes[:3]:
        for spine in ax.spines.values():
            spine.set_visible(False)

    mic = input.microscope()
    obj = input.objective()
    obj = get_nice_objective_name(objective_df, obj)
    info = input.info()

    fig.suptitle(f"Field Uniformity: {mic} {obj} ({info})")

    return fig


@reactive.calc
def create_uniformity_plot():
    """
    Create a heat-map like plot for the Filed Uniformity between 2 dates.

    FIXME: on VM when scaling the window, title gets bigger and bigger,
        until it gives an error...

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

    # Create an image with the difference of the two (in %)
    diff = (df_1 - df_2) * 100

    # Create plot (4 rows, last one for the scale bar)
    fig, axes = plt.subplots(
        nrows=1,
        ncols=4,
        figsize=(12, 4),
        gridspec_kw={"width_ratios": [1, 1, 1, 0.2]},
    )
    # Interpolation = bicubic for smooth interpolation
    axes[0].imshow(
        df_1, interpolation="bicubic", origin="upper", cmap="viridis"
    )
    axes[0].set_title(f"{date1} - {channel}")
    axes[1].imshow(
        df_2, interpolation="bicubic", origin="upper", cmap="viridis"
    )
    axes[1].set_title(f"{date2} - {channel}")

    # Add the difference plot with colors blue>white>red (always show values -100 to + 100)
    diff_img = axes[2].imshow(
        diff,
        interpolation="bicubic",
        origin="upper",
        cmap="bwr",
        vmin=-100,
        vmax=100,
    )
    axes[2].set_title("Difference")
    # Add color bar for the difference plot
    # Can't make it look better than that. Depends on the window size...
    cbar = fig.colorbar(diff_img, ax=axes[3])
    cbar.set_label("Difference [%]")

    # Hide the frames / ticks except for the difference plot
    for i, ax in enumerate(axes):
        if i == 2:
            ax.set_xticks([])
            ax.set_yticks([])
        else:
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

    # Report possible errors (other than the ones below...) with the list data.problems
    if len(data.problems) > 0:
        msg = ["There were some problems while loading the data:"]
        for i in data.problems:
            msg.append(ui.tags.br())
            msg.append(i)
        ui.notification_show(*msg, id="data_problems", type="error")

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
