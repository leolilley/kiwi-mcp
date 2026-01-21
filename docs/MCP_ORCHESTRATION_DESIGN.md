# MCP Orchestration Design: Directives as MCP Routers

**Date:** 2026-01-21  
**Status:** Exploration  
**Author:** Kiwi Team

---

## The Core Insight

Directives already declare _intent_ (what they need to do). Why not also declare _capabilities_ (which MCPs they need)?

When Kiwi MCP runs a directive, it could:

1. Read the directive's MCP requirements
2. Fetch tool schemas from those MCPs
3. Include them in the response to the agent
4. Agent now has full context to execute the directive

**This turns directives into "MCP routing manifests."**

---

## Current Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Agent Context                            │
│  - Kiwi MCP tools (search, load, execute, help)                 │
│  - Other MCPs configured in claude_desktop_config.json          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Kiwi MCP                                 │
│  execute(directive, "run", "create_script")                     │
│         │                                                        │
│         ▼                                                        │
│  Returns: directive content + steps                              │
│  Agent must figure out which tools to use                        │
└─────────────────────────────────────────────────────────────────┘
```

**Problem:** If a directive needs `supabase` MCP but agent doesn't have it loaded, the directive fails or agent improvises poorly.

---

## Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Agent Context                            │
│  - Kiwi MCP tools (always available)                            │
│  - Dynamic: tools from MCPs declared in current directive       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Kiwi MCP                                 │
│  execute(directive, "run", "deploy_to_supabase")                │
│         │                                                        │
│         ▼                                                        │
│  1. Parse directive, find <mcps> declarations                   │
│  2. Connect to declared MCPs (supabase, filesystem)             │
│  3. Fetch their tool schemas                                    │
│  4. Return: directive + MCP tool schemas + steps                │
│         │                                                        │
│         ▼                                                        │
│  Agent now has supabase tools in context for this directive     │
└─────────────────────────────────────────────────────────────────┘
```

---

## New Metadata Tag: `<mcps>`

### Option A: Simple Declaration

```xml
<directive name="deploy_to_supabase" version="1.0.0">
  <metadata>
    <description>Deploy schema and functions to Supabase</description>
    <category>deployment</category>
    <model tier="reasoning" />
    <permissions>
      <execute resource="supabase" action="*" />
    </permissions>

    <!-- NEW: MCP declarations -->
    <mcps>
      <mcp name="supabase" required="true">
        Database operations and edge functions
      </mcp>
      <mcp name="filesystem" required="true">
        Read migration files
      </mcp>
    </mcps>
  </metadata>
  ...
</directive>
```

### Option B: With Tool Filtering

```xml
<mcps>
  <mcp name="supabase" required="true">
    <!-- Only include these tools, not all 30+ -->
    <tools>
      <tool>apply_migration</tool>
      <tool>execute_sql</tool>
      <tool>deploy_edge_function</tool>
    </tools>
  </mcp>
  <mcp name="filesystem">
    <tools>
      <tool>read_file</tool>
      <tool>list_directory</tool>
    </tools>
  </mcp>
</mcps>
```

### Option C: With Aliasing (Advanced)

```xml
<mcps>
  <mcp name="supabase" alias="db">
    <!-- Directive can reference as "db.apply_migration" -->
    <tools>
      <tool name="apply_migration" />
      <tool name="execute_sql" />
    </tools>
  </mcp>
</mcps>
```

---

## Implementation Design

### 1. MCP Registry in Kiwi

Kiwi needs to know how to connect to MCPs:

```python
# kiwi_mcp/config/mcp_registry.py

MCP_REGISTRY = {
    "supabase": {
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "@supabase/mcp-server"],
        "env": {
            "SUPABASE_ACCESS_TOKEN": "${SUPABASE_ACCESS_TOKEN}",
        },
    },
    "filesystem": {
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "@anthropic/mcp-filesystem"],
        "env": {},
    },
    "github": {
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "@anthropic/mcp-github"],
        "env": {
            "GITHUB_TOKEN": "${GITHUB_TOKEN}",
        },
    },
    # User can add more via config file
}
```

### 2. MCP Client Pool

```python
# kiwi_mcp/mcp/client_pool.py

class MCPClientPool:
    """Pool of MCP client connections."""

    def __init__(self):
        self.clients: Dict[str, MCPClient] = {}
        self.schemas: Dict[str, List[Tool]] = {}

    async def get_client(self, mcp_name: str) -> MCPClient:
        """Get or create MCP client connection."""
        if mcp_name not in self.clients:
            config = MCP_REGISTRY.get(mcp_name)
            if not config:
                raise ValueError(f"Unknown MCP: {mcp_name}")

            client = await self._connect(config)
            self.clients[mcp_name] = client

            # Cache tool schemas
            tools = await client.list_tools()
            self.schemas[mcp_name] = tools

        return self.clients[mcp_name]

    async def get_tool_schemas(
        self,
        mcp_name: str,
        tool_filter: Optional[List[str]] = None
    ) -> List[Tool]:
        """Get tool schemas for an MCP, optionally filtered."""
        await self.get_client(mcp_name)  # Ensure connected

        schemas = self.schemas[mcp_name]

        if tool_filter:
            schemas = [t for t in schemas if t.name in tool_filter]

        return schemas

    async def call_tool(
        self,
        mcp_name: str,
        tool_name: str,
        arguments: dict
    ) -> Any:
        """Call a tool on an MCP server."""
        client = await self.get_client(mcp_name)
        return await client.call_tool(tool_name, arguments)
```

### 3. Directive Handler Changes

