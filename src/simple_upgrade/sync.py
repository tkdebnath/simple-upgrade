"""
Sync module - Fetches device information using platform-specific commands.

This module determines the correct commands to execute based on the platform
value from the centralized PLATFORM_MAPPINGS.
"""

from typing import Dict, Any

from .constants import DEVICE_COMMANDS


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
    """

    def __init__(
        self,
        connection_manager: Any,
        platform: str
    ):
        """
        Initialize the SyncManager.

        Args:
            connection_manager: Active ConnectionManager instance
            platform: Platform name (e.g., cisco_ios, cisco_iosxe)
        """
        self.cm = connection_manager
        self.platform = platform.lower().replace('-', '_')
        self.info: Dict[str, Any] = {}

        # Note: channel validation is now done in _send_command() before each command
        pass

    def _validate_channel(self) -> None:
        """
        Validate the connection channel and platform.

        Raises:
            ValueError: If channel is invalid or platform doesn't match
        """
        # Check if connection manager has an active channel
        active_channel = self.cm.get_active_channel()
        if not active_channel:
            raise ValueError(
                "No active channel found. Call get_connection() on the connection manager "
                "before initializing SyncManager."
            )

        # Validate channel is scrapli
        if active_channel != 'scrapli':
            raise ValueError(
                f"Invalid channel: {active_channel}. "
                f"Supported channel: scrapli"
            )

        # Validate platform matches
        channel_platform = self.cm.get_active_channel_platform()
        if channel_platform:
            # Normalize platforms for comparison
            norm_sync_platform = self.platform.replace('-', '_')
            norm_channel_platform = channel_platform.lower().replace('-', '_')

            if norm_sync_platform != norm_channel_platform:
                raise ValueError(
                    f"Platform mismatch: SyncManager platform='{self.platform}', "
                    f"channel platform='{channel_platform}'"
                )

    def _send_command(self, command: str) -> str:
        """
        Send command to scrapli connection.

        Validates channel and platform before executing command.
        """
        # Validate channel
        active_channel = self.cm.get_active_channel()
        if not active_channel:
            raise ValueError(
                "No active channel found. Call get_connection() on the connection manager "
                "before executing commands."
            )

        if active_channel != 'scrapli':
            raise ValueError(
                f"Invalid channel: {active_channel}. "
                f"Supported channel: scrapli"
            )

        # Validate platform
        channel_platform = self.cm.get_active_channel_platform()
        if channel_platform:
            # Normalize platforms for comparison
            norm_sync_platform = self.platform.replace('-', '_')
            norm_channel_platform = channel_platform.lower().replace('-', '_')

            if norm_sync_platform != norm_channel_platform:
                raise ValueError(
                    f"Platform mismatch: SyncManager platform='{self.platform}', "
                    f"channel platform='{channel_platform}'"
                )

        result = self.cm._scrapli_conn.send_command(command)
        return str(result.result)

    def fetch_info(self) -> Dict[str, Any]:
        """
        Fetch all device information using manufacturer-specific sync.

        Returns:
            Complete device information dictionary
        """
        from .manufacturers import execute_stage

        commands = get_device_commands(self.platform)

        # Get connection from connection manager
        conn = self.cm._scrapli_conn

        # Use manufacturer-specific sync (channel is auto-detected from connection)
        device_info = execute_stage('cisco', 'sync', conn, self.platform, commands)

        return device_info


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
        platform: Platform name (e.g., cisco_ios, cisco_iosxe)
        port: SSH port

    Returns:
        Dictionary with device information
    """
    from .connection_manager import ConnectionManager

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
