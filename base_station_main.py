"""
base_station_main.py
Ty Young

This file will handle all the functionaility required to run a base station.

This file is being coded after bue_main.py and will be structured in a similar manner.

The main goal in this file is to make a station that can handle multiple bUEs as they are currently
defined in bue_main.py
"""

# Standard library imports
import queue
import os
import sys
import threading
import time
from loguru import logger
from yaml import load, Loader

# For getting the distance between two bUE coordinates
from geopy import distance  # type:ignore

from collections import deque

logger.remove()  # Remove default sink

# Main log for everything
logger.add("logs/base_station.log", rotation="10 MB")

# Individual files for 6 bUEs
for bue_id in range(10, 61, 10):
    path = f"logs/bue_{bue_id}.log"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    logger.add(
        path,
        rotation="5 MB",
        filter=lambda record, bue_id=bue_id: record["extra"].get("bue_id") == bue_id,
    )
"""
# This variable defines how long it will take for a connected bUE to be thought of as "disconnected"
# Unlike the TIMEOUT in bue_main.py, once this variable expires, it will not automatically disconnect the base
# station from the bUE. Instead, it will prompt the user that they might want to. This will allow the bUE to be able
# to reconnect once it is in range

# The system will recommend disconnecting after missing TIMEOUT PINGs.
# Exact timing depends on CHECK_FOR_TIMEOUTS_INTERVAL variable in base_station_tick()
"""
from constants import TIMEOUT, bUEs


