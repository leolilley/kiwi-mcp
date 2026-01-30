#!/usr/bin/env python3
"""
RYE MCP Server - AI operating system running on Lilux microkernel.

Exposes 5 intelligent MCP tools that understand content shapes
and delegate to Lilux microkernel primitives for execution.
"""

import argparse
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel import NotificationOptions
from mcp.types import Tool, TextContent

# RYE's 5 intelligent MCP tools (create stubs first)
# from rye.tools.search import SearchTool
# from rye.tools.load import LoadTool
# from rye.tools.execute import ExecuteTool
# from rye.tools.sign import SignTool
# from rye.tools.help import HelpTool

__version__ = "0.1.0"
__package_name__ = "rye"


class RYE:
    """RYE OS - Intelligence layer running on Lilux microkernel."""

    def __init__(self):
        self.server = Server(__package_name__)
        self._setup_handlers()

    def _setup_handlers(self):
        """Register MCP handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """Return all 5 RYE tools."""
            # TODO: Return tools when implemented
            return []

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            """Dispatch to appropriate RYE tool."""
            # TODO: Dispatch to tools when implemented
            return [TextContent(type="text", text=f"Tool '{name}' not yet implemented")]

    async def start(self):
        """Start RYE MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name=__package_name__,
                    server_version=__version__,
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(), experimental_capabilities={}
                    ),
                ),
            )


async def run_stdio():
    """Run in stdio mode (for Cursor/Claude connection)."""
    rye = RYE()
    await rye.start()


def main():
    parser = argparse.ArgumentParser(description="RYE - AI operating system")
    parser.add_argument("--stdio", action="store_true", help="Run in stdio mode (default)")
    args = parser.parse_args()
    asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
