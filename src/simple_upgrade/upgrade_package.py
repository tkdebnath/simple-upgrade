"""
UpgradePackage - Central object for managing network device firmware upgrades.

This module provides a single package object that orchestrates the entire upgrade
workflow while maintaining shared state. Each stage updates the package's attributes
with results and device information, allowing decisions on whether to continue.

Usage:
    from simple_upgrade import UpgradePackage

    # Create upgrade package
    upgrade = UpgradePackage(
        host="192.168.1.1",
        username="admin",
        password="password",
        golden_image={
            "version": "17.9.4",
            "image_name": "flash:c9300-universalk9.17.9.4.SPA.bin"
        },
        file_server={
            "ip": "10.0.0.10",
            "protocol": "http",
            "base_path": "/tftpboot"
        }
    )

    # Execute stages in order - each updates the package state
    upgrade.sync()           # Updates device_info
    upgrade.readiness()      # Updates readiness_result
    upgrade.pre_check()      # Updates pre_check_result
    upgrade.distribute()     # Updates distribute_result
    upgrade.activate()       # Updates activate_result
    upgrade.wait()           # Updates wait_result
    upgrade.ping()           # Updates ping_result
    upgrade.post_check()     # Updates post_check_result
    upgrade.verification()   # Updates verification_result

    # Check overall status
    if upgrade.success:
        print("Upgrade successful")
    else:
        print(f"Upgrade failed at stage: {upgrade.failed_stage}")
"""

from typing import Dict, Any, Optional, List
from .device import Device, DeviceConnectionError
from .sync import SyncManager
from .connection_manager import ConnectionManager
from .manufacturers import execute_stage


