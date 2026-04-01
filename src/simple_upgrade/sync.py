"""
Sync module - Fetches device information using platform-specific commands.

This module determines the correct commands to execute based on the platform
value from the centralized PLATFORM_MAPPINGS.
"""

import re

from typing import Dict, Any, Optional

from .constants import PLATFORM_MAPPINGS, get_platform_for_library
from .connection_manager import ConnectionManager, ConnectionError


# Command mapping by platform family
DEVICE_COMMANDS = {
    'cisco_ios': {
        'version': 'show version',
        'inventory': 'show inventory',
        'license': 'show license info',
        'hardware': 'show hardware info',
    },
    'cisco_iosxe': {
        'version': 'show version',
        'inventory': 'show inventory',
        'license': 'show license info',
        'hardware': 'show hardware info',
    },
    'cisco_nxos': {
        'version': 'show version',
        'inventory': 'show inventory',
        'license': 'show license',
        'hardware': 'show hardware',
    },
    'juniper_junos': {
        'version': 'show version',
        'inventory': 'show chassis hardware',
        'license': 'show system license',
        'hardware': 'show system hardware',
    },
    'arista_eos': {
        'version': 'show version',
        'inventory': 'show inventory',
        'license': 'show license',
        'hardware': 'show hardware',
    },
    'paloalto_panos': {
        'version': 'show system info',
        'inventory': 'show hardware',
        'license': 'show license',
        'hardware': 'show hardware',
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

        # Step 1: Get connection and platform
        cm = ConnectionManager(
            host="192.168.1.1",
            username="admin",
            password="password",
            device_type="cisco_xe"
        )
        conn = cm.get_connection(channel='scrapli')

        # Step 2: Get platform from connection manager
        platform = cm.get_platform(channel='scrapli')
        print(f"Using platform: {platform}")

        # Step 3: Use platform to fetch device info
        sync = SyncManager(connection_manager=cm, platform=platform)
        device_info = sync.fetch_info()
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

        # Device info storage
        self.info: Dict[str, Any] = {
            'manufacturer': None,
            'model': None,
            'version': None,
            'current_version': None,
            'hostname': None,
            'serial': None,
            'serial_number': None,
            'platform': None,
            'uptime': None,
            'boot_method': None,
            'boot_mode': None,
            'ios_image': None,
            'config_register': None,
            'flash_size': None,
            'memory_size': None,
        }

        # Determine platform - use provided value or get from connection manager
        if platform:
            self.platform = platform.lower().replace('-', '_')
        elif connection_manager and connection_manager._active_channel:
            self.platform = connection_manager.get_platform(connection_manager._active_channel)
        elif connection_manager and connection_manager.device_type:
            self.platform = get_platform_for_library(connection_manager.device_type, 'scrapli')

    def _normalize_output(self, output: str) -> str:
        """Clean up command output."""
        if isinstance(output, list):
            return '\n'.join(output)
        return str(output)

    def fetch_version(self) -> str:
        """
        Fetch the software version from the device.

        Returns:
            Software version string
        """
        commands = get_device_commands(self.platform)
        output = self.cm.send_command(commands['version'])
        return self._parse_version(output)

    def _parse_version(self, output: str) -> str:
        """
        Parse the software version from show version output.

        Handles different vendor formats.
        """
        output = self._normalize_output(output)

        # Cisco IOS-XE format: Version 17.9.4
        match = self._search_pattern(
            output,
            [
                r'Version\s+(\S+)',
                r'Version\s+(\S+)\s+\([^)]+\)',
                r'IOS-XE\s+Version\s+(\S+)',
                r'IOS\s+Version\s+(\S+)',
            ]
        )
        if match:
            return match

        # Juniper Junos format
        match = self._search_pattern(
            output,
            [
                r'Current\s+version:\s+(\S+)',
                r'Kernel\s+version:\s+(\S+)',
            ]
        )
        if match:
            return match

        # Arista EOS format
        match = self._search_pattern(
            output,
            [
                r'Software image version:\s+(\S+)',
                r'Cisco IOS Software,.*Version\s+(\S+)',
            ]
        )
        if match:
            return match

        return 'Unknown'

    def _search_pattern(self, text: str, patterns: list) -> str:
        """Search text for patterns and return first match."""
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return ''

    def fetch_inventory(self) -> Dict[str, str]:
        """
        Fetch device inventory information.

        Returns:
            Dictionary with inventory details
        """
        commands = get_device_commands(self.platform)
        output = self.cm.send_command(commands['inventory'])
        return self._parse_inventory(output)

    def _parse_inventory(self, output: str) -> Dict[str, str]:
        """Parse inventory output."""
        output = self._normalize_output(output)
        inventory = {}

        # Model/PID
        patterns = {
            'model': [
                r'PID:\s*(\S+)',
                r'Platform:\s*(\S+)',
                r'Catalyst\s+(\d+)',
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

    def fetch_hostname(self) -> str:
        """Fetch the device hostname."""
        commands = get_device_commands(self.platform)
        output = self.cm.send_command(commands['version'])
        output = self._normalize_output(output)

        match = re.search(r'hostname\s+(\S+)', output)
        if match:
            return match.group(1)
        return 'Unknown'

    def fetch_manufacturer(self) -> str:
        """
        Determine manufacturer from platform or output.

        Returns:
            Manufacturer string
        """
        # Use platform-based detection
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

    def fetch_info(self) -> Dict[str, Any]:
        """
        Fetch all device information.

        Returns:
            Complete device information dictionary
        """
        # Get all commands for this platform
        commands = get_device_commands(self.platform)

        # Fetch version
        version_output = self.cm.send_command(commands['version'])
        self.info['version'] = self._parse_version(version_output)

        # Fetch hostname
        self.info['hostname'] = self.fetch_hostname()

        # Fetch manufacturer
        self.info['manufacturer'] = self.fetch_manufacturer()

        # Fetch inventory
        inventory = self.fetch_inventory()
        self.info['model'] = inventory.get('model', '')
        self.info['serial_number'] = inventory.get('serial_number', '')

        # Store raw platform
        self.info['platform'] = self.platform

        # Fetch additional info if available
        try:
            uptime_output = self.cm.send_command("show version")
            uptime_output = self._normalize_output(uptime_output)

            # Parse uptime
            uptime_patterns = [
                r'uptime is\s+([\d\w\s,]+?)(?:,|\s+since|$)',
                r'uptime:\s+([\d\w\s,]+?)(?:,|\s+since|$)',
            ]
            for pattern in uptime_patterns:
                match = re.search(pattern, uptime_output, re.IGNORECASE)
                if match:
                    self.info['uptime'] = match.group(1).strip()
                    break
        except Exception:
            pass

        # Fetch boot method and boot mode
        self._fetch_boot_info(version_output)

        # Store current version
        self.info['current_version'] = self.info['version']

        return self.info

    def _fetch_boot_info(self, version_output: str):
        """
        Fetch boot method and boot mode from device.

        Args:
            version_output: Output from 'show version' command
        """
        version_output = self._normalize_output(version_output)

        # Parse boot method
        boot_patterns = [
            r'config register is\s+(\S+)',
            r'configuration register is\s+(\S+)',
            r'Last reload reason:\s*(.+?)(?:\n|$)',
        ]

        for pattern in boot_patterns:
            match = re.search(pattern, version_output, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if '0x' in value.lower():
                    self.info['config_register'] = value
                else:
                    self.info['boot_method'] = value
                break

        # Parse boot mode
        if 'nx-os' in version_output.lower() or 'nx-os' in self.platform:
            # NX-OS specific
            boot_match = re.search(r'Boot mode:\s*(\S+)', version_output, re.IGNORECASE)
            if boot_match:
                self.info['boot_mode'] = boot_match.group(1)
        else:
            # IOS/XE specific
            boot_match = re.search(r'image file is\s+(\S+)', version_output, re.IGNORECASE)
            if boot_match:
                self.info['boot_method'] = boot_match.group(1)

        # Try to get flash and memory size from inventory
        try:
            inventory_output = self.cm.send_command("show inventory")
            inventory_output = self._normalize_output(inventory_output)

            # Parse flash size
            flash_patterns = [
                r'PID:\s*\S+,\s*(\d+\s+\w+)?\s*bytes',
                r'flash\s+\(.*?\)\s+(\d+\s+\w+)?',
            ]
            for pattern in flash_patterns:
                match = re.search(pattern, inventory_output, re.IGNORECASE)
                if match:
                    self.info['flash_size'] = match.group(1).strip()
                    break

            # Parse memory size
            mem_patterns = [
                r'Processor\s+with\s+(\d+\s+\w+)\s+of\s+memory',
                r'System\s+memory\s+:\s*(\d+\s+\w+)',
            ]
            for pattern in mem_patterns:
                match = re.search(pattern, inventory_output, re.IGNORECASE)
                if match:
                    self.info['memory_size'] = match.group(1).strip()
                    break
        except Exception:
            pass


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
