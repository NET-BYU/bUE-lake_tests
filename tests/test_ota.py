"""
Tests for the OTA (Over-The-Air) communication module.

This test suite covers the message protocol defined in message_dict.txt,
including connection establishment, ping/pong, test coordination, and error handling.
"""

import pytest
import time
import threading
from unittest.mock import patch, MagicMock
import sys
import os

# Add the parent directory to the path so we can import ota
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.conftest import MessageHelper, MessageTypes, DeviceIds
from ota import Ota


class TestOtaBasicFunctionality:
    """Test basic OTA functionality"""

    def test_ota_initialization(self, ota_device):
        """Test that OTA device initializes correctly"""
        device, mock_serial = ota_device

        assert device.id == 5
        assert device.ser == mock_serial
        assert device.receiving_event.is_set()
        assert not device.exit_event.is_set()
        assert device.thread.is_alive()

    def test_send_ota_message(self, ota_device):
        """Test sending OTA messages"""
        device, mock_serial = ota_device

        # Send a simple message
        device.send_ota_message(DeviceIds.BASE_STATION, MessageTypes.PING)

        # Check that the correct AT command was sent
        sent_messages = mock_serial.get_sent_messages()
        expected = MessageHelper.create_at_command(
            DeviceIds.BASE_STATION, MessageTypes.PING
        )
        assert expected in sent_messages

    def test_receive_ota_message(self, ota_device):
        """Test receiving OTA messages"""
        device, mock_serial = ota_device

        # Add a message to the mock serial buffer
        test_message = MessageHelper.create_rcv_message(
            DeviceIds.BASE_STATION, MessageTypes.PING, -75, 12
        )
        mock_serial.add_incoming_message(test_message)

        # Wait for the message to be processed
        time.sleep(0.2)

        # Get new messages
        messages = device.get_new_messages()
        assert len(messages) == 1
        assert messages[0] == test_message

    def test_message_filtering(self, ota_device):
        """Test that empty messages and 'OK' responses are filtered out"""
        device, mock_serial = ota_device

        # Add various messages including ones that should be filtered
        mock_serial.add_incoming_message("")
        mock_serial.add_incoming_message("OK")
        valid_message = MessageHelper.create_rcv_message(
            DeviceIds.BASE_STATION, MessageTypes.PING
        )
        mock_serial.add_incoming_message(valid_message)

        # Wait for processing
        time.sleep(0.2)

        # Should only get the valid message
        messages = device.get_new_messages()
        assert len(messages) == 1
        assert messages[0] == valid_message


class TestConnectionProtocol:
    """Test the connection establishment protocol"""

    def test_request_connection(self, ota_device):
        """Test bUE requesting connection (REQ message)"""
        device, mock_serial = ota_device

        # bUE sends REQ to broadcast address
        device.send_ota_message(DeviceIds.BROADCAST, MessageTypes.REQ)

        # Verify the correct AT command was sent
        sent_messages = mock_serial.get_sent_messages()
        expected = MessageHelper.create_at_command(
            DeviceIds.BROADCAST, MessageTypes.REQ
        )
        assert expected in sent_messages

    def test_connection_confirm(self, ota_device):
        """Test base station confirming connection (CON message)"""
        device, mock_serial = ota_device

        # Simulate base station sending CON message with its ID
        con_message = f"{MessageTypes.CON}:{DeviceIds.BASE_STATION}"
        rcv_message = MessageHelper.create_rcv_message(
            DeviceIds.BASE_STATION, con_message
        )
        mock_serial.add_incoming_message(rcv_message)

        # Wait and get messages
        time.sleep(0.2)
        messages = device.get_new_messages()

        assert len(messages) == 1
        assert con_message in messages[0]

    def test_acknowledge_connection(self, ota_device):
        """Test bUE acknowledging connection (ACK message)"""
        device, mock_serial = ota_device

        # bUE sends ACK to base station
        device.send_ota_message(DeviceIds.BASE_STATION, MessageTypes.ACK)

        # Verify the correct AT command was sent
        sent_messages = mock_serial.get_sent_messages()
        expected = MessageHelper.create_at_command(
            DeviceIds.BASE_STATION, MessageTypes.ACK
        )
        assert expected in sent_messages


