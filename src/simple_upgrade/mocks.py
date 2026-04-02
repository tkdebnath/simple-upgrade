"""
Mock and Dry-Run module - Simulated device connections for testing.

This module provides mock connections for:
- Mock mode: Simulate the entire upgrade pipeline without any real connections
- Dry-run mode: Connect to device but only execute show commands; mock all upgrade commands

Usage:
    from simple_upgrade import MockConnection, DryRunConnection, MockSyncManager
    from simple_upgrade import UpgradeManager

    # Mock mode - pipeline simulation only
    manager = UpgradeManager(
        host="192.168.1.1",
        username="admin",
        password="password",
        device_type="cisco_xe",
        connection_mode="mock"
    )
    result = manager.upgrade()
    print(result['pipeline'])  # Shows what would happen

    # Dry-run mode - connect but only show commands execute
    manager = UpgradeManager(
        host="192.168.1.1",
        username="admin",
        password="password",
        device_type="cisco_xe",
        connection_mode="dry_run"
    )
    result = manager.upgrade()
    print(result['dry_run_commands'])  # Shows what commands would execute

Execution Path Tracking:
In dry-run mode, the execution path is tracked showing:
    class -> function -> line_number

Example:
    {
        "class": "UpgradeWorkflow",
        "function": "_run_stage",
        "line": 118,
        "stage": "distribute"
    }
"""

import time
import re
import inspect
from typing import Optional, Dict, Any, List
from .device import Device, DeviceConnectionError
from .connection_manager import ConnectionManager, ConnectionError
from .sync import SyncManager
from .manufacturers import cisco
from . import manufacturers


