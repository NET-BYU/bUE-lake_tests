"""
base_station_gui.py
Ty Young

A comprehensive GUI for the base station using tkinter.
This GUI provides all the functionality of main_ui.py but with a graphical interface.

Features:
- Connected bUEs menu with status indicators
- Right-click context menu for bUE operations (disconnect, reload, restart, open logs)
- Interactive map showing bUE locations
- Custom markers that can be paired with bUEs
- Color-coded proximity indicators (changes when bUEs are within 10-20m of markers)
- Coordinates table
- Distance table between bUEs
- Received messages table
- Base station log file viewer
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import time
import os
import subprocess
import platform
from datetime import datetime, date, timedelta
from loguru import logger
import math

# Try to import TkinterMapView, fallback to canvas if not available
try:
    import tkintermapview
    from PIL import Image, ImageDraw, ImageTk

    MAP_VIEW_AVAILABLE = True
    print("TkinterMapView is available - using interactive map")
except ImportError:
    MAP_VIEW_AVAILABLE = False
    print("TkinterMapView not available - using fallback canvas map")

from base_station_main import Base_Station_Main

# from constants import bUEs, TIMEOUT


class BaseStationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Base Station Control Panel")
        self.root.geometry("1400x900")

        # Initialize base station
        self.base_station = None
        self.update_thread = None
        self.running = False

        # Custom markers for the map
        self.custom_markers = {}  # {marker_id: {'name': str, 'lat': float, 'lon': float, 'paired_bue': int}}
        self.marker_counter = 0

        # Map configuration
        self.use_interactive_map = MAP_VIEW_AVAILABLE
        self.map_widget = None  # Will hold TkinterMapView or canvas
        self.map_markers = {}  # Track markers on the interactive map
        self.last_bue_positions = {}  # Track last known bUE positions to detect changes
        self.map_auto_positioned = False  # Track if we've done initial positioning

        # Setup GUI
        self.setup_gui()

        # Start base station
        self.start_base_station()

    def create_circle_marker_icon(self, color, size=20):
        """Create a custom circular marker icon similar to canvas map"""
        if not MAP_VIEW_AVAILABLE:
            return None

        try:
            # Create image with transparent background
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # Draw outer circle (border)
            border_color = "darkblue" if color in ["blue", "green"] else "darkred"
            draw.ellipse([0, 0, size - 1, size - 1], fill=color, outline=border_color, width=2)

            # Convert to PhotoImage for tkinter
            return ImageTk.PhotoImage(img)
        except Exception as e:
            logger.error(f"Error creating circle marker icon: {e}")
            return None

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_gui(self):
        """Setup the main GUI layout with all panels always visible"""
        # Increase window size to accommodate all panels
        self.root.geometry("1600x1000")

        # Create main container with grid layout
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Configure grid weights for responsive resizing
        main_frame.grid_columnconfigure(0, weight=1)  # Left column
        main_frame.grid_columnconfigure(1, weight=2)  # Middle column (map)
        main_frame.grid_columnconfigure(2, weight=1)  # Right column
        main_frame.grid_rowconfigure(0, weight=1)  # Top row
        main_frame.grid_rowconfigure(1, weight=1)  # Bottom row

        # Left panel - bUE list and controls
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 2))
        self.setup_left_panel(left_frame)

        # Middle top panel - Map
        map_frame = ttk.LabelFrame(main_frame, text="bUE Location Map")
        map_frame.grid(row=0, column=1, sticky="nsew", padx=2)
        self.setup_map_view(map_frame)

        # Middle bottom panel - Messages
        messages_frame = ttk.LabelFrame(main_frame, text="Messages")
        messages_frame.grid(row=1, column=1, sticky="nsew", padx=2, pady=(2, 0))
        self.setup_messages_view(messages_frame)

        # Right panel - Data tables
        tables_frame = ttk.Frame(main_frame)
        tables_frame.grid(row=0, column=2, rowspan=2, sticky="nsew", padx=(2, 0))
        self.setup_tables_view(tables_frame)

        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Initializing...")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def setup_left_panel(self, parent):
        """Setup the left panel with bUE list and controls"""
        # bUE List Frame
        bue_frame = ttk.LabelFrame(parent, text="Connected bUEs")
        bue_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # bUE Treeview
        self.bue_tree = ttk.Treeview(bue_frame, columns=("status", "ping"), show="tree headings")
        self.bue_tree.heading("#0", text="bUE ID")
        self.bue_tree.heading("status", text="State")
        self.bue_tree.heading("ping", text="Missed Pings")

        self.bue_tree.column("#0", width=100)
        self.bue_tree.column("status", width=100)
        self.bue_tree.column("ping", width=100)

        # Scrollbar for treeview
        bue_scrollbar = ttk.Scrollbar(bue_frame, orient=tk.VERTICAL, command=self.bue_tree.yview)
        self.bue_tree.configure(yscrollcommand=bue_scrollbar.set)

        self.bue_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        bue_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind right-click context menu (cross-platform)
        if platform.system() == "Darwin":  # macOS
            self.bue_tree.bind("<Button-2>", self.show_bue_context_menu)  # macOS right-click
            self.bue_tree.bind("<Control-Button-1>", self.show_bue_context_menu)  # macOS Ctrl+click alternative
        else:  # Linux/Windows
            self.bue_tree.bind("<Button-3>", self.show_bue_context_menu)  # Standard right-click

        # Control buttons frame
        control_frame = ttk.LabelFrame(parent, text="Controls")
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        # Test button
        ttk.Button(control_frame, text="Run Test", command=self.run_test).pack(fill=tk.X, pady=2)

        # Cancel test button
        ttk.Button(control_frame, text="Cancel Tests", command=self.cancel_tests).pack(fill=tk.X, pady=2)

        # Open base station log
        ttk.Button(control_frame, text="Open Base Station Log", command=self.open_base_log).pack(fill=tk.X, pady=2)

        # Map controls frame
        map_control_frame = ttk.LabelFrame(parent, text="Map Controls")
        map_control_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(map_control_frame, text="Add Custom Marker", command=self.add_custom_marker).pack(fill=tk.X, pady=2)
        ttk.Button(map_control_frame, text="Manage Markers", command=self.manage_markers).pack(fill=tk.X, pady=2)

        # Map type toggle (only show if both options are available)
        if MAP_VIEW_AVAILABLE:
            self.map_toggle_btn = ttk.Button(map_control_frame, text="Switch to Simple Map", command=self.toggle_map_type)
            self.map_toggle_btn.pack(fill=tk.X, pady=2)

    def setup_map_view(self, parent):
        """Setup the map view with bUE locations and custom markers"""
        # Create container for map
        self.map_container = parent

        # Set up the appropriate map type
        if self.use_interactive_map and MAP_VIEW_AVAILABLE:
            self.setup_interactive_map()
        else:
            self.setup_canvas_map()

        # Map info frame (always present)
        map_info_frame = ttk.Frame(parent)
        map_info_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(map_info_frame, text="Legend:").pack(side=tk.LEFT)
        ttk.Label(map_info_frame, text="🔵 bUE", foreground="blue").pack(side=tk.LEFT, padx=5)
        ttk.Label(map_info_frame, text="📍 Marker", foreground="red").pack(side=tk.LEFT, padx=5)
        ttk.Label(map_info_frame, text="🟢 Close", foreground="green").pack(side=tk.LEFT, padx=5)

        if self.use_interactive_map and MAP_VIEW_AVAILABLE:
            ttk.Label(map_info_frame, text="| Interactive Map Active", foreground="green").pack(side=tk.LEFT, padx=5)
        else:
            ttk.Label(map_info_frame, text="| Simple Map Active", foreground="orange").pack(side=tk.LEFT, padx=5)

    def setup_interactive_map(self):
        """Setup TkinterMapView interactive map"""
        try:
            # Create the map widget
            self.map_widget = tkintermapview.TkinterMapView(self.map_container, width=600, height=400, corner_radius=0)
            self.map_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            # Set a default position (you can change this to your area)
            self.map_widget.set_position(40.2518, -111.6493)  # Provo, Utah
            self.map_widget.set_zoom(10)

            # Clear any existing markers
            self.map_markers = {}

            print("Interactive map initialized successfully")

        except Exception as e:
            print(f"Failed to setup interactive map: {e}")
            logger.error(f"Failed to setup interactive map: {e}")
            # Fallback to canvas map
            self.use_interactive_map = False
            self.setup_canvas_map()

    def setup_canvas_map(self):
        """Setup fallback canvas-based map"""
        # Create canvas map (original implementation)
        self.map_widget = tk.Canvas(self.map_container, bg="lightblue", width=600, height=400)
        self.map_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Bind canvas events
        self.map_widget.bind("<Button-1>", self.on_map_click)
        self.map_widget.bind("<Motion>", self.on_map_hover)

    def toggle_map_type(self):
        """Toggle between interactive map and simple canvas map"""
        if not MAP_VIEW_AVAILABLE:
            messagebox.showinfo("Map Toggle", "TkinterMapView is not available. Cannot switch map types.")
            return

        try:
            # Store current state
            old_use_interactive = self.use_interactive_map

            # Toggle map type
            self.use_interactive_map = not self.use_interactive_map

            # Clear the current map widget
            if hasattr(self, "map_widget") and self.map_widget:
                self.map_widget.destroy()

            # Create new map
            if self.use_interactive_map:
                self.setup_interactive_map()
                if hasattr(self, "map_toggle_btn"):
                    self.map_toggle_btn.config(text="Switch to Simple Map")
            else:
                self.setup_canvas_map()
                if hasattr(self, "map_toggle_btn"):
                    self.map_toggle_btn.config(text="Switch to Interactive Map")

            # Update the map with current data
            self.update_map()

            # Update info text
            for widget in self.map_container.winfo_children():
                if isinstance(widget, ttk.Frame):
                    for child in widget.winfo_children():
                        if isinstance(child, ttk.Label) and "Map Active" in child.cget("text"):
                            if self.use_interactive_map:
                                child.config(text="| Interactive Map Active", foreground="green")
                            else:
                                child.config(text="| Simple Map Active", foreground="orange")

            logger.info(
                f"Switched from {'Interactive' if old_use_interactive else 'Simple'} to {'Interactive' if self.use_interactive_map else 'Simple'} map"
            )

        except Exception as e:
            messagebox.showerror("Map Error", f"Failed to switch map type: {e}")
            logger.error(f"Failed to toggle map type: {e}")

    def setup_tables_view(self, parent):
        """Setup the tables view with coordinates and distances"""
        # Create paned window for tables
        tables_paned = ttk.PanedWindow(parent, orient=tk.VERTICAL)
        tables_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Coordinates table
        coord_frame = ttk.LabelFrame(tables_paned, text="bUE Coordinates")
        tables_paned.add(coord_frame, weight=1)

        self.coord_tree = ttk.Treeview(coord_frame, columns=("latitude", "longitude"), show="tree headings")
        self.coord_tree.heading("#0", text="bUE ID")
        self.coord_tree.heading("latitude", text="Latitude")
        self.coord_tree.heading("longitude", text="Longitude")
        self.coord_tree.pack(fill=tk.BOTH, expand=True)

        # Distance table
        dist_frame = ttk.LabelFrame(tables_paned, text="bUE Distances")
        tables_paned.add(dist_frame, weight=1)

        self.dist_tree = ttk.Treeview(dist_frame, columns=("distance",), show="tree headings")
        self.dist_tree.heading("#0", text="bUE Pair")
        self.dist_tree.heading("distance", text="Distance (m)")
        self.dist_tree.pack(fill=tk.BOTH, expand=True)

    def setup_messages_view(self, parent):
        """Setup the messages view"""
        # Messages text area - adjust height for horizontal layout
        self.messages_text = scrolledtext.ScrolledText(parent, height=12, wrap=tk.WORD)
        self.messages_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Control frame for buttons
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        # Clear messages button
        ttk.Button(control_frame, text="Clear Messages", command=self.clear_messages).pack(side=tk.LEFT)

    def start_base_station(self):
        """Initialize and start the base station"""
        try:
            self.base_station = Base_Station_Main("config_base.yaml")
            self.base_station.tick_enabled = True
            self.running = True

            # Start update thread
            self.update_thread = threading.Thread(target=self.update_loop, daemon=True)
            self.update_thread.start()

            self.status_var.set("Base Station Running")
            logger.info("Base Station GUI started successfully")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to start base station: {e}")
            logger.error(f"Failed to start base station: {e}")

    def update_loop(self):
        """Main update loop for GUI refresh"""
        while self.running:
            try:
                if self.base_station:
                    self.root.after(0, self.update_display)
                time.sleep(1)  # Update every second
            except Exception as e:
                logger.error(f"Error in update loop: {e}")

    def update_display(self):
        """Update all GUI elements with current data"""
        if not self.base_station:
            return

        self.update_bue_list()
        self.update_map()
        self.update_tables()
        self.update_messages()
        self.update_status()

    def update_bue_list(self):
        """Update the bUE list with current connections and status"""
        # Clear existing items
        for item in self.bue_tree.get_children():
            self.bue_tree.delete(item)

        # Add connected bUEs
        for bue_id in self.base_station.connected_bues:
            bue_name = self.base_station.bue_id_to_hostname[bue_id]

            # # Determine status
            # if bue_id in getattr(self.base_station, "testing_bues", []):
            #     status = "🧪 Testing"
            # else:
            #     status = "💤 Idle"
            status = self.base_station.bue_id_to_state[bue_id]

            # Determine ping status
            timeout_val = self.base_station.bue_missed_ping_counter.get(bue_id, 0)
            # if timeout_val >= TIMEOUT / 2:
            #     ping_status = "🟢 Good"
            # elif timeout_val > 0:
            #     ping_status = "🟡 Warning"
            # else:
            #     ping_status = "🔴 Lost"

            ping_status = timeout_val

            self.bue_tree.insert("", "end", iid=bue_id, text=bue_name, values=(status, ping_status))

    def update_map(self):
        """Update the map with bUE locations and markers"""
        if not hasattr(self, "map_widget") or not self.map_widget:
            return

        if self.use_interactive_map and MAP_VIEW_AVAILABLE:
            self.update_interactive_map()
        else:
            self.update_canvas_map()

    def update_interactive_map(self):
        """Update TkinterMapView with current data"""
        if not hasattr(self, "map_widget") or not self.map_widget:
            return

        try:
            # Clear existing markers
            for marker_id, marker_obj in self.map_markers.items():
                try:
                    marker_obj.delete()
                except:
                    pass
            self.map_markers.clear()

            if not self.base_station or not self.base_station.bue_id_to_coords:
                return

            # Check if bUE positions have changed significantly
            current_positions = {}
            position_changed = False
            new_bues_detected = False

            # Calculate center point for the map
            lats = []
            lons = []

            # Get bUE coordinates and track changes
            for bue_id, coords in self.base_station.bue_id_to_coords.items():
                try:
                    lat, lon = float(coords[0]), float(coords[1])
                    lats.append(lat)
                    lons.append(lon)

                    current_positions[bue_id] = (lat, lon)

                    # Check for new bUEs
                    if bue_id not in self.last_bue_positions:
                        new_bues_detected = True
                    # Check for significant position changes (more than ~100 meters)
                    elif bue_id in self.last_bue_positions:
                        old_lat, old_lon = self.last_bue_positions[bue_id]
                        distance_moved = self.calculate_distance(lat, lon, old_lat, old_lon)
                        if distance_moved > 100:  # 100 meters threshold
                            position_changed = True

                except (ValueError, IndexError):
                    continue

            # Add custom marker coordinates
            for marker in self.custom_markers.values():
                lats.append(marker["lat"])
                lons.append(marker["lon"])

            # Only auto-center/zoom if:
            # 1. This is the first time setting up the map, OR
            # 2. New bUEs have been detected, OR
            # 3. Existing bUEs have moved significantly
            should_auto_position = not self.map_auto_positioned or new_bues_detected or position_changed

            if should_auto_position and lats and lons:
                # Set map center to the average of all coordinates
                center_lat = sum(lats) / len(lats)
                center_lon = sum(lons) / len(lons)
                self.map_widget.set_position(center_lat, center_lon)

                # Auto-zoom to fit all markers with extra context
                lat_range = max(lats) - min(lats)
                lon_range = max(lons) - min(lons)
                max_range = max(lat_range, lon_range)

                # Add padding to ensure markers aren't at the edge (25% extra space)
                padded_range = max_range * 1.25

                # Determine zoom level based on coordinate range (less aggressive zooming)
                if padded_range > 1:
                    zoom = 7  # Reduced from 8 - very wide area view
                elif padded_range > 0.1:
                    zoom = 10  # Reduced from 12 - city-level view
                elif padded_range > 0.01:
                    zoom = 12  # Reduced from 15 - neighborhood view
                elif padded_range > 0.001:
                    zoom = 14  # New level - street level with good context
                else:
                    zoom = 15  # Reduced from 17 - close but not too tight

                self.map_widget.set_zoom(zoom)
                self.map_auto_positioned = True

                if new_bues_detected:
                    logger.info("Auto-centered map due to new bUEs")
                elif position_changed:
                    logger.info("Auto-centered map due to significant bUE movement")

            # Update position tracking
            self.last_bue_positions = current_positions.copy()

            # Add bUE markers
            for bue_id, coords in self.base_station.bue_id_to_coords.items():
                try:
                    lat, lon = float(coords[0]), float(coords[1])
                    bue_name = 55555

                    # Check proximity to custom markers
                    is_close = False
                    for marker in self.custom_markers.values():
                        if marker.get("paired_bue") == bue_id:
                            distance = self.calculate_distance(lat, lon, marker["lat"], marker["lon"])
                            if distance <= 20:  # 20 meters proximity
                                is_close = True
                                break

                    # Choose marker color based on proximity
                    marker_color = "green" if is_close else "blue"

                    # Create custom circle icon matching canvas map style
                    circle_icon = self.create_circle_marker_icon(marker_color)

                    # Create marker with custom circular icon
                    if circle_icon:
                        marker = self.map_widget.set_marker(
                            lat, lon, text=bue_name, icon=circle_icon, font=("Arial", 10, "bold"), text_color="white"
                        )
                    else:
                        # Fallback to default marker if icon creation failed
                        marker = self.map_widget.set_marker(
                            lat,
                            lon,
                            text=bue_name,
                            marker_color_circle=marker_color,
                            marker_color_outside="darkblue",
                            font=("Arial", 10, "bold"),
                        )
                    self.map_markers[f"bue_{bue_id}"] = marker

                except (ValueError, IndexError) as e:
                    logger.error(f"Error plotting bUE {bue_id} on interactive map: {e}")

            # Add custom markers
            for marker_id, marker_data in self.custom_markers.items():
                try:
                    # Create custom circle icon for custom markers
                    circle_icon = self.create_circle_marker_icon("red")

                    # Create custom marker with circular icon
                    if circle_icon:
                        marker = self.map_widget.set_marker(
                            marker_data["lat"],
                            marker_data["lon"],
                            text=marker_data["name"],
                            icon=circle_icon,
                            font=("Arial", 10, "bold"),
                            text_color="white",
                        )
                    else:
                        # Fallback to default marker if icon creation failed
                        marker = self.map_widget.set_marker(
                            marker_data["lat"],
                            marker_data["lon"],
                            text=marker_data["name"],
                            marker_color_circle="red",
                            marker_color_outside="darkred",
                            font=("Arial", 10, "bold"),
                        )
                    self.map_markers[f"custom_{marker_id}"] = marker
                except Exception as e:
                    logger.error(f"Error plotting custom marker {marker_id} on interactive map: {e}")

        except Exception as e:
            logger.error(f"Error updating interactive map: {e}")

    def update_canvas_map(self):
        """Update canvas-based map (original implementation)"""
        if not hasattr(self, "map_widget") or not self.map_widget:
            return

        # Clear canvas
        self.map_widget.delete("all")

        if not self.base_station or not self.base_station.bue_id_to_coords:
            self.map_widget.create_text(
                300,
                200,
                text="No bUE coordinates available",
                font=("Arial", 14),
                fill="gray",
            )
            return

        # Calculate map bounds
        lats = []
        lons = []

        # Get bUE coordinates
        for coords in self.base_station.bue_id_to_coords.values():
            try:
                lat, lon = float(coords[0]), float(coords[1])
                lats.append(lat)
                lons.append(lon)
            except (ValueError, IndexError):
                continue

        # Add custom marker coordinates
        for marker in self.custom_markers.values():
            lats.append(marker["lat"])
            lons.append(marker["lon"])

        if not lats or not lons:
            self.map_widget.create_text(
                300,
                200,
                text="No valid coordinates available",
                font=("Arial", 14),
                fill="gray",
            )
            return

        # Calculate bounds with padding
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)

        # Add padding
        lat_padding = (max_lat - min_lat) * 0.1 or 0.001
        lon_padding = (max_lon - min_lon) * 0.1 or 0.001

        min_lat -= lat_padding
        max_lat += lat_padding
        min_lon -= lon_padding
        max_lon += lon_padding

        # Get canvas dimensions
        canvas_width = self.map_widget.winfo_width() or 600
        canvas_height = self.map_widget.winfo_height() or 400

        # Map coordinate conversion functions
        def lat_to_y(lat):
            return canvas_height - ((lat - min_lat) / (max_lat - min_lat)) * canvas_height

        def lon_to_x(lon):
            return ((lon - min_lon) / (max_lon - min_lon)) * canvas_width

        # Draw bUEs
        for bue_id, coords in self.base_station.bue_id_to_coords.items():
            try:
                lat, lon = float(coords[0]), float(coords[1])
                x, y = lon_to_x(lon), lat_to_y(lat)

                # Check proximity to custom markers
                is_close = False
                for marker in self.custom_markers.values():
                    if marker.get("paired_bue") == bue_id:
                        distance = self.calculate_distance(lat, lon, marker["lat"], marker["lon"])
                        if distance <= 20:  # 20 meters proximity
                            is_close = True
                            break

                # Choose color based on proximity
                color = "green" if is_close else "blue"

                # Draw bUE circle
                radius = 8
                self.map_widget.create_oval(
                    x - radius,
                    y - radius,
                    x + radius,
                    y + radius,
                    fill=color,
                    outline="darkblue",
                    width=2,
                    tags=f"bue_{bue_id}",
                )

                # Label
                # bue_name = bUEs5.get(str(bue_id), f"bUE {bue_id}")
                bue_name = self.base_station.bue_id_to_hostname(int(bue_id))
                self.map_widget.create_text(
                    x,
                    y - 15,
                    text=bue_name,
                    font=("Arial", 8),
                    fill="black",
                    tags=f"bue_{bue_id}",
                )

            except (ValueError, IndexError) as e:
                logger.error(f"Error plotting bUE {bue_id}: {e}")

        # Draw custom markers
        for marker_id, marker in self.custom_markers.items():
            x, y = lon_to_x(marker["lon"]), lat_to_y(marker["lat"])

            # Draw marker
            radius = 6
            self.map_widget.create_oval(
                x - radius,
                y - radius,
                x + radius,
                y + radius,
                fill="red",
                outline="darkred",
                width=2,
                tags=f"marker_{marker_id}",
            )

            # Label
            self.map_widget.create_text(
                x,
                y - 15,
                text=marker["name"],
                font=("Arial", 8),
                fill="red",
                tags=f"marker_{marker_id}",
            )

    def update_tables(self):
        """Update coordinate and distance tables"""
        # Update coordinates table
        for item in self.coord_tree.get_children():
            self.coord_tree.delete(item)

        if self.base_station:
            for bue_id, coords in self.base_station.bue_id_to_coords.items():
                # bue_name = bUEs5.get(str(bue_id), f"bUE {bue_id}")
                bue_name = self.base_station.bue_id_to_hostname(int(bue_id))
                try:
                    lat, lon = coords[0], coords[1]
                    self.coord_tree.insert("", "end", text=bue_name, values=(lat, lon))
                except (IndexError, ValueError):
                    self.coord_tree.insert("", "end", text=bue_name, values=("Invalid", "Invalid"))

        # Update distance table
        for item in self.dist_tree.get_children():
            self.dist_tree.delete(item)

        if self.base_station and len(self.base_station.connected_bues) > 1:
            processed_pairs = set()
            for bue1 in self.base_station.connected_bues:
                for bue2 in self.base_station.connected_bues:
                    if (
                        bue1 != bue2
                        and bue1 in self.base_station.bue_id_to_coords
                        and bue2 in self.base_station.bue_id_to_coords
                        and (bue1, bue2) not in processed_pairs
                        and (bue2, bue1) not in processed_pairs
                    ):

                        distance = self.base_station.get_distance(bue1, bue2)
                        if distance is not None:
                            # pair_name = f"{bUEs5.get(str(bue1), str(bue1))} ↔ {bUEs5.get(str(bue2), str(bue2))}"
                            pair_name = f"{self.base_station.bue_id_to_hostname(int(bue1))} ↔ {self.base_station.bue_id_to_hostname(int(bue1))}"
                            self.dist_tree.insert("", "end", text=pair_name, values=(f"{distance:.2f}"))

                        processed_pairs.add((bue1, bue2))

    def update_messages(self):
        """Update the messages display"""
        if self.base_station and hasattr(self.base_station, "stdout_history"):
            # Get current content
            current_content = self.messages_text.get(1.0, tk.END)

            # Build new content
            new_content = "\n".join(self.base_station.stdout_history)

            # Only update if content changed
            if new_content.strip() != current_content.strip():
                self.messages_text.delete(1.0, tk.END)
                self.messages_text.insert(1.0, new_content)
                self.messages_text.see(tk.END)  # Scroll to bottom

    def update_status(self):
        """Update the status bar"""
        if self.base_station:
            connected = len(self.base_station.connected_bues)
            testing = len(getattr(self.base_station, "testing_bues", []))
            current_time = datetime.now().strftime("%H:%M:%S")
            self.status_var.set(f"Time: {current_time} | Connected: {connected} | Testing: {testing}")

    def show_bue_context_menu(self, event):
        """Show context menu for bUE operations"""
        item = self.bue_tree.selection()[0] if self.bue_tree.selection() else None
        if not item:
            return

        bue_id = int(item)

        # Create context menu
        context_menu = tk.Menu(self.root, tearoff=0)
        context_menu.add_command(label="Disconnect", command=lambda: self.disconnect_bue(bue_id))
        context_menu.add_command(label="Reload", command=lambda: self.reload_bue(bue_id))
        context_menu.add_command(label="Restart", command=lambda: self.restart_bue(bue_id))
        context_menu.add_separator()
        context_menu.add_command(label="Open Log File", command=lambda: self.open_bue_log(bue_id))

        # Show menu
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    def disconnect_bue(self, bue_id):
        """Disconnect a specific bUE"""
        if messagebox.askyesno(
            "Confirm Disconnect",
            # f"Disconnect from {bUEs5.get(str(bue_id), str(bue_id))}?",
            f"Disconnect from {self.base_station.bue_id_to_hostname(int(bue_id))}?",
        ):
            try:
                self.base_station.connected_bues.remove(bue_id)
                if bue_id in self.base_station.bue_id_to_coords:
                    del self.base_station.bue_id_to_coords[bue_id]
                if bue_id in getattr(self.base_station, "testing_bues", []):
                    self.base_station.testing_bues.remove(bue_id)
                if bue_id in self.base_station.bue_missed_ping_counter:
                    del self.base_station.bue_missed_ping_counter[bue_id]
                logger.info(f"Disconnected from bUE {bue_id}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to disconnect: {e}")

    def reload_bue(self, bue_id):
        """Reload a specific bUE"""
        if messagebox.askyesno("Confirm Reload", f"Reload {self.base_station.bue_id_to_hostname(int(bue_id))}?"):
            try:
                self.base_station.ota.send_ota_message(bue_id, "RELOAD")
                self.disconnect_bue(bue_id)
                logger.info(f"Sent reload command to bUE {bue_id}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to reload: {e}")

    def restart_bue(self, bue_id):
        """Restart a specific bUE"""
        if messagebox.askyesno("Confirm Restart", f"Restart {self.base_station.bue_id_to_hostname(int(bue_id))}?"):
            try:
                self.base_station.ota.send_ota_message(bue_id, "RESTART")
                self.disconnect_bue(bue_id)
                logger.info(f"Sent restart command to bUE {bue_id}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to restart: {e}")

    def open_bue_log(self, bue_id):
        """Open the log file for a specific bUE"""
        log_path = f"logs/bue_{bue_id}.log"
        bue_name = self.base_station.bue_id_to_hostname(int(bue_id))
        LogViewerDialog(self.root, log_path, f"{bue_name} Log")

    def open_base_log(self):
        """Open the base station log file"""
        log_path = "logs/base_station.log"
        LogViewerDialog(self.root, log_path, "Base Station Log")

    def run_test(self):
        """Run test dialog and execute tests"""
        if not self.base_station or not self.base_station.connected_bues:
            messagebox.showwarning("No bUEs", "No bUEs currently connected")
            return

        # Create test dialog
        TestDialog(self.root, self.base_station)

    def cancel_tests(self):
        """Cancel running tests"""
        if not hasattr(self.base_station, "testing_bues") or not self.base_station.testing_bues:
            messagebox.showinfo("No Tests", "No tests currently running")
            return

        # Create cancel dialog
        CancelTestDialog(self.root, self.base_station)

    def clear_messages(self):
        """Clear the messages display"""
        self.messages_text.delete(1.0, tk.END)
        if self.base_station and hasattr(self.base_station, "stdout_history"):
            self.base_station.stdout_history.clear()

    def add_custom_marker(self):
        """Add a custom marker to the map"""
        AddMarkerDialog(self.root, self)

    def manage_markers(self):
        """Manage existing custom markers"""
        ManageMarkersDialog(self.root, self)

    def on_map_click(self, event):
        """Handle map click events"""
        # Get clicked coordinates (simplified - would need proper coordinate conversion)
        pass

    def on_map_hover(self, event):
        """Handle map hover events"""
        # Show coordinates or object info on hover
        pass

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two coordinates in meters"""
        # Haversine formula
        R = 6371000  # Earth's radius in meters

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = math.sin(delta_lat / 2) * math.sin(delta_lat / 2) + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(
            delta_lon / 2
        ) * math.sin(delta_lon / 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def on_closing(self):
        """Handle application closing"""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.running = False
            if self.base_station:
                self.base_station.EXIT = True
                if hasattr(self.base_station, "__del__"):
                    self.base_station.__del__()
            self.root.destroy()


class TestDialog:
    """All-in-one test dialog - everything in a single window"""

    def __init__(self, parent, base_station):
        self.parent = parent
        self.base_station = base_station

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Test Management")
        self.dialog.geometry("700x700")
        self.dialog.grab_set()

        # Available test files
        self.test_files = [
            "grc/lora_td_ru",
            "grc/lora_tu_rd",
            "Old/helloworld",
            "Old/sf_msg_test",
            "Old" "gpstest",
            "gpstest2",
            "../osu_testing/run_tx",
            "../osu_testing/run_rx",
            "../osu_testing/run_rx_12_20",
        ]

        # Selected bUEs and their configurations
        self.selected_bues = []
        self.bue_configs = {}  # {bue_id: {'file': str, 'params': str}}

        self.setup_dialog()

    def setup_dialog(self):
        """Setup the all-in-one test dialog"""
        # Step 1: bUE Selection
        selection_frame = ttk.LabelFrame(self.dialog, text="Step 1: Select bUEs for Testing", padding="10")
        selection_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(selection_frame, text="Choose which bUEs will run tests:").pack(anchor=tk.W, pady=(0, 5))

        # Create checkboxes for connected bUEs
        self.bue_vars = {}
        checkbox_frame = ttk.Frame(selection_frame)
        checkbox_frame.pack(fill=tk.X)

        row = 0
        col = 0
        for i, bue_id in enumerate(self.base_station.connected_bues):
            bue_name = self.base_station.bue_id_to_hostname[int(bue_id)]
            var = tk.BooleanVar()
            self.bue_vars[bue_id] = var

            cb = ttk.Checkbutton(
                checkbox_frame,
                text=bue_name,
                variable=var,
                command=self.update_selection,
            )
            cb.grid(row=row, column=col, sticky=tk.W, padx=20, pady=2)

            col += 1
            if col > 1:  # 2 columns
                col = 0
                row += 1

        # Selection summary
        self.selection_label = ttk.Label(selection_frame, text="No bUEs selected", foreground="gray")
        self.selection_label.pack(anchor=tk.W, pady=(5, 0))

        # Step 2: Test Delay
        time_frame = ttk.LabelFrame(self.dialog, text="Step 2: Set Test Delay", padding="10")
        time_frame.pack(fill=tk.X, padx=10, pady=5)

        # Delay input
        delay_controls = ttk.Frame(time_frame)
        delay_controls.pack()

        ttk.Label(delay_controls, text="Start test in:").grid(row=0, column=0, padx=5)
        self.delay_var = tk.StringVar(value="30")
        delay_spin = tk.Spinbox(delay_controls, from_=5, to=300, textvariable=self.delay_var, width=5)
        delay_spin.grid(row=0, column=1, padx=5)
        ttk.Label(delay_controls, text="seconds").grid(row=0, column=2, padx=5)

        # Calculated start time display
        self.start_time_label = ttk.Label(time_frame, text="", foreground="blue", font=("TkDefaultFont", 9))
        self.start_time_label.pack(pady=(10, 0))

        # Update the calculated time when delay changes
        self.delay_var.trace("w", self.update_calculated_time)

        # Start automatic time updates every second
        self.start_auto_time_updates()
        self.update_calculated_time()  # Initial calculation

        # Step 3: Configure Individual bUEs - ALL IN ONE WINDOW
        config_frame = ttk.LabelFrame(self.dialog, text="Step 3: Configure Each Selected bUE", padding="10")
        config_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Create a scrollable frame for bUE configurations
        canvas = tk.Canvas(config_frame, height=300)
        scrollbar = ttk.Scrollbar(config_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Initially empty - will be populated when bUEs are selected
        self.no_selection_label = ttk.Label(
            self.scrollable_frame,
            text="Select bUEs above to configure their tests here",
            foreground="gray",
        )
        self.no_selection_label.pack(pady=50)

        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        self.run_btn = ttk.Button(button_frame, text="Run Tests", command=self.run_tests, state=tk.DISABLED)
        self.run_btn.pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def update_selection(self):
        """Update the selection and show inline configuration"""
        self.selected_bues = [bue_id for bue_id, var in self.bue_vars.items() if var.get()]

        if self.selected_bues:
            bue_names = [self.base_station.bue_id_to_hostname(int(bid)) for bid in self.selected_bues]
            self.selection_label.config(text=f"Selected: {', '.join(bue_names)}", foreground="blue")

            # Show inline configuration for each selected bUE
            self.show_inline_configs()
        else:
            self.selection_label.config(text="No bUEs selected", foreground="gray")
            self.clear_inline_configs()
            self.run_btn.config(state=tk.DISABLED)

    def start_auto_time_updates(self):
        """Start automatic time updates every second"""
        self.update_calculated_time()
        # Schedule next update in 1000ms (1 second)
        self.dialog.after(1000, self.start_auto_time_updates)

    def update_calculated_time(self, *args):
        """Update the calculated start time display using current time"""
        try:
            delay_seconds = int(self.delay_var.get())
            # Always use current time for real-time updates
            current_time = datetime.now().replace(microsecond=0)
            start_time = current_time + timedelta(seconds=delay_seconds)

            # Format the time nicely
            time_str = start_time.strftime("%I:%M:%S %p")
            date_str = start_time.strftime("%Y-%m-%d")

            if start_time.date() == current_time.date():
                # Same day
                self.start_time_label.config(text=f"Tests will start at: {time_str} (today)")
            else:
                # Next day
                self.start_time_label.config(text=f"Tests will start at: {time_str} on {date_str}")

        except ValueError:
            self.start_time_label.config(text="Invalid delay time")

    def show_inline_configs(self):
        """Show configuration options for each selected bUE inline"""
        # Clear existing config widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        self.config_widgets = {}

        for i, bue_id in enumerate(self.selected_bues):
            bue_name = self.base_station.bue_id_to_hostname(int(bue_id))

            # Create a frame for this bUE's configuration
            bue_frame = ttk.LabelFrame(self.scrollable_frame, text=f"Configure {bue_name}", padding="10")
            bue_frame.pack(fill=tk.X, padx=5, pady=5)

            # Test file selection row
            file_frame = ttk.Frame(bue_frame)
            file_frame.pack(fill=tk.X, pady=(0, 5))

            ttk.Label(file_frame, text="Test File:", width=12).pack(side=tk.LEFT)
            file_var = tk.StringVar(value=self.test_files[0])
            file_combo = ttk.Combobox(
                file_frame,
                textvariable=file_var,
                values=self.test_files,
                state="readonly",
                width=20,
            )
            file_combo.pack(side=tk.LEFT, padx=(5, 0))

            # Message field (always visible)
            msg_frame = ttk.Frame(bue_frame)
            msg_frame.pack(fill=tk.X, pady=(0, 5))

            ttk.Label(msg_frame, text="Message:", width=12).pack(side=tk.LEFT)
            msg_var = tk.StringVar()
            msg_entry = ttk.Entry(msg_frame, textvariable=msg_var, width=20)
            msg_entry.pack(side=tk.LEFT, padx=(5, 0))

            # Conditional parameters frame for run_tx/run_rx only
            params_frame = ttk.Frame(bue_frame)

            sf = [5, 6, 7, 8, 9, 10, 11, 12]

            # Create all the conditional widgets but don't pack them yet
            sf_var = tk.IntVar(value=8)
            bw_var = tk.StringVar(value="6000")  # Default bandwidth
            freq_var = tk.StringVar(value="12000")  # Default center frequency
            period_var = tk.StringVar(value="3000")  # Default period

            # Row 1: Spreading Factor and Bandwidth
            row1_frame = ttk.Frame(params_frame)
            ttk.Label(row1_frame, text="Spreading Factor:", width=16).pack(side=tk.LEFT)
            sf_entry = ttk.Combobox(row1_frame, textvariable=sf_var, values=sf, state="readonly", width=8)
            sf_entry.pack(side=tk.LEFT, padx=(5, 15))

            ttk.Label(row1_frame, text="Bandwidth:", width=12).pack(side=tk.LEFT)
            bw_entry = ttk.Entry(row1_frame, textvariable=bw_var, width=10)
            bw_entry.pack(side=tk.LEFT, padx=(5, 0))

            # Row 2: Center Frequency and Period
            row2_frame = ttk.Frame(params_frame)
            ttk.Label(row2_frame, text="Center Frequency:", width=16).pack(side=tk.LEFT)
            freq_entry = ttk.Entry(row2_frame, textvariable=freq_var, width=12)
            freq_entry.pack(side=tk.LEFT, padx=(5, 15))

            ttk.Label(row2_frame, text="Period:", width=12).pack(side=tk.LEFT)
            period_entry = ttk.Entry(row2_frame, textvariable=period_var, width=10)
            period_entry.pack(side=tk.LEFT, padx=(5, 0))

            # Validation function for integer-only fields
            def validate_integer(char):
                return char.isdigit()

            vcmd = (self.dialog.register(validate_integer), "%S")
            bw_entry.config(validate="key", validatecommand=vcmd)
            freq_entry.config(validate="key", validatecommand=vcmd)
            period_entry.config(validate="key", validatecommand=vcmd)

            def update_params_visibility(*args, fvar=file_var, pframe=params_frame, r1frame=row1_frame, r2frame=row2_frame):
                selected_file = fvar.get()
                if selected_file.endswith("run_tx") or selected_file.endswith("run_rx"):
                    pframe.pack(fill=tk.X, pady=(5, 0))
                    r1frame.pack(fill=tk.X, pady=(0, 5))
                    r2frame.pack(fill=tk.X, pady=(0, 5))
                else:
                    pframe.pack_forget()

            # Bind file selection changes to update visibility
            file_var.trace("w", update_params_visibility)
            # Initial visibility check
            update_params_visibility()

            # Add placeholder functionality
            placeholder_text = "No spaces"
            msg_entry.insert(0, placeholder_text)
            msg_entry.config(foreground="gray", font=("TkDefaultFont", 10, "italic"))

            def on_focus_in(event, entry=msg_entry, var=msg_var, placeholder=placeholder_text):
                if var.get() == placeholder:
                    entry.delete(0, tk.END)
                    entry.config(foreground="black", font=("TkDefaultFont", 10, "normal"))

            def on_focus_out(event, entry=msg_entry, var=msg_var, placeholder=placeholder_text):
                if not var.get():
                    entry.insert(0, placeholder)
                    entry.config(foreground="gray", font=("TkDefaultFont", 10, "italic"))

            msg_entry.bind("<FocusIn>", on_focus_in)
            msg_entry.bind("<FocusOut>", on_focus_out)

            # Store the variables for this bUE
            self.config_widgets[bue_id] = {
                "file_var": file_var,
                "sf_var": sf_var,
                "bw_var": bw_var,
                "freq_var": freq_var,
                "period_var": period_var,
                "msg_var": msg_var,
                "file_combo": file_combo,
                "sf_entry": sf_entry,
                "bw_entry": bw_entry,
                "freq_entry": freq_entry,
                "period_entry": period_entry,
                "msg_entry": msg_entry,
            }

            # Bind changes to enable run button
            file_var.trace("w", self.check_ready_to_run)
            sf_var.trace("w", self.check_ready_to_run)
            bw_var.trace("w", self.check_ready_to_run)
            freq_var.trace("w", self.check_ready_to_run)
            period_var.trace("w", self.check_ready_to_run)
            msg_var.trace("w", self.check_ready_to_run)
        # Enable run button if we have configurations
        self.check_ready_to_run()

    def clear_inline_configs(self):
        """Clear all configuration widgets"""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        self.no_selection_label = ttk.Label(
            self.scrollable_frame,
            text="Select bUEs above to configure their tests here",
            foreground="gray",
        )
        self.no_selection_label.pack(pady=50)

        self.config_widgets = {}

    def check_ready_to_run(self, *args):
        """Check if all configurations are ready and enable run button"""
        if self.selected_bues and hasattr(self, "config_widgets") and self.config_widgets:
            # All selected bUEs have configuration widgets, enable run
            self.run_btn.config(state=tk.NORMAL)
        else:
            self.run_btn.config(state=tk.DISABLED)

    def run_tests(self):
        """Execute the configured tests"""
        if not self.selected_bues or not hasattr(self, "config_widgets"):
            messagebox.showwarning(
                "No Configuration",
                "Please select and configure at least one bUE for testing",
            )
            return

        # Collect configurations from the inline widgets
        self.bue_configs = {}
        for bue_id in self.selected_bues:
            if bue_id in self.config_widgets:
                widgets = self.config_widgets[bue_id]
                config = {
                    "file": widgets["file_var"].get(),
                    "msg": widgets["msg_var"].get(),
                }

                # Add run_tx/run_rx specific parameters if applicable
                selected_file = widgets["file_var"].get()
                if selected_file.endswith("run_tx") or selected_file.endswith("run_rx"):
                    config.update(
                        {
                            "sf": widgets["sf_var"].get(),
                            "bw": widgets["bw_var"].get(),
                            "freq": widgets["freq_var"].get(),
                            "period": widgets["period_var"].get(),
                        }
                    )

                self.bue_configs[bue_id] = config

        # Calculate start time using delay - use CURRENT time for actual execution
        try:
            delay_seconds = int(self.delay_var.get())
            execution_time = datetime.now().replace(microsecond=0)  # Fresh time for execution
            start_time = execution_time + timedelta(seconds=delay_seconds)
            unix_timestamp = int(start_time.timestamp())

            # Format the start time for user confirmation
            time_str = start_time.strftime("%I:%M:%S %p")

            # Send test commands
            for bue_id, config in self.bue_configs.items():
                selected_file = config["file"]  # ← FIX: Get file from config, not from outside loop

                if selected_file.endswith("run_tx") or selected_file.endswith("run_rx"):
                    command = f"TEST:{config['file']},{unix_timestamp},-s {config['sf']} -m {config['msg']} -c {config['freq']} -b {config['bw']} -p {config['period']}"
                elif selected_file.startswith("Old"):
                    command = f"TEST:{config['file']},{unix_timestamp},{config['msg']}"
                else:
                    command = f"TEST:{config['file']},{unix_timestamp},"

                self.base_station.ota.send_ota_message(bue_id, command)
                time.sleep(0.1)
                logger.info(f"Sent test command to bUE {bue_id}: {command}")

            bue_names = [self.base_station.bue_id_to_hostname(int(bue_id)) for bue_id in self.bue_configs.keys()]
            messagebox.showinfo(
                "Tests Scheduled",
                f"Tests scheduled for: {', '.join(bue_names)}\n\n"
                f"Actual start time: {time_str}\n"
                f"Delay: {delay_seconds} seconds from when you clicked 'Run'",
            )
            self.dialog.destroy()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to schedule tests: {e}")


# Remove the IndividualBueConfigDialog since we don't need it anymore


class ConfigureBueDialog:
    """Dialog for configuring a single bUE test"""

    def __init__(self, parent, bue_id, test_files, config_tree):
        self.parent = parent
        self.bue_id = bue_id
        self.test_files = test_files
        self.config_tree = config_tree

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Configure {self.base_station.bue_id_to_hostname(int(bue_id))}")
        self.dialog.geometry("400x200")
        self.dialog.grab_set()

        self.setup_dialog()

    def setup_dialog(self):
        """Setup the configuration dialog"""
        ttk.Label(
            self.dialog,
            text=f"Configure test for {self.base_station.bue_id_to_hostname(int(self.bue_id))}",
        ).pack(pady=10)

        # Test file selection
        ttk.Label(self.dialog, text="Test File:").pack(anchor=tk.W, padx=20)
        self.file_var = tk.StringVar(value=self.test_files[0])
        file_combo = ttk.Combobox(
            self.dialog,
            textvariable=self.file_var,
            values=self.test_files,
            state="readonly",
        )
        file_combo.pack(fill=tk.X, padx=20, pady=5)

        # Parameters
        ttk.Label(self.dialog, text="Parameters:").pack(anchor=tk.W, padx=20)
        self.params_var = tk.StringVar()
        ttk.Entry(self.dialog, textvariable=self.params_var).pack(fill=tk.X, padx=20, pady=5)

        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Button(button_frame, text="OK", command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def save_config(self):
        """Save the configuration"""
        bue_name = self.base_station.bue_id_to_hostname(int(self.bue_id))
        self.config_tree.insert(
            "",
            "end",
            text=bue_name,
            values=(self.file_var.get(), self.params_var.get()),
        )
        self.dialog.destroy()


class CancelTestDialog:
    """Dialog for canceling running tests"""

    def __init__(self, parent, base_station):
        self.parent = parent
        self.base_station = base_station

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Cancel Tests")
        self.dialog.geometry("300x200")
        self.dialog.grab_set()

        self.setup_dialog()

    def setup_dialog(self):
        """Setup the cancel dialog"""
        ttk.Label(self.dialog, text="Select tests to cancel:").pack(pady=10)

        self.test_vars = {}
        for bue_id in getattr(self.base_station, "testing_bues", []):
            bue_name = self.base_station.bue_id_to_hostname(int(bue_id))
            var = tk.BooleanVar()
            self.test_vars[bue_id] = var
            ttk.Checkbutton(self.dialog, text=bue_name, variable=var).pack(anchor=tk.W, padx=20)

        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Button(button_frame, text="Cancel Selected", command=self.cancel_tests).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def cancel_tests(self):
        """Cancel selected tests"""
        canceled = []
        for bue_id, var in self.test_vars.items():
            if var.get():
                try:
                    for i in range(3):
                        self.base_station.ota.send_ota_message(bue_id, "CANC")
                        time.sleep(0.1)
                    canceled.append(self.base_station.bue_id_to_hostname(int(bue_id)))
                    logger.info(f"Sent cancel command to bUE {bue_id}")
                except Exception as e:
                    logger.error(f"Failed to cancel test for bUE {bue_id}: {e}")

        if canceled:
            messagebox.showinfo("Tests Canceled", f"Canceled tests for: {', '.join(canceled)}")

        self.dialog.destroy()


class AddMarkerDialog:
    """Dialog for adding custom markers"""

    def __init__(self, parent, main_gui):
        self.parent = parent
        self.main_gui = main_gui

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Add Custom Marker")
        self.dialog.geometry("400x350")
        self.dialog.grab_set()

        self.setup_dialog()

    def setup_dialog(self):
        """Setup the add marker dialog"""
        # Marker name
        ttk.Label(self.dialog, text="Marker Name:").pack(anchor=tk.W, padx=20, pady=(20, 5))
        self.name_var = tk.StringVar()
        ttk.Entry(self.dialog, textvariable=self.name_var, width=30).pack(fill=tk.X, padx=20, pady=5)

        # Coordinates
        ttk.Label(self.dialog, text="Latitude:").pack(anchor=tk.W, padx=20, pady=(10, 5))
        self.lat_var = tk.StringVar()
        ttk.Entry(self.dialog, textvariable=self.lat_var, width=30).pack(fill=tk.X, padx=20, pady=5)

        ttk.Label(self.dialog, text="Longitude:").pack(anchor=tk.W, padx=20, pady=(10, 5))
        self.lon_var = tk.StringVar()
        ttk.Entry(self.dialog, textvariable=self.lon_var, width=30).pack(fill=tk.X, padx=20, pady=5)

        # Pair with bUE
        ttk.Label(self.dialog, text="Pair with bUE (optional):").pack(anchor=tk.W, padx=20, pady=(10, 5))
        try:
            bue_options = ["None"] + [
                self.base_station.bue_id_to_hostname(int(bue_id)) for bue_id in self.main_gui.base_station.connected_bues
            ]
            self.bue_var = tk.StringVar(value="None")
            ttk.Combobox(
                self.dialog,
                textvariable=self.bue_var,
                values=bue_options,
                state="readonly",
            ).pack(fill=tk.X, padx=20, pady=5)
        except Exception as e:
            print(f"Error creating bUE combobox: {e}")
            # Fallback simple combobox
            self.bue_var = tk.StringVar(value="None")
            ttk.Combobox(
                self.dialog,
                textvariable=self.bue_var,
                values=["None"],
                state="readonly",
            ).pack(fill=tk.X, padx=20, pady=5)

        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=20, pady=20)

        # Add some spacing between buttons
        ttk.Button(button_frame, text="Add Marker", command=self.add_marker).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Cancel", command=self.dialog.destroy).pack(side=tk.LEFT, padx=(10, 0))

    def add_marker(self):
        """Add the custom marker"""
        try:
            name = self.name_var.get().strip()
            lat = float(self.lat_var.get())
            lon = float(self.lon_var.get())

            if not name:
                messagebox.showwarning("Invalid Input", "Please enter a marker name")
                return

            # Get paired bUE ID
            paired_bue = None
            bue_selection = self.bue_var.get()
            if bue_selection != "None":
                for bue_id in self.main_gui.base_station.connected_bues:
                    if self.base_station.bue_id_to_hostname(int(bue_id)) == bue_selection:
                        paired_bue = bue_id
                        break

            # Add marker
            marker_id = self.main_gui.marker_counter
            self.main_gui.marker_counter += 1

            self.main_gui.custom_markers[marker_id] = {
                "name": name,
                "lat": lat,
                "lon": lon,
                "paired_bue": paired_bue,
            }

            # Refresh the map to show the new marker
            self.main_gui.update_map()

            messagebox.showinfo("Marker Added", f"Added marker '{name}'")
            self.dialog.destroy()

        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid coordinates")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add marker: {e}")


class ManageMarkersDialog:
    """Dialog for managing custom markers"""

    def __init__(self, parent, main_gui):
        self.parent = parent
        self.main_gui = main_gui

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Manage Custom Markers")
        self.dialog.geometry("600x400")
        self.dialog.grab_set()

        self.setup_dialog()
        self.refresh_markers()

    def setup_dialog(self):
        """Setup the manage markers dialog"""
        # Markers list
        self.markers_tree = ttk.Treeview(self.dialog, columns=("lat", "lon", "paired_bue"), show="tree headings")
        self.markers_tree.heading("#0", text="Marker Name")
        self.markers_tree.heading("lat", text="Latitude")
        self.markers_tree.heading("lon", text="Longitude")
        self.markers_tree.heading("paired_bue", text="Paired bUE")

        self.markers_tree.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Buttons
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(fill=tk.X, padx=20, pady=10)

        ttk.Button(button_frame, text="Delete Selected", command=self.delete_marker).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Edit Selected", command=self.edit_marker).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", command=self.dialog.destroy).pack(side=tk.RIGHT, padx=5)

    def refresh_markers(self):
        """Refresh the markers list"""
        for item in self.markers_tree.get_children():
            self.markers_tree.delete(item)

        for marker_id, marker in self.main_gui.custom_markers.items():
            paired_bue_name = "None"
            if marker.get("paired_bue"):
                paired_bue_name = self.base_station.bue_id_to_hostname(int(paired_bue_name))

            self.markers_tree.insert(
                "",
                "end",
                iid=marker_id,
                text=marker["name"],
                values=(marker["lat"], marker["lon"], paired_bue_name),
            )

    def delete_marker(self):
        """Delete selected marker"""
        selection = self.markers_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a marker to delete")
            return

        marker_id = int(selection[0])
        marker_name = self.main_gui.custom_markers[marker_id]["name"]

        if messagebox.askyesno("Confirm Delete", f"Delete marker '{marker_name}'?"):
            del self.main_gui.custom_markers[marker_id]
            self.refresh_markers()
            # Refresh the map to remove the deleted marker
            self.main_gui.update_map()

    def edit_marker(self):
        """Edit selected marker"""
        selection = self.markers_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a marker to edit")
            return

        marker_id = int(selection[0])
        # Could implement edit dialog similar to AddMarkerDialog
        messagebox.showinfo("Edit Marker", "Edit functionality not yet implemented")


