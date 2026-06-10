import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import seaborn as sns
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_widget

from metroloshiny.utils.common_utils import (
    create_css_color_dict,
    set_local_file,
)
from metroloshiny.utils.dataframe_utils import (
    filter_by_column_value,
    filter_by_date_range,
    get_power_over_time_data,
    keep_non_nan_rows,
    parse_dates,
)
from metroloshiny.utils.read_file import (
    get_sheet,
    load_doc,
)

# Load Data
use_dev_local_file = set_local_file()
sheet_doc = load_doc(dev_local_file=use_dev_local_file)
wsheet_psf, dataframe = get_sheet(
    sheet_doc, "Power", dev_local_file=use_dev_local_file
)

# FIXME: on line 466 - not sure how: UserWarning: Ignoring `palette` because no `hue` variable has been assigned.

# Global variable       ------------------------------------------------------

# Reactive & general variables      ------------------------------------------
sites = np.unique(np.asarray(dataframe["Site"]))
light_kinds = list(dataframe.columns[4:6])  # Laser or LED
# Contains filtered dataframe by sidebar selection except line & power
df_data = reactive.value(None)


# Create UI         ----------------------------------------------------------
ui.page_opts(title="Metrology: Power")
with ui.nav_panel(title="Light Source Power"):
    # Sidebar          -------------------------------------------------------
    with ui.layout_sidebar():
        with ui.sidebar():
            ui.input_select("site", "Select the site", choices=list(sites))
            ui.input_select("microscope", "Select a microscope", choices=[])
            ui.input_select("objective", "Select an objective", choices=[])
            ui.input_select("info", "Filter by info column", choices=[])
            ui.input_select("kind", "Select light source kind", choices=[])
            ui.input_select("line", "Select a wavelength [nm]", choices=[])
            ui.input_select("power", "Select power [%]", choices=[])

        # Plot linearity        ----------------------------------------------
        with ui.navset_card_underline(title="Power linearity"):
            with ui.nav_panel(title="Plot"):

                @render.ui
                def show_single_date_selection():
                    """Show selection UI for picking a date."""
                    sds = ui.input_select(
                        "single_date_selection",
                        "Select a date",
                        choices=get_measurement_dates(),
                    )
                    return sds

                @render.plot
                def plot_power_linearity():
                    """Render the power linearity plot."""
                    df = create_power_linearity_table()
                    return create_power_linearity_plot(df)

            with ui.nav_panel(title="Table"):

                @render.data_frame
                def show_power_linearity():
                    """Show the filtered data table."""
                    return create_power_linearity_table()

        # Plot stability        ----------------------------------------------
        with ui.navset_card_underline(title="Power stability"):
            with ui.nav_panel(title="Plot"):

                @render.ui
                def show_date_range():
                    """Show date range selection UI element."""
                    dr = ui.input_date_range(
                        "date_range_selection",
                        "Select a date range",
                        start=None,
                        end=None,
                        format="yyyymmdd",
                    )
                    return dr

                # @render.plot
                @render_widget
                def plot_power_stability():
                    """Render the power stability plot."""
                    df = create_power_stability_table()
                    # Check line and power selections, and df has data
                    line = input.line()
                    prct = input.power()
                    if None in [line, prct] or len(df.columns) < 3:
                        # Show no plot if line or power is None
                        return create_power_stability_plot(pd.DataFrame())
                    return create_power_stability_plot(df)

            with ui.nav_panel(title="Table"):

                @render.data_frame
                def show_power_stability():
                    """Show the filtered data table."""
                    return create_power_stability_table()


# Reactive functions        --------------------------------------------------


@reactive.calc
@reactive.event(df_data, input.date_range_selection)
def create_power_stability_table() -> pd.DataFrame:
    """
    Create a dataframe for power stability.

    Sorts the date columns and filters dates by date range.
    Does not pivot the table.

    :return: pd.DataFrame
    """
    df = df_data.get()
    start_date = input.date_range_selection()[0]
    end_date = input.date_range_selection()[1]
    # Return empty df, if data/selection not ready
    if None in [start_date, end_date] or df is None or df.empty:
        return pd.DataFrame()

    # Sort the dates
    df = pd.DataFrame(df.copy())
    sorted_headers = list(df.columns[:2])
    for d in sorted(df.columns[2:]):
        sorted_headers.append(d)
    df = df.reindex(sorted_headers, axis=1)

    # Remove date columns outside selected date range
    start_date = input.date_range_selection()[0].strftime("%Y%m%d")
    end_date = input.date_range_selection()[1].strftime("%Y%m%d")
    df = filter_by_date_range(df=df, min=start_date, max=end_date)
    return df


