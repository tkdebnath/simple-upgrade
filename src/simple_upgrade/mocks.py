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
"""

import time
import re
from typing import Optional, Dict, Any, List
from .device import Device, DeviceConnectionError
from .connection_manager import ConnectionManager, ConnectionError
from .sync import SyncManager
from .manufacturers import cisco, juniper, arista


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

    def send_command(self, command: str) -> str:
        """Simulate sending a command and return mock output."""
        self.commands_executed.append({'command': command, 'mode': 'show'})
        return _get_mock_output(command, self.platform)

    def send_configs(self, commands: List[str]) -> str:
        """Simulate sending configuration commands."""
        for cmd in commands:
            self.commands_executed.append({'command': cmd, 'mode': 'config'})
        return "Configuration applied (mock)"

    def execute(self, command: str) -> str:
        """Execute command (unicon-style)."""
        self.commands_executed.append({'command': command, 'mode': 'execute'})
        return _get_mock_output(command, self.platform)


class DryRunConnection:
    """
    Dry-run connection that connects to real device but only executes show commands.

    All upgrade commands (copy, install, activate) are mocked.
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

    def open(self):
        """Open real connection for show commands."""
        if hasattr(self.real_connection, 'open'):
            self.real_connection.open()
        self.connected = True

    def close(self):
        """Close real connection."""
        if hasattr(self.real_connection, 'close'):
            self.real_connection.close()
        self.connected = False

    def send_command(self, command: str) -> str:
        """Send command - real for show, mocked for upgrade."""
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

        # Initialize stages
        self._init_stages()

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

    def _run_stage(self, stage_name: str, **kwargs) -> bool:
        """Run a mock stage."""
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
        """Mock readiness check."""
        self.commands_executed.append({'stage': 'readiness', 'command': 'show version', 'mode': 'show'})
        self.commands_executed.append({'stage': 'readiness', 'command': 'dir', 'mode': 'show'})
        return "Device is ready for upgrade"

    def _mock_pre_check(self) -> str:
        """Mock pre-check."""
        self.commands_executed.append({'stage': 'pre_check', 'command': 'show version', 'mode': 'show'})
        return "Pre-checks passed"

    def _mock_distribute(self) -> str:
        """Mock image distribution."""
        image_name = self.golden_image.get('image_name', 'unknown')
        protocol = self.file_server.get('protocol', 'http')
        server_ip = self.file_server.get('ip', '')
        base_path = self.file_server.get('base_path', '')

        # Build the actual copy command that would be executed
        copy_cmd = f"copy {protocol}://{server_ip}/{base_path}/{image_name} flash:/{image_name}"

        # Record the actual command that would be executed
        self.commands_executed.append({
            'stage': 'distribute',
            'command': copy_cmd,
            'mode': 'upgrade',
            'actual_command': copy_cmd  # The actual command that would execute
        })

        return f"DISTRIBUTION: copy {protocol}://{server_ip}/{base_path}/{image_name} flash:/{image_name}"

    def _mock_activate(self) -> str:
        """Mock image activation."""
        image_name = self.golden_image.get('image_name', 'unknown')

        # Cisco IOS-XE activation
        activate_cmd = f"install add file {image_name} activate commit"
        self.commands_executed.append({
            'stage': 'activate',
            'command': activate_cmd,
            'mode': 'upgrade'
        })

        return f"Image {image_name} would be activated"

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
        current = '17.9.4'  # Would be from post-upgrade

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
        }

        return result


