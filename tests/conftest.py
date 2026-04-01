"""Test fixtures for simple-upgrade package."""

import pytest


class MockConnection:
    """Mock connection object for testing."""
    def __init__(self, *args, **kwargs):
        self.connected = True
        self.platform = kwargs.get('platform', 'cisco_ios')

    def open(self):
        self.connected = True

    def close(self):
        self.connected = False

    def send_command(self, command):
        """Return mock output based on command."""
        outputs = {
            'show version': """Cisco IOS Software, IOS-XE Software, Catalyst 9300 Series
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
        }
        return outputs.get(command, '')

    def send_configs(self, commands):
        return "Configuration applied"


class MockDevice:
    """Mock Device object for testing."""
    def __init__(self, *args, **kwargs):
        self.host = kwargs.get('host', '192.168.1.1')
        self.username = kwargs.get('username', 'admin')
        self.password = kwargs.get('password', 'password')
        self.device_type = kwargs.get('device_type', 'cisco_xe')
        self._connected = False
        self._connection = None

    def connect(self):
        self._connection = MockConnection(host=self.host, platform=self.device_type)
        self._connected = True
        return True

    def disconnect(self):
        if self._connection:
            self._connection.close()
        self._connected = False
        self._connection = None

    def send_command(self, command):
        if not self._connected:
            raise Exception("Not connected")
        return self._connection.send_command(command)


# Test fixtures
@pytest.fixture
def mock_device():
    """Return a mock device for testing."""
    device = MockDevice(host='192.168.1.1', device_type='cisco_xe')
    device.connect()
    yield device
    device.disconnect()


@pytest.fixture
def sample_pre_checks():
    """Return sample pre-upgrade check results."""
    return {
        'pre_upgrade': {
            'ping': {'status': True, 'message': '192.168.1.1 is reachable'},
            'current_version': {'status': True, 'current_version': '17.9.3', 'message': 'Current version: 17.9.3'},
            'free_space': {'status': True, 'free_bytes': 1000000000, 'message': 'Free space: 1000000000 bytes'},
            'running_config': {'status': True, 'has_errors': False, 'message': 'Running configuration is intact'},
            'backup_config': {'status': True, 'backup_file': 'config_20241201_120000.txt', 'message': 'Configuration retrieved'},
            'hardware_health': {'status': True, 'has_errors': False, 'has_issues': False, 'message': 'Hardware health OK'},
        },
        'status': 'passed',
    }


@pytest.fixture
def sample_post_checks():
    """Return sample post-upgrade check results."""
    return {
        'post_upgrade': {
            'ping': {'status': True, 'message': '192.168.1.1 is reachable'},
            'version': {'status': True, 'current_version': '17.9.4', 'message': 'Current version: 17.9.4'},
            'uptime': {'status': True, 'uptime': '2 hours, 15 minutes', 'message': 'Uptime: 2 hours, 15 minutes'},
            'configuration': {'status': True, 'has_errors': False, 'message': 'Configuration intact'},
            'hardware_health': {'status': True, 'has_errors': False, 'has_issues': False, 'message': 'Hardware health OK'},
            'running_config': {'status': True, 'has_errors': False, 'message': 'Running configuration is intact'},
            'services': {'status': True, 'message': 'Services are running'},
        },
        'status': 'passed',
    }
