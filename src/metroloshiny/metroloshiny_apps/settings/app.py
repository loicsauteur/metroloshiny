import os
import time
from pathlib import Path

from shiny import reactive
from shiny.express import input, render, ui

from metroloshiny.utils.common_utils import get_version
from metroloshiny.utils.setting_utils import (
    compare_passwords,
    create_new_data_dict,
    final_check_google,
    final_check_omero,
    final_check_pwd,
    read_data_dict,
    save_private_data,
    try_connect_google,
    try_connect_omero,
)

# Idea new: on file change (reactive file reader) show modal popup to authenticate?


# Get the private data file
data_dir = Path(__file__).parents[4]
data_dir = data_dir / "data"
data_file = data_dir / "private_data.csv"

# Create a file if it does not yet exist
if not os.path.exists(data_file):
    _ = create_new_data_dict()
    # Convert None to "" (not absolutely necessary...)
    for k, v in _.items():
        if v is None:
            _[k] = ""
    save_private_data(_, data_file)

# Reactive variables (final values)       #####################
auth = reactive.value(True)  # Let's initialise this as True
data_dict = reactive.value({})

# ori*pwds: Only not None if pwd set successfully
ori_settings_pwd = reactive.value(None)
ori_upload_pwd = reactive.value(None)

# Following variables are only None if not set/check in UI
new_settings_pwd = reactive.value(None)

gmail = reactive.value(None)
g_json = reactive.value(None)
g_url = reactive.value(None)

omero_host = reactive.value(None)
omero_port = reactive.value(None)
omero_user = reactive.value(None)
omero_pwd = reactive.value(None)

upload_pwd = reactive.value(None)


# Create UI         ----------------------------------------------------------
ui.page_opts(title="Metrology: Settings", footer=f"Version {get_version()}")

with ui.card():
    ui.card_header("Info")

    @render.text
    def load_file():
        """Show information and trigger authentication.

        Sets the reactive values and populates the input fields.
        """
        data_dict.set(load_data_from_file())
        # # Update the field variables
        update_fields_from_dict()

        # Return message
        if ori_settings_pwd.get() is None:
            return "Please set the fields that are necessary!"
        # Otherwise
        return "Saved data reloaded!"


with ui.layout_column_wrap(width=1 / 2):
    with ui.card():
        ui.card_header("Settings password")

        @render.ui
        def show_info_settings_pwd():
            """Show text info for settings password."""
            if ori_settings_pwd.get() is None:
                text = create_red_html_text(
                    "Setting the password to access those settings is<strong> mandatory</strong>."
                )
                return text
            else:
                return "Change the settings password (optional)."

        @render.ui
        def show_ui_settings_pwd():
            """Render the settings password input fields."""
            return (
                input_settings_pwd_1,
                input_settings_pwd_2,
                btn_check_settings_pwd,
            )

    with ui.card():
        ui.card_header("Upload password")

        @render.ui
        def show_info_upload_pwd():
            """Show text info for upload password."""
            if ori_upload_pwd.get() is None:
                text = create_red_html_text(
                    "Setting the upload password is<strong> mandatory</strong>."
                )
                return text
            return ""

        @render.ui
        def show_ui_upload_pwd():
            """Show the upload password input fields."""
            return input_upload_pwd_1, input_upload_pwd_2, btn_check_upload_pwd


with ui.layout_column_wrap(width=1 / 2):
    with ui.card():
        ui.card_header("Google")

        @render.ui
        def show_ui_google():
            """Render the google related input fields."""
            return input_gmail, input_g_json, input_sheet_url, btn_check_google

    with ui.card():
        ui.card_header("OMERO")

        @render.text
        def show_omero_info_text():
            """Show OMERO info text."""
            return "If you don't use OMERO, you can leave this empty."

        @render.ui
        def show_ui_omero():
            """Render the OMERO related input fields."""
            return (
                input_omero_host,
                input_omero_port,
                input_omero_user,
                input_omero_password,
                btn_check_omero,
            )


with ui.card():

    @render.ui
    def show_save_button():
        """Render the saving button."""
        return btn_save_settings


