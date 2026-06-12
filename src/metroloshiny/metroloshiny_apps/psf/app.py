# import seaborn as sns
import warnings
from typing import Optional, Union

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
from shiny import reactive
from shiny.express import input, render, ui
from shinywidgets import render_widget

from metroloshiny.utils.common_utils import (
    get_objective_mag,
    get_objective_na,
    get_objective_ri,
    get_version,
    set_local_file,
    theo_fwhm_2photon,
    theo_fwhm_pointscanner,
    theo_fwhm_spinning,
    theo_fwhm_widefield,
)
from metroloshiny.utils.dataframe_utils import (
    filter_by_column_value,
    filter_by_date_range,
    parse_dates,
)
from metroloshiny.utils.read_file import get_sheet, load_doc

# TODO Add plot for single date chromatic shift, that shows shift in XY
# TODO change channel naming restriction (try get names from OMERO channels), & calibrate XYZ shift

# Load Data
use_dev_local_file = set_local_file(True)
sheet_doc = load_doc(dev_local_file=use_dev_local_file)
wsheet_psf, dataframe = get_sheet(
    sheet_doc, "PSF", dev_local_file=use_dev_local_file
)
# Load objectives dataframe conditionally
objective_df = None
if dataframe["Objective"].str.startswith("ID").any():
    _, objective_df = get_sheet(
        sheet_doc, "Objectives", dev_local_file=use_dev_local_file
    )

# Global variable       ------------------------------------------------------
# highest PSF value in dataframe (reset after filtering by objective)
psf_max_val = reactive.value(dataframe[dataframe.columns[6:]].max().max())
sites = np.unique(np.asarray(dataframe["Site"]))

# Reactive variables              --------------------------------------------
# Contains data filtered by sidebar selections
df_data = reactive.value(None)
# Same as df_data but retains non-numeric values (i.e. Reference channel info)
df_ref = reactive.value(None)
# Remember choices for objectives (to create an objective_db table)
objective_choices = reactive.value(None)


# Create UI         ----------------------------------------------------------
ui.page_opts(title="Metrology: PSF", footer=f"Version {get_version()}")
with ui.nav_panel(title="PSF"):
    # Sidebar          -------------------------------------------------------
    with ui.layout_sidebar():
        with ui.sidebar():
            ui.input_select("site", "Select the site", choices=list(sites))
            ui.input_select("microscope", "Select a microscope", choices=[])
            ui.input_select("objective", "Select an objective", choices=[])
            ui.input_select("info", "Filter by info column", choices=[])

        # Selection card     -------------------------------------------------
        with ui.navset_card_underline(title="Plotting options"):
            with ui.nav_panel(title="Options"):
                # Add checkboxes & other as columns
                with ui.layout_column_wrap(
                    width=1 / 3, min_height="150px", max_height="2000px"
                ):

                    @render.ui
                    def render_channel_choices():
                        """Show channels and FWHM UI choices."""
                        ch_selection = ui.input_checkbox_group(
                            "ch_selection", "", choices={}
                        )
                        fwhm_selection = ui.input_checkbox_group(
                            "fwhm_selection", "", choices={}
                        )
                        date_range_selection = ui.input_date_range(
                            "date_range_selection",
                            "Select date range:",
                            start=None,
                            end=None,
                            format="yyyymmdd",
                        )
                        return (
                            "Select channels for plotting:",
                            ch_selection,
                            "FWHM to display:",
                            fwhm_selection,
                            date_range_selection,
                        )

                    @render.ui
                    def render_theoreticals():
                        """Show theoretical UI choices."""
                        ch_calc_selection = ui.input_select(
                            "ch_calc_selection", "", choices=[]
                        )
                        theoretical = ui.input_checkbox_group(
                            "theoretical",
                            "",
                            choices={"lateral": "Lateral", "axial": "Axial"},
                            selected=["lateral", "axial"],
                        )
                        return (
                            "Show theoretical values:",
                            ch_calc_selection,
                            theoretical,
                        )

                    @render.ui
                    def render_calculations():
                        """Show UI options to calculate theoretical values."""
                        mic_kind_selection = ui.input_select(
                            "mic_kind_selection",
                            "Microscope kind",
                            choices=[
                                "Widefield",
                                "Point Scanner",
                                "Spinning disk",
                                "2-Photon",
                            ],
                            selected="Widefield",
                        )
                        ex_selection = ui.input_numeric(
                            "ex_selection", "Excitation wavelength", value=520
                        )
                        na_selection = ui.input_numeric(
                            "na_selection", "NA", value=1.1
                        )
                        ri_selection = ui.input_numeric(
                            "ri_selection", "Refractive index", value=1.0
                        )
                        return (
                            "For theoretical calculation:",
                            mic_kind_selection,
                            ex_selection,
                            na_selection,
                            ri_selection,
                        )

            with ui.nav_panel(title="Objective information"):

                @render.text
                @reactive.event(objective_choices)
                def show_objective_table_info():
                    """Show info if no database objective available."""
                    oc = objective_choices.get()
                    if oc is None:
                        return ""
                    if any(s.startswith("ID") for s in oc):
                        return ""
                    else:
                        return "No objective information available."

                @render.data_frame
                def show_objective_table():
                    """Render available objective table."""
                    o_df, styles = get_objective_table()
                    return render.DataGrid(o_df, styles=styles)

        # PSF over time     --------------------------------------------------
        with ui.navset_card_underline(title="PSF over time"):
            with ui.nav_panel(title="Plot"):

                @render_widget
                def show_fwhm_plot():
                    _, df_plot = add_theoretical_fwhm()
                    return create_plot(
                        df_plot, y_range=[-10, psf_max_val.get()]
                    )

            with ui.nav_panel(title="Table"):

                @render.data_frame
                def show_fwhm_table():
                    df_table, _ = add_theoretical_fwhm()
                    return df_table

        # Shift over time     ------------------------------------------------
        with ui.navset_card_underline(title="Chromatic shift over time"):
            with ui.nav_panel(title="Plot"):

                @render.text
                def show_ref_channel():
                    _, ref_channel = check_shift_ref_ch()
                    return f"Reference channel: {ref_channel}"

                @render_widget
                def show_shift_plot():
                    _, df_plot = get_shift_data()
                    return create_plot(df_plot)

            with ui.nav_panel(title="Table"):

                @render.data_frame
                def show_shift_table():
                    df, _ = get_shift_data()
                    return df


