import os
from pathlib import Path

from shiny import reactive
from shiny.express import input, render, ui

from metroloshiny.utils.common_utils import get_version
from metroloshiny.utils.setting_utils import (
    compare_passwords,
    create_new_data_dict,
    final_check_google,
    final_check_omero,
    final_check_settings_pwd,
    final_check_upload_pwd,
    read_data_dict,
    save_private_data,
    try_connect_google,
    try_connect_omero,
)

# to modify the metrology_data (private data)
# have a own password for those settings, settable if the file does not exist
# loads existing, but then requires the "own password" for changes
# have test buttons to check if the connections (OMERO, maybe also google sheet)
# after saving setting have the page reloaded!


# Reactive variables (final values)       #####################
data = reactive.value()
settings_pwd = reactive.value(None)

gmail = reactive.value(None)
g_json = reactive.value(None)
sheet_url = reactive.value(None)

omero_host = reactive.value(None)
omero_port = reactive.value(None)
omero_user = reactive.value(None)
omero_pwd = reactive.value(None)

upload_pwd = reactive.value(None)
upload_pwd_from_file = reactive.value(None)

# Get the private data file
data_dir = Path(__file__).parents[4]
data_dir = data_dir / "data"
# file = data_dir / "private_data.csv"
data_file = data_dir / "p_data_test.csv"


# Create UI         ----------------------------------------------------------
ui.page_opts(title="Metrology: Settings", footer=f"Version {get_version()}")

with ui.layout_column_wrap(width=1 / 2):
    with ui.card():
        ui.card_header("Info")

        @render.text
        def load_data():
            """Display information and load data."""
            # Try loading the existing data
            if os.path.exists(data_file):
                data.set(read_data_dict(data_file))
                info = "Data was loaded from file - but I have to finish this function"
                # TODO only init data dict and update fields if pwd correct (-> button)

                # TODO continue here

            else:
                data.set(create_new_data_dict())
                info = "No data available yet"
                # Initialise the reactive values
                init_reactive_vals()
                # Update UI
                update_input_fields()
            return info

    with ui.card():
        ui.card_header("Settings password")
        ui.input_password("old_pwd", "Please provide the current password")
        ui.input_password("new_pwd_1", "Please provide a new password")
        ui.input_password("new_pwd_2", "Please repeat the new password")
        ui.input_action_button("input_check_settings_pwd", "Check")

with ui.card():
    ui.card_header("Apply changes")
    ui.input_action_button("input_save_all", "Save settings")

with ui.layout_column_wrap(width=1 / 2):
    with ui.card():
        ui.card_header("Google")
        ui.input_text("google_mail", "Google Service Email (optional)")
        ui.input_text("account_file", "Path to Service Account JSON file")
        ui.input_text("sheet_url", "Google spreadsheet URL")
        ui.input_action_button("check_google", "Check")

    with ui.card():
        ui.card_header("OMERO")
        ui.input_text("host", "OMERO HOST")
        ui.input_numeric("port", "OMERO PORT", value=1, min=1, step=1)
        ui.input_text("user", "OMERO User")
        ui.input_password("omero_password", "OMERO Password")
        ui.input_action_button("check_omero", "Check")


with ui.card():
    ui.card_header("Upload password")
    ui.input_password(
        "upload_pwd_1", "Please provide a password for uploading"
    )
    ui.input_password("upload_pwd_2", "Please repeat the upload password")
    ui.input_action_button("check_upload", "Check")


# Reactive events                       --------------------------------------