# Reactive functions                    --------------------------------------


@reactive.file_reader(data_file)
def load_data_from_file() -> dict:
    """Load the saved data.

    This is where we trigger the authentication.
    This reactive function is triggered every time the file changes.
    It will cause an exception if the file does not exist.

    Returns
    -------
    dict
        Key value pairs of the red private data
    """
    data = read_data_dict(data_file)
    set_pwd = data.get("Settings password")
    if set_pwd == "":
        # No real settings defined yet -> no authentication needed
        auth.set(True)
        ori_settings_pwd.set(None)
    else:
        # Trigger authentication
        auth.set(False)
        ori_settings_pwd.set(set_pwd)
    # Remember the upload password
    set_pwd = data.get("Upload password")
    if set_pwd == "":
        ori_upload_pwd.set(None)
    else:
        ori_upload_pwd.set(set_pwd)
    # Return the data dictionary
    return data


@reactive.calc
def update_fields_from_dict():
    """Update UI entries using a dictionary.

    Parameters
    ----------
    data : dict
        Data dict, as loaded from the private data file.
    """
    data = data_dict.get()
    set_pwd = data.get("Settings password")
    mail = data.get("GoogleServiceEmail")
    jsn = data.get("PathToServiceAccountJSON")
    url = data.get("Sheet URL")
    host = data.get("OMERO HOST")
    port = data.get("OMERO PORT")
    port = 4064 if port is None else port
    usr = data.get("OMERO USER")
    usr_pwd = data.get("OMERO PASSWORD")
    up_pwd = data.get("Upload password")
    # Set None values to ""
    set_pwd, mail, jsn, url, host, usr, usr_pwd, up_pwd = (
        "" if x is None else x
        for x in (set_pwd, mail, jsn, url, host, usr, usr_pwd, up_pwd)
    )
    # Update UI field inputs
    ui.update_text("input_settings_pwd_1", value=set_pwd)
    ui.update_text("input_settings_pwd_2", value=set_pwd)
    ui.update_text("input_gmail", value=mail)
    ui.update_text("input_g_json", value=jsn)
    ui.update_text("input_sheet_url", value=url)
    ui.update_text("input_omero_host", value=host)
    ui.update_numeric("input_omero_port", value=port)
    ui.update_text("input_omero_user", value=usr)
    ui.update_text("input_omero_password", value=usr_pwd)
    ui.update_text("input_upload_pwd_1", value=up_pwd)
    ui.update_text("input_upload_pwd_2", value=up_pwd)

    # Update check buttons (remove icon)
    ui.update_action_button("btn_check_omero", label="Check", icon=[])
    ui.update_action_button("btn_check_google", label="Check", icon=[])
    ui.update_action_button("btn_check_settings_pwd", label="Check", icon=[])
    ui.update_action_button("btn_check_upload_pwd", label="Check", icon=[])


# Reactive events                       --------------------------------------


# Save data                     #################
@reactive.effect
@reactive.event(input.btn_save_settings)
def check_all_settings_and_save():
    """Check and save the settings.

    Re-runs connection checks.
    Checks if inputs have changed (compared reactive values).
    (Still the user should click through all the check buttons before.)

    Saves/overwrites the private date file. Which triggers re-authentication.
    """
    # Check the settings password   #############
    check, msg = final_check_pwd(
        new_settings_pwd.get(),
        input.input_settings_pwd_1(),
        input.input_settings_pwd_1(),
    )
    if not check:
        ui.notification_show("Settings " + msg, id="final_check", type="error")
        return

    # Check the upload password     #############
    check, msg = final_check_pwd(
        upload_pwd.get(),
        input.input_upload_pwd_1(),
        input.input_upload_pwd_2(),
    )
    if not check:
        ui.notification_show("Upload " + msg, id="final_check", type="error")
        return

    # Check the Google settings     #############
    check, msg = final_check_google(
        gmail.get(),
        g_json.get(),
        g_url.get(),
    )
    if not check:
        ui.notification_show(msg, id="final_check", type="error")
        return

    # Check the OMERO settings     ##############
    check, msg = final_check_omero(
        omero_host.get(),
        omero_port.get(),
        omero_user.get(),
        omero_pwd.get(),
    )
    if not check:
        ui.notification_show(msg, id="final_check", type="error")
        return

    # Save the information to file
    d_dict = create_new_data_dict()
    d_dict["GoogleServiceEmail"] = gmail.get()
    d_dict["PathToServiceAccountJSON"] = g_json.get()
    d_dict["Sheet URL"] = g_url.get()
    d_dict["OMERO HOST"] = omero_host.get()
    d_dict["OMERO PORT"] = str(omero_port.get())
    d_dict["OMERO USER"] = omero_user.get()
    d_dict["OMERO PASSWORD"] = omero_pwd.get()
    d_dict["Upload password"] = upload_pwd.get()
    d_dict["Settings password"] = new_settings_pwd.get()

    # Write the csv file
    ui.notification_show(
        f"Saving data to: {data_file}", id="final_check_warn", type="message"
    )
    # Show UI notification for 2 seconds, then trigger re-authentication with saving to file
    time.sleep(2)
    save_private_data(d_dict, str(data_file))


