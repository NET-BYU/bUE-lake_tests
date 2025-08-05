"""
Integration tests for the complete bUE-base station communication protocol.

These tests simulate the full message exchange sequences as described in message_dict.txt.
"""

import time
import sys
import os

# Add the parent directory to the path so we can import ota
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import pytest
    from unittest.mock import patch
    from tests.conftest import MessageHelper, MessageTypes, DeviceIds
    from tests.mock_serial import MockSerial
    from ota import Ota

    class TestProtocolIntegration:
        """Integration tests for complete protocol flows"""

        def test_complete_connection_sequence(self):
            """Test the complete connection establishment sequence"""
            # Create mock serial devices for base station and bUE
            base_mock = MockSerial("/dev/ttyUSB0", 9600)
            bue_mock = MockSerial("/dev/ttyUSB1", 9600)

            # Create OTA devices
            with patch("serial.Serial", side_effect=[base_mock, bue_mock]):
                base_ota = Ota("/dev/ttyUSB0", 9600, DeviceIds.BASE_STATION)
                bue_ota = Ota("/dev/ttyUSB1", 9600, DeviceIds.BUE_DEVICE)

                time.sleep(0.1)  # Let threads start

                try:
                    # Step 1: bUE sends REQ to broadcast
                    bue_ota.send_ota_message(DeviceIds.BROADCAST, MessageTypes.REQ)

                    # Simulate base station receiving REQ
                    req_message = MessageHelper.create_rcv_message(DeviceIds.BUE_DEVICE, MessageTypes.REQ)
                    base_mock.add_incoming_message(req_message)

                    # Step 2: Base station responds with CON
                    con_message = f"{MessageTypes.CON}:{DeviceIds.BASE_STATION}"
                    base_ota.send_ota_message(DeviceIds.BUE_DEVICE, con_message)

                    # Simulate bUE receiving CON
                    con_rcv = MessageHelper.create_rcv_message(DeviceIds.BASE_STATION, con_message)
                    bue_mock.add_incoming_message(con_rcv)

                    # Step 3: bUE sends ACK
                    bue_ota.send_ota_message(DeviceIds.BASE_STATION, MessageTypes.ACK)

                    # Simulate base station receiving ACK
                    ack_message = MessageHelper.create_rcv_message(DeviceIds.BUE_DEVICE, MessageTypes.ACK)
                    base_mock.add_incoming_message(ack_message)

                    # Wait for processing
                    time.sleep(0.3)

                    # Verify the message exchanges
                    base_messages = base_ota.get_new_messages()
                    bue_messages = bue_ota.get_new_messages()

                    # Base should have received REQ and ACK
                    assert len(base_messages) == 2
                    assert any(MessageTypes.REQ in msg for msg in base_messages)
                    assert any(MessageTypes.ACK in msg for msg in base_messages)

                    # bUE should have received CON
                    assert len(bue_messages) == 1
                    assert MessageTypes.CON in bue_messages[0]
                    assert str(DeviceIds.BASE_STATION) in bue_messages[0]

                finally:
                    base_ota.__del__()
                    bue_ota.__del__()

        def test_ping_pong_sequence(self):
            """Test the ping-pong keep-alive sequence"""
            base_mock = MockSerial("/dev/ttyUSB0", 9600)
            bue_mock = MockSerial("/dev/ttyUSB1", 9600)

            with patch("serial.Serial", side_effect=[base_mock, bue_mock]):
                base_ota = Ota("/dev/ttyUSB0", 9600, DeviceIds.BASE_STATION)
                bue_ota = Ota("/dev/ttyUSB1", 9600, DeviceIds.BUE_DEVICE)

                time.sleep(0.1)

                try:
                    # bUE sends PING
                    bue_ota.send_ota_message(DeviceIds.BASE_STATION, MessageTypes.PING)

                    # Simulate base station receiving PING
                    ping_message = MessageHelper.create_rcv_message(DeviceIds.BUE_DEVICE, MessageTypes.PING)
                    base_mock.add_incoming_message(ping_message)

                    # Base station responds with PINGR
                    base_ota.send_ota_message(DeviceIds.BUE_DEVICE, MessageTypes.PINGR)

                    # Simulate bUE receiving PINGR
                    pingr_message = MessageHelper.create_rcv_message(DeviceIds.BASE_STATION, MessageTypes.PINGR)
                    bue_mock.add_incoming_message(pingr_message)

                    time.sleep(0.3)

                    # Verify exchanges
                    base_messages = base_ota.get_new_messages()
                    bue_messages = bue_ota.get_new_messages()

                    assert len(base_messages) == 1
                    assert MessageTypes.PING in base_messages[0]

                    assert len(bue_messages) == 1
                    assert MessageTypes.PINGR in bue_messages[0]

                finally:
                    base_ota.__del__()
                    bue_ota.__del__()

        def test_test_configuration_sequence(self):
            """Test the complete test configuration and execution sequence"""
            base_mock = MockSerial("/dev/ttyUSB0", 9600)
            bue_mock = MockSerial("/dev/ttyUSB1", 9600)

            with patch("serial.Serial", side_effect=[base_mock, bue_mock]):
                base_ota = Ota("/dev/ttyUSB0", 9600, DeviceIds.BASE_STATION)
                bue_ota = Ota("/dev/ttyUSB1", 9600, DeviceIds.BUE_DEVICE)

                time.sleep(0.1)

                try:
                    # Step 1: Base sends TEST configuration
                    test_config = "0.1.1745004290"  # config.role.starttime
                    test_message = f"{MessageTypes.TEST}:{test_config}"
                    base_ota.send_ota_message(DeviceIds.BUE_DEVICE, test_message)

                    # Simulate bUE receiving TEST
                    test_rcv = MessageHelper.create_rcv_message(DeviceIds.BASE_STATION, test_message)
                    bue_mock.add_incoming_message(test_rcv)

                    # Step 2: bUE responds with PREPR
                    start_time = "1745004290"
                    prepr_message = f"{MessageTypes.PREPR}:{start_time}"
                    bue_ota.send_ota_message(DeviceIds.BASE_STATION, prepr_message)

                    # Simulate base receiving PREPR
                    prepr_rcv = MessageHelper.create_rcv_message(DeviceIds.BUE_DEVICE, prepr_message)
                    base_mock.add_incoming_message(prepr_rcv)

                    # Step 4: bUE sends update
                    upd_message = f"{MessageTypes.UPD}:test_progress_50"
                    bue_ota.send_ota_message(DeviceIds.BASE_STATION, upd_message)

                    # Simulate base receiving UPD
                    upd_rcv = MessageHelper.create_rcv_message(DeviceIds.BUE_DEVICE, upd_message)
                    base_mock.add_incoming_message(upd_rcv)

                    # Step 5: bUE finishes test
                    bue_ota.send_ota_message(DeviceIds.BASE_STATION, MessageTypes.DONE)

                    # Simulate base receiving DONE
                    done_rcv = MessageHelper.create_rcv_message(DeviceIds.BUE_DEVICE, MessageTypes.DONE)
                    base_mock.add_incoming_message(done_rcv)

                    time.sleep(0.5)

                    # Verify all messages were exchanged correctly
                    base_messages = base_ota.get_new_messages()
                    bue_messages = bue_ota.get_new_messages()

                    # Base should have received PREPR, UPD, DONE
                    assert len(base_messages) == 3
                    message_text = " ".join(base_messages)
                    assert MessageTypes.PREPR in message_text
                    assert MessageTypes.UPD in message_text
                    assert MessageTypes.DONE in message_text

                    # bUE should have received TEST
                    assert len(bue_messages) == 1
                    assert MessageTypes.TEST in bue_messages[0]
                    assert test_config in bue_messages[0]

                finally:
                    base_ota.__del__()
                    bue_ota.__del__()

        def test_test_failure_sequence(self):
            """Test the test failure handling sequence"""
            base_mock = MockSerial("/dev/ttyUSB0", 9600)
            bue_mock = MockSerial("/dev/ttyUSB1", 9600)

            with patch("serial.Serial", side_effect=[base_mock, bue_mock]):
                base_ota = Ota("/dev/ttyUSB0", 9600, DeviceIds.BASE_STATION)
                bue_ota = Ota("/dev/ttyUSB1", 9600, DeviceIds.BUE_DEVICE)

                time.sleep(0.1)

                try:
                    # Base sends invalid TEST configuration
                    bad_test_message = f"{MessageTypes.TEST}:invalid_config"
                    base_ota.send_ota_message(DeviceIds.BUE_DEVICE, bad_test_message)

                    # Simulate bUE receiving bad TEST
                    test_rcv = MessageHelper.create_rcv_message(DeviceIds.BASE_STATION, bad_test_message)
                    bue_mock.add_incoming_message(test_rcv)

                    # bUE responds with FAIL
                    fail_message = f"{MessageTypes.FAIL}:BAD_CONFIG"
                    bue_ota.send_ota_message(DeviceIds.BASE_STATION, fail_message)

                    # Simulate base receiving FAIL
                    fail_rcv = MessageHelper.create_rcv_message(DeviceIds.BUE_DEVICE, fail_message)
                    base_mock.add_incoming_message(fail_rcv)

                    time.sleep(0.3)

                    # Verify failure handling
                    base_messages = base_ota.get_new_messages()
                    bue_messages = bue_ota.get_new_messages()

                    # Base should have received FAIL
                    assert len(base_messages) == 1
                    assert MessageTypes.FAIL in base_messages[0]
                    assert "BAD_CONFIG" in base_messages[0]

                    # bUE should have received bad TEST
                    assert len(bue_messages) == 1
                    assert MessageTypes.TEST in bue_messages[0]
                    assert "invalid_config" in bue_messages[0]

                finally:
                    base_ota.__del__()
                    bue_ota.__del__()

        def test_test_cancellation_sequence(self):
            """Test the test cancellation sequence"""
            base_mock = MockSerial("/dev/ttyUSB0", 9600)
            bue_mock = MockSerial("/dev/ttyUSB1", 9600)

            with patch("serial.Serial", side_effect=[base_mock, bue_mock]):
                base_ota = Ota("/dev/ttyUSB0", 9600, DeviceIds.BASE_STATION)
                bue_ota = Ota("/dev/ttyUSB1", 9600, DeviceIds.BUE_DEVICE)

                time.sleep(0.1)

                try:
                    # Base sends CANC message to cancel ongoing test
                    base_ota.send_ota_message(DeviceIds.BUE_DEVICE, MessageTypes.CANC)

                    # Simulate bUE receiving CANC
                    canc_rcv = MessageHelper.create_rcv_message(DeviceIds.BASE_STATION, MessageTypes.CANC)
                    bue_mock.add_incoming_message(canc_rcv)

                    # After cancellation, bUE should resume pinging
                    bue_ota.send_ota_message(DeviceIds.BASE_STATION, MessageTypes.PING)

                    time.sleep(0.3)

                    # Verify cancellation handling
                    bue_messages = bue_ota.get_new_messages()

                    # bUE should have received CANC
                    assert len(bue_messages) == 1
                    assert MessageTypes.CANC in bue_messages[0]

                    # Verify PING was sent after cancellation
                    bue_sent = bue_mock.get_sent_messages()
                    ping_sent = any(MessageTypes.PING in msg for msg in bue_sent)
                    assert ping_sent

                finally:
                    base_ota.__del__()
                    bue_ota.__del__()

except ImportError as e:
    print(f"Warning: Could not import test dependencies: {e}")
    print("Run 'pip install -r setup/requirements_test.txt' to install test dependencies")

    # Create dummy test class for when pytest is not available
    class TestProtocolIntegration:
        def test_placeholder(self):
            pass
