"""Function for plotting."""

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px


def normalize_percentile(values, low: int = 1, high: int = 99) -> list:
    """
    Normalise percitenile.

    :param values: list, np.array, df, of values
    :param low: int, bottom percentile
    :param high: int, top percentile

    :return: list, normalised values
    """
    vmin, vmax = np.nanpercentile(values, q=[low, high])
    return np.clip((values - vmin) / (vmax - vmin), a_min=0, a_max=1)


def no_data_seaborn(message: str = "No data to visualise!"):
    """
    Show a no data plot with matplotlib.

    For @render.plot

    :param message: str, to display in the plot.

    :return: matplot fig
    """
    fig, ax = plt.subplots()
    ax.text(0.5, 0.5, message, ha="center", va="center")
    ax.set_axis_off()
    return fig


def no_data_plotly(message: str = "No data to visualise!"):
    """
    Show a no data plot with plotly.

    For @render_widget

    :param message: str, to display in the plot.

    :return: plotly.plot
    """
    fig = px.line(pd.DataFrame({"x": [], "y": []}), x="x", y="y")
    fig.add_annotation(
        text=message,
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"size": 20, "color": "gray"},
    )
    fig.update_layout(template="simple_white", showlegend=False)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig
