"""Old version of the app."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from shiny import reactive
from shiny.express import input, render, ui

from metroloshiny.utils.dataframe_utils import (
    filter_by_column_value,
    filter_by_date_range,
    get_light_source_kinds,
    get_power_over_time_data,
    keep_non_nan_rows,
    parse_dates,
)

# Import data from shared.py
from metroloshiny.utils.read_file import (
    get_laser_power_objective_data,
    get_sheet,
    load_doc,
)

# FIXME: rewrite the app??
# FIXME: not sure how to fix: UserWarning: Ignoring `palette` because no `hue` variable has been assigned. (line: 473 & 631)

# Load Data
use_dev_local_file = False
sheet_doc = load_doc(dev_local_file=use_dev_local_file)
wsheet_power, df = get_sheet(
    sheet_doc, "Power", dev_local_file=use_dev_local_file
)
# wsheet_psf, df_psf = get_sheet(
#     sheet_doc, "PSF", dev_local_file=use_dev_local_file
# )


gworks_sheet, df = get_laser_power_objective_data(
    dev_local_file=False
)  # FIXME temp tests on local file

# Create UI
ui.page_opts(title="Metrology: Power at the objective")

# ui.nav_spacer()  # Push the navbar items to the right

# Create a tab layout (for metrology kinds)
with ui.navset_pill(id="tab"):
    with ui.nav_panel("Laser Power at Objective"):
        # Choices of sites (Hebel vs Matt)
        sites = np.unique(np.asarray(df["Site"]))

        microscopes = reactive.value([])
        objectives = reactive.value([])
        info = reactive.value([])  # for filtering on the info column
        light_kinds = reactive.value([])  # laser or led
        line = reactive.value([])  # wavelengths
        power_prcts = reactive.value([])  # wavelengths power %
        dates = reactive.value([])
        date_range = reactive.value([])  # min/max date
        _df = reactive.value(None)  # Place holder FIXME unused...

        # Update microscope choices based on site
        @reactive.effect
        @reactive.event(input.site)
        def update_microscope_choices():
            """Update microscope choices."""
            # Filter the data frame (always the original) and
            # set the reactive result dataframe
            df_filtered = filter_by_column_value(df, "Site", input.site())
            _df.set(df_filtered)
            # Get a list of microscopes and set the reactive result
            m_filtered = np.unique(np.asarray(df_filtered["Microscope"]))
            microscopes.set(list(m_filtered))
            # Update the ui selection (using the reactive variable)
            ui.update_select("microscope", choices=microscopes.get())

        # Update objective choices based on microscope
        @reactive.effect
        @reactive.event(input.microscope)
        def update_objective_choices():
            """Update objective choices."""
            # Filter original df from start
            df_filtered = filter_by_column_value(df, "Site", input.site())
            df_filtered = filter_by_column_value(
                df_filtered, "Microscope", input.microscope()
            )
            _df.set(df_filtered)
            # Get a list of unique objective choices
            o = np.unique(np.asarray(df_filtered["Objective"]))
            objectives.set(list(o))
            # Update the ui selection
            ui.update_select("objective", choices=objectives.get())

        # Update Info choices based on objectve
        @reactive.effect
        @reactive.event(input.objective, input.microscope)
        def update_info_choices():
            """Update info choices."""
            # Filter original df from start
            df_filtered = filter_by_column_value(df, "Site", input.site())
            df_filtered = filter_by_column_value(
                df_filtered, "Microscope", input.microscope()
            )
            df_filtered = filter_by_column_value(
                df_filtered, "Objective", input.objective()
            )
            _df.set(df_filtered)
            # Get a list of unique info items
            i = np.unique(np.asarray(df_filtered["Info"]))
            info.set(list(i))
            # Update the ui selection
            ui.update_select("info", choices=info.get())

        # Update light source choices based on info
        @reactive.effect
        @reactive.event(input.info, input.objective, input.microscope)
        def update_line_choices():
            """Update line choices."""
            # Filter original df from start
            df_filtered = filter_by_column_value(df, "Site", input.site())
            df_filtered = filter_by_column_value(
                df_filtered, "Microscope", input.microscope()
            )
            df_filtered = filter_by_column_value(
                df_filtered, "Objective", input.objective()
            )
            df_filtered = filter_by_column_value(
                df_filtered, "Info", input.info()
            )
            _df.set(df_filtered)
            # Get a list of available light sources
            kinds = get_light_source_kinds(df_filtered)
            if len(kinds) == 0:
                kinds.append("No data")
            if len(kinds) == 2:
                kinds.append("Both")
            # Set the choices and update ui selection
            light_kinds.set(list(kinds))
            ui.update_select(
                "kind",
                choices=light_kinds.get(),
                selected=light_kinds.get()[0],
            )

        # Update wavelength choices based on light source
        @reactive.effect
        @reactive.event(
            input.kind, input.info, input.objective, input.microscope
        )
        def update_wavelength_choices():
            """Update wavelength choices."""
            # Filter original df from start
            df_filtered = filter_by_column_value(df, "Site", input.site())
            df_filtered = filter_by_column_value(
                df_filtered, "Microscope", input.microscope()
            )
            df_filtered = filter_by_column_value(
                df_filtered, "Objective", input.objective()
            )
            df_filtered = filter_by_column_value(
                df_filtered, "Info", input.info()
            )

            # Skip updating (if kind is not a valid column name)
            if input.kind() is None or input.kind() in ["No data", "Both"]:
                return

            df_filtered = keep_non_nan_rows(
                df_filtered, column_name=input.kind()
            )
            _df.set(df_filtered)
            # Get a list of available wavelengths
            w = np.unique(np.asarray(df_filtered[input.kind()]))
            w = list(w)
            w.append("All")
            line.set(list(w))
            # Update the ui selection
            ui.update_select("line", choices=line.get())

        # Update power choices based on wavelength  --------------------------
        @reactive.effect
        @reactive.event(
            input.line,
            input.kind,
            input.info,
            input.objective,
            input.microscope,
        )
        def update_power_choices():
            """Update power percent choices."""
            # Filter original df from start
            df_filtered = filter_by_column_value(df, "Site", input.site())
            df_filtered = filter_by_column_value(
                df_filtered, "Microscope", input.microscope()
            )
            df_filtered = filter_by_column_value(
                df_filtered, "Objective", input.objective()
            )
            df_filtered = filter_by_column_value(
                df_filtered, "Info", input.info()
            )

            # Skip updating (if kind is not a valid column name)
            if input.kind() is None or input.kind() in ["No data", "Both"]:
                return
            df_filtered = keep_non_nan_rows(
                df_filtered, column_name=input.kind()
            )

            # Skip updating (if line is None)
            if input.line() is None:
                return
            if input.line() != "All":
                df_filtered = filter_by_column_value(
                    df_filtered, input.kind(), float(input.line())
                )
            _df.set(df_filtered)
            # Get a list of available powers (make sure it is all strings)
            p = [
                str(x) for x in np.unique(np.asarray(df_filtered["Power [%]"]))
            ]
            p.append("All")
            power_prcts.set(p)
            # Update ui selection
            ui.update_select("power", choices=power_prcts.get())

        # Update date choices based on power
        @reactive.effect
        @reactive.event(
            input.power,
            input.line,
            input.kind,
            input.info,
            input.objective,
            input.microscope,
        )
        def update_date_choices():
            """Update date choices."""
            # Filter original df from start
            df_filtered = filter_by_column_value(df, "Site", input.site())
            df_filtered = filter_by_column_value(
                df_filtered, "Microscope", input.microscope()
            )
            df_filtered = filter_by_column_value(
                df_filtered, "Objective", input.objective()
            )
            df_filtered = filter_by_column_value(
                df_filtered, "Info", input.info()
            )

            # Skip updating (if kind is not a valid column name)
            if input.kind() is None or input.kind() in ["No data", "Both"]:
                return
            df_filtered = keep_non_nan_rows(
                df_filtered, column_name=input.kind()
            )

            # Skip updating (if line is None)
            if input.line() is None:
                return
            if input.line() != "All":
                df_filtered = filter_by_column_value(
                    df_filtered, input.kind(), float(input.line())
                )
                # The df now contains only the [LED or Laser] and
                #   [Power] columns + dates
                # Drop all date columns with only NaN values
                df_filtered = df_filtered.iloc[:, 2:].dropna(axis=1, how="all")
            else:
                # df contains still both light source columns
                df_filtered = df_filtered.iloc[:, 3:].dropna(axis=1, how="all")
            dates.set(list(df_filtered.columns))
            # Update the ui selection
            ui.update_select("date", choices=dates.get())

        @reactive.effect
        @reactive.event(
            input.power,
            input.line,
            input.kind,
            input.info,
            input.objective,
            input.microscope,
        )
        def update_date_range():
            """Update date range choices."""
            # Filter original df from start
            df_filtered = filter_by_column_value(df, "Site", input.site())
            df_filtered = filter_by_column_value(
                df_filtered, "Microscope", input.microscope()
            )
            df_filtered = filter_by_column_value(
                df_filtered, "Objective", input.objective()
            )
            df_filtered = filter_by_column_value(
                df_filtered, "Info", input.info()
            )

            # Skip updating (if kind is not a valid column name)
            if input.kind() is None or input.kind() in ["No data", "Both"]:
                return
            df_filtered = keep_non_nan_rows(
                df_filtered, column_name=input.kind()
            )

            # Skip updating (if line is None)
            if input.line() is None:
                return
            if input.line() != "All":
                df_filtered = filter_by_column_value(
                    df_filtered, input.kind(), float(input.line())
                )
                # The df now contains only the [LED or Laser] and
                #   [Power] columns + dates
                # Drop all date columns with only NaN values
                df_filtered = df_filtered.iloc[:, 2:].dropna(axis=1, how="all")
            else:
                # df contains still both light source columns
                df_filtered = df_filtered.iloc[:, 3:].dropna(axis=1, how="all")
            # Parse the dates
            d = parse_dates(list(df_filtered.columns))
            if len(d) < 1:
                # may happen temporarily...
                return
            date_range.set(d)
            # Update the ui selection
            ui.update_date_range(
                "date_range",
                start=date_range.get()[0],
                end=date_range.get()[-1],
            )

        # FIXME # Add reload data button
        # reload_btn = ui.input_action_button("action_button", "Reload data")

        # @reactive.effect
        # @reactive.event(input.action_button)
        # def reload_power_at_objective_data():
        #     print("pressed reload button...")
        #     gsheet_, df_ = get_laser_power_objective_data(
        #           dev_local_file=False
        #     )
        #     _df.set(df_)

        # Inptut selections for shiny cards
        single_date_selection = ui.input_select(
            "date", "Select a date", choices=[]
        )
        date_range_selection = ui.input_date_range(
            "date_range",
            "Select a date range",
            start=None,
            end=None,
            format="yyyymmdd",
        )

        with ui.layout_sidebar():
            with ui.sidebar():
                ui.input_select("site", "Select the site", choices=list(sites))
                ui.input_select(
                    "microscope", "Select a microscope", choices=[]
                )
                ui.input_select("objective", "Select an objective", choices=[])
                ui.input_select("info", "Filter by info column", choices=[])
                ui.input_select("kind", "Select light source kind", choices=[])
                ui.input_select("line", "Select a wavelength [nm]", choices=[])
                ui.input_select("power", "Select power [%]", choices=[])

            # Power linearity per date ---------------------------------------
            with ui.navset_card_underline(header=[single_date_selection]):
                with ui.nav_panel(title="Plot"):
                    # Generate table (filter df from scratch)
                    plt_df = reactive.value(None)

                    @reactive.effect
                    @reactive.event(
                        input.date,
                        input.line,
                        input.kind,
                        input.info,
                        input.objective,
                        input.microscope,
                    )
                    def get_power_linearity_table():
                        """Get power linearity table."""
                        # Filter (remove columns)
                        table = filter_by_column_value(
                            df, "Site", input.site()
                        )
                        table = filter_by_column_value(
                            table, "Microscope", input.microscope()
                        )
                        table = filter_by_column_value(
                            table, "Objective", input.objective()
                        )
                        table = filter_by_column_value(
                            table, "Info", input.info()
                        )
                        # drop the unused light-source column
                        col_to_drop = (
                            "Laser Line [nm]"
                            if input.kind() == "LED Line [nm]"
                            else "LED Line [nm]"
                        )
                        table = table.drop(columns=[col_to_drop])
                        # Filter by wavelength
                        if input.line() is not None and input.line() != "All":
                            table = filter_by_column_value(
                                table,
                                input.kind(),
                                float(input.line()),
                                drop_column=False,
                            )

                        # FIXME: not needed here: Filter by power
                        # if input.power() is not None:
                        #    table = filter_by_column_value(
                        #           table, "Power [%]",
                        #           float(input.power()),
                        #           drop_column=False
                        #    )

                        # Remove measurement columns except the need one...
                        if (
                            input.kind() is not None
                            and input.date() is not None
                        ):
                            table = table[
                                [input.kind(), "Power [%]", input.date()]
                            ]

                        # Only set the reactive variable if 3 columns
                        if len(table.columns) == 3:
                            plt_df.set(table)
                        else:
                            plt_df.set(None)

                    # Card header
                    @render.text
                    def title_card_1():
                        """Render info text."""
                        return f"Power linearity on {input.date()}"

                    @render.plot
                    def power_linearity_per_date():
                        """Render linearity plot."""
                        fig, ax = plt.subplots()
                        # Get the current table
                        table = plt_df.get()
                        # Sanity check
                        if table is None:
                            # Show empty plot
                            ax.text(
                                0.5,
                                0.5,
                                "No data to visualsise!",
                                ha="center",
                                va="center",
                            )
                            ax.set_axis_off()
                            return fig
                        # Work on a copy of the table, otherwise
                        #   the reactive value is changed
                        table = table.copy()
                        # Merge the first two columns
                        table["Line [nm] @ [%]"] = (
                            table[table.columns[0]].astype(int).astype(str)
                            + " @ "
                            + table[table.columns[0]].astype(int).astype(str)
                        )
                        # Reorder columns
                        cols = list(table)
                        cols.insert(0, cols.pop(cols.index(cols[-1])))
                        table = table.loc[:, cols]
                        # Pivot the table
                        table = table.melt(
                            id_vars=table.columns[:3],
                            var_name="Date",
                            value_name="mW",
                        )

                        # Create plot
                        sns.lineplot(
                            data=table,
                            markers=True,
                            style=table.columns[1],  # to ensure markers
                            dashes=False,  # keep sloid lines
                            x=table.columns[2],  # Power
                            y=table.columns[4],  # Date
                            hue=table.columns[1],  # Line
                            palette="turbo",
                            hue_norm=(380, 700),
                            legend="full",  # enures precise line value
                            # estimator=None,
                            # linewidth=2.5, # increase the plotted line width
                        )
                        # Move legend to the right of the plot
                        legend = ax.get_legend()
                        if legend is None:
                            return
                        legend.set_bbox_to_anchor((1.05, 1))
                        legend.set_loc("upper left")
                        fig.tight_layout()

                with ui.nav_panel("Table"):

                    @render.data_frame
                    def power_linearity_table():
                        """Render linearity table."""
                        return plt_df.get()

            # Power stability over time --------------------------------------
            with ui.navset_card_underline(header=[date_range_selection]):
                with ui.nav_panel(title="Plot"):
                    # Generate table (filter df from scratch)
                    pst_df = reactive.value(None)

                    @reactive.effect
                    @reactive.event(
                        input.date_range,
                        input.power,
                        input.line,
                        input.kind,
                        input.info,
                        input.objective,
                        input.microscope,
                    )
                    def get_power_stability_table():
                        """Create table."""
                        # Filter (remove columns)
                        table = filter_by_column_value(
                            df, "Site", input.site()
                        )
                        table = filter_by_column_value(
                            table, "Microscope", input.microscope()
                        )
                        table = filter_by_column_value(
                            table, "Objective", input.objective()
                        )
                        table = filter_by_column_value(
                            table, "Info", input.info()
                        )
                        # drop the unused light-source column
                        col_to_drop = (
                            "Laser Line [nm]"
                            if input.kind() == "LED Line [nm]"
                            else "LED Line [nm]"
                        )
                        table = table.drop(columns=[col_to_drop])
                        # Filter by wavelength
                        if input.line() is not None and input.line() != "All":
                            table = filter_by_column_value(
                                table,
                                input.kind(),
                                float(input.line()),
                                drop_column=False,
                            )
                        # Filter by power
                        if (
                            input.power() is not None
                            and input.power() != "All"
                        ):
                            table = filter_by_column_value(
                                table,
                                "Power [%]",
                                float(input.power()),
                                drop_column=False,
                            )
                        # Drop all nan columns
                        table = table.dropna(axis=1, how="all")
                        # Filter columns by the selected date range
                        start_date = input.date_range()[0].strftime("%Y%m%d")
                        end_date = input.date_range()[1].strftime("%Y%m%d")
                        table = filter_by_date_range(
                            table, start_date, end_date
                        )
                        pst_df.set(table)

                    @render.text
                    def title_over_time():
                        """Render info text."""
                        return "Power stability over time"

                    @render.plot
                    def power_stability_over_time():
                        """Render stability plot."""
                        fig, ax = plt.subplots()
                        # No data plot
                        if input.line() == "All" and input.power() == "All":
                            ax.text(
                                0.5,
                                0.5,
                                "Cannot show all lines at all powers!",
                                ha="center",
                                va="center",
                            )
                            ax.set_axis_off()
                            return fig
                        # Show no plot if no data
                        if None in [
                            input.power(),
                            input.line(),
                        ] or not isinstance(pst_df.get(), pd.DataFrame):
                            # Show empty plot
                            ax.text(
                                0.5,
                                0.5,
                                "No data to visualsise!",
                                ha="center",
                                va="center",
                            )
                            ax.set_axis_off()
                            return fig

                        # Otherwise create plot
                        table = pst_df.get().copy()
                        if table.empty:
                            return
                        wavelength = (
                            None
                            if input.line() == "All"
                            else float(input.line())
                        )
                        prct = (
                            None
                            if input.power() == "All"
                            else float(input.power())
                        )
                        table = get_power_over_time_data(
                            table, line=wavelength, power_prct=prct
                        )
                        if input.power() == "All":
                            # make sure to group per power (not line)
                            sns.lineplot(
                                data=table,
                                x="Date",
                                y="mW",
                                hue=table.columns[2],  # group by "Power [%]"
                                palette="turbo",
                                hue_norm=(0, 100),  # adjust line colors
                                legend="full",  # enures precise line value
                            )
                        else:
                            # default group data by line value
                            sns.lineplot(
                                data=table,
                                x="Date",
                                y="mW",
                                markers=True,
                                style=table.columns[1],  # ensure markers
                                dashes=False,  # keep sloid lines
                                hue=table.columns[1],  # group by "Line"
                                palette="turbo",
                                hue_norm=(380, 700),
                                legend="full",  # enures precise line value
                            )
                        # Move legend to the right of the plot
                        legend = ax.get_legend()
                        if legend is not None:
                            legend.set_bbox_to_anchor((1.05, 1))
                            legend.set_loc("upper left")
                        # X-labels
                        plt.xticks(rotation=45, ha="right")  # rotate
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

                with ui.nav_panel("Table"):

                    @render.data_frame
                    def power_stability_over_time_table():
                        """Render stabiltiy table."""
                        table = pst_df.get()
                        # TODO filter unwanted dates out
                        return table

    # ________________________________________________________________________
    #
    # PSF
    # with ui.nav_panel("PSF"):
    #     with ui.layout_sidebar():
    #         with ui.sidebar():
    #             pass

    #         # Power linearity per date ---------------------------------------
    #         with ui.navset_card_underline():
    #             with ui.nav_panel(title="Plot"):
    #                 pass
    #             with ui.nav_panel(title="Table"):
    #                 pass
