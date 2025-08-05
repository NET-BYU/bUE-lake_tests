# Testing Framework for bUE-lake_tests

This directory contains a comprehensive testing framework for the bUE (Buoyant Underwater Equipment) over-the-air communication system.

## Overview

The testing framework provides:
- **Mock Serial Implementation**: Stubbed serial communication for testing without hardware
- **Protocol Testing**: Tests for all message types defined in `message_dict.txt`
- **Integration Testing**: End-to-end protocol flow testing
- **Concurrent Testing**: Multi-threaded communication scenarios

## Test Structure

```
tests/
├── __init__.py              # Package initialization
├── conftest.py              # Test fixtures and utilities
├── mock_serial.py           # Mock serial port implementation
├── test_ota.py              # Unit tests for OTA functionality
└── test_integration.py      # Integration tests for protocol flows
```

## Message Protocol Testing

The tests cover all message types from the protocol specification:

### Connection Protocol
- **REQ**: bUE requests to join network (broadcast)
- **CON**: Base station confirms connection with ID
- **ACK**: bUE acknowledges connection

### Keep-Alive Protocol
- **PING**: bUE periodic ping to base station
- **PINGR**: Base station ping response

### Test Coordination Protocol
- **TEST**: Base station sends test configuration
- **PREPR**: bUE confirms test preparation
- **BEGIN**: bUE notifies test start
- **UPD**: bUE sends test progress updates
- **DONE**: bUE notifies test completion
- **FAIL**: bUE reports test failure
- **CANC**: Base station cancels ongoing test

## Installation

Install test dependencies:

```bash
# Using pip
pip install -r setup/requirements_test.txt

# Using make
make install
```

## Running Tests

### Basic Test Run
```bash
# Using pytest directly
python -m pytest tests/ -v

# Using make
make test
```

### Verbose Output
```bash
# Using pytest
python -m pytest tests/ -v -s

# Using make
make test-verbose
```

### Coverage Report
```bash
# Using pytest
python -m pytest tests/ -v --cov=ota --cov-report=html --cov-report=term-missing

# Using make
make coverage
```

### Using the Test Runner
```bash
python run_tests.py
```

## Test Features

### Mock Serial Port
The `MockSerial` class provides:
- Simulated read/write operations
- Message buffering
- Error simulation
- Thread-safe operations

### Message Helpers
The `MessageHelper` class provides utilities for:
- Creating properly formatted +RCV messages
- Generating AT+SEND commands
- Parsing message types and bodies

### Integration Tests
Full protocol flow testing including:
- Complete connection establishment
- Ping-pong keep-alive sequences
- Test configuration and execution
- Error handling and cancellation

### Concurrent Testing
Tests for multi-threaded scenarios:
- Simultaneous message sending
- Concurrent reading and writing
- Thread safety verification

## Test Coverage

The framework tests:
- ✅ Message sending and receiving
- ✅ Protocol message formats
- ✅ Connection establishment
- ✅ Keep-alive mechanisms
- ✅ Test coordination
- ✅ Error handling
- ✅ Thread safety
- ✅ Serial port simulation
- ✅ Message filtering
- ✅ Device cleanup

## Example Usage

```python
# Create a mock OTA device for testing
from tests.conftest import ota_device, MessageHelper, MessageTypes, DeviceIds

# In a test function
def test_my_protocol(ota_device):
    device, mock_serial = ota_device
    
    # Send a message
    device.send_ota_message(DeviceIds.BASE_STATION, MessageTypes.PING)
    
    # Simulate receiving a response
    response = MessageHelper.create_rcv_message(
        DeviceIds.BASE_STATION, MessageTypes.PINGR
    )
    mock_serial.add_incoming_message(response)
    
    # Verify the exchange
    messages = device.get_new_messages()
    assert MessageTypes.PINGR in messages[0]
```

## Cleanup

Remove generated test files:

```bash
# Using make
make clean

# Manual cleanup
rm -rf htmlcov/ .coverage .pytest_cache/
```

## Dependencies

- `pytest`: Test framework
- `pytest-mock`: Mocking utilities
- `pytest-cov`: Coverage reporting
- `unittest-mock`: Mock objects (fallback)

The mock serial implementation eliminates the need for physical hardware during testing, allowing for comprehensive protocol validation in a controlled environment.
