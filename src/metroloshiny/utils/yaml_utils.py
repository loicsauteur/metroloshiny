"""YAML utils for writing and reading long term power measurements.

Writing long (/short) term power measurement yaml files:
- all files will be in the same directory
- 1 file per measurement, e.g.:
  ./dirfordata/site__mic__i{interval}__w{wave}__d{date}.yaml
- YAML files contain key-value pairs for:
  - site
  - microscope
  - objective
  - interval (corresponds to Info column in google sheet)
  - wavelength
  - date
  - Time (s): list
  - Power (mW): list
"""

from pathlib import Path
from typing import Any

import pandas as pd
import yaml


def create_long_term_power_file_path(
    path: str,
    site: str,
    microscope: str,
    objective: str,
    interval: float,
    wavelength: float,
    date: str,
) -> str:
    """Create the YAML file path for the long term power measurement.

    Parameters
    ----------
    path : str
        Path to folder containing the file.
    site : str
        Site name
    microscope : str
        Microscope name
    objective : str
        Objective name
    interval : float
        Measurement interval in s
    wavelength : int
        Wavelength in nm
    date : str
        Acquisition date (YYYYMMDD)

    Returns
    -------
    str
        Absolute path to file

    Raises
    ------
    IOError
        If path is not a directory
    """
    if not Path(path).is_dir():
        raise IOError(f"Path is not a directory {path}")
    file = (
        Path(path)
        / f"{site}__{microscope}__o{objective}__i{interval}__w{wavelength}__d{date}.yaml"
    )
    return str(file.absolute())


def read_long_term_power_yaml(
    path: str,
    site: str,
    microscope: str,
    objective: str,
    interval: float,
    wavelength: float,
    date: str,
) -> pd.DataFrame:
    """Read a long term power meeasurement YAML file.

    Parameters
    ----------
    path : str
        Path to folder containing the file.
    site : str
        Site name
    microscope : str
        Microscope name
    objective : str
        Objective name
    interval : float
        Measurement interval in s
    wavelength : int
        Wavelength in nm
    date : str
        Acquisition date (YYYYMMDD)

    Returns
    -------
    pd.DataFrame
        with columns:
        - Time (s)
        - Power (mW)
    """
    # Build the file path
    file = create_long_term_power_file_path(
        path, site, microscope, objective, interval, wavelength, date
    )
    # FYI: open will raise FileNotFoundError
    with open(file) as f:
        doc = yaml.safe_load(f)
    df = pd.DataFrame(
        {"Time (s)": doc["Time (s)"], "Power (mW)": doc["Power (mW)"]}
    )
    return df


def power_dataframe_to_yaml(
    path: str,
    df: pd.DataFrame,
    site: str,
    microscope: str,
    objective: str,
    interval: float,
    wavelength: int,
    date: str,
    overwrite: bool = False,
) -> str:
    """Convert long term power measurements to YAML.

    Parameters
    ----------
    path : str
        Path to folder containing the YAML file.
        E.g. ./data for the file in
        ./data/site__microscope__i{interval}__w{wavelength}__d{date}.yaml
    df : pd.DataFrame
        with columns:
        - Time (s)
        - Power (mW)
    site : str
        Site name
    microscope : str
        Microscope name
    objective : str
        Objective name
    interval : float
        Measurement interval in s
    wavelength : int
        Wavelength in nm
    date : str
        Acquisition date (YYYYMMDD)
    overwrite : bool
        Overwrites an existing file. Default = False

    Returns
    -------
    str
        Absolute path to the written file

    Raises
    ------
    KeyError
        If dataframe does not have expected columns
    ValueError
        If dataframe has not expcected number of columns
    """
    # Checks
    if "Time (s)" not in df.columns:
        raise KeyError("DataFrame does not contain a 'Time (s)' column")
    if "Power (mW)" not in df.columns:
        raise KeyError("DataFrame does not contain a 'Power (mW)' column")
    if len(df.columns) != 2:
        raise ValueError(
            f"Only DataFrames with 2 columns supported. This one had {len(df.columns)}."
        )
    file_path = create_long_term_power_file_path(
        path, site, microscope, objective, interval, wavelength, date
    )
    if Path(file_path).exists() and not overwrite:
        raise FileExistsError("The measurement file already exists.")

    # Create the yaml document
    doc: dict[str, Any] = {
        "site": site,
        "microscope": microscope,
        "objective": objective,
        "interval": float(interval),
        "wavelength": int(wavelength),
        "date": str(date),
    }
    for col in df.columns:
        doc[col] = FlowList(df[col].tolist())

    # Add a represent to YAML Dumper
    yaml.SafeDumper.add_representer(FlowList, flow_list_representer)

    with open(file_path, "w") as file:
        yaml.dump(
            doc,
            file,
            Dumper=yaml.SafeDumper,
            sort_keys=False,
            width=float("inf"),
        )
    return file_path


class FlowList(list):
    """List subclass that is serialized in YAML flow style.

    Wrap a list in this class before dumping to get the compact
    ``[a, b, c]`` form instead of one item per line. Requires
    ``flow_list_representer`` to be registered on the dumper.
    """


def flow_list_representer(dumper: yaml.Dumper, data: list):
    r"""Represent a list in YAML flow style (single-line, e.g. ``[1, 2, 3]``).

    Intended to be registered as a representer for a list subclass such as
    ``FlowList``, so that only those lists are written in flow style while
    all other lists keep the default block style.

    Parameters
    ----------
    dumper : yaml.Dumper
        The PyYAML dumper instance that is currently serializing the data.
    data : list
        The list (or list subclass) to serialize.

    Returns
    -------
    yaml.nodes.SequenceNode
        A YAML sequence node with ``flow_style=True``.

    Examples
    --------
    >>> yaml.SafeDumper.add_representer(FlowList, flow_list_representer)
    >>> yaml.dump({"x": FlowList([1, 2, 3])}, Dumper=yaml.SafeDumper)
    'x: [1, 2, 3]\n'
    """
    return dumper.represent_sequence(
        "tag:yaml.org,2002:seq", data, flow_style=True
    )
