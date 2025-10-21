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

# For gps
from pynmeagps import NMEAReader  # type:ignore
import gps

logger.add("logs/bue.log", rotation="10 MB")  # Example: Add a file sink for all logs

# Internal imports
from ota import Ota

# This variable manages how many PINGRs should be missed until the bUE disconnects from the base station
# and goes back to its CONNECT_OTA state.
# TIMEOUT rotations must pass, then the bUE will disconnect.
# The length of the rotations is defined by IDLE_PING_OTA_INTERVAL in bue_tick()
TIMEOUT = 6
BROADCAST_OTA_ID = 0

class State(Enum):
    INIT = auto()
    CONNECT_OTA = auto()
    IDLE = auto()
    UTW_TEST = auto()


class bUE_Main:
    def __init__(self, yaml_str = "bue_config.yaml"):
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
        while True:
            try:
                self.ota = Ota(
                    self.yaml_data["OTA_PORT"],
                    self.yaml_data["OTA_BAUDRATE"]
                )
                break
            except Exception as e:
                logger.error(f"Failed to initialize OTA module: {e}")
                time.sleep(2)

        # Fetch the Reyax ID from the OTA module
        time.sleep(0.1)
        self.reyax_id = self.ota.fetch_id()
        logger.info(f"__init__: OTA module initialized with Reyax ID {self.reyax_id}")

        # Fetch the device hostname
        self.hostname = os.uname().nodename

        # Build the state machine - states
        self.cur_st, self.nxt_st = State.INIT, State.INIT
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

        # State machine - statuses
        # These are the main internal signals used by the state machine
        self.status_test_running = False
        self.status_ota_connected = False

        # Network information
        self.ota_base_station_id = None
        self.ota_test_params = None
        
        
        
        # Build the state machine - flags
        self.counter_ota_timeout = 0
        self.MAX_ota_timeout = TIMEOUT
        # TODO - add functionality for timeout when also sending a test update

        # Flag to be set if a test is sent
        self.start_testing = False
        self.cancel_test = False
        # TODO - delete/modify these once test functionality gets added

        # Buffer to hold outputs from the UTW script (like helloworld)
        self.test_output_buffer = []
        self.test_output_lock = threading.RLock()
        # TODO - modify these once test functionality gets added

        

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
                    msg_type, msg_body = msg.split(":", 1)
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
            self.flag_ota_connected.clear() = False
            logger.info(f"ota_connect_req: OTA device is connected to network with base station {self.ota_base_station_id}")

            # Send the ACK
            self.ota_outgoing_queue.put((self.ota_base_station_id, "ACK"))
            return
        
        # If flag not set, send another REQ message
        self.ota_outgoing_queue.put((BROADCAST_OTA_ID, f"REQ:{self.hostname},{self.reyax_id}"))
            
    
    def ota_idle_ping(self):
        if not self.status_ota_connected:
            logger.warning("ota_idle_ping: OTA device is not connected to base station")
            return

        lat, long = self.gps_handler()

        self.ota_outgoing_queue.put((self.ota_base_station_id, f"PING,{lat},{long}"))  # test ping for now
        logger.info(f"Sent a PING with position lat: {lat} lon: {long}")

        # Check to see if we are getting ping responses
        if self.flag_ota_pingr.is_set():
            self.counter_ota_timeout = 0
            self.flag_ota_pingr.clear()
        else:
            self.counter_ota_timeout += 1
            if self.counter_ota_timeout == self.MAX_ota_timeout / 2:
                logger.info(f"We haven't heard from {self.ota_base_station_id} in a while....")
            elif self.counter_ota_timeout >= self.MAX_ota_timeout:
                logger.info(f"We have not heard from {self.ota_base_station_id} in too long. Disconnecting...")
                self.status_ota_connected = False


    def ota_send_update(self):
        lat, long = self.gps_handler()
        logger.info(f"Sent UPD to {self.ota_base_station_id}")

        with self.test_output_lock:
            if self.test_output_buffer:
                for line in self.test_output_buffer:
                    self.ota_outgoing_queue.put((self.ota_base_station_id, f"UPD:,{lat},{long},{line}"))
                    logger.info(f"Sent UPD to {self.ota_base_station_id} with console output: {line}")
                    time.sleep(0.4)  # Sleep so UART does not get overwhelmed
                self.test_output_buffer.clear()

            else:  # If there is no message send it blank
                self.ota_outgoing_queue.put((self.ota_base_station_id, f"UPD:,{lat},{long},"))
                logger.info(f"Sent UPD to {self.ota_base_station_id} with no console output")

    def gps_handler(self, max_attempts=50, min_fixes=3, hdop_threshold=2.0, max_runtime=10):
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

    # This function handles operations that happen while a bUE is in the TESTING state
    def test_handler(self, input):  # Input Format: TEST,<file>,<wait_time>,<parameters>
        if not ";" in input:  ## TODO: Perform other checks
            try:
                self.ota.send_ota_message(self.ota_base_station_id, "PREPR")

                parts = input.split(",", maxsplit=3)
                print(parts)
                if len(parts) < 4:
                    raise ValueError(f"Invalid input format: {input}")
                file = parts[1]
                start_time = int(parts[2])
                parameters = parts[3].split(" ")

                self.is_testing = True
                self.cancel_test = False
                self.test_output_buffer = []

                current_time = int(time.time())
                if start_time > current_time:
                    wait_duration = start_time - current_time
                    logger.info(f"Waiting {wait_duration} seconds until start time {start_time}")

                    # Wait in small increments to allow for cancellation
                    while int(time.time()) < start_time and not self.cancel_test:
                        time.sleep(0.001)

                    if self.cancel_test:
                        logger.info("Test cancelled during wait period")
                        self.ota.send_ota_message(self.ota_base_station_id, "CANCD")
                        return

                logger.info(f"Starting test at scheduled time: {start_time}")

                with self.test_output_lock:
                    self.test_output_buffer.clear()

                print(["python3", f"{file}.py"] + parameters)

                if parameters == [""]:
                    parameters = None

                if parameters:
                    process = subprocess.Popen(
                        ["python3", f"{file}.py"] + parameters,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        stdin=subprocess.PIPE,  # Needed to send keystrokes
                        bufsize=1,  # Line-buffered
                        universal_newlines=True,  # Text mode, also enables line buffering
                        text=True,  # decode bytes to str
                        encoding="utf-8",
                        errors="replace",
                    )
                else:
                    process = subprocess.Popen(
                        ["python3", f"{file}.py"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        stdin=subprocess.PIPE,  # Needed to send keystrokes
                        bufsize=1,  # Line-buffered
                        universal_newlines=True,  # Text mode, also enables line buffering
                        text=True,  # decode bytes to str
                        encoding="utf-8",
                        errors="replace",
                    )

                logger.info(f"Started test script: {file}.py with parameters {parameters}")

                def reader_thread(pipe, output_queue):
                    for line in iter(pipe.readline, ""):
                        output_queue.put(line)
                    pipe.close()

                stdout_queue = queue.Queue()
                stderr_queue = queue.Queue()

                # Threads that will be looking in the stdout and stderr termainals for messages while
                # the TEST process runs
                threading.Thread(
                    target=reader_thread,
                    args=(process.stdout, stdout_queue),
                    daemon=True,
                ).start()
                threading.Thread(
                    target=reader_thread,
                    args=(process.stderr, stderr_queue),
                    daemon=True,
                ).start()

                """
                # Process will go to completion unless unless the system receives a CANC message from the base station.
                # The CANC message is received and processed by the utw thread

                # We also collect all the terminal outputs from the script so we can send them back to the base station
                """
                while process.poll() is None:  # poll() returns None if process hasn't terminated
                    # Get all normal terminal outputs
                    try:
                        stdout_line = stdout_queue.get_nowait()
                        clean_line = f"[{file}.py STDOUT] {stdout_line.strip()}"
                        logger.info(clean_line)
                        with self.test_output_lock:
                            if " rx_" in clean_line:
                                self.test_output_buffer.append(f"STDOUT: {clean_line}")
                            # elif "CRC invalid" in clean_line:
                            #     self.test_output_buffer.append(f"STDOUT: {clean_line}")
                    except queue.Empty:
                        pass

                    try:
                        stderr_line = stderr_queue.get_nowait()
                        clean_line = f"[{file}.py STDERR] {stderr_line.strip()}"
                        logger.error(clean_line)
                        with self.test_output_lock:
                            self.test_output_buffer.append(f"STDERR: {clean_line}")
                    except queue.Empty:
                        pass

                    if self.cancel_test:
                        print("TRYING TO CANCEL")
                        print("TRYING TO CANCEL")
                        print("TRYING TO CANCEL")
                        logger.info(f"Sending termination to: {file}.py")
                        try:
                            process.send_signal(signal.SIGINT)
                        except Exception as e:
                            logger.error(f"Failed to terminate: {e}")
                        break
                    time.sleep(0.1)

                """
                Leave this code in! If we want all the output messages from the bUE uncomment it. Otherwise,
                we will only get the output messages before it ends/receives a CANC
                """
                # while not stdout_queue.empty():
                #     line = stdout_queue.get()
                #     clean_line = f"[{file}.py STDOUT] {line.strip()}"
                #     logger.info(clean_line)
                #     with self.test_output_lock:
                #         if "rx msg:" in clean_line:
                #             self.test_output_buffer.append(f"STDOUT: {clean_line}")

                while not stderr_queue.empty():
                    line = stderr_queue.get()
                    clean_line = f"[{file}.py STDERR] {line.strip()}"
                    logger.error(clean_line)
                    with self.test_output_lock:
                        self.test_output_buffer.append(f"STDERR: {clean_line}")

                try:
                    exit_code = process.wait()
                except Exception as e:
                    logger.error(f"Error waiting for subprocess {file}.py: {e}")
                    exit_code = -1

                # If a test is canceled, a CANCD message is sent in responses letting the base station know we have successfully termianted the test
                if self.cancel_test:
                    self.ota.send_ota_message(self.ota_base_station_id, "CANCD")
                elif exit_code == 0:
                    # Any extra messages that have not already been sent to the base station are sent
                    with self.test_output_lock:
                        self.ota_send_upd()

                    logger.info(f"{file}.py completed successfully.")
                    self.ota.send_ota_message(self.ota_base_station_id, "DONE")
                else:
                    logger.error(f"{file}.py exited with code {exit_code}")
                    self.ota.send_ota_message(self.ota_base_station_id, "FAIL")

            except Exception as e:
                logger.info(f"TEST could not be run: {e}")
                self.ota.send_ota_message(self.ota_base_station_id, "FAIL")
            finally:
                self.is_testing = False
                self.cancel_test = False

    ### UTW MODULE METHODS ###

    def utw_task_queue_handler(self):
        while not self.EXIT:
            try:
                task = self.utw_task_queue.get(timeout=0.1)  # Get a task
                task()  # Execute the function
                self.utw_task_queue.task_done()
            except queue.Empty:
                pass

    # Instead of PINGs, bUEs send UPDs while in UTW_TEST state so the base still knows there is a connection
    def ota_send_upd(self):
        lat, long = self.gps_handler()
        # self.ota.send_ota_message(self.ota_base_station_id, f"UPD:{lat},{long}")
        logger.info(f"Sent UPD to {self.ota_base_station_id}")

        with self.test_output_lock:
            if self.test_output_buffer:
                for line in self.test_output_buffer:
                    self.ota.send_ota_message(self.ota_base_station_id, f"UPD:,{lat},{long},{line}")
                    logger.info(f"Sent UPD to {self.ota_base_station_id} with console output: {line}")
                    time.sleep(0.4)  # Sleep so UART does not get overwhelmed
                self.test_output_buffer.clear()

            else:  # If there is no message send it blank
                self.ota.send_ota_message(self.ota_base_station_id, f"UPD:,{lat},{long},")
                logger.info(f"Sent UPD to {self.ota_base_station_id} with no console output")

    """
    # This function checks for incoming messages while in the system is the UTW_TEST state.
    # The messages received in this state should only be CANC. 
    """

    def check_for_cancel(self):
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

    """
    Restarts the service entirely
    """

    def check_for_test_interrupt(self):
        """
        Check periodically to see if the test if CANCELLED, if the service needs to RELOAD, 
        or if the system needs to RESTART
        """
        if self.flag_ota_cancel_test.is_set():
            logger.info("check_for_cancel: Test CANCELLED by base station")
            self.flag_ota_cancel_test.clear()
            self.status_test_running = False

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
            subprocess.call(["sudo", "systemctl", "restart", "bue.service"])
        except Exception as e:
            print(f"Error restarting bue.service': {e}")

    
    def restart_system(self):
        """
        Restarts the entire system using sudo reboot
        """
        try:
            logger.info("Initiating system restart...")
            subprocess.call(["sudo", "reboot"])
        except Exception as e:
            logger.error(f"Error restarting system: {e}")

    
    
    '''def synchronize_time(self, base_timestamp):
        """
        Synchronize bUE time with base station time.

        Args:
            base_timestamp: Unix timestamp from base station
        """
        try:
            import subprocess
            import os

            # Calculate the time difference
            local_time = int(time.time())
            time_diff = base_timestamp - local_time

            logger.info(f"Time sync: Base station time: {base_timestamp}, Local time: {local_time}, Diff: {time_diff}s")

            # Only sync if difference is significant (> 1 second)
            if abs(time_diff) > 1:
                # Use date command to set system time (requires sudo privileges)
                date_str = datetime.fromtimestamp(base_timestamp).strftime("%Y-%m-%d %H:%M:%S")
                result = subprocess.run(["sudo", "date", "-s", date_str], capture_output=True, text=True)

                if result.returncode == 0:
                    logger.info(f"Successfully synchronized time to: {date_str}")
                else:
                    logger.error(f"Failed to set system time: {result.stderr}")
            else:
                logger.info("Time difference is minimal, no sync needed")

        except Exception as e:
            logger.error(f"Error during time synchronization: {e}")
    '''

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

        # How often to ping (once in idle state) IDLE_PING_OTA_INTERVAL seconds
        IDLE_PING_OTA_INTERVAL = 10
        counter_idle_ping = 0
        interval_idle_ping = round(IDLE_PING_OTA_INTERVAL / loop_dur)

        # How often to send UPDs UTW_UPD_OTA_INTERVAL seconds
        UTW_UPD_OTA_INTERVAL = 10
        counter_uta_update = 0
        interval_uta_update = round(UTW_UPD_OTA_INTERVAL / loop_dur)

        while not self.EXIT:
            if not self.tick_enabled:
                time.sleep(loop_dur)   # avoid busy spinning when disabled
                continue

            loop_start = time.time()

            # TRANSITIONS STATE MACHINE
            if self.cur_st == State.INIT:
                # Setup should all be complete, immediately move to the CONNECT_OTA state
                counter_connect_ota = 0

                # Reset the flags that are used in the connect state
                self.flag_ota_connected.clear()

                self.nxt_st = State.CONNECT_OTA
            #
            elif self.cur_st == State.CONNECT_OTA:
                # Wait until the OTA device is connected to the OTA network
                if self.status_ota_connected:
                    counter_idle_ping = 0

                    # Reset the flags used in idle
                    self.flag_ota_pingr.clear()
                    self.flag_ota_start_testing.clear()

                    self.nxt_st = State.IDLE
            #
            elif self.cur_st == State.IDLE:
                # If we lost connection we will go back to the connecting state
                if not self.status_ota_connected:
                    counter_connect_ota = 0

                    # Reset the flags that are used in the connect state
                    self.flag_ota_connected.clear()

                    self.nxt_st = State.CONNECT_OTA
                # If we receivied a TEST message from the base station, we switch to UTW_TEST state
                elif self.is_testing:
                    counter_idle_ping = 0

                    # Reset the flags used in testing
                    self.flag_ota_cancel_test.clear()
                    self.flag_ota_reload.clear()
                    self.flag_ota_restart.clear()
                    
                    self.nxt_st = State.UTW_TEST
            #
            elif self.cur_st == State.UTW_TEST:
                # If we lost connection we will go straight to the connecting state
                if not self.status_ota_connected:
                    counter_connect_ota = 0

                    # Reset the flags that are used in the connect state
                    self.flag_ota_connected.clear()

                    self.nxt_st = State.CONNECT_OTA
                    # TODO: end the test in this instance
                # Once test is complete/terminated, return to the IDLE state
                elif not self.is_testing:
                    counter_idle_ping = 0
                    self.nxt_st = State.IDLE
            #
            else:
                logger.error(f"tick: Invalid state transition {self.cur_st.name}")
                sys.exit(1)

            
            ## ACTION STATE MACHINE
            if self.cur_st == State.INIT:
                pass
            #
            elif self.cur_st == State.CONNECT_OTA:
                counter_connect_ota += 1

                # Send out a message looking for a base station every CONNECT_OTA_REQ_INTERVAL seconds
                if counter_connect_ota % interval_connect_ota == 0:
                    self.ota_task_queue.put(self.ota_connect_req)
            #
            elif self.cur_st == State.IDLE:
                counter_idle_ping += 1

                # Second out a message pinging the base station every IDLE_PING_OTA_INTERVAL seconds
                if counter_idle_ping % interval_idle_ping == 0:
                    self.ota_task_queue.put(self.ota_idle_ping)
            #
            elif self.cur_st == State.UTW_TEST:
                counter_uta_update += 1

                # Do necessary tasks while running a test every UTW_UPD_OTA_INTERVAL seconds
                if counter_uta_update % interval_uta_update == 0:
                    self.ota_task_queue.put(self.ota_send_update)
                    self.ota_task_queue.put(self.check_for_test_interrupt)
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
        time.sleep(2) # Allow some time for threads to initialize

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