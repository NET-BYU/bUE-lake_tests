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
        self.ser = serial.Serial(port, baudrate)
        self.id = id

        # Flags
        self.receiving = True
        self.in_rec_process = False
        self.EXIT = False

        # Received messages
        self.recv_msgs = []

        # Reading thread
        self.thread = threading.Thread(target=self.read_from_port)
        self.thread.start()

    def read_from_port(self):
        """
        SHOULD NOT BE CALLED DIRECTLY

        Read from serial port; this function is executed in a separate thread.

        Flag reads: receiving - to enable/disable reading from serial port; EXIT - to stop the thread

        Flag writes: in_rec_process - to indicate that the thread is processing a message
        """
        while True:
            if self.receiving:
                self.in_rec_process = True
                if self.ser.in_waiting > 0:
                    message = self.ser.readline().decode("utf-8", errors="ignore").strip()
                    if message != "" and message != "OK":
                        self.recv_msgs.append(message)
                self.in_rec_process = False
            if self.EXIT:
                break


    def send_ota_message(self, dest: int, message: str):
        full_message = f"AT+SEND={dest},{len(message)},{message}\r\n"
        self.ser.write(full_message.encode("utf-8"))

    def get_new_messages(self):
        """
        Get all new messages received by the device

        Flag reads: in_rec_process - to wait until the current message is processed

        Flag writes: receiving - to disable the receiver from starting up again
        """

        # Start by disabling the receiver from starting up again
        self.receiving = False

        # Wait until the receiver is done processing the current message (prevent data races)
        while self.in_rec_process:
            pass

        # Copy and erase the messages
        messages = self.recv_msgs
        self.recv_msgs = []

        # Enable the receiver
        self.receiving = True
        return messages

    def __del__(self):
        try:
            self.receiving = False
            self.EXIT = True
            if hasattr(self, "thread"):
                self.thread.join()
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