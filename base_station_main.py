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
import sys
import threading
import time
from datetime import datetime
from loguru import logger
from enum import Enum, auto
from yaml import load, Loader

# For getting the distance between two bUE coordinates
from geopy import distance


logger.remove()
logger.add("file.log", rotation="10 MB") # Example: Add a file sink for all logs

# This variable defines how long it will take for a connected bUE to be thought of as "disconnected"
# Unlike the TIMEOUT in bue_main.py, once this variable expires, it will not automatically disconnect the base
# station from the bUE. Instead, it will prompt the user that they might want to. This will allow the bUE to be able
# to reconnect once it is in range

# The system will recommend disconnecting after missing TIMEOUT * 2 PINGs.
# Exact timing depends on CHECK_FOR_TIMEOUTS_INTERVAL variable in base_station_tick()
TIMEOUT = 3


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

        self.ota = Ota(self.yaml_data["OTA_PORT"], self.yaml_data["OTA_BAUDRATE"], self.yaml_data["OTA_ID"])
        logger.info(f"[DEBUG] OTA ID is set to: {self.ota.id}")

        self.EXIT = False

        # A list of the bUEs currently connected to the base station
        self.connected_bues = []

        # A dictionary that will track how often a bUE is getting ticks
        # A bUE's id is the key. 
        # If the bUE has a value of TIMEOUT or TIMEOUT + 1, it has received a PING recently
        # If a bUE has missed a PING, this value will be decremented by one
        # until too many PINGs have been missed
        self.bue_timeout_tracker = {}

        #Dictionary holds what each bUE's currently location is depending on last PING/UPD
        self.bue_coordinates = {}

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
                pass
    
    def ping_bue(self, bue_id, lat, long):
        if(bue_id in self.connected_bues):
            logger.info(f"Received PING from {bue_id}. Currently at Latitude: {lat}, Longitude: {long}")
            self.ota.send_ota_message(bue_id, "PINGR")
            logger.info(f"Sent a PINGR to {bue_id}")

            if lat not in (None, "None") and long not in (None, "None"):
                self.bue_coordinates[bue_id] = [lat, long]


            # TIMEOUT + 1 is a signal to the rest of the program that a PING has been received
            ## ERROR? Was not in if statement but I moved it into it 
            self.bue_timeout_tracker[bue_id] = TIMEOUT + 1
    

    # This function will cycle through each bUE the base station should be connected to and make sure that
    # it has been receiving some sort of message from it.
    # The messages it checks for our PINGs and UPDs
    #
    # If we went a rotation without receiving a message, we might have lost connection with the bUE 
    def check_bue_timeout(self):
        for bue_id in self.connected_bues:
            if self.bue_timeout_tracker[bue_id] == TIMEOUT + 1:
                # If this is true we know we are getting PINGs from this bue. No need to fear
                self.bue_timeout_tracker[bue_id] = TIMEOUT
                return
            if self.bue_timeout_tracker[bue_id] > -TIMEOUT:
                logger.error(f"We missed a PING from {bue_id}")
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
                pass
    
    # Listens for any incoming message from a bUE. Never called by itself. Runs if put in message_queue.
    def message_listener(self):

        new_messages = self.ota.get_new_messages()

        for message in new_messages:
            try: # Receive messages should look like "+RCV={origin},{len(message)},{message}"
                message = message[5:] # remove +RCV= from beginning of the message 
                parts = message.split(",")
                bue_id = int(parts[0])
                if "REQ" in message:
                    if not bue_id in self.connected_bues:
                        logger.info(f"Received a request signal from {bue_id}")
                        self.ota.send_ota_message(bue_id, f"CON:{self.ota.id}")
                        self.connected_bues.append(bue_id)
                        self.bue_timeout_tracker[bue_id] = TIMEOUT
                    else:
                        logger.error(f"Got a connection request from {bue_id} but it is already listed as connected")
                elif "ACK" in message:
                    logger.info(f"Received ACK from {bue_id}")
                elif "PING" in message: # Looks like <origin id>,<length>,PING,<lat>,<long>,-55,8
                    if len(parts) >= 5:
                        lat = parts[3]
                        long = parts[4]
                    else: 
                        lat = "None"
                        long = "None"
                    self.ping_bue(bue_id, lat, long)
                elif "UPD" in message:
                    lat = parts[3]
                    long = parts[4]
                    logger.info(f"Received UPD from {bue_id}. Currently at Latitude: {lat}, Longitude: {long}")
                    if lat is not None and long is not None:
                        self.bue_coordinates[bue_id] = [lat, long]
                    # Reset the timeout for getting UPDs. If we haven't recieved an update in a while there is a problem
                    self.bue_timeout_tracker[bue_id] = TIMEOUT + 1
                elif "FAIL" in message:
                    logger.error(f"Received FAIL from {bue_id}")
                    self.testing_bues.remove(bue_id)
                elif "DONE" in message:
                    logger.info(f"Received DONE from {bue_id}")
                    self.testing_bues.remove(bue_id)
                elif "PREPR" in message:
                    logger.info(f"Received PREPR from {bue_id}")
                elif "CANCD" in message:
                    logger.info(f"Received CANCD from {bue_id}")
                else:
                    logger.info(f"Received undefined message {message}")

            except ValueError:
                logger.error("message_listener: Error listening for messages")



    def base_station_tick(self, loop_dur=0.01):
        while not self.EXIT:
            loop_start = time.time()

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
                    continue

                loop_start = time.time()

                if listen_for_message_counter % listen_for_message == 0:
                    self.message_queue.put(self.message_listener)
                
                if check_for_timeouts_counter % check_for_timeouts == 0:
                    self.message_queue.put(self.check_bue_timeout)
                
                listen_for_message_counter += 1
                check_for_timeouts_counter += 1

                while time.time() - loop_start < loop_dur:
                    pass

    def __del__(self):
        try:
            if hasattr(self, 'ping_bue_thread'):
                self.ping_bue_thread.join()
            if hasattr(self, 'message_queue_thread'):
                self.message_queue_thread.join()
            if hasattr(self, 'state_machine_thread'):
                self.state_machine_thread.join()
            if hasattr(self, 'ota'):
                self.ota.__del__()
            if hasattr(self, 'connected_bues'):
                self.connected_bues.clear()
        except Exception as e:
            logger.warning(f"__del__: Exception during cleanup: {e}")