@reactive.effect
@reactive.event(input.input_save_all)
def check_all_settings_and_save():
    """
    Check and save the settings.

    Re-runs connection checks.
    Checks if inputs have changed (compared reactive values).
    (Still the user should click through all the check buttons before.)

    Saves/overwrites the private date file.
    """
    # Check the settings password   #############
    check, msg = final_check_settings_pwd(
        data_file,
        settings_pwd.get(),
        input.old_pwd(),
        input.new_pwd_1(),
        input.new_pwd_2(),
    )
    if not check:
        # FIXME could have this only once
        ui.notification_show(msg, id="final_check_warn", type="error")
        return

    # Check the Google settings     #############
    check, msg = final_check_google(
        gmail.get(),
        input.google_mail(),
        g_json.get(),
        input.account_file(),
        sheet_url.get(),
        input.sheet_url(),
    )
    if not check:
        ui.notification_show(msg, id="final_check_warn", type="error")
        return

    # Check the OMERO settings     ##############
    check, msg = final_check_omero(
        omero_host.get(),
        input.host(),
        omero_port.get(),
        input.port(),
        omero_user.get(),
        input.user(),
        omero_pwd.get(),
        input.omero_password(),
    )
    if not check:
        ui.notification_show(msg, id="final_check_warn", type="error")
        return

    # Check the upload password     #############
    check, msg = final_check_upload_pwd(
        upload_pwd_from_file.get(),
        upload_pwd.get(),
        input.upload_pwd_1(),
        input.upload_pwd_2(),
    )
    if not check:
        ui.notification_show(msg, id="final_check_warn", type="error")
        return

    # Save information to file
    d_dict = create_new_data_dict()
    d_dict["GoogleServiceEmail"] = "" if gmail.get() is None else gmail.get()
    d_dict["PathToServiceAccountJSON"] = (
        "" if g_json.get() is None else g_json.get()
    )
    d_dict["Sheet URL"] = sheet_url.get()
    d_dict["Upload password"] = upload_pwd.get()
    d_dict["OMERO HOST"] = "" if omero_host.get() is None else omero_host.get()
    d_dict["OMERO PORT"] = str(omero_port.get())
    d_dict["OMERO USER"] = "" if omero_user.get() is None else omero_user.get()
    d_dict["OMERO PASSWORD"] = (
        "" if omero_pwd.get() is None else omero_pwd.get()
    )
    d_dict["Settings password"] = settings_pwd.get()

    # Write the csv file
    save_private_data(d_dict, str(data_file))
    print("Saved file to:", data_file)
    ui.notification_show(
        f"Saved data to: {data_file}", id="final_check_warn", type="message"
    )
    # TODO reload the app somehow!


# Settings password check       ################
@reactive.effect
@reactive.event(input.input_check_settings_pwd)
def check_settings_password():
    """
    Check the settings passwords.

    TODO describe better
    """
    cur_pwd = input.old_pwd()
    new_pwd_1 = input.new_pwd_1()
    new_pwd_2 = input.new_pwd_2()

    # Ignore current pwd if there is no existing data file
    # But force setting one
    if not os.path.exists(data_file):
        same, msg = compare_passwords(new_pwd_1, new_pwd_2)
        if not same:
            if "empty" in msg:
                ui.notification_show(
                    "You must provide a new Password",
                    id="settings_new_pwd",
                    type="error",
                )
            else:
                ui.notification_show(msg, id="settings_new_pwd", type="error")
            return
        # Save the new password
        settings_pwd.set(new_pwd_1)
        # Mark the check button as good
        ui.update_action_button(
            "input_check_settings_pwd", label="Check", icon=["✅"]
        )
        return

    # If data file exists and correct current pwd -> load all fields from data
    d_dict = read_data_dict(data_file)
    cur_pwd = cur_pwd + d_dict.get("aKey")  # temp precommit fix
    # TODO check if pwd is correct
    # TODO warn / reset new password entries and warn
    # Populte all fields


@reactive.effect
@reactive.event(input.new_pwd_1, input.new_pwd_2)
def update_check_settings_pwd_btn():
    """
    Remove OK icon from check upload password button.

    Resets reactive variables FIXME ?? should it?
    """
    ui.update_action_button("input_check_settings_pwd", label="Check", icon=[])
    # FIXME check if current pwd is correct and set it instead of None ??
    settings_pwd.set(None)


# Upload password check       ##################
@reactive.effect
@reactive.event(input.check_upload)
def check_upload_pwd():
    """Check if the upload password is OK."""
    pwd_1 = input.upload_pwd_1()
    pwd_2 = input.upload_pwd_2()
    saved_pwd = upload_pwd_from_file.get()
    # Allow skipping the setting of the pwd
    if saved_pwd is not None and (pwd_1 == pwd_2 == ""):
        # Remember the saved password
        upload_pwd.set(saved_pwd)
        ui.notification_show(
            "Keeping the current upload password.", id="upload_pwd_error"
        )
        return
    same, msg = compare_passwords(pwd_1, pwd_2)
    if not same:
        ui.notification_show(msg, id="upload_pwd_error", type="error")
        return
    # Remember the upload password
    upload_pwd.set(pwd_1)

    # Mark the check button as good
    ui.update_action_button("check_upload", label="Check", icon=["✅"])


