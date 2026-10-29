"""Utils for common usage."""

import datetime
import os
from collections import Counter, defaultdict
from importlib.metadata import version
from typing import Optional, Union

import numpy as np
import pandas as pd
from bs4 import BeautifulSoup


def get_version() -> str:
    """Get the metroloshiny version."""
    return version("metroloshiny")[:11]


def get_ui_id(input) -> str:
    """Return the ID string from an ui.input* object.

    Parameters
    ----------
    input : ui.input* object
        The ui.input object

    Returns
    -------
    str
        ID of ui.input* object
    """
    soup = BeautifulSoup(str(input), "html.parser")
    try:
        id_str = soup.find("label")["for"]
    except Exception as err:
        raise RuntimeError(
            "Could not identify the selection input label."
        ) from err
    return str(id_str)


def is_input_select_in_list(l: list, id: str) -> bool:
    """Check if a input_select (id) is in a list.

    Parameters
    ----------
    l : list
        Of input_select objects
    id : str
        ID of searched input_select

    Returns
    -------
    bool
        If the id is in the list
    """
    for i in l:
        if get_ui_id(i) == id:
            return True
    return False


def theo_fwhm_2photon(ex: int, na: float, ri: float) -> tuple[float, float]:
    """Calculate theoretical lateral and axial FWHM for point scanning confocals.

    Using Zipfel, W.R. et al, Nonlinear magic: multiphoton microscopy
    in the biosciences Nat Biotechnol. 2003 Nov;21(11):1369-77
    doi = https://doi.org/10.1038/nbt899
    -> also used/referenced by MetroloJ_QC v1.3.1.1 Oct 21. 2024, but formula
    seems to vary...

    FHMWlat NA<=0.7 = 0.320 * ex / (2^0.5 * NA)
    FHMWlat NA>0.7  = 0.325 * ex / (2^0.5 * NA^0.91)
    FHMWax          = 0.532 * ex / (2^0.5 (n - (n^2 - NA^2)^0.5) )
    *ex wavelength is multiplied by 2 because of 2-photons.

    Parameters
    ----------
    ex : int
        Excitation wavelength in nm.
        For calculation using the emission wavelength
        40nm are added to the excitation wavelength.
    na : float
        NA of the objective.
    ri : float
        Refractive index of objective.

    Returns
    -------
    float
        FHMW lateral in nm.
    float
        FHMW axial in nm.
    """
    if na <= 0.7:
        lat = 0.32 * ex * 2 / (2**0.5 * na)
    else:
        lat = 0.325 * ex * 2 / (2**0.5 * na**0.91)
    ax = 0.532 * ex * 2 / (2**0.5 * (ri - (ri * ri - na * na) ** 0.5))
    return round(lat, 2), round(ax, 2)


def theo_fwhm_spinning(ex: int, na: float, ri: float) -> tuple[float, float]:
    """Calculate theoretical lateral and axial FWHM for point scanning confocals.

    Using the MetroloJ_QC v1.3.1.1 Oct 21. 2024:
    https://github.com/MontpellierRessourcesImagerie/MetroloJ_QC/blob/Current_version/manual.pdf
    Which references:
    Toomre, D. and Pawley J.B. Disk-Scanning Confocal Microscopy.
    in Handbook Of Biological Confocal Microscopy 2006 221-238 (Springer)

    FHMWlat = 0.51 * em / NA
    FHMWax  = em / (ri - (ri^2 - NA^2)^0.5)

    Parameters
    ----------
    ex : int
        Excitation wavelength in nm.
        For calculation using the emission wavelength
        40nm are added to the excitation wavelength.
    na : float
        NA of the objective.
    ri : float
        Refractive index of objective.

    Returns
    -------
    float
        FHMW lateral in nm.
    float
        FHMW axial in nm.
    """
    em = ex + 40
    lat = 0.51 * em / na
    ax = em / (ri - (ri * ri - na * na) ** 0.5)
    return round(lat, 2), round(ax, 2)


