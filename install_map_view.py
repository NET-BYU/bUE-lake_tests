#!/usr/bin/env python3
"""
Installation script for TkinterMapView
Run this to install the required package for interactive maps in the uw_env virtual environment
"""

import subprocess
import sys
import os

def install_tkinter_map_view():
    """Install TkinterMapView using pip in the uw_env virtual environment"""
    try:
        # Check if we're in the correct directory
        if not os.path.exists("uw_env"):
            print("❌ uw_env virtual environment not found!")
            print("Make sure you're running this script from the bUE-lake_tests directory.")
            return False
            
        print("Installing TkinterMapView in uw_env virtual environment...")
        # Use the virtual environment's pip
        pip_path = os.path.join("uw_env", "bin", "pip")
        subprocess.check_call([pip_path, "install", "tkintermapview"])
        print("✅ TkinterMapView installed successfully in uw_env!")
        print("You can now use the interactive map feature in the Base Station GUI.")
        print("Run the GUI with: source uw_env/bin/activate && python base_station_gui.py")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install TkinterMapView: {e}")
        print("You can still use the Base Station GUI with the fallback canvas map.")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during installation: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Base Station GUI - Interactive Map Setup")
    print("=" * 60)
    print()
    
    success = install_tkinter_map_view()
    
    print()
    print("=" * 60)
    if success:
        print("🎉 Setup completed successfully!")
        print("Start the GUI with: source uw_env/bin/activate && python base_station_gui.py")
        print("The interactive map will be available by default.")
    else:
        print("⚠️  Interactive map not available")
        print("The GUI will still work with the basic canvas map.")
        print("Start the GUI with: source uw_env/bin/activate && python base_station_gui.py")
    print("=" * 60)
