#!/bin/bash
# 
# launch_gui.sh
# Launcher script for the real base station GUI
#
# Usage:
#   ./launch_gui.sh [config_file]
#
# If no config file is specified, uses config_base.yaml

CONFIG_FILE="${1:-config_base.yaml}"

echo "==================================="
echo "Base Station GUI Launcher"
echo "==================================="
echo "Config file: $CONFIG_FILE"
echo "Working directory: $(pwd)"
echo "Python version: $(python3 --version)"
echo "==================================="

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: Config file '$CONFIG_FILE' not found!"
    echo "Available config files:"
    ls -la *.yaml 2>/dev/null || echo "No .yaml files found"
    exit 1
fi

# Check if virtual environment exists and activate it
if [ -d "uw_env" ]; then
    echo "Activating virtual environment..."
    source uw_env/bin/activate
    echo "Virtual environment activated: $VIRTUAL_ENV"
else
    echo "WARNING: No virtual environment found at 'uw_env'"
    echo "Using system Python"
fi

# Check if required files exist
REQUIRED_FILES=("real_base_station_gui.py" "base_station_main.py" "constants.py" "base_station_gui.py")
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "ERROR: Required file '$file' not found!"
        exit 1
    fi
done

echo "==================================="
echo "Starting Base Station GUI..."
echo "Press Ctrl+C to stop"
echo ""
echo "IMPORTANT:"
echo "1. Make sure your bUEs are configured to connect to this base station"
echo "2. Check that the base station shows 'LISTENING FOR bUEs' status"
echo "3. Monitor the base station log for connection messages"
echo "4. If no bUEs connect, check your config file network settings"
echo "==================================="

# Run the GUI
python3 real_base_station_gui.py "$CONFIG_FILE"