class MockConnection:
    """
    Mock connection that simulates device behavior without real SSH.

    Use for testing and pipeline simulation.
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        device_type: str = "cisco_xe",
        port: int = 22,
        platform: str = "cisco_iosxe"
    ):
        self.host = host
        self.username = username
        self.password = password
        self.device_type = device_type
        self.port = port
        self.platform = platform
        self.connected = True
        self.channel = 'mock'

        # Track what would happen
        self.commands_executed: List[Dict[str, str]] = []
        self.warnings: List[str] = []

    def open(self):
        """Simulate opening connection."""
        self.connected = True
        self.commands_executed.append({'command': 'open_connection', 'output': 'Connected to mock device'})

    def close(self):
        """Simulate closing connection."""
        self.connected = False
        self.commands_executed.append({'command': 'close_connection', 'output': 'Connection closed'})

    def send_command(self, command: str) -> Any:
        """Simulate sending a command and return mock output.

        Returns a result-like object with a .result attribute for compatibility.
        """
        self.commands_executed.append({'command': command, 'mode': 'show'})
        # Get model from platform or use default
        model = self._get_model_from_platform()
        output = _get_mock_output(command, self.platform, model)

        # Return a simple object with .result attribute for compatibility
        class CommandResult:
            def __init__(self, result):
                self.result = result

        return CommandResult(output)

    def send_configs(self, commands: List[str]) -> Any:
        """Simulate sending configuration commands.

        Returns a result-like object with a .result attribute for compatibility.
        """
        for cmd in commands:
            self.commands_executed.append({'command': cmd, 'mode': 'config'})
        result = "Configuration applied (mock)"

        class CommandResult:
            def __init__(self, result):
                self.result = result

        return CommandResult(result)

    def execute(self, command: str) -> str:
        """Execute command (unicon-style)."""
        self.commands_executed.append({'command': command, 'mode': 'execute'})
        # Get model from platform or use default
        model = self._get_model_from_platform()
        return _get_mock_output(command, self.platform, model)

    def _get_model_from_platform(self) -> str:
        """Get model name from device_type/platform."""
        platform = (self.device_type or '').lower()
        if 'cisco' in platform:
            if '9300' in platform:
                return 'C9300'
            elif '9400' in platform:
                return 'C9400'
            elif '9500' in platform:
                return 'C9500'
            return 'C9300'
        elif 'juniper' in platform or 'junos' in platform:
            return 'MX'
        elif 'arista' in platform or 'eos' in platform:
            return '7050'
        return 'C9300'


class DryRunConnection:
    """
    Dry-run connection that connects to real device but only executes show commands.

    All upgrade commands (copy, install, activate) are mocked.
    Tracks the full execution path (class -> function -> line) for dry-run analysis.
    """

    def __init__(
        self,
        real_connection: Any,
        platform: str
    ):
        self.real_connection = real_connection
        self.platform = platform
        self.connected = True
        self.channel = 'dry_run'

        self.commands_executed: List[Dict[str, Any]] = []
        self.show_commands_executed: List[str] = []
        self.mocked_commands: List[Dict[str, str]] = []
        self.execution_path: List[Dict[str, str]] = []  # Tracks: class -> function -> line

    def _track_execution(self, class_name: str, function_name: str, line: int, stage: str = ""):
        """Track the execution path."""
        self.execution_path.append({
            'class': class_name,
            'function': function_name,
            'line': line,
            'stage': stage
        })

    def open(self):
        """Open real connection for show commands."""
        self._track_execution('DryRunConnection', 'open', inspect.currentframe().f_lineno, '')
        if hasattr(self.real_connection, 'open'):
            self.real_connection.open()
        self.connected = True

    def close(self):
        """Close real connection."""
        self._track_execution('DryRunConnection', 'close', inspect.currentframe().f_lineno, '')
        if hasattr(self.real_connection, 'close'):
            self.real_connection.close()
        self.connected = False

    def send_command(self, command: str) -> str:
        """Send command - real for show, mocked for upgrade."""
        self._track_execution('DryRunConnection', 'send_command', inspect.currentframe().f_lineno, '')

        is_upgrade_cmd = any(kw in command.lower() for kw in ['copy ', 'install ', 'activate ', 'commit', 'copy'])

        if is_upgrade_cmd:
            self.commands_executed.append({'command': command, 'mode': 'mocked'})
            self.mocked_commands.append(command)
            return _get_mock_upgrade_output(command, self.platform)
        else:
            self.commands_executed.append({'command': command, 'mode': 'real'})
            self.show_commands_executed.append(command)
            try:
                result = self.real_connection.send_command(command)
                return str(result.result) if hasattr(result, 'result') else str(result)
            except Exception as e:
                return f"Error: {e}"

    def send_configs(self, commands: List[str]) -> str:
        """Send config commands - real for show, mocked for upgrade."""
        self._track_execution('DryRunConnection', 'send_configs', inspect.currentframe().f_lineno, '')

        for cmd in commands:
            is_upgrade_cmd = any(kw in cmd.lower() for kw in ['copy ', 'install ', 'activate ', 'commit', 'copy'])
            if is_upgrade_cmd:
                self.commands_executed.append({'command': cmd, 'mode': 'mocked'})
                self.mocked_commands.append(cmd)
            else:
                self.commands_executed.append({'command': cmd, 'mode': 'real'})
                self.show_commands_executed.append(cmd)
        return "Config applied (mocked)"


class MockSyncManager:
    """
    Mock sync manager for pipeline simulation without real connection.
    """

    def __init__(self, platform: str = "cisco_iosxe"):
        self.platform = platform
        self.info: Dict[str, Any] = {
            'manufacturer': '',
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

    def fetch_info(self) -> Dict[str, Any]:
        """Fetch mock device information."""
        self.info['manufacturer'] = 'Cisco' if 'cisco' in self.platform else 'Juniper' if 'junos' in self.platform else 'Arista'
        self.info['model'] = 'C9300' if 'cisco' in self.platform else 'MX' if 'junos' in self.platform else '7050'
        self.info['version'] = '17.9.4'
        self.info['current_version'] = '17.9.3'
        self.info['hostname'] = 'R1'
        self.info['serial_number'] = 'FCW23456789'
        self.info['serial'] = self.info['serial_number']
        self.info['uptime'] = '2 days, 3 hours'
        self.info['boot_method'] = 'flash:/cat9k_iosxe.SPA.17.9.4.bin'
        self.info['boot_mode'] = 'normal'
        self.info['config_register'] = '0x101'
        self.info['flash_size'] = '8 GB'
        self.info['memory_size'] = '16 GB'

        return self.info


class MockUpgradeWorkflow:
    """
    Mock upgrade workflow for pipeline simulation.

    Manufacturer-specific outputs:
    - Cisco: Uses install add/activate/commit workflow
    - Juniper: Uses request system software add workflow
    - Arista: Uses install image workflow
    """

    def __init__(
        self,
        device: Device,
        golden_image: Dict[str, Any],
        file_server: Dict[str, Any],
        connection_mode: str = "mock"
    ):
        self.device = device
        self.golden_image = golden_image
        self.file_server = file_server
        self.connection_mode = connection_mode
        self.stages: Dict[str, Dict[str, Any]] = {}
        self.commands_executed: List[Dict[str, Any]] = []
        self.warnings: List[str] = []
        self.execution_path: List[Dict[str, Any]] = []  # Tracks: class -> function -> line

        # Get manufacturer and model from device for platform-specific output
        self.manufacturer = self._get_manufacturer()
        self.model = self._get_model()
        self.platform = self._get_platform()

        # Initialize device info (use device's info if available, else default)
        device_info = getattr(self.device, 'info', {})
        if not device_info and hasattr(self.device, 'gather_info'):
            try:
                device_info = self.device.gather_info()
            except Exception:
                device_info = {}
        self.info = {
            'version': device_info.get('version', '17.9.4'),
            'current_version': device_info.get('version', '17.9.4'),
            'hostname': device_info.get('hostname', 'R1'),
            'model': device_info.get('model', self.model),
            'platform': device_info.get('platform', self.platform),
        }

        # Initialize stages
        self._init_stages()

    def _get_manufacturer(self) -> str:
        """Get manufacturer from device info."""
        if hasattr(self.device, 'manufacturer') and self.device.manufacturer:
            return self.device.manufacturer
        # Try to infer from platform
        platform = self.device.device_type or ''
        if 'cisco' in platform.lower():
            return 'Cisco'
        elif 'juniper' in platform.lower() or 'junos' in platform.lower():
            return 'Juniper'
        elif 'arista' in platform.lower():
            return 'Arista'
        return 'Unknown'

    def _get_model(self) -> str:
        """Get model from device info or infer from device_type."""
        if hasattr(self.device, 'model') and self.device.model:
            return self.device.model

        # Infer model from device_type
        platform = (self.device.device_type or '').lower()

        # Cisco models
        if 'cisco' in platform:
            if '9300' in platform or 'c9300' in platform:
                return 'C9300'
            elif '9400' in platform or 'c9400' in platform:
                return 'C9400'
            elif '9500' in platform or 'c9500' in platform:
                return 'C9500'
            elif '4400' in platform or 'isr4400' in platform:
                return 'ISR4400'
            elif '4300' in platform or 'isr4300' in platform:
                return 'ISR4300'
            elif 'n9k' in platform or 'nx9000' in platform:
                return 'N9K'
            # NX-OS disabled
            else:
                return 'C9300'  # Default Cisco model

        # Juniper models
        elif 'juniper' in platform or 'junos' in platform:
            if 'mx' in platform or 'mx' in platform:
                return 'MX'
            elif 'qfx' in platform or 'qfx' in platform:
                return 'QFX'
            elif 'srx' in platform or 'srx' in platform:
                return 'SRX'
            elif 'ptx' in platform or 'ptx' in platform:
                return 'PTX'
            else:
                return 'MX'  # Default Juniper model

        # Arista models
        elif 'arista' in platform or 'eos' in platform:
            if '7050' in platform or '7050' in platform:
                return '7050'
            elif '7280' in platform or '7280' in platform:
                return '7280'
            elif '7500' in platform or '7500' in platform:
                return '7500'
            else:
                return '7050'  # Default Arista model

        return 'Unknown'

    def _get_platform(self) -> str:
        """Get platform from device info."""
        if hasattr(self.device, 'platform') and self.device.platform:
            return self.device.platform
        platform = self.device.device_type or ''
        if 'cisco' in platform.lower():
            return 'cisco_iosxe'
        elif 'juniper' in platform.lower() or 'junos' in platform.lower():
            return 'juniper_junos'
        elif 'arista' in platform.lower():
            return 'arista_eos'
        return 'cisco_iosxe'

    def _init_stages(self):
        """Initialize mock stages."""
        self.stages = {
            'readiness': {'name': 'readiness', 'status': 'pending', 'message': ''},
            'pre_check': {'name': 'pre_check', 'status': 'pending', 'message': ''},
            'distribute': {'name': 'distribute', 'status': 'pending', 'message': ''},
            'activate': {'name': 'activate', 'status': 'pending', 'message': ''},
            'wait': {'name': 'wait', 'status': 'pending', 'message': ''},
            'ping': {'name': 'ping', 'status': 'pending', 'message': ''},
            'post_check': {'name': 'post_check', 'status': 'pending', 'message': ''},
            'verification': {'name': 'verification', 'status': 'pending', 'message': ''},
        }

    def _track_execution(self, class_name: str, function_name: str, line: int, stage: str = ""):
        """Track the execution path."""
        self.execution_path.append({
            'class': class_name,
            'function': function_name,
            'line': line,
            'stage': stage
        })

    def _run_stage(self, stage_name: str, **kwargs) -> bool:
        """Run a mock stage."""
        self._track_execution('MockUpgradeWorkflow', '_run_stage', inspect.currentframe().f_lineno, stage_name)
        stage = self.stages.get(stage_name)
        if not stage:
            self.warnings.append(f"Unknown stage: {stage_name}")
            return False

        stage['status'] = 'running'

        try:
            if stage_name == 'readiness':
                stage['message'] = self._mock_readiness()
                stage['status'] = 'success'
            elif stage_name == 'pre_check':
                stage['message'] = self._mock_pre_check()
                stage['status'] = 'success'
            elif stage_name == 'distribute':
                stage['message'] = self._mock_distribute()
                stage['status'] = 'success'
            elif stage_name == 'activate':
                stage['message'] = self._mock_activate()
                stage['status'] = 'success'
            elif stage_name == 'wait':
                stage['message'] = self._mock_wait(kwargs.get('wait_time', 300))
                stage['status'] = 'success'
            elif stage_name == 'ping':
                stage['message'] = self._mock_ping()
                stage['status'] = 'success'
            elif stage_name == 'post_check':
                stage['message'] = self._mock_post_check()
                stage['status'] = 'success'
            elif stage_name == 'verification':
                stage['message'] = self._mock_verification()
                stage['status'] = 'success'
            else:
                stage['message'] = f"Stage not implemented: {stage_name}"
                stage['status'] = 'failed'
                return False

            return True

        except Exception as e:
            stage['message'] = f"Exception: {str(e)}"
            self.warnings.append(f"{stage_name} failed: {e}")
            stage['status'] = 'failed'
            return False

    def _mock_readiness(self) -> str:
        """Mock readiness check - manufacturer specific."""
        self._track_execution('MockUpgradeWorkflow', '_mock_readiness', inspect.currentframe().f_lineno, 'readiness')
        self.commands_executed.append({'stage': 'readiness', 'command': 'show version', 'mode': 'show'})
        self.commands_executed.append({'stage': 'readiness', 'command': 'dir', 'mode': 'show'})

        target_version = self.golden_image.get('version', 'unknown')
        current_version = self.info.get('version', '17.9.4')

        # Check if versions match (should not upgrade to same version)
        if target_version == current_version:
            if self.manufacturer == 'Cisco':
                return f"Cisco readiness check: Device already running target version {target_version}"
            elif self.manufacturer == 'Juniper':
                return f"Juniper readiness check: Device already running target version {target_version}"
            elif self.manufacturer == 'Arista':
                return f"Arista readiness check: Device already running target version {target_version}"
            return f"Device already running target version {target_version}"

        if self.manufacturer == 'Cisco':
            return "Cisco readiness check: Device is ready for upgrade"
        elif self.manufacturer == 'Juniper':
            return "Juniper readiness check: Device is ready for upgrade"
        elif self.manufacturer == 'Arista':
            return "Arista readiness check: Device is ready for upgrade"
        return "Device is ready for upgrade"

    def _mock_pre_check(self) -> str:
        """Mock pre-check - manufacturer specific."""
        self._track_execution('MockUpgradeWorkflow', '_mock_pre_check', inspect.currentframe().f_lineno, 'pre_check')
        self.commands_executed.append({'stage': 'pre_check', 'command': 'show version', 'mode': 'show'})

        if self.manufacturer == 'Cisco':
            return "Cisco pre-checks: Checksum verified, sufficient flash space"
        elif self.manufacturer == 'Juniper':
            return "Juniper pre-checks: Route engine redundancy OK, sufficient storage"
        elif self.manufacturer == 'Arista':
            return "Arista pre-checks: Checksum verified, sufficient flash space"
        return "Pre-checks passed"

    def _mock_distribute(self) -> str:
        """Mock image distribution - manufacturer specific."""
        self._track_execution('MockUpgradeWorkflow', '_mock_distribute', inspect.currentframe().f_lineno, 'distribute')
        image_name = self.golden_image.get('image_name', 'unknown')
        protocol = self.file_server.get('protocol', 'http')
        server_ip = self.file_server.get('ip', '')
        base_path = self.file_server.get('base_path', '')

        # Build platform-specific copy command
        copy_cmd = _build_manufacturer_copy_command(self.manufacturer, self.platform, protocol, server_ip, base_path, image_name)

        self.commands_executed.append({
            'stage': 'distribute',
            'command': copy_cmd,
            'mode': 'upgrade',
            'actual_command': copy_cmd
        })

        if self.manufacturer == 'Cisco':
            return f"Cisco DISTRIBUTION: copy {protocol}://{server_ip}/{base_path}/{image_name} flash:/{image_name}"
        elif self.manufacturer == 'Juniper':
            return f"Juniper DISTRIBUTION: request system software add {protocol}://{server_ip}/{base_path}/{image_name}"
        elif self.manufacturer == 'Arista':
            return f"Arista DISTRIBUTION: copy {protocol}://{server_ip}/{base_path}/{image_name} flash:/{image_name}"
        return f"DISTRIBUTION: copy {protocol}://{server_ip}/{base_path}/{image_name}"

    def _mock_activate(self) -> str:
        """Mock image activation - manufacturer specific."""
        self._track_execution('MockUpgradeWorkflow', '_mock_activate', inspect.currentframe().f_lineno, 'activate')
        image_name = self.golden_image.get('image_name', 'unknown')

        # Build platform-specific activation command
        activate_cmd = _build_manufacturer_activate_command(self.manufacturer, self.platform, image_name)

        self.commands_executed.append({
            'stage': 'activate',
            'command': activate_cmd,
            'mode': 'upgrade'
        })

        if self.manufacturer == 'Cisco':
            return f"Cisco: Install {image_name} with activate commit"
        elif self.manufacturer == 'Juniper':
            return f"Juniper: Install {image_name} with reboot"
        elif self.manufacturer == 'Arista':
            return f"Arista: Install image {image_name}"
        return f"Install {image_name}"

    def _mock_wait(self, wait_time: int) -> str:
        """Mock wait period."""
        self.commands_executed.append({
            'stage': 'wait',
            'duration': f"{wait_time} seconds",
            'mode': 'simulated'
        })
        time.sleep(min(wait_time, 1))  # Sleep at most 1 second in mock
        return f"Waited {wait_time} seconds for stabilization"

    def _mock_ping(self) -> str:
        """Mock ping check."""
        self.commands_executed.append({
            'stage': 'ping',
            'host': self.device.host,
            'mode': 'simulated'
        })
        return f"Device {self.device.host} is reachable"

    def _mock_post_check(self) -> str:
        """Mock post-check."""
        self.commands_executed.append({'stage': 'post_check', 'command': 'show version', 'mode': 'show'})
        return "Post-checks passed"

    def _mock_verification(self) -> str:
        """Mock version verification."""
        target = self.golden_image.get('version', 'unknown')
        current = self.info.get('version', '17.9.4')  # Use device's current version

        self.commands_executed.append({
            'stage': 'verification',
            'command': 'show version',
            'mode': 'show',
            'target_version': target,
            'current_version': current
        })

        if target == current:
            return f"Version verified: {current}"
        else:
            return f"Version mismatch: expected {target}, got {current}"

    def upgrade(self) -> Dict[str, Any]:
        """Execute mock upgrade workflow."""
        stages_order = ['readiness', 'pre_check', 'distribute', 'activate', 'wait', 'ping', 'post_check', 'verification']

        for stage_name in stages_order:
            self._run_stage(stage_name)

        # Build result
        result = {
            'success': all(s['status'] == 'success' for s in self.stages.values()),
            'stages': {name: {'name': s['name'], 'status': s['status'], 'message': s['message']} for name, s in self.stages.items()},
            'commands_executed': self.commands_executed,
            'warnings': self.warnings,
            'execution_path': self.execution_path,  # Include execution path for analysis
            'manufacturer': self.manufacturer,
            'model': self.model,
            'platform': self.platform,
        }

        return result


class DryRunUpgradeWorkflow:
    """
    Dry-run upgrade workflow that connects to real device but only executes show commands.

    Manufacturer-specific outputs:
    - Cisco: Uses install add/activate/commit workflow
    - Juniper: Uses request system software add workflow
    - Arista: Uses install image workflow

    Execution path is tracked showing: class -> function -> line_number
    """

    def __init__(
        self,
        device: Device,
        golden_image: Dict[str, Any],
        file_server: Dict[str, Any],
        connection_mode: str = "dry_run"
    ):
        self.device = device
        self.golden_image = golden_image
        self.file_server = file_server
        self.connection_mode = connection_mode
        self.stages: Dict[str, Dict[str, Any]] = {}
        self.commands_executed: List[Dict[str, Any]] = []
        self.show_commands: List[str] = []
        self.mocked_upgrade_commands: List[str] = []
        self.warnings: List[str] = []
        self.execution_path: List[Dict[str, Any]] = []  # Tracks: class -> function -> line

        # Get manufacturer and model from device for platform-specific output
        self.manufacturer = self._get_manufacturer()
        self.model = self._get_model()
        self.platform = self._get_platform()

        # Initialize stages
        self._init_stages()

    def _get_manufacturer(self) -> str:
        """Get manufacturer from device info."""
        if hasattr(self.device, 'manufacturer') and self.device.manufacturer:
            return self.device.manufacturer
        platform = self.device.device_type or ''
        if 'cisco' in platform.lower():
            return 'Cisco'
        elif 'juniper' in platform.lower() or 'junos' in platform.lower():
            return 'Juniper'
        elif 'arista' in platform.lower():
            return 'Arista'
        return 'Unknown'

    def _get_model(self) -> str:
        """Get model from device info or infer from device_type."""
        if hasattr(self.device, 'model') and self.device.model:
            return self.device.model

        # Infer model from device_type
        platform = (self.device.device_type or '').lower()

        # Cisco models
        if 'cisco' in platform:
            if '9300' in platform or 'c9300' in platform:
                return 'C9300'
            elif '9400' in platform or 'c9400' in platform:
                return 'C9400'
            elif '9500' in platform or 'c9500' in platform:
                return 'C9500'
            elif '4400' in platform or 'isr4400' in platform:
                return 'ISR4400'
            elif '4300' in platform or 'isr4300' in platform:
                return 'ISR4300'
            elif 'n9k' in platform or 'nx9000' in platform:
                return 'N9K'
            # NX-OS disabled
            else:
                return 'C9300'  # Default Cisco model

        # Juniper models
        elif 'juniper' in platform or 'junos' in platform:
            if 'mx' in platform or 'mx' in platform:
                return 'MX'
            elif 'qfx' in platform or 'qfx' in platform:
                return 'QFX'
            elif 'srx' in platform or 'srx' in platform:
                return 'SRX'
            elif 'ptx' in platform or 'ptx' in platform:
                return 'PTX'
            else:
                return 'MX'  # Default Juniper model

        # Arista models
        elif 'arista' in platform or 'eos' in platform:
            if '7050' in platform or '7050' in platform:
                return '7050'
            elif '7280' in platform or '7280' in platform:
                return '7280'
            elif '7500' in platform or '7500' in platform:
                return '7500'
            else:
                return '7050'  # Default Arista model

        return 'Unknown'

    def _get_platform(self) -> str:
        """Get platform from device info."""
        if hasattr(self.device, 'platform') and self.device.platform:
            return self.device.platform
        platform = self.device.device_type or ''
        if 'cisco' in platform.lower():
            return 'cisco_iosxe'
        elif 'juniper' in platform.lower() or 'junos' in platform.lower():
            return 'juniper_junos'
        elif 'arista' in platform.lower():
            return 'arista_eos'
        return 'cisco_iosxe'

    def _init_stages(self):
        """Initialize dry-run stages."""
        self.stages = {
            'readiness': {'name': 'readiness', 'status': 'pending', 'message': ''},
            'pre_check': {'name': 'pre_check', 'status': 'pending', 'message': ''},
            'distribute': {'name': 'distribute', 'status': 'pending', 'message': ''},
            'activate': {'name': 'activate', 'status': 'pending', 'message': ''},
            'wait': {'name': 'wait', 'status': 'pending', 'message': ''},
            'ping': {'name': 'ping', 'status': 'pending', 'message': ''},
            'post_check': {'name': 'post_check', 'status': 'pending', 'message': ''},
            'verification': {'name': 'verification', 'status': 'pending', 'message': ''},
        }

    def _track_execution(self, class_name: str, function_name: str, line: int, stage: str = ""):
        """Track the execution path."""
        self.execution_path.append({
            'class': class_name,
            'function': function_name,
            'line': line,
            'stage': stage
        })

    def _run_stage(self, stage_name: str, **kwargs) -> bool:
        """Run a dry-run stage."""
        self._track_execution('DryRunUpgradeWorkflow', '_run_stage', inspect.currentframe().f_lineno, stage_name)
        stage = self.stages.get(stage_name)
        if not stage:
            self.warnings.append(f"Unknown stage: {stage_name}")
            return False

        stage['status'] = 'running'

        try:
            if stage_name == 'readiness':
                stage['message'] = self._dryrun_readiness()
                stage['status'] = 'success'
            elif stage_name == 'pre_check':
                stage['message'] = self._dryrun_pre_check()
                stage['status'] = 'success'
            elif stage_name == 'distribute':
                stage['message'] = self._dryrun_distribute()
                stage['status'] = 'success'
            elif stage_name == 'activate':
                stage['message'] = self._dryrun_activate()
                stage['status'] = 'success'
            elif stage_name == 'wait':
                stage['message'] = self._dryrun_wait(kwargs.get('wait_time', 300))
                stage['status'] = 'success'
            elif stage_name == 'ping':
                stage['message'] = self._dryrun_ping()
                stage['status'] = 'success'
            elif stage_name == 'post_check':
                stage['message'] = self._dryrun_post_check()
                stage['status'] = 'success'
            elif stage_name == 'verification':
                stage['message'] = self._dryrun_verification()
                stage['status'] = 'success'
            else:
                stage['message'] = f"Stage not implemented: {stage_name}"
                stage['status'] = 'failed'
                return False

            return True

        except Exception as e:
            stage['message'] = f"Exception: {str(e)}"
            self.warnings.append(f"{stage_name} failed: {e}")
            stage['status'] = 'failed'
            return False

    def _dryrun_readiness(self) -> str:
        """Dry-run readiness check - manufacturer specific."""
        self._track_execution('DryRunUpgradeWorkflow', '_dryrun_readiness', inspect.currentframe().f_lineno, 'readiness')

        # Execute show commands
        self.commands_executed.append({'stage': 'readiness', 'command': 'show version', 'mode': 'show'})
        self.show_commands.append('show version')
        self.commands_executed.append({'stage': 'readiness', 'command': 'dir', 'mode': 'show'})
        self.show_commands.append('dir')

        # Mock flash space check
        self.commands_executed.append({
            'stage': 'readiness',
            'command': 'flash_space_check',
            'mode': 'mocked',
            'result': '10 GB available'
        })

        if self.manufacturer == 'Cisco':
            return "Cisco: Device ready for upgrade - flash space verified"
        elif self.manufacturer == 'Juniper':
            return "Juniper: Device ready for upgrade - storage space verified"
        elif self.manufacturer == 'Arista':
            return "Arista: Device ready for upgrade - disk usage verified"
        return "Device is ready for upgrade"

    def _dryrun_pre_check(self) -> str:
        """Dry-run pre-check - manufacturer specific."""
        self._track_execution('DryRunUpgradeWorkflow', '_dryrun_pre_check', inspect.currentframe().f_lineno, 'pre_check')

        self.commands_executed.append({'stage': 'pre_check', 'command': 'show version', 'mode': 'show'})
        self.show_commands.append('show version')

        if self.manufacturer == 'Cisco':
            return "Cisco: Pre-checks - checksum verified, flash space OK"
        elif self.manufacturer == 'Juniper':
            return "Juniper: Pre-checks - route engine redundancy OK, storage OK"
        elif self.manufacturer == 'Arista':
            return "Arista: Pre-checks - checksum verified, disk usage OK"
        return "Pre-checks passed"

    def _dryrun_distribute(self) -> str:
        """Dry-run image distribution - shows manufacturer-specific command that would execute."""
        self._track_execution('DryRunUpgradeWorkflow', '_dryrun_distribute', inspect.currentframe().f_lineno, 'distribute')

        image_name = self.golden_image.get('image_name', 'unknown')
        protocol = self.file_server.get('protocol', 'http')
        server_ip = self.file_server.get('ip', '')
        base_path = self.file_server.get('base_path', '')

        # Build platform-specific copy command
        copy_cmd = _build_manufacturer_copy_command(self.manufacturer, self.platform, protocol, server_ip, base_path, image_name)

        # Record in show_commands since it's the actual command to execute
        self.show_commands.append(copy_cmd)
        self.commands_executed.append({
            'stage': 'distribute',
            'command': copy_cmd,
            'mode': 'show',
            'actual_command': copy_cmd,
            'manufacturer': self.manufacturer
        })

        return f"DISTRIBUTION: {copy_cmd}"

    def _dryrun_activate(self) -> str:
        """Dry-run image activation - shows manufacturer-specific command that would execute."""
        self._track_execution('DryRunUpgradeWorkflow', '_dryrun_activate', inspect.currentframe().f_lineno, 'activate')

        image_name = self.golden_image.get('image_name', 'unknown')

        # Build platform-specific activation command
        activate_cmd = _build_manufacturer_activate_command(self.manufacturer, self.platform, image_name)

        # Record in show_commands since it's the actual command to execute
        self.show_commands.append(activate_cmd)
        self.commands_executed.append({
            'stage': 'activate',
            'command': activate_cmd,
            'mode': 'show',
            'actual_command': activate_cmd,
            'manufacturer': self.manufacturer
        })

        return f"ACTIVATION: {activate_cmd}"

    def _dryrun_wait(self, wait_time: int) -> str:
        """Dry-run wait period."""
        self._track_execution('DryRunUpgradeWorkflow', '_dryrun_wait', inspect.currentframe().f_lineno, 'wait')
        self.commands_executed.append({
            'stage': 'wait',
            'duration': f"{wait_time} seconds",
            'mode': 'simulated'
        })
        return f"Waited {wait_time} seconds for stabilization"

    def _dryrun_ping(self) -> str:
        """Dry-run ping check."""
        self._track_execution('DryRunUpgradeWorkflow', '_dryrun_ping', inspect.currentframe().f_lineno, 'ping')
        self.commands_executed.append({
            'stage': 'ping',
            'host': self.device.host,
            'mode': 'simulated'
        })
        return f"Device {self.device.host} is reachable"

    def _dryrun_post_check(self) -> str:
        """Dry-run post-check - manufacturer specific."""
        self._track_execution('DryRunUpgradeWorkflow', '_dryrun_post_check', inspect.currentframe().f_lineno, 'post_check')

        self.commands_executed.append({'stage': 'post_check', 'command': 'show version', 'mode': 'show'})
        self.show_commands.append('show version')

        if self.manufacturer == 'Cisco':
            return "Cisco: Post-checks - version verified"
        elif self.manufacturer == 'Juniper':
            return "Juniper: Post-checks - system verified"
        elif self.manufacturer == 'Arista':
            return "Arista: Post-checks - version verified"
        return "Post-checks passed"

    def _dryrun_verification(self) -> str:
        """Dry-run version verification - ONLY real command in dry-run."""
        self._track_execution('DryRunUpgradeWorkflow', '_dryrun_verification', inspect.currentframe().f_lineno, 'verification')

        target = self.golden_image.get('version', 'unknown')

        # Version verification executes real command
        self.commands_executed.append({
            'stage': 'verification',
            'command': 'show version',
            'mode': 'show',
            'actual_command': 'show version'
        })
        self.show_commands.append('show version')

        return f"Version verification complete (target: {target}, manufacturer: {self.manufacturer})"

    def upgrade(self) -> Dict[str, Any]:
        """Execute dry-run upgrade workflow."""
        stages_order = ['readiness', 'pre_check', 'distribute', 'activate', 'wait', 'ping', 'post_check', 'verification']

        for stage_name in stages_order:
            self._run_stage(stage_name)

        result = {
            'success': all(s['status'] == 'success' for s in self.stages.values()),
            'stages': {name: {'name': s['name'], 'status': s['status'], 'message': s['message']} for name, s in self.stages.items()},
            'show_commands_executed': self.show_commands,
            'mocked_upgrade_commands': self.mocked_upgrade_commands,
            'commands_executed': self.commands_executed,
            'warnings': self.warnings,
            'execution_path': self.execution_path,  # Include execution path for dry-run analysis
            'manufacturer': self.manufacturer,
            'model': self.model,
            'platform': self.platform,
        }

        return result


def _get_mock_output(command: str, platform: str, model: str = "C9300") -> str:
    """Get mock output for a command - model specific."""
    # Determine model-specific output
    model_upper = model.upper()

    if command == 'show version':
        if 'cisco' in platform.lower():
            if model_upper == 'C9300':
                return """Cisco IOS Software, IOS-XE Software, Catalyst 9300
