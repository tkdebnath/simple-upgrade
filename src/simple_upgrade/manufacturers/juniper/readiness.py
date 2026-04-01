"""
Juniper Junos readiness module - Validates device can be upgraded.
"""

from typing import Dict, Any


def check_readiness(connection, platform: str, commands: Dict[str, str], golden_image: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if Juniper device is ready for upgrade.

    Args:
        connection: Active connection object
        platform: Platform name (juniper_junos)
        commands: Dictionary of commands to execute
        golden_image: Dictionary with golden image information

    Returns:
        Dictionary with ready status, messages, and errors
    """
    result = {
        'ready': False,
        'messages': [],
        'errors': [],
    }

    # Check 1: Verify connection
    if not connection:
        result['errors'].append('Device not connected')
        return result

    # Check 2: Get system storage
    storage_output = connection.send_command(commands.get('show_system_storage', 'show system storage'))
    storage_info = _parse_storage(storage_output)
    result['messages'].append(f"Storage: {storage_info['free']} free of {storage_info['total']}")

    # Check 3: Verify image size
    if 'image_size' in golden_image:
        image_size = golden_image['image_size']
        if storage_info['free_bytes'] < image_size:
            result['errors'].append(f"Insufficient storage space. Need {image_size} bytes, have {storage_info['free_bytes']}")
            return result
        result['messages'].append(f"Image size requirement met")

    # Check 4: Verify current version
    version_output = connection.send_command(commands.get('show_version', 'show version'))
    current_version = _parse_version(version_output)

    if current_version == golden_image.get('version'):
        result['errors'].append(f"Device already running target version {golden_image['version']}")
        return result

    result['messages'].append(f"Current version: {current_version}, Target: {golden_image.get('version')}")

    # Check 5: Check route engine redundancy (for MX series)
    if 'mx' in platform.lower():
        try:
            fabric_output = connection.send_command(commands.get('show_chassis_fabric', 'show chassis fabric'))
            if 'healthy' in fabric_output.lower():
                result['messages'].append('Route engine redundancy: OK')
            else:
                result['messages'].append('Route engine redundancy: Warning')
        except Exception:
            result['messages'].append('Could not verify route engine redundancy')

    result['ready'] = True
    result['messages'].append('Device is ready for upgrade')

    return result


def _parse_storage(output: str) -> Dict[str, str]:
    """Parse storage information from show system storage output."""
    if isinstance(output, list):
        output = '\n'.join(output)

    result = {
        'total': 'Unknown',
        'free': 'Unknown',
        'total_bytes': 0,
        'free_bytes': 0,
    }

    import re
    total_match = re.search(r'(\d+)\s*(?:KB|MB|GB)\s*total', output, re.IGNORECASE)
    free_match = re.search(r'(\d+)\s*(?:KB|MB|GB)\s*free', output, re.IGNORECASE)

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


def _parse_version(output: str) -> str:
    """Parse version from show version output."""
    if isinstance(output, list):
        output = '\n'.join(output)

    import re
    patterns = [
        r'Current\s+version:\s+(\S+)',
        r'Kernel\s+version:\s+(\S+)',
        r'JUNOS\s+Version\s+(\S+)',
        r'JUNOS\s+(\S+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, output)
        if match:
            return match.group(1)

    return 'Unknown'
