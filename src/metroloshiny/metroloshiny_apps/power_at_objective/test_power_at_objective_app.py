"""Test the power at objective app."""

from playwright.sync_api import Page
from shiny.playwright import controller as ctrl
from shiny.run import ShinyAppProc


def test_basic_app(page: Page, local_app: ShinyAppProc) -> None:
    """
    Test if app starts as expected.

    FYI: test runs on local file.
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
    mics.expect_choices(["Ti CSU-W1"])
    sites.set("Hebelstrasse")
    mics.expect_choices(["Ti2 BSL2", "no_data"])

    # Check objective choices
    objs = ctrl.InputSelect(page, "objective")
    objs.expect_label("Select an objective")
    objs.expect_selected("10x/0,45")
    objs.expect_choices(["10x/0,45"])

    # Check info choices
    info = ctrl.InputSelect(page, "info")
    info.expect_label("Filter by info column")
    info.expect_selected("Multibandpass")

    # Check light source choices
    ls = ctrl.InputSelect(page, "kind")
    ls.expect_label("Select light source kind")
    ls.expect_selected("LED Line [nm]")

    # Check wavelength choices
    w = ctrl.InputSelect(page, "line")
    w.expect_label("Select a wavelength [nm]")
    w.expect_choices(["395.0", "475.0", "555.0", "635.0", "730.0", "All"])

    # Check percentage choices
    prct = ctrl.InputSelect(page, "power")
    prct.expect_label("Select power [%]")
    prct.expect_selected("5")
    prct.expect_choices(["5", "10", "50", "90", "100"])

    # Check Power linearity output
    date = ctrl.InputSelect(page, "single_date_selection")
    date.expect_label("Select a date")
    date.expect_choices(["20190910text", "20191008", "20150101-sort"])
    date.expect_selected("20190910text")

    # Power linearity table output          ##################################
    # Navset card underline need ids  (needs to be selected/clicked)
    linearity_card = ctrl.NavsetCardUnderline(page, "linearity_card")
    linearity_card.set("Table")

    table = ctrl.OutputDataFrame(page, "show_power_linearity")
    table.expect_ncol(3)
    table.expect_column_labels(["LED Line [nm]", "Power [%]", "20190910text"])
    # One wavelength * 5 powers
    table.expect_nrow(5)
    w.set("All")
    # Now for 5 lines * 5 powers
    table.expect_nrow(5 * 5)

    # Power stability table output          ##################################
    w.set("475.0")
    date_range = ctrl.InputDateRange(page, "date_range_selection")
    date_range.expect_value(["20150101", "20191008"])

    # Select the Table tab
    stability_card = ctrl.NavsetCardUnderline(page, "stability_card")
    stability_card.set("Table")
    table_2 = ctrl.OutputDataFrame(page, "show_power_stability")
    # Expected columns = 3 (dates) + 2
    # Always rows = all-wavelengths * powers
    table_2.expect_ncol(5)
    table_2.expect_nrow(5 * 5)
    w.set("All")
    table_2.expect_nrow(5 * 5)

    # Even if all wavelengths and powers selected: there is a table
