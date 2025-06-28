import sys
import signal
import time
import os
import subprocess
import threading
from datetime import datetime
from enum import Enum, auto

from loguru import logger
from rich.console import Console
import survey # type:ignore
import keyboard  # type:ignore

from base_station_main import Base_Station_Main
from UI import create_compact_dashboard
from constants import bUEs

class Command(Enum):
    REFRESH = 0
    TEST = auto()
    DISTANCE = auto()
    DISCONNECT = auto()
    CANCEL = auto()
    # LIST = auto()
    EXIT = auto()

console = Console()

timer = 0
keyboard_input_detected = False
is_user_inputting = False

def on_key_press(event):
    """Callback function triggered on any key press."""
    global keyboard_input_detected
    keyboard_input_detected = True

def keystroke_handler():
    global timer, keyboard_input_detected

    # Set up keyboard listener
    keyboard.on_press(on_key_press)

    while True:
        # Check if keyboard input was detected
        if keyboard_input_detected:
            timer = 0
            keyboard_input_detected = False
        
        if not is_user_inputting and timer > 5: # How many seconds before auto refresh
            os.kill(os.getpid(), signal.SIGINT)
            timer = 0
        else:
            timer += 0.5
        
        time.sleep(0.5)


def user_input_handler(base_station):
    """User input handler with OS clear for stable positioning."""
    global is_user_inputting

    COMMANDS_WITH_DESC = [
        ("REFRESH", "Update the dashboard display"),
        ("TEST", "Run a test file on selected bUEs"),
        ("DISTANCE", "Calculate distance between two bUEs"),
        ("DISCONNECT", "Disconnect from selected bUEs"),
        ("CANCEL", "Cancel running tests on selected bUEs"),
        # ("LIST", "Show all currently connected bUEs"),
        ("EXIT", "Exit the base station application")
    ]
    formatted_options = [f"{cmd:<12} - {desc}" for cmd, desc in COMMANDS_WITH_DESC]
    
    FILES = ("lora_td_ru", "lora_tu_rd", "helloworld", "gpstest", "gpstest2")

    while not base_station.EXIT:
        try:
            console.clear()
            console.print(create_compact_dashboard(base_station), end="")
            print()
            is_user_inputting = False

            # Get input with simple prompt
            index = survey.routines.select('Pick a command: ', options = formatted_options)
            is_user_inputting = True

            if(index != (len(COMMANDS_WITH_DESC) - 1) and len(base_station.connected_bues) == 0):
                print("Currently not connected to any bUEs")
                continue
                
            if index == Command.REFRESH.value:
                continue

            elif index == Command.TEST.value:
                connected_bues = tuple(bUEs[str(x)] for x in base_station.connected_bues)

                bues_indexes = []
                bue_test = {}
                bue_params = {}

                while len(bues_indexes) == 0:
                    bues_indexes = survey.routines.basket('What bUEs will be running tests? ', options = connected_bues)
                    if(len(bues_indexes) == 0):
                        print("You must select at least one bUE...")
                
                start_time = survey.routines.datetime('What time do you want to run the test?: ', attrs = ('hour', 'minute', 'second'))

                bues = [base_station.connected_bues[index] for index in bues_indexes]
                for bue in bues:
                    file_index = survey.routines.select(f'What file would you like to run on {bUEs[str(bue)]}? ', options = FILES)
                    file_name = FILES[file_index]
                    bue_test[bue] = file_name
                    parameters = survey.routines.input(f'Enter parameters for {bUEs[str(bue)]}, {file_name} separated by a space: ')
                    bue_params[int(bue)] = parameters

                    logger.debug(bue_params)

                send_test(base_station, bue_test, start_time, bue_params)


            elif index == Command.DISTANCE.value: 
                connected_bues = tuple(bUEs[str(x)] for x in base_station.connected_bues)

                indexes = survey.routines.basket('Select two bUEs: ',
                                                options = connected_bues)
                
                ## TODO: Need to implement the rest of this once I fixed the coordinates 

                bues = []
                for i in indexes:
                    bues.append(base_station.connected_bues[i])

                print(base_station.bue_coordinates)
                print(base_station.get_distance(bues[0], bues[1]))

            elif index == Command.DISCONNECT.value:
                connected_bues = tuple(bUEs[str(x)] for x in base_station.connected_bues)

                indexes = survey.routines.basket('What bUEs do you want to disconnect from? ',
                                                options = connected_bues)
                
                for i in indexes:
                    bue = base_station.connected_bues[i]
                    base_station.connected_bues.remove(bue)
                    if bue in base_station.bue_coordinates.keys():
                        del base_station.bue_coordinates[bue]
                    if bue in base_station.testing_bues:
                        base_station.testing_bues.remove(bue)
                    if bue in base_station.bue_timeout_tracker.keys():
                        del base_station.bue_timeout_tracker[bue]
                print("\n")
            
            elif index == Command.CANCEL.value:
                testing_bues = tuple(bUEs[str(x)] for x in base_station.testing_bues)
                if(len(testing_bues) == 0):
                    print("No bUEs are currently running any tests")

                indexes = survey.routines.basket('What bUE tests do you want to cancel? ',
                                                options = testing_bues)
                
                print("\n")
                for i in indexes:
                    bue = base_station.testing_bues[i]
                    print(f"Ending test for {base_station.testing_bues[i]}")
                    base_station.ota.send_ota_message(bue, "CANC")
                    logger.info(f"Sending CANC to {bue}")
                print("\n")

            # elif index == Command.LIST.value:
            #     print("\n")
            #     connected_bues = " ".join(bUEs[str(bue)] for bue in base_station.connected_bues)
            #     print(f"Currently connected to {connected_bues}\n\n")
            #     logger.info(f"Currently connected to {connected_bues}")
            
            elif index == Command.EXIT.value:
                base_station.EXIT = True
                base_station.__del__()
                # if 'user_input_thread' in locals() and user_input_thread.is_alive():
                #     user_input_thread.join(timeout=2.0)
                sys.exit(0)
            else: # Catch all
                continue

        except KeyboardInterrupt:
            print("\n[Escape] Cancelled input. Returning to command prompt.\n")
            is_user_inputting = False
            continue 

        except Exception as e:
            logger.error(f"[User Input] Error {e}")
            print(e)

