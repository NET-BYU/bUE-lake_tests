"""
ota.py
Bryson Schiel

This is file operates the Reyax over-the-air (ota) service. It handles message transmssion and reception.
Documentation can be found in the NET Lab Notion at the page "bUE Python Code Guide".
"""

import serial
import threading
import time
import queue


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
        self.exit_event = threading.Event()

        # Received messages buffer
        self.recv_msgs = queue.Queue()

        # Reading thread
        self.thread = threading.Thread(target=self.read_from_port, daemon=True)
        self.thread.start()  # keeping the program from exiting

    def read_from_port(self):
        """
        SHOULD NOT BE CALLED DIRECTLY

        Read from serial port; this function is executed in a separate thread.

        Runs continuously until the program is shut down as set by the exit_event flag

        Allows reading from port is receiving_event is set (meaning is True)
        """
        while not self.exit_event.is_set():
            try:
                message = self.ser.readline().decode("utf-8", errors="ignore").strip()

                if message == "" or message == "OK":
                    continue

                self.recv_msgs.put(message)
            except Exception as e:
                print(f"OTA encountered some error: {e}")

    def send_ota_message(self, dest: int, message: str):
        try:
            full_message = f"AT+SEND={dest},{len(message)},{message}\r\n"
            self.ser.write(full_message.encode("utf-8"))
        except Exception as e:
            print(f"Failed to send OTA message: {e}")

    def get_new_messages(self):
        """
        Get all new messages received by the device
        """

        messages = []
        while not self.recv_msgs.empty():
            try:
                message = self.recv_msgs.get_nowait()
                messages.append(message)
            except queue.Empty:
                break

        return messages

    def __del__(self):
        try:
            self.exit_event.set()

            if self.thread.is_alive():
                self.thread.join()
            if self.ser.is_open:
                self.ser.close()
        except Exception as e:
            pass
