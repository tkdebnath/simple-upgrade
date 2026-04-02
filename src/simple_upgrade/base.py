"""
Core abstractions for the simple-upgrade framework.
Consolidated models and base classes for minimal clear code.
"""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field, field_validator
from .connection_manager import ConnectionManager


# ── Models ───────────────────────────────────────────────────────────

class GoldenImage(BaseModel):
    version: str
    image_name: str
    image_size: Optional[int] = None
    md5: Optional[str] = None
    sha256: Optional[str] = None

    @field_validator('image_name')
    @classmethod
    def validate_image_name(cls, v: str) -> str:
        if not v.strip(): raise ValueError("image_name cannot be empty")
        return v


class FileServer(BaseModel):
    ip: str
    protocol: str = "http"
    base_path: str = ""
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    source_interface: Optional[str] = None


class DeviceInfo(BaseModel):
    manufacturer: str = "Unknown"
    model: Optional[str] = None
    version: Optional[str] = None
    hostname: Optional[str] = None
    serial: Optional[str] = None
    platform: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class StageResult(BaseModel):
    success: bool
    message: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    duration: float = 0.0
    command: Optional[str] = None
    skipped: bool = False


# ── Context & Tasks ──────────────────────────────────────────────────

class ExecutionContext:
    def __init__(
        self,
        connection_manager: ConnectionManager,
        golden_image: GoldenImage,
        file_server: FileServer,
        connection_mode: str = "normal",
        device_type: Optional[str] = None,
        manufacturer: str = "unknown"
    ):
        self.cm = connection_manager
        self.golden_image = golden_image
        self.file_server = file_server
        self.connection_mode = connection_mode
        self.device_type = device_type
        self.manufacturer = manufacturer.lower()
        self.device_info = DeviceInfo()
        self.stage_results: Dict[str, StageResult] = {}
        self.errors: List[str] = []
        self.failed_stage: Optional[str] = None
        self.current_stage: Optional[str] = None
        self.data: Dict[str, Any] = {}


class BaseTask(ABC):
    def __init__(self, context: ExecutionContext):
        self.ctx = context
        self.start_time: float = 0.0

    @property
    @abstractmethod
    def name(self) -> str: pass

    @property
    def conn(self):
        """Shortcut for Scrapli connection."""
        return self.ctx.cm.get_connection('scrapli')

    @property
    def unicon(self):
        """Shortcut for Unicon connection."""
        return self.ctx.cm.get_connection('unicon')

    def execute(self, **kwargs) -> StageResult:
        self.start_time = time.time()
        try:
            self.pre_execute(**kwargs)
            result = self.run(**kwargs)
        except Exception as e:
            result = self._fail(f"Execution failed: {e}")

        result.duration = time.time() - self.start_time
        self.ctx.stage_results[self.name] = result
        if not result.success:
            self.ctx.failed_stage = self.name
            self.ctx.errors.extend(result.errors)
        return result

    def pre_execute(self, **kwargs): pass

    @abstractmethod
    def run(self, **kwargs) -> StageResult: pass

    def _success(self, msg: str = "", data: Optional[Dict] = None, **kwargs) -> StageResult:
        return StageResult(success=True, message=msg, data=data or {}, **kwargs)

    def _fail(self, msg: str, errors: Optional[List] = None, **kwargs) -> StageResult:
        return StageResult(success=False, message=msg, errors=errors or [msg], **kwargs)