def send_test(base_station, bue_test, start_time, bue_params):
    """Send test command to selected bUEs."""
    # Convert datetime to Unix timestamp
    import time as time_module
    from datetime import datetime, date

    if isinstance(start_time, datetime):
        time_part = start_time.time()
    else:
        time_part = start_time
    
    # Combine today's date with the selected time
    today = date.today()
    full_datetime = datetime.combine(today, time_part)
    unix_timestamp = int(full_datetime.timestamp())
    
    for bue in bue_test.keys():
        if not hasattr(base_station, 'testing_bues'):
            base_station.testing_bues = []
        base_station.ota.send_ota_message(bue, f"TEST-{bue_test[int(bue)]}-{unix_timestamp}-{bue_params[bue]}")

def open_new_terminal():
    """Open a new terminal window and run this script in it."""
    # Get the current script path
    script_path = os.path.abspath(__file__)
    
    # Open new terminal with this script
    subprocess.Popen([
        'gnome-terminal', 
        '--', 
        'python3', 
        script_path
    ])
    
    # Exit the current process since we're running in new terminal
    sys.exit(0)

if __name__ == "__main__":
    # if not os.environ.get('DASHBOARD_TERMINAL'):
    #     os.environ['DASHBOARD_TERMINAL'] = '1'
    #     open_new_terminal()
        
    start_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    logger.info(f"This marks the start of the base station service at {start_time}")

    threading.Thread(target=keystroke_handler, daemon=True).start()

    try:
        base_station = Base_Station_Main(yaml_str="config_base.yaml")
        base_station.tick_enabled = True

        user_input_handler(base_station)

        while not base_station.EXIT:
            time.sleep(0.2)

    except KeyboardInterrupt:
        logger.info("Exiting the Base Station service")
        if 'base_station' in locals() and base_station is not None:
            base_station.EXIT = True
            time.sleep(0.5)
            base_station.__del__()
        sys.exit(0)