# Dynamic Tools Architecture: LLM-Created Tools & MCP Integration

**Date:** 2026-01-23  
**Status:** Draft  
**Related:** [DATABASE_EVOLUTION_DESIGN.md](./DATABASE_EVOLUTION_DESIGN.md), [KIWI_HARNESS_ROADMAP.md](./KIWI_HARNESS_ROADMAP.md)

---

## Vision

**Tools are data, not code.** An LLM should be able to:
1. Create a new tool by providing a manifest + implementation
2. Publish it to the registry
3. Other agents discover and use it dynamically

The executor types (python, bash, api, docker, mcp) are the **primitives** - they're the runtime engines. But specific tools are **declarative definitions** stored in the registry.

---

## Current vs Target Architecture

### ❌ Current: Hard-coded Executors

```
Code (hard-coded)                    Registry (data)
┌─────────────────┐                  ┌──────────────────┐
│ PythonExecutor  │◄─── manifest ────│ scripts table    │
│ BashExecutor    │                  │ (Python only)    │
│ APIExecutor     │                  └──────────────────┘
│ MCPExecutor     │ (not implemented)
└─────────────────┘
        │
        ▼
   Actually runs code
```

**Problems:**
- MCP configs are hard-coded in `mcp/registry.py`
- No MCPExecutor to route `tool_type: mcp` tools
- Can't dynamically add new MCP servers via registry

### ✅ Target: Dynamic Tool Resolution

```
Executor Primitives                  Tool Registry (ALL tools as data)
┌─────────────────┐                  ┌──────────────────────────────────┐
│ PythonExecutor  │                  │ tools table                      │
│ BashExecutor    │◄── resolve ──────│ ├─ email_enricher (python)       │
│ APIExecutor     │                  │ ├─ deploy_staging (bash)         │
│ DockerExecutor  │                  │ ├─ stripe_charge (api)           │
│ MCPExecutor     │                  │ ├─ supabase_query (mcp)          │
└─────────────────┘                  │ ├─ github_create_pr (mcp)        │
        │                            │ └─ custom_llm_tool (python)      │
        │                            └──────────────────────────────────┘
        ▼                                         │
   Execute based on                               │
   tool_type in manifest                          ▼
                                     LLM can CREATE new tools here!
```

---

## Key Insight: MCP as a Tool Type

An MCP tool in our registry is just **routing metadata**:

```yaml
# tool.yaml for an MCP-backed tool
tool_id: supabase_execute_sql
tool_type: mcp
version: 1.0.0
description: Execute SQL queries on Supabase
executor_config:
  mcp_server: supabase              # Which MCP to route to
  mcp_tool: execute_sql             # Which tool on that MCP
  transport: stdio
  command: npx
  args: ["-y", "@supabase/mcp-server"]
  env:
    SUPABASE_ACCESS_TOKEN: "${SUPABASE_ACCESS_TOKEN}"
parameters:
  - name: project_id
    type: string
    required: true
  - name: query
    type: string
    required: true
```

When an agent calls this tool:
1. Kiwi looks up `supabase_execute_sql` in registry
2. Sees `tool_type: mcp`
3. Routes to `MCPExecutor`
4. MCPExecutor connects to the Supabase MCP server
5. Calls `execute_sql` with parameters
6. Returns result

**The MCP server config IS the tool definition.**

---

## Database Schema for Dynamic Tools

### Extended `tools` Table

```sql
-- Add fields needed for dynamic tool creation
ALTER TABLE tools ADD COLUMN IF NOT EXISTS 
    mcp_server_config JSONB;  -- For MCP tools: server connection details

-- For MCP tools, executor_config in manifest contains:
-- {
--   "mcp_server": "supabase",
--   "mcp_tool": "execute_sql", 
--   "transport": "stdio",
--   "command": "npx",
--   "args": ["-y", "@supabase/mcp-server"],
--   "env": {"SUPABASE_ACCESS_TOKEN": "${SUPABASE_ACCESS_TOKEN}"}
-- }
```

