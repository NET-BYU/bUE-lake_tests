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
import crc8


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

        # Initialize CRC8 calculator
        self.crc8_calculator = crc8.crc8()

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

        Expected message format: +RCV=<sndr address>,<payload length>,<MESSAGE TYPE><:BODY (optional)>,<RSSI>,<SNR>
        """
        while not self.exit_event.is_set():
            try:
                message_with_crc = self.ser.readline().decode("utf-8", errors="ignore").strip()
                parts = message_with_crc.split(",")

                if message_with_crc == "" or message_with_crc == "OK":
                    continue

                # print(f"Message with CRC: {message_with_crc}")

                if len(parts) < 5:
                    continue
                    # TODO: Maybe log if we are not putting a message into the recv_msgs?

                # Extract components: +RCV=origin,length,message_with_crc,rssi,snr
                origin = parts[0][5:]
                message_with_crc_part = ",".join(parts[2:-2])
                # print(parts)
                # print(f"Message with CRC Part: {message_with_crc_part}")

                valid_crc, original_message = self.verify_crc(message_with_crc_part)

                if not valid_crc:  # Bad checksum
                    continue

                # print("!!!!!!!!!!!")

                self.recv_msgs.put(f"{origin},{original_message}")
            except Exception as e:
                print(f"OTA encountered some error: {e}")

    def calculate_crc(self, message):
        """Calculate CRC8 checksum for a message."""
        calculator = crc8.crc8()
        calculator.update(message.encode("utf-8"))
        return format(calculator.digest()[0], "02x")

    def verify_crc(self, message_with_crc):
        """
        Verify CRC8 checksum of a received message.

        Args:
            message_with_crc: The message content with CRC appended

        Returns:
            tuple: (is_valid, original_message)
        """
        if len(message_with_crc) < 2:
            # Message too short to have CRC
            return False, message_with_crc

        # Extract the last 2 characters as CRC
        original_message = message_with_crc[:-2]
        received_crc = message_with_crc[-2:]

        # Reconstruct the full message format that was used for CRC calculation
        # This should match the format used in send_ota_message: "{len(message)},{message}"
        full_message_for_crc = f"{original_message}"
        calculated_crc = self.calculate_crc(full_message_for_crc)

        is_valid = received_crc.lower() == calculated_crc.lower()
        return is_valid, original_message

    def send_ota_message(self, dest: int, message: str, include_crc: bool = True):
        """
        Send OTA message with optional CRC checksum.

        Args:
            dest (int): Destination address
            message (str): Message to send
            include_crc (bool): Whether to include CRC checksum (default: True)
        """
        try:

            # if include_crc:
            #     crc = self.calculate_crc(message)
            #     message_with_crc = f"{message}{crc}"
            # else:
            #     message_with_crc = message

            crc = self.calculate_crc(message)
            message_with_crc = f"{message}{crc}"

            full_message = f"AT+SEND={dest},{len(message_with_crc)},{message_with_crc}\r\n"
            # print(full_message)
            self.ser.write(full_message.encode("utf-8"))
        except Exception as e:
            print(f"Failed to send OTA message: {e}")

    def get_new_messages(self):
        """
        Get all new messages received by the device (raw, without CRC validation)
        """
        messages = []
        try:
            while True:
                messages.append(self.recv_msgs.get_nowait())
        except queue.Empty:
            pass
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
