# Lake Tests Branch

The next major step for our project is to put everything in a lake and test communication. This repository will store the files needed for this task.

Hint: to run any commands listed in this file, be sure that your terminal is active in the `lake_tests` directory.

## If on the Base Station

Setup a virtual environment and install all the needed packages.

```
python3 -m venv <environment_name>
source /path/to/venv/bin/activate
pip install -r requirements.txt
```

Setup the config file for the base station. Do this by copying `config.example` from the setup folder into the main directory. Rename it `config_base.yaml`. If not uses Linux, you will need to update the `PORT` option of this file to reflect what port the Rayex device is connected to.

### Running Base Station without UI

```
python3 main.py
```

### Running Base Station with UI

Make sure that the keystroke handler thread is commented out in `main_ui.py` and run the following:
``` 
python3 main_ui.py
```

### Running Base Station with UI and auto refresh

Make sure that the keystroke handler thread is uncommented in `main_ui.py` and run the following:
```
sudo -E /path/to/venv/bin/python main_ui.py
```

### Running Base Station GUI

There are two options for this. If on Linux/Mac, run the following:
```
./launch_gui.sh
```

If on Windows, run

```
python base_station_gui.py
```

## If on a bUE

### Install dependencies

The bUE should come with a venv. If it doesn't, create one. Install dependencies into this venv.

```
pip install -r requirements_bue.txt
```

Install `python3-gps`

```
sudo apt-get install python3-gps
```

Run `gpsd.sh` to get all the gps files configured. It is good to reboot after this

```
sudo ./gpsd.sh
```

### Creating the `.service` file

If this device is a Raspberry Pi bUE, then make sure that you have pointed systemd to start the process upon booting the Pi.

```
sudo cp bue.service.txt /etc/systemd/system/bue.service
```

Before activating the service, be sure to edit lines 7 and 8 in your newly created `/etc/systemd/system/bue.service` by changing the value `/path/to/uw_env/...` to whatever path it takes to get to `/uw_env/` and the other paths to your `lake_tests/` folder. There are three isntances of this, so be sure to change them all.

### Creating the `config.yaml` file

Additionally, you need to make sure that there is a `config.yaml` file that the bUE can access. An example with all the fields that you need is found in this repository as `config.example`. You can run the following command:

```
cp config.example config.yaml
```

All the fields should be correct except for `OTA_ID`. Make sure this is set to your Reyex device's address.

### Testing and running the service

Now that you have both the `bue.service` file and `config.yaml` file, let's make sure that they run smoothly. 

To test this, run the following commands:

```
sudo systemctl start bue.service
```

You should see a new log file appear in the `bue_logs` directory. In the first few lines, you should find all the settings from the `config.yaml` file. At this point, if you need to change the yaml file, you will need to run the following command after editing it:

```
sudo systemctl restart bue.service
```

and make sure that the changes are good to go.

### Enabling the bUE service to run on power cycle

The last step for the bUE is to enable it to run when the device power cycles. This is done simply by running the following command:

```
sudo systemctl enable bue.service
```

If you also wish the service to start during this power cycle, just run the `systemctl start` command above.
