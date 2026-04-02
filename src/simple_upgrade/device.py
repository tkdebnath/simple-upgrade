"""
Device class for managing network device connections and information gathering.
Uses scrapli for SSH connections.
"""

import re
from typing import Optional, Dict, Any, List


class DeviceConnectionError(Exception):
    """Raised when device connection fails."""
    pass


class Device:
    """
    Manages connection to a network device and gathers device information.

    Uses scrapli library for connection management.
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 22,
        timeout: int = 30,
        enable_mode: bool = False,
        enable_password: Optional[str] = None,
        device_type: Optional[str] = None,
        connection_mode: str = "normal",  # normal, mock, dry_run
        scrapli_args: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize device connection parameters.

        Args:
            host: IP address or hostname of the device
            username: SSH username
            password: SSH password
            port: SSH port (default: 22)
            timeout: Connection timeout in seconds
            enable_mode: Whether to enter enable mode
            enable_password: Enable password if required
            device_type: Device type/platform (e.g., cisco_ios, cisco_xe)
                        Required for scrapli to determine the correct driver.
            scrapli_args: Additional arguments to pass to scrapli Scrapli() constructor
            **kwargs: Additional keyword arguments (e.g., auth_passphrase)
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.timeout = timeout
        self.enable_mode = enable_mode
        self.enable_password = enable_password
        self.device_type = device_type
        self.connection_mode = connection_mode
        self.scrapli_args = scrapli_args or {}
        self.device_kwargs = kwargs

        # Device information - populated after connection
        self.manufacturer: str = ""
        self.model: str = ""
        self.version: str = ""
        self.hostname: str = ""
        self.serial_number: str = ""
        self.platform: str = ""
        self.tacacs_source_interface: str = ""

        # Connection state
        self._connection = None
        self._connected: bool = False

    def connect(self) -> bool:
        """
        Establish connection to the device using scrapli.

        Returns:
            True if connection successful, False otherwise
        """
        # Handle mock mode
        if self.connection_mode == 'mock':
            from .mocks import MockConnection
            self._connection = MockConnection(
                host=self.host,
                username=self.username,
                password=self.password,
                device_type=self.device_type,
                port=self.port,
                platform=self.device_type
            )
            self._connected = True
            return True

        # Handle dry-run mode
        if self.connection_mode == 'dry_run':
            from .mocks import DryRunConnection
            # Create real connection for show commands
            from scrapli import Scrapli
            from scrapli.exceptions import ScrapliException

            if not self.device_type:
                raise DeviceConnectionError(
                    "device_type is required. Please provide the device type "
                    "(e.g., 'cisco_ios', 'cisco_xe', 'cisco_nxos')."
                )

            # Build connection args
            conn_args = {
                "host": self.host,
                "port": self.port,
                "auth_username": self.username,
                "auth_password": self.password,
                "auth_strict_key": False,
                "timeout_socket": self.timeout,
                "platform": self.device_type,
            }

            # Apply custom scrapli args (e.g., for older devices with different SSH algorithms)
            conn_args.update(self.scrapli_args)

            real_conn = Scrapli(**conn_args)

            self._connection = DryRunConnection(real_conn, self.device_type)
            self._connected = True
            return True

        # Normal mode - actual SSH connection
        try:
            from scrapli import Scrapli
            from scrapli.exceptions import ScrapliException

            # Validate device_type is provided
            if not self.device_type:
                raise DeviceConnectionError(
                    "device_type is required. Please provide the device type "
                    "(e.g., 'cisco_ios', 'cisco_xe', 'cisco_nxos')."
                )

            # Build connection arguments
            conn_args = {
                "host": self.host,
                "port": self.port,
                "auth_username": self.username,
                "auth_password": self.password,
                "auth_strict_key": False,
                "timeout_socket": self.timeout,
                "platform": self.device_type,
            }

            # Apply custom scrapli args (e.g., for older devices with different SSH algorithms)
            if self.scrapli_args:
                conn_args.update(self.scrapli_args)

            self._connection = Scrapli(**conn_args)
            self._connection.open()
            self._connected = True

            return True

        except ScrapliException as e:
            raise DeviceConnectionError(f"Failed to connect to {self.host}: {e}")
        except Exception as e:
            raise DeviceConnectionError(f"Failed to connect to {self.host}: {e}")

    def _enter_enable_mode(self):
        """Enter privileged EXEC mode (enable mode)."""
        if not self._connection:
            raise DeviceConnectionError("Not connected to device")

        try:
            self._connection.send_command("enable")
            self._connection.send_command(self.enable_password)
        except Exception as e:
            # Try alternative approach
            pass

    def send_command(self, command: str) -> str:
        """
        Send a command to the device.

        Args:
            command: The command to send

        Returns:
            Command output as string
        """
        if not self._connection:
            raise DeviceConnectionError("Not connected to device")

        # If not connected but connection exists, try to open it
        # This handles context manager usage
        if not self._connected:
            try:
                self._connection.open()
                self._connected = True
            except Exception as e:
                raise DeviceConnectionError(f"Failed to open connection: {e}")

        try:
            result = self._connection.send_command(command)
            return str(result.result)
        except Exception as e:
            raise DeviceConnectionError(f"Command failed: {e}")

    def send_config(self, commands: List[str]) -> str:
        """
        Send configuration commands to the device.

        Args:
            commands: List of configuration commands

        Returns:
            Output from configuration commands
        """
        if not self._connected or not self._connection:
            raise DeviceConnectionError("Not connected to device")

        try:
            result = self._connection.send_configs(commands)
            return str(result.result)
        except Exception as e:
            raise DeviceConnectionError(f"Config failed: {e}")

    def disconnect(self):
        """Close the connection."""
        if self._connection:
            try:
                self._connection.close()
            except Exception:
                pass
            self._connected = False
            self._connection = None

    def __enter__(self):
        """Enter context manager - open the connection."""
        # If no connection, create one first
        if not self._connection:
            self.connect()
        # If connection exists but not connected, open it
        if self._connection and not self._connected:
            self._connection.open()
            self._connected = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager - close the connection."""
        self.disconnect()
        return False

    def gather_info(self) -> Dict[str, Any]:
        """
        Gather device information from show commands.

        Returns:
            Dictionary containing device information
        """
        if not self._connected:
            raise DeviceConnectionError("Not connected to device")

        # Get basic show commands
        commands = {
            'hostname': 'show run | include hostname',
            'version': 'show version',
            'inventory': 'show inventory',
            'tacacs': 'show run | include tacacs',
        }

        results = {}
        for name, cmd in commands.items():
            try:
                output = self.send_command(cmd)
                results[name] = output
            except Exception as e:
                results[name] = ""

        # Parse the information
        self._parse_device_info(results)

        return {
            'manufacturer': self.manufacturer,
            'model': self.model,
            'version': self.version,
            'hostname': self.hostname,
            'serial_number': self.serial_number,
            'platform': self.platform,
            'tacacs_source_interface': self.tacacs_source_interface,
        }

    def _parse_device_info(self, results: Dict[str, str]):
        """
        Parse device information from command outputs.
        """
        version_output = results.get('version', '')
        inventory_output = results.get('inventory', '')

        # Parse manufacturer from version output
        if 'Cisco' in version_output or 'Cisco Systems' in version_output:
            self.manufacturer = 'Cisco'
        elif 'Juniper' in version_output:
            self.manufacturer = 'Juniper'
        elif 'Arista' in version_output:
            self.manufacturer = 'Arista'
        elif 'Palo Alto' in version_output:
            self.manufacturer = 'Palo Alto Networks'
        else:
            self.manufacturer = 'Unknown'

        # Parse model from version output
        # First try to match the model name after "Catalyst" or other model indicators
        model_patterns = [
            r'Catalyst\s+(\S+)',           # For Catalyst switches like 9300, 9400
            r'Platform:\s*(\S+)',          # Platform line
            r'Product\s+Name:\s*(\S+)',    # Some devices have Product Name
            r'(\S+)\s+Software',           # For IOSv, vios_l2, etc.
        ]

        for pattern in model_patterns:
            match = re.search(pattern, version_output)
            if match:
                self.model = match.group(1)
                break

        # Fallback: try to find model in inventory
        if not self.model and inventory_output:
            model_patterns_inv = [
                r'PID:\s*(\S+)',
            ]
            for pattern in model_patterns_inv:
                match = re.search(pattern, inventory_output)
                if match:
                    self.model = match.group(1)
                    break


        # Parse version
        version_patterns = [
            r'Version\s+(\S+)',
            r'Software\s+\(SUS\)\s+Version\s+(\S+)',
        ]

        for pattern in version_patterns:
            match = re.search(pattern, version_output)
            if match:
                self.version = match.group(1)
                break

        # Parse hostname
        hostname_match = re.search(r'hostname\s+(\S+)', results.get('hostname', ''))
        if hostname_match:
            self.hostname = hostname_match.group(1)

        # Parse serial number
        serial_patterns = [
            r'System serial number:\s*(\S+)',
            r'Serial Number:\s*(\S+)',
        ]

        for pattern in serial_patterns:
            match = re.search(pattern, inventory_output)
            if match:
                self.serial_number = match.group(1)
                break

        # Parse platform
        platform_match = re.search(r'Processor type is\s+(\S+)', version_output)
        if platform_match:
            self.platform = platform_match.group(1)

        # Parse tacacs source interface
        tacacs_output = results.get('tacacs', '')
        source_interface_match = re.search(r'tacacs\s+source-interface\s+(\S+)', tacacs_output)
        if source_interface_match:
            self.tacacs_source_interface = source_interface_match.group(1)

    def check_connection(self) -> bool:
        """Check if device is still reachable."""
        if not self._connected:
            return False

        try:
            output = self.send_command("show version")
            return "Cisco" in output or "Juniper" in output or "Arista" in output
        except Exception:
            return False
