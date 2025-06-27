import serial
import pynmea2

# Change this to your GPS dongle's port
port = '/dev/serial/by-id/usb-u-blox_AG_-_www.u-blox.com_u-blox_7_-_GPS_GNSS_Receiver-if00'  # or 'COM3' on Windows
# port = '/dev/ttyACM0'

with serial.Serial(port, baudrate=38400, timeout=1) as ser:
    while True:
        line = ser.readline().decode('ascii', errors='replace')
        if line.startswith('$GPGGA') or line.startswith('$GPRMC'):
            try:
                msg = pynmea2.parse(line)
                print(f"Latitude: {msg.latitude}, Longitude: {msg.longitude}")
            except pynmea2.ParseError:
                continue