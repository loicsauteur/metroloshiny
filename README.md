


# Deployment

Using [Shiny Server](https://shiny.posit.co/py/get-started/deploy-on-prem.html#deploy-to-shiny-server-open-source):

In short:

## Open port to access the Shiny Server

The shiny server will be accesible on: http://10.32.14.32:3838

For that the port must/may have to be opened on the linux server, i.e. allow the port with:

`sudo ufw allow 3838`


## Shiny Server installation
Install on a linux (server) execute following commands:

For Ubuntu >18.04:

`sudo apt-get install gdebi-core``

`wget https://download3.rstudio.org/ubuntu-20.04/x86_64/shiny-server-1.5.23.1030-amd64.deb`

`sudo gdebi shiny-server-1.5.23.1030-amd64.deb`

The output of the installation:

```
Shiny Server
 Shiny Server is a server program from RStudio, Inc. that makes Shiny applications available over the web. Shiny is a web application framework for the R statistical computation language.
Do you want to install the software package? [y/N]:y
/usr/bin/gdebi:113: FutureWarning: Possible nested set at position 1
  c = findall("[[(](\S+)/\S+[])]", msg)[0].lower()
Selecting previously unselected package shiny-server.
(Reading database ... 125827 files and directories currently installed.)
Preparing to unpack shiny-server-1.5.23.1030-amd64.deb ...
Unpacking shiny-server (1.5.23.1030) ...
Setting up shiny-server (1.5.23.1030) ...
Creating user shiny
Adding LANG to /etc/systemd/system/shiny-server.service, setting to en_US.UTF-8
Created symlink /etc/systemd/system/multi-user.target.wants/shiny-server.service → /etc/systemd/system/shiny-server.service.
● shiny-server.service - ShinyServer
     Loaded: loaded (/etc/systemd/system/shiny-server.service; enabled; vendor preset: enabled)
     Active: active (running) since Thu 2026-03-19 09:12:46 CET; 8ms ago
   Main PID: 3150 (shiny-server)
      Tasks: 6 (limit: 19047)
     Memory: 1.5M
        CPU: 5ms
     CGroup: /system.slice/shiny-server.service
             └─3150 /opt/shiny-server/ext/node/bin/shiny-server /opt/shiny-server/lib/main.js
```

Info: "If all goes well, you should see a welcome page on http://hostname:3838/." *I could not access this page yet*

## Shiny Server configuration

Edit the file `/etc/shiny-server/shiny-server.conf` (root privileges are required). Add a line with python `<path-to-python-or-venv>`.

In addition it should `run_as` my username (not `shiny`, which did not work, maybe also as `ubuntu` might work...)

What I did:

**Still need to modify the pyhton path, once my shiny app is installed...**

```
# Use specific python to run shiny apps
python /users/stud/s/sautlo01/shiny_test/.pixi/envs/default/bin/python;

# Instruct Shiny Server to run applications as the user "shiny"
#run_as shiny;
run_as sautlo01;

# Define a server that listens on port 3838
server {
  listen 3838;

  # Define a location at the base URL
  location / {

    # Host the directory of Shiny Apps stored in this directory
    site_dir /srv/shiny-server;

    # Log all Shiny output to files in this directory
    log_dir /var/log/shiny-server;

    # When a user visits the base URL rather than a particular application,
    # an index of the applications available in this directory will be shown.
    directory_index on;
  }
}
```

Which uses python from this `shiny_test` pixi env.

## Deploy a shiny app (copy app to server folder)

A Shiny app `app.py` must be located in the shiny-server folder. I.e. Clear out the contents of `/srv/shiny-server/` and replace it with your own app(s).

- If you’re only hosting a single app, you can put the `app.py` (and the rest of the app’s files) directly in `/srv/shiny-server/`, and it will be served from http://hostname:3838/.
- If you have multiple apps, copy each app into a subdirectory; for example, `/srv/shiny-server/foo/app.py` would be served from http://hostname:3838/foo/. In this case, you can put static assets into the root `/srv/shiny-server/` directory, like an `index.html` file.

E.g. to copy a folder (with all it's content, parameter `-R`for recursive; if destination does not exist it will be created) use:

`cp -R path/to/source path/to/destination/`

E.g. (sudo may be required):

`cp -R /users/stud/s/sautlo01/shiny_test/basic-navigation /srv/shiny-server/basic-test/`

Make sure to not forget the `/` at the end of the destination path

**Don't forget to restart the Shiny Server**

## Shiny Server restart

`sudo systemctl restart shiny-server`

`sudo systemctl start shiny-server`

`sudo systemctl stop shiny-server`


# Google stuff

## Enable API and services in google:

1. Create a project or select exisiting one in [Google Developers Console](https://console.developers.google.com/)
2. In `Search for APIs and Servies` search and enable:
   - `Google Drive API`
   - `Google Sheets API`

## Create a API key for a public google sheet
1. In `APIs & Services` > `Credentials` choose `Create credentials` > `API key`
2. Give it a name (e.g. API key metroloshiny)
3. Optional: apply restrictions (I choose no restrictions)

## --> Or create a service account:

1. In `APIs & Services` > `Credentials` choose `Create credentials` > `Service account key`
2. Fill out the form...
3. Under `Credentials` > Service Accounts, press `Manage service accounts`
4. Press on ⋮ near recently created service account and select “Manage keys” and then click on “ADD KEY > Create new key”.
5. Select JSON key type and press “Create” -> downloads a json file. Also remember teh service email address
6. Share the google sheet with the service email address created above
7. Move the downloaded file to `~/.config/gspread/service_account.json`. Windows users should put this file to `%APPDATA%\gspread\service_account.json`.