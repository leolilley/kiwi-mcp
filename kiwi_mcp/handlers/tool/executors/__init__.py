from typing import Optional, Dict
from .base import ToolExecutor, ExecutionResult


class ExecutorRegistry:
    """Registry for tool executors based on tool type."""

    _executors: Dict[str, ToolExecutor] = {}

    @classmethod
    def register(cls, tool_type: str, executor: ToolExecutor) -> None:
        """Register an executor for a specific tool type.

        Args:
            tool_type: Type of tool (e.g., 'python', 'bash', 'api')
            executor: Executor instance to handle this tool type
        """
        cls._executors[tool_type] = executor

    @classmethod
    def get(cls, tool_type: str) -> Optional[ToolExecutor]:
        """Get executor for a tool type.

        Args:
            tool_type: Type of tool to get executor for

        Returns:
            Executor instance or None if not found
        """
        return cls._executors.get(tool_type)

    @classmethod
    def list_types(cls) -> list[str]:
        """List all registered tool types.

        Returns:
            List of registered tool type names
        """
        return list(cls._executors.keys())

    @classmethod
    def clear(cls) -> None:
        """Clear all registered executors (mainly for testing)."""
        cls._executors.clear()


__all__ = ["ExecutorRegistry", "ToolExecutor", "ExecutionResult"]
