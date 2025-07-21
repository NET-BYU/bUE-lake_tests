import customtkinter #type:ignore
from tkintermapview import TkinterMapView #type:ignore
import tkinter as tk
from tkinter import ttk

from constants import bUEs, TIMEOUT, bUEs_inverted

class Gui(customtkinter.CTk):

    APP_NAME = "Base Station Control Center"

    def __init__(self, base_station, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.base_station = base_station
        
        # Initialize bUE markers dictionary
        self.bue_markers = {}

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
        self.grid_rowconfigure(0, weight=1)

        self.frame_left = customtkinter.CTkFrame(master=self, corner_radius=0, fg_color=("#F8F9FA", "gray12"))
        self.frame_left.grid(row=0, column=0, padx=0, pady=0, sticky='nsew')
        self.frame_left.grid_rowconfigure((0,1), weight=1)
        self.frame_left.grid_columnconfigure(0, weight=1)

        connected_bues_frame = customtkinter.CTkFrame(master=self.frame_left, corner_radius=0, fg_color="transparent")
        connected_bues_frame.grid(column=0, row=0, padx=0, pady=0, sticky='nsew')

        self.tables = {}
        self.create_table(title="Connected bUEs", columns=["Name", "State", "Status"], frame=connected_bues_frame)

        # Add test configuration button to left frame with professional styling
        test_config_button_frame = customtkinter.CTkFrame(master=self.frame_left, corner_radius=8, fg_color=("#FFFFFF", "gray20"), border_width=1, border_color=("#E3E6EA", "gray25"))
        test_config_button_frame.grid(column=0, row=1, padx=15, pady=15, sticky='ew')
        
        # Button title
        button_title = customtkinter.CTkLabel(
            test_config_button_frame,
            text="Test Management",
            font=customtkinter.CTkFont(size=14, weight="bold"),
            text_color=("#2C3E50", "#ECF0F1")
        )
        button_title.pack(pady=(15, 5))
        
        test_config_button = customtkinter.CTkButton(
            test_config_button_frame,
            text="Configure Test Parameters",
            command=self.open_test_configuration_window,
            width=220,
            height=42,
            font=customtkinter.CTkFont(size=13, weight="normal"),
            fg_color=("#3A8EBA", "#2E6B8A"),
            hover_color=("#2E6B8A", "#1F4A5C"),
            corner_radius=6,
            border_width=1,
            border_color=("#2E6B8A", "#1F4A5C"),
            text_color=("#FFFFFF", "#FFFFFF")
        )
        test_config_button.pack(pady=(0, 15), padx=15)

        self.frame_right = customtkinter.CTkFrame(master=self, corner_radius=0, fg_color=("#FFFFFF", "gray18"))
        self.frame_right.grid(row=0, column=1, padx=0, pady=0, sticky='nsew')

        self.frame_right.grid_rowconfigure((0,1), weight=1)
        self.frame_right.grid_columnconfigure(0, weight=1)
        
        # Add a header for the map section
        map_header = customtkinter.CTkFrame(self.frame_right, corner_radius=0, fg_color="transparent", height=50)
        map_header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        
        map_title = customtkinter.CTkLabel(
            map_header,
            text="Base Station Map View",
            font=customtkinter.CTkFont(size=16, weight="bold"),
            text_color=("#2C3E50", "#ECF0F1")
        )
        map_title.pack(pady=15)

        # Map container with subtle border
        map_container = customtkinter.CTkFrame(self.frame_right, corner_radius=6, fg_color=("#E8F4FD", "gray25"), border_width=1, border_color=("#BDC3C7", "gray30"))
        map_container.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        map_container.grid_columnconfigure(0, weight=1)
        map_container.grid_rowconfigure(0, weight=1)

        self.map_widget = TkinterMapView(map_container, corner_radius=6)
        self.map_widget.set_position(40.44564, -111.49372)
        self.map_widget.grid(row=0, column=0, sticky="nswe", padx=3, pady=3)
        self.map_widget.set_zoom(13)
        
        # Start the dashboard update cycle now that all widgets are created
        self.update_dashboard()

    def open_test_configuration_window(self):
        """Open the test configuration popup window"""
        TestConfigurationWindow(self)

    def update_map_markers(self):
        """Update map markers based on current bUE coordinates and status"""
        # Get current bUE coordinates
        current_coordinates = getattr(self.base_station, 'bue_coordinates', {})
        
        # Remove markers for bUEs that are no longer connected or have no coordinates
        markers_to_remove = []
        for bue_id in list(self.bue_markers.keys()):
            if bue_id not in current_coordinates or bue_id not in self.base_station.connected_bues:
                markers_to_remove.append(bue_id)
        
        for bue_id in markers_to_remove:
            self.remove_bue_marker(bue_id)
        
        # Add or update markers for current bUEs
        for bue_id, coordinates in current_coordinates.items():
            if bue_id in self.base_station.connected_bues:
                self.add_or_update_bue_marker(bue_id, coordinates)

    def add_or_update_bue_marker(self, bue_id, coordinates):
        """Add or update a bUE marker on the map"""
        if not coordinates or len(coordinates) != 2:
            return
        
        # Convert coordinates to float if they're strings
        try:
            lat = float(coordinates[0])
            lon = float(coordinates[1])
        except (ValueError, TypeError):
            print(f"Warning: Invalid coordinates for bUE {bue_id}: {coordinates}")
            return
        
        bue_name = bUEs.get(str(bue_id), f"bUE-{bue_id}")
        
        # Determine status
        timeout = self.base_station.bue_timeout_tracker.get(bue_id, 0)
        if timeout >= TIMEOUT / 2:
            status = "Connected"
            color = "green"
        elif timeout > 0:
            status = "Warning" 
            color = "orange"
        else:
            status = "Disconnected"
            color = "red"
            
        # Check if testing
        test_status = "Testing" if bue_id in getattr(self.base_station, 'testing_bues', []) else "Idle"
        if test_status == "Testing":
            prefix = "[TESTING] "
        else:
            prefix = ""
            
        # Create marker text - now with proper float formatting
        marker_text = f"{prefix}CONN: {bue_name}" if status == "Connected" else f"{prefix}WARN: {bue_name}" if status == "Warning" else f"{prefix}DISC: {bue_name}"
        
        # Remove old marker if it exists
        if bue_id in self.bue_markers:
            self.map_widget.delete(self.bue_markers[bue_id])
        
        # Add new marker with click command
        try:
            marker = self.map_widget.set_marker(
                lat, lon, 
                text=marker_text,
                marker_color_circle=color,
                marker_color_outside=color,
                command=lambda: self.on_marker_click(bue_id)
            )
            self.bue_markers[bue_id] = marker
        except Exception as e:
            print(f"Error creating marker: {e}")
            # Fallback to simpler marker
            try:
                marker = self.map_widget.set_marker(lat, lon, text=marker_text)
                self.bue_markers[bue_id] = marker
            except Exception as e2:
                print(f"Fallback marker creation also failed: {e2}")

    def remove_bue_marker(self, bue_id):
        """Remove a marker for a specific bUE"""
        if bue_id in self.bue_markers:
            try:
                self.bue_markers[bue_id].delete()
                del self.bue_markers[bue_id]
            except Exception as e:
                print(f"Error removing marker for bUE {bue_id}: {e}")

    def on_marker_click(self, bue_id):
        """Handle clicks on map markers"""
        bue_name = bUEs.get(str(bue_id), f"bUE {bue_id}")
        print(f"Clicked on marker for {bue_name} (ID: {bue_id})")
        # Could show a popup or context menu here
        self.view_bue_details(bue_name)

    def show_marker_details_popup(self, bue_id):
        """Show comprehensive marker information in a professional popup window"""
        bue_name = bUEs.get(str(bue_id), f"bUE {bue_id}")
        
        # Get current bUE data
        timeout = self.base_station.bue_timeout_tracker.get(bue_id, 0)
        coordinates = self.base_station.bue_coordinates.get(bue_id, (0.0, 0.0))
        is_testing = bue_id in getattr(self.base_station, 'testing_bues', [])
        
        # Determine status details
        if timeout >= TIMEOUT / 2:
            status = "Connected"
            status_color = "#27AE60"
            connection_strength = "Strong"
        elif timeout > 0:
            status = "Warning"
            status_color = "#F39C12"
            connection_strength = "Weak"
        else:
            status = "Disconnected"
            status_color = "#E74C3C"
            connection_strength = "Lost"
        
        # Create popup window
        popup = customtkinter.CTkToplevel(self)
        popup.title(f"{bue_name} - Device Details")
        popup.geometry("480x580")
        popup.resizable(False, False)
        
        # Make popup modal and center it
        popup.transient(self)
        
        # Center the popup
        popup.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (480 // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (580 // 2)
        popup.geometry(f"480x580+{x}+{y}")
        
        # Set grab after window is positioned and visible
        popup.after(100, popup.grab_set)
        
        # Main content frame
        main_frame = customtkinter.CTkFrame(popup, corner_radius=0, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Header section
        header_frame = customtkinter.CTkFrame(main_frame, corner_radius=8, fg_color=("#F8F9FA", "gray18"))
        header_frame.pack(fill="x", padx=15, pady=(15, 10))
        
        # Device name and ID
        title_label = customtkinter.CTkLabel(
            header_frame,
            text=f"{bue_name}",
            font=customtkinter.CTkFont(size=20, weight="bold"),
            text_color=("#2C3E50", "#ECF0F1")
        )
        title_label.pack(pady=(15, 5))
        
        id_label = customtkinter.CTkLabel(
            header_frame,
            text=f"Device ID: {bue_id}",
            font=customtkinter.CTkFont(size=12),
            text_color=("#7F8C8D", "#95A5A6")
        )
        id_label.pack(pady=(0, 15))
        
        # Status section
        status_frame = customtkinter.CTkFrame(main_frame, corner_radius=8, fg_color=("#FFFFFF", "gray20"))
        status_frame.pack(fill="x", padx=15, pady=5)
        
        status_title = customtkinter.CTkLabel(
            status_frame,
            text="Connection Status",
            font=customtkinter.CTkFont(size=14, weight="bold"),
            text_color=("#2C3E50", "#ECF0F1")
        )
        status_title.pack(pady=(15, 10))
        
        # Status indicator
        status_indicator = customtkinter.CTkFrame(status_frame, corner_radius=6, fg_color=status_color)
        status_indicator.pack(pady=(0, 10))
        
        status_text = customtkinter.CTkLabel(
            status_indicator,
            text=f"{status} - {connection_strength}",
            font=customtkinter.CTkFont(size=12, weight="bold"),
            text_color="#FFFFFF"
        )
        status_text.pack(padx=15, pady=8)
        
        # Timeout info
        timeout_label = customtkinter.CTkLabel(
            status_frame,
            text=f"Last Response: {timeout} seconds ago",
            font=customtkinter.CTkFont(size=11),
            text_color=("#7F8C8D", "#95A5A6")
        )
        timeout_label.pack(pady=(0, 15))
        
        # Location section
        location_frame = customtkinter.CTkFrame(main_frame, corner_radius=8, fg_color=("#FFFFFF", "gray20"))
        location_frame.pack(fill="x", padx=15, pady=5)
        
        location_title = customtkinter.CTkLabel(
            location_frame,
            text="Geographic Location",
            font=customtkinter.CTkFont(size=14, weight="bold"),
            text_color=("#2C3E50", "#ECF0F1")
        )
        location_title.pack(pady=(15, 10))
        
        coord_text = f"Latitude: {coordinates[0]:.6f}\nLongitude: {coordinates[1]:.6f}"
        coord_label = customtkinter.CTkLabel(
            location_frame,
            text=coord_text,
            font=customtkinter.CTkFont(size=12),
            text_color=("#34495E", "#BDC3C7")
        )
        coord_label.pack(pady=(0, 15))
        
        # Test status section
        test_frame = customtkinter.CTkFrame(main_frame, corner_radius=8, fg_color=("#FFFFFF", "gray20"))
        test_frame.pack(fill="x", padx=15, pady=5)
        
        test_title = customtkinter.CTkLabel(
            test_frame,
            text="Test Status",
            font=customtkinter.CTkFont(size=14, weight="bold"),
            text_color=("#2C3E50", "#ECF0F1")
        )
        test_title.pack(pady=(15, 10))
        
        test_status_text = "Currently Running Tests" if is_testing else "Idle - No Active Tests"
        test_color = "#3A8EBA" if is_testing else "#95A5A6"
        
        test_indicator = customtkinter.CTkFrame(test_frame, corner_radius=6, fg_color=test_color)
        test_indicator.pack(pady=(0, 15))
        
        test_label = customtkinter.CTkLabel(
            test_indicator,
            text=test_status_text,
            font=customtkinter.CTkFont(size=12, weight="bold"),
            text_color="#FFFFFF"
        )
        test_label.pack(padx=15, pady=8)
        
        # Actions section
        actions_frame = customtkinter.CTkFrame(main_frame, corner_radius=8, fg_color=("#F8F9FA", "gray18"))
        actions_frame.pack(fill="x", padx=15, pady=(5, 15))
        
        actions_title = customtkinter.CTkLabel(
            actions_frame,
            text="Device Actions",
            font=customtkinter.CTkFont(size=14, weight="bold"),
            text_color=("#2C3E50", "#ECF0F1")
        )
        actions_title.pack(pady=(15, 10))
        
        # Action buttons
        button_frame = customtkinter.CTkFrame(actions_frame, fg_color="transparent")
        button_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        # First row of buttons
        button_row1 = customtkinter.CTkFrame(button_frame, fg_color="transparent")
        button_row1.pack(fill="x", pady=(0, 8))
        
        ping_btn = customtkinter.CTkButton(
            button_row1,
            text="Ping Device",
            command=lambda: [popup.destroy(), self.ping_bue(bue_name)],
            width=100,
            height=32,
            font=customtkinter.CTkFont(size=11),
            fg_color=("#3A8EBA", "#2E6B8A"),
            hover_color=("#2E6B8A", "#1F4A5C")
        )
        ping_btn.pack(side="left", padx=(0, 8))
        
        if is_testing:
            test_btn = customtkinter.CTkButton(
                button_row1,
                text="Stop Test",
                command=lambda: [popup.destroy(), self.stop_test_bue(bue_name)],
                width=100,
                height=32,
                font=customtkinter.CTkFont(size=11),
                fg_color=("#E74C3C", "#C0392B"),
                hover_color=("#C0392B", "#A93226")
            )
        else:
            test_btn = customtkinter.CTkButton(
                button_row1,
                text="Start Test",
                command=lambda: [popup.destroy(), self.start_test_bue(bue_name)],
                width=100,
                height=32,
                font=customtkinter.CTkFont(size=11),
                fg_color=("#27AE60", "#229A54"),
                hover_color=("#229A54", "#1E8B47")
            )
        test_btn.pack(side="left", padx=4)
        
        disconnect_btn = customtkinter.CTkButton(
            button_row1,
            text="Disconnect",
            command=lambda: [popup.destroy(), self.disconnect_bue(bue_name)],
            width=100,
            height=32,
            font=customtkinter.CTkFont(size=11),
            fg_color=("#95A5A6", "#7F8C8D"),
            hover_color=("#7F8C8D", "#6C7B7D")
        )
        disconnect_btn.pack(side="left", padx=(8, 0))
        
        # Close button
        close_button = customtkinter.CTkButton(
            button_frame,
            text="Close Window",
            command=popup.destroy,
            width=320,
            height=36,
            font=customtkinter.CTkFont(size=12, weight="bold"),
            fg_color=("#34495E", "#2C3E50"),
            hover_color=("#2C3E50", "#1B2631"),
            corner_radius=6
        )
        close_button.pack(pady=(8, 0))

        self.update_dashboard()

    def create_table(self, title, columns, frame):
        # Create main container with professional styling
        table_container = customtkinter.CTkFrame(frame, corner_radius=8, fg_color=("#FFFFFF", "gray20"), border_width=1, border_color=("#E3E6EA", "gray25"))
        table_container.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        
        # Professional title label with background
        title_frame = customtkinter.CTkFrame(table_container, corner_radius=6, fg_color=("#F8F9FA", "gray18"), height=40)
        title_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 0))
        title_frame.grid_propagate(False)
        
        title_label = customtkinter.CTkLabel(
            title_frame, 
            text=title, 
            font=customtkinter.CTkFont(size=15, weight="bold"),
            text_color=("#2C3E50", "#ECF0F1")
        )
        title_label.pack(expand=True, fill="both", padx=15, pady=8)
        
        # Configure grid
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        table_container.grid_rowconfigure(1, weight=1)
        table_container.grid_columnconfigure(0, weight=1)
        
        # Create styled treeview frame
        tree_frame = customtkinter.CTkFrame(table_container, fg_color="transparent")
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Create professional treeview
        style = ttk.Style()
        style.theme_use("clam")
        
        # Configure treeview styling
        style.configure("Custom.Treeview", 
                       background="#FFFFFF",
                       foreground="#2C3E50",
                       fieldbackground="#FFFFFF",
                       borderwidth=0,
                       relief="flat",
                       rowheight=35)
        
        style.configure("Custom.Treeview.Heading",
                       background="#F8F9FA",
                       foreground="#2C3E50",
                       font=("", 12, "bold"),
                       borderwidth=1,
                       relief="solid")
        
        style.map("Custom.Treeview",
                 background=[('selected', '#3A8EBA')],
                 foreground=[('selected', 'white')])
        
        tree = ttk.Treeview(
            tree_frame, 
            columns=columns, 
            show="headings", 
            height=8,
            style="Custom.Treeview"
        )
        
        # Professional column configuration
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, anchor="center", width=120, minwidth=80)
        
        # Bind right-click event for context menu
        tree.bind("<Button-3>", lambda event: self.show_context_menu(event, tree, title))
        
        # Professional scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        # Grid layout
        tree.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        scrollbar.grid(row=0, column=1, sticky="ns")
        
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
        self.update_map_markers()
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
            state = "Testing" if bue in getattr(self.base_station, 'testing_bues', []) else "Idle"
            timeout = self.base_station.bue_timeout_tracker.get(bue, 0)
            if timeout >= TIMEOUT / 2:
                status = "Connected"
            elif timeout > 0:
                status = "Warning"
            else:
                status = "Disconnected"
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
        
        # Remove marker from map
        self.remove_bue_marker(bue)

        self.update_dashboard()

    def on_closing(self, event=0):
        self.destroy()
        self.base_station.EXIT = True

    def view_bue_details(self, bue_name):
        """View details for a specific bUE"""
        print(f"Viewing details for {bue_name}")
        # Add your details view logic here

    def ping_bue(self, bue_name):
        """Ping a specific bUE"""
        print(f"Pinging {bue_name}")
        # Add actual ping logic here

    def start_test_bue(self, bue_name):
        """Start test on a specific bUE"""
        print(f"Starting test on {bue_name}")
        bue_id = int(bUEs_inverted[bue_name])
        if bue_id not in getattr(self.base_station, 'testing_bues', []):
            if not hasattr(self.base_station, 'testing_bues'):
                self.base_station.testing_bues = []
            self.base_station.testing_bues.append(bue_id)

    def stop_test_bue(self, bue_name):
        """Stop test on a specific bUE"""
        print(f"Stopping test on {bue_name}")
        bue_id = int(bUEs_inverted[bue_name])
        if hasattr(self.base_station, 'testing_bues') and bue_id in self.base_station.testing_bues:
            self.base_station.testing_bues.remove(bue_id)

