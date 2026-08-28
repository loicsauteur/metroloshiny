"""Test the PSF app."""

from playwright.sync_api import Page
from shiny.playwright import controller as ctrl
from shiny.run import ShinyAppProc


def test_basic_app(page: Page, local_app: ShinyAppProc) -> None:
    """
    Test if app starts as expected.

    FYI: test runs on local file.
        - Sometimes i get errors early,
          re-running will make it go on further/through
    """
    # Navigate to the app URL when it's ready
    page.goto(local_app.url)

    # Check sites
    sites = ctrl.InputSelect(page, "site")
    sites.expect_label("Select the site")
    sites.expect_choices(["Hebelstrasse", "Mattenstrasse"])
    sites.set("Mattenstrasse")

    # Check microscope choices
    mics = ctrl.InputSelect(page, "microscope")
    mics.expect_label("Select a microscope")
    mics.expect_choices(["Example-Entry", "Mic1", "Mic2", "Mic3", "Mic4"])
    sites.set("Hebelstrasse")
    mics.expect_choices(["Example-Entry"])

    # Check objective choices
    objs = ctrl.InputSelect(page, "objective")
    objs.expect_label("Select an objective")
    objs.expect_selected("20x/3.3")
    # Order of the list is important (sorted alpha-numerical)
    objs.expect_choices(
        {
            "20x/3.3": "20x/3.3",
            "ID1": "4x/0.2 (ID1)",
            "ID5": "100x/1.45 (ID5)",
            "ID999": "?x/? (ID999)",
        }
    )
    # Also the version below would work
    # objs.expect_choices(["20x/3.3", "ID1", "ID5", "ID999"])

    # Check info choices
    info = ctrl.InputSelect(page, "info")
    info.expect_label("Filter by info column")
    info.expect_choices(["Pinhole closed"])
    objs.set("ID5")
    info.expect_choices(["Test Entry"])

    # Test plotting options             ######################################
    ch_sel = ctrl.InputCheckboxGroup(page, "ch_selection")
    fwhm_sel = ctrl.InputCheckboxGroup(page, "fwhm_selection")
    date_range = ctrl.InputDateRange(page, "date_range_selection")
    ch_calc_sel = ctrl.InputSelect(page, "ch_calc_selection")
    theo_sel = ctrl.InputCheckboxGroup(page, "theoretical")

    ch_sel.expect_choices(["Cy3", "Cy5", "DAPI", "GFP"])
    fwhm_sel.expect_choices(["FWHM-X", "FWHM-Y", "FWHM-Z"])
    date_range.expect_value(["20100101", "20200101"])
    ch_calc_sel.expect_choices(["Cy3", "Cy5", "DAPI", "GFP"])
    theo_sel.expect_choices(["lateral", "axial"])
    theo_sel.expect_selected(["lateral", "axial"])

    # Check the objective table             #########################
    option_card = ctrl.NavsetCardUnderline(page, "plotting_options")
    option_card.set("Objective information")
    obj_table = ctrl.OutputDataFrame(page, "show_objective_table")
    obj_table.expect_ncol(13)
    # Should have 2 rows for ID1 and ID5
    obj_table.expect_nrow(2)
    # I dont know how to check for highlighted rows...

    # Check the chromatic over time table       #####################
    ref_ch = ctrl.OutputText(page, "show_ref_channel")
    ref_ch.expect_value(
        "Reference channel: ERROR: could not determine ref channel"
    )
    # Filter by date range to get ref channel = Cy5
    # Make sure we are on the Options tab to make date range changes
    option_card.set("Options")
    # Date range values must be format: yyyy-mm-dd
    date_range.set(value=("2009-12-12", "2014-01-01"))
    ref_ch.expect_value("Reference channel: Cy5")
    date_range.set(value=("2009-12-12", "2021-01-01"))

    # Check the XY plot
    chromatic_card = ctrl.NavsetCardUnderline(page, "chromatic_over_time")
    chromatic_card.set("Plot: All")
    ref_all = ref_ch.get_value()
    chromatic_card.set("Plot: XY")
    ref_ch_xy = ctrl.OutputText(page, "show_ref_channel_xy")
    ref_ch_xy.expect_value(ref_all)
    dates_xy = ctrl.InputSelect(page, "date_selection")
    # Expected choices must be sorted...
    dates_xy.expect_choices(["20100101-2", "20131212", "20200101something"])

    # Check the table
    chromatic_card.set("Table")
    shift_table = ctrl.OutputDataFrame(page, "show_shift_table")
    # 3 dates + 2 default columns
    shift_table.expect_ncol(5)
    # Rows = n channels (4) * shifts XYZ (3)
    shift_table.expect_nrow(4 * 3)

    # Check the PSF over time table             #####################
    psf_card = ctrl.NavsetCardUnderline(page, "psf_over_time")
    psf_card.set("Table")
    psf_table = ctrl.OutputDataFrame(page, "show_fwhm_table")
    # Columns = dates + 2 default columns
    psf_table.expect_ncol(3 + 2)
    # Rows = n channels * XYZ + 2 theoreticals
    psf_table.expect_nrow(4 * 3 + 2)

    # Remove the theoreticals
    theo_sel.set(["lateral"])
    psf_table.expect_nrow(4 * 3 + 1)
    theo_sel.set([])
    psf_table.expect_nrow(4 * 3)
