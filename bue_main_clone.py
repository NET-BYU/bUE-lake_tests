"""
bue_main.py
Bryson Schiel

This is the main file for the bUE service. It handles the state machine and the OTA and UTW modules.
Documentation can be found in the NET Lab Notion at the page "bUE Python Code Guide".
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

# Internal imports
from ota import Ota
from utw import Utw

TIMEOUT = 3

class State(Enum):
    INIT = auto()
    CONNECT_OTA = auto()
    IDLE = auto()
    UTW_TEST = auto()


class bUE_Main:
    def __init__(self, yaml_str):
        self.yaml_data = {}
        
        # Load the yaml file
        try:
            with open(yaml_str) as f:
                self.yaml_data = load(f, Loader=Loader)
                logger.info("__init__: Loading config.yaml; items are:")
                for key, value in self.yaml_data.items():
                    logger.info(f"  {key}: {value}")
        except FileNotFoundError:
            logger.error(f"__init__: YAML file {yaml_str} not found", file=sys.stderr)
            sys.exit(1)

        # Initialize the OTA and UTW objects
        self.ota = Ota(self.yaml_data['OTA_PORT'], self.yaml_data['OTA_BAUDRATE'], self.yaml_data['OTA_ID'])
        # self.utw = Utw...

        # Build the state machine - states
        self.cur_st, self.nxt_st = State.INIT, State.INIT
        logger.info(f"__init__: Initializing current state to {self.cur_st.name}")
        self.prv_st = self.cur_st

        # Build the state machine - flags
        self.EXIT = False
        self.ota_connected = False
        self.ota_timeout = TIMEOUT

        # Network information
        self.ota_base_station_id = None
        
        # Set up the ota thread
        self.ota_task_queue = queue.Queue()
        self.ota_thread = threading.Thread(target=self.ota_task_queue_handler)
        self.ota_thread.start()

        # Set up the UTW thread
        self.utw_task_queue = queue.Queue()
        self.utw_thread = threading.Thread(target=self.utw_task_queue_handler)
        self.utw_thread.start()

        # Set up the tick loop
        self.tick_enabled = False
        self.st_thread = threading.Thread(target=self.bue_tick)
        self.st_thread.start()

    ### OTA MODULE METHODS ###

    def ota_task_queue_handler(self):
        while not self.EXIT:
            try:
                task = self.ota_task_queue.get(timeout=0.1)  # Get a task
                task()  # Execute the function
                self.ota_task_queue.task_done()
            except queue.Empty:
                pass  # No task, continue looping

    def ota_connect_req(self):
        if self.ota_connected:
            logger.warning(f"connect_ota_req: OTA device is already connected to base station {self.ota_base_station_id}")
            return
        
        # See if there are any new messages from the OTA device
        #  Note: using get_new_messages will destroy any other incoming messages,
        #   but these are unwanted until the device is connected
        new_messages = self.ota.get_new_messages()

        for message in new_messages:
            try:
                # A connecting message would take the form of "+RCV=<base station id>,<Length>,CON:<base station id>,<RSSI>,<SNR>"
                #  We want to extract the base station id from this message
                if "CON:" in message:
                    message = message[5:]  # Remove the "+RCV=" part
                    parts = message.split(",")
                    if parts[2].startswith("CON:"):  # TY This checks to see if the received message matches a base station connecting
                        if parts[0] == parts[2][4:]: # format. If it does we are now going to be in the connected state
                            self.ota_connected = True
                            self.ota_base_station_id = int(parts[0])
                            logger.info(f"ota_connect_req: OTA device connected to base station {self.ota_base_station_id}")
                            self.ota_timeout = TIMEOUT
                            self.ota.send_ota_message(self.ota_base_station_id, "ACK")
                            return
                        else:
                            logger.warning(f"ota_connect_req: received malformed message: base station id {parts[0]} does not match {parts[2][4:]}")


            except ValueError:
                logger.error("ota_connect_req: Error parsing OTA message")
                continue

        
        self.ota_base_station_id = 0 if self.ota_base_station_id is None else self.ota_base_station_id

        # Send a REQ (request) message through the OTA device
        # Next cycle we will hopefully have a CON (connected) response
        self.ota.send_ota_message(self.ota_base_station_id, "REQ") # TY bUE sends a message back to the base station asking to 
                                                                   # be connected as well
    
    def ota_idle_ping(self):
        if not self.ota_connected:
            logger.warning("ota_idle_ping: OTA device is not connected to base station")
            return
        
        # See if there are any new messages from the OTA device
        new_messages = self.ota.get_new_messages()
        got_pingr = False

        for message in new_messages:
            message = message[5:]  # Remove the "+RCV=" part
            parts = message.split(",")

            ## TODO: there are one of four messages that we could receive in the idle state:
            # 1. A CON (connect0 message from the base station; we can (probably) ignore this for now;
            #     ideally, the base station would have seen our ACK message, but it can also see our PING
            if "ACK" in message:
                logger.info(f"Got an ACK from {self.ota_base_station_id}")

            # If we received a PINGR message, we know we are still connected to the base station.
            # We will not time out our connection
            elif "PINGR" in message:
                logger.info(f"Got a PINGR from {self.ota_base_station_id}")
                self.ota_timeout = TIMEOUT
                got_pingr = True

            elif "TEST" in message:
                logger.info(f"Time to run TEST: {parts[3]}")
                ## TODO Run parts[3]

            else:
                print(message)

        if not got_pingr:
            self.ota_timeout -= 1
            
            if(self.ota_timeout <= 0):
                ## TODO: If we haven't gotten a PINGR in a while we need to switch back to CONNECT state
                logger.info(f"We haven't heard from {self.ota_base_station_id} in a while....")
            if(self.ota_timeout <= -TIMEOUT):
                logger.info(f"We have not heard from {self.ota_base_station_id} in too long. Disconnecting...")
                self.ota_connected = False

        ## TODO: Get the most recent GPS string
        # gps data...
        
        # Send a PING message through the OTA device
        #self.ota.send_ota_message(self.ota_base_station_id, f"PING:{gps_data}")
        self.ota.send_ota_message(self.ota_base_station_id, "PING") # test ping for now



    ### UTW MODULE METHODS ###

    def utw_task_queue_handler(self):
        while not self.EXIT:
            try:
                task = self.utw_task_queue.get(timeout=0.1)  # Get a task
                task()  # Execute the function
                self.utw_task_queue.task_done()
            except queue.Empty:
                pass



    ### STATE MACHINE METHODS ###

    def state_change_logger(self):
        if self.cur_st != self.prv_st:
            logger.info(f"state_change_logger: State changed from {self.prv_st.name} to {self.cur_st.name}")
            self.prv_st = self.cur_st


    def bue_tick(self, loop_dur=0.01):
        # Interconnect flags

        # Internal counters

        # TY How often to try to connect
        CONNECT_OTA_REQ_INTERVAL = 1
        connect_ota_counter = 0
        connect_ota_req = round(CONNECT_OTA_REQ_INTERVAL / loop_dur)

        # TY How often to ping (once in idle state)
        IDLE_PING_OTA_INTERVAL = 10
        idle_counter = 0
        idle_ping_ota = round(IDLE_PING_OTA_INTERVAL / loop_dur)
        
        while not self.EXIT:
            
            if not self.tick_enabled:
                continue

            loop_start = time.time()

            # Perform the state transition first
            match self.cur_st:
                case State.INIT:
                    # Setup should all be complete, immediately move to the CONNECT_OTA state
                    connect_ota_counter = 0
                    self.nxt_st = State.CONNECT_OTA
                
                case State.CONNECT_OTA:
                    # Wait until the OTA device is connected to the OTA network
                    if self.ota_connected:
                        idle_counter = 0
                        self.nxt_st = State.IDLE

                case State.IDLE:
                    # If we lost connected we will go back to the connecting state
                    if not self.ota_connected:
                        connect_ota_counter = 0
                        self.nxt_st = State.CONNECT_OTA
                
                case State.UTW_TEST:
                    pass
                
                case _:
                    logger.error(f"tick: Invalid state transition {self.cur_st.name}")
                    sys.exit(1)

            # Perform the state actions next
            match self.cur_st:
                case State.INIT:
                    pass
                
                case State.CONNECT_OTA:
                    connect_ota_counter += 1

                    if connect_ota_counter % connect_ota_req == 0:
                        self.ota_task_queue.put(self.ota_connect_req)
                        
                
                case State.IDLE:
                    idle_counter += 1

                    if idle_counter % idle_ping_ota == 0:
                        self.ota_task_queue.put(self.ota_idle_ping)
                        
                
                case State.UTW_TEST:
                    pass
                
                case _:
                    logger.error(f"tick: Invalid state action {self.cur_st.name}")
                    sys.exit(1)

            # Update the current state
            self.cur_st = self.nxt_st

            # Log any state change
            self.state_change_logger()
            
            # End of the tick loop, make sure we start loop_dur seconds after the loop started
            while time.time() - loop_start < loop_dur:
                pass


    


    def __del__(self):
        try:
            if hasattr(self, 'st_thread'):
                self.st_thread.join()
            if hasattr(self, 'ota_thread'):
                self.ota_thread.join()
            if hasattr(self, 'utw_thread'):
                self.utw_thread.join()
            if hasattr(self, 'ota'):
                self.ota.__del__()
            # if hasattr(self, 'utw'):
            #     self.utw.__del__()
        except Exception as e:
            logger.warning(f"__del__: Exception during cleanup: {e}")
            # self.utw.__del__()




if __name__ == "__main__":
    
    # Get the current time
    start_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    
    # Set up the logger
    # logger.add(f"bue_logs/bue_log_{start_time}.log", format="{time} {level} {message}", level="INFO")
    # logger.add(format="{time} {level} {message}", level="INFO", sink=sys.stdout)

    # Example usage
    logger.info(f"This marks the start of the bUE service at {start_time}")
    
    try:
        bue = bUE_Main(yaml_str="config_bue_5.yaml")

        # Any other setup code can go here

        bue.tick_enabled = True

        while True:
            pass

    except KeyboardInterrupt:
        if bue is not None:
            logger.info("Exiting the bUE service")
            bue.EXIT = True
            time.sleep(0.5)
            bue.__del__()
            sys.exit(0)