def theo_fwhm_pointscanner(
    ex: int, na: float, ri: float
) -> tuple[float, float]:
    """Calculate theoretical lateral and axial FWHM for point scanning confocals.

    Using the MetroloJ_QC v1.3.1.1 Oct 21. 2024:
    https://github.com/MontpellierRessourcesImagerie/MetroloJ_QC/blob/Current_version/manual.pdf
    Which references:
    Wilhelm, S. Confocal Laser Scanning Microscopy. 2011 (Carl Zeiss ed),
    Amos, B. et al, Confocal Microscopy.
    in Handbook of Comprehensive Biophysics 2012 3-23 (Elsevier).

    FHMWlat = 0.51 * ex / NA
    FHMWax  = 0.88 * ex / (ri - (ri^2 - NA^2)^0.5)

    Parameters
    ----------
    ex : int
        Excitation wavelength in nm.
        For calculation using the emission wavelength
        40nm are added to the excitation wavelength.
    na : float
        NA of the objective.
    ri : float
        Refractive index of objective.

    Returns
    -------
    float
        FHMW lateral in nm.
    float
        FHMW axial in nm.
    """
    lat = 0.51 * ex / na
    ax = 0.88 * ex / (ri - (ri * ri - na * na) ** 0.5)
    return round(lat, 2), round(ax, 2)


def theo_fwhm_widefield(ex: int, na: float, ri: float) -> tuple[float, float]:
    """Calculate theoretical lateral and axial FWHM for widefield system.

    Using the MetroloJ_QC v1.3.1.1 Oct 21. 2024:
    https://github.com/MontpellierRessourcesImagerie/MetroloJ_QC/blob/Current_version/manual.pdf
    Which references:
    Wilhelm, S. Confocal Laser Scanning Microscopy 2011 (Carl Zeiss ed.).

    FHMWlat = 0.51 * em / NA
    FHMWax  = 1.77 * ri * em / NA^2

    Parameters
    ----------
    ex : int
        Excitation wavelength in nm.
        For calculation using the emission wavelength
        40nm are added to the excitation wavelength.
    na : float
        NA of the objective.
    ri : float
        Refractive index of objective.

    Returns
    -------
    float
        FHMW lateral in nm.
    float
        FHMW axial in nm.
    """
    em = ex + 40
    lat = 0.51 * em / na
    ax = 1.77 * ri * em / (na * na)
    return round(lat, 2), round(ax, 2)


def theo_fwhm_quarep(ex: int, na: float, ri: float) -> tuple[float, float]:
    """Calculate theoretical lateral and axial FWHM with QUAREP formula.

    Using the formulas found in the QUAREP PSF protocols.io (v1, page 12):
    https://quarep.org/wp-content/uploads/Monitoring-the-point-spread-function-for-quality-for-quality-control-of-confocal-microscopes.pdf
    Which are the formulas from MetroloJ_QC for confocal point scanners.

    FHMWlat = 0.51 * ex / NA
    FHMWax = 0.88 * ex / (ri -(ri^2 - NA^2)^1/2)

    Parameters
    ----------
    ex : int
        Excitation wavelength in nm.
    na : float
        NA of the objective.
    ri : float
        Refractive index of objective.

    Returns
    -------
    float
        FHMW lateral in nm.
    float
        FHMW axial in nm.
    """
    lat = 0.51 * ex / na
    ax = 0.88 * ex / (ri - (ri**2 - na**2) ** 0.5)
    return round(lat, 2), round(ax, 2)


def get_today() -> str:
    """Get today's date in format YYYYMMDD.

    Returns
    -------
    str
    """
    today = datetime.date.today()
    today = today.strftime("%Y%m%d")
    return today


def check_if_date(date: str) -> bool:
    """Check if a string can be converted to a date.

    Expects date string in format YYYYmmdd.

    Parameters
    ----------
    date : str
        Of possible date

    Returns
    -------
    bool
        True if it can be a date
    """
    try:
        datetime.datetime.strptime(date, "%Y%m%d")
        return True
    except ValueError:
        return False