# General functions         --------------------------------------------------


def create_plot(
    df: pd.DataFrame,
    y_label: Optional[str] = None,
    y_range: Optional[list[Union[int, float]]] = None,
):
    """
    Create a plotly plot from a dataframe.

    Expected are 5 columns, e.g.:
    "Channel FWHM", Channel, "FWHM", Date, "value"
    (From the original dataframe the first two columns combined make the first
    column, then the dataframe is pivoted with the melt function.)

    :param df: pd.DataFrame
    :param ylabel: str, if None (default), takes the last header of the df
    :param y_max: list[int], min/max values for the plot y-axis,
        if None, takes the absolute min/max of the dataframe values to plot.

    :return: plotly line plot
    """
    # Show no data figure if no data
    if df is None or df.empty:
        return no_data_fig()

    # Make sure that there is values to be displayed
    _df = df.dropna(subset=[df.columns[-1]])
    if _df.empty:
        return no_data_fig()

    # Set the y_label if it is None
    if y_label is None:
        y_label = df.columns[-1]

    # Check range and adjust it if necessary
    if y_range is None:
        abs_max = df[df.columns[-1]].abs().max() * 1.05
        y_range = [-abs_max, abs_max]
    else:
        cur_max = df[df.columns[-1]].max()
        input_max = y_range[1]
        y_max = cur_max if input_max < cur_max else input_max
        y_range = [y_range[0], y_max * 1.05]

    # Create the plot
    plot = px.line(
        df,
        x="Date",
        y=y_label,
        color=df.columns[0],
        line_group=df.columns[0],
        line_dash=df.columns[0],
        markers=True,
        hover_data={
            "Date": True,
            y_label: ":.0f",
            df.columns[0]: True,
        },
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
        yaxis_range=y_range,
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


def calculate_theoretical_values(
    kind: str, ex: Optional[float], na: Optional[float], ri: Optional[float]
) -> tuple[float, float]:
    """
    Calculate theoretical FWHM values.

    :param kind: str, one of: Widefield, Point Scanner, Spinning disk, 2-Photon
    :param ex: float, excitation wavelength
    :param na: float, NA
    :param ri: float, refractive index

    :return: tuple[float], (FWHM-lateral, FWHM-axial)
    """
    # Return (0, 0) if values are None or 0
    if ex is None or ex == 0:
        return (0, 0)
    if na is None or na == 0:
        return (0, 0)
    if ri is None or ri == 0:
        return (0, 0)
    if kind is None:
        return (0, 0)

    # Make sure that values are float
    try:
        ex = float(ex)
        na = float(na)
        ri = float(ri)
    except ValueError as err:
        raise ValueError(
            "One of the values is not a number. "
            f"Excitaiton={ex}, NA={na}, refractive index={ri}"
        ) from err
    # Calculate the values based on kind
    if kind == "Widefield":
        theo = theo_fwhm_widefield(ex, na, ri)
    elif kind == "Point Scanner":
        theo = theo_fwhm_pointscanner(ex, na, ri)
    elif kind == "Spinning disk":
        theo = theo_fwhm_spinning(ex, na, ri)
    elif kind == "2-Photon":
        theo = theo_fwhm_2photon(ex, na, ri)
    else:
        raise NotImplementedError(
            f"Calculation of FWHM for {kind} is not implemented."
        )
    # Check for complex numbers, and return 0s if so
    for i in theo:
        if not isinstance(i, float):
            return (0, 0)
    return theo


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


# Reactive functions        --------------------------------------------------


@reactive.calc
@reactive.event(df_data, objective_choices)
def get_objective_table() -> tuple[pd.DataFrame, list[dict]]:
    """
    Get the table about the objectives for the selected microscope.

    Only lists objectives that have been used (i.e. in the PSF dataframe)
    Highlight the selected objective.

    :return: pd.DataFrame
        DataFrame of available objectives
    :return: list[dict]]
        List of dict to be used to highlight row in DataGrid
    """
    # Make sure DF ready and selections valid
    if df_data.get() is None or df_data.get().empty:
        return pd.DataFrame(), []
    objective = input.objective()
    available = objective_choices.get()
    if objective is None or available is None:
        return pd.DataFrame(), []
    # Get a list of objectives that start with ID
    valid = [x for x in available if x.startswith("ID")]
    if len(valid) == 0:
        return pd.DataFrame(), []
    # Create dataframe subset from objective_db
    subset = objective_df.copy()
    subset = subset[subset["ID"].isin(available)]
    subset = subset.reset_index(drop=True)
    # Create a style to highlight the selection
    selected = subset[subset["ID"] == objective].index
    styles = [
        {
            # Rows are re-indexed (NOT df.index)
            "rows": list(selected),
            "style": {"background-color": "yellow", "font-weight": "bold"},
        }
    ]
    return subset, styles


@reactive.calc
@reactive.event(df_ref, input.date_range_selection)
def check_shift_ref_ch():
    """
    Identify the reference channel.

    Work on "unfiltered" dataframe to keep all channels in it.

    Reference-X/Y/Z information is lost already during loading of sheet.
    Hence, try to identify via NaN values...

    :return: tuple(bool, str):
        - bool, True if channel was identified
        - str, message to display in UI, can be channel name

    """
    df = df_ref.get()
    if df is None or df.empty:
        return False, ""

    df = pd.DataFrame(df)
    # Keep only "Shift" rows
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="Boolean Series key will be reindexed to match DataFrame index",
        )
        df = df[df["FWHM"].str.startswith("Shift")]

    if df.empty:
        return False, "No shift data"
    # Remove date columns outside selected date range
    start_date = input.date_range_selection()[0].strftime("%Y%m%d")
    end_date = input.date_range_selection()[1].strftime("%Y%m%d")
    df = filter_by_date_range(df=df, min=start_date, max=end_date)

    # Keep only rows which have NaN values (may have been text, or missing values)
    df_nan = df[df.isnull().any(axis=1)]
    ref_channel = np.unique(np.asarray(df_nan["Channel"]))
    if len(ref_channel) == 1:
        return True, ref_channel[0]
    elif len(ref_channel) == 0:
        return False, "Could not identify ref channel"
    else:
        ui.notification_show(
            "Shift reference channel could not be identified. "
            "Maybe due to: (1) change of reference channel over different measurements; "
            f"(2) missing measurements. Possible channels = {ref_channel}",
            type="warning",
        )
        return False, "ERROR: could not determine ref channel"


