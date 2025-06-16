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
    """Make a new table."""
    table = Table()
    table.add_column("bUEs")

    for bue in base_station.connected_bues:
        table.add_row(
            f"{bue}"
        )

    if not base_station.connected_bues:
        table.add_row("No bUEs connected")
    
    return table

def bue_coordinates_table(base_station) -> Table:
    """Make a new table."""
    table = Table()
    table.add_column("bUEs")
    table.add_column("Coordinates")

    for bue in base_station.connected_bues:
        if bue in base_station.bue_coordinates:
            table.add_row(
                f"{bue}", f"{base_station.bue_coordinates[bue]}"
            )
    return table

def create_dashboard_layout(base_station) -> Layout:
    """Create the main dashboard layout."""
    layout = Layout()
    
    # Split into top and bottom sections
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="tables", ratio=2),
        Layout(name="input_area", size=10)
    )
    
    # Header with timestamp
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    layout["header"].update(
        Panel(f"🏢 Base Station Dashboard - {current_time}", 
              style="bold white on blue")
    )
    
    # Tables section - split horizontally
    layout["tables"].split_row(
        Layout(generate_table(base_station), name="connected_table"),
        Layout(bue_coordinates_table(base_station), name="coordinates_table")
    )
    
    # Input area placeholder
    layout["input_area"].update(
        Panel("User input will appear here...", title="Command Interface", style="dim")
    )
    
    return layout

def send_test(base_station, bue_indexes, file_name, start_time, parameters):
    bues = [base_station.connected_bues[index] for index in bue_indexes]
    for bue in bues:
        base_station.testing_bues.append(bue)
        base_station.ota.send_ota_message(bue, f"TEST-{file_name}-{start_time}-{parameters}")

# def live_display_loop(base_station):
#     with Live(Group(generate_table(base_station), bue_coordinates_table(base_station)),refresh_per_second=4, screen=False) as live:
#         while not base_station.EXIT:
#             time.sleep(0.4)
#             live.update(Group(generate_table(base_station), bue_coordinates_table(base_station))) 

class DashboardApp:
    def __init__(self, base_station):
        self.base_station = base_station
        self.live = None
        self.layout = None
        
    def start_live_display(self):
        """Start the live display in a separate thread."""
        def live_update_loop():
            with Live(create_dashboard_layout(self.base_station), 
                     refresh_per_second=2, console=console, screen=True) as live:
                self.live = live
                while not self.base_station.EXIT:
                    live.update(create_dashboard_layout(self.base_station))
                    time.sleep(0.5)
        
        live_thread = threading.Thread(target=live_update_loop, daemon=True)
        live_thread.start()
        time.sleep(1)  # Give the live display time to start

    def update_input_area(self, message):
        """Update the input area of the dashboard."""
        if hasattr(self, 'live') and self.live:
            layout = create_dashboard_layout(self.base_station)
            layout["input_area"].update(
                Panel(message, title="Command Interface", style="green")
            )
            self.live.update(layout)

