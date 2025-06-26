from datetime import datetime

from rich.table import Table
from rich.console import Group
from rich.panel import Panel

from constants import TIMEOUT, bUEs

def bue_status_table(base_station) -> Table:
    """Make a styled table of connected bUEs."""
    table = Table(title="📡 Connected bUEs", show_header=True, header_style="bold cyan")
    table.add_column("bUE ID", style="green", no_wrap=True, justify="center")
    table.add_column("Status", style="yellow", justify="center")

    for bue in base_station.connected_bues:
        status = "🧪 Testing" if bue in getattr(base_station, 'testing_bues', []) else "💤 Idle"
        table.add_row(bUEs[str(bue)], status)
    
    if not base_station.connected_bues:
        table.add_row("[dim]No bUEs connected[/dim]", "[dim]N/A[/dim]")
    
    return table

def bue_ping_table(base_station) -> Table:
    """Make a styled table of connected bUEs."""
    table = Table(title="🏓 bUE PINGs", show_header=True, header_style="bold cyan")
    table.add_column("bUE ID", style="green", no_wrap=True, justify="center")
    table.add_column("Receiving PINGs", style="yellow", justify="center")

    for bue in base_station.connected_bues:
        if base_station.bue_timeout_tracker[bue] >= TIMEOUT / 2:
            ping_status = "🟢 Good"
        elif base_station.bue_timeout_tracker[bue] > 0:
            ping_status = "🟡 Warning"
        else:
            ping_status = "🔴 Lost"
        
        table.add_row(bUEs[str(bue)], str(ping_status))
    
    if not base_station.connected_bues:
        table.add_row("[dim]No bUEs connected[/dim]", "[dim]N/A[/dim]")
    
    return table

def bue_coordinates_table(base_station) -> Table:
    """Make a styled coordinates table."""
    table = Table(title="🌍 bUE Coordinates", show_header=True, header_style="bold blue")
    table.add_column("bUE ID", style="cyan", justify="center")
    table.add_column("Coordinates", style="yellow", justify="left")

    for bue in base_station.connected_bues:
        if bue in base_station.bue_coordinates:
            coords = base_station.bue_coordinates[bue]
            table.add_row(bUEs[str(bue)], str(coords))
    
    if not base_station.bue_coordinates:
        table.add_row("[dim]No coordinates available[/dim]", "[dim]N/A[/dim]")
    
    return table

def bue_distance_table(base_station) -> Table:
    """Make a styled distance table."""
    table = Table(title="📏 bUE Distances", show_header=True, header_style="bold blue")
    table.add_column("bUE Pair", style="cyan", justify="center")
    table.add_column("Distance", style="yellow", justify="left")

    # Use a set to avoid duplicate pairs
    processed_pairs = set()
    
    for bue1 in base_station.connected_bues:
        for bue2 in base_station.connected_bues:
            if (bue1 != bue2 and 
                bue1 in base_station.bue_coordinates and 
                bue2 in base_station.bue_coordinates and
                (bue1, bue2) not in processed_pairs and
                (bue2, bue1) not in processed_pairs):
                
                dist = base_station.get_distance(bue1, bue2)
                
                if dist is not None:
                    table.add_row(f"{bUEs[str(bue1)]} ↔ {bUEs[str(bue2)]}", f"{dist:.2f}m")
                else:
                    table.add_row(f"{bUEs[str(bue1)]} ↔ {bUEs[str(bue2)]}", "[red]Invalid coordinates[/red]")
                
                # Mark this pair as processed
                processed_pairs.add((bue1, bue2))
    
    if not base_station.bue_coordinates or len(processed_pairs) == 0:
        table.add_row("[dim]No distances available[/dim]", "[dim]N/A[/dim]")
    
    return table

def received_messages_table(base_station) -> Table:
    """Make a styled coordinates table."""
    table = Table(title="💌  Received Messages", show_header=True, header_style="bold blue")
    table.add_column("Messages", style="cyan", justify="center")

    for message in base_station.stdout_history:
            table.add_row(message)
    
    if not base_station.stdout_history:
        table.add_row("[dim]No messages[/dim]")
    
    return table


def create_compact_dashboard(base_station):
    """Create a compact dashboard without Layout."""
    # Header
    current_time = datetime.now().strftime('%H:%M:%S')
    connected_count = len(base_station.connected_bues)
    testing_count = len(getattr(base_station, 'testing_bues', []))
    
    header_text = f"🏢 Base Station Dashboard - {current_time} | Connected: {connected_count} | Testing: {testing_count}"
    header = Panel(header_text, style="bold white on blue", padding=(0,1))
    
    connected_table = bue_status_table(base_station)
    coordinates_table = bue_coordinates_table(base_station)
    distance_table = bue_distance_table(base_station)
    ping_table = bue_ping_table(base_station)
    received_messages = received_messages_table(base_station)
    
    from rich.columns import Columns
    tables = Columns([connected_table, ping_table, coordinates_table, distance_table, received_messages])
    
    return Group(header, tables)