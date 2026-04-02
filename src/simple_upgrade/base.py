"""
Base Task and Execution Context classes.
"""

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, TypeVar, Generic

from .models import GoldenImage, FileServer, DeviceInfo, StageResult
from .connection_manager import ConnectionManager


class ExecutionContext:
    """
    Mutable state shared across the orchestrated upgrade stages.
    """

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

        # Mutable results
        self.device_info = DeviceInfo()
        self.stage_results: Dict[str, StageResult] = {}
        self.errors: List[str] = []
        self.failed_stage: Optional[str] = None
        self.current_stage: Optional[str] = None
        self.data: Dict[str, Any] = {}


class BaseTask(ABC):
    """
    Abstract base class for all upgrade tasks.
    """

    def __init__(self, context: ExecutionContext):
        self.ctx = context
        self.start_time: float = 0.0
        self.end_time: float = 0.0

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the stage."""
        pass

    def execute(self, **kwargs) -> StageResult:
        """
        Public methods to run the task with built-in timing and lifecycle hooks.
        """
        self.start_time = time.time()
        
        # Pre-execute hook
        try:
            self.pre_execute(**kwargs)
        except Exception as e:
            return self._fail(f"Pre-execution failed: {e}")

        # Core logic
        try:
            result = self.run(**kwargs)
        except Exception as e:
            result = self._fail(f"Execution failed: {e}")

        self.end_time = time.time()
        result.duration = self.end_time - self.start_time
        
        # Capture result in context
        self.ctx.stage_results[self.name] = result
        if not result.success:
            self.ctx.failed_stage = self.name
            self.ctx.errors.extend(result.errors)

        return result

    def pre_execute(self, **kwargs):
        """Optional hook to run before the main task."""
        pass

    @abstractmethod
    def run(self, **kwargs) -> StageResult:
        """Core task logic to be implemented by manufacturers."""
        pass

    def _success(self, message: str = "", data: Optional[Dict[str, Any]] = None, **kwargs) -> StageResult:
        """Helper to create a successful StageResult."""
        return StageResult(success=True, message=message, data=data or {}, **kwargs)

    def _fail(self, message: str, errors: Optional[List[str]] = None, **kwargs) -> StageResult:
        """Helper to create a failed StageResult."""
        err_list = errors or [message]
        return StageResult(success=False, message=message, errors=err_list, **kwargs)