def user_input_handler(base_station):
    """Enhanced user input handler with Rich interface."""
    
    # Start the dashboard
    dashboard = DashboardApp(base_station)
    dashboard.start_live_display()
    
    COMMANDS = ["TEST", "DISTANCE", "DISCONNECT", "CANCEL", "LIST", "EXIT"]
    FILES = ["lora_td_ru", "lora_tu_rd", "helloworld", "gpstest", "gpstest2"]

    while not base_station.EXIT:
        try:
            # Update input area to show menu
            menu_text = "[bold cyan]Available Commands:[/bold cyan]\n"
            for i, cmd in enumerate(COMMANDS):
                menu_text += f"  {i}: {cmd}\n"
            dashboard.update_input_area(menu_text)
            
            # Get user input (this will appear in terminal below the dashboard)
            console.print("\n" + "="*50)
            console.print("[bold cyan]Select a command (0-5):[/bold cyan]")
            
            try:
                index = IntPrompt.ask("Command", choices=[str(i) for i in range(len(COMMANDS))])
            except KeyboardInterrupt:
                console.print("\n[yellow]Cancelled input. Returning to menu.[/yellow]")
                continue

            if index != 5 and len(base_station.connected_bues) == 0:
                console.print("[red]Currently not connected to any bUEs[/red]")
                continue

            if index == 0:  # TEST
                connected_bues = [str(x) for x in base_station.connected_bues]
                if len(connected_bues) == 0:
                    console.print("[red]Currently not connected to any bUEs[/red]")
                    continue

                # Show available bUEs
                console.print("\n[bold]Connected bUEs:[/bold]")
                for i, bue in enumerate(connected_bues):
                    console.print(f"  {i}: {bue}")
                
                # Get bUE selection
                bue_choices = Prompt.ask("Select bUEs (comma-separated indices)", default="0")
                bues_indexes = [int(x.strip()) for x in bue_choices.split(",") if x.strip().isdigit()]
                
                # Show available files
                console.print("\n[bold]Available files:[/bold]")
                for i, file in enumerate(FILES):
                    console.print(f"  {i}: {file}")
                
                file_index = IntPrompt.ask("Select file", choices=[str(i) for i in range(len(FILES))])
                file_name = FILES[file_index]

                # Time input
                hour = IntPrompt.ask("Start hour (0-23)", default=0)
                minute = IntPrompt.ask("Start minute (0-59)", default=0)
                second = IntPrompt.ask("Start second (0-59)", default=0)
                start_time = f"{hour:02d}:{minute:02d}:{second:02d}"

                parameters = Prompt.ask("Enter parameters (space-separated)", default="")

                send_test(base_station, bues_indexes, file_name, start_time, parameters)
                console.print(f"[green]✅ Test started for {len(bues_indexes)} bUE(s)[/green]")

            elif index == 1:  # DISTANCE
                connected_bues = [str(x) for x in base_station.connected_bues]
                if len(connected_bues) < 2:
                    console.print("[red]Need at least 2 connected bUEs for distance calculation[/red]")
                    continue

                console.print("\n[bold]Select two bUEs for distance calculation:[/bold]")
                for i, bue in enumerate(connected_bues):
                    console.print(f"  {i}: {bue}")
                
                bue_selection = Prompt.ask("Select two bUEs (comma-separated)", default="0,1")
                indexes = [int(x.strip()) for x in bue_selection.split(",") if x.strip().isdigit()]
                
                if len(indexes) >= 2:
                    bue1 = base_station.connected_bues[indexes[0]]
                    bue2 = base_station.connected_bues[indexes[1]]
                    distance = base_station.get_distance(bue1, bue2)
                    console.print(f"[green]📏 Distance between {bue1} and {bue2}: {distance}[/green]")

            elif index == 2:  # DISCONNECT
                connected_bues = [str(x) for x in base_station.connected_bues]
                if len(connected_bues) == 0:
                    console.print("[red]No bUEs to disconnect[/red]")
                    continue

                console.print("\n[bold]Connected bUEs:[/bold]")
                for i, bue in enumerate(connected_bues):
                    console.print(f"  {i}: {bue}")
                
                selection = Prompt.ask("Select bUEs to disconnect (comma-separated)")
                indexes = [int(x.strip()) for x in selection.split(",") if x.strip().isdigit()]
                
                for i in sorted(indexes, reverse=True):  # Remove in reverse order
                    if i < len(base_station.connected_bues):
                        bue = base_station.connected_bues[i]
                        base_station.connected_bues.remove(bue)
                        if bue in base_station.bue_coordinates:
                            del base_station.bue_coordinates[bue]
                        console.print(f"[yellow]🔌 Disconnected from {bue}[/yellow]")

            elif index == 3:  # CANCEL
                testing_bues = [str(x) for x in base_station.testing_bues]
                if len(testing_bues) == 0:
                    console.print("[yellow]No tests currently running[/yellow]")
                    continue

                console.print("\n[bold]Running tests:[/bold]")
                for i, bue in enumerate(testing_bues):
                    console.print(f"  {i}: {bue}")
                
                selection = Prompt.ask("Select tests to cancel (comma-separated)")
                indexes = [int(x.strip()) for x in selection.split(",") if x.strip().isdigit()]
                
                for i in indexes:
                    if i < len(base_station.testing_bues):
                        bue = base_station.testing_bues[i]
                        base_station.ota.send_ota_message(bue, "CANC")
                        console.print(f"[red]❌ Cancelled test for {bue}[/red]")
                        logger.info(f"Sending CANC to {bue}")

            elif index == 4:  # LIST
                connected_bues = ", ".join(str(bue) for bue in base_station.connected_bues)
                console.print(f"[green]📋 Currently connected: {connected_bues}[/green]")
                logger.info(f"Currently connected to {connected_bues}")

            elif index == 5:  # EXIT
                console.print("[red]👋 Exiting Base Station service...[/red]")
                base_station.EXIT = True
                base_station.__del__()
                sys.exit(0)

        except KeyboardInterrupt:
            console.print("\n[yellow]⚠️ Cancelled input. Returning to command prompt.[/yellow]")
            continue
        except Exception as e:
            logger.error(f"[User Input] Error {e}")
            console.print(f"[red]❌ Error: {e}[/red]")


if __name__ == "__main__":
    start_time = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    logger.info(f"This marks the start of the base station service at {start_time}")

    try:
        base_station = Base_Station_Main(yaml_str="config_base.yaml")
        base_station.tick_enabled = True

        # user_input_thread = threading.Thread(target=user_input_handler, args=(base_station,))
        # user_input_thread.daemon = True
        # user_input_thread.start()

        # live_thread = threading.Thread(target=live_display_loop, args=(base_station,), daemon=True)
        # live_thread.start()

        user_input_handler(base_station)

        while not base_station.EXIT:
            time.sleep(0.2)

    except KeyboardInterrupt:
        logger.info("Exiting the Base Station service")
        if base_station is not None:
            base_station.EXIT = True
            time.sleep(0.5)
            base_station.__del__()
        # if 'user_input_thread' in locals() and user_input_thread.is_alive():
        #     user_input_thread.join(timeout=2.0)
        sys.exit(0)