class DryRunUpgradeWorkflow:
    """
    Dry-run upgrade workflow that connects to real device but only executes show commands.
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

        self._init_stages()

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

    def _run_stage(self, stage_name: str, **kwargs) -> bool:
        """Run a dry-run stage."""
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
        """Dry-run readiness check."""
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

        return "Device is ready for upgrade"

    def _dryrun_pre_check(self) -> str:
        """Dry-run pre-check."""
        self.commands_executed.append({'stage': 'pre_check', 'command': 'show version', 'mode': 'show'})
        self.show_commands.append('show version')
        return "Pre-checks passed"

    def _dryrun_distribute(self) -> str:
        """Dry-run image distribution - shows actual command that would execute."""
        image_name = self.golden_image.get('image_name', 'unknown')
        protocol = self.file_server.get('protocol', 'http')
        server_ip = self.file_server.get('ip', '')
        base_path = self.file_server.get('base_path', '')

        # Build the actual copy command
        copy_cmd = f"copy {protocol}://{server_ip}/{base_path}/{image_name} flash:/{image_name}"

        # Record in show_commands since it's the actual command to execute
        self.show_commands.append(copy_cmd)
        self.commands_executed.append({
            'stage': 'distribute',
            'command': copy_cmd,
            'mode': 'show',
            'actual_command': copy_cmd  # The actual command that would execute
        })

        return f"DISTRIBUTION COMMAND: {copy_cmd}"

    def _dryrun_activate(self) -> str:
        """Dry-run image activation - shows actual command that would execute."""
        image_name = self.golden_image.get('image_name', 'unknown')

        # Cisco IOS-XE activation command
        activate_cmd = f"install add file {image_name} activate commit"

        # Record in show_commands since it's the actual command to execute
        self.show_commands.append(activate_cmd)
        self.commands_executed.append({
            'stage': 'activate',
            'command': activate_cmd,
            'mode': 'show',
            'actual_command': activate_cmd  # The actual command that would execute
        })

        return f"ACTIVATION COMMAND: {activate_cmd}"

    def _dryrun_wait(self, wait_time: int) -> str:
        """Dry-run wait period."""
        self.commands_executed.append({
            'stage': 'wait',
            'duration': f"{wait_time} seconds",
            'mode': 'simulated'
        })
        return f"Waited {wait_time} seconds for stabilization"

    def _dryrun_ping(self) -> str:
        """Dry-run ping check."""
        self.commands_executed.append({
            'stage': 'ping',
            'host': self.device.host,
            'mode': 'simulated'
        })
        return f"Device {self.device.host} is reachable"

    def _dryrun_post_check(self) -> str:
        """Dry-run post-check."""
        self.commands_executed.append({'stage': 'post_check', 'command': 'show version', 'mode': 'show'})
        self.show_commands.append('show version')
        return "Post-checks passed"

    def _dryrun_verification(self) -> str:
        """Dry-run version verification - ONLY real command in dry-run."""
        target = self.golden_image.get('version', 'unknown')

        # Version verification executes real command
        self.commands_executed.append({
            'stage': 'verification',
            'command': 'show version',
            'mode': 'show',
            'actual_command': 'show version'
        })
        self.show_commands.append('show version')

        return f"Version verification complete (target: {target})"

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
        }

        return result


def _get_mock_output(command: str, platform: str) -> str:
    """Get mock output for a command."""
    outputs = {
        'show version': f"""Cisco IOS Software, IOS-XE Software, Catalyst 9300
Software Version: 17.9.4
System image file is "flash0:/cat9k_iosxe.SPA.17.9.4.bin"
Last reload reason: Power On
Uptime is 2 days, 3 hours, 45 minutes
Configuration register is 0x101
""",
        'show run | include hostname': 'hostname R1',
        'show inventory': """PID: C9300L-24P, SN: FXY23456789
PID: C9300X-24P, SN: ABC12345678
""",
        'show interfaces status': """Port          Status       VLAN  Duplex  Speed Type
Gi1/0/1       connected    1     a-full a-100 10/100/1000BaseTX
Gi1/0/2       notconnect   1     a-full a-100 10/100/1000BaseTX
""",
        'dir': """Directory of flash0:/

1234567890 bytes total (123456789 bytes free)
""",
        'show running-config': """Current configuration : 2048 bytes
!
version 17.9
hostname R1
!
interface GigabitEthernet1/0/1
 description Uplink
!
end
""",
    }
    return outputs.get(command, "Command output not simulated")


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
