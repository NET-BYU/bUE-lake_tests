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

logger.remove()
logger.add("file.log", rotation="10 MB") # Example: Add a file sink for all logs


# Internal imports
from ota import Ota
from utw import Utw

class State(Enum):
    INIT = auto()
    IDLE = auto()
    TESTING = auto()

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

        self.cur_st, self.nxt_st = State.INIT, State.INIT
        logger.info(f"__init__: Initializing current state to {self.cur_st.name}")
        self.prv_st = self.cur_st

        self.EXIT = False

        # A list of the bUEs currently connected to the base station
        self.connected_bues = []
        
        # Flags that handle what state we are currently in
        self.running_test = False

        # Ping thread
        self.ping_bue_queue = queue.Queue()
        self.ping_bue_thread = threading.Thread(target=self.ping_bue_queue_handler)
        self.ping_bue_thread.start()

        # Listen for requests thread
        self.req_queue = queue.Queue()
        self.req_queue_thread = threading.Thread(target=self.req_queue_handler)
        self.req_queue_thread.start()

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
    
    def ping_bue(self):
        pass

    def req_queue_handler(self):
        while not self.EXIT:
            try:
                task = self.req_queue.get(timeout=0.1)
                task()
                self.req_queue.task_done()
            except queue.Empty:
                pass
    
    # Listens for requests from bUEs. Never called by itself. Run if put in req_queue.
    def req_listener(self):
        # logger.info("Checking bUE REQs")

        new_messages = self.ota.get_new_messages()

        for message in new_messages:
            try: # Receive messages should look like "+RCV={origin},{len(message)},{message}"
                message = message[5:] # remove +RCV= from beginning of the message 
                parts = message.split(",")
                bue_id = int(parts[0])
                if "REQ" in message: # TO DO: This might be too simple of a check
                    # TO DO: Do I want to only allow bues to connect if they aren't listed as connected?
                    logger.info(f"Received a request signal from {bue_id}")
                    self.ota.send_ota_message(bue_id, f"CON:{self.ota.id}")
                    # self.connecting_to_bue = True
                elif "ACK" in message:
                    logger.info(f"Received ACK from {bue_id}")
                elif "PING" in message:
                    logger.info(f"Received PING from {bue_id}")
                else:
                    print(message)

            except ValueError:
                logger.error("req_listener: Error listening to REQ from bUE")
    

    def state_change_logger(self):
        if self.cur_st != self.prv_st:
            logger.info(f"state_change_logger: State changed from {self.prv_st.name} to {self.cur_st.name}")
            self.prv_st = self.cur_st


    def base_station_tick(self, loop_dur=0.01):
        while not self.EXIT:
            loop_start = time.time()

            #self.req_queue.put(self.req_listener)
            # self.req_listener()


            # How often to listen/process new bUE requests
            LISTEN_FOR_REQUEST_INTERVAL = 1
            listen_for_request_counter = 0
            listen_for_request = round(LISTEN_FOR_REQUEST_INTERVAL / loop_dur)

            while not self.EXIT:

                if not self.tick_enabled:
                    continue

                loop_start = time.time()

                # Planning
                match self.cur_st:
                    case State.INIT:
                        self.nxt_st = State.IDLE
                        listen_for_request_counter = 0
                    
                    case State.IDLE:
                        # TO DO: If REQ is received, go to CONNECTING state
                        listen_for_request_counter += 1
                        # if self.connecting_to_bue == True: 
                        #     self.nxt_st = State.CONNECTING
                        # TO DO: If the user starts a TEST, go to TESTING state
                        pass
                    
                    # case State.CONNECTING:
                    #     # TO DO: stay in this state until ACK is recieved or a timeout period has past
                    #     listen_for_request_counter += 1
                    #     if(not self.connecting_to_bue):
                    #         self.nxt_st = State.IDLE
                    
                    case State.TESTING:
                        # TO DO: stay in this state until DONE is received from correct bUEs or a timeout period has past
                        pass

                # Actions
                match self.cur_st: 
                    case State.INIT:
                        pass

                    case State.IDLE:
                        # TO DO: add a req_listener to the queue periodically
                        if listen_for_request_counter % listen_for_request == 0:
                            self.req_queue.put(self.req_listener)
                        pass
                    
                    # case State.CONNECTING:
                    #     # TO DO: Listen for an acknowledge request
                    #     # if listen_for_request_counter % listen_for_request == 0:
                    #     #     self.req_queue.put(self.ack_listener) 
                    #     pass

                    case State.TESTING:
                        # TO DO: Send test message to the correct bUEs. Wait for their response
                        pass

                # Update the current state
                self.cur_st = self.nxt_st

                self.state_change_logger()

                while time.time() - loop_start < loop_dur:
                    pass

    def __del__(self):
        try:
            if hasattr(self, 'ping_bue_thread'):
                self.ping_bue_thread.join()
            if hasattr(self, 'req_queue_thread'):
                self.req_queue_thread.join()
            if hasattr(self, 'state_machine_thread'):
                self.state_machine_thread.join()
            if hasattr(self, 'ota'):
                self.ota.__del__()
            if hasattr(self, 'connected_bues'):
                self.connected_bues.clear()
            # if hasattr(self, 'utw'):
            #     self.utw.__del__()
        except Exception as e:
            logger.warning(f"__del__: Exception during cleanup: {e}")
            # self.utw.__del__()

def user_input_handler(base_station):

    while not base_station.EXIT:
        try:
            user_input = input(">> ").strip()
            if not user_input:
                continue

            print(user_input)

        except Exception as e:
            logger.error(f"[User Input] Error {e}")


if __name__ == "__main__":
    start_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    logger.info(f"This marks the start of the base station service at {start_time}")

    try:
        base_station = Base_Station_Main(yaml_str="config_base.yaml")

        base_station.tick_enabled = True

        user_input_thread = threading.Thread(target=user_input_handler, args=(base_station,))
        user_input_thread.start()

        while not base_station.EXIT:
            time.sleep(0.2)

    except KeyboardInterrupt:
        logger.info("Exiting the Base Station service")
        # TO DO: implement __del__
        if base_station is not None:
            base_station.EXIT = True
            time.sleep(0.5)
            base_station.__del__()
        if 'user_input_thread' in locals() and user_input_thread.is_alive():
            user_input_thread.join(timeout=2.0)
        sys.exit(0)
