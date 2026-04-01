"""Tests for the Device Profiles module."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from simple_upgrade.device_profiles import (
    load_profile,
    get_profile_path,
    list_manufacturers,
    list_models,
    find_device_profile,
    get_device_profile,
    get_command_template,
    get_upgrade_command,
    get_verification_command,
    execute_upgrade_command,
    execute_command,
    DEVICE_PROFILES_PATH
)


class TestDeviceProfiles:
    """Test cases for device profiles module."""

    def test_list_manufacturers(self):
        """Test listing manufacturers."""
        manufacturers = list_manufacturers()
        assert isinstance(manufacturers, list)
        assert len(manufacturers) > 0
        # Should include cisco, juniper, arista
        assert 'cisco' in manufacturers
        assert 'juniper' in manufacturers
        assert 'arista' in manufacturers

    def test_list_models_cisco(self):
        """Test listing models for Cisco."""
        models = list_models('cisco')
        assert isinstance(models, list)
        assert len(models) > 0

    def test_list_models_juniper(self):
        """Test listing models for Juniper."""
        models = list_models('juniper')
        assert isinstance(models, list)
        assert len(models) > 0

    def test_list_models_arista(self):
        """Test listing models for Arista."""
        models = list_models('arista')
        assert isinstance(models, list)
        assert len(models) > 0

    def test_get_device_profile_cisco(self):
        """Test getting Cisco device profile."""
        profile = get_device_profile('cisco', 'c9300')
        assert profile is not None
        assert 'manufacturer' in profile
        assert profile['manufacturer'] == 'Cisco'
        assert 'model' in profile
        assert profile['model'] == 'c9300'
        assert 'commands' in profile
        assert 'upgrade_commands' in profile

    def test_get_device_profile_juniper(self):
        """Test getting Juniper device profile."""
        profile = get_device_profile('juniper', 'mx')
        assert profile is not None
        assert 'manufacturer' in profile
        assert profile['manufacturer'] == 'Juniper'
        assert 'model' in profile

    def test_get_device_profile_arista(self):
        """Test getting Arista device profile."""
        profile = get_device_profile('arista', '7050')
        assert profile is not None
        assert 'manufacturer' in profile
        assert profile['manufacturer'] == 'Arista'
        assert 'model' in profile

    def test_get_device_profile_nonexistent(self):
        """Test getting non-existent device profile."""
        profile = get_device_profile('nonexistent', 'nonexistent')
        assert profile is None

    def test_find_device_profile_by_manufacturer(self):
        """Test finding profiles by manufacturer."""
        profiles = find_device_profile(manufacturer='cisco')
        assert isinstance(profiles, list)
        assert len(profiles) > 0

    def test_find_device_profile_by_mode(self):
        """Test finding profiles by mode."""
        profiles = find_device_profile(manufacturer='cisco', mode='switch')
        assert isinstance(profiles, list)
        assert len(profiles) > 0

    def test_find_device_profile_by_platform(self):
        """Test finding profiles by platform."""
        profiles = find_device_profile(manufacturer='cisco', platform='cisco_iosxe')
        assert isinstance(profiles, list)
        assert len(profiles) > 0

    def test_find_device_profile_by_series(self):
        """Test finding profiles by series."""
        profiles = find_device_profile(manufacturer='cisco', mode='switch', platform='cisco_iosxe', series='Catalyst 9300')
        assert isinstance(profiles, list)
        assert len(profiles) == 1

    def test_find_device_profile_by_model(self):
        """Test finding profile by model."""
        profiles = find_device_profile(manufacturer='cisco', mode='switch', platform='cisco_iosxe', model='c9300')
        assert isinstance(profiles, list)
        assert len(profiles) == 1

    def test_find_device_profile_empty_results(self):
        """Test finding profile with no matches."""
        profiles = find_device_profile(manufacturer='nonexistent')
        assert profiles == []

    def test_find_device_profile_narrowing(self):
        """Test narrowing down profiles."""
        # Start with many results
        profiles = find_device_profile(manufacturer='cisco')
        initial_count = len(profiles)

        # Add more filters
        profiles = find_device_profile(manufacturer='cisco', mode='switch')
        assert len(profiles) <= initial_count

        # Further narrow
        profiles = find_device_profile(manufacturer='cisco', mode='switch', platform='cisco_iosxe')
        assert len(profiles) <= len(profiles)

    def test_execute_upgrade_command(self):
        """Test execute_upgrade_command function."""
        profile = get_device_profile('cisco', 'c9300')
        assert profile is not None

        cmd = execute_upgrade_command(
            profile,
            'copy_image',
            protocol='tftp',
            server='192.168.1.100',
            path='images',
            image='cat9k-iosxe-17.9.4.bin'
        )

        assert 'copy tftp://' in cmd
        assert '192.168.1.100' in cmd
        assert 'cat9k-iosxe-17.9.4.bin' in cmd

    def test_execute_upgrade_command_invalid_type(self):
        """Test execute_upgrade_command with invalid type."""
        profile = get_device_profile('cisco', 'c9300')

        with pytest.raises(ValueError):
            execute_upgrade_command(profile, 'invalid_type', param='value')

    def test_execute_command(self):
        """Test execute_command function."""
        profile = get_device_profile('cisco', 'c9300')

        cmd = execute_command(
            profile,
            'show_version'
        )

        assert cmd == 'show version'

    def test_execute_command_with_variables(self):
        """Test execute_command with variables."""
        profile = get_device_profile('cisco', 'c9300')

        # This command doesn't have variables, so it should just return the command
        cmd = execute_command(profile, 'show_version')
        assert cmd == 'show version'

    def test_execute_command_invalid_type(self):
        """Test execute_command with invalid type."""
        profile = get_device_profile('cisco', 'c9300')

        with pytest.raises(ValueError):
            execute_command(profile, 'invalid_command')

    def test_get_command_template(self):
        """Test get_command_template function."""
        cmd = get_command_template('cisco', 'c9300', 'show_version')
        assert cmd == 'show version'

    def test_get_command_template_nonexistent(self):
        """Test get_command_template for non-existent command."""
        cmd = get_command_template('cisco', 'c9300', 'nonexistent')
        assert cmd is None

    def test_get_upgrade_command(self):
        """Test get_upgrade_command function."""
        cmd = get_upgrade_command('cisco', 'c9300', 'copy_image')
        assert cmd is not None
        assert '{protocol}' in cmd

    def test_get_upgrade_command_nonexistent(self):
        """Test get_upgrade_command for non-existent command."""
        cmd = get_upgrade_command('cisco', 'c9300', 'nonexistent')
        assert cmd is None

    def test_get_verification_command(self):
        """Test get_verification_command function."""
        cmd = get_verification_command('cisco', 'c9300', 'check_version')
        assert cmd is not None
        assert 'show version' in cmd

    def test_get_verification_command_nonexistent(self):
        """Test get_verification_command for non-existent command."""
        cmd = get_verification_command('cisco', 'c9300', 'nonexistent')
        assert cmd is None


class TestDeviceProfilesPath:
    """Test DEVICE_PROFILES_PATH constant."""

    def test_device_profiles_path_exists(self):
        """Test that DEVICE_PROFILES_PATH exists."""
        assert DEVICE_PROFILES_PATH.exists()
        assert DEVICE_PROFILES_PATH.is_dir()

    def test_device_profiles_path_structure(self):
        """Test that DEVICE_PROFILES_PATH has expected structure."""
        assert (DEVICE_PROFILES_PATH / 'cisco').is_dir()
        assert (DEVICE_PROFILES_PATH / 'juniper').is_dir()
        assert (DEVICE_PROFILES_PATH / 'arista').is_dir()
