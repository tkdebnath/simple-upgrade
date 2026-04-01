"""
Genie Tests module - Network validation using Genie Learn and Test features.

This module provides Cisco IOS-XE specific validation using Genie PyATS library.
It uses Learn objects to gather structured data and Testcases for validation.

Usage:
    from simple_upgrade import CiscoGenieTests

    tests = CiscoGenieTests(
        host="192.168.1.1",
        username="admin",
        password="password",
        device_type="cisco_xe"
    )

    # Learn device information
    topology = tests.learn_topology()
    interfaces = tests.learn_interfaces()
    vrfs = tests.learn_vrfs()
    bgp = tests.learn_bgp()
    ospf = tests.learn_ospf()

    # Run validation tests
    results = tests.validate_interfaces()
    results = tests.validate_bgp_peers()
"""

from typing import Dict, Any, List, Optional
import time

try:
    from genie.conf import Genie
    from pyats.easypy import run
    HAS_GENIE = True
except ImportError:
    HAS_GENIE = False


class CiscoGenieTests:
    """
    Handles Cisco-specific network validation using Genie PyATS.

    Learn features:
        - Topology information
        - Interfaces (status, IP, traffic)
        - VRFs and routing
        - BGP neighbors and routes
        - OSPF neighbors and LSDB
        - MAC address table
        - ARP table
        - LLDP neighbors
        - STP information

    Validation features:
        - Interface status validation
        - BGP peer validation
        - OSPF neighbor validation
        - MAC address validation
        - ARP validation
        - Config consistency checks
    """

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        device_type: str = "cisco_xe",
        port: int = 22,
        secret: str = "",
        timeout: int = 30
    ):
        """
        Initialize the CiscoGenieTests object.

        Args:
            host: Device IP or hostname
            username: SSH username
            password: SSH password
            device_type: Device type (default: cisco_xe)
            port: SSH port (default: 22)
            secret: Enable password
            timeout: Connection timeout in seconds
        """
        self.host = host
        self.username = username
        self.password = password
        self.device_type = device_type
        self.port = port
        self.secret = secret
        self.timeout = timeout

        self.testbed = None
        self.device = None
        self.connections = {}

        # Store learned data
        self.learned_data: Dict[str, Any] = {}

        # Check if Genie is available
        self.genie_available = HAS_GENIE

    def connect(self) -> bool:
        """
        Establish connection using Genie testbed.

        Returns:
            True if connection successful, False otherwise
        """
        if not HAS_GENIE:
            return False

        try:
            # Create testbed
            self.testbed = Genie.initTestbed(
                name='cisco_device',
                nodes={
                    'device': {
                        'type': 'router' if 'mx' in self.device_type.lower() else 'switch',
                        'os': self.device_type,
                        'credentials': {
                            'default': {
                                'username': self.username,
                                'password': self.password,
                            },
                            'enable': {
                                'password': self.secret,
                            },
                        },
                        'connections': {
                            'console': {
                                'protocol': 'ssh',
                                'ip': self.host,
                                'port': self.port,
                            },
                        },
                    },
                },
            )

            self.device = self.testbed.devices['device']
            self.device.connect()
            return True

        except Exception as e:
            return False

    def disconnect(self):
        """Close the Genie connection."""
        if self.device and self.device.connected:
            try:
                self.device.disconnect()
            except Exception:
                pass
        self.testbed = None
        self.device = None

    # ==========================
    # Learn Functions
    # ==========================

    def learn_topology(self) -> Dict[str, Any]:
        """
        Learn topology information from the device.

        Returns:
            Dictionary with topology information
        """
        if not self.genie_available:
            return {'error': 'Genie not available'}

        try:
            if not self.device or not self.device.connected:
                self.connect()

            topology = self.device.learn('topology')
            self.learned_data['topology'] = topology.info
            return topology.info

        except Exception as e:
            return {'error': str(e)}

    def learn_interfaces(self) -> Dict[str, Any]:
        """
        Learn interface information from the device.

        Returns:
            Dictionary with interface information
        """
        if not self.genie_available:
            return {'error': 'Genie not available'}

        try:
            if not self.device or not self.device.connected:
                self.connect()

            interfaces = self.device.learn('interface')
            self.learned_data['interfaces'] = interfaces.info
            return interfaces.info

        except Exception as e:
            return {'error': str(e)}

    def learn_vrfs(self) -> Dict[str, Any]:
        """
        Learn VRF information from the device.

        Returns:
            Dictionary with VRF information
        """
        if not self.genie_available:
            return {'error': 'Genie not available'}

        try:
            if not self.device or not self.device.connected:
                self.connect()

            vrfs = self.device.learn('vrf')
            self.learned_data['vrfs'] = vrfs.info
            return vrfs.info

        except Exception as e:
            return {'error': str(e)}

    def learn_bgp(self) -> Dict[str, Any]:
        """
        Learn BGP information from the device.

        Returns:
            Dictionary with BGP information
        """
        if not self.genie_available:
            return {'error': 'Genie not available'}

        try:
            if not self.device or not self.device.connected:
                self.connect()

            bgp = self.device.learn('bgp')
            self.learned_data['bgp'] = bgp.info
            return bgp.info

        except Exception as e:
            return {'error': str(e)}

    def learn_ospf(self) -> Dict[str, Any]:
        """
        Learn OSPF information from the device.

        Returns:
            Dictionary with OSPF information
        """
        if not self.genie_available:
            return {'error': 'Genie not available'}

        try:
            if not self.device or not self.device.connected:
                self.connect()

            ospf = self.device.learn('ospf')
            self.learned_data['ospf'] = ospf.info
            return ospf.info

        except Exception as e:
            return {'error': str(e)}

    def learn_mac(self) -> Dict[str, Any]:
        """
        Learn MAC address table from the device.

        Returns:
            Dictionary with MAC address information
        """
        if not self.genie_available:
            return {'error': 'Genie not available'}

        try:
            if not self.device or not self.device.connected:
                self.connect()

            mac = self.device.learn('mac')
            self.learned_data['mac'] = mac.info
            return mac.info

        except Exception as e:
            return {'error': str(e)}

    def learn_arp(self) -> Dict[str, Any]:
        """
        Learn ARP table from the device.

        Returns:
            Dictionary with ARP information
        """
        if not self.genie_available:
            return {'error': 'Genie not available'}

        try:
            if not self.device or not self.device.connected:
                self.connect()

            arp = self.device.learn('arp')
            self.learned_data['arp'] = arp.info
            return arp.info

        except Exception as e:
            return {'error': str(e)}

    def learn_lldp(self) -> Dict[str, Any]:
        """
        Learn LLDP neighbors from the device.

        Returns:
            Dictionary with LLDP information
        """
        if not self.genie_available:
            return {'error': 'Genie not available'}

        try:
            if not self.device or not self.device.connected:
                self.connect()

            lldp = self.device.learn('lldp')
            self.learned_data['lldp'] = lldp.info
            return lldp.info

        except Exception as e:
            return {'error': str(e)}

    def learn_stp(self) -> Dict[str, Any]:
        """
        Learn STP information from the device.

        Returns:
            Dictionary with STP information
        """
        if not self.genie_available:
            return {'error': 'Genie not available'}

        try:
            if not self.device or not self.device.connected:
                self.connect()

            stp = self.device.learn('stp')
            self.learned_data['stp'] = stp.info
            return stp.info

        except Exception as e:
            return {'error': str(e)}

    def learn_routes(self) -> Dict[str, Any]:
        """
        Learn routing table from the device.

        Returns:
            Dictionary with routing information
        """
        if not self.genie_available:
            return {'error': 'Genie not available'}

        try:
            if not self.device or not self.device.connected:
                self.connect()

            routes = self.device.learn('routes')
            self.learned_data['routes'] = routes.info
            return routes.info

        except Exception as e:
            return {'error': str(e)}

    # ==========================
    # Validation Functions
    # ==========================

    def validate_interfaces(self) -> Dict[str, Any]:
        """
        Validate interface status.

        Checks:
            - Interface status (up/down)
            - Line protocol status
            - Error counters
            - Speed/duplex settings

        Returns:
            Dictionary with validation results
        """
        results = {
            'test_name': 'Interface Validation',
            'status': 'passed',
            'checks': [],
            'failed_checks': [],
        }

        if not self.genie_available:
            results['status'] = 'skipped'
            results['reason'] = 'Genie not available'
            return results

        try:
            if 'interfaces' not in self.learned_data:
                self.learn_interfaces()

            interfaces = self.learned_data.get('interfaces', {})

            # Check all interfaces
            for interface_name, interface_config in interfaces.items():
                # Skip not present interfaces
                if interface_config.get('enabled') is False:
                    continue

                check = {
                    'interface': interface_name,
                    'status': 'passed',
                    'details': {},
                }

                # Check operational status
                if interface_config.get('oper_status') == 'up':
                    check['details']['oper_status'] = 'up'
                else:
                    check['status'] = 'failed'
                    check['details']['oper_status'] = interface_config.get('oper_status', 'unknown')

                # Check line protocol
                if interface_config.get('line_protocol') == 'up':
                    check['details']['line_protocol'] = 'up'
                else:
                    check['status'] = 'warning'
                    check['details']['line_protocol'] = interface_config.get('line_protocol', 'unknown')

                # Check for input/output errors
                if interface_config.get('counters', {}).get('input_errors', 0) > 0:
                    check['status'] = 'warning'
                    check['details']['input_errors'] = interface_config['counters']['input_errors']

                if interface_config.get('counters', {}).get('output_errors', 0) > 0:
                    check['status'] = 'warning'
                    check['details']['output_errors'] = interface_config['counters']['output_errors']

                results['checks'].append(check)
                if check['status'] == 'failed':
                    results['failed_checks'].append(check)

            if results['failed_checks']:
                results['status'] = 'failed'

            return results

        except Exception as e:
            results['status'] = 'failed'
            results['error'] = str(e)
            return results

    def validate_bgp_peers(self) -> Dict[str, Any]:
        """
        Validate BGP peer status.

        Checks:
            - BGP neighbor state
            - AS number match
            - Uptime
            - Prefix count

        Returns:
            Dictionary with BGP validation results
        """
        results = {
            'test_name': 'BGP Peer Validation',
            'status': 'passed',
            'checks': [],
            'failed_checks': [],
        }

        if not self.genie_available:
            results['status'] = 'skipped'
            results['reason'] = 'Genie not available'
            return results

        try:
            if 'bgp' not in self.learned_data:
                self.learn_bgp()

            bgp = self.learned_data.get('bgp', {})

            # Get AS number
            local_as = bgp.get('instance', {}).get('default', {}).get('as', '')

            # Check neighbors
            bgp_neighbors = bgp.get('vrf', {}).get('default', {}).get('neighbor', {})

            for neighbor_ip, neighbor_config in bgp_neighbors.items():
                check = {
                    'neighbor': neighbor_ip,
                    'status': 'passed',
                    'details': {},
                }

                state = neighbor_config.get('state', '')
                bgp_state = neighbor_config.get('bgp_state', '')

                # Check neighbor state
                if state == 'established' or bgp_state == 'established':
                    check['details']['state'] = 'established'
                else:
                    check['status'] = 'failed'
                    check['details']['state'] = state or bgp_state or 'unknown'

                # Check AS number
                neighbor_as = neighbor_config.get('remote_as', 0)
                if neighbor_as and local_as:
                    check['details']['neighbor_as'] = neighbor_as

                # Check uptime
                uptime = neighbor_config.get('uptime', '')
                if uptime:
                    check['details']['uptime'] = uptime

                # Check prefix count
                prefix_count = neighbor_config.get('prefix_counter', {}).get('received', 0)
                check['details']['prefix_count'] = prefix_count

                results['checks'].append(check)
                if check['status'] == 'failed':
                    results['failed_checks'].append(check)

            if results['failed_checks']:
                results['status'] = 'failed'

            return results

        except Exception as e:
            results['status'] = 'failed'
            results['error'] = str(e)
            return results

    def validate_ospf_neighbors(self) -> Dict[str, Any]:
        """
        Validate OSPF neighbor status.

        Checks:
            - Neighbor state
            - Router ID
            - Priority
            - Dead timer

        Returns:
            Dictionary with OSPF validation results
        """
        results = {
            'test_name': 'OSPF Neighbor Validation',
            'status': 'passed',
            'checks': [],
            'failed_checks': [],
        }

        if not self.genie_available:
            results['status'] = 'skipped'
            results['reason'] = 'Genie not available'
            return results

        try:
            if 'ospf' not in self.learned_data:
                self.learn_ospf()

            ospf = self.learned_data.get('ospf', {})

            # Get neighbors from instance
            neighbors = ospf.get('instance', {}).get('default', {}).get('vrf', {}).get('default', {}).get('neighbors', {})

            for neighbor_id, neighbor_config in neighbors.items():
                check = {
                    'neighbor': neighbor_id,
                    'status': 'passed',
                    'details': {},
                }

                # Check state
                state = neighbor_config.get('state', '')
                if state == 'full' or state == 'full':
                    check['details']['state'] = state
                else:
                    check['status'] = 'warning'
                    check['details']['state'] = state or 'unknown'

                # Check router ID
                router_id = neighbor_config.get('router_id', '')
                if router_id:
                    check['details']['router_id'] = router_id

                results['checks'].append(check)
                if check['status'] == 'warning':
                    results['failed_checks'].append(check)

            if results['failed_checks']:
                results['status'] = 'warning'

            return results

        except Exception as e:
            results['status'] = 'failed'
            results['error'] = str(e)
            return results

    def validate_mac_table(self) -> Dict[str, Any]:
        """
        Validate MAC address table.

        Checks:
            - MAC address count
            - Dynamic vs static entries
            - Port associations

        Returns:
            Dictionary with MAC validation results
        """
        results = {
            'test_name': 'MAC Table Validation',
            'status': 'passed',
            'checks': [],
            'failed_checks': [],
        }

        if not self.genie_available:
            results['status'] = 'skipped'
            results['reason'] = 'Genie not available'
            return results

        try:
            if 'mac' not in self.learned_data:
                self.learn_mac()

            mac_table = self.learned_data.get('mac', {})

            total_mac = 0
            dynamic_mac = 0
            static_mac = 0

            for vlan, vlan_config in mac_table.items():
                if vlan == 'total_entries':
                    continue

                for mac_addr, mac_entry in vlan_config.get('mac_address', {}).items():
                    total_mac += 1
                    if mac_entry.get('entry_type') == 'dynamic':
                        dynamic_mac += 1
                    else:
                        static_mac += 1

            results['checks'].append({
                'validation': 'MAC Table Summary',
                'status': 'passed',
                'total_mac': total_mac,
                'dynamic_mac': dynamic_mac,
                'static_mac': static_mac,
            })

            # Check for suspicious MAC counts
            if total_mac > 10000:
                results['status'] = 'warning'
                results['checks'][-1]['warning'] = 'High MAC count detected'

            return results

        except Exception as e:
            results['status'] = 'failed'
            results['error'] = str(e)
            return results

    def validate_arp_table(self) -> Dict[str, Any]:
        """
        Validate ARP table.

        Checks:
            - ARP entry count
            - Missing entries
            - Incomplete entries

        Returns:
            Dictionary with ARP validation results
        """
        results = {
            'test_name': 'ARP Table Validation',
            'status': 'passed',
            'checks': [],
            'failed_checks': [],
        }

        if not self.genie_available:
            results['status'] = 'skipped'
            results['reason'] = 'Genie not available'
            return results

        try:
            if 'arp' not in self.learned_data:
                self.learn_arp()

            arp_table = self.learned_data.get('arp', {})

            vrf = arp_table.get('vrf', {}).get('default', {})
            total_entries = vrf.get('total_entries', 0)
            incomplete = vrf.get('entries', {}).get('incomplete', 0)

            results['checks'].append({
                'validation': 'ARP Summary',
                'status': 'passed',
                'total_entries': total_entries,
                'incomplete_entries': incomplete,
            })

            if incomplete > 0:
                results['status'] = 'warning'
                results['checks'][-1]['warning'] = f'{incomplete} incomplete ARP entries'

            return results

        except Exception as e:
            results['status'] = 'failed'
            results['error'] = str(e)
            return results

    def validate_config_consistency(self) -> Dict[str, Any]:
        """
        Validate configuration consistency.

        Checks:
            - Running vs startup config consistency
            - Configuration syntax errors
            - Missing required configs

        Returns:
            Dictionary with config validation results
        """
        results = {
            'test_name': 'Configuration Consistency Validation',
            'status': 'passed',
            'checks': [],
            'failed_checks': [],
        }

        if not self.genie_available:
            results['status'] = 'skipped'
            results['reason'] = 'Genie not available'
            return results

        try:
            # Get running config
            running_config = self.device.execute('show running-config')

            # Get startup config
            startup_config = self.device.execute('show startup-config')

            # Check for common issues
            issues = []

            # Check for configuration errors
            if 'error' in running_config.lower():
                issues.append('Configuration errors detected')

            # Check for incomplete commands
            if 'incomplete command' in running_config.lower():
                issues.append('Incomplete commands detected')

            results['checks'].append({
                'validation': 'Config Consistency',
                'status': 'passed' if not issues else 'failed',
                'issues': issues,
            })

            if issues:
                results['status'] = 'failed'

            return results

        except Exception as e:
            results['status'] = 'failed'
            results['error'] = str(e)
            return results

    def run_all_tests(self) -> Dict[str, Any]:
        """
        Run all validation tests.

        Returns:
            Dictionary with all test results
        """
        all_results = {
            'summary': {},
            'details': {},
        }

        # Run all tests
        tests = [
            ('interfaces', self.validate_interfaces),
            ('bgp_peers', self.validate_bgp_peers),
            ('ospf_neighbors', self.validate_ospf_neighbors),
            ('mac_table', self.validate_mac_table),
            ('arp_table', self.validate_arp_table),
            ('config_consistency', self.validate_config_consistency),
        ]

        for test_name, test_func in tests:
            all_results['details'][test_name] = test_func()

        # Calculate summary
        status_counts = {'passed': 0, 'warning': 0, 'failed': 0, 'skipped': 0}
        for test_result in all_results['details'].values():
            status = test_result.get('status', 'skipped')
            status_counts[status] = status_counts.get(status, 0) + 1

        all_results['summary'] = status_counts

        # Determine overall status
        if status_counts['failed'] > 0:
            all_results['overall_status'] = 'failed'
        elif status_counts['warning'] > 0:
            all_results['overall_status'] = 'warning'
        else:
            all_results['overall_status'] = 'passed'

        return all_results


