"""Test the settings app."""

import pytest
from playwright.sync_api import Page

# from shiny.playwright import controller as ctrl
from shiny.run import ShinyAppProc


@pytest.mark.manual
def test_basic_app(page: Page, local_app: ShinyAppProc) -> None:
    """
    Test if app starts as expected.

    No further tests for the app implemented yet. (FIXME)
    """
    page.goto(local_app.url)