class TestPingProtocol:
    """Test the ping/pong keep-alive protocol"""

    def test_ping_message(self, ota_device):
        """Test bUE sending ping message"""
        device, mock_serial = ota_device

        # bUE sends PING to base station
        device.send_ota_message(DeviceIds.BASE_STATION, MessageTypes.PING)

        # Verify the correct AT command was sent
        sent_messages = mock_serial.get_sent_messages()
        expected = MessageHelper.create_at_command(
            DeviceIds.BASE_STATION, MessageTypes.PING
        )
        assert expected in sent_messages

    def test_ping_response(self, ota_device):
        """Test base station responding to ping (PINGR message)"""
        device, mock_serial = ota_device

        # Simulate base station sending PINGR message
        rcv_message = MessageHelper.create_rcv_message(
            DeviceIds.BASE_STATION, MessageTypes.PINGR
        )
        mock_serial.add_incoming_message(rcv_message)

        # Wait and get messages
        time.sleep(0.2)
        messages = device.get_new_messages()

        assert len(messages) == 1
        assert MessageTypes.PINGR in messages[0]


class TestTestProtocol:
    """Test the UTW test coordination protocol"""

    def test_test_configuration_message(self, ota_device):
        """Test base station sending test configuration"""
        device, mock_serial = ota_device

        # Simulate base station sending TEST message
        test_config = "0.1.1745004290"  # config.role.starttime
        test_message = f"{MessageTypes.TEST}:{test_config}"
        rcv_message = MessageHelper.create_rcv_message(
            DeviceIds.BASE_STATION, test_message
        )
        mock_serial.add_incoming_message(rcv_message)

        # Wait and get messages
        time.sleep(0.2)
        messages = device.get_new_messages()

        assert len(messages) == 1
        assert test_config in messages[0]

    def test_test_failure_message(self, ota_device):
        """Test bUE sending test failure message"""
        device, mock_serial = ota_device

        # bUE sends FAIL message with reason
        fail_reason = "BAD_CONFIG"
        fail_message = f"{MessageTypes.FAIL}:{fail_reason}"
        device.send_ota_message(DeviceIds.BASE_STATION, fail_message)

        # Verify the correct AT command was sent
        sent_messages = mock_serial.get_sent_messages()
        expected = MessageHelper.create_at_command(DeviceIds.BASE_STATION, fail_message)
        assert expected in sent_messages

    def test_test_cancel_message(self, ota_device):
        """Test base station canceling test"""
        device, mock_serial = ota_device

        # Simulate base station sending CANC message
        rcv_message = MessageHelper.create_rcv_message(
            DeviceIds.BASE_STATION, MessageTypes.CANC
        )
        mock_serial.add_incoming_message(rcv_message)

        # Wait and get messages
        time.sleep(0.2)
        messages = device.get_new_messages()

        assert len(messages) == 1
        assert MessageTypes.CANC in messages[0]

    def test_test_preparation_response(self, ota_device):
        """Test bUE confirming test preparation"""
        device, mock_serial = ota_device

        # bUE sends PREPR message with start time
        start_time = "1745004290"
        prepr_message = f"{MessageTypes.PREPR}:{start_time}"
        device.send_ota_message(DeviceIds.BASE_STATION, prepr_message)

        # Verify the correct AT command was sent
        sent_messages = mock_serial.get_sent_messages()
        expected = MessageHelper.create_at_command(
            DeviceIds.BASE_STATION, prepr_message
        )
        assert expected in sent_messages

    def test_test_lifecycle_messages(self, ota_device):
        """Test the complete test lifecycle messages"""
        device, mock_serial = ota_device

        # Test BEGIN message
        device.send_ota_message(DeviceIds.BASE_STATION, MessageTypes.BEGIN)

        # Test UPD message with body
        upd_message = f"{MessageTypes.UPD}:test_update_data"
        device.send_ota_message(DeviceIds.BASE_STATION, upd_message)

        # Test DONE message
        device.send_ota_message(DeviceIds.BASE_STATION, MessageTypes.DONE)

        # Verify all messages were sent
        sent_messages = mock_serial.get_sent_messages()
        assert len(sent_messages) == 3

        expected_begin = MessageHelper.create_at_command(
            DeviceIds.BASE_STATION, MessageTypes.BEGIN
        )
        expected_upd = MessageHelper.create_at_command(
            DeviceIds.BASE_STATION, upd_message
        )
        expected_done = MessageHelper.create_at_command(
            DeviceIds.BASE_STATION, MessageTypes.DONE
        )

        assert expected_begin in sent_messages
        assert expected_upd in sent_messages
        assert expected_done in sent_messages


