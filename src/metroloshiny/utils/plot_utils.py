"""Function for plotting."""

from typing import Optional

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


def normalize_df(
    df: pd.DataFrame,
    start_col: int = 0,
    end_col: int = -1,
    low: Optional[float] = None,
    high: Optional[float] = None,
) -> pd.DataFrame:
    """
    Normalize a dataframe by min/max values.

    :param df: pd.DataFrame
    :param start_col: int, first column for normalization. Default = 0
    :param end_col: int, last column for normalization. Default = -1
    :param low: float, min. value for normalization
    :param high: float, max. value for normalization

    :return: pd.Dataframe
    """
    if end_col != -1 and start_col > end_col:
        raise ValueError("start_col cannot be bigger than end_col.")
    # Make the end_col parameter inclusive
    if end_col == -1:
        df_copy = df.iloc[:, start_col:].copy()
    elif end_col + 1 >= len(df.columns):
        df_copy = df.iloc[:, start_col:].copy()
    else:
        df_copy = df.iloc[:, start_col : end_col + 1].copy()

    # Get the min max values
    if low is None:
        if len(df_copy.columns) == 1:
            low = df_copy.abs().min().values[0]
        else:
            low = df_copy.abs().min().min()
    if high is None:
        if len(df_copy.columns) == 1:
            high = df_copy.abs().max().values[0]
        else:
            high = df_copy.abs().max().max()

    if low == high and low == 0:
        # All values are the same
        # In case of 0's don't normalize
        return df
    # Normalize
    if low == high:
        # (low/high =! 0) -> normalize to all 1's
        df_copy = df_copy / low
    else:
        df_copy = (df_copy - low) / (high - low)

    df_out = df.copy()
    for col in df_copy.columns:
        df_out[col] = df_copy[col]
    return df_out


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