@reactive.calc
@reactive.event(
    df_data,
    input.theoretical,
    input.mic_kind_selection,
    input.ex_selection,
    input.na_selection,
    input.ri_selection,
    input.ch_selection,
    input.fwhm_selection,
    input.date_range_selection,
)
def add_theoretical_fwhm() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Add the theoretical FWHM to the dataframe.

    Triggers on card selections inputs AND df_data.

    Creates the final data to be plotted.

    :return: tuple(pd.DataFrame)
        - dataframe for table
        - dataframe for plotting (pivoted)
    """
    df = get_raw_fwhm_data()
    if df.empty:
        return df, df

    # Filter data by selected Channels and FWHM to display
    ch_sel = input.ch_selection()
    fwhm_sel = input.fwhm_selection()
    if len(ch_sel) != len(np.unique(np.asarray(df["Channel"]))):
        df = df[df["Channel"].isin(list(ch_sel))]
    if len(fwhm_sel) != len(np.unique(np.asarray(df["FWHM"]))):
        df = df[df["FWHM"].isin(list(fwhm_sel))]

    # Reset index the dataframe to avoid mistakes when adding new rows
    df = df.reset_index(drop=True)

    # Add theoretical values to the data
    theo_sel = input.theoretical()
    kind = input.mic_kind_selection()
    ex = input.ex_selection()
    na = input.na_selection()
    ri = input.ri_selection()
    values = calculate_theoretical_values(kind, ex, na, ri)
    for t in theo_sel:
        entry = [
            f"Theoretical {kind} " + str(input.ch_calc_selection()),
            t.capitalize(),
        ]
        while len(entry) < len(df.columns):
            if t == "lateral":
                entry.append(values[0])
            else:
                entry.append(values[1])
        df.loc[len(df)] = entry

    # Merge the Channel and FWHM columns (don't drop the original ones)
    plot_df = df.copy()
    plot_df["PSF"] = (
        df[df.columns[0]].astype(str) + " " + df[df.columns[1]].astype(str)
    )
    # Move the new last col to the beginning
    cols = list(plot_df)
    cols.insert(0, cols.pop(cols.index(cols[-1])))
    plot_df = plot_df.loc[:, cols]
    # Pivot the table
    plot_df = plot_df.melt(
        id_vars=plot_df.columns[:3], var_name="Date", value_name="nm"
    )
    return df, plot_df


@reactive.calc
@reactive.event(df_data, input.ch_selection, input.date_range_selection)
def get_shift_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Filter the dataframe for shift values.

    :return: tuple[pd.DataFrame]:
        - dataframe for table
        - dataframe for plotting (pivoted)
    """
    df = df_data.get()
    if df is None or df.empty:
        return pd.DataFrame(), pd.DataFrame()

    df = pd.DataFrame(df)
    # Remove date columns outside selected date range
    start_date = input.date_range_selection()[0].strftime("%Y%m%d")
    end_date = input.date_range_selection()[1].strftime("%Y%m%d")
    df = filter_by_date_range(df=df, min=start_date, max=end_date)

    # Remove non Shift rows
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="Boolean Series key will be reindexed to match DataFrame index",
        )
        df = df[df["FWHM"].str.startswith("Shift")]

    # Replace NaN values with 0 for reference channel
    do_replace, ref_name = check_shift_ref_ch()
    if do_replace:
        mask = df["Channel"] == ref_name
        df.loc[mask] = df.loc[mask].fillna(0)
        # Rename the channel name
        new_ref_name = ref_name + " ref."
        df.loc[mask, "Channel"] = new_ref_name

    # Filter data by selected Channels
    ch_sel = list(input.ch_selection())
    if ref_name in ch_sel:
        # Prevent from removing the reference
        ch_sel.append(new_ref_name)
    # if len(ch_sel) != len(np.unique(np.asarray(df["Channel"]))):
    df = df[df["Channel"].isin(list(ch_sel))]

    # Merge the Channel and FWHM columns (don't drop the original ones)
    plot_df = df.copy()
    plot_df["Shift"] = (
        df[df.columns[0]].astype(str) + " " + df[df.columns[1]].astype(str)
    )
    # Move the new last col to the beginning
    cols = list(plot_df)
    cols.insert(0, cols.pop(cols.index(cols[-1])))
    plot_df = plot_df.loc[:, cols]
    # Pivot the table
    plot_df = plot_df.melt(
        id_vars=plot_df.columns[:3], var_name="Date", value_name="voxels"
    )
    return df, plot_df


