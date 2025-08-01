"""
Test fixtures and utilities for OTA testing.
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock
import time
import crc8

# Add the parent directory to the path so we can import ota
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.mock_serial import MockSerial, MockSerialException
from ota import Ota


@pytest.fixture
def mock_serial():
    """Create a mock serial instance"""
    return MockSerial("/dev/ttyUSB0", 9600)


@pytest.fixture
def ota_device(mock_serial):
    """Create an OTA device with mocked serial"""
    with patch("serial.Serial", return_value=mock_serial):
        device = Ota("/dev/ttyUSB0", 9600, 5)
        # Give the thread a moment to start
        time.sleep(0.1)
        yield device, mock_serial
        # Clean up
        device.__del__()


class MessageHelper:
    """Helper class for creating and parsing OTA messages"""

    @staticmethod
    def calculate_crc8(message: str) -> str:
        """Calculate CRC8 checksum for a message (same as OTA class)"""
        crc8_calculator = crc8.crc8()
        crc8_calculator.update(message.encode("utf-8"))
        return format(crc8_calculator.digest()[0], "02x")

    @staticmethod
    def create_rcv_message(sender_id: int, message: str, rssi: int = -80, snr: int = 10, include_crc: bool = True) -> str:
        """Create a +RCV message as received from the LoRa module"""
        if include_crc:
            # Create the message format used for CRC: "{len(message)},{message}"
            crc = MessageHelper.calculate_crc8(message)
            message_with_crc = f"{message}{crc}"
            return f"+RCV={sender_id},{len(message_with_crc)},{message_with_crc},{rssi},{snr}"
        else:
            return f"+RCV={sender_id},{len(message)},{message},{rssi},{snr}"

    @staticmethod
    def create_at_command(dest_id: int, message: str, include_crc: bool = True) -> str:
        """Create an AT+SEND command as sent to the LoRa module"""
        if include_crc:
            # Create the message format used for CRC: "{len(message)},{message}"
            crc = MessageHelper.calculate_crc8(message)
            message_with_crc = f"{message}{crc}"
            return f"AT+SEND={dest_id},{len(message_with_crc)},{message_with_crc}\r\n"
        else:
            msg_for_send = f"{len(message)},{message}"
            return f"AT+SEND={dest_id},{msg_for_send}\r\n"

    @staticmethod
    def parse_message_type(message: str) -> tuple:
        """Parse a message to extract type and body"""
        if ":" in message:
            msg_type, body = message.split(":", 1)
            return msg_type, body
        return message, None


# Message constants based on message_dict.txt
class MessageTypes:
    REQ = "REQ"  # bUE -> base: Request to join network
    CON = "CON"  # base -> bUE: Confirm join with base station id
    ACK = "ACK"  # bUE -> base: Acknowledge connection
    PING = "PING"  # bUE -> base: Periodic ping
    PINGR = "PINGR"  # base -> bUE: Ping response
    TEST = "TEST"  # base -> bUE: Test configuration
    FAIL = "FAIL"  # bUE -> base: Test failure
    CANC = "CANC"  # base -> bUE: Cancel test
    PREPR = "PREPR"  # bUE -> base: Test preparation response
    UPD = "UPD"  # bUE -> base: Test update
    DONE = "DONE"  # bUE -> base: Test completion


# Device ID constants
class DeviceIds:
    BROADCAST = 0
    BASE_STATION = 1
    BUE_DEVICE = 10
