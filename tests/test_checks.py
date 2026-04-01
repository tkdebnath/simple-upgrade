"""Tests for the Checks module."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from simple_upgrade.checks import Checks, run_pre_checks, run_post_checks


class TestChecks:
    """Test cases for Checks class."""

    def test_checks_initialization(self):
        """Test Checks initialization with required parameters."""
        checks = Checks(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        assert checks.host == '192.168.1.1'
        assert checks.username == 'admin'
        assert checks.password == 'password'
        assert checks.device_type == 'cisco_xe'
        assert checks.port == 22  # default
        assert checks.timeout == 30  # default

    def test_checks_initialization_with_options(self):
        """Test Checks initialization with optional parameters."""
        checks = Checks(
            host='192.168.1.1',
            username='admin',
            password='password',
            port=2222,
            timeout=60,
            secret='enable123',
            platform='cisco_ios'
        )

        assert checks.port == 2222
        assert checks.timeout == 60
        assert checks.secret == 'enable123'
        assert checks.platform == 'cisco_ios'

    def test_checks_connect_method(self):
        """Test connect method exists."""
        checks = Checks(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        # connect() would create a real connection
        # For unit test, just verify the method exists
        assert hasattr(checks, 'connect')

    def test_checks_disconnect_method(self):
        """Test disconnect method exists."""
        checks = Checks(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        assert hasattr(checks, 'disconnect')

    def test_checks_pre_upgrade_checks_method(self):
        """Test pre_upgrade_checks method exists."""
        checks = Checks(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        assert hasattr(checks, 'pre_upgrade_checks')

    def test_checks_post_upgrade_checks_method(self):
        """Test post_upgrade_checks method exists."""
        checks = Checks(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        assert hasattr(checks, 'post_upgrade_checks')

    def test_checks_results_dict(self):
        """Test that results is a dictionary."""
        checks = Checks(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        assert isinstance(checks.results, dict)

    def test_checks_errors_list(self):
        """Test that errors is a list."""
        checks = Checks(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        assert isinstance(checks.errors, list)

    def test_checks_warnings_list(self):
        """Test that warnings is a list."""
        checks = Checks(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        assert isinstance(checks.warnings, list)


class TestRunPreChecks:
    """Test standalone run_pre_checks function."""

    def test_run_pre_checks_signature(self):
        """Test run_pre_checks has correct signature."""
        result = run_pre_checks(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        assert isinstance(result, dict)
        assert 'status' in result


class TestRunPostChecks:
    """Test standalone run_post_checks function."""

    def test_run_post_checks_signature(self):
        """Test run_post_checks has correct signature."""
        result = run_post_checks(
            host='192.168.1.1',
            username='admin',
            password='password',
            device_type='cisco_xe'
        )

        assert isinstance(result, dict)
        assert 'status' in result
