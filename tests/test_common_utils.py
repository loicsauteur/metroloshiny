from shiny.express import ui
import metroloshiny.utils.common_utils as cu

def create_input_list() -> list:
    input_selector = ui.input_select("input_selector", "Choose", choices=["A", "B"])
    input_text = ui.input_text("input_text", "Enter text", "Example entry...")
    return [input_selector, input_text]

def test_get_ui_id():
    input_list = create_input_list()
    assert cu.get_ui_id(input_list[0]) == "input_selector"
    assert cu.get_ui_id(input_list[1]) == "input_text"

def test_is_input_select_in_list():
    input_list = create_input_list()
    assert cu.is_input_select_in_list(input_list, "input_selector")
    assert cu.is_input_select_in_list(input_list, "input_text")
    assert not cu.is_input_select_in_list(input_list, "something")

if __name__ == "__main__":
    pass
    # test_get_ui_id()
    # test_is_input_select_in_list()
    # print("success")