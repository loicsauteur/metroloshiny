"""Test the testing app."""

from playwright.sync_api import Page
from shiny.run import ShinyAppProc


def test_basic_app(page: Page, local_app: ShinyAppProc) -> None:
    """Check if app can be started."""
    # Navigate to the app URL when it's ready
    page.goto(local_app.url)

    # # Controller objects for interacting with specific Shiny components
    # txt = controller.OutputText(page, "txt")
    # slider = controller.InputSlider(page, "n")

    # # Move the slider to position 55
    # slider.set("55")

    # # Verify that the output text shows "n*2 is 110"
    # # (since 55 * 2 = 110)
    # txt.expect_value("n*2 is 110")