# Settings password check       #################
@reactive.effect
@reactive.event(input.btn_check_settings_pwd)
def check_settings_password():
    """Check the settings passwords.

    Comares/checks also with loaded password.
    If all is good, the new_settings_pwd variable is set.
    """
    loaded_pwd = ori_settings_pwd.get()
    new_pwd = new_settings_pwd.get()
    pwd_1 = input.input_settings_pwd_1()
    pwd_2 = input.input_settings_pwd_2()

    # Remove previous notification (when button clicked)
    ui.notification_remove("settings_new_pwd")

    same, msg = compare_passwords(pwd_1, pwd_2)
    # Force setting a password if there is not password yet
    if loaded_pwd is None:
        # No current new password
        if new_pwd is None:
            if not same:
                if "empty" in msg:
                    ui.notification_show(
                        "You must provide a new Settings Password",
                        id="settings_new_pwd",
                        type="error",
                    )
                else:
                    ui.notification_show(
                        "Settings " + msg, id="settings_new_pwd", type="error"
                    )
                return
        elif new_pwd == pwd_1 == pwd_2:
            # Already good: mark the check button as good
            ui.update_action_button(
                "btn_check_settings_pwd", label="Check", icon=["✅"]
            )
            return
        else:
            ui.notification_show(
                "Settings " + msg, id="settings_new_pwd", type="error"
            )
            new_settings_pwd.set(None)
            return

    # There is a loaded settings password
    if same or pwd_1 == pwd_2 == "":
        if pwd_1 == loaded_pwd or pwd_1 == pwd_2 == "":
            ui.notification_show(
                "Keeping the current settings password.",
                id="settings_new_pwd",
            )
            new_settings_pwd.set(loaded_pwd)
        else:
            new_settings_pwd.set(pwd_1)
        # Mark the check button as good
        ui.update_action_button(
            "btn_check_settings_pwd", label="Check", icon=["✅"]
        )
        return
    # The entered passwords do not macht
    ui.notification_show(
        "Settings " + msg, id="settings_new_pwd", type="error"
    )
    new_settings_pwd.set(None)


@reactive.effect
@reactive.event(input.input_settings_pwd_1, input.input_settings_pwd_2)
def update_check_settings_pwd_btn():
    """Remove OK icon from check upload password button.

    Resets reactive variables.
    """
    ui.update_action_button("btn_check_settings_pwd", label="Check", icon=[])
    # Reset the new password variable
    new_settings_pwd.set(None)


