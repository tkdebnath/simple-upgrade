"""
Connection Manager - Unified interface for Scrapli and Unicon.
"""

from typing import Optional, Dict, Any, List
import re
from .constants import PLATFORM_MAPPINGS


class ConnectionError(Exception):
    """Raised when connection fails."""
    pass


class ConnectionManager:
    """
    Unified manager for network device connections.
    Supports Scrapli (軽量) and Unicon (高機能) drivers.
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        device_type: Optional[str] = None,
        port: int = 22,
        timeout: int = 30,
        connection_mode: str = "normal",  # normal, mock, dry_run
        **kwargs
    ):
        self.host = host
        self.username = username
        self.password = password
        self.device_type = device_type
        self.port = port
        self.timeout = timeout
        self.connection_mode = connection_mode
        self.kwargs = kwargs

        self._scrapli = None
        self._unicon = None

    def get_connection(self, library: str = "scrapli") -> Any:
        """Get or create a connection for the specified library."""
        library = library.lower()
        
        if self.connection_mode == "mock":
            return self._get_mock_connection(library)

        if library == "scrapli":
            if not self._scrapli:
                from scrapli import Scrapli
                params = self._get_params("scrapli")
                self._scrapli = Scrapli(**params)
                self._scrapli.open()
            return self._scrapli

        if library == "unicon":
            if not self._unicon:
                from unicon import Connection
                params = self._get_params("unicon")
                self._unicon = Connection(**params)
                self._unicon.connect()
            return self._unicon

        raise ConnectionError(f"Unsupported library: {library}")

    def _get_params(self, library: str) -> Dict[str, Any]:
        """Generate library-specific parameters."""
        platform = self._get_mapped_platform(library)
        
        if library == "scrapli":
            return {
                "host": self.host,
                "port": self.port,
                "auth_username": self.username,
                "auth_password": self.password,
                "platform": platform,
                "auth_strict_key": False,
                "timeout_socket": self.timeout,
            }
        
        if library == "unicon":
            return {
                "os": platform,
                "hostname": self.host,
                "credentials": {
                    "default": {"username": self.username, "password": self.password}
                },
                "start": [f"ssh {self.username}@{self.host}"],
                "timeout": self.timeout
            }
        return {}

    def _get_mapped_platform(self, library: str) -> str:
        """Map generic device_type to library-specific platform."""
        dtype = (self.device_type or "cisco_iosxe").lower().replace("-", "_")
        
        # Direct lookup in constants
        if dtype in PLATFORM_MAPPINGS:
            return PLATFORM_MAPPINGS[dtype].get(library, dtype)
            
        # Common fallbacks
        if "iosxe" in dtype or "cisco_xe" in dtype:
            return "iosxe" if library == "unicon" else "cisco_iosxe"
        
        return dtype

    def _get_mock_connection(self, library: str) -> Any:
        """Return a mock connection object."""
        from .mocks import MockConnection
        return MockConnection(
            host=self.host,
            username=self.username,
            password=self.password,
            platform=self._get_mapped_platform(library)
        )

    def disconnect(self):
        """Close all active connections."""
        if self._scrapli:
            try: self._scrapli.close()
            except: pass
            self._scrapli = None
            
        if self._unicon:
            try: self._unicon.disconnect()
            except: pass
            self._unicon = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.disconnect()