@reactive.calc
@reactive.event(df_data, input.date_range_selection)
def get_raw_fwhm_data() -> pd.DataFrame:
    """
    Filter the dataframe for FWHM values.

    Sets also the plotting UI selection choices.

    :return: pd.DataFrame
    """
    df = df_data.get()
    if df is None or df.empty:
        return pd.DataFrame()

    df = pd.DataFrame(df)
    # Remove date columns outside selected date range
    start_date = input.date_range_selection()[0].strftime("%Y%m%d")
    end_date = input.date_range_selection()[1].strftime("%Y%m%d")
    df = filter_by_date_range(df=df, min=start_date, max=end_date)

    # Remove non FWHM rows
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="Boolean Series key will be reindexed to match DataFrame index",
        )
        df = df[df["FWHM"].str.startswith("FWHM")]

    # Set the plotting option choices
    channels = np.unique(np.asarray(df["Channel"]))
    ch_dict = {ch: ch for ch in channels}
    ui.update_checkbox_group(
        "ch_selection", choices=ch_dict, selected=list(ch_dict.keys())
    )
    fwhms = np.unique(np.asarray(df["FWHM"]))
    fwhm_dict = {f: f for f in fwhms}
    ui.update_checkbox_group(
        "fwhm_selection", choices=fwhm_dict, selected=list(fwhm_dict.keys())
    )
    ui.update_select("ch_calc_selection", choices=list(channels))
    return df


