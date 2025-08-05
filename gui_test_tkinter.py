#!/usr/bin/env python3
"""
Test script for the tkinter base station GUI with mock data
This will populate the GUI with fake bUEs, coordinates, and messages
so you can see how all the features work.
"""

import sys
import os
import threading
import time
import random
from datetime import datetime
from collections import deque

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from base_station_gui import BaseStationGUI


class MockOta:
    """Mock OTA communication for testing"""

    def __init__(self, port, baudrate, ota_id):
        self.id = ota_id

    def send_ota_message(self, bue_id, message):
        print(f"Mock OTA: Sending to bUE {bue_id}: {message}")

    def get_new_messages(self):
        return []  # No new messages for testing


class MockBaseStation:
    """Mock base station with realistic test data"""

    def __init__(self):
        # Basic setup
        self.EXIT = False
        self.tick_enabled = True

        # Mock OTA
        self.ota = MockOta("/dev/ttyUSB0", 9600, 1)

        # Connected bUEs with realistic IDs
        self.connected_bues = [10, 20, 30, 40]

        # Testing status - no bUEs start in testing mode
        self.testing_bues = []

        # Realistic coordinates (around BYU campus area)
        self.bue_coordinates = {
            10: [40.2518, -111.6493],  # BYU campus area
            20: [40.2528, -111.6503],  # Slightly north
            30: [40.2508, -111.6483],  # Slightly south
            40: [40.2538, -111.6513],  # Further north
        }

        # Timeout tracking - different connection qualities
        self.bue_timeout_tracker = {
            10: 8,  # Excellent connection
            20: 5,  # Good connection
            30: 2,  # Warning - poor connection
            40: 0,  # Lost connection
        }

        # Message history with realistic test messages
        self.stdout_history = deque(
            [
                "[helloworld.py] Starting test execution...",
                "[gpstest.py] GPS lock acquired, lat: 40.2518, lon: -111.6493",
                "[lora_tu_rd.py] LoRa transmission successful",
                "[helloworld.py] Test completed successfully",
                "[gpstest2.py] GPS accuracy: 3.2m",
                "[lora_td_ru.py] Received signal strength: -85 dBm",
                "[helloworld.py] Memory usage: 45%",
                "[gpstest.py] Satellite count: 8",
                "[custom_test.py] Battery level: 87%",
                "[system_info.py] Temperature: 23.5°C",
            ],
            maxlen=10,
        )

        # Start mock update thread to simulate dynamic data
        self.mock_thread = threading.Thread(target=self.mock_updates, daemon=True)
        self.mock_thread.start()

    def send_test_to_bue(self, bue_id, test_script):
        """Simulate sending a test to a bUE (like PREPR message)"""
        if bue_id in self.connected_bues and bue_id not in self.testing_bues:
            self.testing_bues.append(bue_id)
            self.stdout_history.append(f"[test_manager.py] PREPR sent to bUE {bue_id} for {test_script}")

            # Simulate test completion after random time (5-15 seconds)
            completion_delay = random.uniform(5, 15)
            completion_timer = threading.Timer(completion_delay, self._complete_test, args=[bue_id])
            completion_timer.daemon = True
            completion_timer.start()

    def _complete_test(self, bue_id):
        """Internal method to simulate test completion"""
        if bue_id in self.testing_bues:
            self.testing_bues.remove(bue_id)
            completion_type = random.choice(["DONE", "FAIL"])
            self.stdout_history.append(f"[test_manager.py] Test {completion_type} on bUE {bue_id}")

    def cancel_test_on_bue(self, bue_id):
        """Simulate canceling a test on a bUE (like CANCD message)"""
        if bue_id in self.testing_bues:
            self.testing_bues.remove(bue_id)
            self.stdout_history.append(f"[test_manager.py] CANCD sent to bUE {bue_id} - test cancelled")

    def mock_updates(self):
        """Simulate dynamic updates to the base station data"""
        message_templates = [
            "[test_script.py] Processing data...",
            "[gps_monitor.py] Position updated",
            "[sensor_read.py] Temperature: {temp}°C",
            "[battery_check.py] Battery: {battery}%",
            "[signal_test.py] RSSI: {rssi} dBm",
            "[memory_check.py] RAM usage: {mem}%",
            "[network_test.py] Ping successful",
            "[data_logger.py] Log entry created",
        ]

        counter = 0
        while not self.EXIT:
            time.sleep(3)  # Update every 3 seconds

            # Simulate changing coordinates slightly (GPS drift)
            for bue_id in self.bue_coordinates:
                current_coords = self.bue_coordinates[bue_id]
                # Add small random movement (GPS drift simulation)
                lat_drift = random.uniform(-0.0001, 0.0001)  # ~10 meter drift
                lon_drift = random.uniform(-0.0001, 0.0001)

                new_lat = current_coords[0] + lat_drift
                new_lon = current_coords[1] + lon_drift
                self.bue_coordinates[bue_id] = [new_lat, new_lon]

            # Simulate changing connection quality
            for bue_id in self.bue_timeout_tracker:
                # Random connection quality changes
                change = random.randint(-1, 1)
                current_val = self.bue_timeout_tracker[bue_id]
                new_val = max(0, min(8, current_val + change))
                self.bue_timeout_tracker[bue_id] = new_val

            # Add new mock messages occasionally
            if counter % 2 == 0:  # Every 6 seconds
                template = random.choice(message_templates)
                if "{temp}" in template:
                    message = template.format(temp=round(random.uniform(20, 30), 1))
                elif "{battery}" in template:
                    message = template.format(battery=random.randint(70, 95))
                elif "{rssi}" in template:
                    message = template.format(rssi=random.randint(-95, -70))
                elif "{mem}" in template:
                    message = template.format(mem=random.randint(30, 80))
                else:
                    message = template

                self.stdout_history.append(message)

            counter += 1

    def get_distance(self, bue_1, bue_2):
        """Calculate distance between two bUEs (simplified for testing)"""
        try:
            c1 = self.bue_coordinates[bue_1]
            c2 = self.bue_coordinates[bue_2]

            # Simple distance calculation (not great circle, but good for testing)
            lat_diff = c1[0] - c2[0]
            lon_diff = c1[1] - c2[1]

            # Convert to approximate meters (rough calculation)
            lat_meters = lat_diff * 111000  # 1 degree lat ≈ 111km
            lon_meters = lon_diff * 111000 * 0.8  # Adjust for longitude at this latitude

            distance = (lat_meters**2 + lon_meters**2) ** 0.5
            return distance

        except Exception as e:
            print(f"Error calculating distance: {e}")
            return None