```python
# kiwi_mcp/handlers/directive/handler.py

async def _run_directive(self, directive_name: str, params: dict):
    # Load directive
    file_path = self.resolver.resolve(directive_name)
    directive_data = parse_directive_file(file_path)

    # NEW: Extract MCP declarations
    mcps_required = directive_data.get("mcps", [])

    # NEW: Fetch tool schemas from declared MCPs
    mcp_tools = {}
    for mcp_decl in mcps_required:
        mcp_name = mcp_decl["name"]
        tool_filter = mcp_decl.get("tools")

        try:
            schemas = await self.mcp_pool.get_tool_schemas(mcp_name, tool_filter)
            mcp_tools[mcp_name] = {
                "available": True,
                "tools": [self._schema_to_dict(t) for t in schemas],
            }
        except Exception as e:
            if mcp_decl.get("required", False):
                return {
                    "error": f"Required MCP '{mcp_name}' not available: {e}",
                    "hint": f"Configure {mcp_name} MCP or remove from directive requirements",
                }
            mcp_tools[mcp_name] = {
                "available": False,
                "error": str(e),
            }

    # Return directive with MCP context
    return {
        "status": "ready",
        "directive": directive_data,
        "mcp_context": mcp_tools,  # NEW: Tool schemas for agent
        "instructions": "Execute directive steps using the provided MCP tools.",
    }
```

### 4. Response Format

When agent runs a directive with MCP declarations:

```json
{
  "status": "ready",
  "directive": {
    "name": "deploy_to_supabase",
    "version": "1.0.0",
    "steps": [...],
    "inputs": {...}
  },
  "mcp_context": {
    "supabase": {
      "available": true,
      "tools": [
        {
          "name": "apply_migration",
          "description": "Applies a migration to the database...",
          "inputSchema": {
            "type": "object",
            "properties": {
              "project_id": {"type": "string"},
              "name": {"type": "string"},
              "query": {"type": "string"}
            },
            "required": ["project_id", "name", "query"]
          }
        },
        {
          "name": "execute_sql",
          "description": "Executes raw SQL...",
          "inputSchema": {...}
        }
      ]
    },
    "filesystem": {
      "available": true,
      "tools": [...]
    }
  },
  "instructions": "Execute directive steps. Use mcp_context tools via Kiwi proxy or direct MCP calls."
}
```

---

## Two Execution Models

### Model A: Kiwi as Proxy (Recommended)

Agent calls Kiwi, Kiwi routes to the MCP:

```python
# Agent's perspective:
mcp__kiwi_mcp__execute(
    item_type="mcp_tool",  # NEW item type
    action="call",
    item_id="supabase.apply_migration",
    parameters={
        "project_id": "abc123",
        "name": "create_users",
        "query": "CREATE TABLE users..."
    },
    project_path="/path/to/project"
)

# Kiwi routes to supabase MCP internally
```

**Pros:**

- Single MCP connection for agent (just Kiwi)
- Kiwi can enforce permissions
- Kiwi can log/audit all MCP calls
- Works with any agent that has Kiwi

**Cons:**

- Extra hop (latency)
- Kiwi becomes bottleneck

### Model B: Direct MCP Access

Agent uses MCPs directly, Kiwi just provides context:

```python
# Agent runs directive via Kiwi
result = mcp__kiwi_mcp__execute(directive, "run", "deploy_to_supabase")

# Agent now has tool schemas in result.mcp_context
# Agent calls supabase MCP directly
mcp__supabase__apply_migration(...)
```

**Pros:**

- No extra hop
- Full MCP performance

**Cons:**

- Agent must have MCPs configured
- Kiwi can't enforce permissions
- No unified audit trail

### Model C: Hybrid (Best of Both)

Kiwi provides context + optional proxy:

```xml
<mcps>
  <mcp name="supabase" proxy="true">
    <!-- Route through Kiwi for audit/permissions -->
  </mcp>
  <mcp name="filesystem" proxy="false">
    <!-- Agent calls directly for performance -->
  </mcp>
</mcps>
```

---

## The `<tools>` Tag Alternative

Instead of `<mcps>`, we could have a more general `<tools>` tag that covers both:

```xml
<metadata>
  <tools>
    <!-- Kiwi MCP tools (current) -->
    <kiwi>
      <search types="script,knowledge" />
      <execute actions="run" />
    </kiwi>

    <!-- External MCP tools -->
    <mcp name="supabase">
      <tool>apply_migration</tool>
      <tool>execute_sql</tool>
    </mcp>

    <!-- Kiwi script/tool execution -->
    <script name="validate_schema" />

    <!-- Shell commands -->
    <shell commands="git,npm" />
  </tools>
</metadata>
```

This unifies:

- Kiwi's own tools
- External MCP tools
- Internal scripts/tools
- Shell access

---

## Front-Loading Tool Context

The key insight: **Directives know what they need before execution.**

### Current Flow (Reactive)

```
1. Agent runs directive
2. Agent reads steps
3. Agent encounters "use supabase"
4. Agent searches for supabase tools
5. Agent may or may not have them
```

### Proposed Flow (Proactive)

```
1. Agent runs directive
2. Kiwi reads <mcps> declarations
3. Kiwi fetches all required tool schemas
4. Kiwi returns directive + tool context
5. Agent has everything needed upfront
```

### Implementation in DirectiveHandler

