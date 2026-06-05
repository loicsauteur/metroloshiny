"""Test the data upload app."""

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
