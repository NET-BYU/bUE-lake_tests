# Real Base Station GUI

This script provides a GUI interface for controlling the base station with actual bUEs.

## Files Created

- `real_base_station_gui.py` - Main GUI script for real base station operations
- `launch_gui.sh` - Launcher script with environment setup and error checking

## Usage

### Option 1: Using the launcher script (Recommended)
```bash
./launch_gui.sh                    # Uses config_base.yaml
./launch_gui.sh my_config.yaml     # Uses custom config file
```

### Option 2: Direct Python execution
```bash
python3 real_base_station_gui.py                    # Uses config_base.yaml  
python3 real_base_station_gui.py my_config.yaml     # Uses custom config file
```

## Features

The real GUI includes all the features from the test GUI but works with actual bUEs:

### Connection Management
- **Start/Stop Listening** - Control whether the base station accepts new connections
- **Connected bUEs List** - Shows all connected bUEs with status indicators
- **Right-click Context Menu** - Disconnect, reload, restart, or view logs for any bUE

### Testing
- **Run Tests** - Configure and execute tests on connected bUEs
- **Cancel Tests** - Stop running tests
- **Test Delay** - Set how long to wait before starting tests

### Monitoring
- **Real-time Map** - Shows bUE locations based on actual GPS coordinates
- **Custom Markers** - Add and manage custom markers on the map
- **Proximity Detection** - bUEs change color when close to paired markers
- **Data Tables** - Live coordinates and distance calculations
- **Message Display** - Real-time message log from base station

### Log Viewing
- **Base Station Log** - View base station logs within the GUI
- **Individual bUE Logs** - View logs for specific bUEs
- **Auto-refresh** - Logs update automatically as new messages arrive

## Key Differences from Test GUI

1. **Real Base Station Integration** - Uses actual `Base_Station_Main` instance
2. **Connection Controls** - Start/stop listening for bUE connections  
3. **Error Handling** - Robust error handling for real-world conditions
4. **Configuration Support** - Can use different config files
5. **Log Integration** - Works with actual log files in `logs/` directory

## Prerequisites

1. **Configuration File** - Ensure you have a valid config file (e.g., `config_base.yaml`)
2. **Virtual Environment** - The launcher will try to activate `uw_env` if it exists
3. **Log Directory** - Ensure `logs/` directory exists for log file viewing
4. **Required Python Packages** - Same as your existing base station setup

## Troubleshooting

### GUI Won't Start
- Check that config file exists and is valid
- Verify all required Python packages are installed
- Check that `base_station_main.py` and `constants.py` are present

### No bUEs Connecting
**CRITICAL**: The base station must be properly listening for connections.

1. **Check the Status Indicator**: The GUI should show "🟢 LISTENING FOR bUEs" in green
2. **Verify Config File**: Make sure your `config_base.yaml` has correct network settings
3. **Test Base Station Independently**: 
   ```bash
   python3 test_base_station.py
   ```
   This will run a simple test to verify the base station is working without the GUI
4. **Check bUE Configuration**: Ensure your bUEs are configured to connect to the correct base station address/port
5. **Monitor Logs**: Check `logs/base_station.log` for connection attempts and errors
6. **Compare with Working Terminal Interface**: Your terminal `main_ui.py` should work - if it doesn't, the issue is with the base station setup, not the GUI

### GUI Shows "Not Listening"
- The base station automatically starts listening when initialized
- If it shows "Not Listening", click "Start Listening" button
- Check the base station log for any initialization errors

### Map Not Showing bUEs
- bUEs must send GPS coordinates to appear on map
- Check that bUEs have valid GPS fixes
- Verify coordinate format matches expected format (latitude, longitude as strings/floats)

### Logs Not Opening
- Ensure `logs/` directory exists
- Check file permissions on log files
- Verify log file paths match those used by your base station

## Testing Connection Issues

### Step 1: Test Base Station Independently
```bash
python3 test_base_station.py
```
This script mimics your working `main_ui.py` structure and will show:
- If the base station initializes correctly
- If it's listening for connections
- Real-time connection status
- Any bUE connection attempts

### Step 2: Compare with Terminal Interface
If the test script above doesn't work, but your `main_ui.py` does work, then:
1. Check the differences in configuration
2. Ensure the same config file is being used
3. Verify the same Python environment

### Step 3: Use the GUI
Once the test script shows bUEs connecting, the GUI should work identically.

## Integration Notes

This GUI is designed to work alongside your existing base station infrastructure. It:

- Uses the same `Base_Station_Main` class as your terminal interface
- Works with the same config files and log files
- Maintains compatibility with existing bUE communication protocols
- Can be used as a drop-in replacement for the terminal interface

The GUI provides all the functionality you had in `main_ui.py` but with a modern, user-friendly interface.
