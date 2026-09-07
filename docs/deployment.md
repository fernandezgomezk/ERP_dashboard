# Deploying the TNO Dashboard on a Server

The following steps install and start the dashboard on a Windows server.

## 1. Clone the Repository

Open PowerShell in the directory where the application should be installed and
clone the repository:

```powershell
git clone <repository-url>
cd ERP_dashboard
```

Replace `<repository-url>` with the Git URL for this repository.

## 2. Install uv

Install [uv](https://docs.astral.sh/uv/) with Winget:

```powershell
winget install --id=astral-sh.uv -e
```

Close and reopen PowerShell after the installation so that `uv` is available
on the `PATH`.

## 3. Install Project Dependencies

From the repository directory, create the virtual environment and install the
locked project dependencies:

```powershell
uv sync
```

## 4. Copy Indicator Data

The indicator data is not included in this repository. Copy all files from the
[indicatoren SharePoint folder](https://365tno.sharepoint.com/:f:/r/teams/P060.55951/TeamDocuments/External%20Audience/WP%20Dashboard/data/indicatoren?d=w7e02c031237649ebb2307ea6adeb8581&csf=1&web=1&e=0vinbh)
to the local `data/indicatoren` folder in the cloned repository.

## 5. Start the Dashboard

Run the included startup script:

```powershell
.\run_streamlit.bat
```

The first time Streamlit runs, it may ask for an email address. This is
optional; press Enter without entering an address to continue.

The script starts Streamlit with `framework_app.py`. By default, Streamlit
listens on port `8501`; open `http://<server-name>:8501` from a browser that can
reach the server. Ensure the server firewall permits inbound traffic to this
port when remote access is required.

## 6. Add a Data Set

See the [data set guide](add-data-set.md) for instructions on adding CSV data
files and their related metadata files.