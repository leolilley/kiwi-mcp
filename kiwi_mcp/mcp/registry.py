from dataclasses import dataclass
from typing import Optional
import os


@dataclass
class MCPConfig:
    name: str
    transport: str  # stdio | sse | websocket
    command: Optional[str] = None
    args: list[str] = None
    env: dict[str, str] = None
    url: Optional[str] = None


# Built-in MCP configurations
MCP_REGISTRY: dict[str, MCPConfig] = {
    "supabase": MCPConfig(
        name="supabase",
        transport="stdio",
        command="npx",
        args=["-y", "@supabase/mcp-server"],
        env={"SUPABASE_ACCESS_TOKEN": "${SUPABASE_ACCESS_TOKEN}"},
    ),
    "github": MCPConfig(
        name="github",
        transport="stdio",
        command="npx",
        args=["-y", "@anthropic/mcp-github"],
        env={"GITHUB_TOKEN": "${GITHUB_TOKEN}"},
    ),
    "filesystem": MCPConfig(
        name="filesystem",
        transport="stdio",
        command="npx",
        args=["-y", "@anthropic/mcp-filesystem"],
        env={},
    ),
}


def get_mcp_config(name: str) -> Optional[MCPConfig]:
    return MCP_REGISTRY.get(name)


def register_mcp(name: str, config: MCPConfig) -> None:
    MCP_REGISTRY[name] = config
