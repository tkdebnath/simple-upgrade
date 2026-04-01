"""
Device Profiles - Model-specific configurations for network devices.

This module provides device profile configurations for different manufacturers
and device groups. Each manufacturer has subdirectories containing profile
files for specific device models or model groups.

Usage:
    from simple_upgrade import get_device_profile

    profile = get_device_profile('cisco', 'c9300')
    print(profile['name'])
    print(profile['commands'])
"""

import os
import json
from typing import Dict, Any, Optional
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
