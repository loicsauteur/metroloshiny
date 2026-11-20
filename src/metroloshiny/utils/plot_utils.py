"""Function for plotting."""

from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
from plotly.graph_objects import Figure


def normalize_percentile(values, low: int = 1, high: int = 99) -> list:
    """Normalize percentile.

    Parameters
    ----------
    values : list, np.array, or df
        Of values
    low : int
        Bottom percentile
    high : int
        Top percentile

    Returns
    -------
    list
        Normalized values
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
    """Normalize a dataframe by min/max values.

    For vector normalization low should be 0, while high the absolute max.

    When no low/high provided, takes the absolute min/max:
        -> max-abs scaling (keeps the symmetry around 0)
        attention in cases where values are all positive,
        normalization low will not be 0.

    Parameters
    ----------
    df : pd.DataFrame
        Input dataframe.
    start_col : int
        First column for normalization. Default = 0
    end_col : int
        Last column for normalization. Default = -1
    low : float
        min. value for normalization
    high : float
        max. value for normalization

    Returns
    -------
    pd.Dataframe
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
    """Show a no data plot with matplotlib.

    For @render.plot

    Parameters
    ----------
    message : str
        To display in the plot.

    Returns
    -------
    matplot fig
    """
    fig, ax = plt.subplots()
    ax.text(0.5, 0.5, message, ha="center", va="center")
    ax.set_axis_off()
    return fig


def no_data_plotly(message: str = "No data to visualise!"):
    """Show a no data plot with plotly.

    For @render_widget

    Parameters
    ----------
    message : str
        To display in the plot.

    Returns
    -------
    plotly.plot
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


def add_center_cross_plotly(
    fig: Figure,
    x_shape: int,
    y_shape: int,
    row: int,
    col: int,
    color: str = "magenta",
    width: float = 1,
    length: float = 1,
    as_x: bool = True,
):
    """Add a centered cross onto a plotly subplot.

    Parameters
    ----------
    fig : plotly Figure
        Subplot
    x_shape : int
        Data shape in x
    y_shape : int
        Data shape in y
    row : int
        Subplot row
    col : int
        Subplot col
    color : str
        Cross color. Default = magenta
    width: float
        Cross line width. Default = 1
    length : float
        Cross arm length (in "XY plot units"). Default = 1
    as_x : bool
        If True (=default) the cross is an X, if False a +
    """
    # Calculate the center locations (off'ed by 0.5 for absolute center)
    cx = (x_shape) / 2 + 0.5
    cy = (y_shape) / 2 + 0.5
    # Define the line-dict
    line = {
        "color": color,
        "width": width,
    }
    # Add a X - cross
    if as_x:
        # 1. Diagonal - top left to bottom right
        fig.add_shape(
            type="line",
            x0=cx - length,
            y0=cy - length,
            x1=cx + length,
            y1=cy + length,
            line=line,
            row=row,
            col=col,
        )
        # 2. Diagonal - top left to bottom right
        fig.add_shape(
            type="line",
            x0=cx - length,
            y0=cy + length,
            x1=cx + length,
            y1=cy - length,
            line=line,
            row=row,
            col=col,
        )
    # Add a + - cross
    else:
        # Horizontal line
        fig.add_shape(
            type="line",
            x0=cx - length,
            y0=cy,
            x1=cx + length,
            y1=cy,
            line=line,
            row=row,
            col=col,
        )
        # Vertical line
        fig.add_shape(
            type="line",
            x0=cx,
            y0=cy - length,
            x1=cx,
            y1=cy + length,
            line=line,
            row=row,
            col=col,
        )


def nm_to_rgb(
    wave: int, gamma: float = 0.8, intensity_max: float = 1.0
) -> list[float]:
    """Convert a wavelength to RGB values.

    Function from https://academo.org/demos/wavelength-to-colour-relationship/

    Parameters
    ----------
    wave : int
        Wavelength in nm
    gamma : float
        Correction factor. Default = 0.8
    intensity_max : float
        Scaling factor (to scale e.g. to values between 0-255). Default = 1

    Returns
    -------
    list[float]
        for RGB values in range 0-1
    """
    # FIXME add min max limits 380-780
    # Base color by wavelength
    if 380 <= wave < 440:
        red = -(wave - 440) / (440 - 380)
        green = 0.0
        blue = 1.0
    elif 440 <= wave < 490:
        red = 0.0
        green = (wave - 440) / (490 - 440)
        blue = 1.0
    elif 490 <= wave < 510:
        red = 0.0
        green = 1.0
        blue = -(wave - 510) / (510 - 490)
    elif 510 <= wave < 580:
        red = (wave - 510) / (580 - 510)
        green = 1.0
        blue = 0.0
    elif 580 <= wave < 645:
        red = 1.0
        green = -(wave - 645) / (645 - 580)
        blue = 0.0
    elif 645 <= wave < 781:
        red = 1.0
        green = 0.0
        blue = 0.0
    else:
        red = green = blue = 0.0

    # Let the intensity fall off near the vision limits
    if 380 <= wave < 420:
        factor = 0.3 + 0.7 * (wave - 380) / (420 - 380)
    elif 420 <= wave < 701:
        factor = 1.0
    elif 701 <= wave < 781:
        factor = 0.3 + 0.7 * (780 - wave) / (780 - 700)
    else:
        factor = 0.0

    def scale(c):
        return round(intensity_max * (c * factor) ** gamma, 2) if c != 0 else 0

    return [scale(red), scale(green), scale(blue)]
