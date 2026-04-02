"""
Manufacturers - Platform-specific upgrade implementations.

This module provides manufacturer-specific implementations for each upgrade stage.
Each manufacturer has submodules for sync, readiness, distribution, and activation.

Available manufacturers:
    - cisco

Usage:
    from simple_upgrade.manufacturers.cisco import sync, readiness, distribution

    # Get device info using Cisco-specific commands
    device_info = sync.fetch_info(connection, platform)

"""

import importlib
from typing import Optional, Dict, Any

from . import cisco


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
        func_name = stage if stage != 'sync' else 'fetch_info'
        if hasattr(module, func_name):
            func = getattr(module, func_name)
            # For sync function, pass channel as second positional argument (after connection)
            if stage == 'sync':
                # Get channel from kwargs if provided
                channel = kwargs.pop('channel', None)
                # If channel not provided, try to get from connection module
                if channel is None and len(args) > 0:
                    conn = args[0]
                    channel_module = getattr(conn, '__module__', '')
                    channel = 'scrapli' if 'scrapli' in channel_module else None
                # Insert channel as second argument (after connection)
                args = list(args)
                args.insert(1, channel)
                return func(*args, **kwargs)
            return func(*args, **kwargs)
        elif hasattr(module, 'execute'):
            return module.execute(*args, **kwargs)
    return None