class UpgradePackage:
    """
    Central object for managing network device firmware upgrades.

    This package object:
    - Holds all configuration (host, credentials, golden_image, file_server)
    - Maintains shared state (device_info, stage_results, errors)
    - Executes stages as methods that update the package state
    - Decides whether to continue based on stage success

    Attributes:
        host: Device IP/hostname
        username: SSH username
        password: SSH password
        port: SSH port (default: 22)
        golden_image: Target firmware information
        file_server: File server configuration
        device_type: Device platform type
        connection_mode: Connection mode (normal, mock, dry_run)

        # State attributes (populated during stages)
        device_info: Dictionary with device information (version, model, etc.)
        stage_results: Dictionary of stage name -> result
        errors: List of error messages
        success: Overall success status
        failed_stage: Name of stage that caused failure (if any)
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 22,
        golden_image: Optional[Dict[str, Any]] = None,
        file_server: Optional[Dict[str, Any]] = None,
        device_type: Optional[str] = None,
        connection_mode: str = "normal",
        **kwargs
    ):
        """
        Initialize the UpgradePackage.

        Args:
            host: Device IP address or hostname
            username: SSH username
            password: SSH password
            port: SSH port
            golden_image: Dictionary with golden image information
            file_server: Dictionary with file server information
            device_type: Device type/platform (e.g., cisco_xe)
            connection_mode: Connection mode - 'normal', 'mock', or 'dry_run'
            **kwargs: Additional arguments for device connection
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.golden_image = golden_image or {}
        self.file_server = file_server or {}
        self.device_type = device_type
        self.connection_mode = connection_mode
        self.device_kwargs = kwargs

        # State attributes - populated during stages
        self.device_info: Dict[str, Any] = {}
        self.stage_results: Dict[str, Dict[str, Any]] = {}
        self.errors: List[str] = []
        self.success: bool = False
        self.failed_stage: Optional[str] = None

        # Internal connection management
        self._device: Optional[Device] = None
        self._connection_manager: Optional[ConnectionManager] = None
        self._scrapli_conn = None

    def _connect(self) -> bool:
        """
        Establish device connection.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self._device = Device(
                host=self.host,
                username=self.username,
                password=self.password,
                port=self.port,
                device_type=self.device_type,
                connection_mode=self.connection_mode,
                **self.device_kwargs
            )

            if not self._device.connect():
                self.errors.append("Failed to connect to device")
                return False

            return True
        except DeviceConnectionError as e:
            self.errors.append(f"Connection error: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Connection failed: {e}")
            return False

    def _get_connection_manager(self) -> ConnectionManager:
        """
        Get or create ConnectionManager for unified connection handling.

        Returns:
            ConnectionManager instance
        """
        if self._connection_manager is None:
            self._connection_manager = ConnectionManager(
                host=self.host,
                username=self.username,
                password=self.password,
                device_type=self.device_type,
                port=self.port,
                connection_timeout=self.device_kwargs.get('connection_timeout', 30),
                enable_mode=self.device_kwargs.get('enable_mode', False),
                enable_password=self.device_kwargs.get('enable_password'),
                auth_strict_key=self.device_kwargs.get('auth_strict_key', False),
                transport=self.device_kwargs.get('transport', 'ssh'),
                connection_mode=self.connection_mode,
                scrapli_args=self.device_kwargs.get('scrapli_args', {})
            )
        return self._connection_manager

    def _get_scrapli_connection(self):
        """
        Get scrapli connection from connection manager.

        Returns:
            Scrapli connection object
        """
        if self._scrapli_conn is not None:
            return self._scrapli_conn

        cm = self._get_connection_manager()
        self._scrapli_conn = cm.get_connection('scrapli')
        self._scrapli_conn.open()
        return self._scrapli_conn

    def _stage_success(self, stage_name: str, result: Dict[str, Any]) -> bool:
        """
        Process stage success and update package state.

        Args:
            stage_name: Name of the stage
            result: Result dictionary from stage execution

        Returns:
            True if stage was successful
        """
        self.stage_results[stage_name] = result

        if result.get('success', False):
            return True

        self.errors.append(f"{stage_name} failed: {result.get('message', 'Unknown error')}")
        self.failed_stage = stage_name
        return False

    def sync(self) -> 'UpgradePackage':
        """
        Synchronize device information - fetch current version, model, etc.

        Updates:
            - device_info: Dictionary with device information
            - stage_results: sync result

        Returns:
            Self for method chaining
        """
        if not self._connect():
            self.stage_results['sync'] = {'success': False, 'message': 'Failed to connect'}
            self.failed_stage = 'sync'
            return self

        try:
            # Use connection manager for unified connection handling
            cm = self._get_connection_manager()

            # Get scrapli connection
            conn = cm.get_connection('scrapli')
            conn.open()

            # Get platform from connection manager
            platform = cm.get_platform(channel='scrapli')

            # Create sync manager and fetch info
            sync_mgr = SyncManager(connection_manager=cm, platform=platform)
            self.device_info = sync_mgr.fetch_info()

            # Update device_type if not set (NX-OS disabled)
            if not self.device_type and self.device_info.get('manufacturer') == 'Cisco':
                self.device_type = 'cisco_xe'

            # Populate tacacs_source_interface from device_info if available
            if self.device_info.get('tacacs_source_interface'):
                self.file_server['source_interface'] = self.device_info['tacacs_source_interface']

            self.stage_results['sync'] = {
                'success': True,
                'message': 'Device synchronized',
                'device_info': self.device_info
            }

        except Exception as e:
            self.stage_results['sync'] = {
                'success': False,
                'message': str(e)
            }
            self.errors.append(f"sync failed: {e}")
            self.failed_stage = 'sync'

        return self

    def readiness(self) -> 'UpgradePackage':
        """
        Check if device is ready for upgrade.

        Validates:
            - Sufficient flash space
            - Version compatibility (not already at target version)
            - Device health

        Updates:
            - stage_results: readiness result
            - errors: any readiness errors

        Returns:
            Self for method chaining
        """
        # Check if sync was run and device_type is available
        if not self.device_type:
            self.stage_results['readiness'] = {
                'success': False,
                'message': 'Device type not set. Run sync() first or provide device_type.'
            }
            self.errors.append("readiness failed: device_type not set")
            self.failed_stage = 'readiness'
            return self

        try:
            conn = self._get_scrapli_connection()
            platform = self.device_type

            # Get commands
            from .constants import DEVICE_COMMANDS
            commands = DEVICE_COMMANDS.get(platform.lower(), DEVICE_COMMANDS['cisco_iosxe'])

            # Execute readiness check
            result = execute_stage('cisco', 'readiness', conn, platform, commands, self.golden_image)

            if result and result.get('ready'):
                # Update device_info with version from readiness check
                if result.get('current_version'):
                    self.device_info['version'] = result['current_version']
                self.stage_results['readiness'] = {
                    'success': True,
                    'message': 'Device is ready for upgrade'
                }
            elif result:
                self.stage_results['readiness'] = {
                    'success': False,
                    'message': result.get('errors', ['Readiness check failed'])[0]
                }
                self.errors.extend(result.get('errors', ['Readiness check failed']))
                self.failed_stage = 'readiness'
            else:
                self.stage_results['readiness'] = {
                    'success': False,
                    'message': 'Readiness check returned no result'
                }
                self.errors.append('readiness failed: no result')
                self.failed_stage = 'readiness'

        except Exception as e:
            self.stage_results['readiness'] = {
                'success': False,
                'message': str(e)
            }
            self.errors.append(f"readiness failed: {e}")
            self.failed_stage = 'readiness'

        return self

    def pre_check(self) -> 'UpgradePackage':
        """
        Run pre-upgrade validation checks.

        Executes show commands and stores output in pre_check folder.

        Updates:
            - stage_results: pre_check result

        Returns:
            Self for method chaining
        """
        try:
            conn = self._get_scrapli_connection()

            # Show commands to run
            commands = {
                'show_ip_interface_brief': 'show ip interface brief',
                'show_version': 'show version',
                'show_inventory': 'show inventory',
                'show_interface_description': 'show interface description',
                'show_cdp_neighbors': 'show cdp neighbors',
                'show_ip_route_summary': 'show ip route summary',
                'show_ip_bgp_summary': 'show ip bgp summary',
                'show_ip_ospf_neighbor': 'show ip ospf neighbor',
                'show_standby_brief': 'show standby summary',
                'show_logging': 'show logging',
                'show_processes_cpu': 'show processes cpu sorted | exclude 0.00',
                'show_environment': 'show environment',
                'show_mac_address_table': 'show mac address-table',
                'show_interfaces_status': 'show interfaces status',
            }

            results = {}
            for cmd_name, cmd in commands.items():
                try:
                    output = conn.send_command(cmd)
                    results[cmd_name] = str(output.result)
                except Exception as e:
                    results[cmd_name] = f"Error: {e}"
                    self.errors.append(f"Failed to execute {cmd_name}: {e}")

            self.stage_results['pre_check'] = {
                'success': True,
                'message': 'Pre-check completed successfully',
                'outputs': results
            }

        except Exception as e:
            self.stage_results['pre_check'] = {
                'success': False,
                'message': str(e)
            }
            self.errors.append(f"pre_check failed: {e}")
            self.failed_stage = 'pre_check'

        return self

    def distribute(self) -> 'UpgradePackage':
        """
        Distribute firmware image to device.

        Uses unicon for file transfer (HTTP/HTTPS/TFTP/FTP/SCP).

        Updates:
            - stage_results: distribute result

        Returns:
            Self for method chaining
        """
        try:
            # Get connection manager for unicon
            cm = self._get_connection_manager()
            device_conn = cm.get_connection('unicon')
            device_conn.connect()

            # Get platform
            platform = self.device_type or 'cisco_iosxe'

            # Get source interface from user-provided file_server, then from device_info
            source_interface = self.file_server.get('source_interface')
            if not source_interface:
                source_interface = self.device_info.get('tacacs_source_interface')

            # Execute distribution using manufacturer module
            result = execute_stage(
                'cisco', 'distribution',
                device_conn, platform,
                self.file_server, self.golden_image,
                source_interface
            )

            if result and result.get('success'):
                self.stage_results['distribute'] = {
                    'success': True,
                    'message': result.get('message', 'Image distributed successfully')
                }
            else:
                self.stage_results['distribute'] = {
                    'success': False,
                    'message': result.get('message', 'Distribution failed') if result else 'Distribution failed'
                }
                self.errors.append(self.stage_results['distribute']['message'])
                self.failed_stage = 'distribute'

        except Exception as e:
            self.stage_results['distribute'] = {
                'success': False,
                'message': str(e)
            }
            self.errors.append(f"distribute failed: {e}")
            self.failed_stage = 'distribute'

        return self

    def activate(self) -> 'UpgradePackage':
        """
        Activate the new firmware on the device using profile-specific commands.

        Steps:
        1. Get hardware model from device
        2. Match model to device profile
        3. Use profile's upgrade_commands for activation

        Updates:
            - stage_results: activate result
            - device_profile: matched profile

        Returns:
            Self for method chaining
        """
        try:
            # Get connection manager for unicon
            cm = self._get_connection_manager()
            device_conn = cm.get_connection('unicon')
            device_conn.connect()

            # Get image name
            image_name = self.golden_image.get('image_name')
            if not image_name:
                self.stage_results['activate'] = {
                    'success': False,
                    'message': 'Missing image name for activation'
                }
                self.errors.append('activate failed: missing image name')
                self.failed_stage = 'activate'
                return self

            # Exit config mode if in configuration mode
            try:
                device_conn.execute('end', timeout=30)
            except Exception:
                pass

            # Configure boot system commands
            config_cmd = [
                "no boot system",
                "boot system flash:packages.conf",
                "no boot manual",
                "no system ignore startupconfig switch all",
            ]
            try:
                device_conn.execute('configure terminal', timeout=30)
                for cmd in config_cmd:
                    device_conn.execute(cmd, timeout=30)
                device_conn.execute('end', timeout=30)
                device_conn.execute('write memory', timeout=30)
            except Exception as e:
                self.stage_results['activate'] = {
                    'success': False,
                    'message': f'Failed to configure boot system: {e}'
                }
                self.errors.append(f"activate failed: boot config error - {e}")
                self.failed_stage = 'activate'
                return self

            # Get hardware model from device
            try:
                model_output = device_conn.execute("show version | include Processor", timeout=30)
                model_output_str = str(model_output)
                # Extract model from output (e.g., "Cisco C9KV-UADP-8P (VXE) processor")
                import re
                model_match = re.search(r'Cisco\s+([A-Z0-9-]+)', model_output_str)
                device_model = model_match.group(1) if model_match else None
                self.device_info['hardware_model'] = device_model
            except Exception as e:
                self.errors.append(f"Could not get hardware model: {e}")
                device_model = None

            # Match device model to profile
            from .device_profiles import match_model_to_profile, get_upgrade_command
            profile = None
            if device_model:
                profile = match_model_to_profile(device_model, 'cisco')

            # Build activation command
            activate_cmd = None
            if profile:
                # Use profile-specific command
                activate_cmd = get_upgrade_command('cisco', profile.get('model'), 'install_add')
                self.device_info['device_profile'] = profile
                self.device_info['profile_model'] = profile.get('model')
            else:
                # Fallback to standard IOS-XE command
                activate_cmd = f"install add file {image_name} activate commit"

            if not activate_cmd:
                self.stage_results['activate'] = {
                    'success': False,
                    'message': 'Could not build activation command'
                }
                self.errors.append('activate failed: could not build command')
                self.failed_stage = 'activate'
                return self

            # Execute activation command
            output = device_conn.execute(activate_cmd, timeout=300)

            # Check if activation was successful
            if "installed" in str(output).lower() or "commit" in str(output).lower():
                self.stage_results['activate'] = {
                    'success': True,
                    'message': 'Firmware activated successfully',
                    'command': activate_cmd,
                    'profile': profile.get('model') if profile else None
                }
            else:
                self.stage_results['activate'] = {
                    'success': False,
                    'message': f'Activation failed: {output}',
                    'command': activate_cmd
                }
                self.errors.append(f"activate failed: {output}")
                self.failed_stage = 'activate'

        except Exception as e:
            self.stage_results['activate'] = {
                'success': False,
                'message': str(e)
            }
            self.errors.append(f"activate failed: {e}")
            self.failed_stage = 'activate'

        return self

    def wait(self) -> 'UpgradePackage':
        """
        Wait for device to stabilize after activation.

        Updates:
            - stage_results: wait result

        Returns:
            Self for method chaining
        """
        import time

        try:
            wait_time = self.device_kwargs.get('wait_time', 300)
            time.sleep(wait_time)

            self.stage_results['wait'] = {
                'success': True,
                'message': f'Waited for {wait_time} seconds'
            }
        except Exception as e:
            self.stage_results['wait'] = {
                'success': False,
                'message': str(e)
            }
            self.errors.append(f"wait failed: {e}")
            self.failed_stage = 'wait'

        return self

    def ping(self) -> 'UpgradePackage':
        """
        Verify device is reachable after upgrade.

        Updates:
            - stage_results: ping result

        Returns:
            Self for method chaining
        """
        import subprocess
        import platform

        try:
            param = '-n' if platform.system().lower() == 'windows' else '-c'
            command = ['ping', param, '1', '-W', '5', self.host]
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                self.stage_results['ping'] = {
                    'success': True,
                    'message': 'Device is reachable'
                }
            else:
                self.stage_results['ping'] = {
                    'success': False,
                    'message': 'Device is not reachable'
                }
                self.errors.append('ping failed: device unreachable')
                self.failed_stage = 'ping'

        except Exception as e:
            self.stage_results['ping'] = {
                'success': False,
                'message': str(e)
            }
            self.errors.append(f"ping failed: {e}")
            self.failed_stage = 'ping'

        return self

    def post_check(self) -> 'UpgradePackage':
        """
        Run post-upgrade validation checks.

        Executes show commands and stores output in post_check folder.

        Updates:
            - stage_results: post_check result

        Returns:
            Self for method chaining
        """
        try:
            conn = self._get_scrapli_connection()

            # Show commands to run
            commands = {
                'show_ip_interface_brief': 'show ip interface brief',
                'show_version': 'show version',
                'show_inventory': 'show inventory',
                'show_interface_description': 'show interface description',
                'show_cdp_neighbors': 'show cdp neighbors',
                'show_ip_route_summary': 'show ip route summary',
                'show_ip_bgp_summary': 'show ip bgp summary',
                'show_ip_ospf_neighbor': 'show ip ospf neighbor',
                'show_standby_brief': 'show standby summary',
                'show_logging': 'show logging',
                'show_processes_cpu': 'show processes cpu sorted | exclude 0.00',
                'show_environment': 'show environment',
                'show_mac_address_table': 'show mac address-table',
                'show_interfaces_status': 'show interfaces status',
            }

            results = {}
            for cmd_name, cmd in commands.items():
                try:
                    output = conn.send_command(cmd)
                    results[cmd_name] = str(output.result)
                except Exception as e:
                    results[cmd_name] = f"Error: {e}"
                    self.errors.append(f"Failed to execute {cmd_name}: {e}")

            self.stage_results['post_check'] = {
                'success': True,
                'message': 'Post-check completed successfully',
                'outputs': results
            }

        except Exception as e:
            self.stage_results['post_check'] = {
                'success': False,
                'message': str(e)
            }
            self.errors.append(f"post_check failed: {e}")
            self.failed_stage = 'post_check'

        return self

    def verification(self) -> 'UpgradePackage':
        """
        Verify the device is running the target version.

        Updates:
            - stage_results: verification result
            - device_info: updated version

        Returns:
            Self for method chaining
        """
        try:
            target_version = self.golden_image.get('version')

            if not target_version:
                self.stage_results['verification'] = {
                    'success': False,
                    'message': 'Target version not specified'
                }
                self.errors.append('verification failed: target version not specified')
                self.failed_stage = 'verification'
                return self

            conn = self._get_scrapli_connection()
            output = conn.send_command("show version")

            # Parse current version
            current_version = str(output.result)
            parsed_version = self._parse_version_from_output(current_version)

            if parsed_version == target_version:
                self.device_info['version'] = parsed_version
                self.stage_results['verification'] = {
                    'success': True,
                    'message': f'Version verified: {parsed_version}'
                }
            else:
                self.stage_results['verification'] = {
                    'success': False,
                    'message': f'Version mismatch: expected {target_version}, got {parsed_version}'
                }
                self.errors.append(f"verification failed: version mismatch")
                self.failed_stage = 'verification'

        except Exception as e:
            self.stage_results['verification'] = {
                'success': False,
                'message': str(e)
            }
            self.errors.append(f"verification failed: {e}")
            self.failed_stage = 'verification'

        return self

    def _parse_version_from_output(self, output: str) -> str:
        """
        Parse version from show version output.

        Args:
            output: Raw show version output

        Returns:
            Version string
        """
        import re

        patterns = [
            r'Version\s+(\S+)',
            r'IOS-XE\s+Version\s+(\S+)',
            r'IOS\s+Version\s+(\S+)',
            r'Software\s+Version\s+(\S+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, output)
            if match:
                return match.group(1)

        return output.strip()[:50]

    def execute(self) -> Dict[str, Any]:
        """
        Execute all upgrade stages in order.

        Stages are executed in sequence:
        1. sync
        2. readiness
        3. pre_check
        4. distribute
        5. activate
        6. wait
        7. ping
        8. post_check
        9. verification

        Stops if any stage fails.

        Returns:
            Dictionary with upgrade results
        """
        stages_order = [
            'sync',
            'readiness',
            'pre_check',
            'distribute',
            'activate',
            'wait',
            'ping',
            'post_check',
            'verification'
        ]

        for stage_name in stages_order:
            stage_method = getattr(self, stage_name)
            stage_method()  # Execute stage

            # Check if stage failed
            if stage_name in self.stage_results:
                result = self.stage_results[stage_name]
                if not result.get('success', False):
                    # Stop on failure
                    break

        # Calculate overall success
        self.success = self.failed_stage is None

        # Generate final result
        result = {
            'success': self.success,
            'device_info': self.device_info,
            'stage_results': self.stage_results,
            'errors': self.errors.copy(),
            'failed_stage': self.failed_stage
        }

        return result

    def disconnect(self):
        """
        Close all connections.
        """
        if self._device:
            try:
                self._device.disconnect()
            except Exception:
                pass
            self._device = None

        if self._connection_manager:
            try:
                self._connection_manager.disconnect()
            except Exception:
                pass
            self._connection_manager = None

        self._scrapli_conn = None

    def __enter__(self):
        """Context manager entry - connect to device."""
        self._connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - disconnect from device."""
        self.disconnect()
        return False
