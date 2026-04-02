"""
Cisco IOS-XE/NX-OS sync module - Fetches device information.

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


def fetch_info(connection, channel: str, platform: str, commands: Dict[str, str]) -> Dict[str, Any]:
    """
    Fetch all device information using Cisco-specific commands.

    Args:
        connection: Active connection object
        channel: Channel name (e.g., scrapli)
        platform: Platform name (cisco_ios, cisco_iosxe, cisco_nxos)
        commands: Dictionary of commands to execute

    Returns:
        Dictionary with device information

    Raises:
        ValueError: If channel is invalid or platform is not a Cisco platform
    """
    # Validate channel
    if channel.lower() != 'scrapli':
        raise ValueError(
            f"Invalid channel: '{channel}'. "
            f"Supported channel: scrapli"
        )

    # Validate platform is Cisco
    platform_lower = platform.lower().replace('-', '_')
    valid_cisco_platforms = ['cisco_ios', 'cisco_iosxe', 'cisco_nxos', 'cisco_xe', 'cisco_nexus']

    if platform_lower not in valid_cisco_platforms:
        raise ValueError(
            f"Invalid platform for Cisco sync: '{platform}'. "
            f"Valid Cisco platforms: {', '.join(valid_cisco_platforms)}"
        )

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

    # Use connection as context manager if it supports __enter__ and __exit__
    if hasattr(connection, '__enter__') and hasattr(connection, '__exit__'):
        with connection:
            if channel.lower() == 'scrapli':
                # Fetch version
                version_output = connection.send_command(commands.get('show_version', 'show version'))
                parsed_version = version_output.textfsm_parse_output()
                
                response_prompt = connection.get_prompt()
                if response_prompt:
                    info['hostname'] = response_prompt.replace("#", "").replace(">", "").strip()

                if parsed_version:
                    if platform_lower in ['cisco_ios', 'cisco_iosxe']:
                        info['version'] = parsed_version[0].get('version', '')
                        info['current_version'] = info['version']

                        if isinstance(parsed_version[0].get('serial'), list):
                            info['serial'] = parsed_version[0].get('serial')[0]
                        else:
                            info['serial'] = parsed_version[0].get('serial', '')
                        
                        info['serial_number'] = info['serial']

                        if not info['hostname']:
                            info['hostname'] = parsed_version[0].get('hostname', '')

                        if isinstance(parsed_version[0].get('hardware'), list):
                            info['model'] = parsed_version[0].get('hardware')[0]
                        else:
                            info['model'] = parsed_version[0].get('hardware', '')
                        
                        info['platform'] = platform_lower
                        info['uptime'] = parsed_version[0].get('uptime', '')
                        info['boot_method'] = parsed_version[0].get('running_image', '')
                        info['config_register'] = parsed_version[0].get('config_register', '')
                    
                    elif platform_lower == 'cisco_nxos':
                        # not yet implemented
                        pass

    else:
        # Fallback: just use the connection without context manager
        # Fetch version
        version_output = connection.send_command(commands.get('show_version', 'show version'))
        info['version'] = version_output
        info['current_version'] = info['version']

    return info