@reactive.effect
@reactive.event(input.upload_pwd_1, input.upload_pwd_2)
def update_check_upload_pwd_btn():
    """
    Remove OK icon from check upload password button.

    Resets reactive variables FIXME ?? should it?
    """
    ui.update_action_button("check_upload", label="Check", icon=[])
    upload_pwd.set(None)


# Google settings check       ###################
@reactive.effect
@reactive.event(input.check_google)
def check_google_connection():
    """Check if it can connect to the google sheet."""
    _mail = input.google_mail()
    _path = input.account_file()
    _url = input.sheet_url()
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
    sheet_url.set(_url)

    # Mark the check button as good
    ui.update_action_button("check_google", label="Check", icon=["✅"])


@reactive.effect
@reactive.event(input.google_mail, input.account_file, input.sheet_url)
def update_check_google_btn():
    """
    Remove OK icon from check google button.

    Resets reactive variables FIXME ?? should it?
    """
    ui.update_action_button("check_google", label="Check", icon=[])
    gmail.set(None)
    g_json.set(None)
    sheet_url.set(None)


# OMERO settings check       ####################
@reactive.effect
@reactive.event(input.check_omero)
def check_omero_connection():
    """Check if it can connect to OMERO."""
    _host = input.host()
    _port = input.port()
    _user = input.user()
    _pwd = input.omero_password()

    # Allow OMERO settings to be unset
    if _host == _user == _pwd == "":
        omero_host.set(None)
        omero_port.set(4064)
        omero_user.set(None)
        omero_pwd.set(None)
        # Mark the check button as good
        ui.update_action_button("check_omero", label="Check", icon=["✅"])
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
    ui.update_action_button("check_omero", label="Check", icon=["✅"])


@reactive.effect
@reactive.event(input.host, input.port, input.user, input.omero_password)
def update_check_omero_btn():
    """
    Remove OK icon from check OMERO button.

    Resets reactive variables FIXME ?? should it?
    """
    ui.update_action_button("check_omero", label="Check", icon=[])
    omero_host.set(None)
    omero_user.set(None)
    omero_pwd.set(None)
    # Set the OMERO port to the default value
    omero_port.set(4064)
    ui.update_numeric("port", value=4064)


# Reactive functions                    --------------------------------------


@reactive.calc
def init_reactive_vals():
    """Set the reactive variables according to data (dict)."""
    d_dict = data.get()
    settings_pwd.set(d_dict.get("Settings password"))
    gmail.set(d_dict.get("GoogleServiceEmail"))
    g_json.set(d_dict.get("PathToServiceAccountJSON"))
    sheet_url.set(d_dict.get("Sheet URL"))
    omero_host.set(d_dict.get("OMERO HOST"))
    omero_port.set(d_dict.get("OMERO PORT"))
    omero_user.set(d_dict.get("OMERO USER"))
    omero_pwd.set(d_dict.get("OMERO PASSWORD"))
    upload_pwd.set(d_dict.get("Upload password"))


@reactive.calc
def update_input_fields():
    """Set input field based on red data."""
    d_dict = data.get()
    s_pwd = d_dict.get("Settings password")
    if s_pwd is not None:
        pass  # Dont do anything here FIXME?
    g_m = d_dict.get("GoogleServiceEmail")
    if g_m is not None:
        ui.update_text("google_mail", value=g_m)
    g_j = d_dict.get("PathToServiceAccountJSON")
    if g_j is not None:
        ui.update_text("account_file", value=g_j)
    s_u = d_dict.get("Sheet URL")
    if s_u is not None:
        ui.update_text("sheet_url", value=s_u)
    o_h = d_dict.get("OMERO HOST")
    if o_h is not None:
        ui.update_text("host", value=o_h)
    o_p = d_dict.get("OMERO PORT")
    if o_p is not None:
        ui.update_numeric("port", value=o_p)
    o_u = d_dict.get("OMERO USER")
    if o_u is not None:
        ui.update_text("user", value=o_u)
    o_pwd = d_dict.get("OMERO PASSWORD")
    if o_pwd is not None:
        ui.update_text("omero_password", value=o_pwd)
    u_p = d_dict.get("Upload password")
    if u_p is not None:
        pass  # Dont do anything here FIXME?


# Functions                             --------------------------------------


# UI elements
