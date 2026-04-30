"""Utils for common usage."""

import datetime
from collections import defaultdict
from typing import Optional

from bs4 import BeautifulSoup


def get_ui_id(input) -> str:
    """
    Return the ID string from an ui.input* object.

    :param input: ui.input* object

    :return: str id of ui.input* object
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
    """
    Check if a input_select (id) is in a list.

    :param l: list of input_select objects
    :param id: str id of searched input_select

    :return: bool if in the list
    """
    for i in l:
        if get_ui_id(i) == id:
            return True
    return False


def theo_fwhm(
    em: int, na: float, ri: float, k: float = 2.0
) -> tuple[float, float]:
    """
    Calculate theoretical lateral and axial FWHM.

    FHMWlat = 0.61 * em / NA
    FHMWax = 2 * ri * em / NA^2

    :param em: Emission wavelength in nm (int).
    :param na: NA of the objective.
    :param ri: Refractive index of objective.
    :param k: Constant for axial FHMW. Default = 2.0 (widefield),
              set to 1.4 for confocal.

    :return: tuple (FHMW lateral, FHMW axial) in nm.
    """
    lat = 0.61 * em / na
    ax = k * ri * em / (na * na)
    return lat, ax


def theo_fwhm_quarep(ex: int, na: float, ri: float) -> tuple[float, float]:
    """
    Calculate theoretical lateral and axial FWHM with QUAREP formula.

    Using the formulas found in the QUAREP PSF protocols.io:
    https://dx.doi.org/10.17504/protocols.io.bp2l61ww1vqe/v1

    FHMWlat = 0.51 * ex / NA
    FHMWax = 0.88 * ex / (ri -(ri^2 - NA^2)^1/2)

    :param em: Emission wavelength in nm (int).
    :param na: NA of the objective.
    :param ri: Refractive index of objective.
    :param k: Constant for axial FHMW. Default = 2.0 (widefield),
              set to 1.4 for confocal.

    :return: tuple (FHMW lateral, FHMW axial) in nm.
    """
    lat = 0.51 * ex / na
    ax = 0.88 * ex / (ri - (ri**2 - na**2) ** 0.5)
    return lat, ax


def get_today() -> str:
    """
    Get today's date in formate YYYYMMDD.

    :return: str
    """
    today = datetime.date.today()
    today = today.strftime("%Y%m%d")
    return today


def check_duplicate_dict_values(
    d: dict[str, str], exclude: Optional[str] = "None"
) -> Optional[dict]:
    """
    Check if a dictionary contains duplicate values.

    Used for checking if a channel identifier (C1 = values)
    was selected for multiple channel names (DAPI/GFP = keys)

    :param d: dict with single str for keys and values.
    :param exclude: Optional str, to exclude a specific value item.

    :return: None if no duplicate,
        otherwise a dict of the first duplicate value.
    """
    # Group keys by value
    groups = defaultdict(list)
    for k, v in d.items():
        if v != exclude:
            groups[v].append(k)
    # Return key & value for first item that has mulitple values
    for k, v in groups.items():
        if len(v) > 1:
            return {k: v}
    return None


if __name__ == "__main__":
    d = {"DAPI": "C1", "GFP": "None", "Cy3": "C2", "Cy5": "None"}
    a = check_duplicate_dict_values(d=d, exclude="None")
    print("found duplicate:", a, type(a))
