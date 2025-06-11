"""
ota.py
Bryson Schiel

This is file operates the Reyax over-the-air (ota) service. It handles message transmssion and reception.
Documentation can be found in the NET Lab Notion at the page "bUE Python Code Guide".
"""

import serial
import threading
import time


class Ota:
    def __init__(self, port, baudrate, id):

        # Serial port configuration
        while True:
            try:
                self.ser = serial.Serial(port, baudrate, timeout=0.1)
                break
            except serial.SerialException as e:
                print(f"Failed to open serial port: {e}")
                time.sleep(2)

        self.id = id

        # Flags
        self.receiving_event = threading.Event()
        self.exit_event = threading.Event()

        # Received messages buffer
        self.recv_msgs = []
        self.recv_lock = threading.Lock()

        # Reading thread
        self.receiving_event.set()
        self.thread = threading.Thread(target=self.read_from_port, daemon = True) # dameon true keeps this thread from 
        self.thread.start()                                                       # keeping the program from exiting
        

    def read_from_port(self):
        """
        SHOULD NOT BE CALLED DIRECTLY

        Read from serial port; this function is executed in a separate thread.

        Runs continuously until the program is shut down as set by the exit_event flag

        Allows reading from port is receiving_event is set (meaning is True)
        """
        while not self.exit_event.is_set():
            if self.receiving_event.is_set():
                if self.ser.in_waiting > 0: #Checks to see if there is any data in the serial buffer
                    try: 
                        message = self.ser.readline().decode("utf-8", errors="ignore").strip()
                        if message != "" and message != "OK":
                            with self.recv_lock: # Mutex to prevent data race conditions between threads
                                self.recv_msgs.append(message)
                    except Exception as e:
                        print(f"OTA encountered some error: {e}")
                else:
                    time.sleep(0.05)
            else:
                time.sleep(0.1)


    def send_ota_message(self, dest: int, message: str):
        try:
            full_message = f"AT+SEND={dest},{len(message)},{message}\r\n"
            self.ser.write(full_message.encode("utf-8"))
        except Exception as e:
            print(f"Failed to send OTA message: {e}")

    def get_new_messages(self):
        """
        Get all new messages received by the device

        Temporarily pauses the read_from_port thread, retrieves messages, and then starts read_from_port again
        """

        # Start by disabling the receiver from starting up again
        self.receiving_event.clear()
        time.sleep(0.05)

        # Mutex to prevent data race
        with self.recv_lock:
            messages = self.recv_msgs[:]
            self.recv_msgs.clear()

        self.receiving_event.set()

        return messages

    def __del__(self):
        try:
            self.receiving_event.clear()
            self.exit_event.set()

            if self.thread.is_alive():
                self.thread.join()
            if self.ser.is_open:
                self.ser.close()
        except Exception as e:
            pass

if __name__ == "__main__":

    import argparse
    import logging

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="OTA test")
    parser.add_argument("-p", "--port", type=int, nargs="?", default=0, help="USB port")
    parser.add_argument(
        "-b", "--baudrate", type=int, nargs="?", default=9600, help="Baudrate"
    )
    parser.add_argument("-i", "--id", type=int, nargs="?", default=0, help="Device ID")
    parser.add_argument(
        "-r", "--rate", type=float, nargs="?", default=1, help="Rate in seconds"
    )
    parser.add_argument(
        "-d", "--dest", type=int, nargs="?", default=1, help="Destination"
    )

    args = parser.parse_args()

    try:

        dev = Ota(f"/dev/ttyUSB{args.port}", args.baudrate, args.id)

        while True:
            time.sleep(args.rate)
            dev.send_ota_message(args.dest, "Hello")
            logging.info(f"Received messages: {dev.get_new_messages()}")

    except KeyboardInterrupt:
        dev.__del__()
        print("Exiting...")