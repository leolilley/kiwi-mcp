# MCP Discovery Flow

**Status:** Current Implementation + Future Pattern  
**Last Updated:** 2026-01-26

## Overview

This document explains how MCP (Model Context Protocol) discovery and integration works in Kiwi MCP. The system uses a **data-driven, tool-based approach** where MCP connectors are themselves tools that discover and generate other tools.

## Current State

### Base Tools

We have three foundational MCP tools:

1. **`mcp_discover.py`** - Python runtime tool that uses the official MCP SDK to discover tools from MCP servers
   - Supports both `stdio` and `sse` (HTTP) transports
   - Returns list of available tools with their schemas
   - Replaces the old `kiwi_mcp/mcp/` package functionality

2. **`mcp_stdio.yaml`** - Base tool for stdio MCP connections
   - Uses `subprocess` executor
   - Handles JSON-RPC over stdio
   - Parameters: `command`, `args`, `env`, `method`, `params`

3. **`mcp_http.yaml`** - Base tool for HTTP MCP connections
   - Uses `http_client` executor
   - Handles JSON-RPC over HTTP/SSE
   - Parameters: `url`, `auth`, `rpc_method`, `rpc_params`

### Architecture Principles

- **Kernel Stays Dumb**: No MCP-specific logic in core handlers
- **Data-Driven Tools**: Everything is a tool, including connectors
- **On-Demand Discovery**: Tools are discovered when connectors run, not automatically
- **Capability-Aware**: Generated tools declare required permissions

## Future Flow: Two-Layer Connector Pattern

### Step 1: Create a Connector Tool

Connector tools are **Python runtime tools** (following the same pattern as sink tools) that:

1. Connect to an MCP server
2. Discover available tools via `tools/list`
3. Generate individual tool YAML files
4. Sign the generated tools

**Example Connector Structure:**

```python
# .ai/tools/mcp/supabase_connector.py
__tool_type__ = "python"
__version__ = "1.0.0"
__executor_id__ = "python_runtime"
__category__ = "mcp"

"""
Supabase MCP Connector: Discovers and generates Supabase MCP tools.

This connector connects to the Supabase MCP server, discovers available tools,
and generates individual tool YAML files that can be used like any other tool.
"""

async def execute(
    mcp_url: str,
    auth: dict,
    output_dir: str = ".ai/tools/mcp/",
    tool_prefix: str = "supabase_",
    **params
) -> dict:
    """
    Discover Supabase MCP tools and generate tool files.
    
    Args:
        mcp_url: URL of the Supabase MCP server
        auth: Authentication configuration
        output_dir: Directory to write generated tool files
        tool_prefix: Prefix for generated tool IDs
        **params: Additional parameters
        
    Returns:
        Result dict with list of created tools
    """
    # 1. Use mcp_discover or MCP SDK to connect and discover tools
    # 2. For each discovered tool, generate a YAML file
    # 3. Sign generated tools
    # 4. Return list of created tools
```

### Step 2: Run the Connector

Connectors are executed like any other tool:

```bash
# Via MCP execute command
execute(
    item_type="tool",
    action="run",
    item_id="supabase_connector",
    parameters={
        "mcp_url": "https://mcp.supabase.com/mcp",
        "auth": {
            "type": "bearer",
            "token": "${SUPABASE_SERVICE_KEY}"
        },
        "output_dir": ".ai/tools/mcp/",
        "tool_prefix": "supabase_"
    }
)
```

### Step 3: Generated Tools

The connector generates individual tool files for each discovered MCP tool:

```yaml
# .ai/tools/mcp/supabase_query.yaml (GENERATED)
# kiwi-mcp:validated:2026-01-26T...:hash...
tool_id: supabase_query
tool_type: http
version: "1.0.0"
executor_id: http_client
category: mcp

# Chains to mcp_http base tool
config:
  method: POST
  url: "https://mcp.supabase.com/mcp"
  headers:
    Content-Type: application/json
    Authorization: "Bearer {auth_token}"
  body:
    jsonrpc: "2.0"
    id: "{request_id}"
    method: "tools/call"
    params:
      name: "query"  # The actual MCP tool name
      arguments: "{arguments}"

parameters:
  - name: arguments
    type: object
    required: true
    description: "Query arguments (sql, etc.)"

requires:
  - db.query
  - mcp.supabase
```

