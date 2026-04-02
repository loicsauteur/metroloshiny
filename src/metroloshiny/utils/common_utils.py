from bs4 import BeautifulSoup

def get_ui_id(input) -> str:
    """
    Return the ID string from an ui.input* object.

    :param input: ui.input* object

    :return: str id of ui.input* object
    """
    soup = BeautifulSoup(str(input), "html.parser")
    return soup.find("label")["for"]

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
