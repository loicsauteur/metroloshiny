import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from shiny import reactive
from shiny.express import input, render, ui

from metroloshiny.utils.common_utils import (
    set_local_file,
    theo_fwhm_2photon,
    theo_fwhm_pointscanner,
    theo_fwhm_spinning,
    theo_fwhm_widefield,
)
from metroloshiny.utils.dataframe_utils import (
    filter_by_column_value,
    filter_by_date_range,
)
from metroloshiny.utils.read_file import get_sheet, load_doc

# FIXME: add plot (table) for shifts

# Load Data
use_dev_local_file = set_local_file()
sheet_doc = load_doc(dev_local_file=use_dev_local_file)
wsheet_psf, df = get_sheet(sheet_doc, "PSF", dev_local_file=use_dev_local_file)

# Global variable       ------------------------------------------------------
psf_max_val = df[df.columns[6:]].max().max()  # highest PSF value in dataframe

# Reactive & general variables      ------------------------------------------
sites = np.unique(np.asarray(df["Site"]))
# FIXME: microsocpes, objectives, info - never really used...
microscopes = reactive.value([])
objectives = reactive.value([])
info = reactive.value([])  # for filtering on the info column
df_data = reactive.value(None)  # Contains only channel, FWHM & Date cols
df_final = reactive.value(None)  # Final plotting data
df_final_table = reactive.value(None)  # Final plotting data for table display
ch_check_boxes = reactive.value(None)  # Selectors for channel displays
fwhm_check_boxes = reactive.value(
    None
)  # Selectors for FWHM measurement display
theoretical_fwhm = reactive.value(
    None
)  # Tuple (lateral, axial) theoretical FWHM values


# Create UI         ----------------------------------------------------------
ui.page_opts(title="Metrology: PSF")
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
            with ui.nav_panel(title=""):
                # Add checkboxes & other as columns
                with ui.layout_column_wrap(
                    width=1 / 3, min_height="150px", max_height="2000px"
                ):

                    @render.ui
                    @reactive.event(ch_check_boxes)
                    def render_channel_choices():
                        return (
                            "Select channels for plotting:",
                            ch_check_boxes.get(),
                            "FWHM to display:",
                            fwhm_check_boxes.get(),
                        )

                    @render.ui
                    def render_theoreticals():
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

        with ui.navset_card_underline(title="PSF over time"):
            with ui.nav_panel(title="Plot"):
                # Add a date range selection
                @render.ui
                def render_date_range_selection():
                    """Find min/max dates and create range selection."""
                    dates = df_data.get()
                    if dates is None or dates.empty:
                        return
                    # Find the min and max dates
                    dates = list(dates.columns[2:])
                    dates_stripped = []
                    for d in dates:
                        dates_stripped.append(d[:8])

                    # Create date range selection
                    date_range_selection = ui.input_date_range(
                        "date_range_selection",
                        "Select date range:",
                        start=min(dates_stripped),
                        end=max(dates_stripped),
                        format="yyyymmdd",
                    )
                    return date_range_selection

                # Render the plot
                @render.plot
                def plot_psf_over_time():
                    """Create the plot."""
                    _df = df_final.get()
                    fig, ax = plt.subplots()
                    # Show no data plot
                    if _df is None or _df.empty:
                        ax.text(
                            0.5,
                            0.5,
                            "No data to visualsise!",
                            ha="center",
                            va="center",
                        )
                        ax.set_axis_off()
                        return fig
                    sns.lineplot(
                        _df,
                        x="Date",
                        y="nm",
                        markers=True,
                        style=_df.columns[0],
                        dashes=False,
                        hue=_df.columns[0],
                        palette="turbo",
                        legend="full",
                    )
                    # Sanity check: ensure that max PSF val < as theoreticals
                    y_max = psf_max_val * 1.05
                    for val in theoretical_fwhm.get():
                        if val > y_max:
                            y_max = val * 1.05
                    # Fix Y axis min/max according to -10 to max+5% in original df
                    ax.set(ylim=(-10, y_max))
                    # Move legend to the right of the plot
                    legend = ax.get_legend()
                    if legend is not None:
                        legend.set_bbox_to_anchor((1.05, 1))
                        legend.set_loc("upper left")
                    # X-labels
                    plt.xticks(rotation=45, ha="right")  # rotate the x-ticks
                    # Do not show all the ticks (for more than 10)
                    ticks = ax.get_xticks()
                    if len(ticks) > 10:
                        new_ticks = ticks[:: int(len(ticks) ** 0.5)]
                        # Make sure the last date tick is shown
                        if new_ticks[-1] != ticks[-1]:
                            new_ticks.append(ticks[-1])
                        ax.set_xticks(new_ticks)
                    ax.set_xlabel("")
                    fig.tight_layout()
                    return fig

            with ui.nav_panel(title="Table"):

                @render.data_frame
                def test2():
                    return df_final_table.get()


