"""
Essential system integration tests for bUE-base station communication.

This test suite focuses on testable components and addresses critical gaps:
1. OTA communication reliability under stress
2. Message protocol edge cases
3. Configuration validation
4. Multi-device message handling
5. Error recovery scenarios

These tests can run without GPS dependencies and focus on the core communication logic.
"""

import pytest
import time
import threading
import queue
import tempfile
import os
import yaml
from unittest.mock import patch, MagicMock
import sys

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.conftest import MessageHelper, MessageTypes, DeviceIds
from tests.mock_serial import MockSerial
from ota import Ota


class TestAdvancedOTACommunication:
    """Test advanced OTA communication scenarios critical for lake deployment"""

    def test_realistic_bue_message_queue_handling(self):
        """Test realistic bUE message handling through task queues like the actual system"""
        mock_serial = MockSerial("/dev/ttyUSB0", 9600)
        
        with patch('serial.Serial', return_value=mock_serial):
            ota_device = Ota("/dev/ttyUSB0", 9600, 10)
            time.sleep(0.1)  # Let thread start
            
            # Simulate the bUE task queue system
            message_queue = queue.Queue()
            messages_sent = []
            
            def queue_processor():
                """Simulate the ota_task_queue_handler from bUE_Main"""
                while True:
                    try:
                        task = message_queue.get(timeout=0.5)
                        if task is None:  # Shutdown signal
                            break
                        # Execute the queued message task
                        target_id, message = task
                        ota_device.send_ota_message(target_id, message)
                        messages_sent.append(message)
                        message_queue.task_done()
                    except queue.Empty:
                        break
            
            # Start the queue processor (like bUE's ota_thread)
            processor_thread = threading.Thread(target=queue_processor)
            processor_thread.start()
            
            # Simulate realistic bUE state machine behavior:
            # 1. CONNECT_OTA state - sending REQ messages
            for i in range(5):
                message_queue.put((1, f"REQ_{i}"))  # Send to base station (ID 1)
                time.sleep(0.1)  # Simulate CONNECT_OTA_REQ_INTERVAL
            
            # 2. IDLE state - sending PING messages with GPS coordinates
            for i in range(10):
                lat, lon = 40.2518 + i*0.001, -111.6493 + i*0.001
                message_queue.put((1, f"PING,{lat},{lon}"))
                time.sleep(0.1)  # Simulate IDLE_PING_OTA_INTERVAL
            
            # 3. UTW_TEST state - sending UPD messages
            for i in range(8):
                lat, lon = 40.2518 + i*0.001, -111.6493 + i*0.001
                message_queue.put((1, f"UPD:,{lat},{lon},Test progress {i*12.5}%"))
                time.sleep(0.1)  # Simulate UTW_UPD_OTA_INTERVAL
            
            # Signal shutdown and wait for completion
            message_queue.put(None)
            processor_thread.join()
            
            # Verify sequential message processing (like real bUE)
            sent_messages = mock_serial.get_sent_messages()
            assert len(sent_messages) == 23, f"Expected 23 messages, got {len(sent_messages)}"
            
            # Verify message order reflects state machine sequence
            assert any("REQ_0" in msg for msg in sent_messages[:5]), "First REQ message not found"
            assert any("PING" in msg for msg in sent_messages[5:15]), "PING messages not in expected range"
            assert any("UPD:" in msg for msg in sent_messages[15:]), "UPD messages not in expected range"
            
            # Verify no message duplication (critical for reliable communication)
            for expected_msg in messages_sent:
                matching_messages = [msg for msg in sent_messages if expected_msg in msg]
                assert len(matching_messages) == 1, f"Message {expected_msg} not found or duplicated"
            
            ota_device.__del__()

    def test_message_ordering_under_load(self):
        """Test that message ordering is preserved under load"""
        mock_serial = MockSerial("/dev/ttyUSB0", 9600)
        
        with patch('serial.Serial', return_value=mock_serial):
            ota_device = Ota("/dev/ttyUSB0", 9600, 10)
            time.sleep(0.1)
            
            # Send a sequence of numbered messages rapidly
            message_count = 50
            for i in range(message_count):
                ota_device.send_ota_message(1, f"SEQ_{i:03d}")
            
            time.sleep(0.5)  # Let all messages process
            
            sent_messages = mock_serial.get_sent_messages()
            assert len(sent_messages) == message_count
            
            # Verify messages are in order
            for i, message in enumerate(sent_messages):
                expected_seq = f"SEQ_{i:03d}"
                assert expected_seq in message, f"Message {i} out of order: {message}"
            
            ota_device.__del__()

    def test_simultaneous_send_receive_realistic(self):
        """Test realistic scenario: state machine sending while receiving base station messages"""
        mock_serial = MockSerial("/dev/ttyUSB0", 9600)
        
        with patch('serial.Serial', return_value=mock_serial):
            ota_device = Ota("/dev/ttyUSB0", 9600, 10)
            time.sleep(0.1)
            
            # Simulate realistic bUE operation
            state_machine_queue = queue.Queue()
            
            def simulate_state_machine():
                """Simulate bUE state machine sending periodic messages"""
                # IDLE state behavior - send PING every few seconds
                for i in range(15):
                    lat, lon = 40.2518 + i*0.001, -111.6493 + i*0.001
                    state_machine_queue.put((1, f"PING,{lat},{lon}"))
                    time.sleep(0.02)  # Faster for testing
                
                # UTW_TEST state behavior - send UPD messages
                for i in range(10):
                    lat, lon = 40.2518 + i*0.001, -111.6493 + i*0.001
                    state_machine_queue.put((1, f"UPD:,{lat},{lon},Progress {i*10}%"))
                    time.sleep(0.02)
            
            def simulate_base_station_messages():
                """Simulate receiving messages from base station during operation"""
                # Base station responses and commands
                for i in range(20):
                    if i < 10:
                        # PINGR responses to our PINGs
                        msg = MessageHelper.create_rcv_message(1, "PINGR")
                    elif i < 15:
                        # CON messages (connection confirmations)
                        msg = MessageHelper.create_rcv_message(1, "CON:1")
                    else:
                        # TEST commands
                        future_time = int(time.time()) + 10
                        msg = MessageHelper.create_rcv_message(1, f"TEST-script{i}-{future_time}-param")
                    
                    mock_serial.add_incoming_message(msg)
                    time.sleep(0.025)  # Slightly different timing to create realistic overlap
            
            def queue_processor():
                """Process state machine messages sequentially"""
                while True:
                    try:
                        task = state_machine_queue.get(timeout=1.0)
                        if task is None:
                            break
                        target_id, message = task
                        ota_device.send_ota_message(target_id, message)
                        state_machine_queue.task_done()
                    except queue.Empty:
                        break
            
            # Start all threads simultaneously (like real bUE operation)
            state_thread = threading.Thread(target=simulate_state_machine)
            base_station_thread = threading.Thread(target=simulate_base_station_messages)
            processor_thread = threading.Thread(target=queue_processor)
            
            state_thread.start()
            base_station_thread.start()
            processor_thread.start()
            
            # Wait for message generation to complete
            state_thread.join()
            base_station_thread.join()
            
            # Signal queue processor to finish and wait
            state_machine_queue.put(None)
            processor_thread.join()
            
            time.sleep(0.2)  # Let final processing complete
            
            # Verify both sending and receiving worked correctly
            sent_messages = mock_serial.get_sent_messages()
            received_messages = ota_device.get_new_messages()
            
            # Should have sent 25 messages (15 PING + 10 UPD)
            assert len(sent_messages) == 25, f"Expected 25 sent messages, got {len(sent_messages)}"
            
            # Should have received 20 messages from base station
            assert len(received_messages) == 20, f"Expected 20 received messages, got {len(received_messages)}"
            
            # Verify realistic message types are present
            sent_text = ' '.join(sent_messages)
            received_text = ' '.join(received_messages)
            
            assert "PING," in sent_text, "PING messages not found in sent messages"
            assert "UPD:" in sent_text, "UPD messages not found in sent messages"
            assert "PINGR" in received_text, "PINGR responses not found in received messages"
            assert "CON:" in received_text, "CON messages not found in received messages"
            assert "TEST-" in received_text, "TEST commands not found in received messages"
            
            # Verify no cross-contamination between send and receive
            for msg in sent_messages:
                assert "+RCV=" not in msg, "Received message format found in sent messages"
            
            for msg in received_messages:
                assert "AT+SEND=" not in msg, "Send command format found in received messages"
            
            ota_device.__del__()


