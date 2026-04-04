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
        source_interface: Optional[str] = None,  # Elevated connectivity property
        source_vrf: Optional[str] = None,        # Elevated VRF context constraint
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

        # Transparently proxy root parameters down into the file engine map
        if source_interface and "source_interface" not in file_server:
            file_server["source_interface"] = source_interface
        if source_vrf and "source_vrf" not in file_server:
            file_server["source_vrf"] = source_vrf

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

        # 3. LINT GLOBAL DEVICE PROFILES
        import os
        from .config_validator import ProfileValidator
        profiles_dir = os.path.join(os.path.dirname(__file__), "device_profiles")
        validator = ProfileValidator(profiles_dir)
        validator.validate_all()

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
        """Intelligently sweep and wait for the device to reload and restore SSH."""
        if self.ctx.connection_mode in ('mock', 'dry_run'):
            res = StageResult(success=True, message="[MOCK] Stabilization done")
            self.ctx.stage_results['post_activation_wait'] = res
            return res

        import socket
        
        host = self.host
        port = self.device_kwargs.get("port", 22)
        
        # Pull timers from device_kwargs root or use standard defaults
        wait_delay  = self.device_kwargs.get("post_wait_delay", 30)
        max_retries = self.device_kwargs.get("post_wait_retries", 60)
        convergence = self.device_kwargs.get("post_wait_convergence", 60)
        
        # 1. Immediate severance: Safely close existing SSH sockets
        try:
            self._connection_manager.disconnect()
        except Exception:
            pass

        # 2. Wait for device to go OFF-LINE safely
        self._log_wait(f"Waiting {wait_delay}s for {host} to go offline...")
        time.sleep(wait_delay)
            
        # 3. Smart Sweep for Up-state (TCP Socket on port)
        self._log_wait(f"Beginning SSH TCP Sweep on {host}:{port} (Max Retries: {max_retries})...")
        is_up = False
        
        for attempt in range(max_retries):
            try:
                # Try a 3-second TCP handshake on the exact SSH port
                with socket.create_connection((host, port), timeout=3):
                    is_up = True
                    self._log_wait(f"TCP {port} is OPEN! Device is back online (attempt {attempt+1}).")
                    break
            except (socket.timeout, ConnectionRefusedError, OSError):
                # Device is still rebooting
                print(".", end="", flush=True)
                time.sleep(15)
                
        if not is_up:
            msg = f"Device {host} completely failed to return online after {max_retries * 15} seconds."
            res = StageResult(success=False, message=msg, errors=[msg])
            self.ctx.stage_results['post_activation_wait'] = res
            return res

        # 4. Stabilization Delay
        # SSH port might be open instantly, but routing protocols/BGP need time to converge
        self._log_wait(f"SSH port detected! Waiting {convergence}s for STP and Routing convergence...")
        time.sleep(convergence)
        
        res = StageResult(success=True, message="Device reloaded and completely stabilized.")
        self.ctx.stage_results['post_activation_wait'] = res
        return res

    def _log_wait(self, msg: str) -> None:
        print(f"[wait] {msg}")

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