# Reactive functions        --------------------------------------------------
@reactive.effect()
@reactive.event(
    input.ch_selection,
    input.fwhm_selection,
    input.theoretical,
    theoretical_fwhm,
    input.date_range_selection,
)
def create_display_df():
    """
    Filter the filtered DF by card selections.

    Adds also entries for theoretical values.
    FYI: sorts the dates (columns).
    """
    # Get the filtered dataframe (as a copy)
    if df_data.get() is None or df_data.get().empty:
        return
    _df = df_data.get().copy()

    # Drop NAN columns (no measurement for a specific date)
    _df = _df.dropna(axis=1, how="all")

    # Make sure all date columns contain float (numeric is already ensured)
    for col in _df.columns[2:]:
        _df[col] = df[col].astype(float)

    # Filter data by selected channels and FWHM to display
    ch_sel = input.ch_selection()
    fwhm_sel = input.fwhm_selection()
    if len(ch_sel) != len(np.unique(np.asarray(_df["Channel"]))):
        _df = _df[_df["Channel"].isin(list(ch_sel))]
    if len(fwhm_sel) != len(np.unique(np.asarray(_df["FWHM"]))):
        _df = _df[_df["FWHM"].isin(list(fwhm_sel))]

    # Add theoretical values to the data
    theoretical_sel = input.theoretical()
    for theo in theoretical_sel:
        entry = [input.ch_calc_selection(), theo.capitalize()]
        while len(entry) < len(_df.columns):
            if theo == "lateral":
                entry.append(theoretical_fwhm.get()[0])
            else:
                entry.append(theoretical_fwhm.get()[1])
        _df.loc[len(_df)] = entry

    # Remove the date columns that do not fall into the date range selection
    start_date = input.date_range_selection()[0].strftime("%Y%m%d")
    end_date = input.date_range_selection()[1].strftime("%Y%m%d")
    _df = filter_by_date_range(_df, start_date, end_date)

    # Merge the Channel and FWHM columns (and drop the original ones)
    _df["PSF"] = (
        _df[_df.columns[0]].astype(str) + " " + _df[_df.columns[1]].astype(str)
    )
    _df = _df.drop(columns=_df.columns[:2])
    # Move new (last) col to beginning
    cols = list(_df)
    cols.insert(0, cols.pop(cols.index(cols[-1])))
    _df = _df.loc[:, cols]

    # Sort date columns
    cols = [_df.columns[0]]
    for c in sorted(_df.columns[1:]):
        cols.append(c)
    _df = _df.reindex(cols, axis=1)

    # Set the reactive value for the table view
    df_final_table.set(_df)

    # Pivot the table?
    _df = _df.melt(id_vars=_df.columns[0], var_name="Date", value_name="nm")

    # Set the final df reactive value for data display
    df_final.set(_df)


@reactive.effect()
@reactive.event(
    input.ch_calc_selection,
    input.mic_kind_selection,
    input.ex_selection,
    input.na_selection,
    input.ri_selection,
)
def update_theoretical_values():
    """Calculate theoretical FWHM values."""
    w = input.ex_selection()
    na = input.na_selection()
    ri = input.ri_selection()
    # Return if values are None or 0
    if w is None or w == 0:
        return
    if na is None or na == 0:
        return
    if ri is None or ri == 0:
        return

    kind = input.mic_kind_selection()
    if kind == "Widefield":
        theo = theo_fwhm_widefield(w, na, ri)
    elif kind == "Point Scanner":
        theo = theo_fwhm_pointscanner(w, na, ri)
    elif kind == "Spinning disk":
        theo = theo_fwhm_spinning(w, na, ri)
    elif kind == "2-Photon":
        theo = theo_fwhm_2photon(w, na, ri)
    else:
        raise NotImplementedError(
            f"Calculation of FWHM for {kind} is not implemented."
        )

    # Set the reactive value
    for i in theo:
        # In case of complex number (e.g. wrong NA and/or RI): set to (0, 0)
        if not isinstance(i, float):
            theoretical_fwhm.set((0, 0))
            return
    theoretical_fwhm.set((round(theo[0], 2), round(theo[1], 2)))