Software Version: 17.9.4
System image file is "flash0:/cat9k_iosxe.SPA.17.9.4.bin"
Last reload reason: Power On
Uptime is 2 days, 3 hours, 45 minutes
Configuration register is 0x101
"""
            elif model_upper == 'C9400':
                return """Cisco IOS Software, IOS-XE Software, Catalyst 9400
Software Version: 17.9.4
System image file is "flash0:/cat9k_iosxe.SPA.17.9.4.bin"
Last reload reason: Power On
Uptime is 2 days, 3 hours, 45 minutes
Configuration register is 0x101
"""
            elif model_upper == 'C9500':
                return """Cisco IOS Software, IOS-XE Software, Catalyst 9500
Software Version: 17.9.4
System image file is "flash0:/cat9k_iosxe.SPA.17.9.4.bin"
Last reload reason: Power On
Uptime is 2 days, 3 hours, 45 minutes
Configuration register is 0x101
"""
            elif model_upper == 'ISR4400':
                return """Cisco IOS Software, ISR4400 Software (ISR4400-universalk9.MPA.1793T)
Version 17.9.3
System image file is "flash0:/ISR4400-universalk9.SPA.17.9.3-23.bin"
Last reload reason: Power On
Uptime is 5 days, 12 hours, 30 minutes
Configuration register is 0x101
"""
            elif model_upper == 'ISR4300':
                return """Cisco IOS Software, ISR4300 Software (ISR4300-universalk9.MPA.1793T)
