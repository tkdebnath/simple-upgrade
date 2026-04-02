"""
simple-upgrade - A minimalist network device firmware upgrade orchestrator.
"""

from .upgrade_package import UpgradePackage
from .models import GoldenImage, FileServer, DeviceInfo, StageResult
from .connection_manager import ConnectionManager

__version__ = "1.0.0"
__author__ = "Tarani Debnath"
