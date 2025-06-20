import serial
from pynmeagps import NMEAReader

# Change this to your GPS dongle's port
port = '/dev/serial/by-id/usb-u-blox_AG_-_www.u-blox.com_u-blox_7_-_GPS_GNSS_Receiver-if00'  # or 'COM3' on Windows
# port = '/dev/ttyACM0'

with serial.Serial(port, baudrate=38400, timeout=1) as stream:
    while True:
        line = stream.readline().decode('ascii', errors='replace')
        if line.startswith('$GPGGA') or line.startswith('$GPRMC'):
            try:
                msg = NMEAReader.parse(line)
                print(f"Currently positioned at Latitude: {msg.lat}, Longitude: {msg.lon} ")
            except serial.SerialException as e:
                print(f"Serial error: {e}")
            except Exception as e:
                print(f"An error occured when gathering GPS data: {e}")