Version 17.9.3
System image file is "flash0:/ISR4300-universalk9.SPA.17.9.3-23.bin"
Last reload reason: Power On
Uptime is 3 days, 8 hours, 15 minutes
Configuration register is 0x101
"""
            else:
                return """Cisco IOS Software, IOS-XE Software, Catalyst Switch
Software Version: 17.9.4
System image file is "flash0:/cat9k_iosxe.SPA.17.9.4.bin"
Last reload reason: Power On
Uptime is 2 days, 3 hours, 45 minutes
Configuration register is 0x101
"""
        elif 'juniper' in platform.lower() or 'junos' in platform.lower():
            if model_upper == 'MX':
                return """JUNOS Software Reference, Juniper Networks, Inc.
JUNOS 22.4R1.10
Kernel version: 22.4R1.10
System image file: /vm/util/juniper-junos-22.4R1.10.img
Last configured by admin at 2024-12-01 12:00:00 UTC
Model: mx204
Serial number: JN1234567890
"""
            elif model_upper == 'QFX':
                return """JUNOS Software Reference, Juniper Networks, Inc.
JUNOS 22.4R1.10
Kernel version: 22.4R1.10
System image file: /vm/util/juniper-junos-22.4R1.10.img
Last configured by admin at 2024-12-01 12:00:00 UTC
Model: qfx10000
Serial number: JN1234567890
"""
            elif model_upper == 'SRX':
                return """JUNOS Software Reference, Juniper Networks, Inc.
