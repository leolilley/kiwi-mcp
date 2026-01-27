# MCP Discovery Workflow

**Date:** 2026-01-27  
**Status:** Specification  
**Purpose:** Define the seamless flow for discovering, configuring, and using external MCP servers

---

## Executive Summary

MCP (Model Context Protocol) servers provide tools that can be discovered and wrapped as reusable Kiwi tools. This document specifies:

1. **Discovery Directive** - Agent-driven workflow to discover MCPs
2. **YAML Tool Format** - Data-driven MCP tool definitions
3. **Core System Tools** - The underlying mcp_discover and mcp_call primitives
4. **Environment Configuration** - How users configure API keys and auth

**Goal:** A user says "discover MCP at https://example.com/mcp" and gets fully configured, signed, reusable tools.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│ User Request                                                     │
│   "discover MCP at https://mcp.context7.com/mcp"                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ discover_mcp Directive                                          │
│                                                                 │
│   1. Validate MCP URL/path                                      │
│   2. Run mcp_discover tool to list available tools              │
│   3. For each discovered tool:                                  │
│      a. Generate YAML tool definition                           │
│      b. Sign the tool                                           │
│   4. Detect required environment variables                      │
│   5. Instruct user on configuration                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Generated Tool YAMLs                                            │
│                                                                 │
│   .ai/tools/mcp/                                                │
│   ├── context7_resolve_library.yaml                             │
│   ├── context7_query_docs.yaml                                  │
│   └── ...                                                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ User Configuration                                              │
│                                                                 │
│   .ai/.env:                                                     │
│     CONTEXT7_API_KEY=ctx7sk-xxxxx                               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Tool Execution                                                  │
│                                                                 │
│   execute(tool="context7_query_docs", params={...})             │
│   → mcp_http_runtime → mcp_call → Context7 MCP Server           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core System Tools

These are foundational tools that power MCP discovery and execution. They live in `.ai/tools/mcp/` and are part of the core Kiwi distribution.

### 1. mcp_discover

**Purpose:** Connect to an MCP server and list available tools.

**Location:** `.ai/tools/mcp/mcp_discover.py` (system tool)

**Parameters:**

```yaml
transport: "http" | "stdio"
url: string          # For HTTP transport
command: string      # For stdio transport
args: list[string]   # For stdio transport
headers: object      # HTTP headers (e.g., {"API_KEY": "..."})
```

**Returns:**

```json
{
  "success": true,
  "tools": [
    {
      "name": "resolve-library-id",
      "description": "Find a library ID from a name",
      "inputSchema": {
        "type": "object",
        "properties": {
          "libraryName": { "type": "string" },
          "query": { "type": "string" }
        },
        "required": ["libraryName"]
      }
    }
  ],
  "count": 2
}
```

### 2. mcp_call

**Purpose:** Execute a single tool call on an MCP server.

**Location:** `.ai/tools/mcp/mcp_call.py` (system tool)

**Parameters:**

```yaml
url: string # MCP server URL
tool: string # Tool name to call
params: object # Tool parameters
headers: object # HTTP headers for auth
timeout: number # Request timeout (default: 30)
```

**Returns:**

```json
{
  "success": true,
  "tool": "resolve-library-id",
  "content": [{ "type": "text", "text": "..." }]
}
```

---

## MCP Tool YAML Format

Discovered MCP tools are represented as YAML files that use the `mcp_http_runtime`.

### Schema

```yaml
# kiwi-mcp signature line (added by sign action)
# .ai/tools/mcp/{mcp_name}_{tool_name}.yaml

tool_id: context7_resolve_library
version: "1.0.0"
tool_type: mcp_tool
executor_id: mcp_http_runtime
category: mcp

metadata:
  mcp_server: context7
  mcp_url: https://mcp.context7.com/mcp
  original_tool_name: resolve-library-id
  discovered_at: "2026-01-27T12:00:00Z"

description: |
  Find a library ID from a name. Returns matching libraries with
  their Context7-compatible IDs.

# Environment variables required for this MCP
env_requirements:
  - name: CONTEXT7_API_KEY
    description: API key from https://context7.com/dashboard
    header: CONTEXT7_API_KEY # Header name to use
    required: true

# Input schema (from MCP discovery)
input_schema:
  type: object
  properties:
    libraryName:
      type: string
      description: Library name to search for
    query:
      type: string
      description: Optional query to refine results
  required:
    - libraryName

# MCP-specific configuration
config:
  url: https://mcp.context7.com/mcp
  tool: resolve-library-id
  timeout: 30
  headers:
    CONTEXT7_API_KEY: "${CONTEXT7_API_KEY}"
```

