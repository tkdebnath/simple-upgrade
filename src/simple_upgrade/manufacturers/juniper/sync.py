"""
Juniper Junos sync module - Fetches device information.

Validates platform and channel before executing commands.
"""

from typing import Dict, Any


def _validate_channel(connection) -> None:
    """
    Validate that the connection is a scrapli connection.

    Args:
        connection: Connection object to validate

    Raises:
        ValueError: If connection is not a scrapli connection
    """
    # Check if connection has send_command method
    if not hasattr(connection, 'send_command'):
        raise ValueError(
            "Invalid connection object. Expected a connection with send_command method."
        )

    # Check module to identify connection type
    module = getattr(connection, '__module__', '')
    if 'scrapli' not in module:
        raise ValueError(
            f"Invalid connection type: {module}. "
            f"Expected scrapli connection."
        )


def fetch_info(connection, platform: str, commands: Dict[str, str]) -> Dict[str, Any]:
    """
    Fetch all device information using Juniper-specific commands.

    Args:
        connection: Active connection object
        platform: Platform name (juniper_junos)
        commands: Dictionary of commands to execute

    Returns:
        Dictionary with device information

    Raises:
        ValueError: If platform is not a Juniper platform or connection is not scrapli
    """
    # Validate channel
    _validate_channel(connection)

    # Validate platform is Juniper
    platform_lower = platform.lower().replace('-', '_')
    valid_juniper_platforms = ['juniper_junos', 'juniper', 'junos']

    if platform_lower not in valid_juniper_platforms:
        raise ValueError(
            f"Invalid platform for Juniper sync: '{platform}'. "
            f"Valid Juniper platforms: {', '.join(valid_juniper_platforms)}"
        )

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
    info['version'] = version_output
    info['current_version'] = info['version']

    # Fetch hostname
    hostname_output = connection.send_command(commands.get('show_version', 'show version'))
    info['hostname'] = hostname_output

    # Fetch inventory
    inventory_output = connection.send_command(commands.get('show_inventory', 'show chassis hardware'))
    info['inventory'] = inventory_output

    return info