```python
async def _run_directive(self, directive_name: str, params: dict):
    directive_data = parse_directive_file(...)

    # Build comprehensive tool context
    tool_context = {
        "kiwi": self._get_kiwi_tool_schemas(),
        "mcps": {},
        "scripts": [],
        "shell": [],
    }

    # Process <tools> or <mcps> declarations
    tools_decl = directive_data.get("tools", {})

    # MCP tools
    for mcp_decl in tools_decl.get("mcp", []):
        schemas = await self.mcp_pool.get_tool_schemas(mcp_decl["name"])
        tool_context["mcps"][mcp_decl["name"]] = schemas

    # Script tools
    for script_decl in tools_decl.get("script", []):
        script_meta = await self.script_handler.load(script_decl["name"])
        tool_context["scripts"].append({
            "name": script_decl["name"],
            "parameters": script_meta.get("parameters"),
            "description": script_meta.get("description"),
        })

    # Shell commands
    tool_context["shell"] = tools_decl.get("shell", {}).get("commands", [])

    return {
        "directive": directive_data,
        "tool_context": tool_context,  # Everything agent needs
        "ready": True,
    }
```

---

## Directive XML Examples

### Example 1: Database Migration Directive

```xml
<directive name="run_migrations" version="1.0.0">
  <metadata>
    <description>Run database migrations on Supabase</description>
    <category>deployment</category>
    <model tier="balanced" />
    <permissions>
      <read resource="filesystem" path="supabase/migrations/**" />
      <execute resource="supabase" action="apply_migration" />
    </permissions>

    <tools>
      <mcp name="supabase" required="true">
        <tool>apply_migration</tool>
        <tool>list_migrations</tool>
      </mcp>
      <mcp name="filesystem" required="true">
        <tool>read_file</tool>
        <tool>list_directory</tool>
      </mcp>
    </tools>
  </metadata>

  <process>
    <step name="list_pending">
      <description>Find pending migrations</description>
      <action>
        1. List files in supabase/migrations/ (filesystem.list_directory)
        2. Get applied migrations (supabase.list_migrations)
        3. Compute pending = local - applied
      </action>
      <tool_calls>
        <call mcp="filesystem" tool="list_directory">
          <param name="path">supabase/migrations</param>
        </call>
        <call mcp="supabase" tool="list_migrations">
          <param name="project_id">{project_id}</param>
        </call>
      </tool_calls>
    </step>

    <step name="apply_each">
      <description>Apply each pending migration</description>
      <action>
        For each pending migration:
        1. Read SQL file (filesystem.read_file)
        2. Apply migration (supabase.apply_migration)
      </action>
    </step>
  </process>
</directive>
```

### Example 2: GitHub PR Workflow

```xml
<directive name="create_pr" version="1.0.0">
  <metadata>
    <description>Create a pull request with proper review setup</description>
    <category>workflows</category>
    <model tier="balanced" />

    <tools>
      <mcp name="github" required="true">
        <tool>create_pull_request</tool>
        <tool>request_review</tool>
        <tool>add_labels</tool>
      </mcp>
      <shell commands="git" />
    </tools>
  </metadata>

  <inputs>
    <input name="branch" type="string" required="true" />
    <input name="title" type="string" required="true" />
    <input name="reviewers" type="array" required="false" />
  </inputs>

  <process>
    <step name="push_branch">
      <action>git push origin {branch}</action>
    </step>
    <step name="create_pr">
      <tool_calls>
        <call mcp="github" tool="create_pull_request">
          <param name="head">{branch}</param>
          <param name="base">main</param>
          <param name="title">{title}</param>
        </call>
      </tool_calls>
    </step>
  </process>
</directive>
```

---

## Permission Integration

The `<tools>` declaration works with existing `<permissions>`:

```xml
<permissions>
  <!-- High-level permission declaration -->
  <execute resource="supabase" action="apply_migration" />
  <execute resource="github" action="create_pull_request" />
</permissions>

<tools>
  <!-- Specific tool requirements (validated against permissions) -->
  <mcp name="supabase">
    <tool>apply_migration</tool>  <!-- ✓ Allowed by permission -->
    <tool>delete_project</tool>   <!-- ✗ NOT in permissions -->
  </mcp>
</tools>
```

Kiwi validates that `<tools>` requests don't exceed `<permissions>` grants.

---

## MCP Tool as Item Type

You could also treat "mcp" as a new item type alongside directive/script/knowledge:

```python
# TypeHandlerRegistry
self.handlers = {
    "directive": DirectiveHandler(...),
    "script": ScriptHandler(...),  # → ToolHandler
    "knowledge": KnowledgeHandler(...),
    "mcp": MCPHandler(...),  # NEW
}

# MCPHandler
class MCPHandler:
    async def search(self, query, **kwargs):
        """Search across all registered MCPs for tools."""
        results = []
        for mcp_name in self.mcp_pool.clients:
            tools = self.mcp_pool.schemas[mcp_name]
            for tool in tools:
                if query in tool.name or query in tool.description:
                    results.append({
                        "mcp": mcp_name,
                        "tool": tool.name,
                        "description": tool.description,
                    })
        return {"results": results}

    async def load(self, mcp_name, **kwargs):
        """Get tool schemas for an MCP."""
        schemas = await self.mcp_pool.get_tool_schemas(mcp_name)
        return {
            "mcp": mcp_name,
            "tools": [self._schema_to_dict(t) for t in schemas],
        }

    async def execute(self, action, mcp_name, parameters, **kwargs):
        """Call a tool on an MCP."""
        if action == "call":
            tool_name = parameters.pop("tool")
            result = await self.mcp_pool.call_tool(mcp_name, tool_name, parameters)
            return {"result": result}
```

Usage:

```python
# Search for database tools across all MCPs
mcp__kiwi_mcp__search(item_type="mcp", query="database migration")

# Load supabase tool schemas
mcp__kiwi_mcp__load(item_type="mcp", item_id="supabase")

# Call a tool
mcp__kiwi_mcp__execute(
    item_type="mcp",
    action="call",
    item_id="supabase",
    parameters={"tool": "apply_migration", "project_id": "...", ...}
)
```

