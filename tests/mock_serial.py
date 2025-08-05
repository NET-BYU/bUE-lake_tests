"""
Mock serial implementation for testing OTA functionality.
"""

import time
from typing import List, Optional
from unittest.mock import Mock


class MockSerial:
    """Mock implementation of pyserial.Serial for testing"""

    def __init__(self, port: str, baudrate: int, timeout: float = 0.1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.is_open = True

        # Buffer to store incoming messages
        self._incoming_buffer: List[str] = []
        self._sent_messages: List[str] = []

        # Simulate serial read position
        self._read_position = 0

    @property
    def in_waiting(self) -> int:
        """Return number of bytes waiting to be read"""
        return len(self._get_current_message())

    def write(self, data: bytes) -> int:
        """Write data to the mock serial port"""
        message = data.decode("utf-8")
        self._sent_messages.append(message)
        return len(data)

    def readline(self) -> bytes:
        """Read a line from the mock serial port"""
        message = self._get_current_message()
        if message:
            self._read_position += 1
            return f"{message}\r\n".encode("utf-8")
        return b""

    def close(self):
        """Close the mock serial port"""
        self.is_open = False

    def _get_current_message(self) -> str:
        """Get the current message to be read"""
        if self._read_position < len(self._incoming_buffer):
            return self._incoming_buffer[self._read_position]
        return ""

    def add_incoming_message(self, message: str):
        """Add a message to the incoming buffer (for testing)"""
        self._incoming_buffer.append(message)

    def get_sent_messages(self) -> List[str]:
        """Get all messages that were sent (for testing)"""
        return self._sent_messages.copy()

    def clear_sent_messages(self):
        """Clear the sent messages buffer (for testing)"""
        self._sent_messages.clear()

    def clear_incoming_messages(self):
        """Clear the incoming messages buffer (for testing)"""
        self._incoming_buffer.clear()
        self._read_position = 0


class MockSerialException(Exception):
    """Mock serial exception for testing error conditions"""

    pass
