"""Utils for common usage."""

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


def theoretical_fwhm(em: int, na: float, ri: float, k: float = 2.0):
    """
    Calculate theoretical lateral and axial FWHM.

    FHMWlat = 0.51 * lambda / NA
    FHMWax = 2 * n * lambda / NA^2

    :param em: Emission wavelength in nm (int).
    :param na: NA of the objective.
    :param ri: Refractive index of objective.
    :param k: Constant for axial FHMW. Default = 2.0 (widefield),
              set to 1.4 for confocal.

    :return: tuple (FHMW lateral, FHMW axial) in nm.
    """
    lat = 0.51 * em / na
    ax = k * ri * em / (na * na)
    return lat, ax