@reactive.effect
@reactive.event(df_data)
def set_date_range():
    """Update the date range selection."""
    df = df_data.get()
    # Set start and end to None, if no data or empty dataframe
    if df is None or df.empty:
        ui.update_date_range("date_range_selection", start=None, end=None)
        return
    # Parse the dates (on headers except first 2)
    d = parse_dates(list(df.columns[2:]))
    # Update the UI selection
    ui.update_date_range("date_range_selection", start=d[0], end=d[-1])


@reactive.calc
@reactive.event(df_data, input.single_date_selection)
def create_power_linearity_table() -> pd.DataFrame:
    """
    Create a power linearity table.

    Removes not-selected date columns.

    :return: pd.DataFrame
    """
    df = df_data.get()
    date = input.single_date_selection()
    # Return empty DataFrame if None (or empty)
    if df is None or date is None:
        return pd.DataFrame()
    if df.empty:
        return df
    df = pd.DataFrame(df.copy())  # ensure type for coding & work with copy
    # Fix when swapping microscope, when df probably not ready yet
    if date not in list(df.columns):
        return pd.DataFrame()
    # Filter df by the selected line
    if input.line() != "All":
        df = filter_by_column_value(
            df, input.kind(), float(input.line()), drop_column=False
        )

    # Remove measurement columns, except the need one...
    df = df[[input.kind(), "Power [%]", date]]
    return df


@reactive.calc
@reactive.event(df_data)
def get_measurement_dates() -> list[str]:
    """
    Get a list of dates where measurements were done.

    Keeps all power rows in the DataFrame, but filters by wavelength.

    :return: list[str], dates to select in format as table (YYYYmmdd)
    """
    df = df_data.get()
    if df is None or input.kind() not in df.columns:
        return []
    if input.line() != "All":
        df = filter_by_column_value(
            df, input.kind(), float(input.line()), drop_column=False
        )
    return list(df.columns[2:])


@reactive.effect
@reactive.event(
    input.power,
    input.line,
    input.kind,
    input.info,
    input.objective,
    input.microscope,
    input.site,
)
def create_filtered_dataframe():
    """Filter the data by sidebar selections, except wavelength and power."""
    # Check that all selections are valid (not None)
    site_ = input.site()
    mic_ = input.microscope()
    obj_ = input.objective()
    info_ = input.info()
    if None in [site_, mic_, obj_, info_]:
        df_data.set(None)
        return
    # Filter the dataframe and set the reactive value (work with df copy)
    df = filter_by_column_value(dataframe.copy(), "Site", input.site())
    df = filter_by_column_value(df, "Microscope", input.microscope())
    df = filter_by_column_value(df, "Objective", input.objective())
    df = filter_by_column_value(df, "Info", input.info())
    # Drop the light source kind which is not selected
    for k in light_kinds:
        if input.kind() != k:
            df = df.drop(columns=[k])
    # Sanity checks
    if input.line() is None:
        df_data.set(None)
        return
    # Filter on selected power
    if input.power() is None:
        df_data.set(None)
        return
    # (Do not filter the df by wavelength or power yet)
    # Drop all nan columns
    df = df.dropna(axis=1, how="all")
    df_data.set(df)


@reactive.effect
@reactive.event(input.site)
def update_microscope_choices():
    """Update microscope choices based on site selection."""
    # Filter the data frame (always the original) and
    # set the reactive result dataframe
    df = filter_by_column_value(dataframe.copy(), "Site", input.site())
    # Get a list of microscopes and set the reactive result
    m_filtered = np.unique(np.asarray(df["Microscope"]))
    # Update the ui selection (using the reactive variable)
    ui.update_select("microscope", choices=list(m_filtered))


@reactive.effect
@reactive.event(input.microscope, input.site)
def update_objective_choices():
    """Update objective choices based on microscope selection."""
    # Filter original df from start
    df = filter_by_column_value(dataframe.copy(), "Site", input.site())
    df = filter_by_column_value(df, "Microscope", input.microscope())
    # Get a list of unique objective choices
    o = np.unique(np.asarray(df["Objective"]))
    # Update the ui selection
    ui.update_select("objective", choices=list(o))


