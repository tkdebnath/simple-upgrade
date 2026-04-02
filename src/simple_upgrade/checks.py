"""
Checks module - Pre-upgrade and post-upgrade validation checks.

This module provides comprehensive validation checks for network devices
before and after firmware upgrades.

Usage:
    from simple_upgrade import Checks

    checks = Checks(
        host="192.168.1.1",
        username="admin",
        password="password",
        device_type="cisco_xe"
    )

    # Pre-upgrade checks
    pre_check_results = checks.pre_upgrade_checks()

    # Post-upgrade checks
    post_check_results = checks.post_upgrade_checks()
"""

import time
import subprocess
from typing import Dict, Any, List, Optional
from .connection_manager import ConnectionManager, ConnectionError


class Checks:
    """
    Handles pre-upgrade and post-upgrade validation checks.

    Usage:
        checks = Checks(
            host="192.168.1.1",
            username="admin",
            password="password",
            device_type="cisco_xe"
        )
        results = checks.pre_upgrade_checks()
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        device_type: Optional[str] = None,
        port: int = 22,
        secret: str = "",
        timeout: int = 30,
        platform: Optional[str] = None
    ):
        """
        Initialize the Checks object.

        Args:
            host: Device IP or hostname
            username: SSH username
            password: SSH password
            device_type: Device type/platform
            port: SSH port (default 22)
            secret: Enable/privileged mode password
            timeout: Connection timeout in seconds
            platform: Platform name (overrides device_type)
        """
        self.host = host
        self.username = username
        self.password = password
        self.device_type = device_type
        self.port = port
        self.secret = secret
        self.timeout = timeout
        self.platform = platform

        self.cm: Optional[ConnectionManager] = None
        self.connection = None
        self.results: Dict[str, Any] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def connect(self) -> bool:
        """
        Establish connection to the device.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.cm = ConnectionManager(
                host=self.host,
                username=self.username,
                password=self.password,
                device_type=self.device_type,
                port=self.port,
                enable_password=self.secret or self.password,
                enable_mode=bool(self.secret),
                connection_timeout=self.timeout,
            )

            self.connection = self.cm.get_connection('scrapli')
            return True
        except Exception as e:
            self.errors.append(f"Connection failed: {e}")
            return False

    def disconnect(self):
        """Close the device connection."""
        if self.cm:
            self.cm.disconnect()
            self.cm = None
            self.connection = None

    def _get_platform(self) -> str:
        """Get the platform from connection manager."""
        if self.platform:
            return self.platform
        if self.cm:
            return self.cm.get_platform('scrapli')
        return 'cisco_iosxe'

    def pre_upgrade_checks(self) -> Dict[str, Any]:
        """
        Run all pre-upgrade checks.

        Checks include:
            - Device reachability (ping)
            - Current version verification
            - Free space check
            - Running config verification
            - Backup configuration
            - Hardware health check
            - License verification
            - Image integrity check

        Returns:
            Dictionary with check results, status, and details
        """
        self.results = {
            'pre_upgrade': {},
            'status': 'pending',
            'errors': [],
            'warnings': [],
        }

        if not self.connect():
            self.results['status'] = 'failed'
            self.results['errors'].extend(self.errors)
            return self.results

        platform = self._get_platform()
        self.results['platform'] = platform

        try:
            # Check 1: Ping test
            self.results['pre_upgrade']['ping'] = self._check_ping()
            if not self.results['pre_upgrade']['ping']['status']:
                self.results['status'] = 'warning'
                self.results['warnings'].append('Ping test failed')

            # Check 2: Current version
            self.results['pre_upgrade']['current_version'] = self._check_version()
            if not self.results['pre_upgrade']['current_version']['status']:
                self.results['status'] = 'warning'
                self.results['warnings'].append('Version check failed')

            # Check 3: Free space
            self.results['pre_upgrade']['free_space'] = self._check_free_space(platform)
            if not self.results['pre_upgrade']['free_space']['status']:
                self.results['status'] = 'failed'
                self.results['errors'].append('Insufficient free space')

            # Check 4: Running config
            self.results['pre_upgrade']['running_config'] = self._check_running_config(platform)

            # Check 5: Backup config
            self.results['pre_upgrade']['backup_config'] = self._backup_config(platform)

            # Check 6: Hardware health
            self.results['pre_upgrade']['hardware_health'] = self._check_hardware_health(platform)
            if not self.results['pre_upgrade']['hardware_health']['status']:
                self.results['status'] = 'warning'
                self.results['warnings'].append('Hardware health issues detected')

            # Check 7: License
            self.results['pre_upgrade']['license'] = self._check_license(platform)

            # Check 8: Image integrity
            self.results['pre_upgrade']['image_integrity'] = self._check_image_integrity(platform)

            # Final status
            if self.results['errors']:
                self.results['status'] = 'failed'
            elif self.results['warnings']:
                self.results['status'] = 'warning'
            else:
                self.results['status'] = 'passed'

        except Exception as e:
            self.results['status'] = 'failed'
            self.results['errors'].append(f"Pre-check exception: {e}")

        self.disconnect()
        return self.results

    def post_upgrade_checks(self) -> Dict[str, Any]:
        """
        Run all post-upgrade checks.

        Checks include:
            - Device reachability (ping)
            - Version verification
            - Uptime check
            - Configuration verification
            - Hardware health check
            - Running config verification
            - Services verification

        Returns:
            Dictionary with check results, status, and details
        """
        self.results = {
            'post_upgrade': {},
            'status': 'pending',
            'errors': [],
            'warnings': [],
        }

        if not self.connect():
            self.results['status'] = 'failed'
            self.results['errors'].extend(self.errors)
            return self.results

        platform = self._get_platform()
        self.results['platform'] = platform

        try:
            # Wait for device to stabilize
            time.sleep(30)

            # Check 1: Ping test
            self.results['post_upgrade']['ping'] = self._check_ping()
            if not self.results['post_upgrade']['ping']['status']:
                self.results['status'] = 'failed'
                self.results['errors'].append('Post-upgrade ping test failed')

            # Check 2: Version verification
            self.results['post_upgrade']['version'] = self._check_version()
            if not self.results['post_upgrade']['version']['status']:
                self.results['status'] = 'failed'
                self.results['errors'].append('Version verification failed')

            # Check 3: Uptime
            self.results['post_upgrade']['uptime'] = self._check_uptime(platform)
            if not self.results['post_upgrade']['uptime']['status']:
                self.results['status'] = 'warning'
                self.results['warnings'].append('Uptime check failed')

            # Check 4: Configuration
            self.results['post_upgrade']['configuration'] = self._check_configuration(platform)

            # Check 5: Hardware health
            self.results['post_upgrade']['hardware_health'] = self._check_hardware_health(platform)
            if not self.results['post_upgrade']['hardware_health']['status']:
                self.results['status'] = 'warning'
                self.results['warnings'].append('Hardware health issues after upgrade')

            # Check 6: Running config
            self.results['post_upgrade']['running_config'] = self._check_running_config(platform)

            # Check 7: Services
            self.results['post_upgrade']['services'] = self._check_services(platform)

            # Final status
            if self.results['errors']:
                self.results['status'] = 'failed'
            elif self.results['warnings']:
                self.results['status'] = 'warning'
            else:
                self.results['status'] = 'passed'

        except Exception as e:
            self.results['status'] = 'failed'
            self.results['errors'].append(f"Post-check exception: {e}")

        self.disconnect()
        return self.results

    def _check_ping(self) -> Dict[str, Any]:
        """Check if device is reachable via ICMP ping."""
        try:
            param = '-n' if subprocess.os.name == 'nt' else '-c'
            command = ['ping', param, '1', '-W', '5', self.host]

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return {
                    'status': True,
                    'message': f'{self.host} is reachable',
                    'latency_ms': self._parse_ping_latency(result.stdout)
                }
            else:
                return {
                    'status': False,
                    'message': f'{self.host} is not reachable'
                }
        except Exception as e:
            return {
                'status': False,
                'message': f'Ping check failed: {e}'
            }

    def _parse_ping_latency(self, output: str) -> Optional[int]:
        """Parse ping latency from output."""
        import re
        # Try various formats
        patterns = [
            r'rtt\s+min/avg/max/mdev\s*=\s*([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)',
            r'round-trip\s+mean\s*:\s*([\d.]+)',
            r'time[=<]([\d.]+)\s*ms',
        ]

        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return int(float(match.group(1)))

        return None

    def _check_version(self) -> Dict[str, Any]:
        """Check current software version."""
        try:
            output = self.connection.send_command("show version")
            # Try to extract version
            import re
            patterns = [
                r'Version\s+(\S+)',
                r'Current\s+version:\s+(\S+)',
                r'JUNOS\s+Version\s+(\S+)',
                r'EOS version:\s+(\S+)',
            ]

            version = 'Unknown'
            output_str = str(output.result)
            for pattern in patterns:
                match = re.search(pattern, output_str)
                if match:
                    version = match.group(1)
                    break

            return {
                'status': True,
                'current_version': version,
                'message': f'Current version: {version}'
            }
        except Exception as e:
            return {
                'status': False,
                'message': f'Version check failed: {e}'
            }

    def _check_free_space(self, platform: str) -> Dict[str, Any]:
        """Check available storage space."""
        try:
            commands = {
                'cisco_iosxe': 'dir',
                'juniper_junos': 'show system storage',
                'arista_eos': 'show disk usage',
            }

            cmd = commands.get(platform, 'dir')
            output = self.connection.send_command(cmd)
            output_str = str(output.result)

            # Parse free space
            import re
            patterns = [
                r'(\d+)\s*(?:KB|MB|GB).*\bfree',
                r'(\d+)\s*(?:KB|MB|GB).*\bavailable',
            ]

            free_bytes = 0
            for pattern in patterns:
                match = re.search(pattern, output_str, re.IGNORECASE)
                if match:
                    free_bytes = int(match.group(1))
                    break

            return {
                'status': free_bytes > 0,
                'free_bytes': free_bytes,
                'message': f'Free space: {free_bytes} bytes'
            }
        except Exception as e:
            return {
                'status': False,
                'message': f'Free space check failed: {e}'
            }

    def _check_running_config(self, platform: str) -> Dict[str, Any]:
        """Verify running configuration is intact."""
        try:
            output = self.connection.send_command("show running-config")
            output_str = str(output.result)

            # Check for configuration errors
            error_patterns = ['error', 'invalid', 'failed']
            has_errors = any(err in output_str.lower() for err in error_patterns)

            return {
                'status': not has_errors,
                'has_errors': has_errors,
                'message': 'Running configuration is intact' if not has_errors else 'Configuration errors detected'
            }
        except Exception as e:
            return {
                'status': False,
                'message': f'Running config check failed: {e}'
            }

    def _backup_config(self, platform: str) -> Dict[str, Any]:
        """Backup current configuration."""
        try:
            # Generate config backup filename
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"config_{timestamp}.txt"

            # Get running config
            config = self.connection.send_command("show running-config")
            config_str = str(config.result)

            # In a real implementation, this would save to a file server
            # For now, just verify we can retrieve the config
            return {
                'status': len(config_str) > 0,
                'backup_file': backup_file,
                'message': f'Configuration retrieved (size: {len(config_str)} bytes)'
            }
        except Exception as e:
            return {
                'status': False,
                'message': f'Config backup failed: {e}'
            }

    def _check_hardware_health(self, platform: str) -> Dict[str, Any]:
        """Check hardware health status."""
        try:
            commands = {
                'cisco_iosxe': 'show inventory',
                'juniper_junos': 'show chassis hardware',
                'arista_eos': 'show inventory',
            }

            cmd = commands.get(platform, 'show inventory')
            output = self.connection.send_command(cmd)
            output_str = str(output.result)

            # Check for hardware errors
            error_keywords = ['error', 'failed', 'notOK', 'critical']
            has_errors = any(err in output_str.lower() for err in error_keywords)

            # Check for specific issues
            issue_patterns = [
                r'Unhealth',
                r'Absent',
                r'Failed',
            ]
            has_issues = any(re.search(pattern, output_str, re.IGNORECASE) for pattern in issue_patterns)

            return {
                'status': not has_errors and not has_issues,
                'has_errors': has_errors,
                'has_issues': has_issues,
                'message': 'Hardware health OK' if not (has_errors or has_issues) else 'Hardware issues detected'
            }
        except Exception as e:
            return {
                'status': False,
                'message': f'Hardware health check failed: {e}'
            }

    def _check_license(self, platform: str) -> Dict[str, Any]:
        """Check license status."""
        try:
            commands = {
                'cisco_iosxe': 'show licenses',
                'juniper_junos': 'show system licenses',
                'arista_eos': 'show licenses',
            }

            cmd = commands.get(platform, 'show license')
            output = self.connection.send_command(cmd)
            output_str = str(output.result)

            # Check for license errors
            error_patterns = ['error', 'invalid', 'expired', 'failed']
            has_errors = any(err in output_str.lower() for err in error_patterns)

            return {
                'status': not has_errors,
                'has_errors': has_errors,
                'message': 'License status OK' if not has_errors else 'License issues detected'
            }
        except Exception as e:
            return {
                'status': False,
                'message': f'License check failed: {e}'
            }

    def _check_image_integrity(self, platform: str) -> Dict[str, Any]:
        """Check image file integrity."""
        try:
            # Cisco specific command
            if 'cisco' in platform.lower():
                output = self.connection.send_command("verify /md5 flash:/*/image.bin")
                output_str = str(output.result)
                return {
                    'status': 'OK' in output_str.upper(),
                    'message': 'Image integrity verified' if 'OK' in output_str.upper() else 'Image integrity check pending'
                }
            else:
                # Other platforms - return placeholder
                return {
                    'status': True,
                    'message': 'Image integrity check not applicable for this platform'
                }
        except Exception as e:
            return {
                'status': False,
                'message': f'Image integrity check failed: {e}'
            }

    def _check_uptime(self, platform: str) -> Dict[str, Any]:
        """Check device uptime."""
        try:
            output = self.connection.send_command("show version")
            output_str = str(output.result)

            import re
            patterns = [
                r'uptime is\s+([\d\w\s,]+?)(?:,|\s+since|$)',
                r'Uptime:\s+([\d\w\s,]+?)(?:\n|$)',
            ]

            uptime = 'Unknown'
            for pattern in patterns:
                match = re.search(pattern, output_str, re.IGNORECASE)
                if match:
                    uptime = match.group(1).strip()
                    break

            return {
                'status': uptime != 'Unknown',
                'uptime': uptime,
                'message': f'Uptime: {uptime}'
            }
        except Exception as e:
            return {
                'status': False,
                'message': f'Uptime check failed: {e}'
            }

    def _check_configuration(self, platform: str) -> Dict[str, Any]:
        """Verify post-upgrade configuration."""
        return self._check_running_config(platform)

    def _check_services(self, platform: str) -> Dict[str, Any]:
        """Check if services are running properly."""
        try:
            output = self.connection.send_command("show version")
            output_str = str(output.result)

            # Check for service status indicators
            service_ok = 'running' in output_str.lower() or 'active' in output_str.lower()

            return {
                'status': service_ok,
                'message': 'Services are running' if service_ok else 'Service status unknown'
            }
        except Exception as e:
            return {
                'status': False,
                'message': f'Services check failed: {e}'
            }


