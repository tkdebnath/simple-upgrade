"""
Cisco IOS-XE/NX-OS readiness module - Validates device can be upgraded.

Validates platform and channel before executing checks.
"""

import re
from typing import Dict, Any


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

    # Use connection as context manager if it supports __enter__ and __exit__
    if hasattr(connection, '__enter__') and hasattr(connection, '__exit__'):
        with connection:
            # Check 2: Get flash space
            flash_output = connection.send_command(commands.get('dir', 'dir'))
            flash_output_str = str(flash_output.result)
            flash_info = _parse_flash_space(flash_output_str)
            result['messages'].append(f"Flash space: {flash_info['free']} free of {flash_info['total']}")

            # Check 3: Verify image size requirement
            if 'image_size' in golden_image:
                image_size = golden_image['image_size']
                if flash_info['free_bytes'] < image_size:
                    result['errors'].append(f"Insufficient flash space. Need {image_size} bytes, have {flash_info['free_bytes']}")
                    return result
                result['messages'].append(f"Image size requirement met: {image_size} bytes available")

            # Check 4: Verify current version is not same as golden image
            version_output = connection.send_command(commands.get('show_version', 'show version'))
            current_version = _parse_version(str(version_output.result), platform)

            if current_version == golden_image.get('version'):
                result['errors'].append(f"Device already running target version {golden_image['version']}")
                return result

            result['messages'].append(f"Current version: {current_version}, Target: {golden_image.get('version')}")

            # Check 5: Check for any active sessions or locks
            try:
                config_output = connection.send_command("show configuration lock")
                if "locked" in config_output.lower():
                    result['errors'].append('Configuration database is locked')
                    return result
                result['messages'].append('No configuration locks detected')
            except Exception:
                result['messages'].append('Could not verify configuration lock status')
    else:
        # Fallback: use connection without context manager
        # Check 2: Get flash space
        flash_output = connection.send_command(commands.get('dir', 'dir'))
        flash_output_str = str(flash_output.result)
        flash_info = _parse_flash_space(flash_output_str)
        result['messages'].append(f"Flash space: {flash_info['free']} free of {flash_info['total']}")

        # Check 3: Verify image size requirement
        if 'image_size' in golden_image:
            image_size = golden_image['image_size']
            if flash_info['free_bytes'] < image_size:
                result['errors'].append(f"Insufficient flash space. Need {image_size} bytes, have {flash_info['free_bytes']}")
                return result
            result['messages'].append(f"Image size requirement met: {image_size} bytes available")

        # Check 4: Verify current version is not same as golden image
        version_output = connection.send_command(commands.get('show_version', 'show version'))
        current_version = _parse_version(str(version_output.result), platform)

        if current_version == golden_image.get('version'):
            result['errors'].append(f"Device already running target version {golden_image['version']}")
            return result

        result['messages'].append(f"Current version: {current_version}, Target: {golden_image.get('version')}")

        # Check 5: Check for any active sessions or locks
        try:
            config_output = connection.send_command("show configuration lock")
            if "locked" in config_output.lower():
                result['errors'].append('Configuration database is locked')
                return result
            result['messages'].append('No configuration locks detected')
        except Exception:
            result['messages'].append('Could not verify configuration lock status')

    # All checks passed
    result['ready'] = True
    result['messages'].append('Device is ready for upgrade')

    return result