class LogViewerDialog:
    """Dialog for viewing log files within the GUI"""

    def __init__(self, parent, log_path, title):
        self.parent = parent
        self.log_path = log_path

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("900x600")
        self.dialog.grab_set()

        # Make dialog resizable
        self.dialog.resizable(True, True)

        self.setup_dialog()
        self.load_log_content()

        # Auto-refresh thread for live log viewing
        self.auto_refresh = True
        self.refresh_thread = threading.Thread(target=self.auto_refresh_loop, daemon=True)
        self.refresh_thread.start()

        # Handle dialog close
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_dialog(self):
        """Setup the log viewer dialog"""
        # Top frame with controls
        control_frame = ttk.Frame(self.dialog)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        # File info
        self.file_info_var = tk.StringVar()
        ttk.Label(control_frame, textvariable=self.file_info_var).pack(side=tk.LEFT)

        # Buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(side=tk.RIGHT)

        ttk.Button(button_frame, text="Refresh", command=self.refresh_log).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Clear", command=self.clear_log).pack(side=tk.LEFT, padx=2)
        ttk.Button(button_frame, text="Save As...", command=self.save_log).pack(side=tk.LEFT, padx=2)

        # Auto-refresh toggle
        self.auto_refresh_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            button_frame,
            text="Auto-refresh",
            variable=self.auto_refresh_var,
            command=self.toggle_auto_refresh,
        ).pack(side=tk.LEFT, padx=5)

        # Search frame
        search_frame = ttk.Frame(self.dialog)
        search_frame.pack(fill=tk.X, padx=10, pady=2)

        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.search_entry.bind("<Return>", self.search_log)
        self.search_entry.bind("<KeyRelease>", self.search_as_type)

        ttk.Button(search_frame, text="Find", command=self.search_log).pack(side=tk.LEFT, padx=2)
        ttk.Button(search_frame, text="Clear Search", command=self.clear_search).pack(side=tk.LEFT, padx=2)

        # Log content area with scrollbars
        content_frame = ttk.Frame(self.dialog)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Text widget with scrollbars
        self.log_text = scrolledtext.ScrolledText(
            content_frame,
            wrap=tk.WORD,
            font=("Consolas", 10),  # Monospace font for logs
            state=tk.DISABLED,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Configure text tags for highlighting
        self.log_text.tag_configure("error", foreground="red", font=("Consolas", 10, "bold"))
        self.log_text.tag_configure("warning", foreground="orange", font=("Consolas", 10, "bold"))
        self.log_text.tag_configure("info", foreground="blue")
        self.log_text.tag_configure("debug", foreground="gray")
        self.log_text.tag_configure("search_highlight", background="yellow")

        # Status bar
        self.status_var = tk.StringVar()
        status_bar = ttk.Label(self.dialog, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def load_log_content(self):
        """Load log file content"""
        try:
            if os.path.exists(self.log_path):
                with open(self.log_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                # Update text widget
                self.log_text.config(state=tk.NORMAL)
                self.log_text.delete(1.0, tk.END)

                # Apply syntax highlighting
                self.insert_with_highlighting(content)

                self.log_text.config(state=tk.DISABLED)
                self.log_text.see(tk.END)  # Scroll to bottom

                # Update file info
                file_size = os.path.getsize(self.log_path)
                line_count = content.count("\n")
                self.file_info_var.set(f"File: {self.log_path} | Size: {file_size:,} bytes | Lines: {line_count:,}")
                self.status_var.set("Log loaded successfully")

            else:
                self.log_text.config(state=tk.NORMAL)
                self.log_text.delete(1.0, tk.END)
                self.log_text.insert(1.0, f"Log file not found: {self.log_path}")
                self.log_text.config(state=tk.DISABLED)
                self.file_info_var.set(f"File: {self.log_path} | Status: Not Found")
                self.status_var.set("Log file not found")

        except Exception as e:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(1.0, f"Error reading log file: {e}")
            self.log_text.config(state=tk.DISABLED)
            self.status_var.set(f"Error: {e}")

    def insert_with_highlighting(self, content):
        """Insert content with syntax highlighting for log levels"""
        lines = content.split("\n")

        for line in lines:
            line_lower = line.lower()

            # Determine tag based on log level
            if "error" in line_lower or "failed" in line_lower or "exception" in line_lower:
                tag = "error"
            elif "warning" in line_lower or "warn" in line_lower:
                tag = "warning"
            elif "info" in line_lower:
                tag = "info"
            elif "debug" in line_lower:
                tag = "debug"
            else:
                tag = None

            if tag:
                self.log_text.insert(tk.END, line + "\n", tag)
            else:
                self.log_text.insert(tk.END, line + "\n")

    def refresh_log(self):
        """Manually refresh the log content"""
        self.load_log_content()

    def clear_log(self):
        """Clear the log display (not the actual file)"""
        if messagebox.askyesno(
            "Clear Display",
            "Clear the log display? (This won't delete the actual log file)",
        ):
            self.log_text.config(state=tk.NORMAL)
            self.log_text.delete(1.0, tk.END)
            self.log_text.config(state=tk.DISABLED)
            self.status_var.set("Display cleared")

    def save_log(self):
        """Save log content to a new file"""
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".log",
                filetypes=[
                    ("Log files", "*.log"),
                    ("Text files", "*.txt"),
                    ("All files", "*.*"),
                ],
            )

            if file_path:
                content = self.log_text.get(1.0, tk.END)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                self.status_var.set(f"Log saved to: {file_path}")

        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save log: {e}")

    def search_log(self, event=None):
        """Search for text in the log"""
        search_text = self.search_var.get()
        if not search_text:
            return

        # Clear previous highlights
        self.log_text.tag_remove("search_highlight", 1.0, tk.END)

        # Search and highlight
        start_pos = 1.0
        matches = 0

        while True:
            pos = self.log_text.search(search_text, start_pos, tk.END, nocase=True)
            if not pos:
                break

            end_pos = f"{pos}+{len(search_text)}c"
            self.log_text.tag_add("search_highlight", pos, end_pos)
            start_pos = end_pos
            matches += 1

        if matches > 0:
            # Jump to first match
            first_match = self.log_text.search(search_text, 1.0, tk.END, nocase=True)
            self.log_text.see(first_match)
            self.status_var.set(f"Found {matches} matches for '{search_text}'")
        else:
            self.status_var.set(f"No matches found for '{search_text}'")

    def search_as_type(self, event=None):
        """Search as user types (with delay)"""
        # Cancel previous search
        if hasattr(self, "search_timer"):
            self.dialog.after_cancel(self.search_timer)

        # Schedule new search
        self.search_timer = self.dialog.after(300, self.search_log)  # 300ms delay

    def clear_search(self):
        """Clear search highlighting"""
        self.search_var.set("")
        self.log_text.tag_remove("search_highlight", 1.0, tk.END)
        self.status_var.set("Search cleared")

    def toggle_auto_refresh(self):
        """Toggle auto-refresh functionality"""
        self.auto_refresh = self.auto_refresh_var.get()
        if self.auto_refresh:
            self.status_var.set("Auto-refresh enabled")
        else:
            self.status_var.set("Auto-refresh disabled")

    def auto_refresh_loop(self):
        """Auto-refresh loop for live log viewing"""
        while self.auto_refresh:
            try:
                if self.auto_refresh_var.get():
                    # Check if file has been modified
                    if os.path.exists(self.log_path):
                        current_mtime = os.path.getmtime(self.log_path)
                        if not hasattr(self, "last_mtime") or current_mtime > self.last_mtime:
                            self.last_mtime = current_mtime
                            self.dialog.after(0, self.load_log_content)

                time.sleep(2)  # Check every 2 seconds

            except Exception as e:
                logger.error(f"Auto-refresh error: {e}")
                time.sleep(5)  # Wait longer on error

    def on_closing(self):
        """Handle dialog closing"""
        self.auto_refresh = False
        self.dialog.destroy()


def main():
    """Main function to start the GUI"""
    root = tk.Tk()
    app = BaseStationGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