def check_duplicate_dict_values(
    d: dict[str, str], exclude: Optional[str] = "None"
) -> Optional[dict]:
    """Check if a dictionary contains duplicate values.

    Used for checking if a channel identifier (C1 = values)
    was selected for multiple channel names (DAPI/GFP = keys)

    Parameters
    ----------
    d : dict
        With single str for keys and values.
    exclude : Optional str
        To exclude a specific value item.

    Returns
    -------
    Optional[dict]
        None if no duplicate,
        otherwise a dict of the first duplicate value.
    """
    # Group keys by value
    groups = defaultdict(list)
    for k, v in d.items():
        if v != exclude:
            groups[v].append(k)
    # Return key & value for first item that has multiple values
    for k, v in groups.items():
        if len(v) > 1:
            return {k: v}
    return None


@DeprecationWarning
def invert_nested_dict(nested_dict: dict) -> dict:
    """Invert nested dicts to {value: path of keys}.

    ! Deprecated !

    Parameters
    ----------
    nested_dict : dict
        e.g. {
            "C1" : {'FWHM-X': 911.0, 'FWHM-Y': 852.0, 'FWHM-Z': 1260.0}
        }

    Returns
    -------
    dict
        e.g. {
            911.0:  ['C1', 'FWHM-X']
            852.0:  ['C1', 'FWHM-Y']
            1260.0: ['C1', 'FWHM-Z']
        }

    Raises
    ------
    KeyError
        If the final value happens to occur more than once.
    """
    inverted = defaultdict(list)

    def walk(current, path):
        """Walk the nested dicts."""
        if isinstance(current, dict):
            for k, v in current.items():
                walk(v, (*path, k))
        else:
            if current in inverted.keys():
                raise KeyError(
                    "Failed to invert the nested dict, because the value "
                    f"{current} happens to occur multiple times..."
                )
            inverted[current].append(path)

    walk(nested_dict, ())
    inverted = dict(inverted)
    # Convert the dict values list[tuple] to list
    for k, v in inverted.items():
        inverted[k] = list(v[0])
    return dict(inverted)


def check_if_sequence(seq: list[str]) -> bool:
    """Check if a list of strings of cell addresses is continuous.

    True for: [A1, A2, B3, ...]
    False for [A1, A3, B4, ...]

    Parameters
    ----------
    seq : list[str]
        Of cell addresses

    Returns
    -------
    bool
    """
    # Remove characters from strings to keep only numbers
    numbers = []
    for num in seq:
        s = list(num)
        i = 0
        while i < len(s):
            # Remove capital characters via ASCII value
            if ord(s[i]) >= ord("A") and ord(s[i]) <= ord("Z"):
                del s[i]
                i = i - 1
            i = i + 1
        s = "".join(s)
        numbers.append(s)
    # Check if the sequence is continuous
    for i in range(1, len(numbers)):
        try:
            cur = int(numbers[i])
            prev = int(numbers[i - 1])
            if prev != cur - 1:
                return False
        except ValueError as err:
            raise ValueError(
                f"Could not parse <{numbers[i]}> or "
                f"<{numbers[i - 1]}> to integer for "
                "checking if cell addresses are continuous."
            ) from err
    return True


def list_duplicates(arr: list) -> list:
    """Get a list of duplicate items within a list.

    Parameters
    ----------
    arr : list
        Of values

    Returns
    -------
    list
        Of duplicate values (may be empty)
    """
    dup = [i for i, count in Counter(arr).items() if count > 1]
    return dup


def set_local_file(default: Optional[bool] = False) -> bool:
    """Return True if in pytest.

    Used for setting local file usage (excel sheet instead of google sheet).

    Parameters
    ----------
    default : Optional bool
        If True returns True.
        To overwrite the logic.

    Returns
    -------
    bool
    """
    if default:
        if os.environ.get("PYTEST_VERSION") is not None:
            raise RuntimeError(
                "Local file is set to TRUE during pytest: "
                "Probably forgot to reset to the default!"
            )
        else:
            return default
    if os.environ.get("PYTEST_VERSION") is not None:
        return True
    else:
        return False