class TestConfigurationWindow(customtkinter.CTkToplevel):
    """Multi-page test configuration window"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.parent = parent
        self.title("Base Station Test Configuration")
        self.geometry("950x700")
        self.resizable(True, True)
        
        # Make window modal
        self.transient(parent)
        
        # Center the window
        self.center_window()
        
        # Set grab after window is visible
        self.after(100, self.grab_set)
        
        # Configure grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Create sidebar for navigation
        self.create_sidebar()
        
        # Initialize data
        self.selected_bues = {}
        self.test_configs = {}
        
        # Create main content area
        self.create_main_content()
        
        # Initialize with first page
        self.current_page = "bue_selection"
        self.show_page("bue_selection")
        
    def center_window(self):
        """Center the window on the parent"""
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (width // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (height // 2)
        self.geometry(f"+{x}+{y}")
    
    def create_sidebar(self):
        """Create navigation sidebar"""
        self.sidebar = customtkinter.CTkFrame(self, width=220, corner_radius=0, fg_color=("#F8F9FA", "gray15"))
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        
        # Title
        title_label = customtkinter.CTkLabel(
            self.sidebar,
            text="Test Configuration",
            font=customtkinter.CTkFont(size=16, weight="bold"),
            text_color=("#2C3E50", "#ECF0F1")
        )
        title_label.pack(pady=(25, 35), padx=20)
        
        # Navigation buttons
        self.nav_buttons = {}
        
        pages = [
            ("bue_selection", "1. Select Devices", None),
            ("time_config", "2. Time Settings", None),
            ("test_config", "3. Test Parameters", None),
            ("review", "4. Review & Execute", None)
        ]
        
        for page_id, title, icon in pages:
            btn = customtkinter.CTkButton(
                self.sidebar,
                text=title,
                command=lambda p=page_id: self.show_page(p),
                width=180,
                height=40,
                font=customtkinter.CTkFont(size=12, weight="normal"),
                fg_color="transparent",
                text_color=("#2C3E50", "#BDC3C7"),
                hover_color=("#E8F4FD", "#34495E"),
                anchor="w",
                corner_radius=4
            )
            btn.pack(pady=6, padx=20, fill="x")
            self.nav_buttons[page_id] = btn
    
    def create_main_content(self):
        """Create main content area"""
        self.main_frame = customtkinter.CTkFrame(self, corner_radius=0, fg_color=("#FFFFFF", "gray12"))
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 0))
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        
        # Create frames for each page
        self.pages = {}
        self.create_bue_selection_page()
        self.create_time_config_page()
        self.create_test_config_page()
        self.create_review_page()
    
    def create_bue_selection_page(self):
        """Create bUE selection page"""
        page = customtkinter.CTkFrame(self.main_frame, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)
        
        # Page title
        title = customtkinter.CTkLabel(
            page,
            text="Select Test Devices",
            font=customtkinter.CTkFont(size=22, weight="bold"),
            text_color=("#2C3E50", "#ECF0F1")
        )
        title.grid(row=0, column=0, pady=(30, 20), sticky="w", padx=30)
        
        # Content frame
        content = customtkinter.CTkFrame(page, corner_radius=8, fg_color=("#F8F9FA", "gray20"), border_width=1, border_color=("#E3E6EA", "gray25"))
        content.grid(row=1, column=0, sticky="nsew", padx=30, pady=(0, 30))
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(1, weight=1)
        
        # Instructions
        instructions = customtkinter.CTkLabel(
            content,
            text="Select the devices you want to include in the test configuration:",
            font=customtkinter.CTkFont(size=13),
            text_color=("#34495E", "#BDC3C7")
        )
        instructions.grid(row=0, column=0, pady=(20, 10), padx=20, sticky="w")
        
        # Scrollable bUE list
        self.bue_list_frame = customtkinter.CTkScrollableFrame(content, fg_color="transparent")
        self.bue_list_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.bue_list_frame.grid_columnconfigure(0, weight=1)
        
        self.pages["bue_selection"] = page
    
    def create_time_config_page(self):
        """Create time configuration page"""
        page = customtkinter.CTkFrame(self.main_frame, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        
        # Page title
        title = customtkinter.CTkLabel(
            page,
            text="Test Execution Time",
            font=customtkinter.CTkFont(size=22, weight="bold"),
            text_color=("#2C3E50", "#ECF0F1")
        )
        title.grid(row=0, column=0, pady=(30, 20), sticky="w", padx=30)
        
        # Content frame
        content = customtkinter.CTkFrame(page, corner_radius=8, fg_color=("#F8F9FA", "gray20"), border_width=1, border_color=("#E3E6EA", "gray25"))
        content.grid(row=1, column=0, sticky="ew", padx=30, pady=(0, 30))
        content.grid_columnconfigure(1, weight=1)
        
        # Time configuration
        from datetime import datetime
        now = datetime.now()
        
        time_label = customtkinter.CTkLabel(
            content,
            text="Execution Schedule:",
            font=customtkinter.CTkFont(size=15, weight="bold"),
            text_color=("#2C3E50", "#ECF0F1")
        )
        time_label.grid(row=0, column=0, columnspan=4, pady=(20, 15), padx=20, sticky="w")
        
        # Time inputs with professional styling
        customtkinter.CTkLabel(content, text="Hour:", font=customtkinter.CTkFont(size=12, weight="bold"), text_color=("#34495E", "#BDC3C7")).grid(
            row=1, column=0, padx=(20, 8), pady=12, sticky="e")
        self.hour_var = tk.StringVar(value=str(now.hour).zfill(2))
        self.hour_entry = customtkinter.CTkEntry(
            content, 
            textvariable=self.hour_var, 
            width=65, 
            height=32,
            justify="center",
            font=customtkinter.CTkFont(size=12, weight="bold"),
            corner_radius=6,
            border_width=2,
            border_color=("#BDC3C7", "#7F8C8D"),
            fg_color=("#FFFFFF", "gray25")
        )
        self.hour_entry.grid(row=1, column=1, padx=5, pady=12)
        
        customtkinter.CTkLabel(content, text="Minute:", font=customtkinter.CTkFont(size=12, weight="bold"), text_color=("#34495E", "#BDC3C7")).grid(
            row=1, column=2, padx=8, pady=12, sticky="e")
        self.minute_var = tk.StringVar(value=str(now.minute).zfill(2))
        self.minute_entry = customtkinter.CTkEntry(
            content, 
            textvariable=self.minute_var, 
            width=65, 
            height=32,
            justify="center",
            font=customtkinter.CTkFont(size=12, weight="bold"),
            corner_radius=6,
            border_width=2,
            border_color=("#BDC3C7", "#7F8C8D"),
            fg_color=("#FFFFFF", "gray25")
        )
        self.minute_entry.grid(row=1, column=3, padx=5, pady=12)
        
        customtkinter.CTkLabel(content, text="Second:", font=customtkinter.CTkFont(size=12, weight="bold"), text_color=("#34495E", "#BDC3C7")).grid(
            row=1, column=4, padx=8, pady=12, sticky="e")
        self.second_var = tk.StringVar(value=str(now.second).zfill(2))
        self.second_entry = customtkinter.CTkEntry(
            content, 
            textvariable=self.second_var, 
            width=65, 
            height=32,
            justify="center",
            font=customtkinter.CTkFont(size=12, weight="bold"),
            corner_radius=6,
            border_width=2,
            border_color=("#BDC3C7", "#7F8C8D"),
            fg_color=("#FFFFFF", "gray25")
        )
        self.second_entry.grid(row=1, column=5, padx=(5, 20), pady=12)
        
        # Options
        options_label = customtkinter.CTkLabel(
            content,
            text="Execution Options:",
            font=customtkinter.CTkFont(size=15, weight="bold"),
            text_color=("#2C3E50", "#ECF0F1")
        )
        options_label.grid(row=2, column=0, columnspan=6, pady=(20, 10), padx=20, sticky="w")
        
        self.start_now_var = customtkinter.BooleanVar(value=True)
        start_now_cb = customtkinter.CTkCheckBox(
            content,
            text="Execute test immediately upon confirmation",
            variable=self.start_now_var,
            font=customtkinter.CTkFont(size=12),
            text_color=("#34495E", "#BDC3C7"),
            corner_radius=4,
            border_width=2,
            fg_color=("#3A8EBA", "#2E6B8A"),
            hover_color=("#2E6B8A", "#1F4A5C"),
            border_color=("#BDC3C7", "#7F8C8D"),
            checkmark_color=("#FFFFFF", "#FFFFFF")
        )
        start_now_cb.grid(row=3, column=0, columnspan=6, pady=8, padx=20, sticky="w")
        
        self.scheduled_var = customtkinter.BooleanVar()
        scheduled_cb = customtkinter.CTkCheckBox(
            content,
            text="Schedule test for specified time",
            variable=self.scheduled_var,
            font=customtkinter.CTkFont(size=12),
            text_color=("#34495E", "#BDC3C7"),
            corner_radius=4,
            border_width=2,
            fg_color=("#3A8EBA", "#2E6B8A"),
            hover_color=("#2E6B8A", "#1F4A5C"),
            border_color=("#BDC3C7", "#7F8C8D"),
            checkmark_color=("#FFFFFF", "#FFFFFF")
        )
        scheduled_cb.grid(row=4, column=0, columnspan=6, pady=(8, 20), padx=20, sticky="w")
        
        self.pages["time_config"] = page
    
    def create_test_config_page(self):
        """Create test configuration page"""
        page = customtkinter.CTkFrame(self.main_frame, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)
        
        # Page title
        title = customtkinter.CTkLabel(
            page,
            text="Test Parameters Configuration",
            font=customtkinter.CTkFont(size=22, weight="bold"),
            text_color=("#2C3E50", "#ECF0F1")
        )
        title.grid(row=0, column=0, pady=(30, 20), sticky="w", padx=30)
        
        # Content frame
        content = customtkinter.CTkFrame(page, corner_radius=8, fg_color=("#F8F9FA", "gray20"), border_width=1, border_color=("#E3E6EA", "gray25"))
        content.grid(row=1, column=0, sticky="nsew", padx=30, pady=(0, 30))
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(1, weight=1)
        
        # Instructions
        instructions = customtkinter.CTkLabel(
            content,
            text="Configure test parameters for each selected device:",
            font=customtkinter.CTkFont(size=13),
            text_color=("#34495E", "#BDC3C7")
        )
        instructions.grid(row=0, column=0, pady=(20, 10), padx=20, sticky="w")
        
        # Scrollable test config list
        self.test_config_frame = customtkinter.CTkScrollableFrame(content, fg_color="transparent")
        self.test_config_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.test_config_frame.grid_columnconfigure(0, weight=1)
        
        self.pages["test_config"] = page
    
    def create_review_page(self):
        """Create review and start page"""
        page = customtkinter.CTkFrame(self.main_frame, fg_color="transparent")
        page.grid_columnconfigure(0, weight=1)
        page.grid_rowconfigure(1, weight=1)
        
        # Page title
        title = customtkinter.CTkLabel(
            page,
            text="Configuration Review",
            font=customtkinter.CTkFont(size=22, weight="bold"),
            text_color=("#2C3E50", "#ECF0F1")
        )
        title.grid(row=0, column=0, pady=(30, 20), sticky="w", padx=30)
        
        # Content frame
        content = customtkinter.CTkFrame(page, corner_radius=8, fg_color=("#F8F9FA", "gray20"), border_width=1, border_color=("#E3E6EA", "gray25"))
        content.grid(row=1, column=0, sticky="nsew", padx=30, pady=(0, 30))
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)
        
        # Review area
        self.review_text = customtkinter.CTkTextbox(
            content,
            font=customtkinter.CTkFont(size=12),
            wrap="word"
        )
        self.review_text.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
        # Action buttons
        button_frame = customtkinter.CTkFrame(content, fg_color="transparent")
        button_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))
        button_frame.grid_columnconfigure((0, 1), weight=1)
        
        cancel_btn = customtkinter.CTkButton(
            button_frame,
            text="Cancel",
            command=self.destroy,
            width=130,
            height=38,
            font=customtkinter.CTkFont(size=13),
            fg_color=("#95A5A6", "#7F8C8D"),
            hover_color=("#7F8C8D", "#95A5A6"),
            corner_radius=4
        )
        cancel_btn.grid(row=0, column=0, padx=(0, 15))
        
        start_btn = customtkinter.CTkButton(
            button_frame,
            text="Execute Test",
            command=self.start_test,
            width=130,
            height=38,
            font=customtkinter.CTkFont(size=13, weight="bold"),
            fg_color=("#3A8EBA", "#2E6B8A"),
            hover_color=("#2E6B8A", "#1F4A5C"),
            corner_radius=4
        )
        start_btn.grid(row=0, column=1, padx=(15, 0))
        
        self.pages["review"] = page
    
    def show_page(self, page_id):
        """Show specified page and update navigation"""
        # Hide all pages
        for page in self.pages.values():
            page.grid_remove()
        
        # Show selected page
        if page_id in self.pages:
            self.pages[page_id].grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
            self.current_page = page_id
            
            # Update navigation button styles
            for btn_id, btn in self.nav_buttons.items():
                if btn_id == page_id:
                    btn.configure(
                        fg_color=("#3A8EBA", "#2E6B8A"),
                        text_color=("#FFFFFF", "#FFFFFF")
                    )
                else:
                    btn.configure(
                        fg_color="transparent",
                        text_color=("#2C3E50", "#BDC3C7")
                    )
            
            # Update page content based on current page
            if page_id == "bue_selection":
                self.populate_bue_selection()
            elif page_id == "test_config":
                self.populate_test_config()
            elif page_id == "review":
                self.populate_review()
    
    def populate_bue_selection(self):
        """Populate bUE selection checkboxes"""
        # Clear existing
        for widget in self.bue_list_frame.winfo_children():
            widget.destroy()
        
        if not self.parent.base_station.connected_bues:
            no_bues = customtkinter.CTkLabel(
                self.bue_list_frame,
                text="No devices currently connected to the base station",
                font=customtkinter.CTkFont(size=13),
                text_color=("#7F8C8D", "#95A5A6")
            )
            no_bues.pack(pady=30)
            return
        
        for i, bue in enumerate(self.parent.base_station.connected_bues):
            bue_name = bUEs[str(bue)]
            
            # Create professional bUE frame
            bue_frame = customtkinter.CTkFrame(self.bue_list_frame, corner_radius=8, fg_color=("#FFFFFF", "gray25"), border_width=1, border_color=("#E3E6EA", "gray30"))
            bue_frame.pack(fill="x", pady=8, padx=15)
            
            # Inner frame for better layout
            inner_frame = customtkinter.CTkFrame(bue_frame, fg_color="transparent")
            inner_frame.pack(fill="x", padx=15, pady=12)
            
            # Checkbox and device info
            if bue not in self.selected_bues:
                self.selected_bues[bue] = customtkinter.BooleanVar()
            
            # Professional checkbox styling
            checkbox = customtkinter.CTkCheckBox(
                inner_frame,
                text="",
                variable=self.selected_bues[bue],
                width=20,
                height=20,
                corner_radius=4,
                border_width=2,
                fg_color=("#3A8EBA", "#2E6B8A"),
                hover_color=("#2E6B8A", "#1F4A5C"),
                border_color=("#BDC3C7", "#7F8C8D"),
                checkmark_color=("#FFFFFF", "#FFFFFF")
            )
            checkbox.pack(side="left", padx=(0, 12))
            
            # Device name with professional styling
            device_label = customtkinter.CTkLabel(
                inner_frame,
                text=f"{bue_name}",
                font=customtkinter.CTkFont(size=14, weight="bold"),
                text_color=("#2C3E50", "#ECF0F1")
            )
            device_label.pack(side="left")
            
            # Status info with professional indicators
            timeout = self.parent.base_station.bue_timeout_tracker.get(bue, 0)
            if timeout >= TIMEOUT / 2:
                status = "Connected"
                status_color = ("#27AE60", "#2ECC71")
                status_bg = ("#E8F5E8", "#1A3A1A")
            elif timeout > 0:
                status = "Warning"
                status_color = ("#F39C12", "#E67E22")
                status_bg = ("#FFF3E0", "#3A2A00")
            else:
                status = "Disconnected"
                status_color = ("#E74C3C", "#C0392B")
                status_bg = ("#FFEBEE", "#3A1A1A")
            
            # Status badge
            status_frame = customtkinter.CTkFrame(
                inner_frame,
                corner_radius=12,
                fg_color=status_bg,
                border_width=1,
                border_color=status_color
            )
            status_frame.pack(side="right")
            
            status_label = customtkinter.CTkLabel(
                status_frame,
                text=status,
                font=customtkinter.CTkFont(size=11, weight="bold"),
                text_color=status_color
            )
            status_label.pack(padx=10, pady=4)
    
    def populate_test_config(self):
        """Populate test configuration for selected bUEs"""
        # Clear existing
        for widget in self.test_config_frame.winfo_children():
            widget.destroy()
        
        selected_bues = [bue for bue, var in self.selected_bues.items() if var.get()]
        
        if not selected_bues:
            no_selection = customtkinter.CTkLabel(
                self.test_config_frame,
                text="No devices selected. Return to page 1 to select devices.",
                font=customtkinter.CTkFont(size=13),
                text_color=("#7F8C8D", "#95A5A6")
            )
            no_selection.pack(pady=30)
            return
        
        # Mock test files
        test_files = ["test_script_1.py", "test_script_2.py", "data_collection.py", "performance_test.py"]
        
        for bue in selected_bues:
            bue_name = bUEs[str(bue)]
            
            # Create professional config frame for each device
            config_frame = customtkinter.CTkFrame(self.test_config_frame, corner_radius=8, fg_color=("#FFFFFF", "gray25"), border_width=1, border_color=("#E3E6EA", "gray30"))
            config_frame.pack(fill="x", pady=12, padx=15)
            
            # Device name with professional header
            header_frame = customtkinter.CTkFrame(config_frame, corner_radius=6, fg_color=("#F8F9FA", "gray18"))
            header_frame.pack(fill="x", padx=12, pady=(12, 8))
            
            name_label = customtkinter.CTkLabel(
                header_frame,
                text=f"{bue_name}",
                font=customtkinter.CTkFont(size=15, weight="bold"),
                text_color=("#2C3E50", "#ECF0F1")
            )
            name_label.pack(pady=8)
            
            # File selection with professional styling
            file_frame = customtkinter.CTkFrame(config_frame, fg_color="transparent")
            file_frame.pack(fill="x", padx=15, pady=8)
            
            customtkinter.CTkLabel(
                file_frame, 
                text="Test Script:", 
                width=100, 
                font=customtkinter.CTkFont(size=12, weight="bold"),
                text_color=("#34495E", "#BDC3C7")
            ).pack(side="left", anchor="w")
            
            if bue not in self.test_configs:
                self.test_configs[bue] = {}
            
            if 'file_var' not in self.test_configs[bue]:
                self.test_configs[bue]['file_var'] = customtkinter.StringVar(value=test_files[0])
            
            file_menu = customtkinter.CTkOptionMenu(
                file_frame,
                variable=self.test_configs[bue]['file_var'],
                values=test_files,
                width=280,
                height=32,
                corner_radius=6,
                fg_color=("#FFFFFF", "gray25"),
                button_color=("#3A8EBA", "#2E6B8A"),
                button_hover_color=("#2E6B8A", "#1F4A5C"),
                dropdown_fg_color=("#FFFFFF", "gray20"),
                font=customtkinter.CTkFont(size=12)
            )
            file_menu.pack(side="left", padx=(15, 0))
            
            # Parameters with professional styling
            param_frame = customtkinter.CTkFrame(config_frame, fg_color="transparent")
            param_frame.pack(fill="x", padx=15, pady=(8, 15))
            
            customtkinter.CTkLabel(
                param_frame, 
                text="Parameters:", 
                width=100,
                font=customtkinter.CTkFont(size=12, weight="bold"),
                text_color=("#34495E", "#BDC3C7")
            ).pack(side="left", anchor="w")
            
            if 'param_var' not in self.test_configs[bue]:
                self.test_configs[bue]['param_var'] = customtkinter.StringVar()
            
            param_entry = customtkinter.CTkEntry(
                param_frame,
                textvariable=self.test_configs[bue]['param_var'],
                placeholder_text="Enter parameters separated by spaces",
                width=280,
                height=32,
                corner_radius=6,
                border_width=2,
                border_color=("#BDC3C7", "#7F8C8D"),
                fg_color=("#FFFFFF", "gray25"),
                font=customtkinter.CTkFont(size=12)
            )
            param_entry.pack(side="left", padx=(15, 0))
    
    def populate_review(self):
        """Populate review information"""
        self.review_text.delete("1.0", "end")
        
        # Selected bUEs
        selected_bues = [bue for bue, var in self.selected_bues.items() if var.get()]
        
        review_content = "TEST CONFIGURATION SUMMARY\n"
        review_content += "=" * 60 + "\n\n"
        
        if not selected_bues:
            review_content += "ERROR: No devices selected for testing.\n"
            review_content += "Please return to page 1 to select devices.\n"
        else:
            review_content += f"SELECTED DEVICES ({len(selected_bues)}):\n"
            for bue in selected_bues:
                bue_name = bUEs[str(bue)]
                review_content += f"   • {bue_name}\n"
            
            review_content += "\nEXECUTION SCHEDULE:\n"
            if hasattr(self, 'start_now_var') and self.start_now_var.get():
                review_content += "   • Execute immediately upon confirmation\n"
            else:
                try:
                    hour = self.hour_var.get()
                    minute = self.minute_var.get()
                    second = self.second_var.get()
                    review_content += f"   • Scheduled execution at {hour}:{minute}:{second}\n"
                except:
                    review_content += "   • ERROR: Invalid time configuration\n"
            
            review_content += "\nTEST CONFIGURATION:\n"
            for bue in selected_bues:
                bue_name = bUEs[str(bue)]
                if bue in self.test_configs:
                    file_name = self.test_configs[bue]['file_var'].get()
                    params = self.test_configs[bue]['param_var'].get()
                    review_content += f"   • {bue_name}:\n"
                    review_content += f"     - Script: {file_name}\n"
                    review_content += f"     - Parameters: {params if params else 'None'}\n"
                else:
                    review_content += f"   • {bue_name}: Configuration incomplete\n"
        
        self.review_text.insert("1.0", review_content)
    
    def start_test(self):
        """Start the configured test"""
        selected_bues = [bue for bue, var in self.selected_bues.items() if var.get()]
        
        if not selected_bues:
            return
        
        # Build test configuration
        bue_test = {}
        bue_params = {}
        
        for bue in selected_bues:
            if bue in self.test_configs:
                bue_test[bue] = self.test_configs[bue]['file_var'].get()
                bue_params[bue] = self.test_configs[bue]['param_var'].get()
        
        # Get start time
        try:
            from datetime import datetime
            if hasattr(self, 'start_now_var') and self.start_now_var.get():
                start_time = datetime.now()
            else:
                hour = int(self.hour_var.get())
                minute = int(self.minute_var.get())
                second = int(self.second_var.get())
                start_time = datetime.now().replace(hour=hour, minute=minute, second=second, microsecond=0)
        except ValueError:
            print("Invalid time format")
            return
        
        print(f"Starting test:")
        print(f"  Selected bUEs: {[bUEs[str(bue)] for bue in selected_bues]}")
        print(f"  Start time: {start_time}")
        print(f"  Test configs: {bue_test}")
        print(f"  Parameters: {bue_params}")
        
        # Close window
        self.destroy()
        
        # Uncomment when ready:
        # send_test(self.parent.base_station, bue_test, start_time, bue_params)