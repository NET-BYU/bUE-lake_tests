#!/usr/bin/env python3
"""
Simple test script to run the GUI with mock base station data
"""

import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent_gui import Gui

class MockBaseStation:
    """Mock base station for testing the GUI"""
    def __init__(self):
        self.connected_bues = [10, 20, 30]  # Some mock connected bUEs
        self.testing_bues = [10]  # bUE 10 is currently testing
        self.bue_coordinates = {
            10: (40.4456, -111.4937),
            20: (40.4466, -111.4947),
            30: (40.4476, -111.4957)
        }
        self.bue_timeout_tracker = {
            10: 6,  # Good connection
            20: 3,  # Warning
            30: 0   # Lost connection
        }
        self.EXIT = False

if __name__ == "__main__":
    # Create mock base station
    base_station = MockBaseStation()
    
    # Create and run GUI
    app = Gui(base_station)
    app.mainloop()
