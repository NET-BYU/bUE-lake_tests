import tkinter as tk
from tkinter import ttk
from datetime import datetime
from enum import Enum, auto

import tkintermapview #type:ignore
import customtkinter #type:ignore

from loguru import logger

from constants import TIMEOUT, bUEs

class Command(Enum):
    REFRESH = 0
    TEST = auto()
    DISTANCE = auto()
    DISCONNECT = auto()
    CANCEL = auto()
    EXIT = auto()

class BaseStationDashboard(tk.Tk):
    def __init__(self, base_station):
        super().__init__()
        self.title("Base Station Dashboard")
        self.base_station = base_station

        self.header_label = tk.Label(self, text="", font=("Arial", 14), bg="black", fg="white", padx=10, pady=5)
        self.header_label.pack(fill="x")

        self.tables_frame = tk.Frame(self)
        self.tables_frame.pack(expand=True, fill="both")

        self.tables = {}
        self.create_table("Connected bUEs", ["bUE ID", "Status"])
        self.create_table("bUE PINGs", ["bUE ID", "Receiving PINGs"])
        self.create_table("bUE Coordinates", ["bUE ID", "Coordinates"])
        self.create_table("bUE Distances", ["bUE Pair", "Distance"])
        self.create_table("Received Messages", ["Messages"])

        self.create_control_panel()

        self.update_dashboard()

    def create_table(self, title, columns):
        lf = ttk.LabelFrame(self.tables_frame, text=title)
        lf.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        tree = ttk.Treeview(lf, columns=columns, show="headings", height=10)
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, anchor="center")
        tree.pack(expand=True, fill="both")
        self.tables[title] = tree

    def create_control_panel(self):
        cp_frame = tk.Frame(self)
        cp_frame.pack(fill="x")

        # Add buttons for each command
        self.command_buttons = {}
        for command in Command:
            if command == Command.REFRESH:
                continue  # Skip refresh button, it's handled in update_dashboard
            btn = tk.Button(cp_frame, text=command.name.capitalize(), command=lambda cmd=command: self.execute_command(cmd))
            btn.pack(side="left", padx=5, pady=5)
            self.command_buttons[command] = btn

    def execute_command(self, command):
        logger.info(f"Executing command: {command.name}")
        if command == Command.TEST:
            self.run_test()
        elif command == Command.DISTANCE:
            self.calculate_distances()
        elif command == Command.DISCONNECT:
            self.disconnect_bues()
        elif command == Command.CANCEL:
            self.cancel_operations()
        elif command == Command.EXIT:
            self.quit()
        self.update_dashboard()

    def run_test(self):
        logger.info("Running tests on all connected bUEs")
        self.base_station.send_tests()

    def calculate_distances(self):
        logger.info("Calculating distances between all connected bUEs")
        self.base_station.calculate_all_distances()

    def disconnect_bues(self):
        logger.info("Disconnecting all bUEs")
        for bue in self.base_station.connected_bues:
            self.base_station.disconnect_bue(bue)

    def cancel_operations(self):
        logger.info("Cancelling all ongoing operations")
        self.base_station.cancel_all_operations()

    def update_dashboard(self):
        now = datetime.now().strftime('%H:%M:%S')
        connected_count = len(self.base_station.connected_bues)
        testing_count = len(getattr(self.base_station, 'testing_bues', []))
        self.header_label.config(text=f"🏢 Base Station Dashboard - {now} | Connected: {connected_count} | Testing: {testing_count}")

        self.populate_connected_table()
        self.populate_ping_table()
        self.populate_coordinates_table()
        self.populate_distance_table()
        self.populate_messages_table()

        self.after(5000, self.update_dashboard)  # Refresh every 5s

    def clear_table(self, title):
        for row in self.tables[title].get_children():
            self.tables[title].delete(row)

    def populate_connected_table(self):
        self.clear_table("Connected bUEs")
        tree = self.tables["Connected bUEs"]
        if not self.base_station.connected_bues:
            tree.insert("", "end", values=("No bUEs connected", "N/A"))
            return
        for bue in self.base_station.connected_bues:
            status = "🧪 Testing" if bue in getattr(self.base_station, 'testing_bues', []) else "💤 Idle"
            tree.insert("", "end", values=(bUEs[str(bue)], status))

    def populate_ping_table(self):
        self.clear_table("bUE PINGs")
        tree = self.tables["bUE PINGs"]
        if not self.base_station.connected_bues:
            tree.insert("", "end", values=("No bUEs connected", "N/A"))
            return
        for bue in self.base_station.connected_bues:
            timeout = self.base_station.bue_timeout_tracker.get(bue, 0)
            if timeout >= TIMEOUT / 2:
                status = "🟢 Good"
            elif timeout > 0:
                status = "🟡 Warning"
            else:
                status = "🔴 Lost"
            tree.insert("", "end", values=(bUEs[str(bue)], status))

    def populate_coordinates_table(self):
        self.clear_table("bUE Coordinates")
        tree = self.tables["bUE Coordinates"]
        if not self.base_station.bue_coordinates:
            tree.insert("", "end", values=("No coordinates available", "N/A"))
            return
        for bue, coords in self.base_station.bue_coordinates.items():
            tree.insert("", "end", values=(bUEs[str(bue)], str(coords)))

    def populate_distance_table(self):
        self.clear_table("bUE Distances")
        tree = self.tables["bUE Distances"]
        coords = self.base_station.bue_coordinates
        processed = set()
        if not coords:
            tree.insert("", "end", values=("No distances available", "N/A"))
            return
        for b1 in self.base_station.connected_bues:
            for b2 in self.base_station.connected_bues:
                if b1 != b2 and (b1, b2) not in processed and (b2, b1) not in processed:
                    processed.add((b1, b2))
                    try:
                        dist = self.base_station.get_distance(b1, b2)
                        if dist is not None:
                            value = f"{dist:.2f}m"
                        else:
                            value = "Invalid coordinates"
                    except Exception as e:
                        value = f"Error: {str(e)}"
                    label = f"{bUEs[str(b1)]} ↔ {bUEs[str(b2)]}"
                    tree.insert("", "end", values=(label, value))

    def populate_messages_table(self):
        self.clear_table("Received Messages")
        tree = self.tables["Received Messages"]
        if not self.base_station.stdout_history:
            tree.insert("", "end", values=("No messages",))
            return
        for msg in self.base_station.stdout_history:
            tree.insert("", "end", values=(msg,))