### Directory Structure

```
.ai/
├── tools/
│   └── mcp/
│       ├── # Core system tools (Python)
│       ├── mcp_discover.py
│       ├── mcp_call.py
│       │
│       ├── # Discovered MCP tools (YAML)
│       ├── context7_resolve_library.yaml
│       ├── context7_query_docs.yaml
│       ├── brave_search.yaml
│       └── github_create_issue.yaml
│
├── .env                    # User's API keys
│   # CONTEXT7_API_KEY=ctx7sk-xxxxx
│   # BRAVE_API_KEY=BSAxxxxx
│
└── directives/
    └── discover_mcp.md     # The discovery directive
```

---

## MCP HTTP Runtime

A new runtime that executes MCP tools via HTTP.

**Location:** `.ai/tools/runtimes/mcp_http_runtime.py`

```python
__version__ = "1.0.0"
__tool_type__ = "runtime"
__executor_id__ = "subprocess"
__category__ = "runtimes"

ENV_CONFIG = {
    "interpreter": {
        "type": "venv_python",
        "search": ["project", "kiwi", "user", "system"],
        "var": "KIWI_PYTHON",
        "fallback": "python3",
    },
}

CONFIG = {
    "command": "${KIWI_PYTHON}",
    "args": [".ai/tools/mcp/mcp_call.py"],
    "timeout": 60,
    "capture_output": True,
}
```

The runtime delegates to `mcp_call.py` which handles the actual MCP communication.

---

## discover_mcp Directive

### Directive Definition

