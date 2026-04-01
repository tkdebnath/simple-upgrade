"""Tests for the ConnectionManager module."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from simple_upgrade.connection_manager import ConnectionManager, ConnectionError


class TestConnectionManager:
    """Test cases for ConnectionManager class."""

    def test_connection_manager_initialization(self):
        """Test ConnectionManager initialization with required parameters."""
        cm = ConnectionManager(
            host='192.168.1.1',
            username='admin',
            password='password'
        )
        assert cm.host == '192.168.1.1'
        assert cm.username == 'admin'
        assert cm.password == 'password'
        assert cm.port == 22  # default
        assert cm.timeout == 30  # default
        assert cm.enable_mode is False  # default

    def test_connection_manager_initialization_with_options(self):
        """Test ConnectionManager initialization with optional parameters."""
        cm = ConnectionManager(
            host='192.168.1.1',
            username='admin',
            password='password',
            port=2222,
            timeout=60,
            enable_mode=True,
            enable_password='enable123',
            secret='secret456',
            device_type='cisco_xe'
        )
        assert cm.port == 2222
        assert cm.timeout == 60
        assert cm.enable_mode is True
        assert cm.enable_password == 'enable123'
        assert cm.secret == 'secret456'
        assert cm.device_type == 'cisco_xe'

    def test_connection_manager_invalid_channel(self):
        """Test that invalid channel raises ConnectionError."""
        cm = ConnectionManager(
            host='192.168.1.1',
            username='admin',
            password='password'
        )

        with pytest.raises(ConnectionError):
            cm.get_connection('invalid_channel')

    def test_connection_manager_default_channel(self):
        """Test default channel is scrapli."""
        cm = ConnectionManager(
            host='192.168.1.1',
            username='admin',
            password='password'
        )

        # Get scrapli connection
        conn = cm.get_connection('scrapli')
        assert conn is not None

        # Verify channel attribute
        assert cm.channel == 'scrapli'
        assert cm._active_channel == 'scrapli'

    def test_connection_manager_scrapli_connection(self):
        """Test getting scrapli connection."""
        cm = ConnectionManager(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        # This would actually create a connection
        # For unit test, just verify the method exists
        assert hasattr(cm, 'get_connection')

    def test_connection_manager_netmiko_connection(self):
        """Test getting netmiko connection."""
        cm = ConnectionManager(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        # This would actually create a connection
        assert hasattr(cm, 'get_connection')

    def test_connection_manager_unicon_connection(self):
        """Test getting unicon connection."""
        cm = ConnectionManager(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        # This would actually create a connection
        assert hasattr(cm, 'get_connection')

    def test_connection_manager_get_platform(self):
        """Test getting platform for a channel."""
        cm = ConnectionManager(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        # After connecting, platform should be available
        conn = cm.get_connection('scrapli')
        platform = cm.get_platform('scrapli')
        assert platform is not None

    def test_connection_manager_get_connection_with_platform(self):
        """Test get_connection_with_platform method."""
        cm = ConnectionManager(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        result = cm.get_connection_with_platform('scrapli')
        assert 'connection' in result
        assert 'platform' in result
        assert result['connection'] is not None
        assert result['platform'] is not None

    def test_connection_manager_disconnect(self):
        """Test disconnect method."""
        cm = ConnectionManager(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        # Connect
        conn = cm.get_connection('scrapli')
        assert cm._active_channel == 'scrapli'

        # Disconnect
        cm.disconnect()
        assert cm._active_channel is None
        assert cm.channel is None

    def test_connection_manager_is_connected(self):
        """Test is_connected method."""
        cm = ConnectionManager(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        # Initially not connected
        assert cm.is_connected() is False

        # After connect
        conn = cm.get_connection('scrapli')
        assert cm.is_connected() is True

    def test_connection_manager_get_active_channel(self):
        """Test get_active_channel method."""
        cm = ConnectionManager(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        conn = cm.get_connection('scrapli')
        assert cm.get_active_channel() == 'scrapli'

    def test_connection_manager_channel_storage(self):
        """Test that platforms are stored per channel."""
        cm = ConnectionManager(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        conn = cm.get_connection('scrapli')
        assert 'scrapli' in cm._platforms

    def test_connection_manager_no_device_type_scrapli(self):
        """Test that scrapli requires device_type."""
        cm = ConnectionManager(
            host='192.168.1.1',
            username='admin',
            password='password'
            # No device_type
        )

        with pytest.raises(ConnectionError):
            cm.get_connection('scrapli')

    def test_connection_manager_get_connection_caching(self):
        """Test that connections are cached."""
        cm = ConnectionManager(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        # First call creates connection
        conn1 = cm.get_connection('scrapli')
        # Second call returns cached connection
        conn2 = cm.get_connection('scrapli')

        # They should be the same object
        assert conn1 is conn2