class TestErrorHandling:
    """Test error handling scenarios"""

    def test_serial_write_error(self, ota_device):
        """Test handling of serial write errors"""
        device, mock_serial = ota_device

        # Mock the write method to raise an exception
        with patch.object(mock_serial, "write", side_effect=Exception("Write error")):
            # This should not raise an exception, but print an error message
            device.send_ota_message(DeviceIds.BASE_STATION, MessageTypes.PING)

    def test_serial_read_error(self, ota_device):
        """Test handling of serial read errors"""
        device, mock_serial = ota_device

        # Mock the readline method to raise an exception
        with patch.object(mock_serial, "readline", side_effect=Exception("Read error")):
            # Add a message that would trigger the error
            mock_serial.add_incoming_message("test")

            # Wait a bit for the thread to process
            time.sleep(0.2)

            # Should still be able to get messages (empty list)
            messages = device.get_new_messages()
            assert isinstance(messages, list)

    def test_device_cleanup(self, mock_serial):
        """Test proper cleanup of OTA device"""
        with patch("serial.Serial", return_value=mock_serial):
            device = Ota("/dev/ttyUSB0", 9600, 5)
            time.sleep(0.1)  # Let thread start

            # Cleanup
            device.__del__()

            # Wait for thread to finish
            time.sleep(0.2)

            # Thread should be stopped
            assert device.exit_event.is_set()
            assert not device.receiving_event.is_set()


class TestMessageHelper:
    """Test the message helper utilities"""

    def test_create_rcv_message(self):
        """Test creating RCV messages"""
        message = MessageHelper.create_rcv_message(5, MessageTypes.PING, -80, 10)
        expected = f"+RCV=5,4,PING,-80,10"
        assert message == expected

    def test_create_at_command(self):
        """Test creating AT commands"""
        command = MessageHelper.create_at_command(10, MessageTypes.PING)
        expected = f"AT+SEND=10,4,PING\r\n"
        assert command == expected

    def test_parse_message_type(self):
        """Test parsing message types"""
        # Message without body
        msg_type, body = MessageHelper.parse_message_type(MessageTypes.PING)
        assert msg_type == MessageTypes.PING
        assert body is None

        # Message with body
        msg_type, body = MessageHelper.parse_message_type("CON:10")
        assert msg_type == "CON"
        assert body == "10"

        # Message with complex body
        msg_type, body = MessageHelper.parse_message_type("TEST:0.1.1745004290")
        assert msg_type == "TEST"
        assert body == "0.1.1745004290"


class TestConcurrentAccess:
    """Test concurrent access scenarios"""

    def test_concurrent_message_sending(self, ota_device):
        """Test sending messages from multiple threads"""
        device, mock_serial = ota_device

        def send_messages(thread_id):
            for i in range(5):
                device.send_ota_message(DeviceIds.BASE_STATION, f"MSG_{thread_id}_{i}")
                time.sleep(0.01)

        # Start multiple threads sending messages
        threads = []
        for i in range(3):
            thread = threading.Thread(target=send_messages, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Should have received 15 messages total (3 threads * 5 messages each)
        sent_messages = mock_serial.get_sent_messages()
        assert len(sent_messages) == 15

    def test_concurrent_message_receiving(self, ota_device):
        """Test receiving messages while sending"""
        device, mock_serial = ota_device

        # Add multiple messages to the buffer
        for i in range(10):
            test_message = MessageHelper.create_rcv_message(
                DeviceIds.BASE_STATION, f"MSG_{i}"
            )
            mock_serial.add_incoming_message(test_message)

        # Send some messages while receiving
        for i in range(5):
            device.send_ota_message(DeviceIds.BASE_STATION, f"SEND_{i}")

        # Wait for processing
        time.sleep(0.3)

        # Get received messages
        messages = device.get_new_messages()
        assert len(messages) == 10

        # Check sent messages
        sent_messages = mock_serial.get_sent_messages()
        assert len(sent_messages) == 5