@reactive.effect
@reactive.event(input.objective, input.microscope, input.site)
def update_info_choices():
    """Update info choices based on microscope & objective selection."""
    # Filter original df from start
    df = filter_by_column_value(dataframe.copy(), "Site", input.site())
    df = filter_by_column_value(df, "Microscope", input.microscope())
    df = filter_by_column_value(df, "Objective", input.objective())
    # Get a list of unique info items
    i = np.unique(np.asarray(df["Info"]))
    # Update the ui selection
    ui.update_select("info", choices=list(i))


@reactive.effect
@reactive.event(input.info, input.objective, input.microscope, input.site)
def update_kind_selection():
    """Update light source kind choices available."""
    # Filter original df from start
    df = filter_by_column_value(dataframe.copy(), "Site", input.site())
    df = filter_by_column_value(df, "Microscope", input.microscope())
    df = filter_by_column_value(df, "Objective", input.objective())
    df = filter_by_column_value(df, "Info", input.info())
    # Select the light source kind that has values
    kinds = []
    for k in light_kinds:
        if len(df.dropna(subset=[k])) > 0:
            kinds.append(k)
    ui.update_select("kind", choices=kinds)


@reactive.effect
@reactive.event(
    input.kind, input.info, input.objective, input.microscope, input.site
)
def update_wavelength_choices():
    """Update available wavelength selections."""
    # Filter original df from start
    df = filter_by_column_value(dataframe.copy(), "Site", input.site())
    df = filter_by_column_value(df, "Microscope", input.microscope())
    df = filter_by_column_value(df, "Objective", input.objective())
    df = filter_by_column_value(df, "Info", input.info())
    if input.kind() is None:
        return
    df = keep_non_nan_rows(df, column_name=input.kind())
    # Get a list of unique wavelengths
    w = np.unique(np.asarray(df[input.kind()]))
    if len(w) == 0:
        ui.update_select("line", choices=[])
        return
    # Append entry for "All"
    w = [str(i) for i in w]
    w.append("All")
    ui.update_select("line", choices=w)


@reactive.effect
@reactive.event(
    input.line,
    input.kind,
    input.info,
    input.objective,
    input.microscope,
    input.site,
)
def update_power_choices():
    """Update available wavelength selections."""
    # Filter original df from start
    df = filter_by_column_value(dataframe.copy(), "Site", input.site())
    df = filter_by_column_value(df, "Microscope", input.microscope())
    df = filter_by_column_value(df, "Objective", input.objective())
    df = filter_by_column_value(df, "Info", input.info())
    if input.kind() is None:
        return
    df = keep_non_nan_rows(df, column_name=input.kind())
    if input.line() is None:
        return
    if input.line() != "All":
        df = filter_by_column_value(df, input.kind(), float(input.line()))
    # Get a list of unique wavelengths
    p = np.unique(np.asarray(df["Power [%]"]))
    if len(p) == 0:
        ui.update_select("power", choices=[])
        return
    # Append entry for "All"
    p = [str(i) for i in p]
    p.append("All")
    ui.update_select("power", choices=p)


# General functions         --------------------------------------------------


def create_power_linearity_plot(df: pd.DataFrame):  # -> sns.lineplot:
    """
    Create the power linearty line plot.

    :param df: pd.DataFrame, with 3 columns: [Line, Power, Date]

    :return: sns.lineplot
    """
    fig, ax = plt.subplots()
    if df.empty:
        # Show empty plot
        ax.text(0.5, 0.5, "No data to visualise!", ha="center", va="center")
        ax.set_axis_off()
        return fig

    # Work with a copy of the dataframe
    df = df.copy()
    # Merge the first two columns
    df["Line [nm] @ [%]"] = (
        df[df.columns[0]].astype(int).astype(str)
        + " @ "
        + df[df.columns[1]].astype(int).astype(str)
    )
    # Reorder columns (new col to the beginning, keep all cols)
    cols = list(df)
    cols.insert(0, cols.pop(cols.index(cols[-1])))
    df = df.loc[:, cols]
    # Pivot the table
    df = df.melt(
        id_vars=df.columns[:3],
        var_name="Date",
        value_name="mW",
    )

    # Create the plot
    plot = sns.lineplot(
        data=df,
        markers=True,
        style=df.columns[1],  # ensure markers
        dashes=False,  # keep solid lines
        x=df.columns[2],  # Power
        y=df.columns[4],  # Date
        hue=df.columns[1],  # Line
        palette="turbo",
        hue_norm=(380, 700),
        legend="full",  # ensure precise wavelength value
    )
    # Move the legend to the right of the plot
    legend = ax.get_legend()
    legend.set_bbox_to_anchor((1.05, 1))
    legend.set_loc("upper left")
    fig.tight_layout()
    return plot


