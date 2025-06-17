import sys
import time
import threading
from datetime import datetime
from loguru import logger

from rich.live import Live
from rich.table import Table
from rich.console import Group, Console
import survey # type:ignore
from rich.layout import Layout
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm

from base_station_main import Base_Station_Main

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

def create_dashboard_layout(base_station) -> Layout:
    """Create the main dashboard layout."""
    layout = Layout()
    
    # Split into header and main content only
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="tables", ratio=1)
    )
    
    # Header with timestamp and connection count
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    connected_count = len(base_station.connected_bues)
    testing_count = len(getattr(base_station, 'testing_bues', []))
    
    header_text = f"🏢 Base Station Dashboard - {current_time} | Connected: {connected_count} | Testing: {testing_count}"
    layout["header"].update(
        Panel(header_text, style="bold white on blue")
    )
    
    # Tables section - split horizontally
    layout["tables"].split_row(
        Layout(generate_table(base_station), name="connected_table"),
        Layout(bue_coordinates_table(base_station), name="coordinates_table")
    )
    
    return layout

def show_menu():
    """Display the command menu."""
    COMMANDS = ["TEST", "DISTANCE", "DISCONNECT", "CANCEL", "LIST", "EXIT"]
    
    # Create a styled menu
    menu_table = Table(title="🎛️  Command Menu", show_header=False, box=None)
    menu_table.add_column("ID", style="bold cyan", width=4, justify="center")
    menu_table.add_column("Command", style="bold white", width=15)
    menu_table.add_column("Description", style="dim", width=30)
    
    descriptions = [
        "Start a test on selected bUEs",
        "Calculate distance between bUEs", 
        "Disconnect from selected bUEs",
        "Cancel running tests",
        "List all connected bUEs",
        "Exit the application"
    ]
    
    for i, (cmd, desc) in enumerate(zip(COMMANDS, descriptions)):
        menu_table.add_row(str(i), cmd, desc)
    
    return menu_table

def user_input_handler(base_station):
    """User input handler with OS clear for stable positioning."""
    
    FILES = ["lora_td_ru", "lora_tu_rd", "helloworld", "gpstest", "gpstest2"]

    while not base_station.EXIT:
        try:
            # Use OS command to truly clear screen
            import os
            os.system('clear')  # Linux/Mac - use 'cls' for Windows
            
            # Print dashboard
            console.print(create_dashboard_layout(base_station))
            console.print()
            console.print(show_menu())
            console.print()
            
            # Get input with simple prompt
            index = IntPrompt.ask(
                "[bold cyan]Select command[/bold cyan]", 
                choices=[str(i) for i in range(6)],
                show_choices=False
            )
            
            # Check if bUEs are connected (except for LIST and EXIT)
            if index not in [4, 5] and len(base_station.connected_bues) == 0:
                console.print("[red]❌ No bUEs currently connected![/red]")
                input("Press Enter to continue...")
                continue

            if index == 0:  # TEST
                console.print("[green]🧪 Test started successfully![/green]")
                # Simplified test process for demo
                if base_station.connected_bues:
                    send_test(base_station, [0], FILES[0], "00:00:00", "")
                input("Press Enter to continue...")
            
            elif index == 1:  # DISTANCE
                if len(base_station.connected_bues) >= 2:
                    bue1 = base_station.connected_bues[0]
                    bue2 = base_station.connected_bues[1]
                    distance = base_station.get_distance(bue1, bue2)
                    console.print(f"[green]📏 Distance: {distance}[/green]")
                else:
                    console.print("[red]❌ Need at least 2 bUEs[/red]")
                input("Press Enter to continue...")
            
            elif index == 2:  # DISCONNECT
                if base_station.connected_bues:
                    bue = base_station.connected_bues[0]
                    base_station.connected_bues.remove(bue)
                    if bue in base_station.bue_coordinates:
                        del base_station.bue_coordinates[bue]
                    console.print(f"[yellow]🔌 Disconnected from {bue}[/yellow]")
                else:
                    console.print("[red]❌ No bUEs to disconnect[/red]")
                input("Press Enter to continue...")
            
            elif index == 3:  # CANCEL
                testing_bues = getattr(base_station, 'testing_bues', [])
                if testing_bues:
                    bue = testing_bues[0]
                    base_station.ota.send_ota_message(bue, "CANC")
                    console.print(f"[red]❌ Cancelled test for {bue}[/red]")
                else:
                    console.print("[yellow]ℹ️  No tests running[/yellow]")
                input("Press Enter to continue...")
            
            elif index == 4:  # LIST
                connected_list = ", ".join(str(bue) for bue in base_station.connected_bues) or "None"
                console.print(f"[green]📋 Connected: {connected_list}[/green]")
                logger.info(f"Currently connected to: {connected_list}")
                input("Press Enter to continue...")
            
            elif index == 5:  # EXIT
                console.print("[red]👋 Shutting down...[/red]")
                base_station.EXIT = True
                base_station.__del__()
                sys.exit(0)
                
        except KeyboardInterrupt:
            console.print("\n[yellow]⚠️  Use EXIT command (5) to quit properly.[/yellow]")
            time.sleep(1)
            continue
        except Exception as e:
            logger.error(f"[User Input] Error {e}")
            console.print(f"[red]❌ Error: {e}[/red]")
            input("Press Enter to continue...")

# Add the missing send_test function:
def send_test(base_station, bue_indexes, file_name, start_time, parameters):
    """Send test command to selected bUEs."""
    bues = [base_station.connected_bues[index] for index in bue_indexes]
    for bue in bues:
        if not hasattr(base_station, 'testing_bues'):
            base_station.testing_bues = []
        base_station.testing_bues.append(bue)
        base_station.ota.send_ota_message(bue, f"TEST-{file_name}-{start_time}-{parameters}")

# Add this at the very end of your file:

if __name__ == "__main__":
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