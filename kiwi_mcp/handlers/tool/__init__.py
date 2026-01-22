"""Tool handler module with executor abstraction."""

from .manifest import ToolManifest
from .executors import ExecutorRegistry, ToolExecutor, ExecutionResult

# Import ToolHandler lazily to avoid dependency issues
try:
    from .handler import ToolHandler

    __all__ = ["ToolHandler", "ToolManifest", "ExecutorRegistry", "ToolExecutor", "ExecutionResult"]
except ImportError:
    ToolHandler = None
    __all__ = ["ToolManifest", "ExecutorRegistry", "ToolExecutor", "ExecutionResult"]
