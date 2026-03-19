## bUE Lake Tests

This repository contains the code used for lake communication tests between a shore-side **base station** and multiple remote **bUE** nodes. Communication is handled by Reyax LoRa modules, with optional GPS integration on the bUEs and a Qt-based GUI for monitoring from the base station.

All paths and commands below assume your shell is in the project root directory:

```bash
cd bUE-lake_tests
```

---

## Project Overview

- **Base station (shore)**
	- Talks to one or more bUE nodes over LoRa via a Reyax module.
	- Tracks connection status, missed pings, and per-bUE GPS coordinates.
	- Can be run as a simple CLI (for quick testing) or with a PySide6 GUI.

- **bUE node (field device / Pi)**
	- Connects to the base station using its own Reyax module.
	- Periodically sends `PING` messages, state, and optional GPS coordinates.
	- Receives commands such as `TEST`, `CANC`, `RELOAD`, and `RESTART`.
	- Can be run manually or as a systemd service on a Raspberry Pi.

---

## Repository Layout

- `base_station_main.py` – Base station core logic and OTA handling.
- `bue_main.py` – Main state machine for a single bUE node.
- `ota.py` – Low-level wrapper around the Reyax serial interface.
- `constants.py` – Shared enums/constants (e.g., bUE state codes).
- `config_base.yaml` – Base station config used by `main.py` and the GUI.
- `base_station.yaml` – Alternative base station config used by `base_station_main.py` when run directly.
- `auto_config.yaml` – Parameter sets for automated over-the-air tests.
- `gui/` – PySide6 GUI (entry point: `gui/main.py`, UI files in `gui/ui/`).
- `setup/` – Example configs, systemd unit template, GPS setup script, and requirements files.
- `logs/` – Log files written by the base station and bUE code.
- `tdo_rup.py`, `tup_rdo.py` and `*.grc` – Test / GNU Radio-related utilities.
- `uw_env/` – Example Python virtual environment directory (may not exist or may be local-only; you can create your own instead).

---

## Base Station Setup (PC / Laptop)

### 1. Create and activate a virtual environment

```bash
python3 -m venv uw_env
source uw_env/bin/activate
```

### 2. Install Python dependencies

Install the base station + GUI dependencies:

```bash
pip install -r setup/requirements.txt
```

> Note: `setup/requirements.txt` and `gui/requirements.txt` are aligned; installing from `setup/requirements.txt` is sufficient for both CLI and GUI.

### 3. Configure the base station Reyax module

`config_base.yaml` (used by `main.py` and the GUI) looks like:

```yaml
OTA_PORT: "/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0"
OTA_BAUDRATE: 9600
```

**NOTE:** "/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0" should be the same for all Linux devices. If running on a Windows or Mac you will need to configure for those ports

---

## Running the Base Station

Make sure your virtual environment is active and you are in the project root.

# PySide6 GUI (RECOMMENDED)

Run the GUI from the project root so that logs and paths resolve correctly:

```bash
python -m gui.main
# or equivalently
python gui/main.py
```

The GUI provides:

- A map view of bUE locations (via `MapManager` and `qgmap`).
- Tables for connected bUEs, distances, and coordinates.
- A log viewer for `logs/last_run.log`.
- Dialogs to run and cancel tests on selected bUEs.

---

## bUE Node Setup (e.g., Raspberry Pi)

These steps assume you are on the device that will act as a bUE. Hopefully this was already done when the pi was setup, but if not here is how to do it manually

### 1. Clone or copy the repository

On the bUE device:

```bash
git clone <this-repo-url> bUE-lake_tests
cd bUE-lake_tests
```

### 2. Install GPS-related system packages

On Debian/Raspberry Pi OS:

```bash
sudo setup/gpsd.sh
```

It is usually a good idea to reboot after configuring GPS:

```bash
sudo reboot
```

### 3. Create a virtual environment and install dependencies

The python environment needs to include system gpsd packages that we installed in the first step. By using the `--system-site-packages` flag, we tell the system to include these packages in our environment

```bash
python3 -m venv uw_env --system-site-packages
source uw_env/bin/activate
pip install -r setup/requirements_bue.txt
```


### 4. Configure the bUE Reyax module

`bue_main.py` expects a YAML file (by default `bue_config.yaml`) in the project root. Start from the example in `setup/`:

```bash
cp setup/config.example bue_config.yaml
```

Then edit `bue_config.yaml`. 

- `OTA_PORT` – Serial device for the bUE’s Reyax module.
- `OTA_BAUDRATE` – Usually `9600` unless your module is configured differently.

**NOTE:** "/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0" should be the same for all Linux devices. If running on a Windows or Mac you will need to configure for those ports

### 5. Running the bUE manually

From the project root on the bUE device (with the venv activated):

```bash
python bue_main.py
```

This starts the bUE state machine, which will:

- Initialize the Reyax driver via `ota.Ota`.
- Fetch its Reyax ID.
- Connect to the base station when requested and begin sending `PING` messages and receiving commands.

---

## Running the bUE as a systemd Service (Pi)

On a Raspberry Pi bUE, you can have the bUE code start automatically on boot.

### 1. Install the service unit

From the project root on the bUE device:

```bash
sudo cp setup/bue.service.txt /etc/systemd/system/bue.service
```

### 2. Edit paths in the service file

Open `/etc/systemd/system/bue.service` with your editor of choice and update:

- Any `/path/to/uw_env/...` segments so they point to the actual Python executable in your venv.
- Any `/path/to/bUE-lake_tests/...` segments so they point to this project’s directory on the bUE.

There are multiple instances; make sure you update them all.

### 3. Test the service

```bash
sudo systemctl daemon-reload
sudo systemctl start bue.service
```

You should see logs under `logs/` on the bUE (e.g., `logs/bue.log`). If configuration settings are incorrect, adjust `bue_config.yaml` and restart:

```bash
sudo systemctl restart bue.service
```

### 4. Enable on boot

```bash
sudo systemctl enable bue.service
```

This will cause the bUE process to start automatically on each boot.

---

## Logs and Troubleshooting

- Base station logs:
	- `logs/base_station.log` – Rotating log of base station activity.
	- `logs/last_run.log` – Overwritten each run; displayed in the GUI log viewer.
- bUE logs:
	- `logs/bue.log` – Rotating log of bUE activity (on the bUE device).

If you are not seeing any traffic:

- Confirm both base station and bUE are using matching LoRa parameters (address, baudrate, bandwidth, etc.).
- Check that `OTA_PORT` paths are correct on both sides.
- Ensure that only one process is talking to a given serial device at a time.

---

## Notes

- This README is intentionally focused on getting a base station + one or more bUEs talking over Reyax modules for lake experiments.
- For deeper architectural details (message formats, state diagrams, etc.), refer to comments in `bue_main.py`, `base_station_main.py`, and `ota.py`, and any accompanying lab documentation (e.g., internal Notion pages).
