"""
simple-upgrade - A simple Python package for network device firmware upgrades

Usage:
    from simple_upgrade import UpgradeManager

    # device_type is REQUIRED - specify the platform
    manager = UpgradeManager(
        host="192.168.1.1",
        username="admin",
        password="password",
        device_type="cisco_xe",
        golden_image={
            "version": "17.9.4",
            "image_name": "flash:c9300-universalk9.17.9.4.SPA.bin",
            "file_server": {
                "ip": "10.0.0.10",
                "protocol": "http",
                "base_path": "/tftpboot"
            }
        }
    )
    manager.upgrade()
"""

from .device import Device, DeviceConnectionError
from .workflow import UpgradeWorkflow, UpgradeManager
from .connection_manager import ConnectionManager, ConnectionError
from .sync import SyncManager, get_device_commands, sync_device
from .checks import Checks, run_pre_checks, run_post_checks
from .genie_tests import CiscoGenieTests, run_genie_tests, pre_upgrade_genie_checks
from .report import ReportGenerator, generate_upgrade_report
from .constants import PLATFORM_MAPPINGS, get_platform_for_library, get_all_libraries, get_supported_platforms
from .device_profiles import (
    get_device_profile,
    get_command_template,
    list_manufacturers,
    list_models,
    find_device_profile,
    execute_upgrade_command,
    execute_command,
    DEVICE_PROFILES_PATH
)
from .manufacturers import cisco, juniper, arista
from .manufacturers import get_manufacturer_module, execute_stage

__version__ = "0.1.0"
__author__ = "Tarani Debnath"
