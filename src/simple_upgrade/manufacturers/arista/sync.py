"""
Arista EOS sync module - Fetches device information.

Validates platform and channel before executing commands.
"""

from typing import Dict, Any


def fetch_info(connection, channel: str, platform: str, commands: Dict[str, str]) -> Dict[str, Any]:
    """
    Fetch all device information using Arista-specific commands.

    Args:
        connection: Active connection object
        channel: Channel name (e.g., scrapli)
        platform: Platform name (arista_eos)
        commands: Dictionary of commands to execute

    Returns:
        Dictionary with device information

    Raises:
        ValueError: If channel is invalid or platform is not an Arista platform
    """
    # Validate channel
    if channel.lower() != 'scrapli':
        raise ValueError(
            f"Invalid channel: '{channel}'. "
            f"Supported channel: scrapli"
        )

    # Validate platform is Arista
    platform_lower = platform.lower().replace('-', '_')
    valid_arista_platforms = ['arista_eos', 'arista', 'eos']

    if platform_lower not in valid_arista_platforms:
        raise ValueError(
            f"Invalid platform for Arista sync: '{platform}'. "
            f"Valid Arista platforms: {', '.join(valid_arista_platforms)}"
        )

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
    info['version'] = version_output
    info['current_version'] = info['version']

    # Fetch hostname
    hostname_output = connection.send_command(commands.get('show_version', 'show version'))
    info['hostname'] = hostname_output

    # Fetch inventory
    inventory_output = connection.send_command(commands.get('show_inventory', 'show inventory'))
    info['inventory'] = inventory_output

    return info
