"""Utils for common usage."""

import datetime
from collections import Counter, defaultdict
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


def theo_fwhm_2photon(ex: int, na: float, ri: float) -> tuple[float, float]:
    """
    Calculate theoretical lateral and axial FWHM for point scanning confocals.

    Using Zipfel, W.R. et al, Nonlinear magic: multiphoton microscopy
    in the biosciences Nat Biotechnol. 2003 Nov;21(11):1369-77
    doi = https://doi.org/10.1038/nbt899
    -> also used/referenced by MetroloJ_QC v1.3.1.1 Oct 21. 2024, but formula
    seems to vary...

    FHMWlat NA<=0.7 = 0.320 * ex / (2^0.5 * NA)
    FHMWlat NA>0.7  = 0.325 * ex / (2^0.5 * NA^0.91)
    FHMWax          = 0.532 * ex / (2^0.5 (n - (n^2 - NA^2)^0.5) )
    *ex wavelength is multiplied by 2 because of 2-photons.

    :param ex: Excitation wavelength in nm (int).
        For calculation using the emission wavelength
        40nm are added to the excitation wavelength.
    :param na: NA of the objective.
    :param ri: Refractive index of objective.

    :return: tuple (FHMW lateral, FHMW axial) in nm.
    """
    if na <= 0.7:
        lat = 0.32 * ex * 2 / (2**0.5 * na)
    else:
        lat = 0.325 * ex * 2 / (2**0.5 * na**0.91)
    ax = 0.532 * ex * 2 / (2**0.5 * (ri - (ri * ri - na * na) ** 0.5))
    return lat, ax


def theo_fwhm_spinning(ex: int, na: float, ri: float) -> tuple[float, float]:
    """
    Calculate theoretical lateral and axial FWHM for point scanning confocals.

    Using the MetroloJ_QC v1.3.1.1 Oct 21. 2024:
    https://github.com/MontpellierRessourcesImagerie/MetroloJ_QC/blob/Current_version/manual.pdf
    Which references:
    Toomre, D. and Pawley J.B. Disk-Scanning Confocal Microscopy.
    in Handbook Of Biological Confocal Microscopy 2006 221-238 (Springer)

    FHMWlat = 0.51 * em / NA
    FHMWax  = em / (ri - (ri^2 - NA^2)^0.5)

    :param ex: Excitation wavelength in nm (int).
        For calculation using the emission wavelength
        40nm are added to the excitation wavelength.
    :param na: NA of the objective.
    :param ri: Refractive index of objective.

    :return: tuple (FHMW lateral, FHMW axial) in nm.
    """
    em = ex + 40
    lat = 0.51 * em / na
    ax = em / (ri - (ri * ri - na * na) ** 0.5)
    return lat, ax


def theo_fwhm_pointscanner(
    ex: int, na: float, ri: float
) -> tuple[float, float]:
    """
    Calculate theoretical lateral and axial FWHM for point scanning confocals.

    Using the MetroloJ_QC v1.3.1.1 Oct 21. 2024:
    https://github.com/MontpellierRessourcesImagerie/MetroloJ_QC/blob/Current_version/manual.pdf
    Which references:
    Wilhelm, S. Confocal Laser Scanning Microscopy. 2011 (Carl Zeiss ed),
    Amos, B. et al, Confocal Microscopy.
    in Handbook of Comprehensive Biophysics 2012 3-23 (Elsevier).

    FHMWlat = 0.51 * ex / NA
    FHMWax  = 0.88 * ex / (ri - (ri^2 - NA^2)^0.5)

    :param ex: Excitation wavelength in nm (int).
        For calculation using the emission wavelength
        40nm are added to the excitation wavelength.
    :param na: NA of the objective.
    :param ri: Refractive index of objective.

    :return: tuple (FHMW lateral, FHMW axial) in nm.
    """
    lat = 0.51 * ex / na
    ax = 0.88 * ex / (ri - (ri * ri - na * na) ** 0.5)
    return lat, ax


def theo_fwhm_widefield(ex: int, na: float, ri: float) -> tuple[float, float]:
    """
    Calculate theoretical lateral and axial FWHM for widefield system.

    Using the MetroloJ_QC v1.3.1.1 Oct 21. 2024:
    https://github.com/MontpellierRessourcesImagerie/MetroloJ_QC/blob/Current_version/manual.pdf
    Which references:
    Wilhelm, S. Confocal Laser Scanning Microscopy 2011 (Carl Zeiss ed.).

    FHMWlat = 0.51 * em / NA
    FHMWax  = 1.77 * ri * em / NA^2

    :param ex: Excitation wavelength in nm (int).
        For calculation using the emission wavelength
        40nm are added to the excitation wavelength.
    :param na: NA of the objective.
    :param ri: Refractive index of objective.

    :return: tuple (FHMW lateral, FHMW axial) in nm.
    """
    em = ex + 40
    lat = 0.51 * em / na
    ax = 1.77 * ri * em / (na * na)
    return lat, ax


def theo_fwhm_quarep(ex: int, na: float, ri: float) -> tuple[float, float]:
    """
    Calculate theoretical lateral and axial FWHM with QUAREP formula.

    Using the formulas found in the QUAREP PSF protocols.io (v1, page 12):
    https://quarep.org/wp-content/uploads/Monitoring-the-point-spread-function-for-quality-for-quality-control-of-confocal-microscopes.pdf
    Which are the formulas from MetroloJ_QC for confocal point scanners.

    FHMWlat = 0.51 * ex / NA
    FHMWax = 0.88 * ex / (ri -(ri^2 - NA^2)^1/2)

    :param ex: Excitation wavelength in nm (int).
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
    Get today's date in format YYYYMMDD.

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
    # Return key & value for first item that has multiple values
    for k, v in groups.items():
        if len(v) > 1:
            return {k: v}
    return None


def invert_nested_dict(nested_dict: dict) -> dict:
    """
    Invert nested dicts to {value: path of keys}.

    :param nested_dict: e.g. {
            "C1" : {'FWHM-X': 911.0, 'FWHM-Y': 852.0, 'FWHM-Z': 1260.0}
        }

    :raises KeyError if the final value happens to occur more than once.

    :return: dict e.g. {
            911.0:  ['C1', 'FWHM-X']
            852.0:  ['C1', 'FWHM-Y']
            1260.0: ['C1', 'FWHM-Z']
        }
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
    """
    Check if a list of strings of cell addresses is continuous.

    True for: [A1, A2, B3, ...]
    False for [A1, A3, B4, ...]

    :param seq: list of cell addresses

    :return: bool
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
    """
    Get a list of duplicate items within a list.

    :param arr: list, of values

    :return: list, of duplicate values (may be empty)
    """
    dup = [i for i, count in Counter(arr).items() if count > 1]
    return dup


if __name__ == "__main__":
    # d = {"DAPI": "C1", "GFP": "None", "Cy3": "C2", "Cy5": "None"}
    # a = check_duplicate_dict_values(d=d, exclude="None")
    # print("found duplicate:", a, type(a))
    pass
