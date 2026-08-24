"""Test the data upload app."""

from pathlib import Path

from playwright.sync_api import Page
from shiny.playwright import controller as ctrl
from shiny.run import ShinyAppProc


def test_basic_app(page: Page, local_app: ShinyAppProc) -> None:
    """
    Test if app starts as expected.

    In addition, check if it can swap between PSF and Power
    category selections.
    """
    # Navigate to the app URL when it's ready
    page.goto(local_app.url)

    # Swap between categories
    category = ctrl.InputSelect(page, "category")
    category.set("PSF")
    category.set("Power")


def test_better(page: Page, local_app: ShinyAppProc) -> None:
    """
    Test more extensively.

    FYI: this test runs on the local file!
    """
    # Navigate to the app URL when it's ready
    page.goto(local_app.url)

    # Check category choices
    category = ctrl.InputSelect(page, "category")
    category.expect_label("Select a Metrology Category")
    category.expect_choices(["Power", "PSF", "Uniformity/Distortion"])

    # Check site selections
    site = ctrl.InputSelect(page, "site")
    site.expect_label("Select a site")
    site.expect_choices(["Hebelstrasse", "Mattenstrasse", "* New site *"])

    # Check upload password
    pwd = ctrl.InputPassword(page, "upload_pwd")
    pwd.set("shrt")
    pwd_check = ctrl.OutputText(page, "password_check")
    pwd_check.expect_value("")
    pwd.set("definitivelyTheWrongPassword")
    pwd_check.expect_value("Wrong password")

    # Set a sites and check the microscope selections
    site.set("Hebelstrasse")
    mic_sel = ctrl.InputSelect(page, "microscope")
    mic_sel.expect_choices(["Ti2 BSL2", "no_data", "* New microscope *"])
    site.set("Mattenstrasse")
    mic_sel.expect_choices(["Ti CSU-W1", "* New microscope *"])

    # Set microscope and check that objective/info selection are '* new ... *'
    mic_sel.set("* New microscope *")
    obj_sel = ctrl.InputSelect(page, "objective")
    info_sel = ctrl.InputSelect(page, "info")
    obj_sel.expect_selected("* New objective *")
    info_sel.expect_selected("* New info *")

    # Check some OMERO stuff            ######################################
    dataset_id_selector = ctrl.InputText(page, "dataset_id_selector")
    image_id_selector = ctrl.InputSelect(page, "image_id_selector")

    category.set("PSF")
    category.set("Power")
    # Get everything rendered by the function rrender_omero_upload()
    x = ctrl.OutputUi(page, "render_omero_upload")
    # Check the Power category shows not implemented for OMERO
    # If wrong text -> time out error
    x.loc.get_by_text("Power upload from OMERO is not implemented!").wait_for(
        timeout=5000
    )
    assert not dataset_id_selector.loc.is_visible()
    category.set("PSF")
    dataset_id_selector.loc.wait_for(state="visible", timeout=5000)
    assert dataset_id_selector.loc.is_visible()
    assert image_id_selector.loc.is_visible()

    # Check some CSV stuff
    # Still PSF category
    # Need to click the tab, to be able to see a message...
    page.get_by_text("Upload from CSV", exact=True).click()
    category.set("PSF")
    x = ctrl.OutputUi(page, "render_csv_file_selector")
    csv_file_selector = ctrl.InputFile(page, "csv_file_selector")
    # If wrong text -> time out error
    x.loc.get_by_text("PSF upload from CSV is not implemented!").wait_for(
        timeout=15000
    )
    assert csv_file_selector.loc.is_hidden()
    category.set("Power")
    csv_file_selector.loc.wait_for(timeout=5000)
    assert csv_file_selector.loc.is_visible()
    csv_file_selector.expect_label("Choose a .csv or .xlsx file")

    # Set the file to an example file
    table = ctrl.OutputDataFrame(page, "csv_data")
    path = Path(__file__).parent.parent.parent.parent.parent
    path = path / "example_files" / "example_simple_power_measurement.xlsx"
    assert path.exists()
    table.expect_ncol(0)
    table.expect_nrow(0)

    csv_file_selector.set(str(path))
    table.expect_ncol(7, timeout=5000)
    table.expect_nrow(8, timeout=5000)
