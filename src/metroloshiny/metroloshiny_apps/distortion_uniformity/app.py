from typing import Optional, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.figure_factory as pff
import plotly.graph_objects as go
from matplotlib.figure import Figure
from matplotlib.quiver import Quiver
from plotly.subplots import make_subplots
from shiny import reactive
from shiny.express import input, render, session, ui
from shinywidgets import render_plotly, render_widget

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
    add_center_cross_plotly,
    no_data_plotly,
    no_data_seaborn,
    normalize_df,
    normalize_percentile,
)
from metroloshiny.utils.read_file import get_sheet, load_doc

# Ideas:
# Uniformity        --------------
# Line profiles (averages?) in different directions (also diagonal?) ?? TODO? probably not
# TODO: Roll-off metrics instead of the current averages...

# TODO add absolute intensities to uniformity plot hover over

# TODO distortion plots add difference plot (calculate new vectors from dx/dy)


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
# Card heights (random initial values)
uni_2_dates_card_height = reactive.value("20px")
uni_channel_compare_card_height = reactive.value("20px")

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

        #   Field Distortion and Uniformity - average metrics   ##############
        with ui.navset_card_underline(
            title="Average Field Distortion & Uniformity", id="averages_card"
        ):
            with ui.nav_panel(title="Plot Field Uniformity"):

                @render.ui
                def show_uniformity_date_range():
                    """Show Uniformity date range selector."""
                    # For sanity check the same as in show_distortion_date_range
                    data = get_omero_data()
                    if data is None:
                        uni_date_range = ui.input_date_range(
                            "uni_date_range",
                            "Select a date range",
                            format="yyyymmdd",
                        )
                        return uni_date_range
                    # Specify date range
                    dates = data.get_uniformity().keys()
                    dates = sorted([str(x)[:8] for x in dates])
                    uni_date_range = ui.input_date_range(
                        "uni_date_range",
                        "Select a date range",
                        format="yyyymmdd",
                        start=dates[0],
                        end=dates[-1],
                    )
                    return uni_date_range

                @render_widget
                def show_field_uniformity_over_time_plot():
                    """Show field uniformity average over time plot."""
                    data = get_omero_data()
                    if data is None:
                        return no_data_plotly()
                    # Get the dataframe and filter by date
                    df_unif = filter_avg_unifomrmity_by_date()
                    return create_plot_over_time(df_unif)

            with ui.nav_panel(title="Plot Field Distortion"):

                @render.ui
                def show_distortion_date_range():
                    """Show Distortion date range selector."""
                    # Reactive event for date range may have been triggered before date_range ui render
                    data = get_omero_data()
                    # No initial date range specification
                    if data is None:
                        dist_date_range = ui.input_date_range(
                            "dist_date_range",
                            "Select a date range",
                            format="yyyymmdd",
                        )
                        return dist_date_range
                    # Specify date range
                    dates = data.get_distortion().keys()
                    dates = sorted([str(x)[:8] for x in dates])
                    dist_date_range = ui.input_date_range(
                        "dist_date_range",
                        "Select a date range",
                        format="yyyymmdd",
                        start=dates[0],
                        end=dates[-1],
                    )
                    return dist_date_range

                @render_widget
                def show_field_distortion_over_time_plot():
                    """Show field distortion average over time plot."""
                    data = get_omero_data()
                    if data is None:
                        return no_data_plotly()
                    # Get the dataframe and filter by date
                    # df_dist = data.get_distortion_over_time_melt()
                    df_dist = filter_avg_distortion_by_date()
                    return create_plot_over_time(df_dist)

            with ui.nav_panel(title="Table"):

                @render.data_frame
                def show_uni_dist_avg_over_time_table():
                    """Show table of distortion/uniformity average over time."""
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

        # Uniformity - Heat-map like plots                  ##################
        # TODO FIXME: could do also use express.ui.accordion for collapsible vertical tabs??
        with ui.navset_card_underline(
            title="Field Uniformity", id="uniformity_card"
        ):
            # Compare 2 dates for the same colors           ##################
            with ui.nav_panel(title="Compare two dates"):
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
                            choices = list(choices)
                        # Unfortunately a slider does not work nicely
                        uni_date_selector_1 = ui.input_select(
                            "uni_date_selector_1",
                            "Select a first date",
                            choices=list(choices),
                            selected=None if len(choices) == 0 else choices[0],
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
                            "Select a second date",
                            choices=choices,
                            selected=(
                                None if len(choices) == 0 else choices[-1]
                            ),
                        )
                        return uni_date_selector_2

                # Plot the uniformity comparison between 2 dates   -----------
                # Add a little space
                ui.div(style="margin-top: 20px;")

                @render.express
                def card_uni_2_dates():
                    # """Trick to dynamically set the card height."""
                    # No doc-string, would be printed in UI.
                    with ui.card(min_height=uni_2_dates_card_height.get()):

                        @render_plotly
                        def plot_field_uniformity():
                            """Plot field uniformity of 2 dates side by side."""
                            # Trigger card height reactive calculation
                            _height = set_card_height_uni_2date_comparison()

                            # Show the plot
                            # return create_uniformity_plot()
                            # FIXME convert to plotly plots
                            fig, _ = plot_uniformity_2_measurements()
                            return fig

            # Compare 2 channels on the same date           ##################
            with ui.nav_panel(title="Compare channels"):
                # Add 2 columns for 2 channel selections (for 1 date)
                with ui.layout_column_wrap(width=1 / 2):

                    @render.ui
                    def uniformity_channel_selector_1():
                        """Show selector for a first channel."""
                        data = get_omero_data()
                        date = input.uni_single_date_selector()
                        if data is None or date is None:
                            channels = []
                        else:
                            channels = sorted(data.get_channel_names(date))
                        uni_ch_selector1 = ui.input_select(
                            "uni_ch_selector1",
                            "Select a first channel",
                            choices=channels,
                            selected=(
                                None if len(channels) == 0 else channels[0]
                            ),
                        )
                        return uni_ch_selector1

                    @render.ui
                    def uniformity_channel_selector_2():
                        """Show selector for a second channel."""
                        data = get_omero_data()
                        date = input.uni_single_date_selector()
                        if data is None or date is None:
                            channels = []
                        else:
                            channels = sorted(data.get_channel_names(date))
                        uni_ch_selector2 = ui.input_select(
                            "uni_ch_selector2",
                            "Select a second channel",
                            choices=channels,
                            selected=(
                                None if len(channels) == 0 else channels[-1]
                            ),
                        )
                        return uni_ch_selector2

                @render.ui
                def uni_single_date_sel():
                    """Show date selection for 1st unifomrity figure."""
                    data = get_omero_data()
                    if data is None:
                        choices = []
                    else:
                        choices = data.get_uniformity().keys()
                        choices = list(choices)
                    # Unfortunately a slider does not work nicely
                    uni_single_date_selector = ui.input_select(
                        "uni_single_date_selector",
                        "Select a date",
                        choices=list(choices),
                        selected=None if len(choices) == 0 else choices[0],
                    )
                    return uni_single_date_selector

                # Add a little space
                ui.div(style="margin-top: 20px;")

                # Plot the uniformity comparison between channels       ------
                @render.express
                def card_uni_compare_channels():
                    # """Trick to dynamically set the card height."""
                    # No doc-string, would be printed in UI.
                    with ui.card(
                        min_height=uni_channel_compare_card_height.get()
                    ):

                        @render_plotly
                        def plot_field_uniformity_between_channels():
                            """Plot field uniformity of different channels on same date."""
                            # Trigger card height reactive calculation
                            _ = set_card_height_uni_2channel_comparison()
                            return plot_uniformity_between_channels()

        # Distortion - Heat-map like plots                  ##################
        with ui.navset_card_underline(
            title="Field Distortion", id="distortion_card"
        ):
            with ui.nav_panel(title="Plot"):
                # Add 2 columns for date comparison selections
                with ui.layout_column_wrap(width=1 / 2):

                    @render.ui
                    def distortion_selectors_1():
                        """Show date/channel selection for 1st distortion figure."""
                        return dist_date_selector_1, dist_ch_selector1

                    @render.ui
                    def distortion_selectors_2():
                        """Show date/channel selection for 2nd distortion figure."""
                        return dist_date_selector_2, dist_ch_selector2

                @render_widget
                def plot_distortion():
                    """
                    Plot distortion for a channel.

                    Free choice between dates and channel.
                    """
                    return create_distortion_plot()


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
    date2 = input.dist_date_selector_2()
    channel1 = input.dist_ch_selector1()
    channel2 = input.dist_ch_selector2()
    if None in [omero_data, date1, date2, channel1, channel2]:
        return no_data_plotly()

    # Get the plotting data
    df1 = omero_data.get_distortion_dataframe(date1).copy()
    df2 = omero_data.get_distortion_dataframe(date2).copy()
    df1 = filter_by_column_value(df1, column_name="Channel", value=channel1)
    df2 = filter_by_column_value(df2, column_name="Channel", value=channel2)

    # Create magnitude heat-map data (no normalization)
    heat1 = df1.pivot(index="y", columns="x", values="Magnitude").to_numpy()
    heat2 = df2.pivot(index="y", columns="x", values="Magnitude").to_numpy()

    # Create normalized distortion vectors
    df_norm1 = normalize_df(df1, start_col=3)
    x1 = df_norm1["x"].to_numpy()
    y1 = df_norm1["y"].to_numpy()
    dx1 = df_norm1["dx"].to_numpy()
    dy1 = df_norm1["dy"].to_numpy()
    df_norm2 = normalize_df(df2, start_col=3)
    x2 = df_norm2["x"].to_numpy()
    y2 = df_norm2["y"].to_numpy()
    dx2 = df_norm2["dx"].to_numpy()
    dy2 = df_norm2["dy"].to_numpy()

    df1["angle"] = (
        np.degrees(np.arctan2(df1["dx"], df1["dy"])) * -1 + 180
    ) % 360
    df2["angle"] = (
        np.degrees(np.arctan2(df2["dx"], df2["dy"])) * -1 + 180
    ) % 360
    angle1 = df1.pivot(index="y", columns="x", values="angle").to_numpy()
    angle2 = df2.pivot(index="y", columns="x", values="angle").to_numpy()

    # Get the magnitude max values (min is set to 0)
    heat_max = max(np.nanmax(heat1), np.nanmax(heat2))

    # Create the heatmap figure             ##################################
    fig = make_subplots(
        rows=1,
        cols=2,
    )
    # Heat-map for date1
    fig.add_trace(
        go.Heatmap(
            z=heat1,
            x=np.arange(1, heat1.shape[1] + 1),
            y=np.arange(1, heat1.shape[0] + 1),
            colorscale="Viridis",
            # Set the color min/max
            zmin=0,
            zmax=heat_max,
            # No colorbar explicitly with showscale=False
            showscale=False,
            zsmooth="best",
            customdata=angle1,
            hovertemplate=(
                "x=%{x}<br>"
                "y=%{y}<br>"
                "Magnitude=%{z:.3f}<br>"
                "Angle=%{customdata:.1f}°<extra></extra>"
            ),
        ),
        row=1,
        col=1,
    )
    # Heat-map for date1
    fig.add_trace(
        go.Heatmap(
            z=heat2,
            x=np.arange(1, heat2.shape[1] + 1),
            y=np.arange(1, heat2.shape[0] + 1),
            colorscale="Viridis",
            # Set the color min/max
            zmin=0,
            zmax=heat_max,
            zsmooth="best",
            customdata=angle2,
            hovertemplate=(
                "x=%{x}<br>"
                "y=%{y}<br>"
                "Magnitude=%{z:.3f}<br>"
                "Angle=%{customdata:.1f}°<extra></extra>"
            ),
            colorbar={
                "title": {
                    "text": "Magnitude [µm]",
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
        ),
        row=1,
        col=2,
    )

    # Add quiver plots on top               ##################################
    quiv1 = pff.create_quiver(
        x1,
        y1,
        dx1,
        dy1,
        scale=2,
        arrow_scale=0.3,
        hoverinfo="skip",
        showlegend=False,
        # fill="white",
    )
    # Add the quiver to the figure
    for trace in quiv1.data:
        # Define arrow color and line width
        trace.line.color = "white"
        trace.line.width = 1.0
        fig.add_trace(trace, row=1, col=1)
    quiv2 = pff.create_quiver(
        x2,
        y2,
        dx2,
        dy2,
        scale=2,
        arrow_scale=0.3,
        hoverinfo="skip",
        showlegend=False,
        # fill="white",
    )
    # Add the quiver to the figure
    for trace in quiv2.data:
        # Define arrow color and line width
        trace.line.color = "white"
        trace.line.width = 1.0
        fig.add_trace(trace, row=1, col=2)

    # Layout                                ##################################
    mic = input.microscope()
    obj = input.objective()
    obj = get_nice_objective_name(objective_df, obj)
    info = input.info()

    fig.update_layout(
        title={
            "text": f"Field Distortion: {mic} {obj} ({info})",
            "y": 0.94,
            "yanchor": "top",
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 18},
        },
        plot_bgcolor="white",
        margin={
            "l": 0,
            "r": 80,
            "t": 60,
            "b": 0,
        },
        autosize=True,
    )
    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        showticklabels=False,
        constrain="domain",
    )
    fig.update_yaxes(
        showgrid=False,
        zeroline=False,
        showticklabels=False,
        autorange="reversed",
    )
    # Ensure square plots
    fig.update_yaxes(row=1, col=1, scaleanchor="x", scaleratio=1)
    fig.update_yaxes(row=1, col=2, scaleanchor="x2", scaleratio=1)
    # Shift the plot a bit down (relative to title/top of the full figure)
    # for ann in fig.layout.annotations:
    #     ann.y -= 0.02
    # Add subplot tiltes
    fig.add_annotation(
        text=f"{date1} - {channel1}",
        xref="x domain",
        yref="y domain",  # relative to subplot 1's own domain
        x=0.5,  # centered horizontally
        y=0.94,  # top of domain
        xanchor="center",
        yanchor="bottom",
        yshift=-10,  # small pixel offset (to shift text down)
        showarrow=False,
        font={"size": 18},  # match default subplot title size if needed
    )
    fig.add_annotation(
        text=f"{date2} - {channel2}",
        xref="x2 domain",
        yref="y2 domain",  # relative to subplot 2's own domain
        x=0.5,  # centered horizontally
        y=0.94,  # top of domain
        xanchor="center",
        yanchor="bottom",
        yshift=-10,  # small pixel offset (to shift text down)
        showarrow=False,
        font={"size": 18},  # match default subplot title size if needed
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

    FIXME deprecated matplotlib version of the plot (uses info from ROIs)

    Create a heat-map background for the magnitude.
    Add arrows for the distortion direction (+ magnitude.)
    Returns plotting relevant variables for the arrows,
    which allows modification on the fly (within the plot UI function).
    However, animated plots do not work on the VM.

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
    # currently pixel units
    cbar.set_label("Magnitude (currently in pixels)")
    # ax.legend() # not needed
    mic = input.microscope()
    obj = input.objective()
    obj = get_nice_objective_name(objective_df, obj)
    info = input.info()
    fig.suptitle(f"Field Distortion (from OMERO ROIs):\n{mic} {obj} ({info})")
    return fig, quiver, df["dx"], df["dy"]


@reactive.calc
def plot_uniformity_between_channels():
    """
    Create heatmap like plots of the Field uniformity to compare 2 channels.

    On the same date.

    :return: plotly figure
    """
    # The the UI selections
    ch1 = input.uni_ch_selector1()
    ch2 = input.uni_ch_selector2()
    date = input.uni_single_date_selector()
    omero_data = get_omero_data()
    if None in [ch1, ch2, date, omero_data]:
        return no_data_plotly()

    # Don't bother plotting if there is only one channel
    if len(omero_data.get_channel_names(date)) == 1:
        msg = f"Only one channel ({omero_data.get_channel_names(date)[0]}) available for date {date}!"
        return no_data_plotly(msg)

    # Get the data (convert unidata for heatmap)
    uni_data = omero_data.get_uniformity()
    df = omero_data.get_heat_map_dataframe(date=date, data_dict=uni_data)

    # Pivot the dfs for given channel (-> XY-table)
    raw1 = df.pivot(index="Y", columns="X", values=ch1)
    raw2 = df.pivot(index="Y", columns="X", values=ch2)
    # Normalise the values (individually for each df)
    df1 = normalize_percentile(raw1).to_numpy()
    df2 = normalize_percentile(raw2).to_numpy()
    # Create an image of the difference of the 2 (in %)
    # FIXME not 100% correct since normalisation over percentile
    diff = (df1 - df2) * 100

    # Create figure panels          ##########################################
    fig = make_subplots(
        rows=1,
        cols=3,
        row_heights=None,
        column_widths=None,
    )
    # Add the channel panels        ------------------
    for i, plot_data in enumerate(
        zip([df1, df2], [raw1.to_numpy(), raw2.to_numpy()], strict=True),
        start=1,
    ):
        cur_df, raw = plot_data
        fig.add_trace(
            go.Heatmap(
                z=cur_df,
                x=np.arange(1, cur_df.shape[1] + 1),
                y=np.arange(1, cur_df.shape[0] + 1),
                colorscale="Viridis",
                showscale=False,  # No colorbar
                zsmooth="best",
                customdata=raw,
                hovertemplate=(
                    "x=%{x}<br>"
                    "y=%{y}<br>"
                    "Normalised Intensity=%{z:.0%}<br>"  # Show rounded percentage 0.1 = 10%
                    "Absolute Intensity=%{customdata:.0f} AU<br>"
                    "<extra></extra>"  # hide trace info hoverbox
                ),
            ),
            row=1,
            col=i,
        )
        # Add centering cross
        add_center_cross_plotly(
            fig,
            x_shape=cur_df.shape[1],
            y_shape=cur_df.shape[0],
            row=1,
            col=i,
            length=0.5,
            as_x=False,
        )
    # Add the difference panel      ------------------
    # Get the plot y location for the colorbar
    diff_domain = fig.layout["yaxis3"].domain
    fig.add_trace(
        go.Heatmap(
            z=diff,
            x=np.arange(1, diff.shape[1] + 1),
            y=np.arange(1, diff.shape[0] + 1),
            colorscale="RdBu",  # Red -> Blue
            # Adjust color range and show heatmap
            zmin=-100,
            zmax=100,
            colorbar={
                "title": {
                    "text": "Difference [%]",
                    "side": "right",
                },
                # Position relative to whole figure
                "x": 1.02,
                "xanchor": "left",
                "xpad": 0,
                "yref": "paper",
                "y": (diff_domain[0] + diff_domain[1])
                / 2,  # middle of the row
                "yanchor": "middle",
                "len": (diff_domain[1] - diff_domain[0])
                * 0.8,  # 80% of the row height
                "thickness": 15,  # Default = 30 (bar-width)
            },
            reversescale=True,  # Blue -> Red
            zsmooth="best",
            hovertemplate=(
                "x=%{x}<br>"
                "y=%{y}<br>"
                "Normalised Intensity=%{z:.0f}%<br>"
                "<extra></extra>"  # hide trace info hoverbox
            ),
        ),
        row=1,
        col=3,
    )
    # Add centering cross
    add_center_cross_plotly(
        fig,
        x_shape=diff.shape[1],
        y_shape=diff.shape[0],
        row=1,
        col=3,
        length=0.5,
        color="black",
        as_x=False,
    )
    # Add an outline to the Difference plot
    fig.add_shape(
        type="rect",
        xref="x3",  # Refers to the data plot
        yref="y3",
        x0=0.5,
        x1=diff.shape[1] + 0.5,
        y0=0.5,
        y1=diff.shape[0] + 0.5,
        line={"color": "black", "width": 1},
        fillcolor="rgba(0,0,0,0)",  # transparent
        layer="above",
    )
    # Plot title & layout           ##########################################
    mic = input.microscope()
    obj = input.objective()
    obj = get_nice_objective_name(objective_df, obj)
    info = input.info()
    fig.update_layout(
        title={
            "text": f"Field Uniformity {date}: {mic} {obj} ({info})",
            "yref": "container",  # the full canvas
            "pad": {
                "b": 0,
                "l": 0,
                "r": 0,
                "t": 10,
            },  # Give a little space to top
            "y": 1,  # at the top
            "yanchor": "top",
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 18},
        },
        plot_bgcolor="white",
        margin={
            # "autoexpand": False, # Default True, needed for colorbar
            "l": 25,
            "r": 0,
            "t": 70,  # min. title font + title top pad (empiric, 60 is not good anymore)
            "b": 0,
        },
        autosize=True,
    )
    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        showticklabels=False,
        constrain="domain",
    )
    fig.update_yaxes(
        showgrid=False,
        zeroline=False,
        showticklabels=False,
        autorange="reversed",
    )
    # Ensure square plots
    fig.update_yaxes(row=1, col=1, scaleanchor="x", scaleratio=1)
    fig.update_yaxes(row=1, col=2, scaleanchor="x2", scaleratio=1)
    fig.update_yaxes(row=1, col=3, scaleanchor="x3", scaleratio=1)
    # Add subplot tiltes            ##########################################
    for i, title in enumerate([ch1, ch2, "Difference"], start=1):
        if i == 1:
            panel = ""
        else:
            panel = i
        fig.add_annotation(
            text=title,
            xref=f"x{panel} domain",  # relative to panel's domain
            x=0.5,  # centered horizontally
            xanchor="center",
            # yref=f"y{panel}",  # relative to the heatmap
            yref="paper",
            y=1,  # top of domain
            yanchor="bottom",
            # yshift=10,  # small pixel offset (- to shift text down; + up)
            showarrow=False,
            font={"size": 18},  # match default subplot title size if needed
        )
    # Add row title (date)
    fig.add_annotation(
        text=date,
        xref="x domain",  # relative to the first panel
        yref="y domain",  # relative to the first panel
        x=0,
        y=0.5,
        xanchor="right",
        yanchor="middle",
        showarrow=False,
        font={"size": 18},
        textangle=-90,
    )
    return fig