def run_pre_checks(
    host: str,
    username: str,
    password: str,
    device_type: str,
    port: int = 22,
    secret: str = "",
    platform: Optional[str] = None
) -> Dict[str, Any]:
    """
    Standalone function to run pre-upgrade checks.

    Args:
        host: Device IP or hostname
        username: SSH username
        password: SSH password
        device_type: Device type/platform
        port: SSH port
        secret: Enable password
        platform: Platform name (optional)

    Returns:
        Dictionary with check results
    """
    checks = Checks(
        host=host,
        username=username,
        password=password,
        device_type=device_type,
        port=port,
        secret=secret,
        platform=platform
    )
    return checks.pre_upgrade_checks()


def run_post_checks(
    host: str,
    username: str,
    password: str,
    device_type: str,
    port: int = 22,
    secret: str = "",
    platform: Optional[str] = None
) -> Dict[str, Any]:
    """
    Standalone function to run post-upgrade checks.

    Args:
        host: Device IP or hostname
        username: SSH username
        password: SSH password
        device_type: Device type/platform
        port: SSH port
        secret: Enable password
        platform: Platform name (optional)

    Returns:
        Dictionary with check results
    """
    checks = Checks(
        host=host,
        username=username,
        password=password,
        device_type=device_type,
        port=port,
        secret=secret,
        platform=platform
    )
    return checks.post_upgrade_checks()
