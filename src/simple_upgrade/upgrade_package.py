"""
UpgradePackage - High-level dynamic firmware upgrade orchestrator.
"""

import time
import subprocess
import platform as py_platform
from typing import Dict, Any, Optional, List

from .connection_manager import ConnectionManager
from .models import GoldenImage, FileServer, DeviceInfo, StageResult
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
        'verification'
    ]

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 22,
        manufacturer: str = "cisco",
        golden_image: Optional[Dict[str, Any]] = None,
        file_server: Optional[Dict[str, Any]] = None,
        device_type: Optional[str] = None,
        connection_mode: str = "normal",
        **kwargs
    ):
        self.host = host
        self.device_kwargs = kwargs
        
        # Initialize Core components
        self._connection_manager = ConnectionManager(
            host=host, username=username, password=password, port=port,
            device_type=device_type, connection_mode=connection_mode,
            **kwargs
        )

        self.ctx = ExecutionContext(
            connection_manager=self._connection_manager,
            golden_image=GoldenImage(**(golden_image or {"version": "unknown", "image_name": "unknown"})),
            file_server=FileServer(**(file_server or {"ip": "127.0.0.1"})),
            connection_mode=connection_mode,
            device_type=device_type,
            manufacturer=manufacturer
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
            if self.ctx.failed_stage:
                break
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
    def stage_results(self) -> Dict[str, Any]: return self.execute() # For legacy callers
    
    @property
    def errors(self) -> List[str]: return self.ctx.errors
    
    @property
    def context(self) -> ExecutionContext: return self.ctx
    
    @property
    def device_info(self) -> Dict[str, Any]: return self.ctx.device_info.model_dump()