def create_css_color_dict(
    range_list: list,
    min_val: Optional[int] = 380,
    max_val: Optional[int] = 700,
) -> dict:
    """Map input values do CSS colors.

    To create color dictionaries for plotly plots (up to 14 colors).
    Suggestion: use it only for matching colors to wavelength values.

    Parameters
    ----------
    range_list : list
        Of numbers to map colors to.
    min_val : int
        Lowest input number to map color to.
        Default 380. If None, will check min value of the input array.
    max_val : int
        Highest input number to map color to.
        Default 700. If None, will check max value of the input array.

    Returns
    -------
    dict
        key = input numbers, values = CSS color names.
        Returns empty dict if request color number > max color numbers
    """
    # Make sure all values are numbers
    try:
        range_list = [float(x) for x in range_list]
    except ValueError as err:
        raise ValueError(
            f"Range values must be numbers. Input: {range_list}"
        ) from err

    # Set min max values if None
    min_v = min(range_list) if min_val is None else min_val
    max_v = max(range_list) if max_val is None else max_val
    if min_val is None:
        min_val = min(range_list)
    if max is None:
        max_val = max(range_list)
    if min_v >= max_v:
        raise ValueError(f"Min <{min_v}> must be smaller than max <{max_v}>!")
    # Re-adjust min/max if inputs are lower/higher than current - dont do that
    # if min_val > min(range_list):
    #     min_val = min(range_list)
    # if max_val < max(range_list):
    #     max_val = max(range_list)

    # Make sure only unique input values
    range_list.sort()
    range_list = list(np.unique(np.asarray(range_list)))

    # My default color range (14 colors in total)
    all_colors = {
        0: "indigo",
        0.08: "purple",
        0.15: "mediumblue",
        0.23: "dodgerblue",
        0.30: "aqua",
        0.38: "darkturquoise",
        0.46: "springgreen",
        0.54: "green",
        0.62: "olive",
        0.69: "gold",
        0.77: "orange",
        0.885: "tomato",
        0.92: "red",
        1: "darkred",
    }
    # TODO: maybe would be good to check if all colors really exist:
    # https://plotly.com/python/css-colors/

    # Return an empty dict if requested colors > max colors
    valid_range = [x for x in range_list if x >= min_v and x <= max_v]
    if len(valid_range) > len(all_colors):
        return {}

    # Normalise the input numbers to values 0-1
    norm_range = [(x - min_v) / (max_v - min_v) for x in range_list]
    # Distribute colors more evenly, if n input numbers close to max colors
    # Dont do that either...
    # valid_range = [x for x in range_list if x >= min_val and x <= max_val]
    # if len(valid_range) >= 8:
    #     print("distributing evenly")
    #     norm_range = [0 for x in range_list if x < min_val]
    #     for i in np.linspace(0, 1, len(valid_range)):
    #         norm_range.append(i)
    #     for i in range_list:
    #         if i > max_val:
    #             norm_range.append(i)

    # if len(norm_range) != len(range_list):
    #     raise RuntimeError(
    #         "Something went wrong! I did a logic error..."
    #     )

    dict_out = {}
    for i in range(len(range_list)):
        closes_color = min(
            all_colors.keys(), key=lambda x: abs(x - norm_range[i])
        )
        dict_out[range_list[i]] = all_colors.get(closes_color)

    return dict_out


