"""
Cisco IOS-XE/NX-OS sync module - Fetches device information.
"""


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
    info['version'] = version_output
    info['current_version'] = info['version']

    # Fetch hostname
    hostname_output = connection.send_command(commands.get('show_version', 'show version'))
    info['hostname'] = hostname_output

    # Fetch inventory
    inventory_output = connection.send_command(commands.get('show_inventory', 'show inventory'))
    info['inventory'] = inventory_output

    return info