### `mcp_servers` Table (Optional - for reusable server configs)

```sql
-- Reusable MCP server configurations
CREATE TABLE mcp_servers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,         -- e.g., "supabase", "github"
    transport TEXT NOT NULL,           -- stdio | sse | websocket
    command TEXT,                      -- e.g., "npx"
    args TEXT[],                       -- e.g., ["-y", "@supabase/mcp-server"]
    env JSONB,                         -- env vars needed
    url TEXT,                          -- for SSE/websocket transport
    is_official BOOLEAN DEFAULT false,
    schema_cache JSONB,                -- Cached tool schemas from server
    schema_cached_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Example data
INSERT INTO mcp_servers (name, transport, command, args, env, is_official) VALUES
('supabase', 'stdio', 'npx', ARRAY['-y', '@supabase/mcp-server'], 
 '{"SUPABASE_ACCESS_TOKEN": "${SUPABASE_ACCESS_TOKEN}"}', true),
('github', 'stdio', 'npx', ARRAY['-y', '@anthropic/mcp-github'],
 '{"GITHUB_TOKEN": "${GITHUB_TOKEN}"}', true),
('filesystem', 'stdio', 'npx', ARRAY['-y', '@anthropic/mcp-filesystem'],
 '{}', true);
```

---

## How LLMs Create Tools Dynamically

### Scenario: LLM Creates a Custom API Tool

```python
# LLM wants to create a tool to call a new API
tool_manifest = {
    "tool_id": "weather_forecast",
    "tool_type": "api",
    "version": "1.0.0",
    "description": "Get weather forecast for a location",
    "executor_config": {
        "method": "GET",
        "url_template": "https://api.weather.com/forecast?lat={lat}&lon={lon}",
        "headers": {
            "Authorization": "Bearer ${WEATHER_API_KEY}"
        },
        "response_path": "$.forecast.daily"
    },
    "parameters": [
        {"name": "lat", "type": "number", "required": True},
        {"name": "lon", "type": "number", "required": True}
    ]
}

# LLM calls: execute(item_type="tool", action="create", ...)
result = await tool_handler.create(tool_manifest)
# Tool is now in registry and usable!
```

### Scenario: LLM Wraps an MCP Server

```python
# LLM discovers a new MCP server and wants to expose its tools
tool_manifest = {
    "tool_id": "notion_create_page",
    "tool_type": "mcp",
    "version": "1.0.0", 
    "description": "Create a new page in Notion",
    "executor_config": {
        "mcp_server": "notion",  # Reference to mcp_servers table or inline config
        "mcp_tool": "create_page",
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@notionhq/mcp-server"],
        "env": {"NOTION_API_KEY": "${NOTION_API_KEY}"}
    },
    "parameters": [
        {"name": "parent_id", "type": "string", "required": True},
        {"name": "title", "type": "string", "required": True},
        {"name": "content", "type": "string", "required": False}
    ]
}

result = await tool_handler.create(tool_manifest)
```

### Scenario: LLM Creates a Python Tool

```python
# LLM writes a new Python script tool
tool_content = '''
"""
Enrich email addresses with company information.
"""
import httpx

async def run(email: str) -> dict:
    domain = email.split("@")[1]
    response = await httpx.get(f"https://clearbit.com/v1/companies/{domain}")
    return response.json()
'''

tool_manifest = {
    "tool_id": "email_enricher",
    "tool_type": "python",
    "version": "1.0.0",
    "description": "Enrich email with company info from Clearbit",
    "executor_config": {
        "entrypoint": "main.py",
        "requires": ["httpx"]
    },
    "parameters": [
        {"name": "email", "type": "string", "required": True}
    ]
}

# Create tool with manifest + code file
result = await tool_handler.create(tool_manifest, files={"main.py": tool_content})
```

---

## MCPExecutor Implementation

