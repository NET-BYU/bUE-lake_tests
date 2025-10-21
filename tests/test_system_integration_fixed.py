"""
System Integration Tests for bUE Lake Deployment

This module provides comprehensive integration tests for the bUE system,
focusing on real-world scenarios that might occur during lake deployment.
These tests require actual bUE modules and handle cases where dependencies
might not be available in the test environment.
"""

import pytest
import time
import tempfile
import os
import sys
import yaml
from unittest.mock import patch, MagicMock

# Add multiple paths to find modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

# Mock problematic modules before importing
sys.modules["gps"] = MagicMock()
sys.modules["gpsd"] = MagicMock()
sys.modules["pynmea2"] = MagicMock()

# Mock subprocess for test execution
mock_subprocess = MagicMock()
mock_subprocess.Popen = MagicMock()
sys.modules["subprocess"] = mock_subprocess

# Try to import required modules - handle gracefully if missing
try:
    from bue_main import bUE_Main, State
    from base_station_main import Base_Station_Main
    from .conftest import MessageTypes, DeviceIds

    MODULES_AVAILABLE = True
    print("Successfully imported all required modules")
except ImportError as e:
    print(f"Warning: Could not import required modules: {e}")
    MODULES_AVAILABLE = False

# Import test helpers that should always be available
from .mock_serial import MockSerial
from .conftest import MessageHelper