@reactive.effect()
@reactive.event(df_data, input.ch_calc_selection)
def update_theoretical_calculation():
    """
    Update UI values for theoretical calculations.

    Based on the channel selection for the calculation.
    Also updates the NA and RI selections.
    """
    # Make sure that the dataframe and selections are valid
    if df_data.get() is None or df_data.get().empty:
        return
    cur = input.ch_calc_selection()
    if cur is None:
        return
    # Try to map a string input to a wavelength
    val = 488
    if cur == "DAPI":
        val = 405
    if cur == "GFP":
        val = 488
    if cur == "Cy3":
        val = 561
    if cur == "Cy5":
        val = 647
    # If the selected channel is already a wavelength
    try:
        val = float(cur)
    except ValueError:
        pass
    ui.update_numeric("ex_selection", value=val)

    # Update the NA and guess the refractive index based on NA
    objective = input.objective()
    na = 1.0  # Default value
    ri = 1.0  # Default value
    if objective.startswith("ID"):
        try:
            _na = get_objective_na(objective_df, objective)
            _ri = get_objective_ri(objective_df, objective)
            # None values from parsing errors -> leave to default
            na = na if _na is None else _na
            ri = ri if _ri is None else _ri
        except RuntimeError as err:
            # In case the ID is not in the database
            ui.notification_show(str(err), type="warning")
    else:
        # Try to parse the selection (expected "max/NA")
        try:
            na = float(objective.split("/")[1])
        except Exception:
            pass
    ui.update_numeric("na_selection", value=na)
    # TODO find a way to discrimnate if values come from ID or not...
    ri = 1.0
    if na > 1:
        ri = 1.515
    ui.update_numeric("ri_selection", value=ri)


@reactive.effect
@reactive.event(input.site, input.microscope, input.objective, input.info)
def filter_by_sidebar_selections():
    """
    Filter the data by the common columns.

    Sets also the date range selection min/max.
    """
    # Check that all selections are valid (not None)
    site_ = input.site()
    mic_ = input.microscope()
    obj_ = input.objective()
    info_ = input.info()
    if None in [site_, mic_, obj_, info_]:
        df_data.set(None)
        df_ref.set(None)
        return
    # Filter the dataframe and set the reactive value (work with df copy)
    df = filter_by_column_value(dataframe.copy(), "Site", input.site())
    df = filter_by_column_value(df, "Microscope", input.microscope())
    df = filter_by_column_value(df, "Objective", input.objective())
    # Reset the psf max value
    psf_max_val.set(df[df.columns[3:]].max().max())
    df = filter_by_column_value(df, "Info", input.info())
    # Drop NAN columns
    df = df.dropna(axis=1, how="all")
    # Before enusring numeric, keep copy of that dataframe
    df_ref.set(df)
    # Ensure numeric data values (date columns)
    for col in df.columns[2:]:
        df[col] = df[col].astype(float)
    # Sort the date columns
    cols = list(df.columns[:2])
    for c in sorted(df.columns[2:]):
        cols.append(c)
    df = df.reindex(cols, axis=1)
    df_data.set(df)


@reactive.effect
@reactive.event(df_data)
def update_date_range_ui():
    df = df_data.get()
    if df is None or df.empty:
        return
    # Update the date range selections
    dates = parse_dates(list(df.columns[2:]))
    if len(dates) == 0:
        return
    ui.update_date_range("date_range_selection", start=dates[0], end=dates[-1])


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
