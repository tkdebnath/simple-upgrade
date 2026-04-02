"""
Arista EOS verification module - Confirms version match.
"""

from typing import Dict, Any


def verify_version(connection, platform: str, commands: Dict[str, str], golden_image: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify the device is running the target version.

    Args:
        connection: Active connection object
        platform: Platform name (arista_eos)
        commands: Dictionary of commands to execute
        golden_image: Dictionary with golden image information

    Returns:
        Dictionary with verified status, current_version, target_version, and message
    """
    result = {
        'verified': False,
        'current_version': '',
        'target_version': golden_image.get('version', ''),
        'message': '',
    }

    # Fetch current version
    version_output = connection.send_command(commands.get('show_version', 'show version'))
    current_version = _parse_version(version_output)
    result['current_version'] = current_version

    # Compare with target
    if current_version == result['target_version']:
        result['verified'] = True
        result['message'] = f'Version verified: {current_version}'
    else:
        target_ver = result['target_version']
        result['message'] = f'Version mismatch. Current: {current_version}, Target: {target_ver}'

    return result


def _parse_version(output: str) -> str:
    """Parse software version from show version output."""
    if isinstance(output, list):
        output = '\n'.join(output)

    import re
    patterns = [
        r'Software image version:\s+(\S+)',
        r'Cisco IOS Software,.*Version\s+(\S+)',
        r'Arista.*Version\s+(\S+)',
        r'EOS version:\s+(\S+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, output)
        if match:
            return match.group(1)

    return 'Unknown'
