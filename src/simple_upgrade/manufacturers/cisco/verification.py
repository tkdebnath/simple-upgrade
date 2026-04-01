"""
Cisco IOS-XE/NX-OS verification module - Confirms version match.

This module provides Cisco-specific version verification using scrapli.
"""

from typing import Dict, Any


def verify_version(connection, platform: str, commands: Dict[str, str], golden_image: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify the device is running the target version.

    Args:
        connection: Active connection object (scrapli)
        platform: Platform name (cisco_iosxe, cisco_nxos)
        commands: Dictionary of commands to execute
        golden_image: Dictionary with golden image information

    Returns:
        Dictionary with:
            - verified: Boolean indicating if version matches
            - current_version: Current version on device
            - target_version: Target version to verify
            - message: Status message
    """
    result = {
        'verified': False,
        'current_version': '',
        'target_version': golden_image.get('version', ''),
        'message': '',
    }

    # Fetch current version
    version_output = connection.send_command(commands.get('show_version', 'show version'))
    current_version = _parse_version(version_output, platform)
    result['current_version'] = current_version

    # Compare with target
    if current_version == result['target_version']:
        result['verified'] = True
        result['message'] = f'Version verified: {current_version}'
    else:
        result['message'] = f'Version mismatch. Current: {current_version}, Target: {result['target_version']}'

    return result


def _parse_version(output: str, platform: str) -> str:
    """
    Parse software version from show version output.

    Args:
        output: Output from 'show version' command
        platform: Platform name

    Returns:
        Software version string
    """
    if isinstance(output, list):
        output = '\n'.join(output)

    import re

    # Platform-specific patterns
    if 'nx-os' in platform.lower():
        nxos_patterns = [
            r'NXOS\s+Version\s+(\S+)',
            r'Software\s+version:\s+(\S+)',
        ]
        for pattern in nxos_patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return match.group(1)

    # Generic Cisco patterns
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


import re