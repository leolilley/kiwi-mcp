"""
Lilux MCP Kernel

5 primitive tools for AI agent orchestration:
- search: Find directives, tools, knowledge
- load: Get/copy items between locations
- execute: Run directives and tools
- sign: Validate and sign items
- help: Kernel documentation

Install: pip install lilux
"""

__version__ = "0.1.0"

from lilux.server import main

__all__ = ["main", "__version__"]