@reactive.effect()
@reactive.event(input.ch_calc_selection)
def update_theoretical_calculation():
    """
    Update values for theoretical calculations.

    Based on the channel selection for the calculation.
    """
    # Update the wavelength
    cur = input.ch_calc_selection()
    val = 488
    if cur == "DAPI":
        val = 405
    if cur == "GFP":
        val = 488
    if cur == "Cy3":
        val = 561
    if cur == "Cy5":
        val = 647
    ui.update_numeric("ex_selection", value=val)
    # Update the NA and guess the refractive index based on NA
    _objective = input.objective()
    na = 1.0  # Default value
    try:
        na = float(_objective.split("/")[1])
    except Exception:
        pass
    ui.update_numeric("na_selection", value=na)
    ri = 1.0
    if na > 1:
        ri = 1.515
    ui.update_numeric("ri_selection", value=ri)


@reactive.effect
@reactive.event(df_data)
def create_card_data_selectors():
    """Create checkbox groups for channels and FWHM entries."""
    _df = df_data.get()
    # If filtered df is None, there should be no checkboxes
    if _df is None:
        ch_check_boxes.set([])
        return
    # The dataframe only contains columns Channel, FWHM and dates
    # Get unique channel names
    channels = np.unique(np.asarray(_df["Channel"]))
    # Create a checkbox group for the channels
    ch_dict = {}
    for ch in channels:
        ch_dict[ch] = ch
    ch_check_boxes.set(
        ui.input_checkbox_group(
            "ch_selection", "", choices=ch_dict, selected=list(ch_dict.keys())
        )
    )
    # Update also the ch_calc_selection
    ui.update_select("ch_calc_selection", choices=list(channels))
    # Get unique FWHM names
    fwhms = np.unique(np.asarray(_df["FWHM"]))
    # Create a checkbox group for the FWHM
    fwhm_dict = {}
    for f in fwhms:
        fwhm_dict[f] = f
    fwhm_check_boxes.set(
        ui.input_checkbox_group(
            "fwhm_selection",
            "",
            choices=fwhm_dict,
            selected=list(fwhm_dict.keys()),
        )
    )


@reactive.effect
@reactive.event(input.site, input.microscope, input.objective, input.info)
def create_final_data():
    """Filter the data by the common columns."""
    # Check that all selections are valid (not None)
    site_ = input.site()
    mic_ = input.microscope()
    obj_ = input.objective()
    info_ = input.info()
    if None in [site_, mic_, obj_, info_]:
        df_data.set(None)
        return
    # Filter the dataframe and set the reactive value (work with df copy)
    _df = filter_by_column_value(df.copy(), "Site", input.site())
    _df = filter_by_column_value(
        _df,
        "Microscope",
        input.microscope(),
    )
    _df = filter_by_column_value(_df, "Objective", input.objective())
    _df = filter_by_column_value(_df, "Info", input.info())
    df_data.set(_df)


@reactive.effect
@reactive.event(input.site)
def update_microscope_choices():
    """Update microscope choices based on site selection."""
    # Filter the data frame (always the original) and
    # set the reactive result dataframe
    df_filtered = filter_by_column_value(df.copy(), "Site", input.site())
    # Get a list of microscopes and set the reactive result
    m_filtered = np.unique(np.asarray(df_filtered["Microscope"]))
    microscopes.set(list(m_filtered))
    # Update the ui selection (using the reactive variable)
    ui.update_select("microscope", choices=microscopes.get())


@reactive.effect
@reactive.event(input.microscope, input.site)
def update_objective_choices():
    """Update objective choices based on microscope selection."""
    # Filter original df from start
    df_filtered = filter_by_column_value(df.copy(), "Site", input.site())
    df_filtered = filter_by_column_value(
        df_filtered, "Microscope", input.microscope()
    )
    # Get a list of unique objective choices
    o = np.unique(np.asarray(df_filtered["Objective"]))
    objectives.set(list(o))
    # Update the ui selection
    ui.update_select("objective", choices=objectives.get())


@reactive.effect
@reactive.event(input.objective, input.microscope, input.site)
def update_info_choices():
    """Update info choices based on microscope & objective selection."""
    # Filter original df from start
    df_filtered = filter_by_column_value(df.copy(), "Site", input.site())
    df_filtered = filter_by_column_value(
        df_filtered, "Microscope", input.microscope()
    )
    df_filtered = filter_by_column_value(
        df_filtered, "Objective", input.objective()
    )
    # Get a list of unique info items
    i = np.unique(np.asarray(df_filtered["Info"]))
    info.set(list(i))
    # Update the ui selection
    ui.update_select("info", choices=info.get())


# General functions         --------------------------------------------------
