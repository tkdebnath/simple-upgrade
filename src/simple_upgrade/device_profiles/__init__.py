"""
Device Profiles - Model-specific configurations for network devices.

This module provides device profile configurations for different manufacturers
and device groups. Each manufacturer has subdirectories containing profile
files for specific device models or model groups.

Usage:
    from simple_upgrade import get_device_profile, find_device_profile

    # Direct lookup
    profile = get_device_profile('cisco', 'c9300')
    print(profile['name'])
    print(profile['commands'])

    # Smart matching with mode and platform
    profiles = find_device_profile(manufacturer='cisco', mode='switch', platform='cisco_iosxe')
    if len(profiles) == 1:
        profile = profiles[0]
    elif len(profiles) > 1:
        # Narrow down with additional parameters
        profiles = find_device_profile(manufacturer='cisco', mode='switch', platform='cisco_iosxe', series='catalyst_9300')
        if len(profiles) == 1:
            profile = profiles[0]

    # Using command templates with variables
    from simple_upgrade import execute_upgrade_command

    copy_cmd = execute_upgrade_command(
        profile, 'copy_image', protocol='tftp', server='192.168.1.100',
        path='images', image='device.bin'
    )
"""

import os
import json
from typing import Dict, Any, Optional, List
from pathlib import Path


# Get the base path for device profiles
DEVICE_PROFILES_PATH = Path(__file__).parent


