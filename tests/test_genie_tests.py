"""Tests for the Genie Tests module."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from simple_upgrade.genie_tests import CiscoGenieTests, run_genie_tests, pre_upgrade_genie_checks


class TestCiscoGenieTests:
    """Test cases for CiscoGenieTests class."""

    def test_cisco_genie_tests_initialization(self):
        """Test CiscoGenieTests initialization."""
        tests = CiscoGenieTests(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        assert tests.host == '192.168.1.1'
        assert tests.username == 'admin'
        assert tests.password == 'password'
        assert tests.device_type == 'cisco_xe'
        assert tests.port == 22  # default

    def test_cisco_genie_tests_initialization_with_options(self):
        """Test CiscoGenieTests initialization with optional parameters."""
        tests = CiscoGenieTests(
            host='192.168.1.1',
            username='admin',
            password='password',
            port=2222,
            secret='enable123',
            timeout=60
        )

        assert tests.port == 2222
        assert tests.secret == 'enable123'
        assert tests.timeout == 60

    def test_cisco_genie_tests_genie_available(self):
        """Test genie availability check."""
        tests = CiscoGenieTests(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        # Should be False if genie not installed
        assert hasattr(tests, 'genie_available')

    def test_cisco_genie_tests_connect(self):
        """Test connect method."""
        tests = CiscoGenieTests(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        assert hasattr(tests, 'connect')

    def test_cisco_genie_tests_disconnect(self):
        """Test disconnect method."""
        tests = CiscoGenieTests(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        assert hasattr(tests, 'disconnect')

    def test_cisco_genie_tests_learn_topology(self):
        """Test learn_topology method."""
        tests = CiscoGenieTests(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        result = tests.learn_topology()
        assert isinstance(result, dict)

    def test_cisco_genie_tests_learn_interfaces(self):
        """Test learn_interfaces method."""
        tests = CiscoGenieTests(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        result = tests.learn_interfaces()
        assert isinstance(result, dict)

    def test_cisco_genie_tests_learn_vrfs(self):
        """Test learn_vrfs method."""
        tests = CiscoGenieTests(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        result = tests.learn_vrfs()
        assert isinstance(result, dict)

    def test_cisco_genie_tests_learn_bgp(self):
        """Test learn_bgp method."""
        tests = CiscoGenieTests(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        result = tests.learn_bgp()
        assert isinstance(result, dict)

    def test_cisco_genie_tests_learn_ospf(self):
        """Test learn_ospf method."""
        tests = CiscoGenieTests(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        result = tests.learn_ospf()
        assert isinstance(result, dict)

    def test_cisco_genie_tests_learn_mac(self):
        """Test learn_mac method."""
        tests = CiscoGenieTests(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        result = tests.learn_mac()
        assert isinstance(result, dict)

    def test_cisco_genie_tests_learn_arp(self):
        """Test learn_arp method."""
        tests = CiscoGenieTests(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        result = tests.learn_arp()
        assert isinstance(result, dict)

    def test_cisco_genie_tests_learn_lldp(self):
        """Test learn_lldp method."""
        tests = CiscoGenieTests(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        result = tests.learn_lldp()
        assert isinstance(result, dict)

    def test_cisco_genie_tests_learn_stp(self):
        """Test learn_stp method."""
        tests = CiscoGenieTests(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        result = tests.learn_stp()
        assert isinstance(result, dict)

    def test_cisco_genie_tests_learn_routes(self):
        """Test learn_routes method."""
        tests = CiscoGenieTests(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        result = tests.learn_routes()
        assert isinstance(result, dict)

    def test_cisco_genie_tests_validate_interfaces(self):
        """Test validate_interfaces method."""
        tests = CiscoGenieTests(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        result = tests.validate_interfaces()
        assert isinstance(result, dict)
        assert 'status' in result
        assert 'checks' in result

    def test_cisco_genie_tests_validate_bgp_peers(self):
        """Test validate_bgp_peers method."""
        tests = CiscoGenieTests(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        result = tests.validate_bgp_peers()
        assert isinstance(result, dict)
        assert 'status' in result
        assert 'checks' in result

    def test_cisco_genie_tests_validate_ospf_neighbors(self):
        """Test validate_ospf_neighbors method."""
        tests = CiscoGenieTests(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        result = tests.validate_ospf_neighbors()
        assert isinstance(result, dict)
        assert 'status' in result
        assert 'checks' in result

    def test_cisco_genie_tests_validate_mac_table(self):
        """Test validate_mac_table method."""
        tests = CiscoGenieTests(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        result = tests.validate_mac_table()
        assert isinstance(result, dict)
        assert 'status' in result
        assert 'checks' in result

    def test_cisco_genie_tests_validate_arp_table(self):
        """Test validate_arp_table method."""
        tests = CiscoGenieTests(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        result = tests.validate_arp_table()
        assert isinstance(result, dict)
        assert 'status' in result
        assert 'checks' in result

    def test_cisco_genie_tests_validate_config_consistency(self):
        """Test validate_config_consistency method."""
        tests = CiscoGenieTests(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        result = tests.validate_config_consistency()
        assert isinstance(result, dict)
        assert 'status' in result

    def test_cisco_genie_tests_run_all_tests(self):
        """Test run_all_tests method."""
        tests = CiscoGenieTests(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        result = tests.run_all_tests()
        assert isinstance(result, dict)
        assert 'summary' in result
        assert 'details' in result
        assert 'overall_status' in result


class TestRunGenieTests:
    """Test standalone run_genie_tests function."""

    def test_run_genie_tests_signature(self):
        """Test run_genie_tests has correct signature."""
        result = run_genie_tests(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        assert isinstance(result, dict)

    def test_run_genie_tests_run_all_false(self):
        """Test run_genie_tests with run_all=False."""
        result = run_genie_tests(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe',
            run_all=False
        )

        assert isinstance(result, dict)


class TestPreUpgradeGenieChecks:
    """Test standalone pre_upgrade_genie_checks function."""

    def test_pre_upgrade_genie_checks_signature(self):
        """Test pre_upgrade_genie_checks has correct signature."""
        result = pre_upgrade_genie_checks(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        assert isinstance(result, dict)
