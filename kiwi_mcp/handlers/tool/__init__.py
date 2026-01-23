"""Tool handler module with executor abstraction."""

from .manifest import ToolManifest
from kiwi_mcp.primitives.executor import PrimitiveExecutor, ExecutionResult

# Import ToolHandler lazily to avoid dependency issues
try:
    from .handler import ToolHandler

    __all__ = ["ToolHandler", "ToolManifest", "PrimitiveExecutor", "ExecutionResult"]
except ImportError:
    ToolHandler = None
    __all__ = ["ToolManifest", "PrimitiveExecutor", "ExecutionResult"]
