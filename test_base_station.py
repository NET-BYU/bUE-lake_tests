#!/usr/bin/env python3
"""
test_base_station.py
Ty Young

A simple test script to verify the base station is working correctly without GUI.
This matches the working main_ui.py structure to help debug connection issues.
"""

import sys
import time
import threading
from datetime import datetime
from loguru import logger

from base_station_main import Base_Station_Main


def test_base_station(config_file="config_base.yaml"):
    """Test the base station functionality"""
    print(f"Testing Base Station with config: {config_file}")
    print("=" * 50)

    try:
        # Initialize base station (same as working main_ui.py)
        base_station = Base_Station_Main(config_file)

        # CRITICAL: Enable tick system (same as main_ui.py)
        base_station.tick_enabled = True

        print(f"✅ Base station initialized successfully")
        print(f"✅ Tick system enabled: {base_station.tick_enabled}")
        print(f"✅ OTA ID: {base_station.ota.id}")
        print(f"✅ Connected bUEs: {base_station.connected_bues}")
        print("")
        print("🔍 Listening for bUE connections...")
        print("   (Press Ctrl+C to stop)")
        print("")

        # Monitor for connections
        start_time = time.time()
        last_status_time = 0

        while True:
            current_time = time.time()

            # Print status every 5 seconds
            if current_time - last_status_time >= 5:
                elapsed = int(current_time - start_time)
                connected_count = len(base_station.connected_bues)
                testing_count = len(getattr(base_station, "testing_bues", []))

                print(
                    f"[{elapsed:03d}s] Connected: {connected_count} | Testing: {testing_count} | "
                    f"Listening: {base_station.tick_enabled}"
                )

                if connected_count > 0:
                    print(f"      📡 Connected bUEs: {base_station.connected_bues}")
                    if (
                        hasattr(base_station, "bue_coordinates")
                        and base_station.bue_coordinates
                    ):
                        print(
                            f"      📍 Coordinates available for: {list(base_station.bue_coordinates.keys())}"
                        )

                if testing_count > 0:
                    print(f"      🧪 Testing bUEs: {base_station.testing_bues}")

                # Show recent messages
                if (
                    hasattr(base_station, "stdout_history")
                    and base_station.stdout_history
                ):
                    recent_msgs = list(base_station.stdout_history)[
                        -2:
                    ]  # Last 2 messages
                    for msg in recent_msgs:
                        print(f"      💬 Recent: {msg}")

                print("")
                last_status_time = current_time

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n🛑 Stopping base station test...")
        if "base_station" in locals():
            base_station.EXIT = True
            time.sleep(0.5)
            base_station.__del__()
        print("✅ Test completed")

    except Exception as e:
        print(f"❌ Error: {e}")
        logger.error(f"Base station test failed: {e}")
        return False

    return True


def main():
    """Main function"""
    config_file = "config_base.yaml"
    if len(sys.argv) > 1:
        config_file = sys.argv[1]

    if not test_base_station(config_file):
        sys.exit(1)


if __name__ == "__main__":
    main()