@reactive.calc
def plot_uniformity_between_channels_mpl():
    """
    Create heatmap like plots of the Field uniformity to compare 2 channels.

    (On the same date)

    FIXME DEPRECATED -> replaced with plotly plots

    :return: matplotlib figure
    """
    # The the UI selections
    ch1 = input.uni_ch_selector1()
    ch2 = input.uni_ch_selector2()
    date = input.uni_single_date_selector()
    omero_data = get_omero_data()
    if None in [ch1, ch2, date, omero_data]:
        return no_data_seaborn()

    # Don't bother plotting if there is only one channel
    if len(omero_data.get_channel_names(date)) == 1:
        msg = f"Only one channel ({omero_data.get_channel_names(date)[0]}) available for date {date}!"
        return no_data_seaborn(msg)

    # Get the data (convert unidata for heatmap)
    uni_data = omero_data.get_uniformity()
    df = omero_data.get_heat_map_dataframe(date=date, data_dict=uni_data)

    # Create figure (4 rows, last one for the scale bar)
    fig, axes = plt.subplots(
        nrows=1,
        ncols=4,
        figsize=(12, 4),
        gridspec_kw={"width_ratios": [1, 1, 1, 0.2]},
    )

    # Pivot the dfs for given channel (-> XY-table)
    df1 = df.pivot(index="Y", columns="X", values=ch1)
    df2 = df.pivot(index="Y", columns="X", values=ch2)
    # Normalise the values (individually for each df)
    df1 = normalize_percentile(df1).to_numpy()
    df2 = normalize_percentile(df2).to_numpy()
    # Create an image of the difference of the 2 (in %)
    # FIXME not 100% correct since normalisation over percentile
    diff = (df1 - df2) * 100

    # Interpolation = bicubic for smooth interpolation
    axes[0].imshow(
        df1, interpolation="bicubic", origin="upper", cmap="viridis"
    )
    axes[1].imshow(
        df2, interpolation="bicubic", origin="upper", cmap="viridis"
    )

    # Add date as title to the left
    axes[0].text(
        -0.05,
        0.5,
        date,
        rotation="vertical",
        transform=axes[0].transAxes,
        va="center",
        ha="center",
        fontsize=12,
    )

    # Add the difference plot with colors blue>white>red (always show values -100 to + 100)
    diff_img = axes[2].imshow(
        diff,
        interpolation="bicubic",
        origin="upper",
        cmap="bwr",
        vmin=-100,
        vmax=100,
    )
    # Add color bar for the difference plot
    # Can't make it look better than that. Depends on the window size...
    cbar = fig.colorbar(diff_img, ax=axes[3])
    cbar.set_label("Difference [%]")

    # Adjust titles
    axes[0].set_title(f"{ch1}")
    axes[1].set_title(f"{ch2}")
    axes[2].set_title("Difference")

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
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    return fig