def create_power_stability_plot(df: pd.DataFrame):  # -> sns.lineplot:
    """
    Create the power stability line plot.

    :param df: pd.DataFrame, with columns: [Line, Power]
        and multiple Date columns

    :return: sns.lineplot
    """
    # Do not show a plot if both power and line are set to "All"
    line = input.line()
    prct = input.power()
    if line == "All" and prct == "All":
        return no_data_fig("Cannot show all lines at all powers!")
    # Show not plot if there is no data
    if df.empty:
        return no_data_fig()

    # Merge line/power columns and pivot the table
    line = None if line == "All" else float(line)
    prct = None if prct == "All" else float(prct)
    df = get_power_over_time_data(df=df, line=line, power_prct=prct)

    # Create the plot #####################################
    # Group the plot by power or line and colors accordingly
    # plot = sns.lineplot(
    #     data=df,
    #     x="Date",
    #     y="mW",
    #     markers=True,
    #     # ensure markers
    #     style=df.columns[2] if input.power() == "All" else df.columns[1],
    #     # keep solid lines
    #     dashes=False,
    #     # group by "Power [%]" if prct=all, else by "Line"
    #     hue=df.columns[2] if input.power() == "All" else df.columns[1],
    #     palette="turbo",
    #     # adjust line colors
    #     hue_norm=(0, 100) if input.power() == "All" else (380, 700),
    #     # ensure precise line values
    #     legend="full",
    # )

    # # Move legend to the right of the plot
    # legend = ax.get_legend()
    # if legend is not None:
    #     legend.set_bbox_to_anchor((1.05, 1))
    #     legend.set_loc("upper left")
    # # X-labels adjustments
    # plt.xticks(rotation=45, ha="right")  # rotate ticks
    # ticks = ax.get_xticks()
    # new_ticks = np.linspace(0, len(ticks) - 1, min(10, len(ticks)), dtype=int)
    # ax.set_xticks(new_ticks)
    # ax.set_xlabel("")
    # fig.tight_layout()
    # return plot

    # Create a plot with plotly
    group_col = df.columns[2] if input.power() == "All" else df.columns[1]
    wavelengths = np.unique(np.asarray(df[df.columns[1]]))
    color_map = (
        {} if input.power() == "All" else create_css_color_dict(wavelengths)
    )

    plot = px.line(
        df,
        x="Date",
        y="mW",
        color=group_col,
        line_group=group_col,
        line_dash=group_col,  # gives different dashes per group
        markers=True,
        hover_data={
            "Date": True,
            "mW": ":.3f",
            group_col: True,
        },
        color_discrete_map=color_map,
    )

    # Move legend to the right
    plot.update_layout(
        template="simple_white",
        legend={
            "yanchor": "top",
            "y": 1,
            "xanchor": "left",
            "x": 1.02,
        },
        margin={"r": 200},
    )

    # Rotate x-axis labels
    plot.update_xaxes(
        tickangle=45,
        # Reduce number of displayed ticks
        nticks=10,
        showgrid=False,
        title="",
    )
    plot.update_yaxes(showgrid=True, gridcolor="lightgrey")

    # Custom hover template
    plot.update_traces(
        hovertemplate="<b>%{fullData.name}</b><br>"
        "Date: %{x}<br>"
        "mW: %{y:.3f}<extra></extra>"
    )
    return plot


def no_data_fig_simple(message: str = "No data to visualise!"):
    """
    Show a no data plot with matplotlib.

    :param message: str, to display in the plot.

    :return: matplot fig
    """
    fig, ax = plt.subplots()
    ax.text(0.5, 0.5, message, ha="center", va="center")
    ax.set_axis_off()
    return fig


def no_data_fig(message: str = "No data to visualise!"):
    """
    Show a no data plot with plotly.

    :param message: str, to display in the plot.

    :return: plotly.plot
    """
    fig = px.line(pd.DataFrame({"x": [], "y": []}), x="x", y="y")
    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"size": 20, "color": "gray"},
    )
    fig.update_layout(template="simple_white", showlegend=False)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig
