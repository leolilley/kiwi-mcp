"""Tool handler module with schema-driven extraction."""

from kiwi_mcp.primitives.executor import PrimitiveExecutor, ExecutionResult
from kiwi_mcp.schemas import extract_tool_metadata, validate_tool_metadata

try:
    from .handler import ToolHandler

    __all__ = ["ToolHandler", "PrimitiveExecutor", "ExecutionResult", "extract_tool_metadata", "validate_tool_metadata"]
except ImportError:
    ToolHandler = None
    __all__ = ["PrimitiveExecutor", "ExecutionResult", "extract_tool_metadata", "validate_tool_metadata"]
