import unittest
from unittest.mock import patch, MagicMock

import sys
import os

root_dir = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(root_dir, "src"))

# Import the class we want to test
from simple_upgrade.upgrade_package import UpgradePackage
from simple_upgrade.base import StageResult

class TestUpgradePackage(unittest.TestCase):

    @patch('simple_upgrade.upgrade_package.ConnectionManager')
    def setUp(self, MockConnectionManager):
        # We replace ConnectionManager with a mock during setup
        # so instantiation of UpgradePackage doesn't trigger network activity
        self.mock_cm_class = MockConnectionManager
        self.mock_cm_instance = MagicMock()
        self.mock_cm_class.return_value = self.mock_cm_instance

        self.pkg = UpgradePackage(
            host="192.168.1.1",
            username="admin",
            password="admin",
            platform="cisco_iosxe"
        )

    @patch('simple_upgrade.registry.global_registry.execute_stage')
    def test_run_stage_success(self, mock_execute_stage):
        """Test that a stage successfully executes and returns a success StageResult."""
        # 1. ARRANGE (Set up the mock response)
        expected_result = StageResult(success=True, message="Mocked success")
        mock_execute_stage.return_value = expected_result

        # 2. ACT (Run the function we are testing)
        result = self.pkg.run_stage('readiness')

        # 3. ASSERT (Verify the results and interactions)
        self.assertTrue(result.success)
        self.assertEqual(result.message, "Mocked success")
        mock_execute_stage.assert_called_once_with('readiness', self.pkg.ctx)

    @patch('simple_upgrade.registry.global_registry.execute_stage')
    def test_run_stage_failure(self, mock_execute_stage):
        """Test that exceptions raised during execution are handled correctly."""
        # 1. ARRANGE (Simulate a failure/exception)
        mock_execute_stage.side_effect = ValueError("CLI syntax error")

        # 2. ACT
        result = self.pkg.run_stage('distribute')

        # 3. ASSERT (Verify exception is caught and formatted properly)
        self.assertFalse(result.success)
        self.assertIn("failed: CLI syntax error", result.message)
        self.assertEqual(self.pkg.ctx.failed_stage, 'distribute')

if __name__ == '__main__':
    unittest.main()
