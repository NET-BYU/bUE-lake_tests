#!/bin/bash

# Update the system
sudo apt-get update
sudo apt-get upgrade -y

# Install necessary packages
sudo apt-get install -y gpsd gpsd-clients chrony

# Stop gpsd service if running
sudo systemctl stop gpsd.socket
sudo systemctl disable gpsd.socket

# Create a gpsd configuration file
sudo tee /etc/default/gpsd > /dev/null <<EOT
# Default settings for gpsd
START_DAEMON="true"
GPSD_OPTIONS="-n -b"
DEVICES="/dev/serial/by-id/usb-u-blox_AG_-_www.u-blox.com_u-blox_7_-_GPS_GNSS_R>
USBAUTO="false"
GPSD_SOCKET="/var/run/gpsd.sock"
EOT

# Restart the gpsd service
sudo systemctl enable gpsd.socket
sudo systemctl start gpsd.socket

# Test GPS signal (optional step)
echo "Testing GPS signal..."
gpsmon /dev/ttyACM0  # or use `cgps` to see a simpler GPS readout

# Configure chrony to use GPS for time sync
sudo tee -a /etc/chrony/chrony.conf > /dev/null <<EOT

# GPS time source
refclock SHM 0 offset 0.5 delay 0.2 refid NMEA
EOT

# Restart chrony service
sudo systemctl restart chrony

# Display the status of chrony
echo "Chrony status:"
chronyc sources -v

sudo systemctl disable gpsd.socket
sudo systemctl stop gpsd.socket

sudo systemctl enable gpsd
sudo systemctl start gpsd

sudo usermod -a -G dialout $USER
sudo udevadm trigger

echo "GPS time synchronization setup complete! Please sudo reboot"
