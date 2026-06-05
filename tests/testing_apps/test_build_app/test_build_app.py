"""Test the test build app."""

from playwright.sync_api import Page
from shiny.playwright import controller as ctrl
from shiny.run import ShinyAppProc

# from app import set_to_local_for_test # cant do that


def test_basic_app(page: Page, local_app: ShinyAppProc) -> None:
    """
    Test the app, build similarly to my other apps.

    This was for testing pytest purposes.
    """
    # Navigate to the app URL when it's ready
    page.goto(local_app.url)

    # Swap between categories
    category = ctrl.InputSelect(page, "category")
    category.set("PSF")
    category.set("Power")
    # category.set("NotAnOption") # gives a timeout

    # I cannot call functions of my app, e.g. to swap to a local file instead
    # of gspread, because if I import a function, the app is build.
    # I cant wrap the app build to be called, as it must be a stand alone
    # i.e. this does not work!
    #  - wrap the app building into a function,
    #  - rename the file (core_app.py)
    #  - create new app.py and call the build_wrapper
