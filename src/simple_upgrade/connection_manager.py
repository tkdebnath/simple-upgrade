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
        enable_password: Optional[str] = None,  # privilege-exec / enable secret
        **kwargs
    ):
        self.host = host
        self.username = username
        self.password = password
        self.enable_password = enable_password
        self.device_type = device_type
        self.port = port
        self.timeout = timeout
        self.connection_mode = connection_mode
        self.kwargs = kwargs

        self._scrapli = None
        self._unicon = None
        self._mock_library_map = {}

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
            params: Dict[str, Any] = {
                "host": self.host,
                "port": self.port,
                "auth_username": self.username,
                "auth_password": self.password,
                "platform": platform,
                "transport": "ssh2",
                "auth_strict_key": False,
                "timeout_socket": self.timeout,
            }
            # Scrapli uses auth_secondary for the enable / privilege-exec password
            if self.enable_password:
                params["auth_secondary"] = self.enable_password
            return params
        
        if library == "unicon":
            credentials: Dict[str, Any] = {
                "default": {"username": self.username, "password": self.password}
            }
            # Unicon uses a separate 'enable' credential entry
            if self.enable_password:
                credentials["enable"] = {"password": self.enable_password}
            return {
                "os": platform,
                "hostname": self.host,
                "credentials": credentials,
                "start": [f"ssh {self.username}@{self.host}"],
                "learn_hostname": True,
                "goto_enable": False,
                "init_commands": [],
                "timeout": self.timeout,
                # Legacy SSH compatibility: allow older key exchange algorithms
                # and ciphers required by many Cisco IOS / IOS-XE devices.
                "ssh_options": (
                    "-o KexAlgorithms=+diffie-hellman-group-exchange-sha1,"
                    "diffie-hellman-group14-sha1,"
                    "diffie-hellman-group1-sha1 "
                    "-o HostKeyAlgorithms=+ssh-rsa "
                    "-o Ciphers=+aes128-cbc,3des-cbc,aes192-cbc,aes256-cbc "
                    "-o StrictHostKeyChecking=no"
                ),
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
        if library not in self._mock_library_map:
            conn = MockConnection(
                host=self.host,
                username=self.username,
                password=self.password,
                platform=self._get_mapped_platform(library)
            )
            conn.open()
            self._mock_library_map[library] = conn
        return self._mock_library_map[library]

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