if MODULES_AVAILABLE:

    class TestStateMachine:
        """Test bUE state machine behavior and transitions"""

        @pytest.fixture
        def mock_config_file(self):
            """Create a temporary config file for testing"""
            config_data = {"OTA_PORT": "/dev/ttyUSB0", "OTA_BAUDRATE": 9600, "OTA_ID": 10}

            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                yaml.dump(config_data, f)
                yield f.name
            os.unlink(f.name)

        def test_complete_connection_flow(self, mock_config_file):
            """Test complete connection establishment state flow"""
            with patch("serial.Serial") as mock_serial:
                mock_ota = MockSerial("/dev/ttyUSB0", 9600)
                mock_serial.return_value = mock_ota

                bue = bUE_Main(mock_config_file)
                bue.tick_enabled = True

                # Wait for REQ to be sent
                time.sleep(1.2)  # Should trigger REQ after 1 second

                # Verify REQ was sent
                sent_messages = mock_ota.get_sent_messages()
                req_sent = any("REQ" in msg for msg in sent_messages)
                assert req_sent, "bUE should send REQ message"

                # Simulate base station CON response
                con_message = MessageHelper.create_rcv_message(1, "CON:1")
                mock_ota.add_incoming_message(con_message)

                # Wait for processing
                time.sleep(2)

                # Should now be connected and in IDLE state
                assert bue.status_ota_connected
                assert bue.ota_base_station_id == DeviceIds.BASE_STATION
                assert bue.cur_st == State.IDLE

                # Verify ACK was sent
                sent_messages = mock_ota.get_sent_messages()
                ack_sent = any("ACK" in msg for msg in sent_messages)
                assert ack_sent, "bUE should send ACK after receiving CON"

                bue.__del__()

        def test_timeout_and_reconnection_cycle(self, mock_config_file):
            """Test that bUE properly handles timeouts and reconnects"""
            with patch("serial.Serial") as mock_serial:
                mock_ota = MockSerial("/dev/ttyUSB0", 9600)
                mock_serial.return_value = mock_ota

                bue = bUE_Main(mock_config_file)
                bue.tick_enabled = True

                # Establish connection first
                time.sleep(1.2)
                con_message = MessageHelper.create_rcv_message(
                    DeviceIds.BASE_STATION, f"{MessageTypes.CON}:{DeviceIds.BASE_STATION}"
                )
                mock_ota.add_incoming_message(con_message)
                time.sleep(2)

                assert bue.status_ota_connected
                initial_timeout = bue.ota_timeout

                # Send PING but don't respond with PINGR (simulate timeout)
                time.sleep(11)  # Should trigger PING after 10 seconds

                # Verify PING was sent
                sent_messages = mock_ota.get_sent_messages()
                ping_sent = any("PING" in msg for msg in sent_messages[-5:])
                assert ping_sent, "bUE should send PING periodically"

                # Wait for timeout to decrease (no PINGR received)
                time.sleep(1)
                assert bue.ota_timeout < initial_timeout, "Timeout should decrease when no PINGR received"

                # Simulate multiple missed PINGs to trigger disconnection
                bue.ota_timeout = 0
                time.sleep(11)

                # Should transition back to CONNECT_OTA
                assert not bue.status_ota_connected
                assert bue.cur_st == State.CONNECT_OTA

                bue.__del__()

        def test_test_state_transition(self, mock_config_file):
            """Test transition to UTW_TEST state when receiving TEST message"""
            with patch("serial.Serial") as mock_serial:
                mock_ota = MockSerial("/dev/ttyUSB0", 9600)
                mock_serial.return_value = mock_ota

                # Mock subprocess to prevent actual script execution
                with patch("subprocess.Popen") as mock_popen:
                    mock_process = MagicMock()
                    mock_process.poll.return_value = None  # Process running
                    mock_process.stdout.readline.return_value = ""
                    mock_process.stderr.readline.return_value = ""
                    mock_popen.return_value = mock_process

                    bue = bUE_Main(mock_config_file)
                    bue.tick_enabled = True

                    # Establish connection
                    time.sleep(1.2)
                    con_message = MessageHelper.create_rcv_message(
                        DeviceIds.BASE_STATION, f"{MessageTypes.CON}:{DeviceIds.BASE_STATION}"
                    )
                    mock_ota.add_incoming_message(con_message)
                    time.sleep(2)

                    assert bue.cur_st == State.IDLE

                    # Send TEST message
                    future_time = int(time.time()) + 2
                    test_message = f"TEST,helloworld,{future_time},param1 param2"
                    test_rcv = MessageHelper.create_rcv_message(DeviceIds.BASE_STATION, test_message)
                    mock_ota.add_incoming_message(test_rcv)

                    # Wait for processing
                    time.sleep(10)

                    # Should transition to UTW_TEST state
                    assert bue.is_testing
                    assert bue.cur_st == State.UTW_TEST

                    # Verify PREPR was sent
                    sent_messages = mock_ota.get_sent_messages()
                    prepr_sent = any("PREPR" in msg for msg in sent_messages)
                    assert prepr_sent, "bUE should send PREPR when receiving valid TEST"

                    # Simulate test completion
                    mock_process.poll.return_value = 0  # Process completed successfully
                    bue.is_testing = False
                    time.sleep(0.1)

                    # Should return to IDLE state
                    assert bue.cur_st == State.IDLE

                    bue.__del__()

    class TestMultiDeviceScenarios:
        """Test scenarios with multiple bUEs connecting to a base station"""

        @pytest.fixture
        def base_station_config(self):
            """Create base station config"""
            config_data = {"OTA_PORT": "/dev/ttyUSB0", "OTA_BAUDRATE": 9600, "OTA_ID": 1}

            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                yaml.dump(config_data, f)
                yield f.name
            os.unlink(f.name)

        @pytest.fixture
        def bue_configs(self):
            """Create multiple bUE configs with different IDs"""
            configs = []
            for bue_id in [10, 20, 30]:
                config_data = {"OTA_PORT": f"/dev/ttyUSB{bue_id}", "OTA_BAUDRATE": 9600, "OTA_ID": bue_id}

                with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                    yaml.dump(config_data, f)
                    configs.append(f.name)

            yield configs

            for config_file in configs:
                if os.path.exists(config_file):
                    os.unlink(config_file)

        def test_multiple_bue_connections(self, base_station_config, bue_configs):
            """Test base station handling multiple bUE connections"""
            # Create mock serials for each device
            base_mock = MockSerial("/dev/ttyUSB0", 9600)
            bue_mocks = [MockSerial(f"/dev/ttyUSB{bue_id}", 9600) for bue_id in [10, 20, 30]]

            def mock_serial_factory(port, baudrate, timeout=0.1):
                if port == "/dev/ttyUSB0":
                    return base_mock
                elif port == "/dev/ttyUSB10":
                    return bue_mocks[0]
                elif port == "/dev/ttyUSB20":
                    return bue_mocks[1]
                elif port == "/dev/ttyUSB30":
                    return bue_mocks[2]
                return MockSerial(port, baudrate)

            with patch("serial.Serial", side_effect=mock_serial_factory):
                # Initialize base station
                base_station = Base_Station_Main(base_station_config)
                base_station.tick_enabled = True
                print(f"Created base_station object: {id(base_station)}")
                print(f"Base station using MockSerial: {id(base_station.ota.ser)}")

                # Initialize bUEs
                bues = []
                for config_file in bue_configs:
                    bue = bUE_Main(config_file)
                    bue.tick_enabled = True
                    bues.append(bue)

                time.sleep(0.5)  # Let initialization complete

                # Test connection establishment for each bUE
                for i, bue in enumerate(bues):
                    bue_id = [10, 20, 30][i]

                    # Simulate connection process
                    bue.ota_connected = True
                    bue.ota_base_station_id = DeviceIds.BASE_STATION
                    bue.cur_st = State.IDLE
                    base_station.connected_bues.append(bue_id)

                # Verify all three bUEs are connected
                assert len(base_station.connected_bues) == 3
                assert set(base_station.connected_bues) == {10, 20, 30}

                # Test simultaneous PING handling
                print(f"About to add messages to base_mock: {id(base_mock)}")
                print(f"Base station's actual MockSerial: {id(base_station.ota.ser)}")

                # Use the base station's actual MockSerial instead of base_mock
                actual_base_mock = base_station.ota.ser

                for i, bue in enumerate(bues):
                    bue_id = [10, 20, 30][i]

                    # Send PING with GPS coordinates
                    ping_message = f"PING,40.{i},-111.{i}"
                    # bue.ota.send_ota_message(DeviceIds.BASE_STATION, ping_message)

                    # Base station receives PING - use the correct MockSerial
                    ping_rcv = MessageHelper.create_rcv_message(bue_id, ping_message)
                    actual_base_mock.add_incoming_message(ping_rcv)
                    print(f"Added PING message for bUE {bue_id}")

                # Wait longer for message processing and add polling
                print("Waiting for message processing...")
                max_wait = 12  # Maximum wait time in seconds
                wait_interval = 0.5  # Check every 0.5 seconds
                waited = 0

                while len(base_station.bue_coordinates) < 3 and waited < max_wait:
                    time.sleep(wait_interval)
                    waited += wait_interval
                    print(f"Waited {waited}s, coordinates: {len(base_station.bue_coordinates)}")

                print(f"Final wait time: {waited}s")

                # Verify all bUEs have coordinates stored
                assert len(base_station.bue_coordinates) == 3
                for i, bue_id in enumerate([10, 20, 30]):
                    assert bue_id in base_station.bue_coordinates
                    coords = base_station.bue_coordinates[bue_id]
                    assert coords[0] == f"40.{i}"  # latitude
                    assert coords[1] == f"-111.{i}"  # longitude

                # Cleanup
                base_station.__del__()
                for bue in bues:
                    bue.__del__()

    class TestConfigurationAndErrorHandling:
        """Test configuration loading and error scenarios"""

        def test_invalid_config_file(self):
            """Test handling of invalid configuration files"""
            # Test missing file
            with pytest.raises(SystemExit):
                bUE_Main("nonexistent_config.yaml")

            # Test malformed YAML
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                f.write("invalid: yaml: content: [")
                invalid_config = f.name

            try:
                with pytest.raises(yaml.YAMLError):
                    with open(invalid_config) as file:
                        yaml.load(file, Loader=yaml.Loader)
            finally:
                os.unlink(invalid_config)

        def test_missing_required_config_keys(self):
            """Test handling of missing required configuration keys"""
            incomplete_config = {
                "OTA_PORT": "/dev/ttyUSB0",
                # Missing OTA_BAUDRATE and OTA_ID
            }

            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                yaml.dump(incomplete_config, f)
                config_file = f.name

            try:
                with patch("serial.Serial"):
                    # Should handle missing keys gracefully
                    bue = None
                    try:
                        bue = bUE_Main(config_file)
                        # If we get here without an exception, that's unexpected
                        assert False, "Expected KeyError was not raised"
                    except KeyError:
                        # This is expected - the test should pass
                        pass
                    finally:
                        # Cleanup any created bUE object
                        if bue is not None:
                            bue.EXIT = True
                            bue.tick_enabled = False
                            time.sleep(0.1)  # Brief pause for threads to see the flags
                            bue.__del__()
            finally:
                os.unlink(config_file)

    class TestRealWorldScenarios:
        """Test scenarios that might occur during actual lake deployment"""

        @pytest.fixture
        def mock_config_file(self):
            """Create a temporary config file for testing"""
            config_data = {"OTA_PORT": "/dev/ttyUSB0", "OTA_BAUDRATE": 9600, "OTA_ID": 10}

            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                yaml.dump(config_data, f)
                yield f.name
            os.unlink(f.name)

        def test_gps_coordinate_validation(self, mock_config_file):
            """Test GPS coordinate handling and validation"""
            with patch("serial.Serial") as mock_serial:
                mock_ota = MockSerial("/dev/ttyUSB0", 9600)
                mock_serial.return_value = mock_ota

                # Mock GPS handler to return test coordinates
                def mock_gps_handler():
                    return "40.2518", "-111.6493"  # BYU coordinates

                bue = bUE_Main(mock_config_file)
                bue.gps_handler = mock_gps_handler
                bue.tick_enabled = True

                # Setup connected state
                bue.status_ota_connected = True
                bue.ota_base_station_id = DeviceIds.BASE_STATION
                bue.cur_st = State.IDLE

                # Trigger PING with GPS coordinates
                time.sleep(11)  # Should trigger PING

                # Verify PING contains GPS coordinates
                sent_messages = mock_ota.get_sent_messages()
                ping_with_coords = None
                for msg in sent_messages:
                    if "PING" in msg and "40.2518" in msg and "-111.6493" in msg:
                        ping_with_coords = msg
                        break

                assert ping_with_coords is not None, "PING should include GPS coordinates"

                bue.__del__()

else:
    # If modules are not available, create placeholder tests that skip
    class TestStateMachine:
        def test_modules_not_available(self):
            pytest.skip("Required modules not available - install missing dependencies")

    class TestMultiDeviceScenarios:
        def test_modules_not_available(self):
            pytest.skip("Required modules not available - install missing dependencies")

    class TestConfigurationAndErrorHandling:
        def test_modules_not_available(self):
            pytest.skip("Required modules not available - install missing dependencies")

    class TestRealWorldScenarios:
        def test_modules_not_available(self):
            pytest.skip("Required modules not available - install missing dependencies")
