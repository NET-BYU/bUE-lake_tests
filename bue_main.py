# Standard library imports
import os
import queue
import sys
import select
import signal
import subprocess
import threading
import time
from datetime import datetime
from loguru import logger
from enum import Enum, auto
from yaml import load, Loader

from pathlib import Path

is_pi = (
    Path("/sys/firmware/devicetree/base/model").exists()
    and "raspberry pi" in Path("/sys/firmware/devicetree/base/model").read_text().lower()
)
if is_pi:
    import gps

logger.add("logs/bue.log", rotation="10 MB")  # Example: Add a file sink for all logs

# Internal imports
from ota import Ota
from utw import Utw
from constants import Bue_State

# This variable manages how many PINGRs should be missed until the bUE disconnects from the base station
# and goes back to its CONNECT_OTA state.
TIMEOUT = 6
BROADCAST_OTA_ID = 0



class Test_State(Enum):
    IDLE = auto()
    RUNNING = auto()
    PASS = auto()
    FAIL = auto()
    CLEANUP = auto()


class bUE_Main:
    def __init__(self, yaml_str="bue_config.yaml"):
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
        # Give it a 5 second timeout
        start_ota_build_time = time.time()
        while True:
            try:
                self.ota = Ota(self.yaml_data["OTA_PORT"], self.yaml_data["OTA_BAUDRATE"])
                break
            except Exception as e:
                logger.error(f"Failed to initialize OTA module: {e}")
                time.sleep(2)

        self.utw = Utw()

        # Fetch the Reyax ID from the OTA module
        self.reyax_id = None
        while self.reyax_id is None:
            time.sleep(0.2)
            self.reyax_id = self.ota.fetch_id()
        logger.info(f"__init__: OTA module initialized with Reyax ID {self.reyax_id}")

        # Fetch the device hostname
        self.hostname = os.uname().nodename

        # Build the state machine - states
        self.cur_st, self.nxt_st = Bue_State.INIT, Bue_State.INIT
        logger.info(f"__init__: Initializing current state to {self.cur_st.name}")
        self.prv_st = self.cur_st

        # State machine EXIT signal - closes everything
        self.EXIT = False

        # State machine - flags
        # To be raised by ota and lowered by sm
        self.flag_ota_connected = threading.Event()
        self.flag_ota_pingr = threading.Event()
        self.flag_ota_start_testing = threading.Event()
        self.flag_ota_cancel_test = threading.Event()
        self.flag_ota_reload = threading.Event()
        self.flag_ota_restart = threading.Event()
        self.flag_ota_tout = threading.Event()

        # State machine - statuses
        # These are the main internal signals used by the state machine
        self.status_ota_connected = False

        # Network information
        self.ota_base_station_id = None
        self.ota_test_params = None

        # Variable to hold how many PINGRs have been missed
        self.ota_pingrs_missed: int = 0

        # Variables to handle test subprocess
        # self.test_command = None
        self.test_start_time = None
        # self.test_info = None
        # self.test_process = None
        # self.test_stdout_queue = queue.Queue()
        # self.test_stdout_thread = None
        self.flag_test_running = False

        # Holds what state the test currently is in
        self.test_state = Test_State.IDLE

        # Build the state machine - flags
        self.counter_ota_timeout = 0
        self.MAX_ota_timeout = TIMEOUT
        # TODO - add functionality for timeout when also sending a test update

        # Flag to be set if a test is sent
        self.start_testing = False
        self.cancel_test = False
        # TODO - delete/modify these once test functionality gets added

        # Set up the ota threads
        self.ota_incoming_queue = queue.Queue()
        self.ota_outgoing_queue = queue.Queue()

        self.ota_trx_thread = threading.Thread(target=self.ota_message_trx)
        self.ota_trx_thread.start()

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
        When messages are received, they are interpretted here. Based on the message,
        certain flags may be raised and variables set. These flags need to be lowered by
        the state machine as soon as they're read so that new messages are recorded. The
        variables that are set in here are read-only to the state machine functions.
        """
        while not self.ota_incoming_queue.empty():
            try:
                message: str = self.ota_incoming_queue.get()
                logger.info(f"Received OTA message: {message}")

                # Process the message based on its type
                # A message body is "<source id>,<message type><:message body (optional)>"
                src_id, msg = message.split(",", 1)

                if ":" in msg:
                    msg_type, msg_body, *_ = msg.split(":", maxsplit=2)
                else:
                    msg_type, msg_body = msg, None

                if msg_type == "CON":
                    if int(src_id) != int(msg_body):
                        logger.warning(f"CON message source ID {src_id} does not match body {msg_body}")
                    else:
                        self.ota_base_station_id = int(msg_body)
                        self.flag_ota_connected.set()

                elif msg_type == "PINGR":
                    self.flag_ota_pingr.set()

                elif msg_type == "TEST":
                    self.flag_ota_start_testing.set()
                    self.ota_test_params = msg_body

                elif msg_type == "CANC":
                    self.flag_ota_cancel_test.set()

                elif msg_type == "RELOAD":
                    self.flag_ota_reload.set()

                elif msg_type == "RESTART":
                    self.flag_ota_restart.set()

                else:
                    logger.warning(f"Unknown message type: {msg_type}")

                self.ota_incoming_queue.task_done()
            except Exception as e:
                logger.error(f"Error processing OTA messages: {e}")
                self.ota_incoming_queue.task_done()

    ## OTA Task Handling Thread and Functions ##
    def ota_task_queue_handler(self):
        """
        A thread to handle all the OTA-related tasks that will be called by the state machine
        """
        while not self.EXIT:
            try:
                task = self.ota_task_queue.get(timeout=0.1)  # Get a task
                task()  # Execute the function
                self.ota_task_queue.task_done()
            except queue.Empty:
                pass  # No task, continue looping

    def ota_connect_req(self):
        if self.status_ota_connected:
            logger.warning(f"connect_ota_req: OTA device is already connected to base station {self.ota_base_station_id}")
            return

        # Start by checking the flag
        if self.flag_ota_connected.is_set():
            # Our connection request was received, set the status and send an ACK
            self.status_ota_connected = True
            self.flag_ota_connected.clear()
            logger.info(f"ota_connect_req: OTA device is connected to network with base station {self.ota_base_station_id}")

            # Send the ACK
            self.ota_outgoing_queue.put((self.ota_base_station_id, "ACK"))
            return

        # If flag not set, send another REQ message
        self.ota_outgoing_queue.put((BROADCAST_OTA_ID, f"REQ:{self.hostname},{self.reyax_id}"))

    def ota_ping(self):
        if is_pi:
            lat, long = self.gps_handler()
        else:
            lat, long = "", ""

        if self.flag_ota_pingr.is_set():
            self.flag_ota_pingr.clear()
        else:
            self.ota_pingrs_missed += 1

        self.ota_outgoing_queue.put((self.ota_base_station_id, f"PING:{self.cur_st.value},{lat},{long}"))
        logger.info(f"ota_ping: Sent ping to {self.ota_base_station_id}")

    def gps_handler(
        self, max_attempts=50, min_fixes=3, hdop_threshold=2.0, max_runtime=2
    ):  # TODO: what should max_runtime be? I had it as 10 historically
        start_time = time.time()
        try:
            session = gps.gps(mode=gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE)
            all_fixes = []

            while time.time() - start_time < max_runtime and len(all_fixes) < min_fixes:
                if select.select([session.sock], [], [], 1)[0]:
                    try:
                        report = session.next()
                    except StopIteration:
                        logger.warning("GPSD stream ended unexpectedly.")
                        break
                    except Exception as e:
                        logger.error(f"Error reading GPS data: {e}")
                        continue

                    if report["class"] == "TPV":
                        if getattr(report, "mode", 0) >= 2:
                            lat = getattr(report, "lat", None)
                            lon = getattr(report, "lon", None)
                            eph = getattr(report, "eph", None)

                            if lat is not None and lon is not None:
                                logger.debug(f"Got GPS fix: lat={lat}, lon={lon}, HDOP={eph}")
                                all_fixes.append((lat, lon))
                            else:
                                logger.debug("GPS fix missing lat/lon fields")
                else:
                    logger.debug("No GPS data available yet")

            if all_fixes:
                avg_lat = sum(f[0] for f in all_fixes) / len(all_fixes)
                avg_lon = sum(f[1] for f in all_fixes) / len(all_fixes)
                logger.info(f"GPS: Averaged Latitude: {avg_lat}, Longitude: {avg_lon}")
                return avg_lat, avg_lon
            else:
                logger.debug("Could not obtain any GPS fix.")

        except Exception as e:
            logger.error(f"GPSD error: {e}")

        return "", ""

    ### UTW MODULE METHODS ###

    def utw_task_queue_handler(self):
        while not self.EXIT:
            try:
                task = self.utw_task_queue.get(timeout=0.1)  # Get a task
                task()  # Execute the function
                self.utw_task_queue.task_done()
            except queue.Empty:
                pass

    # Sends a message from the test back to the base station
    def ota_send_tout(self, message):
        self.ota_outgoing_queue.put((self.ota_base_station_id, f"TOUT:{message}"))
        logger.info(f"Sent TOUT to {self.ota_base_station_id} with console output: {message}")
        self.flag_ota_tout.clear()

    """
    Checks to see if the ota system a valid TEST message from the base station
    It is important that we check this before running that actual test subprocess
    to prevent needless errors.

    self.ota_test_params format: <start_time>;<test_info>
    parameters are separated by spaces
    """

    def test_has_valid_params(self) -> bool:
        params_parts: list[str] = self.ota_test_params.split(";", maxsplit=1)

        if len(params_parts) < 2:
            logger.warning(f"Invalid parameters used to initalize test: {params_parts}")
            ## TODO: Do I need to do something with a flag here?
            return False

        self.test_start_time = int(params_parts[0])
        test_info = params_parts[1]

        if not self.utw.setup_test(test_info):
            logger.warning(f"Failed to set up test with info: {test_info}")
            return False

        logger.info(f"Test prepared: Start time of: {self.test_start_time}; for: {test_info}")

        return True


    """
    Once a utw test is ready to start, we create the subprocess and pipe all of the stdout
    content into the test_stdout_queue to be sent out with messages.
    """
    def start_utw_test(self):
        self.flag_test_running = self.utw.run_test()
        return self.flag_test_running

    def read_test_outputs(self):
        t_outputs = self.utw.get_output()

        for output in t_outputs:
            self.ota_send_tout(output)

            if "erminate" in output:
                # Test has terminated
                self.flag_test_running = False
                self.test_state = Test_State.IDLE

    """
    Checks on the test subprocess to collect outputs and see if it is still running.
    subprocess returns None if still running
    subprocess return 0 if it ended successfully
    subprocess returns -2 if it was ended by a signal.SIGINT (better none as a CANC)
    subprocess returns something else otherwise, meaning it ended unexpectedly
    """
    def check_on_test(self):
        # Start by collecting outputs
        self.read_test_outputs()
        
        
        
        status, return_code = self.utw.get_test_status()

        if not status: # Test is not set up
            logger.error("check_on_test: Test is not set up, cannot check on test process")

        if return_code is None:
            return  # The test is still running
        
        # Test ended; interpret return code
        # Test ended successfully
        elif return_code == 0:
            self.test_state = Test_State.PASS
            self.ota_outgoing_queue.put((self.ota_base_station_id, "DONE"))

        # Test was terminated with a CANC. When a subprocess is terminated with a signal.SIGINT,
        # it returns -2
        elif return_code == -2:
            self.test_state = Test_State.PASS
            self.ota_outgoing_queue.put((self.ota_base_station_id, "CANCD"))

        # If anything else, the test ended unexpectedly and we will mark it as a FAIL    
        else:
            self.test_state = Test_State.FAIL
            self.ota_outgoing_queue.put((self.ota_base_station_id, "FAIL"))


    def clean_up_test(self):
        self.utw_task_queue.put(self.utw.reset_test)
        
        self.test_state = Test_State.CLEANUP


    def check_for_cancel_from_base(self):
        """
        This function checks for incoming messages while in the system is the UTW_TEST state.
        The messages received in this state should only be CANC. 
        """
        try:
            new_messages = self.ota.get_new_messages()
        except Exception as e:
            logger.error(f"Failed to get OTA messages: {e}")
            return

        for message in new_messages:
            parts = message.split(",")

            if parts[1].startswith("CANC"):
                logger.info(f"Received a CANC message")
                self.cancel_test = True
            elif parts[1].startswith("RELOAD"):
                logger.info(f"Received a RELOAD message")
                self.reload_service()
            elif parts[1].startswith("RESTART"):
                logger.info(f"Received a RESTART message")
                self.restart_system()
            else:
                logger.error(f"Received unexpected message while in UTW_TEST state: {message}")


    def check_for_test_interrupt(self):
        """
        Check periodically to see if the test if CANCELLED, if the service needs to RELOAD,
        or if the system needs to RESTART
        """
        if self.flag_ota_cancel_test.is_set():
            logger.info("check_for_cancel: Test CANCELLED by base station")
            self.flag_ota_cancel_test.clear()
            self.utw.cancel_test()

        elif self.flag_ota_reload.is_set():
            logger.info("check_for_cancel: Received a RELOAD message")
            self.flag_ota_reload.clear()
            self.reload_service()

        elif self.flag_ota_restart.is_set():
            logger.info("check_for_cancel: Received a RESTART message")
            self.flag_ota_restart.clear()
            self.restart_system()

    def reload_service(self):
        """
        Reloads the service without restarting the system entirely
        """
        try:
            os.system("sudo systemctl restart bue.service")
        except Exception as e:
            print(f"Error restarting bue.service': {e}")

    def restart_system(self):
        """
        Restarts the entire system using sudo reboot
        """
        try:
            logger.info("Initiating system restart...")
            os.system("sudo reboot")
        except Exception as e:
            logger.error(f"Error restarting system: {e}")

    
    ### STATE MACHINE METHODS ###

    def state_change_logger(self):
        if self.cur_st != self.prv_st:
            logger.info(f"state_change_logger: State changed from {self.prv_st.name} to {self.cur_st.name}")
            self.prv_st = self.cur_st

    def bue_tick(self, loop_dur=0.01):
        # Interconnect flags

        # Internal counters

        # How often to try to connect in CONNECT_OTA_REQ_INTERVAL seconds
        CONNECT_OTA_REQ_INTERVAL = 1
        counter_connect_ota = 0
        interval_connect_ota = round(CONNECT_OTA_REQ_INTERVAL / loop_dur)

        # How often to ping (once in idle state) PING_OTA_INTERVAL seconds
        PING_OTA_INTERVAL = 10
        counter_ping = 0
        interval_ping = round(PING_OTA_INTERVAL / loop_dur)

        while not self.EXIT:
            if not self.tick_enabled:
                time.sleep(loop_dur)  # avoid busy spinning when disabled
                continue

            loop_start = time.time()

            ### TRANSITIONS STATE MACHINE ###

            if self.cur_st == Bue_State.INIT:
                # Setup should all be complete, immediately move to the CONNECT_OTA state
                counter_connect_ota = 0

                # Reset the flags that are used in the connect state
                self.flag_ota_connected.clear()

                self.nxt_st = Bue_State.CONNECT_OTA
            #
            elif self.cur_st == Bue_State.CONNECT_OTA:
                # Wait until the OTA device is connected to the OTA network
                if self.status_ota_connected:

                    # Reset the flags used in idle
                    self.flag_ota_pingr.clear()
                    self.flag_ota_start_testing.clear()

                    counter_ping = 0
                    self.nxt_st = Bue_State.IDLE
                else:
                    self.nxt_st = Bue_State.CONNECT_OTA

            # If the bUE ever loses connected to the base station, return to CONNECTED_OTA state
            #
            # If the bUE gets a TEST from the base station and that TEST contained valid parameters,
            # enter the WAIT_FOR_START state
            elif self.cur_st == Bue_State.IDLE:
                # If we lost connection we will go back to the connecting state
                if not self.status_ota_connected:
                    counter_connect_ota = 0

                    # Reset the flags that are used in the connect state
                    self.flag_ota_connected.clear()

                    self.nxt_st = Bue_State.CONNECT_OTA
                # If we receivied a TEST message from the base station, we switch to UTW_TEST state
                elif self.flag_ota_start_testing.is_set():
                    # Reset the flags used in testing
                    self.flag_ota_start_testing.clear()
                    self.flag_ota_cancel_test.clear()
                    self.flag_ota_reload.clear()
                    self.flag_ota_restart.clear()
                    self.test_state = Test_State.RUNNING

                    # TODO reset other falgs?
                    if self.test_has_valid_params():
                        self.nxt_st = Bue_State.WAIT_FOR_START
                    else:
                        self.nxt_st = Bue_State.IDLE
                        # TODO: SEND A BAD PARAMETERS MESSAGE?
            #
            # In the WAIT_FOR START state, the bUE is waiting for a certain time to arrive. Once it has, it
            # will enter into the UTW_TEST state
            #
            # If while waiting the bUE receives a CANC message, it will stop waiting and go straight to the
            # TEST_CLEANUP state so flags can be reset approriately
            #
            elif self.cur_st == Bue_State.WAIT_FOR_START:
                current_time: int = int(time.time())
                if self.flag_ota_cancel_test.is_set():
                    self.ota_outgoing_queue.put((self.ota_base_station_id, "CANCD"))
                    self.utw_task_queue.put(self.utw.cancel_test)
                    self.utw_task_queue.put(self.utw.reset_test)
                    self.nxt_st = Bue_State.TEST_CLEANUP

                elif current_time < self.test_start_time:
                    self.nxt_st = Bue_State.WAIT_FOR_START

                elif current_time >= self.test_start_time:
                    self.nxt_st = Bue_State.UTW_TEST
                    self.start_utw_test()
                else:
                    logger.warning("Got to last transition in WAIT_FOR_START. This should not be possible")
            #
            # If the bUE ever receives a CANC while testing, it should response with a CANCD
            # message and enter the TEST_CLEANUP state
            #
            # If the test subprocess is no longer running, the bUE will report how the
            # test subprocessed ended and enter the TEST_CLEANUP state
            #
            # Otherwise, stay in the UTW_TEST state
            #
            elif self.cur_st == Bue_State.UTW_TEST:
                if self.test_state == Test_State.PASS:
                    self.utw_task_queue.put(self.utw.reset_test)
                    self.nxt_st = Bue_State.TEST_CLEANUP

                elif self.test_state == Test_State.FAIL:
                    self.utw_task_queue.put(self.utw.reset_test)
                    self.nxt_st = Bue_State.TEST_CLEANUP

                elif self.test_state == Test_State.RUNNING:
                    self.nxt_st = Bue_State.UTW_TEST

                else:
                    logger.error(f"bue_tick: bUE in unexpected test_state while in UTW_TEST: {self.test_state}")
            #
            # Once all the stdout queue messages have been sent, return to the IDLE state
            #
            elif self.cur_st == Bue_State.TEST_CLEANUP:
                if not self.flag_test_running:
                    self.nxt_st = Bue_State.IDLE
                else:
                    self.nxt_st = Bue_State.TEST_CLEANUP

            else:
                logger.error(f"tick: Invalid state transition {self.cur_st.name}")
                sys.exit(1)

            ### ACTION STATE MACHINE ###

            if self.cur_st == Bue_State.INIT:
                pass
            #
            elif self.cur_st == Bue_State.CONNECT_OTA:
                counter_connect_ota += 1

                # Send out a REQ every CONNECT_OTA_REQ_INTERVAL seconds
                if counter_connect_ota % interval_connect_ota == 0:
                    self.ota_task_queue.put(self.ota_connect_req)
            #
            elif self.cur_st == Bue_State.IDLE:
                counter_ping += 1

                # Send a PING every PING_OTA_INTERVAL seconds
                if counter_ping % interval_ping == 0:
                    self.ota_task_queue.put(self.ota_ping)
                    counter_ping = 0

            #
            elif self.cur_st == Bue_State.WAIT_FOR_START:
                counter_ping += 1

                # Send a PING every PING_OTA_INTERVAL seconds
                if counter_ping % interval_ping == 0:
                    self.ota_task_queue.put(self.ota_ping)
                    counter_ping = 0
            #
            elif self.cur_st == Bue_State.UTW_TEST:
                counter_ping += 1

                # Send a PING every PING_OTA_INTERVAL seconds
                if counter_ping % interval_ping == 0:
                    self.ota_task_queue.put(self.ota_ping)
                    counter_ping = 0

                self.check_on_test()
                self.check_for_test_interrupt()

                # I get the messages during check_on_test now
                # if not self.flag_ota_tout.is_set() and not self.test_stdout_queue.empty():
                #     self.flag_ota_tout.set()
                #     self.ota_task_queue.put(self.ota_send_tout)
            #
            elif self.cur_st == Bue_State.TEST_CLEANUP:
                counter_ping += 1

                # Send a PING every PING_OTA_INTERVAL seconds
                if counter_ping % interval_ping == 0:
                    self.ota_task_queue.put(self.ota_ping)
                    counter_ping = 0

                self.read_test_outputs()
                
                
            #
            else:
                logger.error(f"tick: Invalid state action {self.cur_st.name}")
                sys.exit(1)

            # Update the current state
            self.cur_st = self.nxt_st

            # Log any state change
            self.state_change_logger()

            # End of the tick loop, make sure we start loop_dur seconds after the loop started
            remaining = loop_dur - (time.time() - loop_start)
            if remaining > 0:
                time.sleep(remaining)

    def __del__(self):
        try:
            self.EXIT = True
            self.tick_enabled = False

            if hasattr(self, "st_thread"):
                self.st_thread.join()
            if hasattr(self, "ota_thread"):
                self.ota_thread.join()
            if hasattr(self, "utw_thread"):
                self.utw_thread.join()
            if hasattr(self, "ota_trx_thread"):
                self.ota_trx_thread.join()
            if hasattr(self, "ota"):
                self.ota.__del__()

        except Exception as e:
            logger.warning(f"__del__: Exception during cleanup: {e}")


if __name__ == "__main__":

    # Get the current time
    start_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Set up the logger
    # logger.add(f"bue_logs/bue_log_{start_time}.log", format="{time} {level} {message}", level="INFO")
    # logger.add(format="{time} {level} {message}", level="INFO", sink=sys.stdout)

    # Example usage
    logger.info(f"This marks the start of the bUE service at {start_time}")

    try:
        bue = bUE_Main(yaml_str="bue_config.yaml")

        # Any other setup code can go here
        time.sleep(2)  # Allow some time for threads to initialize

        bue.tick_enabled = True

        while True:
            time.sleep(0.1)

    except KeyboardInterrupt:
        if bue is not None:
            logger.info("Exiting the bUE service")
            bue.EXIT = True
            time.sleep(0.5)
            bue.__del__()
            sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception in main: {e}")
        if bue is not None:
            bue.EXIT = True
            time.sleep(0.5)
            bue.__del__()
        sys.exit(1)