````xml
<?xml version="1.0" encoding="UTF-8"?>
<directive name="discover_mcp" version="1.0.0">
  <metadata>
    <description>
      Discover tools from an MCP server and create reusable Kiwi tool definitions.
      Supports both HTTP (remote) and stdio (local) MCP servers.
    </description>
    <category>mcp</category>
    <author>kiwi-mcp</author>
    <tags>mcp, discovery, integration</tags>
  </metadata>

  <inputs>
    <input name="url" type="string" required="false">
      MCP server URL for HTTP transport (e.g., https://mcp.context7.com/mcp)
    </input>
    <input name="command" type="string" required="false">
      Command for stdio transport (e.g., "npx @modelcontextprotocol/server-github")
    </input>
    <input name="name" type="string" required="true">
      Short name for this MCP (used in tool IDs, e.g., "context7", "github", "brave")
    </input>
    <input name="auth_header" type="string" required="false">
      Name of the authentication header (e.g., "CONTEXT7_API_KEY", "Authorization")
    </input>
    <input name="auth_env_var" type="string" required="false">
      Environment variable containing the auth value (e.g., "CONTEXT7_API_KEY")
    </input>
  </inputs>

  <process>
    <step name="validate_input">
      <description>Validate that either url or command is provided</description>
      <action>
        Ensure exactly one of 'url' (for HTTP) or 'command' (for stdio) is provided.
        If neither or both are provided, ask the user to clarify.
      </action>
    </step>

    <step name="check_auth">
      <description>Check if authentication is configured</description>
      <action>
        If auth_header is specified:
        1. Check if auth_env_var exists in environment or .ai/.env
        2. If not found, inform user they need to add it before tools will work
        3. Continue with discovery (tools can be created before auth is configured)
      </action>
    </step>

    <step name="discover_tools">
      <description>Connect to MCP server and discover available tools</description>
      <tool_call>
        <mcp>kiwi-mcp</mcp>
        <tool>execute</tool>
        <params>
          <item_type>tool</item_type>
          <action>run</action>
          <item_id>mcp_discover</item_id>
          <parameters>
            <transport>http</transport>  <!-- or stdio based on input -->
            <url>{url}</url>
            <headers>
              <{auth_header}>${{{auth_env_var}}}</{auth_header}>
            </headers>
          </parameters>
        </params>
      </tool_call>
      <on_success>
        Store discovered tools list for next step.
        Log: "Discovered {count} tools from {name} MCP"
      </on_success>
      <on_failure>
        If connection failed:
        - Check if URL is correct
        - Check if auth is required but not provided
        - Suggest user verify the MCP server is running
      </on_failure>
    </step>

    <step name="generate_tool_yamls">
      <description>Generate YAML tool definition for each discovered tool</description>
      <action>
        For each discovered tool:

        1. Generate tool_id: {mcp_name}_{tool_name_snake_case}
           Example: "resolve-library-id" → "context7_resolve_library"

        2. Create YAML file at .ai/tools/mcp/{tool_id}.yaml with:
           - Full metadata from discovery
           - Input schema from MCP
           - Config pointing to mcp_call
           - Environment requirements

        3. Use the following template:

        ```yaml
        tool_id: {tool_id}
        version: "1.0.0"
        tool_type: mcp_tool
        executor_id: mcp_http_runtime
        category: mcp

        metadata:
          mcp_server: {mcp_name}
          mcp_url: {url}
          original_tool_name: {original_name}
          discovered_at: {timestamp}

        description: |
          {tool_description}

        env_requirements:
          - name: {auth_env_var}
            description: "API key for {mcp_name}"
            header: {auth_header}
            required: true

        input_schema:
          {input_schema_from_discovery}

        config:
          url: {url}
          tool: {original_tool_name}
          timeout: 30
          headers:
            {auth_header}: "${{{auth_env_var}}}"
        ```
      </action>
    </step>

    <step name="sign_tools">
      <description>Sign each generated tool</description>
      <action>
        For each generated YAML file:

        execute(
          item_type="tool",
          action="sign",
          item_id="{tool_id}",
          project_path="{project_path}",
          parameters={"category": "mcp"}
        )
      </action>
    </step>

    <step name="report_results">
      <description>Report results and configuration instructions</description>
      <action>
        Generate a summary for the user:

        ## MCP Discovery Complete: {mcp_name}

        ### Discovered Tools

        | Tool ID | Description |
        |---------|-------------|
        | {tool_id_1} | {description_1} |
        | {tool_id_2} | {description_2} |

        ### Configuration Required

        Add the following to `.ai/.env`:

        ```
        {auth_env_var}=your_api_key_here
        ```

        Get your API key from: {mcp_docs_url_if_known}

        ### Usage

        ```
        execute(item_type="tool", action="run", item_id="{tool_id_1}",
                project_path="/path/to/project",
                parameters={...})
        ```

        Or via directive:
        ```
        run tool {tool_id_1} with param1=value1
        ```
      </action>
    </step>
  </process>

  <outputs>
    <output name="tools_created" type="list">
      List of tool IDs that were created
    </output>
    <output name="env_requirements" type="list">
      List of environment variables the user needs to configure
    </output>
  </outputs>

  <examples>
    <example name="discover_context7">
      <input>
        url: https://mcp.context7.com/mcp
        name: context7
        auth_header: CONTEXT7_API_KEY
        auth_env_var: CONTEXT7_API_KEY
      </input>
      <output>
        Created tools:
        - context7_resolve_library
        - context7_query_docs

        Add to .ai/.env:
        CONTEXT7_API_KEY=your_key
      </output>
    </example>

    <example name="discover_brave_search">
      <input>
        url: https://mcp.brave.com/search
        name: brave
        auth_header: X-Subscription-Token
        auth_env_var: BRAVE_API_KEY
      </input>
      <output>
        Created tools:
        - brave_web_search
        - brave_local_search

        Add to .ai/.env:
        BRAVE_API_KEY=BSAxxxxx
      </output>
    </example>

    <example name="discover_local_mcp">
      <input>
        command: npx @modelcontextprotocol/server-filesystem /home/user/docs
        name: filesystem
      </input>
      <output>
        Created tools:
        - filesystem_read_file
        - filesystem_write_file
        - filesystem_list_directory

        No authentication required.
      </output>
    </example>
  </examples>
</directive>
````

---

## Environment Variable Configuration

### Where to Add API Keys

Users configure MCP authentication in `.ai/.env`:

```bash
# .ai/.env - Project-level MCP configuration

# Context7 - Documentation lookup
CONTEXT7_API_KEY=ctx7sk-xxxxxxxxxx

# Brave Search
BRAVE_API_KEY=BSAxxxxxxxxxx

# GitHub (for github MCP)
GITHUB_TOKEN=ghp_xxxxxxxxxx

# OpenAI (if using OpenAI MCP)
OPENAI_API_KEY=sk-xxxxxxxxxx
```

### Resolution Order

Environment variables are resolved in this order (later overrides earlier):

1. `~/.ai/.env` - User-level defaults
2. `.ai/.env` - Project-level configuration
3. `.env` - Root project env (standard)
4. `.env.local` - Local overrides (gitignored)

### Security Notes

- `.ai/.env` should be in `.gitignore`
- Never commit API keys to version control
- Use `~/.ai/.env` for keys used across multiple projects

---

## Complete Discovery Flow Example

### 1. User Initiates Discovery

```
User: "discover the Context7 MCP at https://mcp.context7.com/mcp"
```

### 2. Agent Runs Directive

```
Agent: I'll discover the Context7 MCP and create reusable tools.

Running discover_mcp directive with:
- url: https://mcp.context7.com/mcp
- name: context7
- auth_header: CONTEXT7_API_KEY
- auth_env_var: CONTEXT7_API_KEY
```

### 3. Discovery Execution

```
Agent: Connecting to MCP server...

Discovered 2 tools:
1. resolve-library-id - Find a library ID from a name
2. query-docs - Get documentation for a library

Creating tool definitions...
```

### 4. Tool Creation

Agent creates:

**`.ai/tools/mcp/context7_resolve_library.yaml`**

```yaml
# kiwi-mcp:validated:2026-01-27T12:00:00Z:abc123...
tool_id: context7_resolve_library
version: "1.0.0"
tool_type: mcp_tool
executor_id: mcp_http_runtime
category: mcp

metadata:
  mcp_server: context7
  mcp_url: https://mcp.context7.com/mcp
  original_tool_name: resolve-library-id
  discovered_at: "2026-01-27T12:00:00Z"

description: |
  Resolves a package/product name to a Context7-compatible library ID.
  Call this before query-docs to get the correct library ID.

env_requirements:
  - name: CONTEXT7_API_KEY
    description: API key from https://context7.com/dashboard
    header: CONTEXT7_API_KEY
    required: true

input_schema:
  type: object
  properties:
    libraryName:
      type: string
      description: Library name to search for
    query:
      type: string
      description: The user's original question for ranking
  required:
    - libraryName
    - query

config:
  url: https://mcp.context7.com/mcp
  tool: resolve-library-id
  timeout: 30
  headers:
    CONTEXT7_API_KEY: "${CONTEXT7_API_KEY}"
```

### 5. Signing

```
Agent: Signing tools...
✓ Signed context7_resolve_library
✓ Signed context7_query_docs
```

### 6. User Instructions

```
Agent:
## MCP Discovery Complete: context7

### Created Tools

| Tool ID | Description |
|---------|-------------|
| context7_resolve_library | Find a library ID from a name |
| context7_query_docs | Get documentation for a library |

### Configuration Required

Add the following to `.ai/.env`:

```

CONTEXT7_API_KEY=your_api_key_here

```

Get your API key at: https://context7.com/dashboard

### Usage

Once configured, use the tools like any other Kiwi tool:

```

execute(item_type="tool", action="run", item_id="context7_resolve_library",
project_path="/home/user/myproject",
parameters={"libraryName": "react", "query": "hooks"})

```

```

### 7. User Configures

User adds to `.ai/.env`:

```
CONTEXT7_API_KEY=ctx7sk-xxxxxxxxxxxxx
```

### 8. Tools Are Reusable

From now on, any agent can use:

```
run tool context7_query_docs with libraryId=/reactjs/react.dev query="useEffect cleanup"
```

---

## MCP YAML Tool Execution Flow

When an MCP YAML tool is executed:

```
┌─────────────────────────────────────────────────────────────────┐
│ execute(tool="context7_query_docs", params={...})               │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Chain Resolution                                                │
│                                                                 │
│   context7_query_docs.yaml (mcp_tool)                           │
│         ↓                                                       │
│   mcp_http_runtime.py (runtime)                                 │
│         ↓                                                       │
│   subprocess (primitive)                                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Config Merge                                                    │
│                                                                 │
│   From YAML:                                                    │
│     url: https://mcp.context7.com/mcp                           │
│     tool: query-docs                                            │
│     headers: {CONTEXT7_API_KEY: "${CONTEXT7_API_KEY}"}          │
│                                                                 │
│   From runtime:                                                 │
│     command: ${KIWI_PYTHON}                                     │
│     args: [".ai/tools/mcp/mcp_call.py"]                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Environment Resolution                                          │
│                                                                 │
│   EnvResolver loads .ai/.env                                    │
│   CONTEXT7_API_KEY=ctx7sk-xxxxx                                 │
│                                                                 │
│   Templates config:                                             │
│     headers: {CONTEXT7_API_KEY: "ctx7sk-xxxxx"}                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Subprocess Execution                                            │
│                                                                 │
│   python mcp_call.py \                                          │
│     --url https://mcp.context7.com/mcp \                        │
│     --tool query-docs \                                         │
│     --params '{"libraryId": "...", "query": "..."}' \           │
│     --headers '{"CONTEXT7_API_KEY": "ctx7sk-xxxxx"}'            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ MCP Call                                                        │
│                                                                 │
│   mcp_call.py uses MCP SDK to:                                  │
│   1. Connect to MCP server via Streamable HTTP                  │
│   2. Initialize session                                         │
│   3. Call tool with params                                      │
│   4. Return result                                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Checklist

### Core Tools (Already Exist)

- [x] `mcp_discover.py` - Discovers MCP tools
- [x] `mcp_call.py` - Calls MCP tools

### New Components Needed

- [x] `mcp_http_runtime.py` - Runtime for MCP YAML tools
- [x] YAML extractor support for `mcp_tool` type (via mcp_http.yaml)
- [x] `discover_mcp` directive (`.ai/directives/integration/discover_mcp.md`)
- [x] Template for generating MCP tool YAMLs (`mcp_tool_template.py`)

### Enhancements

- [ ] Auto-detect common MCP auth patterns (Context7, Brave, etc.)
- [ ] Validate generated YAML against schema
- [ ] Support for stdio transport in YAML tools
- [ ] MCP tool versioning (re-discover to update)

---

## Benefits

### For Users

1. **One command to integrate** - Just provide URL and name
2. **No code writing** - YAML is generated automatically
3. **Familiar configuration** - API keys in .env files
4. **Reusable across projects** - Copy YAML files to other projects

### For the System

1. **Data-driven** - MCP tools are just YAML, no Python needed
2. **Consistent** - All MCP tools follow the same pattern
3. **Discoverable** - Tools can be searched and listed
4. **Maintainable** - Update by re-running discovery

### For Agents

1. **Self-service** - Agents can discover and use new MCPs
2. **Type-safe** - Input schemas are captured from MCP
3. **Documented** - Descriptions preserved from discovery
4. **Integrated** - Works with existing tool execution flow

---

## References

- [MCP Specification](https://modelcontextprotocol.io/specification)
- [mcp_discover.py](/home/leo/projects/kiwi-mcp/.ai/tools/mcp/mcp_discover.py)
- [mcp_call.py](/home/leo/projects/kiwi-mcp/.ai/tools/mcp/mcp_call.py)
- [ENVIRONMENT_RESOLUTION_ARCHITECTURE.md](./new%20auth/ENVIROMENT_RESOLUTION_ARCHETECTURE.md)