### Step 4: Use Discovered Tools

Once generated, tools are available like any other tool:

```bash
# Search for them
search(item_type="tool", query="supabase query")

# Execute them
execute(
    item_type="tool",
    action="run",
    item_id="supabase_query",
    parameters={
        "arguments": {
            "sql": "SELECT * FROM users LIMIT 10"
        }
    }
)
```

## Complete Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User/Agent Needs MCP Access                              │
│    "I need to query Supabase database"                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Search for Connector Tool                                │
│    search(item_type="tool", query="supabase connector")     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Load Connector from Registry                             │
│    load(item_type="tool", item_id="supabase_connector")     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Run Connector (Discovery Phase)                          │
│    execute(item_type="tool", action="run",                   │
│            item_id="supabase_connector", ...)                │
│                                                              │
│    Connector:                                                │
│    - Connects to MCP server                                 │
│    - Calls tools/list                                        │
│    - Generates tool YAML files                               │
│    - Signs generated tools                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Generated Tools Available                                │
│    .ai/tools/mcp/                                            │
│    ├── supabase_query.yaml                                  │
│    ├── supabase_migrate.yaml                                │
│    └── ...                                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Use Generated Tools                                      │
│    execute(item_type="tool", action="run",                   │
│            item_id="supabase_query", ...)                    │
└─────────────────────────────────────────────────────────────┘
```

## Benefits

### 1. Data-Driven Architecture
- Connectors are tools, not hardcoded infrastructure
- No MCP-specific logic in core kernel
- Follows the same pattern as all other tools

### 2. On-Demand Discovery
- Tools are discovered when connectors run
- No automatic background processes
- Full control over when MCPs are integrated

### 3. Capability-Aware
- Generated tools declare required permissions
- Integrates with capability token system
- Harness validates permissions before execution

### 4. Scalable
- Unlimited MCPs can be added
- Each MCP is just a connector tool
- No central configuration file needed

### 5. Versioned & Signed
- Generated tools can be signed and versioned
- Integrity verification works on generated tools
- Tools can be published to registry

## Implementation Status

### ✅ Completed
- `mcp_discover.py` - Tool discovery using MCP SDK
- `mcp_stdio.yaml` - Base stdio MCP tool
- `mcp_http.yaml` - Base HTTP MCP tool
- Removed old `kiwi_mcp/mcp/` package
- Cleaned directive handler (no MCP dependencies)

### 📋 Future (Phase 8.13)
- Create example connector tool (`supabase_connector.py`)
- Implement tool schema generation
- Add capability requirements to generated tools
- Auto-signing of generated tools
- Comprehensive tests

## Example: Adding a New MCP

To add a new MCP (e.g., GitHub):

1. **Create connector tool:**
   ```bash
   .ai/tools/mcp/github_connector.py
   ```

2. **Publish to registry:**
   ```bash
   execute(
       item_type="tool",
       action="publish",
       item_id="github_connector"
   )
   ```

3. **Users discover and use:**
   ```bash
   # Search
   search(item_type="tool", query="github connector")
   
   # Load
   load(item_type="tool", item_id="github_connector")
   
   # Run (discovers tools)
   execute(item_type="tool", action="run", item_id="github_connector")
   
   # Use generated tools
   execute(item_type="tool", action="run", item_id="github_create_issue")
   ```

## Related Documents

- `docs/THREAD_AND_STREAMING_ARCHITECTURE.md` - Full architecture specification
- `implementation/thread-streaming/phases/8.13-mcp-connector/README.md` - Implementation plan
- `docs/THREAD_AND_STREAMING_ARCHITECTURE.md` (lines 5625-5773) - Appendix A.6 (External MCP Integration)
