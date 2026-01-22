from typing import Optional
import asyncio
from .client import MCPClient
from .registry import get_mcp_config


class MCPClientPool:
    """Pool of MCP client connections with lazy initialization."""

    def __init__(self):
        self._clients: dict[str, MCPClient] = {}
        self._schemas: dict[str, list[dict]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def get_client(self, mcp_name: str) -> MCPClient:
        """Get or create MCP client connection."""
        if mcp_name not in self._locks:
            self._locks[mcp_name] = asyncio.Lock()

        async with self._locks[mcp_name]:
            if mcp_name not in self._clients:
                config = get_mcp_config(mcp_name)
                if not config:
                    raise ValueError(f"Unknown MCP: {mcp_name}")

                client = MCPClient(config)
                await client.connect()
                self._clients[mcp_name] = client
                self._schemas[mcp_name] = await client.list_tools()

            return self._clients[mcp_name]

    async def get_tool_schemas(self, mcp_name: str, tool_filter: list[str] = None) -> list[dict]:
        """Get tool schemas, optionally filtered."""
        await self.get_client(mcp_name)  # Ensure connected

        schemas = self._schemas[mcp_name]
        if tool_filter:
            schemas = [s for s in schemas if s["name"] in tool_filter]

        return schemas

    async def call_tool(self, mcp_name: str, tool_name: str, arguments: dict) -> dict:
        """Call a tool through the pool."""
        client = await self.get_client(mcp_name)
        return await client.call_tool(tool_name, arguments)

    async def close_all(self) -> None:
        """Close all connections."""
        for client in self._clients.values():
            await client.close()
        self._clients.clear()
        self._schemas.clear()