def get_objective_info(
    df: pd.DataFrame, id_name: str, info: str
) -> Union[str, int, float]:
    """Load any of the values from the objective database for an objective.

    Parameters
    ----------
    df : pd.DataFrame
        Of the objecive database
    id_name : str
        Objective id number, e.g. "ID17" or "ID17 40x/1.3".
        Should/must always start with "ID"
    info : str
        Any of the column headers of the objecitve database

    Returns
    -------
    Union[str, int, float]
        the value for row with "id" and column "info"
    """
    # Make sure it is the correct dataframe
    if "ID" != df.columns[0]:
        raise RuntimeError(
            "The dataframe does not seem to be the objecive database."
        )
    # Make sure the "info" is in the dataframe
    if info not in df.columns:
        raise KeyError(
            f"<{info}> is not a valid key for the objective database. "
            f"Please use: {df.columns[1:]}"
        )
    # Allow IDs with spaces (ID1 40x/0.5)
    if " " in id_name:
        id_name = id_name.split(" ", maxsplit=1)[0]
    # Check that the requested ID is in the df
    if id_name not in df["ID"].values:
        raise ValueError(
            f"The ID <{id_name}> is not present in the objective database."
        )

    return df.loc[df["ID"] == id_name, info].iloc[0]


def get_objective_na(df: pd.DataFrame, id_name: str) -> Optional[float]:
    """Get the NA for objective in the database.

    Parameters
    ----------
    df : pd.DataFrame
        Of the objecive database
    id_name : str
        Objective id number, e.g. "ID17" or "ID17 40x/1.3".
        Should/must always start with "ID"

    Returns
    -------
    Optional[float]
        NA of the objective, or None if parsing error
    """
    # Get the NA of the objective
    try:
        na = get_objective_info(df, id_name, "NA")
    except ValueError as err:
        # Objective not in database
        raise RuntimeError(str(err)) from err
    # Make sure the return value is a number
    try:
        na = float(na)
    except ValueError:
        return None
    return na


def get_objective_ri(df: pd.DataFrame, id_name: str) -> Optional[float]:
    """Get the refractive index for objective in the database.

    Parameters
    ----------
    df : pd.DataFrame
        Of the objecive database
    id_name : str
        Objective id number, e.g. "ID17" or "ID17 40x/1.3".
        Should/must always start with "ID"

    Returns
    -------
    Optional[float]
        RI of the objective, or None if parsing error
    """
    try:
        ri = get_objective_info(df, id_name, "Refractive Index")
    except ValueError as err:
        # Objective not in database
        raise RuntimeError(str(err)) from err
    # Make sure the return value is a number
    try:
        ri = float(ri)
    except ValueError:
        return None
    return ri


def get_objective_mag(df: pd.DataFrame, id_name: str) -> Optional[int]:
    """Get the magnification for objective in the database.

    Parameters
    ----------
    df : pd.DataFrame
        Of the objecive database
    id_name : str
        Objective id number, e.g. "ID17" or "ID17 40x/1.3".
        Should/must always start with "ID"

    Returns
    -------
    Optional[int]
        magnification of the objective, or None if parsing error
    """
    try:
        x = get_objective_info(df, id_name, "Magnification")
    except ValueError as err:
        # Objective not in database
        raise RuntimeError(str(err)) from err
    # Make sure the return value is a number
    x = str(x).lower().strip("x")
    try:
        x = int(float(x))
    except ValueError:
        return None
    return x


def get_nice_objective_name(df: Optional[pd.DataFrame], id_name: str) -> str:
    """Get a nice name for an objective in the database.

    Returns e.g. 40x/1.25 (ID1)
        if id_name not in database, returns ?x/? (ID1)
        if id_name does not start with "ID", returns input id_name

    Parameters
    ----------
    df : pd.DataFrame
        Of the objective database
    id_name : str
        Objective ID

    Returns
    -------
    str
        e.g. "40x/1.25 (ID1)"
    """
    # Allow inputs with more than just the ID number
    if " " in id_name:
        id_name = id_name.split(" ", maxsplit=1)[0]
    if not id_name.startswith("ID"):
        return id_name
    # Sanity check -> return input name if there is no dataframe
    if df is None or df.empty:
        return id_name
    try:
        mag = get_objective_mag(df, id_name)
    except RuntimeError:
        mag = None
    try:
        na = get_objective_na(df, id_name)
    except RuntimeError:
        na = None
    if mag is None:
        mag = "?"
    if na is None:
        na = "?"
    return f"{mag}x/{na} ({id_name})"


