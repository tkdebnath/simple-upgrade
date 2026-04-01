"""
Cisco IOS-XE/NX-OS sync module - Fetches device information.

This module provides Cisco-specific commands for fetching device information
during the sync stage of the upgrade workflow.
"""

from typing import Dict, Any, Optional
import re


def fetch_version(connection, platform: str, output: str) -> str:
    """
    Parse software version from Cisco device output.

    Args:
        connection: Active connection object (scrapli/unicon)
        platform: Platform name (cisco_iosxe, cisco_nxos)
        output: Output from 'show version' command

    Returns:
        Software version string
    """
    # Normalize output
    if isinstance(output, list):
        output = '\n'.join(output)

    # Cisco IOS-XE format: Version 17.9.4
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


def fetch_hostname(connection, platform: str, output: str) -> str:
    """
    Fetch device hostname from Cisco device.

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
        r'hostname\s+(\S+)',
        r'System\s+name:\s+(\S+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, output)
        if match:
            return match.group(1)

    return 'Unknown'


def fetch_inventory(connection, platform: str, output: str) -> Dict[str, str]:
    """
    Parse inventory information from Cisco device.

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
            r'PID:\s*(\S+)',
            r'Platform:\s*(\S+)',
            r'Catalyst\s+(\d+)',
            r'Processor\s+board\s+ID\s+(\S+)',
        ],
        'serial_number': [
            r'System\s+Serial\s+Number:\s*(\S+)',
            r'Serial\s+Number:\s*(\S+)',
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
    Fetch all device information using Cisco-specific commands.

    Args:
        connection: Active connection object
        platform: Platform name (cisco_iosxe, cisco_nxos)
        commands: Dictionary of commands to execute

    Returns:
        Dictionary with device information
    """
    info = {
        'manufacturer': 'Cisco',
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

    # Parse uptime and boot info from version output
    version_output = connection.send_command(commands.get('show_version', 'show version'))
    info['uptime'] = _parse_uptime(version_output)
    _parse_boot_info(info, version_output, platform)

    # Get flash and memory size
    info['flash_size'] = _parse_flash_size(connection, platform, commands)
    info['memory_size'] = _parse_memory_size(connection, platform, commands)

    return info


def _parse_uptime(output: str) -> str:
    """Parse uptime from show version output."""
    if isinstance(output, list):
        output = '\n'.join(output)

    patterns = [
        r'uptime is\s+([\d\w\s,]+?)(?:,|\s+since|$)',
        r'uptime:\s+([\d\w\s,]+?)(?:,|\s+since|$)',
        r'up\s+([\d\w\s,]+?)(?:,|\s+since|$)',
    ]

    for pattern in patterns:
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ''


def _parse_boot_info(info: Dict[str, Any], output: str, platform: str):
    """Parse boot method and config register from output."""
    if isinstance(output, list):
        output = '\n'.join(output)

    # Config register
    patterns = [
        r'config register is\s+(\S+)',
        r'configuration register is\s+(\S+)',
        r'Config\s+register\s+=\s+(\S+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            info['config_register'] = match.group(1)
            break

    # Boot method
    patterns = [
        r'image file is\s+(\S+)',
        r'Last reload reason:\s*(.+?)(?:\n|$)',
    ]

    for pattern in patterns:
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if '0x' not in value.lower():
                info['boot_method'] = value
            break

    # NX-OS specific boot mode
    if 'nx-os' in platform.lower() or 'nx-os' in output.lower():
        match = re.search(r'Boot mode:\s*(\S+)', output, re.IGNORECASE)
        if match:
            info['boot_mode'] = match.group(1)


def _parse_flash_size(connection, platform: str, commands: Dict[str, str]) -> str:
    """Parse flash size from device."""
    try:
        output = connection.send_command(commands.get('dir', 'dir'))
        if isinstance(output, list):
            output = '\n'.join(output)

        patterns = [
            r'(\d+)\s*(?:KB|MB|GB).*\bfree',
            r'total\s+(\d+)\s*(?:KB|MB|GB)',
        ]

        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return match.group(1) + ' ' + ('KB' if 'KB' in output.upper() else 'MB' if 'MB' in output.upper() else 'GB')
    except Exception:
        pass
    return ''


def _parse_memory_size(connection, platform: str, commands: Dict[str, str]) -> str:
    """Parse memory size from device."""
    try:
        output = connection.send_command(commands.get('show_inventory', 'show inventory'))
        if isinstance(output, list):
            output = '\n'.join(output)

        patterns = [
            r'Processor\s+with\s+(\d+\s+\w+)\s+of\s+memory',
            r'System\s+memory\s+:\s*(\d+\s+\w+)',
            r'Memory\s+\(System\):\s*(\d+\s+\w+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return match.group(1).strip()
    except Exception:
        pass
    return ''
