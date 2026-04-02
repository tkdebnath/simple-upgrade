"""
Registry for stage-based manufacturer dispatching.
"""

from typing import Dict, Any, Type, Optional, Callable, Union
from .base import BaseTask, ExecutionContext, StageResult

# Type alias for functional tasks: (context, **kwargs) -> StageResult
FunctionalTask = Callable[[ExecutionContext, Any], StageResult]
TaskImplementation = Union[Type[BaseTask], FunctionalTask]


class TaskRegistry:
    """
    Centralized dispatcher to manage stage implementations for different manufacturers.
    """

    def __init__(self):
        # Format: {(stage, manufacturer): TaskImplementation}
        self._registry: Dict[tuple, TaskImplementation] = {}

    def register(self, stage: str, manufacturer: str, implementation: TaskImplementation):
        """Register a class or function for a specific stage and manufacturer."""
        key = (stage.lower(), manufacturer.lower())
        self._registry[key] = implementation

    def execute_stage(self, stage: str, context: ExecutionContext, **kwargs) -> StageResult:
        """Standard dispatcher for executing a stage across any manufacturer."""
        stage = stage.lower()
        manufacturer = context.manufacturer.lower()
        key = (stage, manufacturer)
        
        # Track current stage in context
        context.current_stage = stage
        
        if key not in self._registry:
            # Fallback to 'generic' if manufacturer-specific not found
            generic_key = (stage, 'generic')
            if generic_key in self._registry:
                key = generic_key
            else:
                raise ValueError(f"No implementation for stage '{stage}' and manufacturer '{manufacturer}'")

        handler = self._registry[key]

        # If it's a Task class, instantiate and execute
        if isinstance(handler, type) and issubclass(handler, BaseTask):
            task = handler(context)
            return task.execute(**kwargs)

        # If it's a function, call it directly
        return handler(context, **kwargs)


# Global registry instance
global_registry = TaskRegistry()


def register_stage(stage: str, manufacturer: str):
    """Decorator to easily register functional or class-based manufacturer stages."""
    def decorator(impl: TaskImplementation):
        global_registry.register(stage, manufacturer, impl)
        return impl
    return decorator