```python
# kiwi_mcp/handlers/tool/executors/mcp.py

from .base import ToolExecutor, ExecutionResult
from kiwi_mcp.mcp.pool import MCPClientPool
from kiwi_mcp.handlers.tool.manifest import ToolManifest


class MCPExecutor(ToolExecutor):
    """Executor that routes to external MCP servers."""
    
    def __init__(self, pool: MCPClientPool):
        self.pool = pool
    
    async def execute(
        self, 
        manifest: ToolManifest, 
        parameters: dict
    ) -> ExecutionResult:
        """Route tool call to external MCP server."""
        config = manifest.executor_config
        
        # Get or create MCP client connection
        mcp_server = config.get("mcp_server")
        mcp_tool = config.get("mcp_tool")
        
        if not mcp_server or not mcp_tool:
            return ExecutionResult(
                success=False,
                error="MCP tool must specify mcp_server and mcp_tool"
            )
        
        # Connect to MCP server (pool handles caching)
        client = await self.pool.get_or_create(
            name=mcp_server,
            transport=config.get("transport", "stdio"),
            command=config.get("command"),
            args=config.get("args", []),
            env=config.get("env", {}),
            url=config.get("url")
        )
        
        # Call the tool on the MCP server
        result = await client.call_tool(mcp_tool, parameters)
        
        return ExecutionResult(
            success=True,
            output=result
        )
```

---

## Tool Discovery & Resolution Flow

```
Agent wants to use "supabase_execute_sql"
                │
                ▼
┌───────────────────────────────────┐
│ 1. Search Registry                │
│    search_tools_hybrid(           │
│      "supabase execute sql",      │
│      embedding                    │
│    )                              │
└───────────────┬───────────────────┘
                │
                ▼
┌───────────────────────────────────┐
│ 2. Load Tool Manifest             │
│    SELECT * FROM tools            │
│    JOIN tool_versions             │
│    WHERE tool_id = 'supabase_...' │
└───────────────┬───────────────────┘
                │
                ▼
┌───────────────────────────────────┐
│ 3. Route to Executor              │
│    tool_type = 'mcp'              │
│    → MCPExecutor.execute()        │
└───────────────┬───────────────────┘
                │
                ▼
┌───────────────────────────────────┐
│ 4. MCPExecutor routes to server   │
│    Connect to Supabase MCP        │
│    Call execute_sql(params)       │
│    Return result                  │
└───────────────────────────────────┘
```

---

## Auto-Discovery of MCP Tools

When an MCP server is registered, we can auto-discover its tools:

```python
async def discover_mcp_tools(mcp_server_name: str) -> list[dict]:
    """Connect to MCP server and discover available tools."""
    client = await pool.get_or_create(mcp_server_name)
    
    # MCP servers expose their tool schemas
    tools = await client.list_tools()
    
    # Create tool entries for each discovered tool
    created_tools = []
    for tool in tools:
        manifest = {
            "tool_id": f"{mcp_server_name}_{tool['name']}",
            "tool_type": "mcp",
            "version": "1.0.0",
            "description": tool.get("description", ""),
            "executor_config": {
                "mcp_server": mcp_server_name,
                "mcp_tool": tool["name"]
            },
            "parameters": tool.get("inputSchema", {}).get("properties", [])
        }
        result = await tool_handler.create(manifest)
        created_tools.append(result)
    
    return created_tools

# Usage:
# await discover_mcp_tools("supabase")
# Creates: supabase_execute_sql, supabase_apply_migration, etc.
```

---

## Migration from Hard-coded MCP Registry

### Current: `kiwi_mcp/mcp/registry.py`

```python
# Hard-coded - DELETE THIS
MCP_REGISTRY: dict[str, MCPConfig] = {
    "supabase": MCPConfig(...),
    "github": MCPConfig(...),
    "filesystem": MCPConfig(...),
}
```

### Target: Registry in Database