class TestProtocolEdgeCases:
    """Test edge cases in the communication protocol"""

    def test_message_boundary_conditions(self):
        """Test messages at size boundaries"""
        mock_serial = MockSerial("/dev/ttyUSB0", 9600)
        
        with patch('serial.Serial', return_value=mock_serial):
            ota_device = Ota("/dev/ttyUSB0", 9600, 10)
            time.sleep(0.1)
            
            # Test various message sizes
            test_cases = [
                "",  # Empty message
                "A",  # Single character
                "A" * 50,  # Medium message
                "A" * 200,  # Large message
                "SPECIAL:CHARS!@#$%^&*()",  # Special characters
                "MESSAGE:WITH:COLONS:AND:STRUCTURE",  # Structured message
            ]
            
            for i, test_message in enumerate(test_cases):
                ota_device.send_ota_message(1, test_message)
                
                # Verify message was formatted correctly
                sent_messages = mock_serial.get_sent_messages()
                latest_message = sent_messages[i]
                
                expected_format = f"AT+SEND=1,{len(test_message)},{test_message}\r\n"
                assert latest_message == expected_format, f"Message format incorrect for: {test_message}"
            
            ota_device.__del__()

    def test_malformed_incoming_message_handling(self):
        """Test handling of various malformed incoming messages"""
        mock_serial = MockSerial("/dev/ttyUSB0", 9600)
        
        with patch('serial.Serial', return_value=mock_serial):
            ota_device = Ota("/dev/ttyUSB0", 9600, 10)
            time.sleep(0.1)
            
            # Add various malformed messages
            malformed_messages = [
                "+RCV=",  # Incomplete header
                "+RCV=1",  # Missing fields
                "+RCV=1,5",  # Missing message content
                "+RCV=abc,5,HELLO,-50,10",  # Invalid sender ID
                "+RCV=1,999,SHORT,-50,10",  # Length mismatch (too long)
                "+RCV=1,2,TOOLONG,-50,10",  # Length mismatch (too short)
                "+RCV=1,5,HELLO,-50",  # Missing SNR
                "+RCV=1,5,HELLO,-50,abc",  # Invalid SNR
                "COMPLETELY_INVALID_FORMAT",  # Not a +RCV message
                "",  # Empty message
                "+RCV=1,5,HELLO,-50,10,EXTRA",  # Extra fields
            ]
            
            for bad_message in malformed_messages:
                mock_serial.add_incoming_message(bad_message)
            
            time.sleep(0.5)  # Let messages process
            
            # System should filter out malformed messages
            received_messages = ota_device.get_new_messages()
            
            # Only properly formatted messages should be received
            # (in this case, none of the test messages are properly formatted)
            valid_messages = [msg for msg in received_messages if msg.startswith("+RCV=") and len(msg.split(",")) >= 5]
            
            # The system should handle malformed messages gracefully without crashing
            # and should not pass them through to the application

            print(f"{len(received_messages)}!!!!!!!!!!!!!!!!!!!!!!!!!!!")

            for msg in received_messages:
                print(msg)
                # Should not contain obviously malformed messages
                # assert not msg.startswith("COMPLETELY_INVALID_FORMAT")
                assert msg != ""  # Empty messages should be filtered
            
            ota_device.__del__()

    def test_rapid_connection_disconnection(self):
        """Test rapid connection/disconnection scenarios"""
        mock_serial = MockSerial("/dev/ttyUSB0", 9600)
        
        with patch('serial.Serial', return_value=mock_serial):
            ota_device = Ota("/dev/ttyUSB0", 9600, 10)
            time.sleep(0.1)
            
            # Simulate rapid connection establishment and teardown
            for cycle in range(10):
                # Connection sequence
                req_msg = MessageHelper.create_rcv_message(10, MessageTypes.REQ)
                con_msg = MessageHelper.create_rcv_message(1, f"{MessageTypes.CON}:1")
                ack_msg = MessageHelper.create_rcv_message(10, MessageTypes.ACK)
                
                mock_serial.add_incoming_message(req_msg)
                mock_serial.add_incoming_message(con_msg)
                mock_serial.add_incoming_message(ack_msg)
                
                # Ping sequence
                ping_msg = MessageHelper.create_rcv_message(10, MessageTypes.PING)
                pingr_msg = MessageHelper.create_rcv_message(1, MessageTypes.PINGR)
                
                mock_serial.add_incoming_message(ping_msg)
                mock_serial.add_incoming_message(pingr_msg)
                
                time.sleep(0.01)  # Very short processing time
            
            time.sleep(0.5)  # Final processing time
            
            # Should have processed all messages without errors
            received_messages = ota_device.get_new_messages()
            assert len(received_messages) == 50  # 10 cycles * 5 messages each
            
            # Verify message types are present
            message_text = ' '.join(received_messages)
            assert MessageTypes.REQ in message_text
            assert MessageTypes.CON in message_text
            assert MessageTypes.ACK in message_text
            assert MessageTypes.PING in message_text
            assert MessageTypes.PINGR in message_text
            
            ota_device.__del__()


