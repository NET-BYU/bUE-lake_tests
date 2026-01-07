"""
base_station_main.py
Ty Young

This file will handle all the functionaility required to run a base station.

This file is being coded after bue_main.py and will be structured in a similar manner.

The main goal in this file is to make a station that can handle multiple bUEs as they are currently
defined in bue_main.py
"""

import queue
import sys
from yaml import load, Loader
import time
import threading
from datetime import datetime
import traceback

from loguru import logger

from ota import Ota

logger.remove()  # Remove default sink

# Main log for everything
logger.add("logs/base_station.log", rotation="10 MB")


class Base_Station_Main:
    def __init__(self, yaml_str):
        self.yaml_data = {}

        try:
            with open(yaml_str) as yaml:
                self.yaml_data = load(yaml, Loader=Loader)
                logger.info("__init__: Loading config.yaml. Items are: ")
                for key, value in self.yaml_data.items():
                    logger.info(f" {key}: {value}")
        except FileNotFoundError:
            logger.error(f"__init__: YAML file {yaml_str} no found", file=sys.stderr)
            sys.exit(1)

        self.ota = Ota(self.yaml_data["OTA_PORT"], self.yaml_data["OTA_BAUDRATE"])

        # Fetch the Reyax ID from the OTA module
        time.sleep(0.1)
        self.reyax_id = self.ota.fetch_id()

        logger.info(f"[DEBUG] OTA ID is set to: {self.reyax_id}")

        self.EXIT = False
        self.PING_TIMEOUT_SECONDS = 15  # Number of seconds waiting for a PING to come before its considered missed
        self.PING_MAX_MISSES = 5  # Number of missed PINGs received before connected considered lost

        self.bue_id_to_hostname: dict[int, str] = {}  # Dictionary that pairs rayex ids to bue name. (ex: 20 -> Perry)

        self.connected_bues: list[int] = []  # List to hold rayex ids of each connected bue.
        self.bue_missed_ping_counter: dict[int, int] = {}  # Dictionary to hold how many PINGs have been missed
        self.bue_tout: list[str] = []  # List to hold messages that come with TOUT messages
        self.bue_id_to_state: dict[int, str] = {}  # Dictionary to hold what state each bUE is currently in
        self.bue_id_to_coords: dict[int, (int, int)] = {}  # Dictionary to hold the coords of each bUE
        self.bue_id_to_last_ping_time: dict[int, int] = {}  # Dictionary to hold when a bUE got its last PING

        # Set up the ota threads
        self.ota_incoming_queue = queue.Queue()
        self.ota_outgoing_queue = queue.Queue()
        self.ota_trx_thread = threading.Thread(target=self.ota_message_trx)
        self.ota_trx_thread.start()

        # Set up the ping handler thread
        self.ping_timeout_handler_thread = threading.Thread(target=self.ping_timeout_handler)
        self.ping_timeout_handler_thread.start()

    ## OTA Message Handling Thread and Functions ##
    def ota_message_trx(self):
        """
        A thread to handle message transmission and reception on the OTA device.
        """
        while not self.EXIT:
            # Grab any messages from the OTA and store them in the incoming queue
            try:
                new_messages = self.ota.get_new_messages()

                for message in new_messages:
                    self.ota_incoming_queue.put(message)
            except Exception as e:
                logger.error(f"Failed to get OTA messages: {e}")

            # Push any new messages from the outgoing queue to the OTA
            while not self.ota_outgoing_queue.empty():
                (recipient_id, message) = self.ota_outgoing_queue.get()
                self.ota.send_ota_message(recipient_id, message)
                self.ota_outgoing_queue.task_done()

            if not self.ota_incoming_queue.empty():
                self.ota_message_handler()

            # Sleep for a short duration to avoid busy waiting
            time.sleep(0.1)

    def ota_message_handler(self):
        """
        When messages are received, they are interpretted here.
        """
        while not self.ota_incoming_queue.empty():
            try:
                message: str = self.ota_incoming_queue.get()
                logger.info(f"Received OTA message: {message}")

                # Process the message based on its type
                # A message body is "<source id>,<message type><:message body (optional)>"
                src_id, msg = message.split(",", 1)

                if ":" in msg:
                    msg_type, msg_body = msg.split(":", maxsplit=1)
                else:
                    msg_type, msg_body = msg, None

                if msg_type == "REQ":  # Expected format: REQ:<hostname>,<bUE_id>
                    hostname, bue_id = msg_body.split(",", 1)

                    if int(src_id) != int(bue_id):
                        logger.warning(f"REQ message source ID {src_id} does not match body {bue_id}")
                    else:
                        self.bue_id_to_hostname[int(bue_id)] = str(hostname)
                        self.ota_outgoing_queue.put((bue_id, f"CON:{self.reyax_id}"))
                        logger.info(f"{self.bue_id_to_hostname[int(src_id)]}: REQ")

                elif msg_type == "ACK":
                    # If not already connected, list in connected bUEs and initialize all variables
                    if not int(src_id) in self.connected_bues:
                        self.connected_bues.append(int(src_id))
                        self.bue_missed_ping_counter[int(src_id)] = 0
                        self.bue_id_to_state[int(src_id)] = "IDLE"
                        self.bue_id_to_last_ping_time[int(src_id)] = time.time()
                        logger.info(f"{self.bue_id_to_hostname[int(src_id)]}: Received an ACK")

                elif msg_type == "PING":  # Expected format: PING:<state>,<lat>,<long>
                    # If the bUE is connected,
                    if int(src_id) in self.connected_bues:
                        self.bue_missed_ping_counter[int(src_id)] = 0
                        state, lat, long = msg_body.split(",", 2)
                        self.ota_ping_handler(src_id=src_id, state=state, lat=lat, long=long)
                    else:
                        logger.error(f"{self.bue_id_to_hostname[int(src_id)]}: PING but not listed as connected")

                elif msg_type == "TOUT":
                    self.bue_tout.append(f"{self.bue_id_to_hostname[int(src_id)]}: {msg_body}")
                    logger.info(f"{self.bue_id_to_hostname[int(src_id)]}: TOUT")

                elif msg_type == "FAIL":
                    logger.info(f"{self.bue_id_to_hostname[int(src_id)]}: FAIL")

                elif msg_type == "DONE":
                    logger.info(f"{self.bue_id_to_hostname[int(src_id)]}: DONE")

                else:
                    logger.warning(f"Unknown message type: {msg_type}")

                self.ota_incoming_queue.task_done()
            except Exception as e:
                tb_str = traceback.format_exc()
                logger.error(f"Error processing OTA messages: {e}\nFull traceback:\n{tb_str}")
                self.ota_incoming_queue.task_done()

    def ping_timeout_handler(self):
        """
        Function runs in its own thread. Repeats every second (set by time.sleep below)
        Checks to see if each connected bue has sent a PING in the last self.PING_TIMEOUT_SECONDS
        If not PING received in that amount of time, increments self.bue_missed_ping_counter
        """
        while not self.EXIT:
            try:
                current_time = time.time()

                for bue_id in self.connected_bues.copy():
                    last_ping_time = self.bue_id_to_last_ping_time[int(bue_id)]

                    if current_time - last_ping_time >= self.PING_TIMEOUT_SECONDS:
                        self.bue_missed_ping_counter[bue_id] += 1

                        # Need to update last_ping_time or this will occur every loop
                        self.bue_id_to_last_ping_time[bue_id] = current_time

                        if self.bue_missed_ping_counter[bue_id] >= self.PING_MAX_MISSES:
                            logger.error(
                                f"{self.bue_id_to_hostname[int(bue_id)]}: Has missed {self.bue_missed_ping_counter[bue_id]} PINGs"
                            )
                        else:
                            logger.warning(
                                f"{self.bue_id_to_hostname[int(bue_id)]}: Has missed {self.bue_missed_ping_counter[bue_id]} PINGs"
                            )

            except Exception as e:
                tb_str = traceback.format_exc()
                logger.error(f"ping_timeout_handler: Error {e}\nFull traceback:\n{tb_str}")

            time.sleep(1)

    # OTA Helper Functions
    def ota_ping_handler(self, src_id: str, state: str, lat: str, long: str):
        """
        Takes in the parts from a PING message. If the PING had valid coordinates, those are stored
        and reported. Always note the time the PING was received, the state the bUE reports to be at,
        and response to the bUE with a PINGR
        """
        self.bue_id_to_state[int(src_id)] = state
        self.bue_id_to_last_ping_time[int(src_id)] = time.time()

        coords: str = ""
        if lat != "" and long != "":
            self.bue_id_to_coords[int(src_id)] = (int(lat), int(long))
            coords = f"@ {lat}, {long}"

        self.ota_outgoing_queue.put((src_id, "PINGR"))
        logger.info(f"{self.bue_id_to_hostname[int(src_id)]}: PING {coords}")

    def __del__(self):
        try:
            self.EXIT = True
            if hasattr(self, "ota_trx_thread"):
                self.ota_trx_thread.join()
            if hasattr(self, "ping_timeout_handler_thread"):
                self.ping_timeout_handler_thread.join()
            if hasattr(self, "ota"):
                self.ota.__del__()
            if hasattr(self, "connected_bues"):
                self.connected_bues.clear()
        except Exception as e:
            logger.warning(f"__del__: Exception during cleanup: {e}")


if __name__ == "__main__":

    # Get the current time
    start_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Example usage
    logger.info(f"This marks the start of the base station service at {start_time}")

    try:
        base_station = Base_Station_Main(yaml_str="base_station.yaml")

        # Any other setup code can go here
        time.sleep(2)  # Allow some time for threads to initialize

        while True:
            time.sleep(0.1)

    except KeyboardInterrupt:
        if base_station is not None:
            logger.info("Exiting the base station service")
            base_station.EXIT = True
            time.sleep(0.5)
            base_station.__del__()
            sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception in main: {e}")
        if base_station is not None:
            base_station.EXIT = True
            time.sleep(0.5)
            base_station.__del__()
        sys.exit(1)