---

## Configuration: mcp_registry.yaml

```yaml
# .ai/config/mcp_registry.yaml (project-level)
# ~/.ai/config/mcp_registry.yaml (user-level)

mcps:
  supabase:
    type: stdio
    command: npx
    args: ["-y", "@supabase/mcp-server"]
    env:
      SUPABASE_ACCESS_TOKEN: ${SUPABASE_ACCESS_TOKEN}
    description: Database operations, edge functions, storage

  filesystem:
    type: stdio
    command: npx
    args: ["-y", "@anthropic/mcp-filesystem"]
    allowed_paths:
      - ${PROJECT_PATH}
      - ~/.ai
    description: File system operations

  github:
    type: stdio
    command: npx
    args: ["-y", "@anthropic/mcp-github"]
    env:
      GITHUB_TOKEN: ${GITHUB_TOKEN}
    description: GitHub repository operations

  custom-api:
    type: sse
    url: https://api.mycompany.com/mcp
    headers:
      Authorization: Bearer ${API_TOKEN}
    description: Internal company API
```

---

## Summary: Design Decisions

| Decision        | Options                   | Recommendation                                   |
| --------------- | ------------------------- | ------------------------------------------------ |
| Tag name        | `<mcps>` vs `<tools>`     | `<tools>` (more general)                         |
| Tool filtering  | All vs explicit list      | Explicit list (security)                         |
| Execution model | Proxy vs Direct vs Hybrid | Hybrid (per-MCP choice)                          |
| New item type?  | Yes vs extend directive   | Both (mcp as item type + directive declarations) |
| Schema caching  | None vs in-memory vs file | In-memory + file cache                           |

---

## Next Steps

1. **Define `<tools>` XML schema** in directive authoring guide
2. **Create MCP registry config** format
3. **Implement MCPClientPool** for connection management
4. **Add MCPHandler** as new item type
5. **Modify DirectiveHandler** to parse and resolve `<tools>`
6. **Add tool context to run response**
7. **Create example directives** using external MCPs
8. **Write integration tests** with mock MCPs

---

## Design Decision: Proxy Mode Required

**For agent automation, proxy mode is mandatory.**

When humans use Kiwi MCP interactively, direct MCP access is fine. But as we scale to agents running autonomously—agents orchestrating other agents, self-modifying codebases, continuous automation—we need:

1. **Unified audit trail** - Every action logged through one system
2. **Permission enforcement** - Agents can't exceed their granted capabilities
3. **Rate limiting** - Prevent runaway agents from hammering APIs
4. **Rollback capability** - Undo agent actions when things go wrong
5. **Human-in-the-loop checkpoints** - Pause for approval on risky operations

**Kiwi MCP becomes the agent harness.**

---

## The Agent Harness Vision

### Current: Agents Talk Directly to Tools

```
┌─────────────────────────────────────────────────────────────────┐
│                           Agent                                  │
│                             │                                    │
│      ┌──────────────────────┼──────────────────────┐            │
│      │                      │                      │            │
│      ▼                      ▼                      ▼            │
│  ┌────────┐           ┌──────────┐          ┌──────────┐       │
│  │ Files  │           │ Supabase │          │  GitHub  │       │
│  │ (Read/ │           │   MCP    │          │   MCP    │       │
│  │ Write) │           └──────────┘          └──────────┘       │
│  └────────┘                                                     │
│                                                                  │
│  No central control. No audit. No enforcement.                  │
└─────────────────────────────────────────────────────────────────┘
```

### Proposed: Kiwi as Agent Harness

```
┌─────────────────────────────────────────────────────────────────┐
│                           Agent                                  │
│                             │                                    │
│                      (ONLY talks to Kiwi)                        │
│                             │                                    │
│                             ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    KIWI MCP (Harness)                     │   │
│  │                                                           │   │
│  │  ┌─────────────────────────────────────────────────────┐ │   │
│  │  │                 Permission Layer                     │ │   │
│  │  │  • Check directive permissions                       │ │   │
│  │  │  • Validate tool access                              │ │   │
│  │  │  • Rate limiting                                     │ │   │
│  │  └─────────────────────────────────────────────────────┘ │   │
│  │                           │                               │   │
│  │  ┌─────────────────────────────────────────────────────┐ │   │
│  │  │                  Audit Layer                         │ │   │
│  │  │  • Log all operations                                │ │   │
│  │  │  • Track agent sessions                              │ │   │
│  │  │  • Git checkpoint integration                        │ │   │
│  │  └─────────────────────────────────────────────────────┘ │   │
│  │                           │                               │   │
│  │  ┌─────────────────────────────────────────────────────┐ │   │
│  │  │                  Router Layer                        │ │   │
│  │  │  • Route to internal tools (scripts, knowledge)      │ │   │
│  │  │  • Route to external MCPs (supabase, github)         │ │   │
│  │  │  • Route to filesystem operations                    │ │   │
│  │  └─────────────────────────────────────────────────────┘ │   │
│  │                           │                               │   │
│  └───────────────────────────┼───────────────────────────────┘   │
│                              │                                    │
│      ┌───────────────────────┼───────────────────────┐           │
│      │                       │                       │           │
│      ▼                       ▼                       ▼           │
│  ┌────────┐           ┌──────────┐          ┌──────────┐        │
│  │ Files  │           │ Supabase │          │  GitHub  │        │
│  │ Proxy  │           │   MCP    │          │   MCP    │        │
│  └────────┘           └──────────┘          └──────────┘        │
│                                                                  │
│  Full control. Full audit. Full enforcement.                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## File Operations Through Proxy

### How Amp/Claude Handle Files Currently

When you use Amp (or similar), file operations happen via built-in tools:

```
Agent says: "Read file src/main.py"
     │
     ▼
