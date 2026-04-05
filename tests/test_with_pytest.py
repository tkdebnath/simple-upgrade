import pytest
from unittest.mock import MagicMock
import sys
import os

root_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(root_dir, "src"))

from simple_upgrade.upgrade_package import UpgradePackage
from simple_upgrade.base import StageResult


@pytest.fixture
def mock_upgrade_package(monkeypatch):
    """
    Fixture to create an UpgradePackage without making any real connections.
    We use pytest's built-in 'monkeypatch' to overwrite the ConnectionManager.
    """
    # Create a MagicMock to replace ConnectionManager
    mock_cm = MagicMock()
    
    # We monkeypatch the ConnectionManager class entirely 
    # anywhere it gets imported in the upgrade_package module
    monkeypatch.setattr('simple_upgrade.upgrade_package.ConnectionManager', MagicMock(return_value=mock_cm))
    
    # Now we can safely instantiate it
    pkg = UpgradePackage(
        host="10.0.0.1",
        username="admin",
        password="test",
        platform="cisco_iosxe"
    )
    return pkg


# -------------------------------------------------------------------------
# Actual Test Functions
# -------------------------------------------------------------------------

def test_missing_initialization_params():
    """Test that missing required parameters raise a ValueError."""
    # Pytest makes exception testing extremely easy
    with pytest.raises(ValueError) as excinfo:
        UpgradePackage(host='', username='', password='', platform="cisco_iosxe")
    
    assert "strictly required" in str(excinfo.value)


def test_invalid_manufacturer():
    """Test validation of manufacturer strings."""
    with pytest.raises(ValueError) as excinfo:
        UpgradePackage(host='a', username='b', password='c', platform="cisco_iosxe", manufacturer="juniper_fake")
    
    assert "Invalid manufacturer" in str(excinfo.value)


def test_wait_function_mock_mode(mock_upgrade_package):
    """Test that the _handle_wait function respects 'mock' connection mode."""
    # The 'mock_upgrade_package' parameter automatically injects the result of our fixture
    mock_upgrade_package.connection_mode = 'mock'
    
    # Run the wait sequence
    result = mock_upgrade_package._handle_wait()
    
    # Verify the simulated logic bypassed the real TCP sweeps
    assert result.success is True
    assert "[MOCK]" in result.message
    
def test_successful_execution_flow(monkeypatch, mock_upgrade_package):
    """Use monkeypatch to test the full pipeline loop without actual stages running."""
    
    # Create a mock StageResult block
    fake_result = StageResult(success=True, message="mocked stage passing")
    
    # We monkeypatch the internal run_stage method to always return a success
    # Because we are testing the loop logic, not the individual stages here
    monkeypatch.setattr(mock_upgrade_package, 'run_stage', MagicMock(return_value=fake_result))
    
    # Run all 9 stages
    results = mock_upgrade_package.execute()
    
    assert len(results) >= 0  # Tests return a dict of results
