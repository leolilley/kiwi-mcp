"""
API clients for registry operations.
"""

from kiwi_mcp.api.base import BaseRegistry
from kiwi_mcp.api.directive_registry import DirectiveRegistry
from kiwi_mcp.api.knowledge_registry import KnowledgeRegistry
from kiwi_mcp.api.tool_registry import ToolRegistry

# Backward compatibility - ScriptRegistry is now deprecated
# Use ToolRegistry instead
from kiwi_mcp.api.script_registry import ScriptRegistry  # deprecated

__all__ = [
    "BaseRegistry",
    "DirectiveRegistry",
    "KnowledgeRegistry",
    "ToolRegistry",
    "ScriptRegistry",  # deprecated, use ToolRegistry
]
