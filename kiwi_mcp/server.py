#!/usr/bin/env python3
"""
Kiwi MCP Server - Unified MCP with 4 tools for directives, scripts, and knowledge.
"""

import argparse
import asyncio
import json
import logging
import os
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


def validate_rag_config() -> dict:
    """Validate RAG configuration - MANDATORY for MCP operation."""
    embedding_url = os.getenv("EMBEDDING_URL")
    vector_db_url = os.getenv("VECTOR_DB_URL")
    
    errors = []
    if not embedding_url:
        errors.append("EMBEDDING_URL is required")
    if not vector_db_url:
        errors.append("VECTOR_DB_URL is required")
    
    if errors:
        error_msg = "\n".join([
            "RAG configuration missing. Kiwi MCP requires vector search.",
            "",
            "Missing:",
            *[f"  - {e}" for e in errors],
            "",
            "Configure via MCP client settings:",
            '  "env": {',
            '    "EMBEDDING_URL": "https://api.openai.com/v1/embeddings",',
            '    "EMBEDDING_API_KEY": "sk-...",',
            '    "VECTOR_DB_URL": "postgresql://...",',
            '  }',
            "",
            "Or set environment variables:",
            "  export EMBEDDING_URL=...",
            "  export VECTOR_DB_URL=...",
            "",
            "Setup help: python -m kiwi_mcp.setup_rag",
        ])
        raise ValueError(error_msg)
    
    return {
        "embedding_url": embedding_url,
        "embedding_key": os.getenv("EMBEDDING_API_KEY", ""),
        "embedding_model": os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        "vector_db_url": vector_db_url,
    }


class KiwiMCP:
    """Unified Kiwi MCP server with 4 tools."""

    def __init__(self):
        # MANDATORY: Validate RAG config first
        self.rag_config = validate_rag_config()
        self.logger = logging.getLogger("KiwiMCP")
        self.logger.info(f"RAG configured: embedding_url={self.rag_config['embedding_url']}")
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
