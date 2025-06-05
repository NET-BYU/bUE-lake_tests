# Lake Tests Branch

Then next major step for our project is to put everything in a lake and test communication. This folder/branch will store the files needed for this task.

Hint: to run any commands listed in this file, be sure that your terminal is active in the `lake_tests` directory.

## If on the Base Station

Simply run the following command:

``` 
python3 base_station_main.py 
```

## If on a bUE

### Creating the `.service` file

If this device is a Raspberry Pi bUE, then make sure that you have pointed systemd to start the process upon booting the Pi.

```
sudo cp bue.service.txt /etc/systemd/system/bue.service
```

Before activating the service, be sure to edit lines 7 and 8 in your newly created `/etc/systemd/system/bue.service` by changing the value `/path/to/uw_env/...` to whatever path it takes to get to `/uw_env/`. There are three isntances of this, so be sure to change them all.

### Creating the `config.yaml` file

Additionally, you need to make sure that there is a `config.yaml` file that the bUE can access. An example with all the fields that you need is found in this repository as `config.example`. You can run the following command:

```
cp config.example config.yaml
```

You can then update the fields as needed for the bUE before running it.

### Testing and running the service

Now that you have both the `bue.service` file and `config.yaml` file, let's make sure that they run smoothly. 

To test this, run the follwoing commands:

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