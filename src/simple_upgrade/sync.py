"""
Sync module - Fetches device information using platform-specific commands.

This module determines the correct commands to execute based on the platform
value from the centralized PLATFORM_MAPPINGS.
"""

from typing import Dict, Any, Optional

from .constants import PLATFORM_MAPPINGS, get_platform_for_library
from .connection_manager import ConnectionManager, ConnectionError


# Command mapping by platform family - basic commands for parsing
DEVICE_COMMANDS = {
    'cisco_ios': {
        'version': 'show version',
        'inventory': 'show inventory',
    },
    'cisco_iosxe': {
        'version': 'show version',
        'inventory': 'show inventory',
    },
    'cisco_nxos': {
        'version': 'show version',
        'inventory': 'show inventory',
    },
    'juniper_junos': {
        'version': 'show version',
        'inventory': 'show chassis hardware',
    },
    'arista_eos': {
        'version': 'show version',
        'inventory': 'show inventory',
    },
    'paloalto_panos': {
        'version': 'show system info',
        'inventory': 'show hardware',
    },
}


def get_device_commands(platform: str) -> Dict[str, str]:
    """
    Get the command set for a specific platform.

    Args:
        platform: The platform name (e.g., cisco_ios, cisco_iosxe, juniper_junos)

    Returns:
        Dictionary of command names to command strings
    """
    # Normalize platform name
    platform = platform.lower().replace('-', '_')

    # Try direct lookup
    if platform in DEVICE_COMMANDS:
        return DEVICE_COMMANDS[platform]

    # Try variations
    variations = [
        platform,
        f'cisco_{platform}',
        f'cisco-{platform}',
        platform.replace('_', '-'),
        platform.replace('_', ''),
    ]

    for variant in variations:
        if variant in DEVICE_COMMANDS:
            return DEVICE_COMMANDS[variant]

    # Return default Cisco commands
    return DEVICE_COMMANDS['cisco_ios']


class SyncManager:
    """
    Manages device synchronization - fetching device information.

    Usage:
        from simple_upgrade import ConnectionManager, SyncManager

        cm = ConnectionManager(
            host="192.168.1.1",
            username="admin",
            password="password",
            device_type="cisco_xe"
        )
        conn = cm.get_connection(channel='scrapli')
        platform = cm.get_platform(channel='scrapli')

        sync = SyncManager(connection_manager=cm, platform=platform)
        info = sync.fetch_info()
    """

    def __init__(
        self,
        connection_manager: ConnectionManager,
        platform: Optional[str] = None
    ):
        """
        Initialize the SyncManager.

        Args:
            connection_manager: Active ConnectionManager instance
            platform: Platform name (e.g., cisco_ios, cisco_iosxe, juniper_junos)
                     If not provided, uses the active channel's platform.
        """
        self.cm = connection_manager
        self.platform = ''

        # Device info storage - populate with values for your textfsm parsing
        self.info: Dict[str, Any] = {
            'hostname': None,
            'version': None,
            'current_version': None,
            'model': None,
            'serial': None,
            'serial_number': None,
            'manufacturer': None,
            'platform': None,
            'uptime': None,
            'boot_method': None,
            'boot_mode': None,
            'ios_image': None,
            'config_register': None,
            'flash_size': None,
            'memory_size': None,
        }

        # Determine platform
        if platform:
            self.platform = platform.lower().replace('-', '_')
        elif connection_manager and connection_manager._active_channel:
            self.platform = connection_manager.get_platform(connection_manager._active_channel)
        elif connection_manager and connection_manager.device_type:
            self.platform = get_platform_for_library(connection_manager.device_type, 'scrapli')

    def _send_command(self, command: str) -> str:
        """
        Send command based on the active channel type.
        """
        conn = self.cm.get_active_channel()
        output = ""

        if conn == 'scrapli':
            result = self.cm._scrapli_conn.send_command(command)
            output = str(result.result)
        elif conn == 'netmiko':
            output = self.cm._netmiko_conn.send_command(command)
        elif conn == 'unicon':
            output = str(self.cm._unicon_conn.execute(command))

        return output

    def fetch_info(self) -> Dict[str, Any]:
        """
        Fetch all device information.

        Returns:
            Complete device information dictionary
        """
        commands = get_device_commands(self.platform)

        # Fetch version output
        version_output = self._send_command(commands['version'])
        self.info['version'] = version_output

        # Fetch inventory output
        inventory_output = self._send_command(commands['inventory'])
        self.info['inventory'] = inventory_output

        # Parse hostname from version output
        self.info['hostname'] = self._parse_hostname(version_output)

        # Parse manufacturer from platform
        self.info['manufacturer'] = self._parse_manufacturer()

        # Store raw platform
        self.info['platform'] = self.platform

        # Store current version
        self.info['current_version'] = self.info['version']

        return self.info

    def _parse_hostname(self, output: str) -> str:
        """Parse hostname from version output."""
        import re
        match = re.search(r'hostname\s+(\S+)', output)
        if match:
            return match.group(1)
        return 'Unknown'

    def _parse_manufacturer(self) -> str:
        """Determine manufacturer from platform."""
        platform_lower = self.platform.lower()

        if 'cisco' in platform_lower:
            return 'Cisco'
        elif 'juniper' in platform_lower or 'junos' in platform_lower:
            return 'Juniper'
        elif 'arista' in platform_lower or 'eos' in platform_lower:
            return 'Arista'
        elif 'paloalto' in platform_lower or 'panos' in platform_lower:
            return 'Palo Alto Networks'
        else:
            return 'Unknown'


def sync_device(
    host: str,
    username: str,
    password: str,
    platform: str,
    port: int = 22,
) -> Dict[str, Any]:
    """
    Standalone function to sync device information.

    Args:
        host: Device IP or hostname
        username: SSH username
        password: SSH password
        platform: Platform name (e.g., cisco_ios, cisco_iosxe, juniper_junos)
        port: SSH port

    Returns:
        Dictionary with device information
    """
    cm = ConnectionManager(
        host=host,
        username=username,
        password=password,
        device_type=None,
        port=port,
    )

    conn = cm.get_connection('scrapli')
    sync_mgr = SyncManager(connection_manager=cm, platform=platform)
    device_info = sync_mgr.fetch_info()
    cm.disconnect()

    return device_info