@reactive.calc
def plot_uniformity_2_measurements():
    """
    Create heatmap like plots for the Field uniformity between 2 dates.

    For all common channels. I.e.:
    DAPI | date1 | date2 | diff
    488  | date1 | date2 | diff
    ...

    :return: tuple,
        - plotly figure
        - int, number of plot rows
    """
    # Get date selections
    date1 = input.uni_date_selector_1()
    date2 = input.uni_date_selector_2()
    omero_data = get_omero_data()
    if None in [date1, date2, omero_data]:
        return no_data_plotly(), 1

    # Check available channels for the dates
    channels1 = omero_data.get_channel_names(date1)
    channels2 = omero_data.get_channel_names(date2)
    common_chs = sorted(set(channels1).intersection(channels2))
    if len(common_chs) == 0:
        return no_data_plotly("No common channels between the 2 dates!"), 1

    # Get the data (convert unidata for heatmap)
    uni_data = omero_data.get_uniformity()
    df_1 = omero_data.get_heat_map_dataframe(date=date1, data_dict=uni_data)
    df_2 = omero_data.get_heat_map_dataframe(date=date2, data_dict=uni_data)

    # Create figure panels              ######################################
    fig = make_subplots(rows=len(common_chs), cols=3, vertical_spacing=0.05)
    # Add the panels row by row
    for row, channel in enumerate(common_chs, start=1):
        # Pivot the dfs for given channel (-> XY-table)
        raw1 = df_1.pivot(index="Y", columns="X", values=channel)
        raw2 = df_2.pivot(index="Y", columns="X", values=channel)
        # Normalise the values (individually for each df)
        df1 = normalize_percentile(raw1).to_numpy()
        df2 = normalize_percentile(raw2).to_numpy()
        # Create an image of the difference of the 2 (in %)
        # FIXME not 100% correct since normalisation over percentile
        diff = (df1 - df2) * 100

        # Add channel plots     ----------------------
        for col, plot_data in enumerate(
            zip([df1, df2], [raw1.to_numpy(), raw2.to_numpy()], strict=True),
            start=1,
        ):
            z, raw = plot_data
            fig.add_trace(
                go.Heatmap(
                    z=z,
                    x=np.arange(1, z.shape[1] + 1),
                    y=np.arange(1, z.shape[0] + 1),
                    colorscale="Viridis",
                    showscale=False,  # No colorbar
                    zsmooth="best",
                    customdata=raw,
                    hovertemplate=(
                        "x=%{x}<br>"
                        "y=%{y}<br>"
                        "Normalised Intensity=%{z:.0%}<br>"  # Show rounded percentage 0.1 = 10%
                        "Absolute Intensity=%{customdata:.0f} AU<br>"
                        "<extra></extra>"  # hide trace info hoverbox
                    ),
                ),
                row=row,
                col=col,
            )
            # Add centering cross
            add_center_cross_plotly(
                fig,
                x_shape=z.shape[1],
                y_shape=z.shape[0],
                row=row,
                col=col,
                length=0.5,
                as_x=False,
            )
        # Add the difference panel      --------------
        # Get the plot y location for the colorbar
        yaxis = "yaxis" if row == 1 else f"yaxis{row * 3}"
        diff_domain = fig.layout[yaxis].domain

        fig.add_trace(
            go.Heatmap(
                z=diff,
                x=np.arange(1, diff.shape[1] + 1),
                y=np.arange(1, diff.shape[0] + 1),
                colorscale="RdBu",  # Red -> Blue
                # Adjust color range and show heatmap
                zmin=-100,
                zmax=100,
                colorbar={
                    "title": {
                        "text": "Difference [%]",
                        "side": "right",
                    },
                    # Position relative to whole figure
                    "x": 1.02,
                    "xanchor": "left",
                    "xpad": 0,
                    "yref": "paper",
                    "y": (diff_domain[0] + diff_domain[1])
                    / 2,  # middle of the row
                    "yanchor": "middle",
                    "len": (diff_domain[1] - diff_domain[0])
                    * 0.8,  # 80% of the row height
                    "thickness": 15,  # Default = 30 (bar-width)
                },
                reversescale=True,  # Blue -> Red
                zsmooth="best",
                hovertemplate=(
                    "x=%{x}<br>"
                    "y=%{y}<br>"
                    "Normalised Intensity=%{z:.0f}%<br>"
                    "<extra></extra>"  # hide trace info hoverbox
                ),
            ),
            row=row,
            col=3,
        )
        # Add centering cross
        add_center_cross_plotly(
            fig,
            x_shape=diff.shape[1],
            y_shape=diff.shape[0],
            row=row,
            col=3,
            length=0.5,
            color="black",
            as_x=False,
        )
        # Add an outline to the Difference plot
        fig.add_shape(
            type="rect",
            xref=f"x{3 * row}",  # Refers to the data plot
            yref=f"y{3 * row}",
            x0=0.5,
            x1=diff.shape[1] + 0.5,
            y0=0.5,
            y1=diff.shape[0] + 0.5,
            line={"color": "black", "width": 1},
            fillcolor="rgba(0,0,0,0)",  # transparent
            layer="above",
        )
    # Plot title & layout           ##########################################
    mic = input.microscope()
    obj = input.objective()
    obj = get_nice_objective_name(objective_df, obj)
    info = input.info()
    fig.update_layout(
        title={
            "text": f"Field Uniformity: {mic} {obj} ({info})",
            "yref": "container",  # the full canvas
            "pad": {
                "b": 0,
                "l": 0,
                "r": 0,
                "t": 10,
            },  # Give a little space to top
            "y": 1,  # at the top
            "yanchor": "top",
            "x": 0.5,
            "xanchor": "center",
            "font": {"size": 18},
        },
        plot_bgcolor="white",
        margin={
            # "autoexpand": False, # Default True, needed for colorbar
            "l": 25,
            "r": 0,
            "t": 70,  # min. title font + title top pad (empiric, 60 is not good anymore)
            "b": 0,
        },
        autosize=True,
    )
    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        showticklabels=False,
        constrain="domain",
    )
    fig.update_yaxes(
        showgrid=False,
        zeroline=False,
        showticklabels=False,
        autorange="reversed",
    )
    # Ensure square plots
    for row in range(1, len(common_chs) + 1):
        for col in range(1, 4):
            subplot = fig.get_subplot(row=row, col=col)
            ax_id = subplot.xaxis.plotly_name.replace("axis", "")
            fig.update_yaxes(row=row, col=col, scaleanchor=ax_id, scaleratio=1)

    # Add subplot tiltes            ##########################################
    for i, title in enumerate([date1, date2, "Difference"], start=1):
        if i == 1:
            panel = ""
        else:
            panel = i
        fig.add_annotation(
            text=title,
            xref=f"x{panel} domain",  # relative to panel's domain
            x=0.5,  # centered horizontally
            xanchor="center",
            yref="paper",  # ref = paper, works well with y=1 and anchor=bottom
            y=1,
            yanchor="bottom",
            # yshift=10,  # small pixel offset (- to shift text down; + up)
            showarrow=False,
            font={"size": 18},  # match default subplot title size if needed
        )
    # Add row title (date)
    for row, ch in enumerate(common_chs, start=1):
        if row == 1:
            domain = ""
        else:
            domain = 1 + (row - 1) * 3  # since 3 panels per row
        fig.add_annotation(
            text=ch,
            xref="x domain",  # relative to the first panel
            yref=f"y{domain} domain",  # relative to the first panel
            x=0,
            y=0.5,
            xanchor="right",
            yanchor="middle",
            showarrow=False,
            font={"size": 18},
            textangle=-90,
        )
    return fig, len(common_chs)


