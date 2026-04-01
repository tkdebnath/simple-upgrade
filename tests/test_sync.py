"""Tests for the Sync module."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from simple_upgrade.sync import SyncManager, get_device_commands, sync_device


class TestGetDeviceCommands:
    """Test get_device_commands function."""

    def test_cisco_ios_commands(self):
        """Test getting commands for cisco_ios platform."""
        commands = get_device_commands('cisco_ios')
        assert 'version' in commands
        assert 'inventory' in commands
        assert 'license' in commands
        assert 'hardware' in commands
        assert commands['version'] == 'show version'

    def test_cisco_iosxe_commands(self):
        """Test getting commands for cisco_iosxe platform."""
        commands = get_device_commands('cisco_iosxe')
        assert 'version' in commands
        assert commands['version'] == 'show version'

    def test_cisco_nxos_commands(self):
        """Test getting commands for cisco_nxos platform."""
        commands = get_device_commands('cisco_nxos')
        assert 'version' in commands
        assert commands['version'] == 'show version'

    def test_juniper_junos_commands(self):
        """Test getting commands for juniper_junos platform."""
        commands = get_device_commands('juniper_junos')
        assert 'version' in commands
        assert commands['version'] == 'show version'

    def test_arista_eos_commands(self):
        """Test getting commands for arista_eos platform."""
        commands = get_device_commands('arista_eos')
        assert 'version' in commands
        assert commands['version'] == 'show version'

    def test_platform_case_insensitive(self):
        """Test that platform names are case-insensitive."""
        commands1 = get_device_commands('cisco_ios')
        commands2 = get_device_commands('CISCO_IOS')
        assert commands1 == commands2

    def test_platform_with_hyphen(self):
        """Test platform names with hyphens."""
        commands = get_device_commands('cisco-ios')
        assert 'version' in commands

    def test_default_fallback(self):
        """Test fallback to default commands."""
        commands = get_device_commands('unknown_platform')
        assert 'version' in commands


class TestSyncManager:
    """Test SyncManager class."""

    def test_sync_manager_initialization(self):
        """Test SyncManager initialization."""
        # This test would require mocking ConnectionManager
        # For now, just verify the class can be imported
        pass

    def test_sync_manager_with_platform(self):
        """Test SyncManager with explicit platform."""
        # This test would require mocking ConnectionManager
        pass

    def test_sync_manager_with_connection_manager(self):
        """Test SyncManager with connection manager."""
        # This test would require mocking ConnectionManager
        pass

    def test_normalize_output(self):
        """Test _normalize_output method."""
        sync = SyncManager(connection_manager=None, platform='cisco_ios')

        # Test list input
        result = sync._normalize_output(['line1', 'line2'])
        assert result == 'line1\nline2'

        # Test string input
        result = sync._normalize_output('output')
        assert result == 'output'

    def test_parse_version(self):
        """Test _parse_version method."""
        sync = SyncManager(connection_manager=None, platform='cisco_ios')

        # Test IOS-XE format
        output = "Cisco IOS Software, IOS-XE Software, Catalyst 9300\nVersion: 17.9.4"
        version = sync._parse_version(output)
        assert version == '17.9.4'

    def test_fetch_version_method(self):
        """Test fetch_version method exists."""
        sync = SyncManager(connection_manager=None, platform='cisco_ios')
        assert hasattr(sync, 'fetch_version')

    def test_fetch_inventory_method(self):
        """Test fetch_inventory method exists."""
        sync = SyncManager(connection_manager=None, platform='cisco_ios')
        assert hasattr(sync, 'fetch_inventory')

    def test_fetch_hostname_method(self):
        """Test fetch_hostname method exists."""
        sync = SyncManager(connection_manager=None, platform='cisco_ios')
        assert hasattr(sync, 'fetch_hostname')

    def test_fetch_manufacturer_method(self):
        """Test fetch_manufacturer method exists."""
        sync = SyncManager(connection_manager=None, platform='cisco_ios')
        assert hasattr(sync, 'fetch_manufacturer')

    def test_fetch_info_method(self):
        """Test fetch_info method exists."""
        sync = SyncManager(connection_manager=None, platform='cisco_ios')
        assert hasattr(sync, 'fetch_info')


class TestSyncManagerAttributes:
    """Test SyncManager attributes."""

    def test_info_attributes(self):
        """Test that info dictionary has expected keys."""
        sync = SyncManager(connection_manager=None, platform='cisco_ios')

        expected_keys = [
            'manufacturer', 'model', 'version', 'current_version',
            'hostname', 'serial', 'serial_number', 'platform',
            'uptime', 'boot_method', 'boot_mode', 'config_register',
            'flash_size', 'memory_size'
        ]

        for key in expected_keys:
            assert key in sync.info