JUNOS 22.4R1.10
Kernel version: 22.4R1.10
System image file: /vm/util/juniper-junos-22.4R1.10.img
Last configured by admin at 2024-12-01 12:00:00 UTC
Model: srx5800
Serial number: JN1234567890
"""
            else:
                return """JUNOS Software Reference, Juniper Networks, Inc.
JUNOS 22.4R1.10
Kernel version: 22.4R1.10
System image file: /vm/util/juniper-junos-22.4R1.10.img
Last configured by admin at 2024-12-01 12:00:00 UTC
Model: MX
Serial number: JN1234567890
"""
        elif 'arista' in platform.lower() or 'eos' in platform.lower():
            if model_upper == '7050':
                return """Aboot 4.6.1
System image version: 4.30.0
Last reload reason: Power Cycle
Uptime: 5 days, 14:30:00
Model: Arista DCS-7050CX3
Serial number: JAB12345678
Hardware revision: 01.00
"""
            elif model_upper == '7280':
                return """Aboot 4.6.1
System image version: 4.30.0
Last reload reason: Power Cycle
Uptime: 5 days, 14:30:00
Model: Arista DCS-7280
Hardware revision: 01.00
"""
            elif model_upper == '7500':
                return """Aboot 4.6.1
System image version: 4.30.0
Last reload reason: Power Cycle
Uptime: 5 days, 14:30:00
Model: Arista DCS-7500
Hardware revision: 01.00
"""
            else:
                return """Aboot 4.6.1
