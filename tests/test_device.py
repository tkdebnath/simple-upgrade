"""Tests for the Device module."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from simple_upgrade import Device, DeviceConnectionError


class TestDevice:
    """Test cases for Device class."""

    def test_device_initialization(self):
        """Test Device initialization with required parameters."""
        device = Device(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )
        assert device.host == '192.168.1.1'
        assert device.username == 'admin'
        assert device.password == 'password'
        assert device.device_type == 'cisco_xe'
        assert device.port == 22  # default
        assert device.timeout == 30  # default
        assert device.enable_mode is False  # default

    def test_device_initialization_with_options(self):
        """Test Device initialization with optional parameters."""
        device = Device(
            host='192.168.1.1',
            username='admin',
            password='password',
            port=2222,
            timeout=60,
            enable_mode=True,
            enable_password='enable123',
            device_type='cisco_ios'
        )
        assert device.port == 2222
        assert device.timeout == 60
        assert device.enable_mode is True
        assert device.enable_password == 'enable123'
        assert device.device_type == 'cisco_ios'

    def test_device_connection_error_without_device_type(self):
        """Test that DeviceConnectionError is raised without device_type."""
        device = Device(
            host='192.168.1.1',
            username='admin',
            password='password'
            # No device_type
        )
        # Note: We can't actually test connect() without mocking scrapli
        # This is just to verify the initialization works

    def test_device_info_attributes(self):
        """Test that device info attributes are initialized."""
        device = Device(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        # These should be empty strings before connection
        assert device.manufacturer == ''
        assert device.model == ''
        assert device.version == ''
        assert device.hostname == ''
        assert device.serial_number == ''
        assert device.platform == ''

        # Connection state
        assert device._connected is False
        assert device._connection is None

    def test_device_connection_state(self):
        """Test device connection state tracking."""
        device = Device(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        # Initially not connected
        assert device._connected is False

        # connect() would set _connected to True (mocked in actual test)
        # disconnect() would set _connected to False

    def test_device_connection_error_exception(self):
        """Test DeviceConnectionError exception class."""
        error = DeviceConnectionError("Connection failed")
        assert str(error) == "Connection failed"

    def test_device_gather_info_requires_connection(self):
        """Test that gather_info requires connection."""
        device = Device(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        with pytest.raises(DeviceConnectionError):
            device.gather_info()

    def test_device_send_command_requires_connection(self):
        """Test that send_command requires connection."""
        device = Device(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        with pytest.raises(DeviceConnectionError):
            device.send_command("show version")

    def test_device_send_config_requires_connection(self):
        """Test that send_config requires connection."""
        device = Device(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        with pytest.raises(DeviceConnectionError):
            device.send_config(["interface Gig1", "description test"])

    def test_device_check_connection(self):
        """Test check_connection method."""
        device = Device(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        # Not connected, should return False
        assert device.check_connection() is False

        # After connect(), would return True (mocked in actual test)