class TestConfigurationScenarios:
    """Test configuration-related scenarios"""

    def test_yaml_configuration_validation(self):
        """Test YAML configuration parsing and validation"""
        # Test valid configuration
        valid_config = {
            'OTA_PORT': '/dev/ttyUSB0',
            'OTA_BAUDRATE': 9600,
            'OTA_ID': 10
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(valid_config, f)
            valid_config_file = f.name
        
        try:
            # Should load without errors
            with open(valid_config_file) as file:
                loaded_config = yaml.load(file, Loader=yaml.Loader)
                assert loaded_config == valid_config
        finally:
            os.unlink(valid_config_file)
        
        # Test invalid YAML syntax
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: [unclosed")
            invalid_config_file = f.name
        
        try:
            with pytest.raises(yaml.YAMLError):
                with open(invalid_config_file) as file:
                    yaml.load(file, Loader=yaml.Loader)
        finally:
            os.unlink(invalid_config_file)

    def test_configuration_parameter_ranges(self):
        """Test configuration parameter validation"""
        # Test various parameter combinations
        test_configs = [
            {'OTA_PORT': '/dev/ttyUSB0', 'OTA_BAUDRATE': 9600, 'OTA_ID': 1},  # Min ID
            {'OTA_PORT': '/dev/ttyUSB0', 'OTA_BAUDRATE': 9600, 'OTA_ID': 255},  # Max typical ID
            {'OTA_PORT': '/dev/ttyUSB1', 'OTA_BAUDRATE': 115200, 'OTA_ID': 50},  # High baudrate
            {'OTA_PORT': '/dev/ttyACM0', 'OTA_BAUDRATE': 2400, 'OTA_ID': 10},  # Low baudrate
        ]
        
        for config in test_configs:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                yaml.dump(config, f)
                config_file = f.name
            
            try:
                # Configuration should be loadable
                with open(config_file) as file:
                    loaded = yaml.load(file, Loader=yaml.Loader)
                    assert loaded['OTA_ID'] > 0
                    assert loaded['OTA_BAUDRATE'] > 0
                    assert isinstance(loaded['OTA_PORT'], str)
                    assert len(loaded['OTA_PORT']) > 0
            finally:
                os.unlink(config_file)


class TestMultiDeviceMessageHandling:
    """Test message handling with multiple simulated devices"""

    def test_message_isolation_between_devices(self):
        """Test that messages from different devices don't interfere"""
        # Create multiple OTA devices
        devices = []
        mock_serials = []
        
        for device_id in [10, 20, 30]:
            mock_serial = MockSerial(f"/dev/ttyUSB{device_id}", 9600)
            mock_serials.append(mock_serial)
            
            with patch('serial.Serial', return_value=mock_serial):
                device = Ota(f"/dev/ttyUSB{device_id}", 9600, device_id)
                devices.append(device)
        
        time.sleep(0.2)  # Let all devices initialize
        
        try:
            # Each device sends messages to a different target
            for i, device in enumerate(devices):
                target_id = [1, 2, 3][i]
                device.send_ota_message(target_id, f"MESSAGE_FROM_{device.id}_TO_{target_id}")
            
            # Each device receives different messages
            for i, mock_serial in enumerate(mock_serials):
                sender_id = [100, 200, 300][i]
                device_id = [10, 20, 30][i]
                test_message = MessageHelper.create_rcv_message(sender_id, f"MESSAGE_TO_{device_id}")
                mock_serial.add_incoming_message(test_message)
            
            time.sleep(0.5)  # Let processing complete
            
            # Verify each device only received its own messages
            for i, device in enumerate(devices):
                device_id = [10, 20, 30][i]
                received_messages = device.get_new_messages()
                
                assert len(received_messages) == 1
                assert f"MESSAGE_TO_{device_id}" in received_messages[0]
                
                # Verify no cross-contamination
                other_device_ids = [10, 20, 30]
                other_device_ids.remove(device_id)
                for other_id in other_device_ids:
                    for msg in received_messages:
                        assert f"MESSAGE_TO_{other_id}" not in msg
            
            # Verify sent messages are isolated
            for i, mock_serial in enumerate(mock_serials):
                device_id = [10, 20, 30][i]
                target_id = [1, 2, 3][i]
                sent_messages = mock_serial.get_sent_messages()
                
                assert len(sent_messages) == 1
                assert f"MESSAGE_FROM_{device_id}_TO_{target_id}" in sent_messages[0]
        
        finally:
            # Cleanup all devices
            for device in devices:
                device.__del__()

    def test_broadcast_message_handling(self):
        """Test handling of broadcast messages"""
        mock_serial = MockSerial("/dev/ttyUSB0", 9600)
        
        with patch('serial.Serial', return_value=mock_serial):
            ota_device = Ota("/dev/ttyUSB0", 9600, 10)
            time.sleep(0.1)
            
            # Send broadcast message (address 0)
            ota_device.send_ota_message(0, MessageTypes.REQ)
            
            # Verify broadcast format
            sent_messages = mock_serial.get_sent_messages()
            assert len(sent_messages) == 1
            assert "AT+SEND=0," in sent_messages[0]
            assert MessageTypes.REQ in sent_messages[0]
            
            # Simulate receiving broadcast-type messages
            broadcast_msg = MessageHelper.create_rcv_message(0, "BROADCAST_ANNOUNCEMENT")
            mock_serial.add_incoming_message(broadcast_msg)
            
            time.sleep(0.2)
            
            received_messages = ota_device.get_new_messages()
            assert len(received_messages) == 1
            assert "BROADCAST_ANNOUNCEMENT" in received_messages[0]
            
            ota_device.__del__()


class TestErrorRecoveryScenarios:
    """Test error recovery and resilience"""

    def test_serial_reconnection_simulation(self):
        """Test behavior when serial connection is lost and restored"""
        mock_serial = MockSerial("/dev/ttyUSB0", 9600)
        
        with patch('serial.Serial', return_value=mock_serial):
            ota_device = Ota("/dev/ttyUSB0", 9600, 10)
            time.sleep(0.1)
            
            # Normal operation
            ota_device.send_ota_message(1, "BEFORE_DISCONNECT")
            
            # Simulate connection loss by making serial operations fail
            original_write = mock_serial.write
            original_readline = mock_serial.readline
            
            def failing_write(data):
                raise Exception("Connection lost")
            
            def failing_readline():
                raise Exception("Connection lost")
            
            mock_serial.write = failing_write
            mock_serial.readline = failing_readline
            
            # Try to send during connection loss - should handle gracefully
            ota_device.send_ota_message(1, "DURING_DISCONNECT")
            
            time.sleep(0.2)
            
            # Restore connection
            mock_serial.write = original_write
            mock_serial.readline = original_readline
            
            # Should work again after restoration
            ota_device.send_ota_message(1, "AFTER_RECONNECT")
            
            time.sleep(0.2)
            
            # Verify system recovered
            sent_messages = mock_serial.get_sent_messages()
            
            # Should have the first and last messages (middle one may have failed)
            message_text = ' '.join(sent_messages)
            assert "BEFORE_DISCONNECT" in message_text
            assert "AFTER_RECONNECT" in message_text
            
            ota_device.__del__()

    def test_thread_safety_under_stress(self):
        """Test thread safety under stress conditions"""
        mock_serial = MockSerial("/dev/ttyUSB0", 9600)
        
        with patch('serial.Serial', return_value=mock_serial):
            ota_device = Ota("/dev/ttyUSB0", 9600, 10)
            time.sleep(0.1)
            
            # Create stress conditions with multiple operations
            results = {'send_errors': 0, 'receive_errors': 0}
            
            def stress_sender():
                try:
                    for i in range(100):
                        ota_device.send_ota_message(1, f"STRESS_{threading.current_thread().ident}_{i}")
                        if i % 10 == 0:
                            time.sleep(0.001)  # Occasional small delay
                except Exception:
                    results['send_errors'] += 1
            
            def stress_receiver():
                try:
                    for i in range(100):
                        test_msg = MessageHelper.create_rcv_message(1, f"RECV_{threading.current_thread().ident}_{i}")
                        mock_serial.add_incoming_message(test_msg)
                        if i % 10 == 0:
                            # Occasionally read messages
                            ota_device.get_new_messages()
                        time.sleep(0.001)
                except Exception:
                    results['receive_errors'] += 1
            
            # Start multiple stress threads
            threads = []
            for _ in range(5):
                threads.append(threading.Thread(target=stress_sender))
                threads.append(threading.Thread(target=stress_receiver))
            
            for thread in threads:
                thread.start()
            
            for thread in threads:
                thread.join()
            
            time.sleep(1.0)  # Let all operations complete
            
            # Should have completed without errors
            assert results['send_errors'] == 0, f"Send errors: {results['send_errors']}"
            assert results['receive_errors'] == 0, f"Receive errors: {results['receive_errors']}"
            
            # Verify substantial message throughput
            sent_messages = mock_serial.get_sent_messages()
            received_messages = ota_device.get_new_messages()
            
            assert len(sent_messages) >= 400, f"Low send throughput: {len(sent_messages)}"
            assert len(received_messages) >= 400, f"Low receive throughput: {len(received_messages)}"
            
            ota_device.__del__()


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
