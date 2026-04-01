"""
Manufacturers - Platform-specific upgrade implementations.

This module provides manufacturer-specific implementations for each upgrade stage.
Each manufacturer has submodules for sync, readiness, distribution, and activation.

Available manufacturers:
    - cisco
    - juniper
    - arista

Usage:
    from simple_upgrade.manufacturers.cisco import sync, readiness, distribution

    # Get device info using Cisco-specific commands
    device_info = sync.fetch_info(connection, platform)

"""

import importlib
from typing import Optional, Dict, Any

from . import cisco, juniper, arista


def get_manufacturer_module(manufacturer: str, stage: str) -> Optional[Any]:
    """
    Get the module for a manufacturer and stage.

    Args:
        manufacturer: Manufacturer name (cisco, juniper, arista)
        stage: Stage name (sync, readiness, distribution, activation, verification, etc.)

    Returns:
        Module object or None if not found
    """
    try:
        module_path = f"simple_upgrade.manufacturers.{manufacturer}.{stage}"
        return importlib.import_module(module_path)
    except ImportError:
        return None


def execute_stage(manufacturer: str, stage: str, *args, **kwargs) -> Any:
    """
    Execute a stage for a manufacturer using manufacturer-specific logic.

    Args:
        manufacturer: Manufacturer name
        stage: Stage to execute
        *args: Arguments to pass to the stage function
        **kwargs: Keyword arguments to pass to the stage function

    Returns:
        Result from the stage function
    """
    module = get_manufacturer_module(manufacturer, stage)
    if module:
        # Try to find a function that matches the stage name or a generic execute function
        if hasattr(module, stage):
            return getattr(module, stage)(*args, **kwargs)
        elif hasattr(module, 'execute'):
            return module.execute(*args, **kwargs)
    return None