# Upload password check         #################
@reactive.effect
@reactive.event(input.btn_check_upload_pwd)
def check_upload_pwd():
    """Check if the upload password is OK.

    Compares also the loaded upload password.
    If all is good the new_upload_pwd variable is set.
    """
    pwd_1 = input.input_upload_pwd_1()
    pwd_2 = input.input_upload_pwd_2()
    saved_pwd = ori_upload_pwd.get()
    # Allow skipping the setting of the pwd
    if (
        saved_pwd is not None and (pwd_1 == pwd_2 == "")
    ) or saved_pwd == pwd_1 == pwd_2:
        # Remember the saved password
        upload_pwd.set(saved_pwd)
        ui.notification_show(
            "Keeping the current upload password.", id="upload_pwd_error"
        )
        # Mark the check button as good
        ui.update_action_button(
            "btn_check_upload_pwd", label="Check", icon=["✅"]
        )
        return
    same, msg = compare_passwords(pwd_1, pwd_2)
    if not same:
        ui.notification_show(msg, id="upload_pwd_error", type="error")
        return
    # Remember the upload password
    upload_pwd.set(pwd_1)

    # Mark the check button as good
    ui.update_action_button("btn_check_upload_pwd", label="Check", icon=["✅"])


@reactive.effect
@reactive.event(input.input_upload_pwd_1, input.input_upload_pwd_2)
def update_check_upload_pwd_btn():
    """Remove OK icon from check upload password button.

    Resets reactive variables.
    """
    ui.update_action_button("btn_check_upload_pwd", label="Check", icon=[])
    upload_pwd.set(None)


# Google settings check         #################
@reactive.effect
@reactive.event(input.btn_check_google)
def check_google_connection():
    """Check if it can connect to the google sheet."""
    _mail = input.input_gmail()
    _path = input.input_g_json()
    _url = input.input_sheet_url()
    if _path == "":
        ui.notification_show(
            "JSON file path missing. May work if the file is located in the default location: `~/.config/gspread/service_account.json`",
            type="warning",
            id="warn_json",
        )
    if _url == "":
        ui.notification_show(
            "Please provide a google sheet URL", type="error", id="warn_url"
        )
        return
    else:
        ui.notification_remove("warn_url")

    success, msg = try_connect_google(path=_path, url=_url)

    if not success:
        ui.notification_show(
            f"Google connection failed with error: {msg}",
            id="g_fail",
            type="error",
        )
        return

    ui.notification_show("Connection successful", type="message", id="o_fail")
    # Remember the stuff
    gmail.set(_mail)
    g_json.set(_path)
    g_url.set(_url)

    # Mark the check button as good
    ui.update_action_button("btn_check_google", label="Check", icon=["✅"])


@reactive.effect
@reactive.event(input.input_gmail, input.input_g_json, input.input_sheet_url)
def update_check_google_btn():
    """Remove OK icon from check google button.

    Resets reactive variables.
    """
    ui.update_action_button("btn_check_google", label="Check", icon=[])
    gmail.set(None)
    g_json.set(None)
    g_url.set(None)


# OMERO settings check          #################


@reactive.effect
@reactive.event(input.btn_check_omero)
def check_omero_connection():
    """Check if it can connect to OMERO."""
    _host = input.input_omero_host()
    _port = input.input_omero_port()
    _user = input.input_omero_user()
    _pwd = input.input_omero_password()

    # Allow OMERO settings to be unset
    if _host == _user == _pwd == "":
        omero_host.set(_host)
        omero_user.set(_user)
        omero_pwd.set(_pwd)
        omero_port.set(4064)
        ui.update_numeric("input_omero_port", value=4064)
        # Mark the check button as good
        ui.update_action_button("btn_check_omero", label="Check", icon=["✅"])
        return

    # Check inputs are provided
    if "" in [_host, _user, _pwd]:
        if _host == "":
            ui.notification_show(
                "Please provide an OMERO HOST", id="o_host", type="error"
            )
        else:
            ui.notification_remove("o_host")
        if _user == "":
            ui.notification_show(
                "Please provide an OMERO user name", id="o_usr", type="error"
            )
        else:
            ui.notification_remove("o_usr")
        if _pwd == "":
            ui.notification_show(
                "Please provide an OMERO password", id="o_pwd", type="error"
            )
        else:
            ui.notification_remove("o_pwd")
        return
    # Try connect to OMERO
    success, msg = try_connect_omero(
        host=_host, port=_port, usr=_user, pwd=_pwd
    )
    if not success:
        ui.notification_show(
            f"Connection failed with error: {msg}", type="error", id="o_fail"
        )
        return

    ui.notification_show("Connection successful", type="message", id="o_fail")
    # Remember the stuff
    omero_host.set(_host)
    omero_port.set(_port)
    omero_user.set(_user)
    omero_pwd.set(_pwd)

    # Mark the check button as good
    ui.update_action_button("btn_check_omero", label="Check", icon=["✅"])


