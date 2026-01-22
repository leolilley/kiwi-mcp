from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ExecutionResult:
    """Result of tool execution."""

    success: bool
    output: str
    error: Optional[str] = None
    duration_ms: float = 0


class ToolExecutor(ABC):
    """Abstract base class for tool executors."""

    @abstractmethod
    async def execute(self, manifest: "ToolManifest", params: dict) -> ExecutionResult:
        """Execute a tool with the given parameters.

        Args:
            manifest: Tool manifest describing the tool
            params: Parameters to pass to the tool

        Returns:
            ExecutionResult with success status and output
        """
        pass

    @abstractmethod
    def can_execute(self, manifest: "ToolManifest") -> bool:
        """Check if this executor can handle the given manifest.

        Args:
            manifest: Tool manifest to check

        Returns:
            True if this executor can handle the tool type
        """
        pass
