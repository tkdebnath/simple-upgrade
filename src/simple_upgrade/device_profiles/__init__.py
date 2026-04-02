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

            # Check if model matches - check both 'model' field and 'models' list
            if model:
                model_match = profile.get('model') == model
                # Check if model is in the models list
                models_list = profile.get('models', [])
                if isinstance(models_list, list):
                    model_match = model_match or model in models_list
                elif isinstance(models_list, str):
                    # Handle string case (single model in list format)
                    model_match = model_match or models_list == model
                if not model_match:
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


def match_model_to_profile(model: str, manufacturer: str) -> Optional[Dict[str, Any]]:
    """
    Match a device model to a device profile.

    This function checks if a model matches a profile's 'model' field or
    is in the profile's 'models' list (if defined).

    Args:
        model: Device model identifier (e.g., 'C9300', 'C9300L')
        manufacturer: Manufacturer name (e.g., 'cisco', 'juniper', 'arista')

    Returns:
        Device profile dictionary if a match is found, None otherwise

    Example:
        # Match different C9300 variants to the same profile
        profile = match_model_to_profile('C9300L', 'cisco')
        # Returns the c9300.json profile since C9300L is in its models list
    """
    manufacturer_path = DEVICE_PROFILES_PATH / manufacturer.lower()
    if not manufacturer_path.exists():
        return None

    for file in manufacturer_path.glob("*.json"):
        try:
            with open(file, 'r') as f:
                profile = json.load(f)

            # Check if model matches the profile's model field (case-insensitive)
            if profile.get('model', '').lower() == model.lower():
                return profile

            # Check if model is in the models list (case-insensitive)
            models_list = profile.get('models', [])
            if isinstance(models_list, list):
                if model.lower() in [m.lower() for m in models_list]:
                    return profile
            elif isinstance(models_list, str):
                if models_list.lower() == model.lower():
                    return profile

        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading profile {file.name}: {e}")
            continue

    return None


def validate_device_profiles(manufacturer: str) -> Dict[str, Any]:
    """
    Validate device profiles for a manufacturer to ensure no duplicate model+platform combinations.

    This function checks that:
    1. No model+platform combination is defined in more than one profile
    2. No model appears in multiple profiles' 'models' lists (for the same platform)

    A model can appear in different profiles if they have different platforms.
    For example, "c9300" can be in both cisco_ios and cisco_iosxe profiles.

    Args:
        manufacturer: Manufacturer name (e.g., 'cisco', 'juniper', 'arista')

    Returns:
        Dictionary with:
            - valid: bool - True if no duplicates found
            - errors: list - List of duplicate model+platform errors
            - warnings: list - List of warnings

    Example:
        >>> result = validate_device_profiles('cisco')
        >>> if not result['valid']:
        ...     print("Duplicates found:", result['errors'])
    """
    manufacturer_path = DEVICE_PROFILES_PATH / manufacturer.lower()
    if not manufacturer_path.exists():
        return {
            'valid': True,
            'errors': [],
            'warnings': [],
            'message': f"Manufacturer '{manufacturer}' not found"
        }

    # Track model+platform references: (model, platform) -> set of profile_files
    model_platform_refs: Dict[tuple, set] = {}
    # Track all models: (model, platform) -> profile_file
    all_models: Dict[tuple, str] = {}

    for file in manufacturer_path.glob("*.json"):
        try:
            with open(file, 'r') as f:
                profile = json.load(f)

            profile_name = file.stem
            platform = profile.get('platform', '').lower()

            # Get the primary model
            primary_model = profile.get('model', '').lower()
            if primary_model:
                model_key = (primary_model, platform)
                if model_key in all_models:
                    # Duplicate model+platform combination
                    if model_key not in model_platform_refs:
                        model_platform_refs[model_key] = {all_models[model_key]}
                    model_platform_refs[model_key].add(profile_name)
                else:
                    # First occurrence - store
                    all_models[model_key] = profile_name

            # Get models from the models list (if any)
            models_list = profile.get('models', [])
            if isinstance(models_list, str):
                models_list = [models_list]

            for model in models_list:
                model_lower = model.lower()
                model_key = (model_lower, platform)
                if model_key in all_models:
                    # Model+platform already exists in a profile
                    if model_key not in model_platform_refs:
                        model_platform_refs[model_key] = {all_models[model_key]}
                    model_platform_refs[model_key].add(profile_name)
                else:
                    # First occurrence - store
                    all_models[model_key] = profile_name

        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading profile {file.name}: {e}")
            continue

    # Convert sets to lists for output
    model_platform_refs_list = {k: list(v) for k, v in model_platform_refs.items()}

    # Check for duplicates
    errors = []
    for (model, platform), profiles in model_platform_refs_list.items():
        if len(profiles) > 1:
            unique_profiles = set(profiles)
            if len(unique_profiles) > 1:
                errors.append(f"Model '{model}' with platform '{platform}' is defined in multiple profiles: {', '.join(profiles)}")

    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': [],
        'total_profiles': len(list(manufacturer_path.glob("*.json"))),
        'unique_model_platform_combinations': len(all_models)
    }
