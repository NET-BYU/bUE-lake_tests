import sys
import time
import os
import subprocess
from datetime import datetime
from loguru import logger


from rich.table import Table
from rich.console import Group, Console
import survey # type:ignore
from rich.panel import Panel
from enum import Enum, auto

from base_station_main import Base_Station_Main

class Command(Enum):
    REFRESH = 0
    TEST = auto()
    DISTANCE = auto()
    DISCONNECT = auto()
    CANCEL = auto()
    LIST = auto()
    EXIT = auto()

console = Console()

def generate_table(base_station) -> Table:
    """Make a styled table of connected bUEs."""
    table = Table(title="📡 Connected bUEs", show_header=True, header_style="bold cyan")
    table.add_column("bUE ID", style="green", no_wrap=True, justify="center")
    table.add_column("Status", style="yellow", justify="center")

    for bue in base_station.connected_bues:
        status = "🧪 Testing" if bue in getattr(base_station, 'testing_bues', []) else "💤 Idle"
        table.add_row(str(bue), status)
    
    if not base_station.connected_bues:
        table.add_row("[dim]No bUEs connected[/dim]", "[dim]N/A[/dim]")
    
    return table

def bue_coordinates_table(base_station) -> Table:
    """Make a styled coordinates table."""
    table = Table(title="🗺️  bUE Coordinates", show_header=True, header_style="bold blue")
    table.add_column("bUE ID", style="cyan", justify="center")
    table.add_column("Coordinates", style="yellow", justify="left")

    for bue in base_station.connected_bues:
        if bue in base_station.bue_coordinates:
            coords = base_station.bue_coordinates[bue]
            table.add_row(str(bue), str(coords))
    
    if not base_station.bue_coordinates:
        table.add_row("[dim]No coordinates available[/dim]", "[dim]N/A[/dim]")
    
    return table

def create_compact_dashboard(base_station):
    """Create a compact dashboard without Layout."""
    # Header
    current_time = datetime.now().strftime('%H:%M:%S')
    connected_count = len(base_station.connected_bues)
    testing_count = len(getattr(base_station, 'testing_bues', []))
    
    header_text = f"🏢 Base Station Dashboard - {current_time} | Connected: {connected_count} | Testing: {testing_count}"
    header = Panel(header_text, style="bold white on blue", padding=(0,1))
    
    # Create tables side by side using Group
    connected_table = generate_table(base_station)
    coordinates_table = bue_coordinates_table(base_station)
    
    # Use Group to combine everything compactly
    from rich.columns import Columns
    tables = Columns([connected_table, coordinates_table])
    
    return Group(header, tables)


