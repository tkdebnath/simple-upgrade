"""
Upgrade workflow management - handles the upgrade stages from readiness to verification.

Library usage:
- scrapli: sync, readiness, pre-checks, post-checks, ping, verification
- unicon: manually managed for distribution and activation

Mock and Dry-Run modes:
- mock: Simulate entire pipeline without any real connections
- dry_run: Connect to device but only execute show commands; mock upgrade commands
"""

import time
from typing import Optional, Dict, Any, List

from .device import Device, DeviceConnectionError
from .sync import SyncManager
from .connection_manager import ConnectionManager
from .mocks import MockUpgradeWorkflow, DryRunUpgradeWorkflow


class UpgradeStage:
    """Represents a single upgrade stage."""
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.success: bool = False
        self.message: str = ""
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None


class UpgradeWorkflow:
    """
    Manages the complete upgrade workflow for a network device.

    Workflow stages:
        1. Readiness - Validate device can be upgraded (using scrapli)
        2. Pre-check - Run pre-upgrade validations (using unicon)
        3. Distribute - Download firmware image (using unicon)
        4. Activate - Apply new firmware (using unicon)
        5. Wait - Wait for stabilization
        6. Ping - Verify device is reachable
        7. Post-check - Run post-upgrade validations (using unicon)
        8. Verification - Confirm version match (using scrapli)

    Connection Modes:
        - normal: Actual SSH connection with full upgrade execution
        - mock: Simulate entire pipeline without any real connections
        - dry_run: Connect to device but only execute show commands; mock upgrade commands
    """

    def __init__(
        self,
        device: Device,
        golden_image: Dict[str, Any],
        file_server: Dict[str, Any],
        auto_update: bool = True,
        wait_time: int = 300,
        max_retries: int = 3,
        connection_mode: str = "normal",  # normal, mock, dry_run
        connection_manager: Optional[Any] = None
    ):
        """
        Initialize the upgrade workflow.

        Args:
            device: Device object with active connection
            golden_image: Dictionary with golden image information
            file_server: Dictionary with file server information
            auto_update: Whether to automatically apply changes
            wait_time: Wait time after activation in seconds
            max_retries: Maximum retries for each stage
            connection_mode: Connection mode - 'normal', 'mock', or 'dry_run'
            connection_manager: Optional ConnectionManager for unified connection handling
        """
        self.device = device
        self.golden_image = golden_image
        self.file_server = file_server
        self.auto_update = auto_update
        self.wait_time = wait_time
        self.max_retries = max_retries
        self.connection_mode = connection_mode
        self.connection_manager = connection_manager

        self.stages: Dict[str, UpgradeStage] = {}
        self.errors: List[str] = []

        # Initialize stages
        self._init_stages()

    def _init_stages(self):
        """Initialize all upgrade stages."""
        self.stages = {
            'readiness': UpgradeStage('readiness', 'Validate device readiness for upgrade'),
            'pre_check': UpgradeStage('pre_check', 'Run pre-upgrade validation checks'),
            'distribute': UpgradeStage('distribute', 'Download firmware image'),
            'activate': UpgradeStage('activate', 'Apply new firmware'),
            'wait': UpgradeStage('wait', 'Wait for device stabilization'),
            'ping': UpgradeStage('ping', 'Verify device reachability'),
            'post_check': UpgradeStage('post_check', 'Run post-upgrade validation checks'),
            'verification': UpgradeStage('verification', 'Confirm version matches target'),
        }

    def _run_stage(self, stage_name: str, **kwargs) -> bool:
        """
        Run a single upgrade stage.

        Args:
            stage_name: Name of the stage to run
            **kwargs: Additional arguments for the stage

        Returns:
            True if stage succeeded, False otherwise
        """
        stage = self.stages.get(stage_name)
        if not stage:
            self.errors.append(f"Unknown stage: {stage_name}")
            return False

        stage.start_time = time.time()
        stage.success = False

        try:
            if stage_name == 'readiness':
                success = self._check_readiness(**kwargs)
            elif stage_name == 'pre_check':
                success = self._run_pre_checks(**kwargs)
            elif stage_name == 'distribute':
                success = self._distribute_image(**kwargs)
            elif stage_name == 'activate':
                success = self._activate_image(**kwargs)
            elif stage_name == 'wait':
                success = self._wait_for_stabilization(**kwargs)
            elif stage_name == 'ping':
                success = self._ping_device(**kwargs)
            elif stage_name == 'post_check':
                success = self._run_post_checks(**kwargs)
            elif stage_name == 'verification':
                success = self._verify_version(**kwargs)
            else:
                self.errors.append(f"Stage not implemented: {stage_name}")
                success = False

            stage.success = success
            stage.end_time = time.time()

            if success:
                stage.message = f"{stage.name} completed successfully"
            else:
                stage.message = f"{stage.name} failed"

            return success

        except Exception as e:
            stage.message = f"Exception: {str(e)}"
            self.errors.append(f"{stage_name} failed with exception: {str(e)}")
            return False

    def upgrade(self) -> Dict[str, Any]:
        """
        Execute the complete upgrade workflow.

        Returns:
            Dictionary containing:
                - success: Overall success status
                - stages: Individual stage results
                - errors: List of errors encountered
        """
        # Handle mock mode
        if self.connection_mode == 'mock':
            mock_workflow = MockUpgradeWorkflow(
                device=self.device,
                golden_image=self.golden_image,
                file_server=self.file_server,
                connection_mode='mock'
            )
            return mock_workflow.upgrade()

        # Handle dry-run mode
        if self.connection_mode == 'dry_run':
            dryrun_workflow = DryRunUpgradeWorkflow(
                device=self.device,
                golden_image=self.golden_image,
                file_server=self.file_server,
                connection_mode='dry_run'
            )
            return dryrun_workflow.upgrade()

        # Normal mode - run actual stages
        result = {
            'success': False,
            'stages': {},
            'errors': self.errors.copy()
        }

        # Execute stages in order
        # Note: Only using scrapli-based stages
        # unicon-based stages (distribute, activate) are handled separately
        stages_order = [
            'readiness',
            'pre_check',
            'wait',
            'ping',
            'post_check',
            'verification'
        ]

        for stage_name in stages_order:
            if not self._run_stage(stage_name):
                # Continue to next stage but mark overall as failed
                pass

        # Check if all stages succeeded
        all_success = all(stage.success for stage in self.stages.values())

        result['success'] = all_success
        result['stages'] = {
            name: {
                'name': stage.name,
                'success': stage.success,
                'message': stage.message,
                'duration': (stage.end_time - stage.start_time) if stage.start_time and stage.end_time else 0
            }
            for name, stage in self.stages.items()
        }

        return result

    def _check_readiness(self, **kwargs) -> bool:
        """
        Check if device is ready for upgrade using scrapli and manufacturer module.

        Validates:
            - Sufficient flash space
            - Version compatibility
            - Device health
        """
        try:
            # Get platform from device
            platform = self.device.platform

            # Use manufacturer-specific readiness check
            from .manufacturers import execute_stage

            # Get commands
            from .constants import DEVICE_COMMANDS
            commands = DEVICE_COMMANDS.get('cisco_iosxe', {'dir': 'dir', 'show_version': 'show version'})

            # Build golden image from kwargs or instance
            golden_image = kwargs.get('golden_image', self.golden_image)

            # Execute manufacturer readiness check
            result = execute_stage('cisco', 'readiness', self.device._connection, 'scrapli', platform, commands, golden_image)

            if result and result.get('ready'):
                self.errors.extend(result.get('errors', []))
                return True
            elif result:
                self.errors.extend(result.get('errors', []))
                return False

            # Fallback if execute_stage fails
            if not self.device._connection:
                self.errors.append("Device not connected")
                return False

            # Get flash info
            flash_output = self.device.send_command("dir")

            # Check if image size requirement can be met
            if 'image_size' in self.golden_image:
                image_size = self.golden_image['image_size']
                if 'bytes' in flash_output.lower():
                    pass

            # Check current version
            if self.device.version == self.golden_image.get('version'):
                self.errors.append("Device already running target version")
                return False

            return True

        except Exception as e:
            self.errors.append(f"Readiness check failed: {e}")
            return False

    def _run_checks(self, check_type: str, **kwargs) -> bool:
        """
        Run pre or post upgrade validation checks using scrapli.

        Args:
            check_type: 'pre' or 'post' to determine folder naming
        """
        try:
            import os
            from datetime import datetime

            # Get device info for folder name
            hostname = self.device.hostname or self.device.host
            folder_name = f"{check_type}_check_{hostname}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            output_dir = os.path.join("output", folder_name)
            os.makedirs(output_dir, exist_ok=True)

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

            for cmd_name, cmd in commands.items():
                try:
                    output = self.device.send_command(cmd)
                    output_file = os.path.join(output_dir, f"{cmd_name}.txt")
                    with open(output_file, 'w') as f:
                        f.write(output)
                except Exception as e:
                    self.errors.append(f"Failed to execute {cmd_name}: {e}")

            return True
        except Exception as e:
            self.errors.append(f"{check_type.title()}-check failed: {e}")
            return False

    def _run_pre_checks(self, **kwargs) -> bool:
        """
        Run pre-upgrade validation checks.
        """
        return self._run_checks('pre', **kwargs)

    def _run_post_checks(self, **kwargs) -> bool:
        """
        Run post-upgrade validation checks.
        """
        return self._run_checks('post', **kwargs)

    def _wait_for_stabilization(self, **kwargs) -> bool:
        """
        Wait for device to stabilize after activation.
        """
        wait_time = kwargs.get('wait_time', self.wait_time)
        time.sleep(wait_time)
        return True

    def _ping_device(self, **kwargs) -> bool:
        """
        Verify device is reachable after upgrade.
        """
        import subprocess
        import platform

        try:
            param = '-n' if platform.system().lower() == 'windows' else '-c'
            command = ['ping', param, '1', '-W', '5', self.device.host]
            result = subprocess.run(command, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return True
        except Exception:
            pass

        return False

    def _run_post_checks(self, **kwargs) -> bool:
        """
        Run post-upgrade validation checks using scrapli.
        Executes show commands and stores output in post_check folder.
        """
        try:
            import os
            import time
            from datetime import datetime

            # Get device info for folder name
            hostname = self.device.hostname or self.device.host
            folder_name = f"post_check_{hostname}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            output_dir = os.path.join("output", folder_name)
            os.makedirs(output_dir, exist_ok=True)

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

            for cmd_name, cmd in commands.items():
                try:
                    output = self.device.send_command(cmd)
                    output_file = os.path.join(output_dir, f"{cmd_name}.txt")
                    with open(output_file, 'w') as f:
                        f.write(output)
                except Exception as e:
                    self.errors.append(f"Failed to execute {cmd_name}: {e}")

            return True
        except Exception as e:
            self.errors.append(f"Post-check failed: {e}")
            return False

    def _verify_version(self, **kwargs) -> bool:
        """
        Verify the device is running the target version using scrapli.
        """
        try:
            target_version = self.golden_image.get('version', '')

            if not target_version:
                return False

            # Get current version using scrapli
            output = self.device.send_command("show version")

            # Compare with current version
            if self.device.version == target_version:
                return True

            return False
        except Exception as e:
            self.errors.append(f"Version verification failed: {e}")
            return False


class UpgradeManager:
    """
    High-level manager for firmware upgrades.

    Usage:
        manager = UpgradeManager(
            host="192.168.1.1",
            username="admin",
            password="password",
            device_type="cisco_xe",
            golden_image={
                "version": "17.9.4",
                "image_name": "flash:c9300-universalk9.17.9.4.SPA.bin",
            },
            file_server={
                "ip": "10.0.0.10",
                "protocol": "http",
                "base_path": "/tftpboot"
            }
        )
        result = manager.upgrade()

    Connection Modes:
        - normal: Actual SSH connection with full upgrade execution
        - mock: Simulate entire pipeline without any real connections
        - dry_run: Connect to device but only execute show commands; mock upgrade commands
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 22,
        device_type: Optional[str] = None,
        golden_image: Optional[Dict[str, Any]] = None,
        file_server: Optional[Dict[str, Any]] = None,
        connection_mode: str = "normal",  # normal, mock, dry_run
        **kwargs
    ):
        """
        Initialize the UpgradeManager.

        Args:
            host: Device IP or hostname
            username: SSH username
            password: SSH password
            port: SSH port
            device_type: Device type/platform (e.g., cisco_ios, cisco_xe, cisco_nxos)
                        Required for scrapli connection.
            golden_image: Golden image information
            file_server: File server information
            connection_mode: Connection mode - 'normal', 'mock', or 'dry_run'
            **kwargs: Additional arguments passed to Device and UpgradeWorkflow
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.device_type = device_type
        self.golden_image = golden_image or {}
        self.file_server = file_server or {}
        self.connection_mode = connection_mode
        self.device_kwargs = kwargs

        self.device: Optional[Device] = None
        self.workflow: Optional[UpgradeWorkflow] = None

    def connect(self) -> bool:
        """Establish connection to the device."""
        device_kwargs = {
            'host': self.host,
            'username': self.username,
            'password': self.password,
            'port': self.port,
        }
        # Add device_type if provided
        if self.device_type:
            device_kwargs['device_type'] = self.device_type
        device_kwargs['connection_mode'] = self.connection_mode
        device_kwargs.update(self.device_kwargs)

        self.device = Device(**device_kwargs)

        try:
            return self.device.connect()
        except DeviceConnectionError as e:
            raise e

    def upgrade(self) -> Dict[str, Any]:
        """
        Perform the complete upgrade process.

        Returns:
            Dictionary with upgrade results
        """
        if not self.device:
            raise DeviceConnectionError("Not connected. Call connect() first.")

        # Gather device information
        device_info = self.device.gather_info()

        # Create ConnectionManager for unified connection handling
        connection_manager = ConnectionManager(
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

        # Initialize workflow
        # Filter device_kwargs to only include valid UpgradeWorkflow parameters
        workflow_kwargs = {
            'auto_update': self.device_kwargs.get('auto_update', True),
            'wait_time': self.device_kwargs.get('wait_time', 300),
            'max_retries': self.device_kwargs.get('max_retries', 3),
            'connection_manager': connection_manager,
        }

        # Update file_server with tacacs source interface from device if not already set
        file_server = self.file_server.copy()
        if not file_server.get('source_interface'):
            # Try to get tacacs_source_interface from device or device_info
            tacacs_interface = getattr(self.device, 'tacacs_source_interface', None)
            if tacacs_interface:
                file_server['source_interface'] = tacacs_interface
            elif self.device_kwargs.get('tacacs_source_interface'):
                file_server['source_interface'] = self.device_kwargs.get('tacacs_source_interface')

        self.workflow = UpgradeWorkflow(
            device=self.device,
            golden_image=self.golden_image,
            file_server=file_server,
            connection_mode=self.connection_mode,
            **workflow_kwargs
        )

        # Execute upgrade
        result = self.workflow.upgrade()

        # Update result with device info
        result['device_info'] = device_info

        return result

    def disconnect(self):
        """Close the device connection."""
        if self.device:
            self.device.disconnect()
            self.device = None

    def sync(self) -> Dict[str, Any]:
        """
        Synchronize device information - fetch current version, model, etc.

        Returns:
            Dictionary with device information
        """
        if not self.device:
            raise DeviceConnectionError("Not connected. Call connect() first.")

        # Use ConnectionManager to sync device info
        cm = ConnectionManager(
            host=self.device.host,
            username=self.device.username,
            password=self.device.password,
            device_type=self.device_type,
            port=self.device.port,
        )

        # Get scrapli connection
        conn = cm.get_connection('scrapli')

        # Open connection
        conn.open()

        # Get platform from connection manager
        platform = cm.get_platform(channel='scrapli')

        # Create sync manager with platform
        sync_mgr = SyncManager(connection_manager=cm, platform=platform)

        # Fetch info using the connection
        device_info = sync_mgr.fetch_info()

        # Close connection
        conn.close()
        cm.disconnect()

        return device_info
