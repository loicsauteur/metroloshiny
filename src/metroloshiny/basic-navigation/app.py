import numpy as np
import seaborn as sns

# Import data from shared.py
from shared import df as penguins
from shiny.express import input, render, ui

from metroloshiny.utils.dataframe_utils import (
    get_power_over_time_data,
)  # FIXME unused: get_linearity, wavelength_to_color
from metroloshiny.utils.read_file import read_xlsx

# from shinywidgets import render_plotly

ui.page_opts(title="Shiny navigation components")

ui.nav_spacer()  # Push the navbar items to the right


footer = ui.input_select(
    "var", "Select variable", choices=["bill_length_mm", "body_mass_g"]
)


with ui.nav_panel("Page 1"):
    with ui.navset_card_underline(title="Penguins data", footer=footer):
        with ui.nav_panel("Plot"):

            @render.plot
            def hist():
                """Render histogram plot."""
                p = sns.histplot(
                    penguins,
                    x=input.var(),
                    facecolor="#007bc2",
                    edgecolor="white",
                )
                return p.set(xlabel=None)

        with ui.nav_panel("Table"):

            @render.data_frame
            def data():
                """Render dataframe."""
                print("----")
                print(penguins[["species", "island", input.var()]])
                print("----")
                return penguins[["species", "island", input.var()]]


# this caches when it is loading... so can always use the function directly
#    @reactive.calc
#    def get_data():
#        print("get_data executed")
#        return read_xlsx()


# mydata = read_xlsx() # using default parameter for testing file
# selection = ui.input_select("line", "Select", choices=["405", "477"])


# Load data
df_power_data = read_xlsx("./dummy.xls")
power_lines = ["All"]
power_lines.extend(
    np.unique(np.asarray(df_power_data[df_power_data.columns[0]]))
)
# power_prct = ["All"]
power_prct = np.unique(np.asarray(df_power_data[df_power_data.columns[1]]))
measurement_dates = list(df_power_data.columns[3:])

# Create drop-down selections
selection_line = ui.input_select(
    "line", f"Select {df_power_data.columns[0]}", choices=list(power_lines)
)
selection_date = ui.input_select(
    "date", "Select date", choices=measurement_dates
)
selection_power = ui.input_select(
    "power_prct", "Select the power %", choices=list(power_prct)
)


# Create a side bar, which is shown the same for
# all pages (per page not possible?)
# with ui.sidebar():
#    pass

with ui.nav_panel("Laser Power"):
    # "This is the second 'page'."

    with ui.navset_card_underline(
        title="Power Linearity", header=[selection_date]
    ):
        with ui.nav_panel("Plot"):

            @render.plot
            def power_linearity_per_date():
                """Render power-linearity plot."""
                # Keep only the measurements of the selected date
                df = df_power_data[
                    [
                        df_power_data.columns[0],
                        df_power_data.columns[1],
                        input.date(),
                    ]
                ]
                # print("************")
                # Rename the date to mW
                df.columns = [df.columns[0], df.columns[1], "mW"]
                # print(df)
                # print("************")
                sns.lineplot(
                    data=df,
                    markers=True,
                    style=df.columns[0],  # To ensure markers
                    dashes=False,  # keep sloid lines
                    x=df.columns[1],  # 'Power...'
                    y=df.columns[2],  # date
                    hue=df.columns[0],  # 'Line...'
                    palette="turbo",
                    hue_norm=(380, 700),
                    legend="full",  # ensure that the poper line values
                    # are shown in the legend
                    # estimator=None,
                    # linewidth=2.5, # increase the plotted line width
                )

        with ui.nav_panel("Table"):

            @render.data_frame
            def power_linearity_per_date_table():
                """Render power-linearity table."""
                # Keep only the measurements of the selected date
                df = df_power_data[
                    [
                        df_power_data.columns[0],
                        df_power_data.columns[1],
                        input.date(),
                    ]
                ]
                # Make sure header is all strings
                df.columns = [str(x) for x in df.columns]
                return df

    with ui.navset_card_underline(
        title="Power over time", header=[selection_line, selection_power]
    ):
        with ui.nav_panel("Plot"):

            @render.plot
            def power_over_time():
                # Parse the selection (make sure All becomes None)
                line = None if input.line() == "All" else int(input.line())
                # "All" option not in selection anymore
                prct = (
                    None
                    if input.power_prct() == "All"
                    else int(input.power_prct())
                )

                df = get_power_over_time_data(
                    df_power_data, line=line, power_prct=prct
                )  # , merge=True)
                sns.lineplot(
                    df,
                    x="Date",
                    y="mW",
                    hue=df.columns[
                        1
                    ],  # Do not merge values, use individual lines per row
                    palette="turbo",  # Colors
                    hue_norm=(
                        380,
                        700,
                    ),  # Color palette normalization on Line [nm]
                    legend="full",  # ensure that the poper line values
                    # are shown in the legend
                )

    # # Laser power linearity ################################################
    # with ui.navset_card_underline(title="Power linearity"):
    # #, footer=selection):

    #         with ui.nav_panel("Plot"):

    #             @render.plot
    #             def power_linearity_per_day():
    #                 # Select only the rows, which correspond to
    #                   the selected power line (nm)
    #                 df = get_linearity(df_power_data, input.date())

    #                 print(df)
    #                 df2 = df.reset_index(drop=True)
    #                 print("---")
    #                 print(df2)

    #                 # create line plot colors
    #                 wavelengths = list(df.columns)
    #                 palette = {
    #                   w: wavelength_to_color(w) for w in wavelengths
    #                 }

    #                 # Group df by line and power
    #                 p = sns.lineplot(
    #                     df, markers=True,
    #                     palette='turbo',
    #                     #hue_norm=(350, 800)
    #                     #palette=palette,
    #                 )
    #                 return p

    #         with ui.nav_panel("Table"):
    #             @render.data_frame
    #             def power_linearity_per_daydata():
    #                 # Needs header to be all string
    #                   (all numbers does not work)
    #                 df = get_linearity(df_power_data, input.date())
    #                 return df
    #         #with ui.na