@reactive.calc
def plot_uniformity_2_measurements_mpl():
    """
    Create heatmap like plots for the Field uniformity between 2 dates.

    FIXME to be deprecated -> replace with plotly plots

    For all common channels. I.e.:
    DAPI | date1 | date2 | diff
    488  | date1 | date2 | diff
    ...

    :return: matplotlib plot
    """
    # Get date selections
    date1 = input.uni_date_selector_1()
    date2 = input.uni_date_selector_2()
    omero_data = get_omero_data()
    if date1 is None or date2 is None or omero_data is None:
        return no_data_seaborn()

    # Check available channels for the dates
    channels1 = omero_data.get_channel_names(date1)
    channels2 = omero_data.get_channel_names(date2)
    common_chs = sorted(set(channels1).intersection(channels2))
    if len(common_chs) == 0:
        return no_data_seaborn("No common channels between the 2 dates!")

    # Get the data (convert unidata for heatmap)
    uni_data = omero_data.get_uniformity()
    df_1 = omero_data.get_heat_map_dataframe(date=date1, data_dict=uni_data)
    df_2 = omero_data.get_heat_map_dataframe(date=date2, data_dict=uni_data)

    # Create figure (4 rows, last one for the scale bar)
    fig, axes = plt.subplots(
        nrows=len(common_chs),
        ncols=4,
        figsize=(12, 4 * len(common_chs)),
        gridspec_kw={"width_ratios": [1, 1, 1, 0.2]},
    )
    # Create figure: one channel per row
    for row, channel in enumerate(common_chs):
        # Pivot the dfs for given channel (-> XY-table)
        df1 = df_1.pivot(index="Y", columns="X", values=channel)
        df2 = df_2.pivot(index="Y", columns="X", values=channel)
        # Normalise the values (individually for each df)
        df1 = normalize_percentile(df1).to_numpy()
        df2 = normalize_percentile(df2).to_numpy()
        # Create an image of the difference of the 2 (in %)
        # FIXME not 100% correct since normalisation over percentile
        diff = (df1 - df2) * 100

        # Interpolation = bicubic for smooth interpolation
        axes[row][0].imshow(
            df1, interpolation="bicubic", origin="upper", cmap="viridis"
        )
        axes[row][1].imshow(
            df2, interpolation="bicubic", origin="upper", cmap="viridis"
        )

        # Add channel title to the left
        # axes[row][0].set_title(channel, rotation="vertical", x=-0.05, y=0.5)
        axes[row][0].text(
            -0.05,
            0.5,
            channel,
            rotation="vertical",
            transform=axes[row][0].transAxes,
            va="center",
            ha="center",
            fontsize=12,
        )

        # Add the difference plot with colors blue>white>red (always show values -100 to + 100)
        diff_img = axes[row][2].imshow(
            diff,
            interpolation="bicubic",
            origin="upper",
            cmap="bwr",
            vmin=-100,
            vmax=100,
        )
        # Add color bar for the difference plot
        # Can't make it look better than that. Depends on the window size...
        cbar = fig.colorbar(diff_img, ax=axes[row][3])
        cbar.set_label("Difference [%]")

    # Adjust titles
    axes[0][0].set_title(f"{date1}")
    axes[0][1].set_title(f"{date2}")
    axes[0][2].set_title("Difference")

    # Hide the frames / ticks except for the difference plot
    for row in axes:
        for i, ax in enumerate(row):
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
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    return fig