Built-in Read tool executes
     │
     ▼
Returns file content to agent
```

These tools are hard-coded into the agent runtime. The agent doesn't go through MCP for basic file ops—they're native capabilities.

### The Problem for Agent Automation

When Agent A spawns Agent B (via subagent/Task):

- Agent B has same file access as Agent A
- No visibility into what Agent B reads/writes
- No permission scoping (Agent B can touch anything)
- No rollback if Agent B corrupts files

### Kiwi Proxy Solution: Filesystem as MCP

Route ALL file operations through Kiwi:

```python
# Instead of agent's native Read tool...
# Agent calls Kiwi for ALL file operations:

mcp__kiwi_mcp__execute(
    item_type="tool",
    action="call",
    item_id="filesystem.read",
    parameters={
        "path": "src/main.py"
    },
    project_path="/home/user/project"
)
```

### Kiwi Filesystem Proxy Implementation

```python
# kiwi_mcp/handlers/tool/executors/filesystem.py

class FilesystemExecutor(ToolExecutor):
    """Proxy for filesystem operations with permission enforcement."""

    TOOLS = {
        "read": "Read file contents",
        "write": "Write file contents",
        "list": "List directory contents",
        "create": "Create new file",
        "delete": "Delete file",
        "move": "Move/rename file",
    }

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.allowed_paths: List[Path] = []
        self.audit_log: List[dict] = []

    async def execute(
        self,
        tool_name: str,
        params: dict,
        directive_context: Optional[dict] = None
    ) -> ExecutionResult:
        path = Path(params.get("path", ""))

        # 1. Permission check
        if not self._check_permission(tool_name, path, directive_context):
            return ExecutionResult(
                success=False,
                error=f"Permission denied: {tool_name} on {path}",
                hint="Check directive <permissions> for filesystem access"
            )

        # 2. Audit log
        self._log_operation(tool_name, path, directive_context)

        # 3. Execute
        if tool_name == "read":
            return await self._read(path)
        elif tool_name == "write":
            return await self._write(path, params.get("content"))
        elif tool_name == "list":
            return await self._list(path)
        # ... etc

    def _check_permission(
        self,
        tool_name: str,
        path: Path,
        directive_context: Optional[dict]
    ) -> bool:
        """Check if operation is allowed by directive permissions."""
        if not directive_context:
            return True  # No directive = interactive mode, allow all

        permissions = directive_context.get("permissions", [])

        # Find matching permission
        for perm in permissions:
            if perm["tag"] == "read" and tool_name == "read":
                if self._path_matches(path, perm["attrs"].get("path", "**/*")):
                    return True
            elif perm["tag"] == "write" and tool_name in ["write", "create", "delete"]:
                if self._path_matches(path, perm["attrs"].get("path", "**/*")):
                    return True

        return False

    def _log_operation(self, tool_name: str, path: Path, context: dict):
        """Log operation for audit trail."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": tool_name,
            "path": str(path),
            "directive": context.get("directive_name") if context else None,
            "agent_session": context.get("session_id") if context else None,
        }
        self.audit_log.append(entry)

        # Also write to .ai/logs/filesystem.jsonl
        self._persist_log(entry)

    async def _write(self, path: Path, content: str) -> ExecutionResult:
        """Write with git integration."""
        # Store original for potential rollback
        original = None
        if path.exists():
            original = path.read_text()

        # Write file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

        return ExecutionResult(
            success=True,
            data={
                "path": str(path),
                "bytes_written": len(content),
                "had_original": original is not None,
            },
            rollback_info={
                "path": str(path),
                "original_content": original,
            }
        )
```

### Agent Configuration for Proxy Mode

When running agents in automation mode, configure them to use ONLY Kiwi:

```yaml
# .ai/config/agent_harness.yaml

mode: proxy # "proxy" | "direct" | "hybrid"

# In proxy mode, agent should ONLY have Kiwi MCP
# All other tools are accessed through Kiwi
allowed_mcps:
  - kiwi-mcp

# Kiwi routes to these internally
internal_tools:
  filesystem:
    enabled: true
    allowed_paths:
      - ${PROJECT_PATH}
      - ~/.ai
    read_only_paths:
      - /etc
      - /usr

  shell:
    enabled: true
    allowed_commands:
      - git
      - npm
      - pnpm
      - python
      - pytest
    blocked_commands:
      - rm -rf
      - sudo
      - curl # Use API tool instead

  mcps:
    supabase:
      enabled: true
      rate_limit: 100/minute
    github:
      enabled: true
      require_approval:
        - create_pull_request
        - merge_pull_request
```

### The Agent Only Sees Kiwi

From the agent's perspective:

```python
# Agent's tool list (proxy mode):
tools = [
    "mcp__kiwi_mcp__search",
    "mcp__kiwi_mcp__load",
    "mcp__kiwi_mcp__execute",
    "mcp__kiwi_mcp__help",
]

# That's it. Everything goes through Kiwi.
# No direct file access.
# No direct MCP access.
# Full control.
```

---

## Tool Item Type with MCP Filtering

Keep `item_type="tool"` but add query modifiers for MCP-specific searches.

### Search Query Syntax

```python
# Search all tools (scripts, MCP tools, etc.)
search(item_type="tool", query="database migration")

# Search only MCP tools
search(item_type="tool", query="mcp:* database migration")

# Search specific MCP
search(item_type="tool", query="mcp:supabase migration")

# Search only local scripts/tools
search(item_type="tool", query="local:* scraper")

# Search by tool type
search(item_type="tool", query="type:bash deploy")
search(item_type="tool", query="type:api stripe")
```

### Implementation

```python
# kiwi_mcp/handlers/tool/handler.py

class ToolHandler:
    async def search(self, query: str, source: str = "all", **kwargs):
        """Search for tools across all sources."""
        results = []

        # Parse query modifiers
        modifiers, clean_query = self._parse_query_modifiers(query)

        # Determine what to search
        search_local = modifiers.get("scope") in (None, "local", "all")
        search_mcps = modifiers.get("scope") in (None, "mcp", "all")
        mcp_filter = modifiers.get("mcp")  # Specific MCP name
        type_filter = modifiers.get("type")  # python, bash, api, etc.

        # Search local tools (scripts)
        if search_local:
            local_results = await self._search_local_tools(clean_query, type_filter)
            results.extend(local_results)

        # Search MCP tools
        if search_mcps:
            mcp_results = await self._search_mcp_tools(clean_query, mcp_filter)
            results.extend(mcp_results)

        # Search registry
        if source in ("registry", "all"):
            registry_results = await self._search_registry(clean_query)
            results.extend(registry_results)

        return {"results": results, "query": query}

    def _parse_query_modifiers(self, query: str) -> Tuple[dict, str]:
        """Parse query modifiers like mcp:supabase, type:bash."""
        modifiers = {}
        clean_parts = []

        for part in query.split():
            if part.startswith("mcp:"):
                mcp_name = part[4:]
                if mcp_name == "*":
                    modifiers["scope"] = "mcp"
                else:
                    modifiers["mcp"] = mcp_name
                    modifiers["scope"] = "mcp"
            elif part.startswith("local:"):
                modifiers["scope"] = "local"
            elif part.startswith("type:"):
                modifiers["type"] = part[5:]
            else:
                clean_parts.append(part)

        return modifiers, " ".join(clean_parts)

    async def _search_mcp_tools(
        self,
        query: str,
        mcp_filter: Optional[str] = None
    ) -> List[dict]:
        """Search across MCP tool schemas."""
        results = []

        # Get list of MCPs to search
        if mcp_filter:
            mcp_names = [mcp_filter]
        else:
            mcp_names = list(self.mcp_pool.clients.keys())

        for mcp_name in mcp_names:
            try:
                schemas = await self.mcp_pool.get_tool_schemas(mcp_name)

                for tool in schemas:
                    # Score relevance
                    searchable = f"{tool.name} {tool.description}"
                    score = self._score_relevance(query, searchable)

                    if score > 0.3:  # Threshold
                        results.append({
                            "name": f"{mcp_name}.{tool.name}",
                            "tool_type": "mcp",
                            "mcp": mcp_name,
                            "tool_name": tool.name,
                            "description": tool.description,
                            "parameters": tool.inputSchema,
                            "score": score,
                            "source": "mcp",
                        })
            except Exception as e:
                self.logger.warning(f"Failed to search MCP {mcp_name}: {e}")

        return results
```

### Load Tool (with MCP support)

```python
async def load(
    self,
    tool_id: str,  # "google_maps_scraper" or "supabase.apply_migration"
    source: Literal["project", "user", "registry", "mcp"],
    **kwargs
) -> Dict[str, Any]:
    """Load tool details."""

    # Check if this is an MCP tool (contains dot)
    if "." in tool_id and source == "mcp":
        mcp_name, tool_name = tool_id.split(".", 1)
        return await self._load_mcp_tool(mcp_name, tool_name)

    # Otherwise load local/registry tool
    return await self._load_local_tool(tool_id, source)

async def _load_mcp_tool(self, mcp_name: str, tool_name: str) -> dict:
    """Load tool schema from MCP."""
    schemas = await self.mcp_pool.get_tool_schemas(mcp_name)

    for tool in schemas:
        if tool.name == tool_name:
            return {
                "name": f"{mcp_name}.{tool_name}",
                "tool_type": "mcp",
                "mcp": mcp_name,
                "tool_name": tool_name,
                "description": tool.description,
                "parameters": tool.inputSchema,
                "source": "mcp",
                "call_example": {
                    "item_type": "tool",
                    "action": "call",
                    "item_id": f"{mcp_name}.{tool_name}",
                    "parameters": "{ ... see inputSchema ... }",
                },
            }

    return {"error": f"Tool '{tool_name}' not found in MCP '{mcp_name}'"}
```

### Execute Tool (unified call)

```python
async def execute(
    self,
    action: str,
    tool_id: str,
    parameters: Optional[dict] = None,
    **kwargs
) -> Dict[str, Any]:
    """Execute tool action."""

    if action == "call":
        return await self._call_tool(tool_id, parameters or {}, kwargs)
    elif action == "run":
        # Alias for call
        return await self._call_tool(tool_id, parameters or {}, kwargs)
    # ... other actions (create, update, delete, publish)

async def _call_tool(
    self,
    tool_id: str,
    parameters: dict,
    context: dict
) -> dict:
    """Route tool call to appropriate executor."""

    # Get current directive context (if running within a directive)
    directive_context = context.get("directive_context")

    # MCP tool (e.g., "supabase.apply_migration")
    if "." in tool_id:
        mcp_name, tool_name = tool_id.split(".", 1)

        # Permission check
        if directive_context:
            if not self._check_mcp_permission(mcp_name, tool_name, directive_context):
                return {
                    "error": f"Permission denied: {mcp_name}.{tool_name}",
                    "hint": "Add <mcp> permission to directive",
                }

        # Rate limit check
        if not self._check_rate_limit(mcp_name):
            return {
                "error": f"Rate limit exceeded for MCP '{mcp_name}'",
                "retry_after": self._get_retry_after(mcp_name),
            }

        # Audit log
        self._log_mcp_call(mcp_name, tool_name, parameters, directive_context)

        # Execute via MCP
        result = await self.mcp_pool.call_tool(mcp_name, tool_name, parameters)

        return {
            "status": "success",
            "tool": f"{mcp_name}.{tool_name}",
            "result": result,
        }

    # Local tool (script)
    else:
        return await self._run_local_tool(tool_id, parameters, directive_context)
```

---

## Unified Tool Interface

From the agent's perspective, all tools work the same way:

```python
# Call a Python script
mcp__kiwi_mcp__execute(
    item_type="tool",
    action="call",
    item_id="google_maps_scraper",
    parameters={"query": "coffee shops", "location": "NYC"}
)

# Call an MCP tool
mcp__kiwi_mcp__execute(
    item_type="tool",
    action="call",
    item_id="supabase.apply_migration",
    parameters={"project_id": "abc", "name": "create_users", "query": "..."}
)

# Call filesystem (through proxy)
mcp__kiwi_mcp__execute(
    item_type="tool",
    action="call",
    item_id="filesystem.read",
    parameters={"path": "src/main.py"}
)

# Call shell command (through proxy)
mcp__kiwi_mcp__execute(
    item_type="tool",
    action="call",
    item_id="shell.run",
    parameters={"command": "git status"}
)
```

**Same interface. Full control. Complete audit trail.**

---

## Tool ID Conventions

| Tool ID Format    | Type                | Example                               |
| ----------------- | ------------------- | ------------------------------------- |
| `{name}`          | Local Python script | `google_maps_scraper`                 |
| `{name}`          | Local Bash script   | `deploy_production`                   |
| `{mcp}.{tool}`    | External MCP tool   | `supabase.apply_migration`            |
| `filesystem.{op}` | Filesystem proxy    | `filesystem.read`, `filesystem.write` |
| `shell.run`       | Shell command proxy | `shell.run`                           |
| `git.{op}`        | Git operations      | `git.commit`, `git.push`              |

---

## Directive Example with Full Tool Declaration

```xml
<directive name="deploy_feature" version="1.0.0">
  <metadata>
    <description>Deploy a feature branch to staging</description>
    <category>deployment</category>
    <model tier="balanced" />

    <permissions>
      <read resource="filesystem" path="**/*" />
      <write resource="filesystem" path=".ai/outputs/**" />
      <execute resource="shell" commands="git,npm,pnpm" />
      <execute resource="mcp" name="supabase" tools="apply_migration,deploy_edge_function" />
      <execute resource="mcp" name="github" tools="create_pull_request" />
    </permissions>

    <tools>
      <!-- Filesystem operations (proxied) -->
      <filesystem>
        <read paths="src/**,supabase/**" />
        <write paths=".ai/outputs/**" />
      </filesystem>

      <!-- Shell commands (proxied) -->
      <shell>
        <command>git</command>
        <command>npm</command>
        <command>pnpm</command>
      </shell>

      <!-- External MCPs -->
      <mcp name="supabase" required="true">
        <tool>apply_migration</tool>
        <tool>deploy_edge_function</tool>
        <tool>get_project</tool>
      </mcp>

      <mcp name="github" required="false">
        <tool>create_pull_request</tool>
      </mcp>

      <!-- Local Kiwi tools/scripts -->
      <script name="validate_schema" />
      <script name="run_e2e_tests" />
    </tools>
  </metadata>

  <process>
    <step name="validate">
      <action>
        Run validate_schema tool to check migrations
      </action>
      <tool_call tool="validate_schema" />
    </step>

    <step name="apply_migrations">
      <action>
        Apply all pending migrations to staging
      </action>
      <tool_call tool="supabase.apply_migration">
        <param name="project_id">{staging_project_id}</param>
      </tool_call>
    </step>

    <step name="deploy_functions">
      <action>
        Deploy edge functions
      </action>
      <tool_call tool="supabase.deploy_edge_function" />
    </step>

    <step name="run_tests">
      <action>
        Run e2e tests against staging
      </action>
      <tool_call tool="run_e2e_tests" />
    </step>

    <step name="create_pr" condition="tests_pass">
      <action>
        Create PR for review
      </action>
      <tool_call tool="github.create_pull_request" />
    </step>
  </process>
</directive>
```

---

## Run Response with Full Tool Context

When agent runs this directive, Kiwi returns:

```json
{
  "status": "ready",
  "directive": {
    "name": "deploy_feature",
    "version": "1.0.0",
    "inputs": [...],
    "process": [...]
  },
  "tool_context": {
    "filesystem": {
      "available": true,
      "tools": [
        {"name": "filesystem.read", "description": "Read file contents", ...},
        {"name": "filesystem.write", "description": "Write file contents", ...},
        {"name": "filesystem.list", "description": "List directory", ...}
      ],
      "constraints": {
        "read_paths": ["src/**", "supabase/**"],
        "write_paths": [".ai/outputs/**"]
      }
    },
    "shell": {
      "available": true,
      "tools": [
        {"name": "shell.run", "description": "Run shell command", ...}
      ],
      "constraints": {
        "allowed_commands": ["git", "npm", "pnpm"]
      }
    },
    "supabase": {
      "available": true,
      "tools": [
        {
          "name": "supabase.apply_migration",
          "description": "Applies a migration to the database...",
          "inputSchema": {...}
        },
        {
          "name": "supabase.deploy_edge_function",
          "description": "Deploys an Edge Function...",
          "inputSchema": {...}
        }
      ]
    },
    "github": {
      "available": true,
      "tools": [
        {
          "name": "github.create_pull_request",
          "description": "Creates a pull request...",
          "inputSchema": {...}
        }
      ]
    },
    "scripts": {
      "available": true,
      "tools": [
        {
          "name": "validate_schema",
          "description": "Validate database schema...",
          "parameters": [...]
        },
        {
          "name": "run_e2e_tests",
          "description": "Run end-to-end tests...",
          "parameters": [...]
        }
      ]
    }
  },
  "call_format": {
    "description": "All tools called via Kiwi execute",
    "example": "mcp__kiwi_mcp__execute(item_type='tool', action='call', item_id='{tool_name}', parameters={...})"
  }
}
```

**Agent now has complete context to execute the directive.**

---

## Open Questions & Recommendations

### 1. Lazy vs Eager connection? Connect to MCPs on first use or when directive loads?

**Recommendation: Lazy connection with eager schema fetch.**

- When directive loads, fetch tool schemas but don't hold connections
- When tool is first called, establish connection
- Keep connection alive for duration of directive execution
- Close connections after execution completes (with configurable keep-alive)

```python
class MCPClientPool:
    async def get_tool_schemas(self, mcp_name: str):
        # Fetch schemas (may cache) - doesn't require persistent connection
        ...
    
    async def call_tool(self, mcp_name: str, tool_name: str, params: dict):
        # Establish connection on first call, reuse for subsequent
        if mcp_name not in self._active_connections:
            self._active_connections[mcp_name] = await self._connect(mcp_name)
        ...
```

### 2. Schema versioning? MCP tool schemas can change. Cache invalidation strategy?

**Recommendation: TTL-based cache with directive-level override.**

- Default: Cache schemas for 1 hour
- Directive can force refresh: `<mcp name="supabase" refresh="true">`
- Store schema version/hash, warn if changed during execution
- On publish: Always fetch fresh schemas

```python
SCHEMA_CACHE_TTL = 3600  # 1 hour

class SchemaCache:
    def get(self, mcp_name: str, force_refresh: bool = False):
        cached = self._cache.get(mcp_name)
        if cached and not force_refresh:
            if time.time() - cached["fetched_at"] < SCHEMA_CACHE_TTL:
                return cached["schemas"]
        return None  # Trigger fresh fetch
```

### 3. Error handling? What if MCP connection fails mid-directive?

**Recommendation: Graceful degradation with retry.**

1. First failure: Retry with exponential backoff (3 attempts)
2. Persistent failure: Check if tool is `required`
   - If required: Fail directive, trigger annealing
   - If optional: Skip tool, continue with warning
3. Log all failures for debugging
4. Return partial results with clear error context

```python
async def call_tool_with_retry(self, mcp_name: str, tool_name: str, params: dict):
    for attempt in range(3):
        try:
            return await self.call_tool(mcp_name, tool_name, params)
        except ConnectionError:
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
                continue
            raise MCPConnectionFailed(mcp_name, tool_name)
```

### 4. Subagent tool inheritance? When directive spawns subagent, does it inherit tool access or get fresh permissions?

**Recommendation: Scoped inheritance with explicit grants.**

- Subagent inherits parent's tool access by default
- Parent can restrict: `Task(tools=["filesystem.read", "supabase.*"])`
- Subagent CANNOT exceed parent's permissions (enforced by proxy)
- Audit log links subagent calls to parent session

```python
async def spawn_subagent(self, directive_name: str, tools: list[str] = None):
    # If tools specified, validate against parent's manifest
    if tools:
        for tool in tools:
            if not self._parent_has_tool(tool):
                raise PermissionError(f"Cannot grant tool '{tool}' - parent lacks access")
    else:
        # Inherit all parent tools
        tools = list(self.tool_manifest.keys())
    
    # Spawn with scoped tools
    return await self._spawn_executor(directive_name, tools)
```

### 5. Human approval integration? How do `require_approval` tools pause execution and wait for human?

**Recommendation: Checkpoint-based approval with configurable timeout.**

```yaml
# In agent_harness.yaml
mcps:
  github:
    require_approval:
      - create_pull_request
      - merge_pull_request
    approval_timeout: 3600  # 1 hour, then fail
```

Implementation:
1. Before calling `require_approval` tool, create checkpoint
2. Pause executor, persist state to `.ai/checkpoints/{session_id}.json`
3. Notify human (webhook, email, Slack - configurable)
4. Human approves via CLI or web interface: `kiwi approve {session_id}`
5. Resume executor from checkpoint
6. Timeout: Fail with "approval_timeout" status

```python
async def _call_tool(self, tool_id: str, params: dict):
    if self._requires_approval(tool_id):
        checkpoint_id = await self._create_checkpoint(tool_id, params)
        await self._notify_for_approval(checkpoint_id)
        
        # Wait for approval (with timeout)
        approved = await self._wait_for_approval(checkpoint_id, timeout=3600)
        
        if not approved:
            raise ApprovalTimeout(tool_id, checkpoint_id)
    
    return await self.proxy.call_tool(tool_id, params)
```

---

## Cross-Reference

This document is part of the Kiwi MCP evolution:

- [TOOLS_EVOLUTION_PROPOSAL.md](./TOOLS_EVOLUTION_PROPOSAL.md) - Scripts → Tools upgrade
- [DIRECTIVE_RUNTIME_ARCHITECTURE.md](./DIRECTIVE_RUNTIME_ARCHITECTURE.md) - Executor spawning
- [KIWI_HARNESS_ROADMAP.md](./KIWI_HARNESS_ROADMAP.md) - Implementation roadmap
