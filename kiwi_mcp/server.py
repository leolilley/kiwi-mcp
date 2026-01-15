#!/usr/bin/env python3
"""
Kiwi MCP Server - Unified MCP with 4 tools for directives, scripts, and knowledge.
"""

import argparse
import asyncio
import json
import logging
from dotenv import load_dotenv

load_dotenv()

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel import NotificationOptions
from mcp.types import Tool, TextContent

from kiwi_mcp.tools.search import SearchTool
from kiwi_mcp.tools.load import LoadTool
from kiwi_mcp.tools.execute import ExecuteTool
from kiwi_mcp.tools.help import HelpTool


__version__ = "0.1.0"
__package_name__ = "kiwi-mcp"


class KiwiMCP:
    """Unified Kiwi MCP server with 4 tools."""

    def __init__(self):
        self.logger = logging.getLogger("KiwiMCP")
        self.server = Server(__package_name__)
        
        # Initialize tools (handlers are created dynamically per request)
        self.tools = {
            "search": SearchTool(),
            "load": LoadTool(),
            "execute": ExecuteTool(),
            "help": HelpTool(),
        }
        self._setup_handlers()

    def _setup_handlers(self):
        """Register MCP handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """Return all 4 unified tools."""
            return [tool.schema for tool in self.tools.values()]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            """Dispatch to appropriate tool."""
            if name not in self.tools:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({"error": f"Unknown tool: {name}"}),
                    )
                ]

            try:
                result = await self.tools[name].execute(arguments)
                return [TextContent(type="text", text=result)]
            except Exception as e:
                import traceback
                error = {"error": str(e), "traceback": traceback.format_exc()}
                return [TextContent(type="text", text=json.dumps(error, indent=2))]

    async def start(self):
        """Start the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name=__package_name__,
                    server_version=__version__,
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={}
                    ),
                ),
            )


async def run_stdio():
    """Run in stdio mode (for Cursor/Claude connection)."""
    mcp = KiwiMCP()
    await mcp.start()


def main():
    parser = argparse.ArgumentParser(description="Kiwi MCP Server")
    parser.add_argument("--stdio", action="store_true", help="Run in stdio mode (default)")
    args = parser.parse_args()
    
    asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