@reactive.calc
def set_card_height_uni_2date_comparison() -> str:
    """
    Calculate card display height based on plot's number of rows and plot width.

    For Uniformity plot that compares 2 dates.
    Basically sets the card height = width / (3 cols) * n rows.
    (minus a fixed value = 50)

    :return: str, e.g. 1000px
    """
    _, rows = plot_uniformity_2_measurements()
    width = get_uniformity_2dates_plot_width()
    row_height = width // 3 * rows - 50
    uni_2_dates_card_height.set(f"{row_height}px")
    uni_channel_compare_card_height.set(f"{row_height}px")
    # print("Plot width = ", width)
    # print(f"Card height should be = {row_height}px")
    return f"{row_height}px"


@reactive.calc
def set_card_height_uni_2channel_comparison() -> str:
    """
    Calculate card display height based on plot's number of rows and plot width.

    For Uniformity plot that compares 2 channels.
    Basically sets the card height = width / (3 cols) for one row
    (minus a fixed value = 50)

    :return: str, e.g. 1000px
    """
    width = get_uniformity_2channels_plot_width()
    row_height = width // 3 - 50
    uni_channel_compare_card_height.set(f"{row_height}px")
    # print("Plot width = ", width)
    # print(f"Card height should be = {row_height}px")
    return f"{row_height}px"


