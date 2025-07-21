import customtkinter #type:ignore
from tkintermapview import TkinterMapView #type:ignore
import tkinter as tk
from tkinter import ttk

from constants import bUEs, TIMEOUT, bUEs_inverted

class Gui(customtkinter.CTk):

    APP_NAME = "Base Station GUI"

    def __init__(self, base_station, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.base_station = base_station

        self.title(Gui.APP_NAME)
        
        # Get screen dimensions and set window to 80% of screen size
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # For dual monitor setups, use half the total width to get single monitor width
        single_monitor_width = screen_width // 2 if screen_width > 2560 else screen_width
        
        window_width = int(single_monitor_width * 0.8)
        window_height = int(screen_height * 0.8)
        
        # Center the window on screen
        x = (single_monitor_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.minsize(600, 400)  # Set reasonable minimum size

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.bind("<Command-q>", self.on_closing)
        self.bind("<Command-w>", self.on_closing)

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.frame_left = customtkinter.CTkFrame(master=self, corner_radius=0, fg_color='Green')
        self.frame_left.grid(row=0, column=0, padx=0, pady=0, sticky='nsew')
        self.frame_left.grid_rowconfigure((0,1), weight=1)
        self.frame_left.grid_columnconfigure(0, weight=1)

        connected_bues_frame = customtkinter.CTkFrame(master=self.frame_left, corner_radius=0, fg_color='yellow')
        connected_bues_frame.grid(column=0, row=0, padx=0, pady=0, sticky='nsew')

        self.tables = {}
        self.create_table(title="Connected bUEs", columns=["Name", "State", "Status"], frame=connected_bues_frame)
        self.update_dashboard()

        self.frame_middle = customtkinter.CTkFrame(master=self, corner_radius=0, fg_color='Black') 
        self.frame_middle.grid(row=0, column=1, padx=0, pady=0, sticky='nsew')
        
        self.frame_right = customtkinter.CTkFrame(master=self, corner_radius=0, fg_color='Red')
        self.frame_right.grid(row=0, column=2, padx=0, pady=0, sticky='nsew')

        self.frame_right.grid_rowconfigure((0,1), weight=1)
        self.frame_right.grid_columnconfigure(0, weight=1)

        self.map_widget = TkinterMapView(self.frame_right, corner_radius=0)
        self.map_widget.set_position(40.44564, -111.49372)
        self.map_widget.grid(row=1, column=0, sticky="nswe", padx=(0, 0), pady=(0, 0))
        self.map_widget.set_zoom(13)

    def create_table(self, title, columns, frame):
        # Create main container with subtle styling
        table_container = customtkinter.CTkFrame(frame, corner_radius=8, fg_color="transparent")
        table_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Simple title label
        title_label = customtkinter.CTkLabel(
            table_container, 
            text=title, 
            font=customtkinter.CTkFont(size=14, weight="bold")
        )
        title_label.grid(row=0, column=0, sticky="w", padx=10, pady=(5, 10))
        
        # Configure grid
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        table_container.grid_rowconfigure(1, weight=1)
        table_container.grid_columnconfigure(0, weight=1)
        
        # Create treeview with minimal styling
        tree = ttk.Treeview(
            table_container, 
            columns=columns, 
            show="headings", 
            height=8
        )
        
        # Simple column configuration
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, anchor="center", width=100)
        
        # Bind right-click event for context menu
        tree.bind("<Button-3>", lambda event: self.show_context_menu(event, tree, title))
        
        # Simple scrollbar
        scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        # Grid layout
        tree.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=(0, 10))
        scrollbar.grid(row=1, column=1, sticky="ns", pady=(0, 10))
        
        self.tables[title] = tree

    def show_context_menu(self, event, tree, table_title):
        # Get the item that was right-clicked
        item = tree.identify_row(event.y)
        if not item:
            return
        
        # Select the item
        tree.selection_set(item)
        
        # Get the bUE name from the selected row
        values = tree.item(item, 'values')
        if not values or values[0] == "No bUEs connected":
            return
        
        bue_name = values[0]
        
        # Create context menu
        context_menu = tk.Menu(self, tearoff=0)
        context_menu.add_command(label=f"Ping {bue_name}", command=lambda: self.ping_bue(bue_name))
        context_menu.add_command(label=f"Start Test on {bue_name}", command=lambda: self.start_test_bue(bue_name))
        context_menu.add_command(label=f"Stop Test on {bue_name}", command=lambda: self.stop_test_bue(bue_name))
        context_menu.add_separator()
        context_menu.add_command(label=f"View Details", command=lambda: self.view_bue_details(bue_name))
        context_menu.add_command(label=f"Disconnect {bue_name}", command=lambda: self.disconnect_bue(bue_name))
        
        # Function to close menu when clicking outside
        def close_menu():
            context_menu.unpost()
            self.unbind("<Button-1>")
        
        # Show the menu at the cursor position
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
            # Bind left-click to close menu when clicking outside
            self.bind("<Button-1>", lambda e: close_menu())
        finally:
            context_menu.grab_release()
    
    def clear_table(self, title):
        for row in self.tables[title].get_children():
            self.tables[title].delete(row)

    def update_dashboard(self):
        self.populate_connected_table()
        # self.populate_ping_table()
        # self.populate_coordinates_table()
        # self.populate_distance_table()
        # self.populate_messages_table()

        self.after(5000, self.update_dashboard)  # Refresh every 5s

    def populate_connected_table(self):
        self.clear_table("Connected bUEs")
        tree = self.tables["Connected bUEs"]
        if not self.base_station.connected_bues:
            tree.insert("", "end", values=("No bUEs connected", "N/A", "N/A"))
            return
        for bue in self.base_station.connected_bues:
            state = "🧪 Testing" if bue in getattr(self.base_station, 'testing_bues', []) else "💤 Idle"
            timeout = self.base_station.bue_timeout_tracker.get(bue, 0)
            if timeout >= TIMEOUT / 2:
                status = "✅ Good"
            elif timeout > 0:
                status = "⚠️ Warning"
            else:
                status = "❌ Lost"
            tree.insert("", "end", values=(bUEs[str(bue)], state, status))

    def disconnect_bue(self, bue_name):
        print(f'Disconnecting from {bue_name}')

        bue = int(bUEs_inverted[bue_name])
        self.base_station.connected_bues.remove(bue)
        if bue in self.base_station.bue_coordinates.keys():
            del self.base_station.bue_coordinates[bue]
        if bue in self.base_station.testing_bues:
            self.base_station.testing_bues.remove(bue)
        if bue in self.base_station.bue_timeout_tracker.keys():
            del self.base_station.bue_timeout_tracker[bue]

        self.update_dashboard()

    def on_closing(self, event=0):
        self.destroy()
        self.base_station.EXIT = True