# Internal imports
from ota import Ota


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

        self.ota = Ota(
            self.yaml_data["OTA_PORT"],
            self.yaml_data["OTA_BAUDRATE"],
            self.yaml_data["OTA_ID"],
        )
        logger.info(f"[DEBUG] OTA ID is set to: {self.ota.id}")

        self.EXIT = False

        # A list of the bUEs currently connected to the base station
        self.connected_bues = []

        """
        # A dictionary that will track how often a bUE is getting ticks
        # A bUE's id is the key. 
        # If the bUE has a value of TIMEOUT or TIMEOUT + 1, it has received a PING recently
        # If a bUE has missed a PING, this value will be decremented by one
        # until too many PINGs have been missed
        """
        self.bue_timeout_tracker = {}

        # Dictionary holds what each bUE's currently location is depending on last PING/UPD
        self.bue_coordinates = {}

        # Hold all UPD messages so they can be displayed in the UI
        self.stdout_history = deque()

        # A list that tracks what bUEs are currently in the TEST state
        self.testing_bues = []

        # Ping thread
        self.ping_bue_queue = queue.Queue()
        self.ping_bue_thread = threading.Thread(target=self.ping_bue_queue_handler)
        self.ping_bue_thread.start()

        # Listen for requests thread. Also handles PINGs.
        self.message_queue = queue.Queue()
        self.message_queue_thread = threading.Thread(target=self.req_queue_handler)
        self.message_queue_thread.start()

        # Tick thread for state machine
        self.tick_enabled = False
        self.state_machine_thread = threading.Thread(target=self.base_station_tick)
        self.state_machine_thread.start()

    def ping_bue_queue_handler(self):
        while not self.EXIT:
            try:
                task = self.ping_bue_queue.get(timeout=0.1)
                task()
                self.ping_bue_queue.task_done()
            except queue.Empty:
                time.sleep(0.01)
            except Exception as e:
                logger.error(f"ping_bue_queue_handler: Exception occurred: {e}")

    def ping_bue(self, bue_id, lat="", long=""):
        if bue_id in self.connected_bues:
            try:
                logger.bind(bue_id=bue_id).info(
                    f"Received PING from {bue_id}. Currently at Latitude: {lat}, Longitude: {long}"
                )
                self.ota.send_ota_message(bue_id, "PINGR")

                if bue_id in self.testing_bues:
                    self.testing_bues.remove(bue_id)

                if lat != "" and long != "":
                    self.bue_coordinates[bue_id] = [lat, long]

                self.bue_timeout_tracker[bue_id] = TIMEOUT + 1
            except Exception as e:
                logger.bind(bue_id=bue_id).error(f"ping_bue: Error while handling PING from {bue_id}: {e}")

    def check_bue_timeout(self):
        """
        This function will cycle through each bUE the base station should be connected to and make sure that
        it has been receiving some sort of message from it.
        The messages it checks for our PINGs and UPDs
        If we went a rotation without receiving a message, we might have lost connection with the bUE
        """
        for bue_id in self.connected_bues:
            if self.bue_timeout_tracker[bue_id] == TIMEOUT + 1:
                # If this is true we know we are getting PINGs from this bue. No need to fear
                self.bue_timeout_tracker[bue_id] = TIMEOUT
                continue
            if self.bue_timeout_tracker[bue_id] > 0:
                logger.bind(bue_id=bue_id).error(f"We missed a PING from {bue_id}")
                self.bue_timeout_tracker[bue_id] -= 1
            else:
                logger.error(f"We haven't heard from {bue_id} in awhile. Maybe disconnected?")

    def req_queue_handler(self):
        while not self.EXIT:
            try:
                task = self.message_queue.get(timeout=0.1)
                task()
                self.message_queue.task_done()
            except queue.Empty:
                time.sleep(0.01)

    # Listens for any incoming message from a bUE. Never called by itself. Runs if put in message_queue.
    def message_listener(self):

        new_messages = self.ota.get_new_messages()

        for message in new_messages:
            print(message)
            try:  # Receive messages should look like "{bue_id},{message}"
                try:
                    parts = message.split(",", 1)
                    bue_id = int(parts[0])
                    message_body = parts[1]
                    print(f"Mesage body: {message_body}")

                except Exception as e:
                    logger.error(f"message_listener: Failed to parse message '{message}': {e}")
                    continue  # Skip to the next message

                if message_body.startswith("REQ"):
                    logger.debug("Sending a CON")
                    self.ota.send_ota_message(bue_id, f"CON:{self.ota.id}")
                    self.bue_timeout_tracker[bue_id] = TIMEOUT
                    if not bue_id in self.connected_bues:
                        logger.bind(bue_id=bue_id).info(f"Received a request signal from {bue_id}")
                        self.connected_bues.append(bue_id)
                    else:
                        logger.error(f"Got a connection request from {bue_id} but it is already listed as connected")

                elif message_body.startswith("ACK"):
                    logger.bind(bue_id=bue_id).info(f"Received ACK from {bue_id}")

                elif message_body.startswith("PING"):  # Looks like <origin id>,PING,<lat>,<long>
                    header, lat, long = message_body.split(",")
                    print(f"header: {header}, lat: {lat}, long: {long}", flush=True)
                    self.ping_bue(bue_id, lat, long)

                elif message_body.startswith("UPD"):  # 40,55,UPD:LAT,LONG,STDOUT: [helloworld.py STDOUT] TyGoodTest,-42,8
                    if not bue_id in self.testing_bues:
                        self.testing_bues.append(bue_id)
                    header, lat, long, stdout = message_body.split(",", maxsplit=3)
                    # logger.info(f"Received UPD from {bue_id}. Currently at Latitude: {lat}, Longitude: {long}. Message: {stdout}")
                    logger.bind(bue_id=bue_id).info(f"Received UPD from {bue_id}. Message: {stdout}")
                    if lat != "" and long != "":
                        self.bue_coordinates[bue_id] = [lat, long]
                    else:
                        logger.bind(bue_id=bue_id).info("Lat and/or Long was empty")
                    # Reset the timeout for getting UPDs. If we haven't recieved an update in a while there is a problem
                    self.bue_timeout_tracker[bue_id] = TIMEOUT + 1

                    if stdout != "":
                        self.stdout_history.append(stdout)

                elif message_body.startswith("FAIL"):
                    logger.bind(bue_id=bue_id).error(f"Received FAIL from {bue_id}")
                    self.testing_bues.remove(bue_id)

                elif message_body.startswith("DONE"):
                    logger.bind(bue_id=bue_id).info(f"Received DONE from {bue_id}")
                    self.testing_bues.remove(bue_id)

                elif message_body.startswith("PREPR"):
                    logger.bind(bue_id=bue_id).info(f"Received PREPR from {bue_id}")
                    self.testing_bues.append(bue_id)

                elif message_body.startswith("CANCD"):
                    logger.bind(bue_id=bue_id).info(f"Received CANCD from {bue_id}")
                    self.testing_bues.remove(bue_id)
                elif message_body.startswith("BAD"):
                    logger.bind(bue_id=bue_id).info(f"Received BAD from {bue_id}")
                    self.stdout_history.append(f"Received a BAD from {bUEs[str(bue_id)]}")

                else:
                    logger.info(f"Received undefined message {message}")

            except ValueError:
                logger.error("message_listener: Error listening for messages")

    def get_distance(self, bue_1, bue_2):
        try:
            c1 = self.bue_coordinates[bue_1]
            c2 = self.bue_coordinates[bue_2]

            # Validate that coordinates are lists/tuples with 2 elements
            if not isinstance(c1, (list, tuple)) or len(c1) != 2:
                logger.error(f"Invalid coordinates for bUE {bue_1}: {c1}")
                return None

            if not isinstance(c2, (list, tuple)) or len(c2) != 2:
                logger.error(f"Invalid coordinates for bUE {bue_2}: {c2}")
                return None

            # Validate that coordinates are numeric and within valid ranges
            try:
                lat1, lon1 = float(c1[0]), float(c1[1])
                lat2, lon2 = float(c2[0]), float(c2[1])
            except (ValueError, TypeError):
                logger.error(f"Non-numeric coordinates: bUE {bue_1}: {c1}, bUE {bue_2}: {c2}")
                return None

            # Check if coordinates are within valid ranges
            if not (-90 <= lat1 <= 90) or not (-180 <= lon1 <= 180):
                logger.error(f"Invalid latitude/longitude for bUE {bue_1}: lat={lat1}, lon={lon1}")
                return None

            if not (-90 <= lat2 <= 90) or not (-180 <= lon2 <= 180):
                logger.error(f"Invalid latitude/longitude for bUE {bue_2}: lat={lat2}, lon={lon2}")
                return None

            # Check if coordinates are not empty/zero (optional - depends on your use case)
            if (lat1 == 0 and lon1 == 0) or (lat2 == 0 and lon2 == 0):
                logger.warning(f"Zero coordinates detected: bUE {bue_1}: {c1}, bUE {bue_2}: {c2}")

            logger.info(f"Calculating distance between bUE {bue_1} at ({lat1}, {lon1}) and bUE {bue_2} at ({lat2}, {lon2})")

            return distance.great_circle((lat1, lon1), (lat2, lon2)).meters

        except KeyError as e:
            logger.error(f"bUE coordinates not found: {e}")
            return None
        except Exception as e:
            logger.error(f"Error calculating distance: {e}")
            return None

    def base_station_tick(self, loop_dur=0.01):

        # The base station will read incoming messages roughly every LISTEN_FOR_MESSAGE_INTERVAL seconds
        LISTEN_FOR_MESSAGE_INTERVAL = 1
        listen_for_message_counter = 0
        listen_for_message = round(LISTEN_FOR_MESSAGE_INTERVAL / loop_dur)

        # The base station will check to see if a bUE has timed out every CHECK_FOR_TIMEOUTS_INTERVAL seconds
        CHECK_FOR_TIMEOUTS_INTERVAL = 10
        check_for_timeouts_counter = 0
        check_for_timeouts = round(CHECK_FOR_TIMEOUTS_INTERVAL / loop_dur)

        while not self.EXIT:

            if not self.tick_enabled:
                time.sleep(0.1)
                continue

            loop_start = time.time()

            if listen_for_message_counter % listen_for_message == 0:
                self.message_queue.put(self.message_listener)
                listen_for_message_counter = 0

            if check_for_timeouts_counter % check_for_timeouts == 0:
                self.message_queue.put(self.check_bue_timeout)
                check_for_timeouts_counter = 0

            listen_for_message_counter += 1
            check_for_timeouts_counter += 1

            elapsed = time.time() - loop_start
            if elapsed < loop_dur:
                time.sleep(loop_dur - elapsed)

    def __del__(self):
        try:
            self.EXIT = True
            if hasattr(self, "ping_bue_thread"):
                self.ping_bue_thread.join()
            if hasattr(self, "message_queue_thread"):
                self.message_queue_thread.join()
            if hasattr(self, "state_machine_thread"):
                self.state_machine_thread.join()
            if hasattr(self, "ota"):
                self.ota.__del__()
            if hasattr(self, "connected_bues"):
                self.connected_bues.clear()
        except Exception as e:
            logger.warning(f"__del__: Exception during cleanup: {e}")
