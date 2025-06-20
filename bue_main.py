"""
bue_main.py
Bryson Schiel

This is the main file for the bUE service. It handles the state machine and the OTA and UTW modules.
Documentation can be found in the NET Lab Notion at the page "bUE Python Code Guide".
"""

# Standard library imports
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
from serial import Serial, SerialException
from pynmeagps import NMEAReader
import gps

logger.add("logs/bue.log", rotation="10 MB") # Example: Add a file sink for all logs

# Internal imports
from ota import Ota

# This variable manages how many PINGRs should be missed until the bUE disconnects from the base station
# and goes back to its CONNECT_OTA state. 
# TIMEOUT * 2 rotations must pass, then the bUE will disconnect.
# The length of the rotations is defined by IDLE_PING_OTA_INTERVAL in bue_tick()
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
        while True:
            try:
                self.ota = Ota(self.yaml_data['OTA_PORT'], self.yaml_data['OTA_BAUDRATE'], self.yaml_data['OTA_ID'])
                break
            except Exception as e:
                logger.error(f"Failed to initialize OTA module: {e}")
                time.sleep(2)


        # Build the state machine - states
        self.cur_st, self.nxt_st = State.INIT, State.INIT
        logger.info(f"__init__: Initializing current state to {self.cur_st.name}")
        self.prv_st = self.cur_st

        # Build the state machine - flags
        self.EXIT = False
        self.ota_connected = False
        self.ota_timeout = TIMEOUT

        # Flag to be set if a test is sent
        self.is_testing = False
        self.cancel_test = False

        # Buffer to hold outputs from the UTW script (like helloworld)
        self.test_output_buffer = []
        self.test_output_lock = threading.RLock()

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


    # Send out REQs until a base station is found
    def ota_connect_req(self):
        if self.ota_connected:
            logger.warning(f"connect_ota_req: OTA device is already connected to base station {self.ota_base_station_id}")
            return
        
        # See if there are any new messages from the OTA device
        #  Note: using get_new_messages will destroy any other incoming messages,
        #   but these are unwanted until the device is connected
        try:
            new_messages = self.ota.get_new_messages()
        except Exception as e:
            logger.error(f"Failed to get OTA messages: {e}")
            return

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
        self.ota.send_ota_message(self.ota_base_station_id, "REQ") # bUE sends a message back to the base station asking to 
                                                                   # be connected as well
        print("Sending a REQ")
    
    # This function looks for all messages it might receive while in the IDLE state.
    # It keeps track of whether or not it received a PING in a given rotation (timing defined by IDLE_PING_OTA_INTERVAL in bue_tick())
    # If enough PINGRs are missed, it will automatically disconnect and return to the OTA_CONNECT state
    def ota_idle_ping(self):
        if not self.ota_connected:
            logger.warning("ota_idle_ping: OTA device is not connected to base station")
            return
        
        print("Getting GPS Data")
        lat, long = self.gps_handler()
        print("trying to send a ping")
        self.ota.send_ota_message(self.ota_base_station_id, f"PING,{lat},{long}") # test ping for now
        
        # See if there are any new messages from the OTA device
        try:
            new_messages = self.ota.get_new_messages()
        except Exception as e:
            logger.error(f"Failed to get OTA messages: {e}")
            return
        got_pingr = False

        for message in new_messages:
            message = message[5:]  # Remove the "+RCV=" part
            parts = message.split(",")

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

            elif "TEST" in message: # Message should look like 1,34,TEST.<file>.<configuration>.<role>.<starttime>,-1,8
                input = parts[2]

                self.test_handler(input)

            else:
                logger.error(f"Unknown message type: {message}")

        if not got_pingr:
            self.ota_timeout -= 1
            
            if(self.ota_timeout <= 0):
                logger.info(f"We haven't heard from {self.ota_base_station_id} in a while....")
            if(self.ota_timeout <= -TIMEOUT):
                logger.info(f"We have not heard from {self.ota_base_station_id} in too long. Disconnecting...")
                self.ota_connected = False


    # def gps_handler(self, max_attempts=20, max_runtime = 5):
    #     start_time = time.time()
    #     try:
    #         with Serial('/dev/serial/by-id/usb-u-blox_AG_-_www.u-blox.com_u-blox_7_-_GPS_GNSS_Receiver-if00', 38400, timeout=3) as stream:
    #             nmr = NMEAReader(stream)

    #             for _ in range(max_attempts):
    #                 # if time.time() - start_time > max_runtime:
    #                 #     logger.warning("GPS handler timed out.")
    #                 #     break

    #                 try:
    #                     line = stream.readline().decode('ascii', errors='replace').strip()
    #                     print(line)
    #                     if line.startswith('$GPGGA') or line.startswith('$GPRMC'):
    #                         msg = nmr.parse(line)

    #                         if hasattr(msg, "lat") and hasattr(msg, "lon"):
    #                             logger.info(f"GPS: Latitude: {msg.lat}, Longitude: {msg.lon}")
                                
    #                             if(msg.lat != "" and msg.lon != ""):
    #                                 return msg.lat, msg.lon
    #                             else:
    #                                 break
    #                         else:
    #                             logger.debug("NMEA message missing lat/lon")
    #                 except Exception as parse_error:
    #                     logger.debug(f"Parse error: {parse_error}")

    #                 time.sleep(0.1)  # Give GPS time to provide valid data
    #     except SerialException as se:
    #         logger.error(f"GPS SerialException: {se}")
    #     except Exception as e:
    #         logger.error(f"GPS error: {e}")

    #     logger.debug("Could not find coordinates. Are they off?")
    #     return "", ""

    def gps_handler(self, max_attempts=50, min_fixes=3, hdop_threshold=2.0, max_runtime=10):
    start_time = time.time()
    try:
        session = gps.gps(mode=gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE)
        good_fixes = []

        while time.time() - start_time < max_runtime and len(good_fixes) < min_fixes:
            if select.select([session.sock], [], [], 1)[0]:
                try:
                    report = session.next()
                except StopIteration:
                    logger.warning("GPSD stream ended unexpectedly.")
                    break
                except Exception as e:
                    logger.error(f"Error reading GPS data: {e}")
                    continue

                if report['class'] == 'TPV':
                    if getattr(report, 'mode', 0) >= 2:
                        lat = getattr(report, 'lat', None)
                        lon = getattr(report, 'lon', None)
                        eph = getattr(report, 'eph', None)

                        if lat is not None and lon is not None:
                            if eph is not None and eph <= hdop_threshold:
                                logger.debug(f"Accepted GPS fix: lat={lat}, lon={lon}, HDOP={eph}")
                                good_fixes.append((lat, lon))
                            else:
                                logger.debug(f"Rejected fix due to poor HDOP (eph={eph})")
                        else:
                            logger.debug("GPS fix missing lat/lon fields")
            else:
                logger.debug("No GPS data available yet")

        if good_fixes:
            avg_lat = sum(f[0] for f in good_fixes) / len(good_fixes)
            avg_lon = sum(f[1] for f in good_fixes) / len(good_fixes)
            logger.info(f"GPS: Averaged Latitude: {avg_lat}, Longitude: {avg_lon}")
            return avg_lat, avg_lon
        else:
            logger.debug("Could not obtain reliable GPS fix.")

    except Exception as e:
        logger.error(f"GPSD error: {e}")

    return "", ""




    # This function handles operations that happen while a bUE is in the TESTING state
    def test_handler(self, input): # Input Format: TEST-<file>-<start_time>-<parameters>
        if not ";" in input: ## TODO: Perform other checks
            try:
                self.ota.send_ota_message(self.ota_base_station_id, "PREPR")

                parts = input.split("-")
                if len(parts) < 4:
                    raise ValueError(f"Invalid input format: {input}")
                file = parts[1]
                start_time = parts[2]
                parameters = parts[3].split(" ")

                self.is_testing = True
                self.cancel_test = False

                ## TODO: Wait to run the task until given time it reached

                with self.test_output_lock:
                    self.test_output_buffer.clear()

                process = subprocess.Popen(
                    ["python3", f"{file}.py"] + parameters,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.PIPE,  # Needed to send keystrokes
                    bufsize=1,              # Line-buffered
                    universal_newlines=True, # Text mode, also enables line buffering
                    text=True  # decode bytes to str
                )

                logger.info(f"Started test script: {file}.py with parameters {parameters}")

                def reader_thread(pipe, output_queue):
                    for line in iter(pipe.readline, ''):
                        output_queue.put(line)
                    pipe.close()

                stdout_queue = queue.Queue()
                stderr_queue = queue.Queue()

                # Threads that will be looking in the stdout and stderr termainals for messages while 
                # the TEST process runs
                threading.Thread(target=reader_thread, args=(process.stdout, stdout_queue), daemon=True).start()
                threading.Thread(target=reader_thread, args=(process.stderr, stderr_queue), daemon=True).start()

                """
                # Process will go to completion unless unless the system receives a CANC message from the base station.
                # The CANC message is received and processed by the utw thread

                # We also collect all the terminal outputs from the script so we can send them back to the base station
                """
                while process.poll() is None: # poll() returns None if process hasn't terminated
                    # Get all normal terminal outputs
                    try:
                        stdout_line = stdout_queue.get_nowait()
                        clean_line = f"[{file}.py STDOUT] {stdout_line.strip()}"
                        logger.info(clean_line)
                        with self.test_output_lock:
                            if "rx msg:" in clean_line:
                                self.test_output_buffer.append(f"STDOUT: {clean_line}") ## TODO: Is this too long?
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
                        print("TRYING TO CANCEL")
                        print("TRYING TO CANCEL")
                        print("TRYING TO CANCEL")
                        print("TRYING TO CANCEL")
                        print("TRYING TO CANCEL")
                        print("TRYING TO CANCEL")
                        print("TRYING TO CANCEL")
                        print("TRYING TO CANCEL")
                        print("TRYING TO CANCEL")
                        print("TRYING TO CANCEL")
                        print("TRYING TO CANCEL")
                        print("TRYING TO CANCEL")
                        print("TRYING TO CANCEL")
                        print("TRYING TO CANCEL")
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
                    logger.info(f"{file}.py completed successfully.")
                    self.ota.send_ota_message(self.ota_base_station_id, "DONE")
                else:
                    logger.error(f"{file}.py exited with code {exit_code}")

            except Exception as e:
                logger.info(f"TEST could not be run: {e}")
                self.ota.send_ota_message(self.ota_base_station_id, "FAIL")
            finally:
                self.is_testing = False
                self.cancel_test = False

                # Any extra messages that have not already been sent to the base station are sent
                with self.test_output_lock:
                    self.ota_send_upd()

    


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
                    time.sleep(0.4) # Sleep so UART does not get overwhelmed 
                self.test_output_buffer.clear()
                
            else: # If there is no message send it blank
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
            if "CANC" in message:
                logger.info(f"Received a CANC message")
                self.cancel_test = True
            else:
                logger.error(f"Received unexpected message while in UTW_TEST state: {message}")



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
        connect_ota_counter = 0
        connect_ota_req = round(CONNECT_OTA_REQ_INTERVAL / loop_dur)

        # How often to ping (once in idle state) IDLE_PING_OTA_INTERVAL seconds
        IDLE_PING_OTA_INTERVAL = 10
        idle_counter = 0
        idle_ping_ota = round(IDLE_PING_OTA_INTERVAL / loop_dur)

        # How often to send UPDs UTW_UPD_OTA_INTERVAL seconds
        UTW_UPD_OTA_INTERVAL = 10
        uta_counter = 0
        uta_upd_ota = round(UTW_UPD_OTA_INTERVAL / loop_dur)
        
        while not self.EXIT:

            if not self.tick_enabled:
                continue

            loop_start = time.time()

            # TRANSITIONS STATE MACHINE
            if self.cur_st == State.INIT:
                # Setup should all be complete, immediately move to the CONNECT_OTA state
                connect_ota_counter = 0
                self.nxt_st = State.CONNECT_OTA
                
            elif self.cur_st == State.CONNECT_OTA:
                # Wait until the OTA device is connected to the OTA network
                if self.ota_connected:
                    idle_counter = 0
                    self.nxt_st = State.IDLE

            elif self.cur_st ==  State.IDLE:
                # If we lost connected we will go back to the connecting state
                if not self.ota_connected:
                    connect_ota_counter = 0
                    self.nxt_st = State.CONNECT_OTA
                # If we receivied a TEST message from the base station, we switch to UTW_TEST state
                elif self.is_testing:
                    idle_counter = 0
                    self.nxt_st = State.UTW_TEST
                
            elif self.cur_st == State.UTW_TEST:
                # If we lost connection we will go straight to the connecting state
                if not self.ota_connected:
                    connect_ota_counter = 0
                    self.nxt_st = State.CONNECT_OTA
                # Once test is complete/terminated, return to the IDLE state
                elif not self.is_testing:
                    idle_counter = 0
                    self.nxt_st = State.IDLE
                
            else:
                logger.error(f"tick: Invalid state transition {self.cur_st.name}")
                sys.exit(1)

            # ACTION STATE MACHINE
            if self.cur_st ==  State.INIT:
                pass
            
            elif self.cur_st == State.CONNECT_OTA:
                connect_ota_counter += 1

                # Send out a message looking for a base station every CONNECT_OTA_REQ_INTERVAL seconds
                if connect_ota_counter % connect_ota_req == 0:
                    self.ota_task_queue.put(self.ota_connect_req)
                    
            
            elif self.cur_st == State.IDLE:
                idle_counter += 1

                # Second out a message pinging the base station every IDLE_PING_OTA_INTERVAL seconds
                if idle_counter % idle_ping_ota == 0:
                    self.ota_task_queue.put(self.ota_idle_ping)
                    
            
            elif self.cur_st == State.UTW_TEST:
                uta_counter += 1

                # Do necessary tasks while running a test every UTW_UPD_OTA_INTERVAL seconds
                if uta_counter % uta_upd_ota == 0:
                    self.utw_task_queue.put(self.ota_send_upd)
                    self.utw_task_queue.put(self.check_for_cancel)
            
            else:
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
        except Exception as e:
            logger.warning(f"__del__: Exception during cleanup: {e}")




if __name__ == "__main__":
    
    # Get the current time
    start_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    
    # Set up the logger
    # logger.add(f"bue_logs/bue_log_{start_time}.log", format="{time} {level} {message}", level="INFO")
    # logger.add(format="{time} {level} {message}", level="INFO", sink=sys.stdout)

    # Example usage
    logger.info(f"This marks the start of the bUE service at {start_time}")
    
    try:
        bue = bUE_Main(yaml_str="config.yaml")

        # Any other setup code can go here

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