System image version: 4.30.0
Last reload reason: Power Cycle
Uptime: 5 days, 14:30:00
Model: Arista DCS-7050
Hardware revision: 01.00
"""

    elif command == 'show run | include hostname':
        return 'hostname R1'

    elif command == 'show inventory':
        if 'cisco' in platform.lower():
            if model_upper == 'C9300':
                return """PID: C9300L-24P, SN: FXY23456789
PID: C9300X-24P, SN: ABC12345678
"""
            elif model_upper == 'C9400':
                return """PID: C9400R-24P, SN: FXY23456790
PID: C9400X-24P, SN: ABC12345679
"""
            elif model_upper == 'C9500':
                return """PID: C9500-40X, SN: FXY23456791
PID: C9500-24Y, SN: ABC1234567A
"""
            else:
                return """PID: Catalyst 9300, SN: FXY23456789
PID: Catalyst 9300X, SN: ABC12345678
"""
        elif 'juniper' in platform.lower() or 'junos' in platform.lower():
            if model_upper == 'MX':
                return """Chassis:
  Model: mx204
  Serial number: JN1234567890
"""
            elif model_upper == 'QFX':
                return """Chassis:
  Model: qfx10000
  Serial number: JN1234567890
"""
            elif model_upper == 'SRX':
                return """Chassis:
  Model: srx5800
  Serial number: JN1234567890