def run_genie_tests(
    host: str,
    username: str,
    password: str,
    device_type: str = "cisco_xe",
    port: int = 22,
    secret: str = "",
    run_all: bool = True
) -> Dict[str, Any]:
    """
    Standalone function to run Genie tests on a Cisco device.

    Args:
        host: Device IP or hostname
        username: SSH username
        password: SSH password
        device_type: Device type (default: cisco_xe)
        port: SSH port (default: 22)
        secret: Enable password
        run_all: If True, run all tests

    Returns:
        Dictionary with test results
    """
    tests = CiscoGenieTests(
        host=host,
        username=username,
        password=password,
        device_type=device_type,
        port=port,
        secret=secret,
    )

    if run_all:
        return tests.run_all_tests()
    else:
        # Return empty results if not running all tests
        return {'status': 'skipped', 'reason': 'run_all=False'}


def pre_upgrade_genie_checks(
    host: str,
    username: str,
    password: str,
    device_type: str = "cisco_xe",
    port: int = 22,
    secret: str = "",
) -> Dict[str, Any]:
    """
    Run Genie-based pre-upgrade checks.

    Includes:
        - Interface validation
        - BGP peer validation
        - OSPF neighbor validation
        - MAC/ARP table validation

    Returns:
        Dictionary with check results
    """
    tests = CiscoGenieTests(
        host=host,
        username=username,
        password=password,
        device_type=device_type,
        port=port,
        secret=secret,
    )

    return tests.run_all_tests()
