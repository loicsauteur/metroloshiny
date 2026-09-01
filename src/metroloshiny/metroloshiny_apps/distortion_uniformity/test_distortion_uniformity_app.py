"""Test the field distortion/uniformity app."""

import time

import pytest
from playwright.sync_api import Page
from shiny.playwright import controller as ctrl
from shiny.run import ShinyAppProc


@pytest.mark.manual
def test_basic_app(page: Page, local_app: ShinyAppProc) -> None:
    """
    Test if app starts as expected.

    FYI:
        ! test runs on local file !
        ! Runs on manual tests only, since it requires OMERO connection !
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
    mics.expect_choices(["Test_microscope"])
    sites.set("Hebelstrasse")
    mics.expect_choices(["Test_microscope", "Test_microscope2"])
    mics.set("Test_microscope2")

    # Check objective choices
    objs = ctrl.InputSelect(page, "objective")
    objs.expect_choices(
        sorted(
            {
                "Test_63x": "Test_63x",
                "ID2": "10x/0.45 (ID2)",
                "IDN3": "20x/0.75 (IDN3)",
                "noID": "noID",
            }
        )
    )

    # Check info choices
    info = ctrl.InputSelect(page, "info")
    info.expect_choices(["Test_info"])
    info.expect_selected("Test_info")

    # Check stuff on the "averages" card        ##############################
    averages_card = ctrl.NavsetUnderline(page, "averages_card")
    # There should be no data in the plots
    averages_card.set("Plot Field Uniformity")
    plot_uni_avg = ctrl.OutputUi(page, "show_field_uniformity_over_time_plot")
    assert "No data to visualise!" in str(plot_uni_avg.loc.text_content())
    averages_card.set("Plot Field Distortion")
    plot_dist_avg = ctrl.OutputUi(page, "show_field_distortion_over_time_plot")
    # Needs some waiting until ready... (does not work with timeout...)
    time.sleep(5)
    assert "No data to visualise!" in str(plot_dist_avg.loc.text_content())
    averages_card.set("Table")
    avg_table = ctrl.OutputDataFrame(page, "show_uni_dist_avg_over_time_table")
    avg_table.expect_ncol(0)
    avg_table.expect_nrow(0)

    # Objective table stuff
    averages_card.set("Objective information")
    obj_msg = ctrl.OutputText(page, "show_objective_table_message")
    obj_msg.expect_value("")
    obj_table = ctrl.OutputDataFrame(page, "show_objective_table")
    obj_table.expect_ncol(13)
    obj_table.expect_nrow(2)

    sites.set("Mattenstrasse")
    averages_card.set("Plot Field Uniformity")
    averages_card.set("Objective information")
    obj_msg.expect_value("No objective information available.")
    obj_table.expect_nrow(0)
    obj_table.expect_ncol(0)

    # Check stuff on the Uniformity card (only input selections)    ##########
    uniformity_card = ctrl.NavsetCardUnderline(page, "uniformity_card")
    uniformity_card.set("Compare two dates")
    # (on Mattenstrasse, where there is some data associated)
    expected_dates = ["20260101", "20260109", "20260120"]
    expected_channels = sorted(["488", "561", "Alexa 647", "DAPI"])
    uni_date1 = ctrl.InputSelect(page, "uni_date_selector_1")
    uni_date2 = ctrl.InputSelect(page, "uni_date_selector_2")
    uni_date1.expect_choices(expected_dates)
    uni_date2.expect_choices(expected_dates)
    uni_date1.expect_selected(expected_dates[0])
    uni_date2.expect_selected(expected_dates[-1])

    uniformity_card.set("Compare channels")
    uni_ch1 = ctrl.InputSelect(page, "uni_ch_selector1")
    uni_ch2 = ctrl.InputSelect(page, "uni_ch_selector2")
    uni_single_date = ctrl.InputSelect(page, "uni_single_date_selector")
    uni_ch1.expect_choices(expected_channels)
    uni_ch2.expect_choices(expected_channels)
    uni_ch1.expect_selected(expected_channels[0])
    uni_ch2.expect_selected(expected_channels[-1])
    uni_single_date.expect_choices(expected_dates)
    uni_single_date.expect_selected(expected_dates[0])

    # Check stuff on the Distortion card (only input selections)    ##########
    dist_date1 = ctrl.InputSelect(page, "dist_date_selector_1")
    dist_date2 = ctrl.InputSelect(page, "dist_date_selector_2")
    dist_ch = ctrl.InputSelect(page, "dist_ch_selector")
    dist_date1.expect_choices(expected_dates)
    dist_date2.expect_choices(expected_dates)
    dist_date1.expect_selected(expected_dates[0])
    dist_date2.expect_selected(expected_dates[-1])
    dist_ch.expect_choices(expected_channels)

    # TODO/FIXME test more/better once more data and more final app

    print("----DONE----")