def create_test_gui():
    """Create and run the test GUI with mock data"""
    root = tk.Tk()

    # Create the GUI but override the base station with our mock
    gui = BaseStationGUI(root)

    # Replace the real base station with our mock
    if gui.base_station:
        gui.base_station.EXIT = True  # Stop the real base station

    gui.base_station = MockBaseStation()

    # Add some test custom markers
    gui.custom_markers = {
        0: {
            "name": "Building A",
            "lat": 40.2520,
            "lon": -111.6495,
            "paired_bue": 10,  # Paired with bUE 10
        },
        1: {
            "name": "Parking Lot",
            "lat": 40.2530,
            "lon": -111.6505,
            "paired_bue": None,  # Not paired
        },
        2: {
            "name": "Test Point C",
            "lat": 40.2510,
            "lon": -111.6485,
            "paired_bue": 30,  # Paired with bUE 30
        },
    }
    gui.marker_counter = 3

    # Update the status
    gui.status_var.set("Mock Base Station Running - Test Data Active")

    print("🚀 Test GUI launched with mock data!")
    print("Features to test:")
    print("  - Connected bUEs: 10, 20, 30, 40")
    print("  - Testing bUEs: 10, 30 (changes dynamically)")
    print("  - Map shows bUE locations around BYU campus")
    print("  - Custom markers with proximity detection")
    print("  - Live message updates every few seconds")
    print("  - Connection quality changes dynamically")
    print("  - Right-click bUEs for context menu")
    print("  - Try adding/managing custom markers")
    print("  - Watch proximity detection (bUEs turn green near paired markers)")

    return gui


if __name__ == "__main__":
    print("Starting tkinter GUI test with mock data...")
    gui = create_test_gui()
    gui.root.mainloop()