@reactive.calc
def get_uniformity_2dates_plot_width() -> Union[int, float]:
    """Get the plot width in pixels for Uniformity date comparison."""
    width = session.clientdata.output_width("plot_field_uniformity")
    if width is None:
        # Set an arbitrary width
        width = 800
    return width


@reactive.calc
def get_uniformity_2channels_plot_width() -> Union[int, float]:
    """Get the plot width in pixels for Uniformity channel comparison."""
    width = session.clientdata.output_width(
        "plot_field_uniformity_between_channels"
    )
    if width is None:
        # Set an arbitrary width
        width = 800
    return width


@reactive.calc
def set_card_height_uni_2_dates_mpl() -> str:
    """
    Calculate card display height based on plot size.

    FIXME DEPRECATED (old version for mpl plots)

    Tries to set 400px height per row (channel).
    FIXME: this is not optimal, since it should be in relation
        to the window width. But it is not really possible to get it...

    :return: str, e.g. 1000px (but stays unused I guess)
        400px * number of figure rows
    """
    fig = plot_uniformity_2_measurements()

    # Height is to be set 4x number of rows
    _w, h = fig.get_size_inches()

    # Empirically set min row height (in pixels)
    row_height = 400
    row_height = row_height * h // 4
    # print(f"Row height set to: {row_height}px")
    uni_2_dates_card_height.set(f"{row_height}px")
    return f"{row_height}px"


