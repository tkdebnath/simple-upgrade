"""
Arista EOS sync module - Fetches device information.
"""

from typing import Dict, Any
import re


def fetch_version(connection, platform: str, output: str) -> str:
    """
    Parse software version from Arista device output.

    Args:
        connection: Active connection object
        platform: Platform name (arista_eos)
        output: Output from 'show version' command

    Returns:
        Software version string
    """
    if isinstance(output, list):
        output = '\n'.join(output)

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


def fetch_hostname(connection, platform: str, output: str) -> str:
    """
    Fetch device hostname from Arista device.

    Args:
        connection: Active connection object
        platform: Platform name
        output: Output from command

    Returns:
        Hostname string
    """
    if isinstance(output, list):
        output = '\n'.join(output)

    patterns = [
        r'hostname:\s*(\S+)',
        r'Name:\s*(\S+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, output)
        if match:
            return match.group(1)

    return 'Unknown'


def fetch_inventory(connection, platform: str, output: str) -> Dict[str, str]:
    """
    Parse inventory information from Arista device.

    Args:
        connection: Active connection object
        platform: Platform name
        output: Output from 'show inventory' or 'show version'

    Returns:
        Dictionary with model, serial_number keys
    """
    if isinstance(output, list):
        output = '\n'.join(output)

    inventory = {}
    patterns = {
        'model': [
            r'Product Name:\s*(\S+)',
            r'Hardware version:\s*(\S+)',
            r'Model number:\s*(\S+)',
        ],
        'serial_number': [
            r'Serial Number:\s*(\S+)',
            r'Serial ID:\s*(\S+)',
            r'SN:\s*(\S+)',
        ],
    }

    for key, patterns_list in patterns.items():
        for pattern in patterns_list:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                inventory[key] = match.group(1)
                break

    return inventory


def fetch_info(connection, platform: str, commands: Dict[str, str]) -> Dict[str, Any]:
    """
    Fetch all device information using Arista-specific commands.

    Args:
        connection: Active connection object
        platform: Platform name (arista_eos)
        commands: Dictionary of commands to execute

    Returns:
        Dictionary with device information
    """
    info = {
        'manufacturer': 'Arista',
        'model': '',
        'version': '',
        'current_version': '',
        'hostname': '',
        'serial': '',
        'serial_number': '',
        'platform': platform,
        'uptime': '',
        'boot_method': '',
        'boot_mode': '',
        'config_register': '',
        'flash_size': '',
        'memory_size': '',
    }

    # Fetch version
    version_output = connection.send_command(commands.get('show_version', 'show version'))
    info['version'] = fetch_version(connection, platform, version_output)
    info['current_version'] = info['version']

    # Fetch hostname
    hostname_output = connection.send_command(commands.get('show_version', 'show version'))
    info['hostname'] = fetch_hostname(connection, platform, hostname_output)

    # Fetch inventory
    inventory_output = connection.send_command(commands.get('show_inventory', 'show inventory'))
    inventory = fetch_inventory(connection, platform, inventory_output)
    info['model'] = inventory.get('model', '')
    info['serial_number'] = inventory.get('serial_number', '')
    info['serial'] = info['serial_number']

    # Parse uptime
    info['uptime'] = _parse_uptime(version_output)

    # Get flash and memory size
    info['flash_size'] = _parse_flash_size(connection, platform, commands)
    info['memory_size'] = _parse_memory_size(connection, platform, commands)

    return info


def _parse_uptime(output: str) -> str:
    """Parse uptime from show version output."""
    if isinstance(output, list):
        output = '\n'.join(output)

    patterns = [
        r'Up\s+time:\s+([\d\w\s,]+?)(?:\n|$)',
        r'Uptime:\s+([\d\w\s,]+?)(?:\n|$)',
    ]

    for pattern in patterns:
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ''


def _parse_flash_size(connection, platform: str, commands: Dict[str, str]) -> str:
    """Parse flash size from device."""
    try:
        output = connection.send_command(commands.get('show_disk_usage', 'show disk usage'))
        if isinstance(output, list):
            output = '\n'.join(output)

        patterns = [
            r'(\d+)\s*GB\s+total',
            r'(\d+)\s*MB\s+total',
        ]

        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                return match.group(1) + ' ' + ('GB' if 'GB' in match.group(0) else 'MB')
    except Exception:
        pass
    return ''


def _parse_memory_size(connection, platform: str, commands: Dict[str, str]) -> str:
    """Parse memory size from device."""
    try:
        output = connection.send_command(commands.get('show_environment', 'show environment'))
        if isinstance(output, list):
            output = '\n'.join(output)

        patterns = [
            r'Memory:\s*(\d+)\s*MB',
            r'RAM:\s*(\d+)\s*MB',
        ]

        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                return match.group(1) + ' MB'
    except Exception:
        pass
    return ''