@reactive.effect
@reactive.event(
    input.input_omero_host, input.input_omero_user, input.input_omero_password
)
def update_check_omero_btn():
    """Remove OK icon from check OMERO button.

    Resets reactive variables.
    """
    ui.update_action_button("btn_check_omero", label="Check", icon=[])
    omero_host.set(None)
    omero_user.set(None)
    omero_pwd.set(None)
    # Set the OMERO port to the default value
    omero_port.set(4064)
    ui.update_numeric("input_omero_port", value=4064)


# Settings authentication       #################
@reactive.effect
def ask_for_authentication():
    """Trigger showing the authentication pop-up."""
    if not auth.get():
        authenticate()


@reactive.effect
@reactive.event(input.submit_auth_pwd_button)
def check_auth_pwd():
    """Check the authentication password."""
    input_pwd = input.auth_pwd()
    if input_pwd == ori_settings_pwd.get():
        ui.modal_remove()
        auth.set(True)
    else:
        ui.modal_remove()
        authenticate(failed=True)


# Functions                             --------------------------------------


def authenticate(failed: bool = False):
    """Create a pop-up to ask for a password.

    Parameters
    ----------
    failed : bool
        Shows "Wrong password" warning if True. Default False
    """
    m = ui.modal(
        "Please provide the settings password to make changes.",
        ui.input_password("auth_pwd", "Authentication Password", value=""),
        ui.p("Wrong password", style="color:red") if failed else None,
        title="Authenticate",
        easy_close=False,
        footer=ui.input_action_button("submit_auth_pwd_button", "OK"),
    )
    ui.modal_show(m)


def create_red_html_text(text: str):
    """Create a ui.HTML object in red color.

    Parameters
    ----------
    text : str
        Text with optional HTML tags. E.g.:
        "Setting the password to access those settings is<strong> mandatory</strong>."

    Returns
    -------
    ui.HTML
        UI element.
    """
    txt_out = '<p><span style="color: #ff0000;">' + text + "</span></p>"
    return ui.HTML(txt_out)


# UI elements                   ----------------------------------------------

# Settings password entries
input_settings_pwd_1 = ui.input_password(
    "input_settings_pwd_1", "Please provide a new password"
)
input_settings_pwd_2 = ui.input_password(
    "input_settings_pwd_2", "Please repeat the new password"
)
btn_check_settings_pwd = ui.input_action_button(
    "btn_check_settings_pwd", "Check"
)

# Google sheet entries
input_gmail = ui.input_text("input_gmail", "Google Service Email (optional)")
input_g_json = ui.input_text(
    "input_g_json", "Path to Service Account JSON file"
)
input_sheet_url = ui.input_text("input_sheet_url", "Google spreadsheet URL")
btn_check_google = ui.input_action_button("btn_check_google", "Check")

# OMERO entries
input_omero_host = ui.input_text("input_omero_host", "OMERO HOST")
input_omero_port = ui.input_numeric(
    "input_omero_port", "OMERO PORT", value=1, min=1, step=1
)
input_omero_user = ui.input_text("input_omero_user", "OMERO User")
input_omero_password = ui.input_password(
    "input_omero_password", "OMERO Password"
)
btn_check_omero = ui.input_action_button("btn_check_omero", "Check")

# Upload password entries
input_upload_pwd_1 = ui.input_password(
    "input_upload_pwd_1", "Please provide a password for uploading"
)
input_upload_pwd_2 = ui.input_password(
    "input_upload_pwd_2", "Please repeat the upload password"
)
btn_check_upload_pwd = ui.input_action_button("btn_check_upload_pwd", "Check")

# Saving button
btn_save_settings = ui.input_action_button(
    "btn_save_settings", "Save settings"
)