def user_input_handler(base_station):
    """User input handler with OS clear for stable positioning."""

    COMMANDS_WITH_DESC = [
        ("REFRESH", "Update the dashboard display"),
        ("TEST", "Run a test file on selected bUEs"),
        ("DISTANCE", "Calculate distance between two bUEs"),
        ("DISCONNECT", "Disconnect from selected bUEs"),
        ("CANCEL", "Cancel running tests on selected bUEs"),
        ("LIST", "Show all currently connected bUEs"),
        ("EXIT", "Exit the base station application")
    ]
    formatted_options = [f"{cmd:<12} - {desc}" for cmd, desc in COMMANDS_WITH_DESC]
    
    COMMANDS = ("REFRESH", "TEST", "DISTANCE", "DISCONNECT", "CANCEL", "LIST", "EXIT")
    FILES = ("lora_td_ru", "lora_tu_rd", "helloworld", "gpstest", "gpstest2")

    console
    while not base_station.EXIT:
        try:
            console.clear()
            console.print(create_compact_dashboard(base_station), end="")
            print()

            # Get input with simple prompt
            index = survey.routines.select('Pick a command: ', options = formatted_options)

            if(index != 6 and len(base_station.connected_bues) == 0):
                print("Currently not connected to any bUEs")
                continue
                
            if index == Command.REFRESH.value:
                continue

            elif index == Command.TEST.value:
                connected_bues = tuple(str(x) for x in base_station.connected_bues)
                if(len(connected_bues) == 0):
                    print("Currently not connected to any bUEs")

                bues_indexes = []

                while len(bues_indexes) == 0:
                    bues_indexes = survey.routines.basket('What bUEs will be running tests? ', options = connected_bues)
                    if(len(bues_indexes) == 0):
                        print("You must select at least one bUE...")
                
                ## TODO: Should there be a check to see if a bUE is currently being tested or trust the user to handle this themselves?


                file_index = survey.routines.select('What file would you like to run? ', options = FILES)
                file_name = FILES[file_index]

                start_time = survey.routines.datetime('When would you like to run the test? ',  attrs = ('hour', 'minute', 'second')).time()
                ## TODO: It would be nice if these parameters setup to conincide with the script being run

                parameters = survey.routines.input('Enter parameters separated by a space:\n')

                send_test(base_station, bues_indexes, file_name, start_time, parameters)


            elif index == Command.DISTANCE.value: 
                connected_bues = tuple(str(x) for x in base_station.connected_bues)
                if(len(connected_bues) == 0):
                    print("Currently not connected to any bUEs")

                indexes = survey.routines.basket('Select two bUEs: ',
                                                options = connected_bues)
                
                ## TODO: Need to implement the rest of this once I fixed the coordinates 

                bues = []
                for i in indexes:
                    bues.append(base_station.connected_bues[i])

                print(base_station.bue_coordinates)
                print(base_station.get_distance(bues[0], bues[1]))

            if index == Command.DISCONNECT.value:
                connected_bues = tuple(str(x) for x in base_station.connected_bues)
                if(len(connected_bues) == 0):
                    print("Currently not connected to any bUEs")

                indexes = survey.routines.basket('What bUEs do you want to disconnect from? ',
                                                options = connected_bues)
                
                print("\n")
                for i in indexes:
                    bue = base_station.connected_bues[i]
                    print(f"Disconnected from {base_station.connected_bues[i]}")
                    base_station.connected_bues.remove(bue)
                    print(f"Connected bUES: {base_station.connected_bues}")
                    if bue in base_station.bue_coordinates.keys():
                        del base_station.bue_coordinates[bue]
                print("\n")
            
            elif index == Command.CANCEL.value:
                testing_bues = tuple(str(x) for x in base_station.testing_bues)
                if(len(testing_bues) == 0):
                    print("No bUEs are currently running any tests")

                indexes = survey.routines.basket('What bUE tests do you want to cancel? ',
                                                options = testing_bues)
                
                print("\n")
                ## TODO: Send a CANC to each of these bUEs
                for i in indexes:
                    bue = base_station.testing_bues[i]
                    print(f"Ending test for {base_station.testing_bues[i]}")
                    base_station.ota.send_ota_message(bue, "CANC")
                    logger.info(f"Sending CANC to {bue}")
                print("\n")

            elif index == Command.LIST.value:
                print("\n")
                connected_bues = " ".join(str(bue) for bue in base_station.connected_bues)
                print(f"Currently connected to {connected_bues}\n\n")
                logger.info(f"Currently connected to {connected_bues}")
            
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
            continue 

        except Exception as e:
            logger.error(f"[User Input] Error {e}")
            print(e)

# Add the missing send_test function:
def send_test(base_station, bue_indexes, file_name, start_time, parameters):
    """Send test command to selected bUEs."""
    bues = [base_station.connected_bues[index] for index in bue_indexes]
    for bue in bues:
        if not hasattr(base_station, 'testing_bues'):
            base_station.testing_bues = []
        base_station.testing_bues.append(bue)
        base_station.ota.send_ota_message(bue, f"TEST-{file_name}-{start_time}-{parameters}")

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