def load_profile(manufacturer: str, model: str) -> Optional[Dict[str, Any]]:
    """
    Load a device profile by manufacturer and model.

    Args:
        manufacturer: Manufacturer name (e.g., 'cisco', 'juniper', 'arista')
        model: Model identifier (e.g., 'c9300', 'c9400', 'mx')

    Returns:
        Dictionary containing device profile configuration or None if not found
    """
    profile_file = get_profile_path(manufacturer, model)
    if profile_file and profile_file.exists():
        try:
            with open(profile_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading profile {model}: {e}")
            return None
    return None


def get_profile_path(manufacturer: str, model: str) -> Optional[Path]:
    """
    Get the file path for a device profile.

    Args:
        manufacturer: Manufacturer name
        model: Model identifier

    Returns:
        Path object for the profile file or None if not found
    """
    # Try exact match first
    profile_file = DEVICE_PROFILES_PATH / manufacturer.lower() / f"{model.lower()}.json"
    if profile_file.exists():
        return profile_file

    # Try partial match (e.g., model '9300' matches 'c9300')
    manufacturer_path = DEVICE_PROFILES_PATH / manufacturer.lower()
    if manufacturer_path.exists():
        for file in manufacturer_path.glob("*.json"):
            filename = file.stem.lower()
            if filename == model.lower() or model.lower() in filename:
                return file

    return None


def list_manufacturers() -> list:
    """Return list of available manufacturers."""
    manufacturers = []
    if DEVICE_PROFILES_PATH.exists():
        for item in DEVICE_PROFILES_PATH.iterdir():
            if item.is_dir():
                manufacturers.append(item.name)
    return sorted(manufacturers)


def list_models(manufacturer: str) -> list:
    """
    List all models for a manufacturer.

    Args:
        manufacturer: Manufacturer name

    Returns:
        List of model identifiers
    """
    models = []
    manufacturer_path = DEVICE_PROFILES_PATH / manufacturer.lower()
    if manufacturer_path.exists():
        for file in manufacturer_path.glob("*.json"):
            models.append(file.stem)
    return sorted(models)


def find_device_profile(
    manufacturer: str,
    mode: str = None,
    platform: str = None,
    series: str = None,
    model: str = None
) -> List[Dict[str, Any]]:
    """
    Find device profiles matching specified criteria.

    This function allows flexible matching by checking if the profile contains
    matching values for any of the provided parameters. It returns a list of
    matching profiles which can then be narrowed down with additional parameters.

    Args:
        manufacturer: Manufacturer name (e.g., 'cisco', 'juniper', 'arista')
        mode: Device mode/type (e.g., 'switch', 'router', 'firewall')
        platform: Platform name (e.g., 'cisco_iosxe', 'juniper_junos')
        series: Device series (e.g., 'catalyst_9300', 'MX Series')
        model: Specific model identifier

    Returns:
        List of matching device profile dictionaries

    Example:
        # Find all Cisco switches
        profiles = find_device_profile(manufacturer='cisco', mode='switch')

        # Narrow down by platform
        profiles = find_device_profile(manufacturer='cisco', mode='switch', platform='cisco_iosxe')

        # Get specific profile (single result expected)
        profiles = find_device_profile(manufacturer='cisco', mode='switch', platform='cisco_iosxe', series='catalyst_9300')
        if len(profiles) == 1:
            profile = profiles[0]
    """
    manufacturer_path = DEVICE_PROFILES_PATH / manufacturer.lower()
    if not manufacturer_path.exists():
        return []

    matching_profiles = []

    for file in manufacturer_path.glob("*.json"):
        try:
            with open(file, 'r') as f:
                profile = json.load(f)

            # Check if profile matches all provided criteria
            match = True

            if mode and profile.get('mode') != mode:
                match = False

            if platform and profile.get('platform') != platform:
                match = False

            if series and profile.get('series') != series:
                match = False

            if model and profile.get('model') != model:
                match = False

            if match:
                matching_profiles.append(profile)

        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading profile {file.name}: {e}")
            continue

    return matching_profiles


def get_device_profile(manufacturer: str, model: str) -> Optional[Dict[str, Any]]:
    """
    Get device profile with commands and configurations.

    Args:
        manufacturer: Manufacturer name
        model: Model identifier

    Returns:
        Device profile dictionary or None
    """
    return load_profile(manufacturer, model)


def get_command_template(manufacturer: str, model: str, command_type: str) -> Optional[str]:
    """
    Get a specific command template for a device.

    Args:
        manufacturer: Manufacturer name
        model: Model identifier
        command_type: Type of command (e.g., 'show_version', 'upgrade', 'verify')

    Returns:
        Command template string or None
    """
    profile = load_profile(manufacturer, model)
    if profile and 'commands' in profile:
        return profile['commands'].get(command_type)
    return None


def get_upgrade_command(manufacturer: str, model: str, command_type: str) -> Optional[str]:
    """
    Get a specific upgrade command template for a device.

    Args:
        manufacturer: Manufacturer name
        model: Model identifier
        command_type: Type of upgrade command (e.g., 'copy_image', 'install_add', 'verify_image')

    Returns:
        Command template string or None
    """
    profile = load_profile(manufacturer, model)
    if profile and 'upgrade_commands' in profile:
        return profile['upgrade_commands'].get(command_type)
    return None


def get_verification_command(manufacturer: str, model: str, command_type: str) -> Optional[str]:
    """
    Get a specific verification command template for a device.

    Args:
        manufacturer: Manufacturer name
        model: Model identifier
        command_type: Type of verification command (e.g., 'check_version', 'check_uptime')

    Returns:
        Command template string or None
    """
    profile = load_profile(manufacturer, model)
    if profile and 'verification_commands' in profile:
        return profile['verification_commands'].get(command_type)
    return None


def execute_upgrade_command(profile: Dict[str, Any], command_type: str, **kwargs) -> str:
    """
    Execute an upgrade command by filling in template variables.

    Args:
        profile: Device profile dictionary
        command_type: Type of upgrade command (e.g., 'copy_image', 'install_add', 'verify_image')
        **kwargs: Variables to fill into the template (e.g., protocol='tftp', server='192.168.1.1')

    Returns:
        Completed command string with variables substituted

    Raises:
        ValueError: If command_type is not found in the profile's upgrade_commands
    """
    if command_type not in profile.get('upgrade_commands', {}):
        raise ValueError(f"Unknown command type '{command_type}'. Available: {list(profile.get('upgrade_commands', {}).keys())}")

    template = profile['upgrade_commands'][command_type]
    return template.format(**kwargs)


def execute_command(profile: Dict[str, Any], command_type: str, **kwargs) -> str:
    """
    Execute a standard command by filling in template variables.

    Args:
        profile: Device profile dictionary
        command_type: Type of command (e.g., 'show_version', 'show_inventory')
        **kwargs: Variables to fill into the template

    Returns:
        Completed command string with variables substituted

    Raises:
        ValueError: If command_type is not found in the profile's commands
    """
    if command_type not in profile.get('commands', {}):
        raise ValueError(f"Unknown command type '{command_type}'. Available: {list(profile.get('commands', {}).keys())}")

    template = profile['commands'][command_type]
    return template.format(**kwargs)
