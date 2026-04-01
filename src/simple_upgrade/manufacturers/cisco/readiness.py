"""
Cisco IOS-XE/NX-OS readiness module - Validates device can be upgraded.

This module provides Cisco-specific readiness checks using scrapli.
Checks include:
    - Sufficient flash space
    - Version compatibility
    - Device health
"""

from typing import Dict, Any


def check_readiness(connection, platform: str, commands: Dict[str, str], golden_image: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if Cisco device is ready for upgrade.

    Args:
        connection: Active connection object
        platform: Platform name (cisco_iosxe, cisco_nxos)
        commands: Dictionary of commands to execute
        golden_image: Dictionary with golden image information

    Returns:
        Dictionary with:
            - ready: Boolean indicating if device is ready
            - messages: List of status messages
            - errors: List of errors encountered
    """
    result = {
        'ready': False,
        'messages': [],
        'errors': [],
    }

    # Check 1: Verify device is connected
    if not connection:
        result['errors'].append('Device not connected')
        return result

    # Check 2: Get flash space
    flash_output = connection.send_command(commands.get('dir', 'dir'))
    flash_info = _parse_flash_space(flash_output)
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
    current_version = _parse_version(version_output, platform)

    if current_version == golden_image.get('version'):
        result['errors'].append(f"Device already running target version {golden_image['version']}")
        return result

    result['messages'].append(f"Current version: {current_version}, Target: {golden_image.get('version')}")

    # Check 5: Check for any active sessions or locks
    # This is device-specific - for Cisco we can check for config locks
    try:
        config_output = connection.send_command("show configuration lock")
        if "locked" in config_output.lower():
            result['errors'].append('Configuration database is locked')
            return result
        result['messages'].append('No configuration locks detected')
    except Exception:
        # Some platforms may not support this command
        result['messages'].append('Could not verify configuration lock status')

    # All checks passed
    result['ready'] = True
    result['messages'].append('Device is ready for upgrade')

    return result


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

    # Look for patterns like "1234567890 bytes total" and "123456789 bytes free"
    total_match = re.search(r'(\d+)\s*bytes?\s*total', output, re.IGNORECASE)
    free_match = re.search(r'(\d+)\s*bytes?\s*free', output, re.IGNORECASE)

    if total_match:
        result['total'] = _format_bytes(total_match.group(1))
        result['total_bytes'] = int(total_match.group(1))

    if free_match:
        result['free'] = _format_bytes(free_match.group(1))
        result['free_bytes'] = int(free_match.group(1))

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


def _parse_version(output: str, platform: str) -> str:
    """Parse version from show version output."""
    if isinstance(output, list):
        output = '\n'.join(output)

    import re

    patterns = [
        r'Version\s+(\S+)',
        r'IOS-XE\s+Version\s+(\S+)',
        r'IOS\s+Version\s+(\S+)',
        r'Software\s+image\s+version:\s+(\S+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, output)
        if match:
            return match.group(1)

    return 'Unknown'