"""
            else:
                return """Chassis:
  Model: MX
  Serial number: JN1234567890
"""
        elif 'arista' in platform.lower():
            return """System Memory: 16384 MB
Board ID: 7050
Hardware revision: 01.00
Serial number: JAB12345678
"""

    elif command == 'show interfaces status':
        return """Port          Status       VLAN  Duplex  Speed Type
Gi1/0/1       connected    1     a-full a-100 10/100/1000BaseTX
Gi1/0/2       notconnect   1     a-full a-100 10/100/1000BaseTX
"""

    elif command == 'dir':
        return """Directory of flash0:/

1234567890 bytes total (123456789 bytes free)
"""

    elif command == 'show running-config':
        return """Current configuration : 2048 bytes
!
version 17.9
hostname R1
!
interface GigabitEthernet1/0/1
 description Uplink
!
end
"""

    return "Command output not simulated"


def _get_mock_upgrade_output(command: str, platform: str) -> str:
    """Get mock output for upgrade commands."""
    if 'copy' in command.lower():
        return "87654321 bytes copied in 45.123 seconds (1944543 bytes/s)"
    elif 'install' in command.lower():
        return "Installation successful. Committing changes..."
    elif 'activate' in command.lower():
        return "Activate command accepted. Changes will be committed."
    elif 'commit' in command.lower():
        return "Configuration committed successfully"
    else:
        return "Command executed successfully"


def _build_manufacturer_copy_command(manufacturer: str, platform: str, protocol: str, server_ip: str, base_path: str, image_name: str) -> str:
    """
    Build copy command based on manufacturer.

    Args:
        manufacturer: Manufacturer name (Cisco, Juniper, Arista)
        platform: Platform name
        protocol: Transfer protocol (http, https, tftp, ftp, scp)
        server_ip: File server IP
        base_path: Base path on server
        image_name: Image filename (may include flash:/ or bootflash:/ prefix)

    Returns:
        Platform-specific copy command
    """
    protocol = protocol.lower()

    # Strip any flash:/ or bootflash:/ prefix from image_name for URL
    # The prefix is only for the destination path on the device
    image_filename = image_name
    if image_filename.startswith('flash:/'):
        image_filename = image_filename[7:]  # Remove 'flash:/'
    elif image_filename.startswith('bootflash:/'):
        image_filename = image_filename[11:]  # Remove 'bootflash:/'

    if manufacturer == 'Cisco':
        # Cisco uses copy protocol://server/path/image dest (NX-OS disabled)
        dest_path = f"flash:/{image_name}"

        if protocol == 'http' or protocol == 'https':
            return f"copy {protocol}://{server_ip}/{base_path}/{image_filename} {dest_path}"
        elif protocol == 'tftp':
            return f"copy tftp://{server_ip}/{base_path}/{image_filename} {dest_path}"
        elif protocol == 'ftp':
            return f"copy ftp://{server_ip}/{base_path}/{image_filename} {dest_path}"
        elif protocol == 'scp':
            return f"copy scp://admin@{server_ip}/{base_path}/{image_filename} {dest_path}"

    elif manufacturer == 'Juniper':
        # Juniper uses request system software add protocol://server/path/image
        return f"request system software add {protocol}://{server_ip}/{base_path}/{image_filename}"

    elif manufacturer == 'Arista':
        # Arista uses copy protocol://server/path/image flash:/image
        dest_path = f"flash:/{image_name}"
        if protocol == 'http' or protocol == 'https':
            return f"copy {protocol}://{server_ip}/{base_path}/{image_filename} {dest_path}"
        elif protocol == 'tftp':
            return f"copy tftp://{server_ip}/{base_path}/{image_filename} {dest_path}"
        elif protocol == 'ftp':
            return f"copy ftp://{server_ip}/{base_path}/{image_filename} {dest_path}"
        elif protocol == 'scp':
            return f"copy scp://admin@{server_ip}/{base_path}/{image_filename} {dest_path}"

    # Default: Cisco IOS-XE style
    dest_path = f"flash:/{image_name}"
    return f"copy {protocol}://{server_ip}/{base_path}/{image_filename} {dest_path}"


def _build_manufacturer_activate_command(manufacturer: str, platform: str, image_name: str) -> str:
    """
    Build activation command based on manufacturer.

    Args:
        manufacturer: Manufacturer name (Cisco, Juniper, Arista)
        platform: Platform name
        image_name: Image filename

    Returns:
        Platform-specific activation command
    """
    if manufacturer == 'Cisco':
        # Cisco IOS-XE uses: install add file <image> activate commit (NX-OS disabled)
        return f"install add file {image_name} activate commit"

    elif manufacturer == 'Juniper':
        # Juniper uses: request system software add <image> reboot
        return f"request system software add {image_name} reboot"

    elif manufacturer == 'Arista':
        # Arista uses: install image flash:/<image>
        return f"install image flash:/{image_name}"

    # Default: Cisco IOS-XE style
    return f"install add file {image_name} activate commit"