def point_2d_point_distance(
    p1: Union[tuple[float, float], list[float]],
    p2: Union[tuple[float, float], list[float]],
) -> float:
    """Calculate the distance between 2 points.

    Parameters
    ----------
    p1 : list[float, float]
        XY of point 1
    p2 : list[float, float]
        XY of point 1

    Returns
    -------
    float
        distance
    """
    # 3D points not implemented
    if len(p1) == 3 and len(p2) == 3:
        raise NotImplementedError("3D point distance is not implemented.")
    # Sanity test
    if 2 != len(p1) or len(p2) != 2:
        raise ValueError(
            "The point list do not have XY coordinates (!= len = 2)"
        )
    try:
        x = float(p1[0])
        y = float(p1[1])
        p1 = (x, y)
        x = float(p2[0])
        y = float(p2[1])
        p2 = (x, y)
    except ValueError as err:
        raise ValueError(
            f"Could not parse points <{p1}; {p2}> to numbers."
        ) from err
    # Calculate the distance
    return ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) ** 0.5


def identify_date_format(text: str) -> str:
    """Identify the date format from a string.

    Find the datetime compatible format.

    Parameters
    ----------
    text : str
        The format enclosed in brackets "()".
        E.g., "Date (MM/dd/yyyy)"

    Returns
    -------
    str
        datetime compatible format. E.g. "%m/%d/%Y"

    Raises
    ------
    ValueError
        - If text does not have brackets
        - Or not a valid date format (not containing m, d, or y)
    RuntimeError
        If date identifiers are not 3 and separators are not 2 or 0.
    """
    if "(" not in text or ")" not in text:
        raise ValueError(
            "Cannot parse dateformat from input as it does not have brackets."
        )

    text = text.split(")", maxsplit=1)[0]
    text = text.rsplit("(", maxsplit=1)[-1].lower()
    ids = []
    separators = []
    for c in text:
        if c.isalpha():
            if c not in ids:
                ids.append(c)
        else:
            separators.append(c)
    # Sanity checks
    if len(ids) != 3 or (len(separators) != 2 and len(separators) != 0):
        raise RuntimeError(f"Could not identify format for: {text}")
    if not all(c in ids for c in ["m", "d", "y"]):
        raise ValueError(f"Not a valid date format ({text})")

    dform = ""
    for idx, i in enumerate(ids):
        if i == "y":
            dform = dform + "%Y"
        else:
            dform = dform + f"%{i}"
        if idx < 2 and len(separators) == 2:
            dform = dform + separators[idx]
    return dform


def identify_time_format(text: str) -> str:
    """Identify the time format from a string.

    Find the datetime compatible format.

    Parameters
    ----------
    text : str
        The format enclosed in brackets "()".
        E.g., "Time (hh:mm:ss)"

    Returns
    -------
    str
        datetime compatible format. E.g. "%H:%M:%S"

    Raises
    ------
    ValueError
        - If text does not have brackets
        - Or not a valid date format (not containing h, m or s)
    RuntimeError
        If date identifiers are not 3 and separators are not 2 or 0.
    """
    if "(" not in text or ")" not in text:
        raise ValueError(
            "Cannot parse timeformat from input as it does not have brackets."
        )

    text = text.split(")", maxsplit=1)[0]
    text = text.rsplit("(", maxsplit=1)[-1].lower()
    ids = []
    separators = []
    for c in text:
        if c.isalpha():
            if c not in ids:
                ids.append(c)
        else:
            separators.append(c)
        if len(ids) == 3:
            break
    # Sanity checks
    if len(ids) < 3 or len(separators) != 2:
        raise RuntimeError(f"Could not identify format for: {text}")
    if not all(c in ids for c in ["m", "h", "s"]):
        raise ValueError(f"Not a valid time format ({text})")

    dform = ""
    for idx, i in enumerate(ids):
        dform = dform + f"%{i.upper()}"
        if idx < 2:
            dform = dform + separators[idx]
    return dform


if __name__ == "__main__":
    pass