@reactive.calc
def create_uniformity_plot():
    """
    Create a heat-map like plot for the Filed Uniformity between 2 dates.

    # FIXME Deprecated: replaced by plot_uniformity_2_measurements()

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
def filter_avg_unifomrmity_by_date() -> pd.DataFrame:
    """
    Filter the average uniformity dataframe by date range.

    Gets the dataframe from the OMERO data, then filters
    out the rows, that are not in the date range selector.
    """
    date_range = input.uni_date_range()
    data = get_omero_data()
    if data is None:
        return pd.DataFrame()
    df = data.get_uniformity_over_time_melt().copy()
    date_min = int(date_range[0].strftime("%Y%m%d"))
    date_max = int(date_range[1].strftime("%Y%m%d"))

    # Get the date column in format YYYYmmdd as integer
    date_col = df["Date"].astype(str).str.extract(r"(\d{8})")[0]
    date_col = date_col.astype(int)
    # Remove the rows which are not within the date range
    df = df[(date_col >= date_min) & (date_col <= date_max)].reset_index(
        drop=True
    )
    return df


@reactive.calc
def filter_avg_distortion_by_date() -> pd.DataFrame:
    """
    Filter the average uniformity dataframe by date range.

    Gets the dataframe from the OMERO data, then filters
    out the rows, that are not in the date range selector.
    """
    date_range = input.dist_date_range()
    data = get_omero_data()
    if data is None:
        return pd.DataFrame()
    df = data.get_distortion_over_time_melt().copy()
    date_min = int(date_range[0].strftime("%Y%m%d"))
    date_max = int(date_range[1].strftime("%Y%m%d"))

    # Get the date column in format YYYYmmdd as integer
    date_col = df["Date"].astype(str).str.extract(r"(\d{8})")[0]
    date_col = date_col.astype(int)
    # Remove the rows which are not within the date range
    df = df[(date_col >= date_min) & (date_col <= date_max)].reset_index(
        drop=True
    )
    return df


@reactive.calc
def get_common_distortion_channels() -> list[str]:
    """
    Get a list of common distortion channels (between 2 dates).

    Reacts on inputs uni_date_selector_1 & uni_date_selector_2
    Function is shortened compared to the uniformity analog (below).

    :return: list[str] of channels or empty list
    """
    # Get the date inputs
    date1 = input.dist_date_selector_1()
    date2 = input.dist_date_selector_2()
    if None in [date1, date2]:
        return []
    # Get the OMERO data
    data = get_omero_data()
    if data is None:
        return []

    channels1 = data.get_channel_names(date1)
    channels2 = data.get_channel_names(date2)
    # Filter common channels between 2 dates
    common_chs = list(set(channels1).intersection(channels2))
    if len(common_chs) != len(channels1) or len(common_chs) != len(channels2):
        ui.notification_show(
            "Some distortion channels are not available for both dates!",
            type="warning",
            id="dist_ch_warn",
        )
    return common_chs


@reactive.calc
def get_common_uniformity_channels() -> list[str]:
    """
    Get a list of common uniformity channels (between 2 dates).

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
    # Make sure that there are only dates (keys) with dataframes
    uni_tables = {
        # Key must be cast to str
        str(k): v
        for k, v in data.get_uniformity().items()
        if v is not None
    }
    # Get channel names for date 1 & 2
    date1_chs = [
        x for x in uni_tables.get(date1).columns if x not in default_cols
    ]
    date2_chs = [
        x for x in uni_tables.get(date2).columns if x not in default_cols
    ]
    # Get the common channels
    common_chs = list(set(date1_chs).intersection(date2_chs))
    # Warn if some channels are not available for both dates
    if len(common_chs) != len(date1_chs) or len(common_chs) != len(date2_chs):
        ui.notification_show(
            "Some uniformity channels are not available for both dates!",
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
    df = df.dropna(axis="columns", how="all")
    # Make sure that headers are all str
    df.columns = [str(x) for x in df.columns]

    # Create and load data
    data = FieldData(df, retrieve_omero=True)

    # Report possible errors (other than the ones below...) with the list data.problems
    if len(data.problems) > 0:
        msg = ["There were some problems while loading the data:"]
        for i in data.problems:
            msg.append(" | ")
            msg.append(i)
        ui.notification_show("".join(msg), id="data_problems", type="error")

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


# Reactive functions - UI           ------------------------------------------


@reactive.effect
@reactive.event(get_omero_data)
def update_date_range_selector_for_averages():
    """Update date range selectors for avg. Uniformity & Distortion."""
    data = get_omero_data()
    if data is None:
        return

    # Get the dates
    uni_dates = data.get_uniformity().keys()
    dist_dates = data.get_distortion().keys()
    # Make sure that they are in YYYYmmdd format
    uni_dates = sorted([str(x)[:8] for x in uni_dates])
    dist_dates = sorted([str(x)[:8] for x in dist_dates])
    ui.update_date_range(
        "uni_date_range", start=uni_dates[0], end=uni_dates[-1]
    )
    ui.update_date_range(
        "dist_date_range", start=dist_dates[0], end=dist_dates[-1]
    )


@reactive.effect
@reactive.event(input.uni_single_date_selector)
def update_uni_channel_selectors():
    """Update the channel choices for Uniformity comparison."""
    data = get_omero_data()
    date = input.uni_single_date_selector()
    if data is None or date is None:
        channels = []
    else:
        channels = sorted(data.get_channel_names(date))

    ui.update_select(
        "uni_ch_selector1",
        choices=channels,
        selected=None if len(channels) == 0 else channels[0],
    )
    ui.update_select(
        "uni_ch_selector2",
        choices=channels,
        selected=None if len(channels) == 0 else channels[-1],
    )


# TODO FIXME - not needed
# @reactive.effect
# @reactive.event(input.dist_date_selector_1, input.dist_date_selector_2)
# def update_dist_channel_selector():
#     """Update the channel choices for the Distortion plot."""
#     channels = sorted(get_common_distortion_channels())
#     dist_ch_selector = ui.update_select(
#         "dist_ch_selector", choices=channels
#     )


@reactive.effect
@reactive.event(get_omero_data)
def update_distortion_dates():
    """
    Update distortion date selectors on OMERO data changes.

    Sets date selectors, to compare first and last date initially.
    """
    data = get_omero_data()
    if data is None:
        choices = []
    else:
        choices = data.get_distortion().keys()
        choices = list(choices)
    ui.update_select(
        "dist_date_selector_1",
        choices=choices,
        selected=None if len(choices) == 0 else choices[0],
    )
    ui.update_select(
        "dist_date_selector_2",
        choices=choices,
        selected=None if len(choices) == 0 else choices[-1],
    )


@reactive.effect
@reactive.event(input.dist_date_selector_1)
def update_distortion_channels_on_date_1():
    """
    Update distortion channel selection on date 1 changes.

    Matches the channel selection between the 2 dates if possible.
    """
    date1 = input.dist_date_selector_1()
    date2 = input.dist_date_selector_2()
    if date1 is None or date2 is None:
        ui.update_select("dist_ch_selector1", choices=[])
        ui.update_select("dist_ch_selector2", choices=[])
        return

    channels1 = get_omero_data().get_channel_names(date1)
    channels2 = get_omero_data().get_channel_names(date2)
    ui.update_select(
        "dist_ch_selector1", choices=channels1, selected=channels1[0]
    )
    ui.update_select(
        "dist_ch_selector2",
        choices=channels2,
        selected=channels1[0] if channels1[0] in channels2 else channels2[0],
    )


@reactive.effect
@reactive.event(input.dist_date_selector_2)
def update_distortion_channels_on_date_2():
    """
    Update distortion channel selection on date 2 changes.

    Matches date 1 channel selection if possible
    """
    date2 = input.dist_date_selector_2()
    if date2 is None:
        ui.update_select("dist_ch_selector2", choices=[])
        return

    channels2 = get_omero_data().get_channel_names(date2)
    selected_ch1 = input.dist_ch_selector1()
    if selected_ch1 is None:
        select_ch2 = None
    elif selected_ch1 in channels2:
        select_ch2 = selected_ch1
    else:
        select_ch2 = channels2[0]
    ui.update_select(
        "dist_ch_selector2", choices=channels2, selected=select_ch2
    )


# UI selectors                      ------------------------------------------

# Distortion channel and date selecotrs
dist_date_selector_1 = ui.input_select(
    "dist_date_selector_1",
    "Select a first date",
    choices=[],
)
dist_date_selector_2 = ui.input_select(
    "dist_date_selector_2",
    "Select a second date",
    choices=[],
)
dist_ch_selector1 = ui.input_select(
    "dist_ch_selector1", "Channel for first date (reference)", choices=[]
)
dist_ch_selector2 = ui.input_select(
    "dist_ch_selector2", "Channel for second date", choices=[]
)

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
