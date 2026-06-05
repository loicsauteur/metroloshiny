"""
Example testing app.

Example from: https://shiny.posit.co/py/docs/end-to-end-testing.html
"""

from shiny.express import input, render, ui

ui.panel_title("Hello Shiny!")
ui.input_slider("n", "N", 0, 100, 20)


@render.text
def txt():
    """Render calculation as text."""
    return f"n*2 is {input.n() * 2}"
