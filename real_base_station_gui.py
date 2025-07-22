#!/usr/bin/env python3
"""
real_base_station_gui.py
Ty Young

A GUI for the base station that works with actual bUEs.
This script launches the GUI with real base station functionality.

Usage:
    python3 real_base_station_gui.py [config_file]

If no config file is specified, it will use 'config_base.yaml'
"""

import sys
import os
import threading
import time
import math
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
from datetime import datetime, date, timedelta
from loguru import logger

# Import the base station and constants
from base_station_main import Base_Station_Main
from constants import bUEs, TIMEOUT

class RealBaseStationGUI:
    """GUI for real base station operations"""
    
    def __init__(self, root, config_file="config_base.yaml"):
        self.root = root
        self.config_file = config_file
        self.root.title(f"Base Station Control Panel - {config_file}")
        self.root.geometry("1600x1000")
        
        # Initialize base station
        self.base_station = None
        self.update_thread = None
        self.running = False
        
        # Custom markers for the map
        self.custom_markers = {}  # {marker_id: {'name': str, 'lat': float, 'lon': float, 'paired_bue': int}}
        self.marker_counter = 0
        
        # Status variables
        self.listening_status_var = None  # Will be initialized in setup_gui
        
        # Setup GUI
        self.setup_gui()
        
        # Start base station
        self.start_base_station()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_gui(self):
        """Setup the main GUI layout with all panels always visible"""
        # Create main container with grid layout
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configure grid weights for responsive resizing
        main_frame.grid_columnconfigure(0, weight=1)  # Left column
        main_frame.grid_columnconfigure(1, weight=2)  # Middle column (map)
        main_frame.grid_columnconfigure(2, weight=1)  # Right column
        main_frame.grid_rowconfigure(0, weight=1)     # Top row
        main_frame.grid_rowconfigure(1, weight=1)     # Bottom row
        
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
        self.bue_tree = ttk.Treeview(bue_frame, columns=('status', 'ping'), show='tree headings')
        self.bue_tree.heading('#0', text='bUE ID')
        self.bue_tree.heading('status', text='Status')
        self.bue_tree.heading('ping', text='Ping Status')
        
        self.bue_tree.column('#0', width=100)
        self.bue_tree.column('status', width=100)
        self.bue_tree.column('ping', width=100)
        
        # Scrollbar for treeview
        bue_scrollbar = ttk.Scrollbar(bue_frame, orient=tk.VERTICAL, command=self.bue_tree.yview)
        self.bue_tree.configure(yscrollcommand=bue_scrollbar.set)
        
        self.bue_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        bue_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind right-click context menu
        self.bue_tree.bind("<Button-3>", self.show_bue_context_menu)
        
        # Control buttons frame
        control_frame = ttk.LabelFrame(parent, text="Base Station Controls")
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Connection status indicator (read-only)
        status_frame = ttk.LabelFrame(control_frame, text="Connection Status")
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Status indicator
        self.listening_status_var = tk.StringVar()
        self.listening_status_label = ttk.Label(status_frame, textvariable=self.listening_status_var, 
                                              font=('TkDefaultFont', 10, 'bold'))
        self.listening_status_label.pack(pady=5)
        
        # Test controls
        test_frame = ttk.LabelFrame(control_frame, text="Test Controls")
        test_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(test_frame, text="Run Test", command=self.run_test).pack(fill=tk.X, pady=2)
        ttk.Button(test_frame, text="Cancel Tests", command=self.cancel_tests).pack(fill=tk.X, pady=2)
        
        # Log controls
        log_frame = ttk.LabelFrame(control_frame, text="Logs")
        log_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(log_frame, text="Open Base Station Log", command=self.open_base_log).pack(fill=tk.X, pady=2)
        
        # Map controls frame
        map_control_frame = ttk.LabelFrame(parent, text="Map Controls")
        map_control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(map_control_frame, text="Add Custom Marker", command=self.add_custom_marker).pack(fill=tk.X, pady=2)
        ttk.Button(map_control_frame, text="Manage Markers", command=self.manage_markers).pack(fill=tk.X, pady=2)
    
    def setup_map_view(self, parent):
        """Setup the map view with bUE locations and custom markers"""
        # Map canvas
        self.map_canvas = tk.Canvas(parent, bg='lightblue', width=600, height=300)
        self.map_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Map info frame
        map_info_frame = ttk.Frame(parent)
        map_info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(map_info_frame, text="Legend:").pack(side=tk.LEFT)
        ttk.Label(map_info_frame, text="🔵 bUE", foreground='blue').pack(side=tk.LEFT, padx=5)
        ttk.Label(map_info_frame, text="📍 Marker", foreground='red').pack(side=tk.LEFT, padx=5)
        ttk.Label(map_info_frame, text="🟢 Close", foreground='green').pack(side=tk.LEFT, padx=5)
        
        # Bind canvas events
        self.map_canvas.bind("<Button-1>", self.on_map_click)
        self.map_canvas.bind("<Motion>", self.on_map_hover)
    
    def setup_tables_view(self, parent):
        """Setup the tables view with coordinates and distances"""
        # Create paned window for tables
        tables_paned = ttk.PanedWindow(parent, orient=tk.VERTICAL)
        tables_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Coordinates table
        coord_frame = ttk.LabelFrame(tables_paned, text="bUE Coordinates")
        tables_paned.add(coord_frame, weight=1)
        
        self.coord_tree = ttk.Treeview(coord_frame, columns=('latitude', 'longitude'), show='tree headings')
        self.coord_tree.heading('#0', text='bUE ID')
        self.coord_tree.heading('latitude', text='Latitude')
        self.coord_tree.heading('longitude', text='Longitude')
        self.coord_tree.pack(fill=tk.BOTH, expand=True)
        
        # Distance table
        dist_frame = ttk.LabelFrame(tables_paned, text="bUE Distances")
        tables_paned.add(dist_frame, weight=1)
        
        self.dist_tree = ttk.Treeview(dist_frame, columns=('distance',), show='tree headings')
        self.dist_tree.heading('#0', text='bUE Pair')
        self.dist_tree.heading('distance', text='Distance (m)')
        self.dist_tree.pack(fill=tk.BOTH, expand=True)
    
    def setup_messages_view(self, parent):
        """Setup the messages view"""
        # Messages text area
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
            logger.info(f"Starting base station with config: {self.config_file}")
            self.base_station = Base_Station_Main(self.config_file)
            
            # CRITICAL: Enable the tick system to start listening for bUEs
            # This matches the working main_ui.py implementation
            self.base_station.tick_enabled = True
            
            self.running = True
            
            # Start update thread
            self.update_thread = threading.Thread(target=self.update_loop, daemon=True)
            self.update_thread.start()
            
            self.status_var.set(f"Base Station Listening - Config: {self.config_file}")
            logger.info("Base Station GUI started successfully and listening for bUEs")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start base station: {e}")
            logger.error(f"Failed to start base station: {e}")
            self.status_var.set(f"Error: {e}")
    
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
        
        try:
            self.update_bue_list()
            self.update_map()
            self.update_tables()
            self.update_messages()
            self.update_status()
            
            # Debug logging every 10 seconds
            if hasattr(self, '_debug_counter'):
                self._debug_counter += 1
            else:
                self._debug_counter = 1
            
            if self._debug_counter % 10 == 0:  # Every 10 seconds
                logger.debug(f"GUI Update - Connected bUEs: {len(self.base_station.connected_bues)}, "
                           f"Tick enabled: {getattr(self.base_station, 'tick_enabled', False)}, "
                           f"Has coordinates: {len(getattr(self.base_station, 'bue_coordinates', {}))}")
        except Exception as e:
            logger.error(f"Error updating display: {e}")
    
    def update_bue_list(self):
        """Update the bUE list with current connections and status"""
        # Clear existing items
        for item in self.bue_tree.get_children():
            self.bue_tree.delete(item)
        
        # Add connected bUEs
        for bue_id in self.base_station.connected_bues:
            bue_name = bUEs.get(str(bue_id), f"bUE {bue_id}")
            
            # Determine status
            if hasattr(self.base_station, 'testing_bues') and bue_id in self.base_station.testing_bues:
                status = "🧪 Testing"
            else:
                status = "💤 Idle"
            
            # Determine ping status
            timeout_val = self.base_station.bue_timeout_tracker.get(bue_id, 0)
            if timeout_val >= TIMEOUT / 2:
                ping_status = "🟢 Good"
            elif timeout_val > 0:
                ping_status = "🟡 Warning"
            else:
                ping_status = "🔴 Lost"
            
            self.bue_tree.insert('', 'end', iid=bue_id, text=bue_name, 
                               values=(status, ping_status))
    
    def update_map(self):
        """Update the map with bUE locations and markers"""
        # Clear canvas
        self.map_canvas.delete("all")
        
        if not self.base_station or not hasattr(self.base_station, 'bue_coordinates') or not self.base_station.bue_coordinates:
            self.map_canvas.create_text(300, 200, text="No bUE coordinates available", 
                                      font=("Arial", 14), fill="gray")
            return
        
        # Calculate map bounds
        lats = []
        lons = []
        
        # Get bUE coordinates
        for coords in self.base_station.bue_coordinates.values():
            try:
                lat, lon = float(coords[0]), float(coords[1])
                lats.append(lat)
                lons.append(lon)
            except (ValueError, IndexError, TypeError):
                continue
        
        # Add custom marker coordinates
        for marker in self.custom_markers.values():
            lats.append(marker['lat'])
            lons.append(marker['lon'])
        
        if not lats or not lons:
            self.map_canvas.create_text(300, 200, text="No valid coordinates available", 
                                      font=("Arial", 14), fill="gray")
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
        canvas_width = self.map_canvas.winfo_width() or 600
        canvas_height = self.map_canvas.winfo_height() or 400
        
        # Map coordinate conversion functions
        def lat_to_y(lat):
            return canvas_height - ((lat - min_lat) / (max_lat - min_lat)) * canvas_height
        
        def lon_to_x(lon):
            return ((lon - min_lon) / (max_lon - min_lon)) * canvas_width
        
        # Draw bUEs
        for bue_id, coords in self.base_station.bue_coordinates.items():
            try:
                lat, lon = float(coords[0]), float(coords[1])
                x, y = lon_to_x(lon), lat_to_y(lat)
                
                # Check proximity to custom markers
                is_close = False
                for marker in self.custom_markers.values():
                    if marker.get('paired_bue') == bue_id:
                        distance = self.calculate_distance(lat, lon, marker['lat'], marker['lon'])
                        if distance <= 20:  # 20 meters proximity
                            is_close = True
                            break
                
                # Choose color based on proximity
                color = "green" if is_close else "blue"
                
                # Draw bUE circle
                radius = 8
                self.map_canvas.create_oval(x-radius, y-radius, x+radius, y+radius, 
                                          fill=color, outline="darkblue", width=2, 
                                          tags=f"bue_{bue_id}")
                
                # Label
                bue_name = bUEs.get(str(bue_id), f"bUE {bue_id}")
                self.map_canvas.create_text(x, y-15, text=bue_name, font=("Arial", 8), 
                                          fill="black", tags=f"bue_{bue_id}")
                
            except (ValueError, IndexError, TypeError) as e:
                logger.debug(f"Error plotting bUE {bue_id}: {e}")
        
        # Draw custom markers
        for marker_id, marker in self.custom_markers.items():
            x, y = lon_to_x(marker['lon']), lat_to_y(marker['lat'])
            
            # Draw marker
            radius = 6
            self.map_canvas.create_oval(x-radius, y-radius, x+radius, y+radius, 
                                      fill="red", outline="darkred", width=2, 
                                      tags=f"marker_{marker_id}")
            
            # Label
            self.map_canvas.create_text(x, y-15, text=marker['name'], font=("Arial", 8), 
                                      fill="red", tags=f"marker_{marker_id}")
    
    def update_tables(self):
        """Update coordinate and distance tables"""
        # Update coordinates table
        for item in self.coord_tree.get_children():
            self.coord_tree.delete(item)
        
        if self.base_station and hasattr(self.base_station, 'bue_coordinates'):
            for bue_id, coords in self.base_station.bue_coordinates.items():
                bue_name = bUEs.get(str(bue_id), f"bUE {bue_id}")
                try:
                    lat, lon = coords[0], coords[1]
                    self.coord_tree.insert('', 'end', text=bue_name, values=(lat, lon))
                except (IndexError, ValueError, TypeError):
                    self.coord_tree.insert('', 'end', text=bue_name, values=("Invalid", "Invalid"))
        
        # Update distance table
        for item in self.dist_tree.get_children():
            self.dist_tree.delete(item)
        
        if (self.base_station and 
            hasattr(self.base_station, 'connected_bues') and 
            len(self.base_station.connected_bues) > 1 and
            hasattr(self.base_station, 'bue_coordinates')):
            
            processed_pairs = set()
            for bue1 in self.base_station.connected_bues:
                for bue2 in self.base_station.connected_bues:
                    if (bue1 != bue2 and 
                        bue1 in self.base_station.bue_coordinates and 
                        bue2 in self.base_station.bue_coordinates and
                        (bue1, bue2) not in processed_pairs and
                        (bue2, bue1) not in processed_pairs):
                        
                        if hasattr(self.base_station, 'get_distance'):
                            distance = self.base_station.get_distance(bue1, bue2)
                            if distance is not None:
                                pair_name = f"{bUEs.get(str(bue1), str(bue1))} ↔ {bUEs.get(str(bue2), str(bue2))}"
                                self.dist_tree.insert('', 'end', text=pair_name, values=(f"{distance:.2f}"))
                        
                        processed_pairs.add((bue1, bue2))
    
    def update_messages(self):
        """Update the messages display"""
        if self.base_station and hasattr(self.base_station, 'stdout_history'):
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
        """Update the status bar and connection status"""
        if self.base_station:
            connected = len(self.base_station.connected_bues)
            testing = len(getattr(self.base_station, 'testing_bues', []))
            is_listening = getattr(self.base_station, 'tick_enabled', False)
            
            # Update connection status indicator - always shows listening since it should always be on
            self.listening_status_var.set("🟢 LISTENING FOR bUEs")
            
            # Update main status bar
            current_time = datetime.now().strftime('%H:%M:%S')
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
        if messagebox.askyesno("Confirm Disconnect", f"Disconnect from {bUEs.get(str(bue_id), str(bue_id))}?"):
            try:
                if bue_id in self.base_station.connected_bues:
                    self.base_station.connected_bues.remove(bue_id)
                if hasattr(self.base_station, 'bue_coordinates') and bue_id in self.base_station.bue_coordinates:
                    del self.base_station.bue_coordinates[bue_id]
                if hasattr(self.base_station, 'testing_bues') and bue_id in self.base_station.testing_bues:
                    self.base_station.testing_bues.remove(bue_id)
                if bue_id in self.base_station.bue_timeout_tracker:
                    del self.base_station.bue_timeout_tracker[bue_id]
                logger.info(f"Disconnected from bUE {bue_id}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to disconnect: {e}")
    
    def reload_bue(self, bue_id):
        """Reload a specific bUE"""
        if messagebox.askyesno("Confirm Reload", f"Reload {bUEs.get(str(bue_id), str(bue_id))}?"):
            try:
                if hasattr(self.base_station, 'ota'):
                    self.base_station.ota.send_ota_message(bue_id, "RELOAD")
                    self.disconnect_bue(bue_id)
                    logger.info(f"Sent reload command to bUE {bue_id}")
                else:
                    messagebox.showwarning("Feature Unavailable", "OTA functionality not available")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to reload: {e}")
    
    def restart_bue(self, bue_id):
        """Restart a specific bUE"""
        if messagebox.askyesno("Confirm Restart", f"Restart {bUEs.get(str(bue_id), str(bue_id))}?"):
            try:
                if hasattr(self.base_station, 'ota'):
                    self.base_station.ota.send_ota_message(bue_id, "RESTART")
                    self.disconnect_bue(bue_id)
                    logger.info(f"Sent restart command to bUE {bue_id}")
                else:
                    messagebox.showwarning("Feature Unavailable", "OTA functionality not available")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to restart: {e}")
    
    def open_bue_log(self, bue_id):
        """Open the log file for a specific bUE"""
        log_path = f"logs/bue_{bue_id}.log"
        bue_name = bUEs.get(str(bue_id), f"bUE {bue_id}")
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
        if not hasattr(self.base_station, 'testing_bues') or not self.base_station.testing_bues:
            messagebox.showinfo("No Tests", "No tests currently running")
            return
        
        # Create cancel dialog
        CancelTestDialog(self.root, self.base_station)
    
    def clear_messages(self):
        """Clear the messages display"""
        self.messages_text.delete(1.0, tk.END)
        if self.base_station and hasattr(self.base_station, 'stdout_history'):
            self.base_station.stdout_history.clear()
    
    def add_custom_marker(self):
        """Add a custom marker to the map"""
        AddMarkerDialog(self.root, self)
    
    def manage_markers(self):
        """Manage existing custom markers"""
        ManageMarkersDialog(self.root, self)
    
    def on_map_click(self, event):
        """Handle map click events"""
        pass
    
    def on_map_hover(self, event):
        """Handle map hover events"""
        pass
    
    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance between two coordinates in meters"""
        # Haversine formula
        R = 6371000  # Earth's radius in meters
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat/2) * math.sin(delta_lat/2) + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * 
             math.sin(delta_lon/2) * math.sin(delta_lon/2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def on_closing(self):
        """Handle application closing"""
        if messagebox.askokcancel("Quit", "Do you want to quit the Base Station GUI?"):
            self.running = False
            if self.base_station:
                try:
                    self.base_station.EXIT = True
                    if hasattr(self.base_station, '__del__'):
                        self.base_station.__del__()
                except Exception as e:
                    logger.error(f"Error closing base station: {e}")
            self.root.destroy()


# Import the dialog classes from the main GUI
from base_station_gui import TestDialog, CancelTestDialog, AddMarkerDialog, ManageMarkersDialog, LogViewerDialog


def main():
    """Main function to start the real GUI"""
    # Get config file from command line arguments
    config_file = "config_base.yaml"
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
        if not os.path.exists(config_file):
            print(f"Error: Config file '{config_file}' not found")
            sys.exit(1)
    
    print(f"Starting Base Station GUI with config: {config_file}")
    
    root = tk.Tk()
    app = RealBaseStationGUI(root, config_file)
    root.mainloop()


if __name__ == "__main__":
    main()