```sql
-- MCP server configs live in mcp_servers table
-- Tools that use them live in tools table with tool_type='mcp'

-- Query to get an MCP tool with its server config:
SELECT 
    t.tool_id,
    t.description,
    tv.manifest->'executor_config' AS config,
    ms.command,
    ms.args,
    ms.env
FROM tools t
JOIN tool_versions tv ON t.id = tv.tool_id AND tv.is_latest = true
LEFT JOIN mcp_servers ms ON tv.manifest->>'mcp_server' = ms.name
WHERE t.tool_id = 'supabase_execute_sql';
```

---

## Complete Tool Type Matrix

| tool_type | What's stored | What's executed | Dynamic? |
|-----------|--------------|-----------------|----------|
| `python` | Python code + manifest | PythonExecutor runs code in venv | ✅ LLM can create |
| `bash` | Bash script + manifest | BashExecutor runs with params | ✅ LLM can create |
| `api` | API config in manifest | APIExecutor makes HTTP request | ✅ LLM can create |
| `docker` | Docker config in manifest | DockerExecutor runs container | ✅ LLM can create |
| `mcp` | MCP routing in manifest | MCPExecutor proxies to MCP server | ✅ LLM can create |

**Key insight:** The executors are the **primitives**. They're the only hard-coded parts. Everything else is **data** in the registry.

---

## Executor Registration

The executors are registered at startup, but tools are loaded dynamically:

```python
# kiwi_mcp/handlers/tool/__init__.py

from .executors import ExecutorRegistry
from .executors.python import PythonExecutor
from .executors.bash import BashExecutor
from .executors.api import APIExecutor
from .executors.mcp import MCPExecutor


def register_executors(mcp_pool: MCPClientPool):
    """Register executor primitives at startup."""
    ExecutorRegistry.register("python", PythonExecutor())
    ExecutorRegistry.register("bash", BashExecutor())
    ExecutorRegistry.register("api", APIExecutor())
    ExecutorRegistry.register("mcp", MCPExecutor(mcp_pool))
    # Future: ExecutorRegistry.register("docker", DockerExecutor())
```

---

## Summary

| Concept | Static (Code) | Dynamic (Registry) |
|---------|--------------|-------------------|
| Executor types | ✅ PythonExecutor, BashExecutor, etc. | ❌ |
| Specific tools | ❌ | ✅ All tools stored as data |
| MCP server configs | ❌ (migrate away) | ✅ `mcp_servers` table |
| MCP tools | ❌ | ✅ `tools` with `tool_type='mcp'` |
| Tool discovery | ❌ | ✅ Hybrid search in registry |
| LLM tool creation | N/A | ✅ Via `execute(action='create')` |

**The executor primitives are the "assembly language". Tools are the "high-level programs" that LLMs write and share.**

---

## Next Steps

1. **Create MCPExecutor** - Route `tool_type: mcp` to MCP servers
2. **Create `mcp_servers` table** - Move configs from code to DB
3. **Implement auto-discovery** - Scan MCP servers for available tools
4. **Update ToolHandler.create** - Support creating all tool types
5. **Seed official tools** - Migrate hard-coded MCP configs to registry tools

---

## Example: Full Dynamic Tool Lifecycle

```python
# 1. LLM discovers a need for a Slack notification tool
# 2. LLM searches registry - not found
# 3. LLM creates the tool:

await execute(
    item_type="tool",
    action="create",
    item_id="slack_notify",
    parameters={
        "content": {
            "tool_id": "slack_notify",
            "tool_type": "api",
            "version": "1.0.0",
            "description": "Send a notification to Slack",
            "executor_config": {
                "method": "POST",
                "url_template": "https://hooks.slack.com/services/${SLACK_WEBHOOK}",
                "headers": {"Content-Type": "application/json"},
                "body_template": {"text": "{message}"}
            },
            "parameters": [
                {"name": "message", "type": "string", "required": True}
            ]
        }
    }
)

# 4. Tool is now in registry
# 5. Any agent can now use it:

await execute(
    item_type="tool",
    action="run",
    item_id="slack_notify",
    parameters={"message": "Deployment complete!"}
)
```

The system is now **self-extending** - agents can create the tools they need.
