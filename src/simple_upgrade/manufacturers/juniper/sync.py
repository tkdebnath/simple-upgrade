"""
Juniper Junos sync module - Fetches device information.

This module provides Juniper-specific commands for fetching device information.
"""

from typing import Dict, Any
import re


def fetch_version(connection, platform: str, output: str) -> str:
    """
    Parse software version from Juniper device output.

    Args:
        connection: Active connection object
        platform: Platform name (juniper_junos)
        output: Output from 'show version' command

    Returns:
        Software version string
    """
    if isinstance(output, list):
        output = '\n'.join(output)

    patterns = [
        r'Current\s+version:\s+(\S+)',
        r'Kernel\s+version:\s+(\S+)',
        r'JUNOS\s+Version\s+(\S+)',
        r'JUNOS\s+(\S+)',
        r'JUNOS\s+\[(\S+)\]',
    ]

    for pattern in patterns:
        match = re.search(pattern, output)
        if match:
            return match.group(1)

    return 'Unknown'


def fetch_hostname(connection, platform: str, output: str) -> str:
    """
    Fetch device hostname from Juniper device.

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
        r'Host name:\s*(\S+)',
        r'Instance name:\s*(\S+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, output)
        if match:
            return match.group(1)

    return 'Unknown'


def fetch_inventory(connection, platform: str, output: str) -> Dict[str, str]:
    """
    Parse inventory information from Juniper device.

    Args:
        connection: Active connection object
        platform: Platform name
        output: Output from 'show chassis hardware' or 'show version'

    Returns:
        Dictionary with model, serial_number keys
    """
    if isinstance(output, list):
        output = '\n'.join(output)

    inventory = {}
    patterns = {
        'model': [
            r'Product name:\s*(\S+)',
            r'Hardware version:\s*(\S+)',
            r'Chassis:\s*(\S+)',
        ],
        'serial_number': [
            r'Serial number:\s*(\S+)',
            r'Serial ID:\s*(\S+)',
            r'Board\s+serial\s+number:\s*(\S+)',
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
    Fetch all device information using Juniper-specific commands.

    Args:
        connection: Active connection object
        platform: Platform name (juniper_junos)
        commands: Dictionary of commands to execute

    Returns:
        Dictionary with device information
    """
    info = {
        'manufacturer': 'Juniper',
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
    inventory_output = connection.send_command(commands.get('show_inventory', 'show chassis hardware'))
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
        r'Current time:\s+.*?System\s+started:\s+([\d\w\s,]+?)(?:\n|$)',
        r'(\d+)\s+days?,\s+(\d+)\s+hours?,\s+(\d+)\s+minutes?',
    ]

    for pattern in patterns:
        match = re.search(pattern, output)
        if match:
            if isinstance(match, re.Match):
                return match.group(0)
            return str(match)

    return ''


def _parse_flash_size(connection, platform: str, commands: Dict[str, str]) -> str:
    """Parse flash size from device."""
    try:
        output = connection.send_command(commands.get('show_system_storage', 'show system storage'))
        if isinstance(output, list):
            output = '\n'.join(output)

        patterns = [
            r'(\d+)\s*GB\s+total',
            r'(\d+)\s*MB\s+total',
            r'Total:\s*(\d+)\s*MB',
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
        output = connection.send_command(commands.get('show_system_memory', 'show system memory'))
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
