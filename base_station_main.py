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
from constants import Bue_State

logger.remove()  # Remove default sink

# Main log for everything
logger.add("logs/base_station.log", rotation="10 MB", enqueue=True)
logger.add("logs/last_run.log", mode="w", enqueue=True)


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

        # Fetch the Reyax ID from the OTA module. Same fix as bue_main.py's
        # Reyax-ID fetch: this was a single, unretried attempt with no
        # visibility into failure -- confirmed in the field (2026-08-03)
        # that under heavy simultaneous REQ traffic from many bUEs at once,
        # the module can fail to answer a local AT command at all, leaving
        # self.reyax_id permanently None with nothing logged to explain why
        # (every REQ handled afterward would silently send "CON:None").
        self.reyax_id = None
        REYAX_FETCH_WARN_EVERY_S = 10
        REYAX_FETCH_MAX_WAIT_S = 30
        wait_start = time.time()
        last_warn = 0.0
        while self.reyax_id is None:
            time.sleep(0.2)
            self.reyax_id = self.ota.fetch_id()
            elapsed = time.time() - wait_start
            if self.reyax_id is None and elapsed - last_warn >= REYAX_FETCH_WARN_EVERY_S:
                last_warn = elapsed
                logger.warning(
                    f"__init__: Reyax module has not responded to an ID query "
                    f"in {elapsed:.0f}s -- if this keeps climbing, the module "
                    f"may be overwhelmed by channel traffic or wedged and may "
                    f"need its physical reset button pressed."
                )
            if self.reyax_id is None and elapsed >= REYAX_FETCH_MAX_WAIT_S:
                logger.error(
                    f"__init__: giving up on Reyax ID fetch after {elapsed:.0f}s -- "
                    f"proceeding without one. REQ handling will misbehave until "
                    f"this is set manually (bs.reyax_id = <known id>)."
                )
                break

        logger.info(f"[DEBUG] OTA ID is set to: {self.reyax_id}")

        self.EXIT = False
        self.PING_TIMEOUT_SECONDS = 15  # Number of seconds waiting for a PING to come before its considered missed
        self.PING_MAX_MISSES = 5  # Number of missed PINGs received before connected considered lost

        self.bue_id_to_hostname: dict[int, str] = {}  # Dictionary that pairs rayex ids to bue name. (ex: 20 -> Perry)

        self.connected_bues: list[int] = []  # List to hold rayex ids of each connected bue.
        self.bue_missed_ping_counter: dict[int, int] = {}  # Dictionary to hold how many PINGs have been missed
        self.bue_tout: list[str] = []  # List to hold messages that come with TOUT messages
        self.bue_id_to_state: dict[int, str] = {}  # Dictionary to hold what state each bUE is currently in
        self.bue_id_to_coords: dict[int, (float, float)] = {}  # Dictionary to hold the coords of each bUE
        self.bue_id_to_last_ping_time: dict[int, int] = {}  # Dictionary to hold when a bUE got its last PING
        self.bue_id_to_last_cancd_time: dict[int, float] = {}  # Dictionary to hold when a bUE last confirmed a cancel via CANCD

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

            # Push any new messages from the outgoing queue to the OTA.
            # Same fix as bue_main.py's ota_message_trx: this was
            # unprotected, so one bad send could silently kill this entire
            # thread (all OTA I/O, not just sending) with nothing logged --
            # confirmed as a real risk under heavy channel load, 2026-08-03.
            while not self.ota_outgoing_queue.empty():
                (recipient_id, message) = self.ota_outgoing_queue.get()
                try:
                    self.ota.send_ota_message(recipient_id, message)
                except Exception as e:
                    logger.error(f"ota_message_trx: Failed to send {message!r} to {recipient_id}: {e}")
                finally:
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
                # A bUE can keep sending PING/TOUT/etc. as if still connected
                # after this process restarts (it only notices and re-REQs
                # once it misses enough PINGRs, or if it's mid-test it won't
                # notice until that ends) -- bue_id_to_hostname won't have it
                # yet in that window. Falling back instead of a direct dict
                # index avoids crashing (with a KeyError traceback) on every
                # single message from a bUE we just haven't re-recognized yet.
                hostname = self.bue_id_to_hostname.get(int(src_id), f"unknown-{src_id}")

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
                        logger.info(f"{hostname}: REQ")

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
                        logger.warning(f"{hostname}: PING but not listed as connected (will reconnect once it notices)")

                elif msg_type == "TOUT":
                    self.bue_tout.append(f"{hostname}: {msg_body}")
                    logger.info(f"{hostname}: TOUT")

                elif msg_type == "FAIL":
                    logger.info(f"{hostname}: FAIL")

                elif msg_type == "DONE":
                    logger.info(f"{hostname}: DONE")

                elif msg_type == "CANCD":
                    self.bue_id_to_last_cancd_time[int(src_id)] = time.time()
                    logger.info(f"{hostname}: CANCD (test cancelled)")

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
        self.bue_id_to_state[int(src_id)] = Bue_State(int(state))
        self.bue_id_to_last_ping_time[int(src_id)] = time.time()

        coords: str = ""
        if lat != "" and long != "":
            self.bue_id_to_coords[int(src_id)] = (float(lat), float(long))
            coords = f"@ {lat}, {long}"

        self.ota_outgoing_queue.put((src_id, "PINGR"))
        logger.info(f"{self.bue_id_to_hostname[int(src_id)]}: PING {coords}")

    def cancel_bue_reliable(self, bue_id: int, max_retries: int = 5, retry_interval_s: float = 2.0) -> bool:
        """
        CANC is a single unacknowledged OTA packet, sent once and forgotten.
        Confirmed lost in the field (2026-08-03 tub test): a bUE that never
        receives it just keeps running its test subprocess indefinitely,
        unattended, with no way to recover short of SSHing in manually.
        (bue_main.py also now has a local MAX_TEST_DURATION_S backstop for
        when this fails completely, but that's a 15-minute safety net, not
        a substitute for actually cancelling promptly.)

        Resends CANC, checking after each attempt for confirmation via
        either of two independent signals:
          - CANCD, sent by the bUE immediately upon actually cancelling
            (near-instant -- this is the primary signal).
          - self-reported state (from its periodic PING, tracked in
            bue_id_to_state) leaving WAIT_FOR_START/UTW_TEST.
        The state signal alone was found to produce false negatives here:
        it only updates on the bUE's ~10s PING cycle, which is often slower
        than this function's own retry_interval_s, so a cancel that
        actually succeeded could still read as WAIT_FOR_START/UTW_TEST for
        several seconds after the fact (confirmed directly against device
        logs, 2026-08-03 -- a "NOT CONFIRMED" case where the device had
        already cleanly cancelled a few seconds earlier). CANCD isn't
        gated on that cycle, so checking it first resolves that.

        Stops as soon as either signal confirms, since further CANCs would
        just be wasted airtime once the first one has landed. Blocking --
        call from a background thread, not the GUI thread, so the UI
        doesn't freeze for however long this takes.

        Returns True if the bUE was confirmed to leave a testing state,
        False if it still reports one after max_retries attempts.
        """
        testing_states = (Bue_State.WAIT_FOR_START, Bue_State.UTW_TEST)
        for attempt in range(1, max_retries + 1):
            send_time = time.time()
            self.ota.send_ota_message(bue_id, "CANC")
            logger.info(f"cancel_bue_reliable: sent CANC to {bue_id} (attempt {attempt}/{max_retries})")

            deadline = time.time() + retry_interval_s
            while time.time() < deadline:
                if self.bue_id_to_last_cancd_time.get(bue_id, 0) > send_time:
                    logger.info(f"cancel_bue_reliable: {bue_id} confirmed via CANCD")
                    return True
                if self.bue_id_to_state.get(bue_id) not in testing_states:
                    logger.info(f"cancel_bue_reliable: {bue_id} confirmed via state")
                    return True
                time.sleep(0.2)

        logger.warning(
            f"cancel_bue_reliable: {bue_id} still reports a testing state after "
            f"{max_retries} CANC attempts -- it will self-cancel via its own "
            f"MAX_TEST_DURATION_S backstop if this keeps failing."
        )
        return False

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
