"""
Cisco IOS-XE checks module - Pre-upgrade and post-upgrade validation checks.

This module provides Cisco-specific validation checks for network devices
before and after firmware upgrades.
"""

import time
import subprocess
from typing import Dict, Any, List

from .__helpers import flash_free_space


class Checks:
    """
    Handles Cisco-specific pre-upgrade and post-upgrade validation checks.
    """

    def __init__(
        self,
        connection,
        platform: str = "cisco_iosxe"
    ):
        """
        Initialize the Checks object.

        Args:
            connection: Active connection object (scrapli)
            platform: Platform name (cisco_ios, cisco_iosxe)
        """
        self.connection = connection
        self.platform = platform.lower().replace('-', '_')
        self.results: Dict[str, Any] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def pre_upgrade_checks(self) -> Dict[str, Any]:
        """
        Run Cisco-specific pre-upgrade checks.

        Checks include:
            - Device reachability (ping)
            - Current version verification
            - Free space check (using show file systems)
            - Running config verification
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

        try:
            # Check 1: Ping test
            self.results['pre_upgrade']['ping'] = self._check_ping()

            # Check 2: Current version
            self.results['pre_upgrade']['current_version'] = self._check_version()

            # Check 3: Free space using show file systems
            self.results['pre_upgrade']['free_space'] = self._check_free_space()

            # Check 4: Running config
            self.results['pre_upgrade']['running_config'] = self._check_running_config()

            # Check 5: Hardware health
            self.results['pre_upgrade']['hardware_health'] = self._check_hardware_health()

            # Check 6: License
            self.results['pre_upgrade']['license'] = self._check_license()

            # Check 7: Image integrity
            self.results['pre_upgrade']['image_integrity'] = self._check_image_integrity()

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

        return self.results

    def post_upgrade_checks(self) -> Dict[str, Any]:
        """
        Run Cisco-specific post-upgrade checks.

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

        try:
            # Wait for device to stabilize
            time.sleep(30)

            # Check 1: Ping test
            self.results['post_upgrade']['ping'] = self._check_ping()

            # Check 2: Version verification
            self.results['post_upgrade']['version'] = self._check_version()

            # Check 3: Uptime
            self.results['post_upgrade']['uptime'] = self._check_uptime()

            # Check 4: Configuration
            self.results['post_upgrade']['configuration'] = self._check_configuration()

            # Check 5: Hardware health
            self.results['post_upgrade']['hardware_health'] = self._check_hardware_health()

            # Check 6: Running config
            self.results['post_upgrade']['running_config'] = self._check_running_config()

            # Check 7: Services
            self.results['post_upgrade']['services'] = self._check_services()

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

        return self.results

    def _check_ping(self) -> Dict[str, Any]:
        """Check if device is reachable via ICMP ping."""
        try:
            param = '-n' if subprocess.os.name == 'nt' else '-c'
            command = ['ping', param, '1', '-W', '5', self.connection.host]

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return {
                    'status': True,
                    'message': f'{self.connection.host} is reachable',
                    'latency_ms': self._parse_ping_latency(result.stdout)
                }
            else:
                return {
                    'status': False,
                    'message': f'{self.connection.host} is not reachable'
                }
        except Exception as e:
            return {
                'status': False,
                'message': f'Ping check failed: {e}'
            }

    def _parse_ping_latency(self, output: str) -> int:
        """Parse ping latency from output."""
        import re
        patterns = [
            r'rtt\s+min/avg/max/mdev\s*=\s*([\d.]+)/([\d.]+)/([\d.]+)/([\d.]+)',
            r'round-trip\s+mean\s*:\s*([\d.]+)',
            r'time[=<]([\d.]+)\s*ms',
        ]

        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return int(float(match.group(1)))

        return 0

    def _check_version(self) -> Dict[str, Any]:
        """Check current software version using genie parser."""
        try:
            output = self.connection.send_command("show version")
            parsed = output.genie_parse_output()

            version = 'Unknown'
            if parsed and parsed.get('version', {}).get('version', ''):
                version = parsed['version']['version']

            return {
                'status': version != 'Unknown',
                'current_version': version,
                'message': f'Current version: {version}'
            }
        except Exception as e:
            return {
                'status': False,
                'message': f'Version check failed: {e}'
            }

    def _check_free_space(self) -> Dict[str, Any]:
        """Check available storage space using show file systems."""
        try:
            output = self.connection.send_command("show file systems")
            parsed = output.genie_parse_output()

            if not parsed or not parsed.get('file_systems'):
                return {
                    'status': False,
                    'message': 'Could not parse file systems output'
                }

            # Calculate total free space across all flash devices
            total_free_bytes = 0
            flash_devices = []

            for fs_id, fs_info in parsed['file_systems'].items():
                if 'flash' in fs_info.get('prefixes', ''):
                    free_size = fs_info.get('free_size', 0)
                    total_free_bytes += free_size
                    flash_devices.append(fs_info.get('prefixes', ''))

            # Convert to bytes if needed (genie typically returns bytes)
            if total_free_bytes > 0:
                # Check if value needs to be converted (genie may return in bytes)
                if total_free_bytes < 1000000:  # Likely KB or needs scaling
                    # Try to get actual bytes
                    for fs_id, fs_info in parsed['file_systems'].items():
                        if 'flash' in fs_info.get('prefixes', ''):
                            total_free_bytes = fs_info.get('free_size', 0)
                            break

            return {
                'status': total_free_bytes > 0,
                'free_bytes': total_free_bytes,
                'flash_devices': flash_devices,
                'message': f'Free space: {total_free_bytes} bytes across {len(flash_devices)} device(s)'
            }
        except Exception as e:
            return {
                'status': False,
                'message': f'Free space check failed: {e}'
            }

    def _check_running_config(self) -> Dict[str, Any]:
        """Verify running configuration is intact."""
        try:
            output = self.connection.send_command("show running-config")

            # Check for configuration errors
            error_patterns = ['error', 'invalid', 'failed']
            has_errors = any(err in output.textfsm_parse_output().lower() if hasattr(output, 'textfsm_parse_output') else err in output.lower() for err in error_patterns)

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

    def _check_hardware_health(self) -> Dict[str, Any]:
        """Check hardware health status using show inventory."""
        try:
            output = self.connection.send_command("show inventory")

            # Check for hardware errors
            error_keywords = ['error', 'failed', 'notOK', 'critical']
            has_errors = any(err in output.lower() for err in error_keywords)

            # Check for specific issues
            issue_patterns = [
                r'Unhealth',
                r'Absent',
                r'Failed',
            ]
            has_issues = False
            for pattern in issue_patterns:
                if hasattr(output, 'textfsm_parse_output'):
                    import re
                    if re.search(pattern, output.textfsm_parse_output(), re.IGNORECASE):
                        has_issues = True
                        break

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

    def _check_license(self) -> Dict[str, Any]:
        """Check license status using show licenses."""
        try:
            output = self.connection.send_command("show licenses")

            # Check for license errors
            error_patterns = ['error', 'invalid', 'expired', 'failed']
            has_errors = any(err in output.lower() for err in error_patterns)

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

    def _check_image_integrity(self) -> Dict[str, Any]:
        """Check image file integrity using verify /md5."""
        try:
            output = self.connection.send_command("verify /md5 flash:/*/image.bin")

            return {
                'status': 'OK' in output.upper(),
                'message': 'Image integrity verified' if 'OK' in output.upper() else 'Image integrity check pending'
            }
        except Exception as e:
            return {
                'status': False,
                'message': f'Image integrity check failed: {e}'
            }

    def _check_uptime(self) -> Dict[str, Any]:
        """Check device uptime using show version."""
        try:
            output = self.connection.send_command("show version")
            parsed = output.genie_parse_output()

            uptime = 'Unknown'
            if parsed and parsed.get('version', {}).get('uptime', ''):
                uptime = parsed['version']['uptime']

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

    def _check_configuration(self) -> Dict[str, Any]:
        """Verify post-upgrade configuration."""
        return self._check_running_config()

    def _check_services(self) -> Dict[str, Any]:
        """Check if services are running properly."""
        try:
            output = self.connection.send_command("show version")

            # Check for service status indicators
            service_ok = 'running' in output.lower() or 'active' in output.lower()

            return {
                'status': service_ok,
                'message': 'Services are running' if service_ok else 'Service status unknown'
            }
        except Exception as e:
            return {
                'status': False,
                'message': f'Services check failed: {e}'
            }
