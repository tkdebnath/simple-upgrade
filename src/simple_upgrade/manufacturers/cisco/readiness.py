"""
Cisco IOS-XE/NX-OS readiness module - Validates device can be upgraded.

Validates platform and channel before executing checks.
"""

import re
from typing import Dict, Any

# import helpers
from .__helpers import flash_free_space
from netutils.os_version import compare_version_loose


def _validate_channel(connection) -> None:
    """
    Validate that the connection is a scrapli connection.

    Args:
        connection: Connection object to validate

    Raises:
        ValueError: If connection is not a scrapli connection
    """
    if not hasattr(connection, 'send_command'):
        raise ValueError(
            "Invalid connection object. Expected a connection with send_command method."
        )

    module = getattr(connection, '__module__', '')
    if 'scrapli' not in module:
        raise ValueError(
            f"Invalid connection type: {module}. "
            f"Expected scrapli connection."
        )


def _parse_version(output: str, platform: str) -> str:
    """
    Parse version from show version output.

    Args:
        output: Raw output from show version
        platform: Platform name

    Returns:
        Version string
    """
    patterns = [
        r'Version\s+(\S+)',
        r'IOS-XE\s+Version\s+(\S+)',
        r'IOS\s+Version\s+(\S+)',
        r'Software\s+image\s+version:\s+(\S+)',
        r'Version\s+(\d+\.\d+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, output)
        if match:
            return match.group(1)

    return 'Unknown'


def _parse_flash_space(output: str) -> Dict[str, str]:
    """Parse flash space information from dir output."""
    if isinstance(output, list):
        output = '\n'.join(output)

    result = {
        'total': 'Unknown',
        'free': 'Unknown',
        'total_bytes': 0,
        'free_bytes': 0,
    }

    total_match = re.search(r'(\d+)\s*bytes?\s*total', output, re.IGNORECASE)
    free_match = re.search(r'(\d+)\s*bytes?\s*free', output, re.IGNORECASE)

    if total_match:
        result['total_bytes'] = int(total_match.group(1))
        result['total'] = _format_bytes(total_match.group(1))

    if free_match:
        result['free_bytes'] = int(free_match.group(1))
        result['free'] = _format_bytes(free_match.group(1))

    return result


def _format_bytes(bytes_str: str) -> str:
    """Convert bytes to human-readable format."""
    bytes_int = int(bytes_str)
    if bytes_int >= 1024**3:
        return f"{bytes_int / (1024**3):.2f} GB"
    elif bytes_int >= 1024**2:
        return f"{bytes_int / (1024**2):.2f} MB"
    elif bytes_int >= 1024:
        return f"{bytes_int / 1024:.2f} KB"
    return f"{bytes_int} bytes"


def check_readiness(connection, channel: str, platform: str, commands: Dict[str, str], golden_image: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if Cisco device is ready for upgrade.

    Args:
        connection: Active connection object
        channel: Channel name (e.g., scrapli)
        platform: Platform name (cisco_iosxe, cisco_nxos)
        commands: Dictionary of commands to execute
        golden_image: Dictionary with golden image information

    Returns:
        Dictionary with:
            - ready: Boolean indicating if device is ready
            - messages: List of status messages
            - errors: List of errors encountered
    """
    # Validate channel
    if channel.lower() != 'scrapli':
        raise ValueError(
            f"Invalid channel: '{channel}'. "
            f"Supported channel: scrapli"
        )

    # Validate platform is Cisco
    platform_lower = platform.lower().replace('-', '_')
    valid_cisco_platforms = ['cisco_ios', 'cisco_iosxe', 'cisco_nxos', 'cisco_xe', 'cisco_nexus']

    if platform_lower not in valid_cisco_platforms:
        raise ValueError(
            f"Invalid platform for Cisco readiness: '{platform}'. "
            f"Valid Cisco platforms: {', '.join(valid_cisco_platforms)}"
        )

    result = {
        'ready': False,
        'messages': [],
        'errors': [],
    }

    # Check 1: Verify device is connected
    if not connection:
        result['errors'].append('Device not connected')
        return result

    # Check if connection is already open (managed externally)
    # Use context manager only if connection is not already open
    needs_closing = False
    if hasattr(connection, 'is_open'):
        needs_closing = not connection.is_open
    elif hasattr(connection, '_connected'):
        needs_closing = not connection._connected

    if needs_closing and hasattr(connection, '__enter__') and hasattr(connection, '__exit__'):
        with connection:
            _run_readiness_checks(connection, platform_lower, golden_image, commands, result)
    else:
        _run_readiness_checks(connection, platform_lower, golden_image, commands, result)

    return result


def _run_readiness_checks(connection, platform_lower, golden_image, commands, result):
    """
    Run readiness checks - shared between context manager and non-context manager paths.

    Args:
        connection: Active connection object
        platform_lower: Lowercase platform name
        golden_image: Golden image dictionary
        commands: Command dictionary
        result: Result dictionary to populate
    """
    # Check 1: using golden image file size determine if free space is enough or not
    image_size = golden_image.get('image_size', 0)

    if platform_lower in ['cisco_ios', 'cisco_iosxe']:
        # Check 2: Get all flash storages
        show_file_systems = connection.send_command("show file systems")
        show_file_systems_parsed = show_file_systems.genie_parse_output()
        if show_file_systems_parsed:
            free_space = flash_free_space(show_file_systems_parsed, image_size)
            if not free_space:
                result['errors'].append('Insufficient flash space')
                return
            result['messages'].append('Sufficient flash space')

        # Check 3: if upgrade or downgrade
        show_version = connection.send_command("show version")
        show_version_parsed = show_version.genie_parse_output()
        if show_version_parsed and show_version_parsed.get('version', {}).get('version', ''):
            current_version = show_version_parsed['version']['version']
            target_version = golden_image.get('version', '')
            if target_version:
                is_equal = compare_version_loose(current_version, "==", target_version)
                if is_equal:
                    result['errors'].append('Device already running target version')
                    return

                is_less = compare_version_loose(current_version, "<", target_version)
                if is_less:
                    result['messages'].append('Upgrade')
                else:
                    result['errors'].append('Downgrade not allowed')
                    return

        # Check 4: Get flash space
        flash_output = connection.send_command(commands.get('dir', 'dir'))
        flash_output_str = str(flash_output.result)
        flash_info = _parse_flash_space(flash_output_str)
        result['messages'].append(f"Flash space: {flash_info['free']} free of {flash_info['total']}")
    else:
        # For other platforms, use the fallback method
        flash_output = connection.send_command(commands.get('dir', 'dir'))
        flash_output_str = str(flash_output.result)
        flash_info = _parse_flash_space(flash_output_str)
        result['messages'].append(f"Flash space: {flash_info['free']} free of {flash_info['total']}")

    # Check 5: Verify image size requirement
    if image_size > 0:
        if flash_info['free_bytes'] < image_size:
            result['errors'].append(f"Insufficient flash space. Need {image_size} bytes, have {flash_info['free_bytes']}")
            return
        result['messages'].append(f"Image size requirement met: {image_size} bytes available")

    # Check 6: Verify current version is not same as golden image
    version_output = connection.send_command(commands.get('show_version', 'show version'))
    current_version = _parse_version(str(version_output.result), platform_lower)

    if current_version == golden_image.get('version'):
        result['errors'].append(f"Device already running target version {golden_image['version']}")
        return

    result['messages'].append(f"Current version: {current_version}, Target: {golden_image.get('version')}")

    # Check 7: Check for any active sessions or locks
    try:
        config_output = connection.send_command("show configuration lock")
        if "locked" in config_output.lower():
            result['errors'].append('Configuration database is locked')
            return
        result['messages'].append('No configuration locks detected')
    except Exception:
        result['messages'].append('Could not verify configuration lock status')

    # All checks passed
    result['ready'] = True
    result['messages'].append('Device is ready for upgrade')

    return result
