"""Test the PSF app."""

from playwright.sync_api import Page
from shiny.run import ShinyAppProc

# from shiny.playwright import controller as ctrl


def test_basic_app(page: Page, local_app: ShinyAppProc) -> None:
    """Test if app starts as expected."""
    # Navigate to the app URL when it's ready
    page.goto(local_app.url)
