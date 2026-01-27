# MCP Discovery Tool Fix - Handoff Prompt

## Context: How We Build Tools in Kiwi MCP

Kiwi MCP follows a **data-driven architecture** where everything is a tool, not hardcoded infrastructure:

### Tool Patterns

1. **Python Runtime Tools** (like `mcp_discover.py`):
   - Self-contained Python files in `.ai/tools/{category}/`
   - Metadata declared at top: `__tool_type__ = "python"`, `__executor_id__ = "python_runtime"`, `__category__ = "mcp"`
   - No YAML sidecars - all logic in the Python file
   - Must have an `async def execute(...)` function as entry point
   - Must have a `if __name__ == "__main__":` block for CLI/subprocess execution
   - Executed via `python_runtime` executor → `subprocess` primitive
   - Examples: `.ai/tools/sinks/file_sink.py`, `.ai/tools/threads/thread_registry.py`

2. **HTTP Tools** (like `mcp_http.yaml`):
   - Pure YAML configuration files
   - Chain to `http_client` primitive
   - Examples: `.ai/tools/mcp/mcp_http.yaml`, `.ai/tools/llm/anthropic_messages.yaml`

### Architecture Principles

- **Kernel Stays Dumb**: Core MCP kernel has NO tool-specific logic - it only loads and returns data
- **Data-Driven Tools**: Everything is a tool with config (except primitives)
- **On-Demand Discovery**: Tools are discovered when connectors run, not automatically
- **Capability-Aware**: Generated tools declare required permissions

### Current Implementation

We've created `mcp_discover.py` as a Python runtime tool that:
- Uses the official MCP SDK (`mcp` package) to connect to MCP servers
- Supports both `stdio` and `sse` (HTTP/SSE) transports
- Discovers available tools via `tools/list` RPC call
- Returns tool schemas for connector tools to generate child tools

## The Problem

The `mcp_discover.py` tool is timing out when trying to connect to Context7 MCP server via SSE transport:

**Server Details:**
- URL: `https://mcp.context7.com/mcp`
- Auth: API key via header `Context7-API-Key` or `CONTEXT7_API_KEY`
- Key: `ctx7sk-576ef284-381b-436d-b4e6-be26c1bd0438`

**What Happens:**
```bash
python .ai/tools/mcp/mcp_discover.py \
  --transport sse \
  --url "https://mcp.context7.com/mcp" \
  --auth '{"type": "api_key", "header": "Context7-API-Key", "key": "ctx7sk-..."}'
```

**Result:** Connection timeout after 10 seconds

**Error:**
```json
{
  "success": false,
  "error": "Connection timeout after 10 seconds",
  "transport": "sse",
  "url": "https://mcp.context7.com/mcp",
  "headers": ["Context7-API-Key", "X-Context7-API-Key"],
  "diagnosis": "Server may not support SSE transport, URL may be incorrect, or authentication may have failed. Try stdio transport if available."
}
```

## What We've Tried

1. ✅ Added 10-second timeout (fails fast)
2. ✅ Tested basic HTTP connectivity - `/mcp` returns 406, `/sse` returns 404
3. ✅ Tried different header names: `CONTEXT7_API_KEY`, `Context7-API-Key`, `X-Context7-API-Key`
4. ✅ Configured MCP SDK SSE client with explicit timeouts: `timeout=5.0, sse_read_timeout=10.0`
5. ✅ Added better error handling and diagnostics

**HTTP Test Results:**
- `GET https://mcp.context7.com/mcp` → 406 (Not Acceptable)
- `GET https://mcp.context7.com/sse` → 404 (Not Found)
- Headers show allowed: `X-Context7-API-Key`, `Context7-API-Key`, `X-API-Key`, `Authorization`

## The Code

**File:** `.ai/tools/mcp/mcp_discover.py`

**Key Section (SSE transport):**
```python
elif transport == "sse":
    if not url:
        return {"success": False, "error": "url is required for sse transport"}
    
    # Create SSE client
    headers = {}
    if auth:
        if auth.get("type") == "bearer":
            headers["Authorization"] = f"Bearer {auth.get('token')}"
        elif auth.get("type") == "api_key":
            header_name = auth.get("header", "X-API-Key")
            headers[header_name] = auth.get("key")
            if not header_name.startswith("X-") and f"X-{header_name}" not in headers:
                headers[f"X-{header_name}"] = auth.get("key")
    
    try:
        async with asyncio.timeout(10):
            async with sse_client(url, headers=headers, timeout=5.0, sse_read_timeout=10.0) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools_result = await session.list_tools()
                    # ... process tools
    except asyncio.TimeoutError:
        return {"success": False, "error": "Connection timeout..."}
```

## What Needs to Be Fixed

The SSE connection is timing out. Possible issues:

1. **Wrong endpoint URL** - Maybe it should be `/sse` or a different path?
2. **Wrong connection method** - Maybe the MCP SDK SSE client doesn't work with this server?
3. **Authentication format** - Maybe headers need to be in query params or different format?
4. **Server doesn't support SSE** - Maybe this server only supports stdio or a different transport?

## Expected Behavior

The tool should:
1. Connect to the MCP server via SSE
2. Initialize the session
3. Call `tools/list` to discover available tools
4. Return the list of tools with their schemas
5. Close the connection

**Success response should look like:**
```json
{
  "success": true,
  "transport": "sse",
  "tools": [
    {
      "name": "tool_name",
      "description": "Tool description",
      "inputSchema": {...}
    }
  ],
  "count": 1
}
```

## Investigation Steps

1. Check MCP SDK documentation for SSE client usage
2. Test if the server supports SSE at all (maybe it's stdio-only?)
3. Check if the endpoint URL format is correct
4. Verify authentication header format matches server expectations
5. Consider if we need to use a different MCP SDK method or HTTP client directly

## Related Files

- `.ai/tools/mcp/mcp_discover.py` - The tool that needs fixing
- `.ai/tools/mcp/mcp_stdio.yaml` - Stdio transport base tool (works)
- `.ai/tools/mcp/mcp_http.yaml` - HTTP transport base tool
- `docs/MCP_DISCOVERY_FLOW.md` - Documentation of the discovery flow
- `implementation/thread-streaming/phases/8.8-cleanup/README.md` - Context about cleanup phase

## Constraints

- Must remain a Python runtime tool (no YAML sidecar)
- Must work via both direct CLI and MCP execute command
- Must handle both stdio and SSE transports
- Must maintain the data-driven architecture (no hardcoded logic in kernel)
- Must provide clear error messages for debugging

## Success Criteria

- [ ] Tool successfully connects to Context7 MCP server via SSE
- [ ] Tool discovers and returns available tools
- [ ] Tool handles errors gracefully with clear messages
- [ ] Tool works via both CLI and MCP execute command
- [ ] No breaking changes to existing functionality
