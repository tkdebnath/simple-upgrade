"""
UpgradePackage - High-level dynamic firmware upgrade orchestrator.
"""

import time
import subprocess
import platform as py_platform
from typing import Dict, Any, Optional, List

from .connection_manager import ConnectionManager
from .base import GoldenImage, FileServer, DeviceInfo, StageResult, ExecutionContext
from .base import ExecutionContext
from .registry import global_registry
from . import manufacturers


class UpgradePackage:
    """
    Orchestrates the firmware upgrade workflow across any manufacturer.
    
    This class is now a lean 'runner' that executes a sequence of stages 
    retrieved from the TaskRegistry.
    """

    STAGES = [
        'sync', 
        'readiness', 
        'pre_check', 
        'distribute', 
        'activate', 
        'post_activation_wait', 
        'post_check', 
        'verification',
        'diff'
    ]

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        platform: str,
        port: int = 22,
        manufacturer: str = "cisco",
        golden_image: Optional[Dict[str, Any]] = None,
        file_server: Optional[Dict[str, Any]] = None,
        connection_mode: str = "normal",
        enable_password: Optional[str] = None,   # enable / privilege-exec secret
        **kwargs
    ):
        self.host = host
        self.device_kwargs = kwargs
        
        # Initialize Core components
        self._connection_manager = ConnectionManager(
            host=host, username=username, password=password, port=port,
            platform=platform, connection_mode=connection_mode,
            enable_password=enable_password,
            **kwargs
        )

        # ── Safely structure payload to trigger Pydantic validation ─────
        if not golden_image:
            golden_image = {"version": "unknown", "image_name": "unknown", "image_size": 1, "md5": "x"}
        if not file_server:
            file_server = {"ip": "127.0.0.1", "base_path": "/"}

        self.ctx = ExecutionContext(
            connection_manager=self._connection_manager,
            golden_image=GoldenImage(**golden_image),
            file_server=FileServer(**file_server),
            connection_mode=connection_mode,
            device_type=platform,  # We still map to device_type on ExecutionContext for backwards compat internally
            manufacturer=manufacturer
        )

        # ── Validate Root Config ──────────────────────────────────────────
        # 1. Base Authentication & Connectivity
        if not host or not username or not password:
            raise ValueError("UpgradePackage initialization failed: 'host', 'username', and 'password' are strictly required.")
            
        # 2. Platform & Classification
        if not manufacturer or not platform:
            raise ValueError("UpgradePackage initialization failed: 'manufacturer' and 'platform' are strictly required.")
            
        manufacturer = manufacturer.lower()
        
        SUPPORTED_DEVICES = {
            "cisco": ["cisco-ios-xe", "cisco_xe", "cisco_iosxe", "iosxe"]
        }

        if manufacturer not in SUPPORTED_DEVICES:
            raise ValueError(
                f"UpgradePackage initialization failed: Invalid manufacturer '{manufacturer}'. "
                f"Supported manufacturers and their platforms are: {SUPPORTED_DEVICES}"
            )
            
        valid_platforms = SUPPORTED_DEVICES[manufacturer]
        if platform.lower() not in valid_platforms:
            raise ValueError(
                f"UpgradePackage initialization failed: Invalid platform '{platform}' for manufacturer '{manufacturer}'. "
                f"Valid platforms: {valid_platforms}"
            )

    # ── Orchestration ─────────────────────────────────────────────────

    def run_stage(self, stage: str) -> StageResult:
        """Executes a single workflow stage using the dynamic registry."""
        # Special case: built-in logic for generic wait/ping if not overriden
        if stage == 'post_activation_wait':
            return self._handle_wait()

        try:
            # Multi-manufacturer dispatch via registry
            return global_registry.execute_stage(stage, self.ctx)
        except Exception as e:
            msg = f"Stage '{stage}' failed: {e}"
            self.ctx.errors.append(msg)
            self.ctx.failed_stage = stage
            return StageResult(success=False, message=msg, errors=[msg])

    def execute(self) -> Dict[str, Any]:
        """Runs the complete sequence of upgrade stages."""
        for stage in self.STAGES:
            # The 'diff' stage is a special teardown stage always executed
            if self.ctx.failed_stage and stage != 'diff':
                continue
            self.run_stage(stage)
        
        return {name: res.model_dump() for name, res in self.ctx.stage_results.items()}

    # ── Built-in Handlers ─────────────────────────────────────────────

    def _handle_wait(self) -> StageResult:
        """Generic stabilization logic used across vendors."""
        if self.ctx.connection_mode in ('mock', 'dry_run'):
            res = StageResult(success=True, message="[MOCK] Stabilization done")
        else:
            # 10m pause + Ping sweep (simplified)
            time.sleep(600)
            res = StageResult(success=True, message="Stabilization delay completed")
        
        self.ctx.stage_results['post_activation_wait'] = res
        return res

    # ── Compatibility Aliases ─────────────────────────────────────────

    @property
    def success(self) -> bool: return self.ctx.failed_stage is None and len(self.ctx.stage_results) > 0
    
    @property
    def connection_mode(self) -> str: return self.ctx.connection_mode

    @connection_mode.setter
    def connection_mode(self, value: str):
        self.ctx.connection_mode = value
        self._connection_manager.connection_mode = value

    @property
    def golden_image(self) -> GoldenImage: return self.ctx.golden_image

    @golden_image.setter
    def golden_image(self, value: GoldenImage):
        self.ctx.golden_image = value

    @property
    def file_server(self) -> FileServer: return self.ctx.file_server

    @file_server.setter
    def file_server(self, value: FileServer):
        self.ctx.file_server = value
    
    @property
    def stage_results(self) -> Dict[str, Any]: return self.execute() # For legacy callers
    
    @property
    def errors(self) -> List[str]: return self.ctx.errors
    
    @property
    def context(self) -> ExecutionContext: return self.ctx
    
    @property
    def device_info(self) -> Dict[str, Any]: return self.ctx.device_info.model_dump()
