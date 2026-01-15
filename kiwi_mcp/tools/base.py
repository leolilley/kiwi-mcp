"""Base tool class."""

from abc import ABC, abstractmethod
import json
from mcp.types import Tool


class BaseTool(ABC):
    """Base class for all tools."""

    @property
    @abstractmethod
    def schema(self) -> Tool:
        """Return MCP tool schema."""
        pass

    @property
    def inputSchema(self) -> dict:
        """Get inputSchema from tool schema."""
        return self.schema.inputSchema

    @abstractmethod
    async def execute(self, arguments: dict) -> str:
        """Execute the tool with given arguments."""
        pass

    def _format_response(self, data: dict) -> str:
        """Format response as JSON string."""
        return json.dumps(data, indent=2)
