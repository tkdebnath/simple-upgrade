"""
Connection Manager - Centralized connection object management.

Provides a unified interface to create connection objects for scrapli and unicon.
"""

from typing import Optional, Dict, Any

from .constants import PLATFORM_MAPPINGS


class ConnectionError(Exception):
    """Raised when connection fails."""
    pass


def _normalize_platform_name(platform: str) -> str:
    """Normalize platform name to standard format."""
    platform = platform.lower().replace('-', '_')
    return platform


class ConnectionManager:
    """
    Manages network device connections using scrapli.

    Usage:
        from simple_upgrade import ConnectionManager

        conn = ConnectionManager(
            host="192.168.1.1",
            username="admin",
            password="password",
            device_type="cisco_xe",
            enable_password="enable123"
        )

        # Get scrapli connection
        sc = conn.get_connection(channel='scrapli')
        output = sc.send_command("show version")

        conn.disconnect()
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        device_type: Optional[str] = None,
        port: int = 22,
        timeout: int = 30,
        connection_timeout: int = 30,
        enable_mode: bool = False,
        enable_password: Optional[str] = None,
        auth_strict_key: bool = False,
        transport: str = "ssh",
        connection_mode: str = "normal",  # normal, mock, dry_run
        scrapli_args: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize the ConnectionManager.

        Args:
            host: IP address or hostname of the device
            username: SSH username
            password: SSH password
            device_type: Device type/platform (e.g., cisco_ios, cisco_xe)
            port: SSH port (default: 22)
            timeout: Command timeout in seconds (default: 30)
            connection_timeout: Connection timeout in seconds (default: 30)
            enable_mode: Whether to enter enable mode (default: False)
            enable_password: Enable password if required
            auth_strict_key: Strict SSH key checking (default: False)
            transport: Transport type (default: "ssh")
            connection_mode: Connection mode - 'normal', 'mock', or 'dry_run'
            scrapli_args: Additional arguments to pass to scrapli Scrapli() constructor
            **kwargs: Additional keyword arguments
        """
        self.host = host
        self.username = username
        self.password = password
        self.device_type = device_type
        self.port = port
        self.timeout = timeout
        self.connection_timeout = connection_timeout
        self.enable_mode = enable_mode
        self.enable_password = enable_password
        self.auth_strict_key = auth_strict_key
        self.transport = transport
        self.connection_mode = connection_mode
        self.scrapli_args = scrapli_args or {}
        self.device_kwargs = kwargs

        # Connection objects
        self._scrapli_conn = None
        self._unicon_conn = None
        self._active_channel = None
        self.channel = None  # Channel name for external use
        self.channel_platform = None  # Platform for the active channel

    def _get_library_platform(self, library: str) -> str:
        """
        Get the platform name for a specific library using the centralized mapping.

        Args:
            library: Library name (scrapli)

        Returns:
            Platform name specific to the library

        Raises:
            ConnectionError: If no compatible platform mapping is found
        """
        platform = _normalize_platform_name(self.device_type or 'default')

        # Try direct lookup
        if platform in PLATFORM_MAPPINGS:
            mapping = PLATFORM_MAPPINGS[platform].get(library)
            if mapping:
                return mapping

        # Try with cisco_ prefix variations
        variations = [
            platform,
            f'cisco_{platform}',
            f'cisco-{platform}',
            platform.replace('_', '-'),
            platform.replace('_', ''),
        ]

        for variant in variations:
            if variant in PLATFORM_MAPPINGS:
                mapping = PLATFORM_MAPPINGS[variant].get(library)
                if mapping:
                    return mapping

        # No compatible platform found
        raise ConnectionError(
            f"No compatible platform found for device_type '{self.device_type}' "
            f"with library '{library}'. "
            f"Supported platforms: {', '.join(PLATFORM_MAPPINGS.keys())}"
        )

    def get_connection(self, channel: str = "scrapli") -> Any:
        """
        Get a connection object for the specified library.

        Args:
            channel: The library to use - 'scrapli' or 'unicon'

        Returns:
            Connection object for the specified library

        Raises:
            ConnectionError: If connection fails or channel is invalid
        """
        channel = channel.lower()

        if channel == 'unicon':
            return self._get_unicon_connection()

        if channel != 'scrapli':
            raise ConnectionError(
                f"Invalid channel: {channel}. "
                f"Supported channels: scrapli, unicon"
            )

        # Return existing connection if already established
        if channel == 'scrapli' and self._scrapli_conn:
            return self._scrapli_conn

        # Create new connection
        try:
            self._scrapli_conn = self._get_scrapli_connection()
            self._active_channel = 'scrapli'
            self.channel = 'scrapli'
            self.channel_platform = self._get_library_platform('scrapli')
            return self._scrapli_conn

        except Exception as e:
            raise ConnectionError(f"Failed to connect to {self.host}: {e}")

    def _get_unicon_connection(self) -> Any:
        """
        Create and return a unicon connection object.

        Returns:
            Unicon Connection object
        """
        try:
            from unicon import Connection

            # Get platform for unicon
            unicon_platform = self._get_library_platform('unicon')

            conn = Connection(
                os=unicon_platform,
                hostname=self.host,
                learn_hostname=True,
                goto_enable=False,
                credentials={
                    'default': {
                        'username': self.username,
                        'password': self.password
                    },
                    'enable': {
                        'password': self.enable_password or ''
                    }
                },
                start=[f'ssh {self.username}@{self.host}'],
                init_commands=[],
                timeout=self.connection_timeout
            )
            conn.connect()

            self._unicon_conn = conn
            self._active_channel = 'unicon'
            self.channel = 'unicon'

            return conn

        except Exception as e:
            raise ConnectionError(f"Unicon connection failed: {e}")

    def get_platform(self, channel: Optional[str] = None) -> str:
        """
        Get the platform name for the active channel.

        Args:
            channel: The channel to get platform for. If None, uses active channel.

        Returns:
            Platform name for the specified library

        Raises:
            ConnectionError: If platform not found
        """
        if channel:
            channel = channel.lower()
            if channel in ['scrapli'] and self.channel_platform:
                return self.channel_platform

        # Use active channel
        if self._active_channel and self.channel_platform:
            return self.channel_platform

        raise ConnectionError(
            "No active channel. Call get_connection() first to establish a connection "
            "and get the platform value."
        )

    def get_connection_with_platform(self, channel: str = "scrapli") -> Dict[str, Any]:
        """
        Get a connection object and its corresponding platform.

        Args:
            channel: The library to use - 'scrapli'

        Returns:
            Dictionary with 'connection' and 'platform' keys

        Raises:
            ConnectionError: If connection fails or channel is invalid
        """
        conn = self.get_connection(channel)
        platform = self.get_platform(channel)
        return {
            'connection': conn,
            'platform': platform,
        }

    def _get_scrapli_connection(self):
        """
        Create and return a scrapli connection object.
        """
        try:
            from scrapli import Scrapli
            from scrapli.exceptions import ScrapliException

            # Validate device_type for scrapli
            if not self.device_type:
                raise ConnectionError(
                    "device_type is required for scrapli connections. "
                    "Please provide device_type (e.g., 'cisco_ios', 'cisco_xe')."
                )

            # Get platform from centralized mapping
            scrapli_platform = self._get_library_platform('scrapli')

            # Build base connection args
            conn_args = {
                "host": self.host,
                "port": self.port,
                "auth_username": self.username,
                "auth_password": self.password,
                "auth_strict_key": self.auth_strict_key,
                "timeout_socket": self.connection_timeout,
                "platform": scrapli_platform,
                "transport": "ssh2",
            }

            # enable password
            if self.enable_password:
                conn_args["auth_secondary"] = self.enable_password

            # Apply any additional scrapli arguments (e.g., for older devices)
            if self.scrapli_args:
                conn_args.update(self.scrapli_args)

            conn = Scrapli(**conn_args)

            return conn

        except ScrapliException as e:
            raise ConnectionError(f"Scrapli connection failed: {e}")
        except Exception as e:
            raise ConnectionError(f"Scrapli connection failed: {e}")

    def disconnect(self, channel: Optional[str] = None):
        """
        Disconnect from the device.

        Args:
            channel: If specified, disconnect only this channel.
                    If None, disconnect all channels.
        """
        if channel:
            channel = channel.lower()
            if channel == 'scrapli' and self._scrapli_conn:
                try:
                    self._scrapli_conn.close()
                except Exception:
                    pass
                self._scrapli_conn = None
            elif channel == 'unicon' and self._unicon_conn:
                try:
                    self._unicon_conn.disconnect()
                except Exception:
                    pass
                self._unicon_conn = None

        else:
            # Disconnect all channels
            if self._scrapli_conn:
                try:
                    self._scrapli_conn.close()
                except Exception:
                    pass
                self._scrapli_conn = None
            if self._unicon_conn:
                try:
                    self._unicon_conn.disconnect()
                except Exception:
                    pass
                self._unicon_conn = None

        self._active_channel = None
        self.channel = None

    def is_connected(self, channel: Optional[str] = None) -> bool:
        """
        Check if connected.

        Args:
            channel: If specified, check only this channel.
                    If None, check any active channel.

        Returns:
            True if connected, False otherwise
        """
        if channel:
            channel = channel.lower()
            if channel == 'scrapli':
                return self._scrapli_conn is not None
            elif channel == 'unicon':
                return self._unicon_conn is not None
            return False

        return self._active_channel is not None

    def get_active_channel(self) -> Optional[str]:
        """Return the currently active connection channel."""
        return self._active_channel

    def get_active_channel_platform(self) -> Optional[str]:
        """Return the platform for the currently active channel."""
        return self.channel_platform

    def get_channel_for_connection(self, conn: Any) -> Optional[str]:
        """
        Get the channel name for a connection object.

        Args:
            conn: Connection object (scrapli)

        Returns:
            Channel name ('scrapli') or None if not found
        """
        if conn is None:
            return None

        # Check if it's the scrapli connection
        if conn is self._scrapli_conn:
            return 'scrapli'

        # Check type for externally created connections
        try:
            module = getattr(conn, '__module__', '')
            if 'scrapli' in module:
                return 'scrapli'
        except Exception:
            pass

        return None