# This function handles the console input for sending commands to bUEs      
def user_input_handler(base_station):
    
    ## TODO: GPS timing needs to be included

    while not base_station.EXIT:
        try:
            user_input = input(">> ").strip()
            if not user_input:
                continue
            
            if user_input == "LIST": #Temporary TODO Implment this
                connected_bues = " ".join(str(bue) for bue in base_station.connected_bues)
                logger.info(f"Currently connected to {connected_bues}")
                continue
                
            parts = user_input.split(".")

            bue_id = int(parts[0])

            if(bue_id not in base_station.connected_bues):
                logger.error(f"Not currently connected to bUE {bue_id}")
                continue

            # At any time, a bUE can be disconnected from the base station. 
            # This will likely only happen it they bUE has not been heard from in a while
            if(parts[1] == "DISC"): # Format: <bue_id>.DISC
                logger.info(f"Disconnecting from bUE {bue_id}")
                base_station.connected_bues.remove(bue_id)
                if bue_id in base_station.bue_coordinates.keys():
                    del base_station.bue_coordinates[bue_id]
                    
            # If the base station ever wants to prematurely terminate a test in a specific bUE, this
            # command allows them to do so
            elif(parts[1] == "CANC"): # Format: <bue_id>.CANC
                if bue_id in base_station.testing_bues: ##TODO: bUE needs to take this request and actually terminate the process
                    logger.info(f"Sending a CANC to {bue_id}")
                    base_station.testing_bues.remove(bue_id) ## TODO. Uncomment this line. Maybe? It can be handled automatically
                    base_station.ota.send_ota_message(bue_id, "CANC")
                else:
                    logger.error(f"{bue_id} is not currently running any tests")
                
            # For sending tests to a specific bUE
            elif parts[1] == "TEST": # Format: <bue_id>.TEST.<file>.<configuration>.<role>.<starttime>
                if ";" not in parts[2]: ## TODO: What other checks need to be done here?
                    logger.info(f"Sending {bue_id} TEST with config {parts[2]}. Will start at {parts[4]}")
                    base_station.testing_bues.append(bue_id)
                    base_station.ota.send_ota_message(bue_id, f"TEST.{parts[2]}.{parts[3]}.{parts[4]}.{parts[5]}")
                else:
                    logger.error(f"This TEST does not match the required format")

            elif parts[1] == "DIST": # Format: <bue_id>.DIST.<bue_2>
                bue_2 = int(parts[2])

                if bue_2 not in base_station.connected_bues:
                    logger.error(f"Not currently connected to bUE {bue_2}")
                    continue

                if bue_id not in base_station.bue_coordinates or bue_2 not in base_station.bue_coordinates:
                    missing = [b for b in (bue_id, bue_2) if b not in base_station.bue_coordinates]
                    logger.error(f"Missing coordinates for: {', '.join(missing)}")
                    continue

                

                point1 = base_station.bue_coordinates[bue_id]
                point2 = base_station.bue_coordinates[bue_2]

                if "None" in point1 or "None" in point2:
                    logger.error(f"Missing coordinates from {bue_id} or {bue_2}")
                    continue

                dist = distance.distance(point1, point2)

                logger.info(f"{bue_id} and {bue_2} are currently {dist} apart")

            else:
                logger.error(f"Unknown command: {user_input}")


        except Exception as e:
            logger.error(f"[User Input] Error {e}")


if __name__ == "__main__":
    start_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    logger.info(f"This marks the start of the base station service at {start_time}")

    try:
        base_station = Base_Station_Main(yaml_str="config_base.yaml")

        user_input_thread = threading.Thread(target=user_input_handler, args=(base_station,))
        user_input_thread.start()

        base_station.tick_enabled = True


        while not base_station.EXIT:
            time.sleep(0.2)

    except KeyboardInterrupt:
        logger.info("Exiting the Base Station service")
        if base_station is not None:
            base_station.EXIT = True
            time.sleep(0.5)
            base_station.__del__()
        if 'user_input_thread' in locals() and user_input_thread.is_alive():
            user_input_thread.join(timeout=2.0)
        sys.exit(0)

