# Directive Runtime Architecture: Purpose-Built Agent Spawning

**Date:** 2026-01-21  
**Status:** Exploration  
**Author:** Kiwi Team

---

## The Evolution

### Current: Return Instructions to Caller

```
Agent: "Run directive deploy_feature"
     │
     ▼
Kiwi MCP: Parses directive, returns content
     │
     ▼
Same Agent: Reads instructions, figures out tools, executes
     │
     ▼
Problems:
  - Agent has ALL its tools, not just what directive needs
  - Agent context polluted with previous work
  - No isolation between directive executions
  - Caller agent does the work (context budget consumed)
```

### Proposed: Spawn Purpose-Built Executor

```
Agent: "Run directive deploy_feature"
     │
     ▼
Kiwi MCP: Parses directive, extracts <tools>
     │
     ▼
Kiwi MCP: Spawns dedicated executor with:
  - ONLY the tools declared in directive
  - ONLY the permissions granted
  - Fresh context (no pollution)
  - Single mission: execute this directive
     │
     ▼
Executor: Runs directive steps
     │
     ├─ Success: Returns result to caller
     │
     └─ Failure: Triggers annealing, retries, or escalates
```

---

## Why This is Powerful

### 1. Minimal Attack Surface

Agent only has the tools it needs. Can't accidentally (or maliciously) access anything else.

### 2. Fresh Context

Each directive execution starts clean. No context pollution from previous work.

### 3. Parallel Execution

Spawn multiple executors for independent directives. True parallelism.

### 4. Self-Annealing

Failed executions can trigger directive improvement automatically.

### 5. Audit & Replay

Complete record of what each executor did. Can replay with same inputs.

### 6. Cost Control

Use smaller/cheaper models for simple directives, bigger models for complex ones (based on `<model tier>`).

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Calling Agent                                │
│  "Run directive deploy_feature with inputs {...}"               │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      KIWI MCP SERVER                             │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    Directive Router                         │ │
│  │                                                             │ │
│  │  1. Parse directive                                         │ │
│  │  2. Extract <tools> declarations                            │ │
│  │  3. Build executor manifest                                 │ │
│  │  4. Spawn executor runtime                                  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                               │                                  │
│                               ▼                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   Executor Runtime                          │ │
│  │                                                             │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │              Tool Manifest                            │  │ │
│  │  │  - filesystem.read (paths: src/**)                   │  │ │
│  │  │  - supabase.apply_migration                          │  │ │
│  │  │  - shell.run (commands: git, npm)                    │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  │                                                             │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │              System Prompt                            │  │ │
│  │  │  "You are executing directive: deploy_feature         │  │ │
│  │  │   Follow these steps exactly..."                      │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  │                                                             │ │
│  │  ┌──────────────────────────────────────────────────────┐  │ │
│  │  │              LLM Loop                                 │  │ │
│  │  │  - Anthropic/OpenAI/Local API call                   │  │ │
│  │  │  - Tool calls routed through Kiwi proxy              │  │ │
│  │  │  - Iteration until complete or max steps             │  │ │
│  │  └──────────────────────────────────────────────────────┘  │ │
│  │                                                             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                               │                                  │
│                               ▼                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                   Result Handler                            │ │
│  │                                                             │ │
│  │  Success: Return structured result to caller                │ │
│  │  Failure: Trigger annealing → retry or escalate            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Minimal Implementation: No VMs

VMs are overkill. We need:

1. An LLM API connection
2. A tool manifest (what tools are available)
3. A system prompt (the directive)
4. A loop (call LLM, execute tools, repeat)

### The Executor Class

```python
# kiwi_mcp/runtime/executor.py

from dataclasses import dataclass
from typing import Any, Callable, Optional
import anthropic  # or openai, or local


@dataclass
class ToolDefinition:
    """Tool available to the executor."""
    name: str
    description: str
    input_schema: dict
    handler: Callable[[dict], Any]  # Function to call


@dataclass
class ExecutorConfig:
    """Configuration for a directive executor."""
    directive_name: str
    directive_content: str
    inputs: dict
    tools: list[ToolDefinition]
    model: str = "claude-sonnet-4-20250514"
    max_steps: int = 50
    timeout: int = 300  # seconds


class DirectiveExecutor:
    """
    Purpose-built agent for executing a single directive.

    Has ONLY the tools declared in the directive.
    Runs until completion or failure.
    """

    def __init__(self, config: ExecutorConfig, kiwi_proxy: "KiwiProxy"):
        self.config = config
        self.kiwi = kiwi_proxy
        self.client = anthropic.Anthropic()

        self.messages: list[dict] = []
        self.step_count = 0
        self.audit_log: list[dict] = []

    def _build_system_prompt(self) -> str:
        """Build focused system prompt for this directive."""
        return f"""You are a directive executor. Your ONLY job is to execute this directive:

# Directive: {self.config.directive_name}

{self.config.directive_content}

# Inputs Provided
{self._format_inputs()}

# Rules
1. Follow the directive steps EXACTLY
2. Use ONLY the tools provided - you have no others
3. Report completion or failure clearly
4. Do not deviate from the directive scope

# Available Tools
You have access to these tools and ONLY these tools:
{self._format_tool_list()}

Execute the directive now. Start with step 1."""

    def _format_inputs(self) -> str:
        """Format inputs as readable text."""
        lines = []
        for key, value in self.config.inputs.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines) if lines else "(no inputs)"

    def _format_tool_list(self) -> str:
        """Format tool list for system prompt."""
        lines = []
        for tool in self.config.tools:
            lines.append(f"- {tool.name}: {tool.description}")
        return "\n".join(lines)

    def _build_tools_schema(self) -> list[dict]:
        """Build Anthropic-compatible tool schemas."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in self.config.tools
        ]

    async def execute(self) -> dict:
        """
        Execute the directive.

        Returns:
            {
                "status": "success" | "failure" | "timeout",
                "result": Any,
                "steps_taken": int,
                "audit_log": list,
                "error": Optional[str],
            }
        """
        system_prompt = self._build_system_prompt()
        tools_schema = self._build_tools_schema()

        # Initial message - just trigger execution
        self.messages = [{"role": "user", "content": "Execute the directive."}]

        while self.step_count < self.config.max_steps:
            self.step_count += 1

            # Call LLM
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=4096,
                system=system_prompt,
                messages=self.messages,
                tools=tools_schema,
            )

            # Check for completion
            if response.stop_reason == "end_turn":
                # Extract final text response
                final_text = self._extract_text(response)

                # Check if it indicates success or failure
                if self._indicates_success(final_text):
                    return {
                        "status": "success",
                        "result": final_text,
                        "steps_taken": self.step_count,
                        "audit_log": self.audit_log,
                    }
                elif self._indicates_failure(final_text):
                    return {
                        "status": "failure",
                        "error": final_text,
                        "steps_taken": self.step_count,
                        "audit_log": self.audit_log,
                    }
                else:
                    # Ambiguous - treat as success with result
                    return {
                        "status": "success",
                        "result": final_text,
                        "steps_taken": self.step_count,
                        "audit_log": self.audit_log,
                    }

            # Handle tool calls
            if response.stop_reason == "tool_use":
                tool_results = await self._handle_tool_calls(response)

                # Add assistant message and tool results to conversation
                self.messages.append({"role": "assistant", "content": response.content})
                self.messages.append({"role": "user", "content": tool_results})

        # Max steps reached
        return {
            "status": "timeout",
            "error": f"Max steps ({self.config.max_steps}) reached",
            "steps_taken": self.step_count,
            "audit_log": self.audit_log,
        }

    async def _handle_tool_calls(self, response) -> list[dict]:
        """Execute tool calls and return results."""
        results = []

        for block in response.content:
            if block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input
                tool_id = block.id

                # Find tool handler
                tool = self._find_tool(tool_name)
                if not tool:
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": f"Error: Tool '{tool_name}' not available",
                        "is_error": True,
                    })
                    continue

                # Log the call
                self._log_tool_call(tool_name, tool_input)

                # Execute through Kiwi proxy
                try:
                    result = await self.kiwi.call_tool(tool_name, tool_input)
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": self._serialize_result(result),
                    })
                except Exception as e:
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": f"Error: {str(e)}",
                        "is_error": True,
                    })

        return results

    def _find_tool(self, name: str) -> Optional[ToolDefinition]:
        """Find tool by name."""
        for tool in self.config.tools:
            if tool.name == name:
                return tool
        return None

    def _log_tool_call(self, tool_name: str, inputs: dict):
        """Log tool call for audit trail."""
        self.audit_log.append({
            "step": self.step_count,
            "tool": tool_name,
            "inputs": inputs,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def _serialize_result(self, result: Any) -> str:
        """Serialize result for LLM consumption."""
        if isinstance(result, str):
            return result
        return json.dumps(result, indent=2, default=str)

    def _extract_text(self, response) -> str:
        """Extract text content from response."""
        for block in response.content:
            if hasattr(block, "text"):
                return block.text
        return ""

    def _indicates_success(self, text: str) -> bool:
        """Check if response indicates success."""
        success_markers = ["completed", "success", "done", "finished", "✓", "✅"]
        text_lower = text.lower()
        return any(marker in text_lower for marker in success_markers)

    def _indicates_failure(self, text: str) -> bool:
        """Check if response indicates failure."""
        failure_markers = ["failed", "error", "could not", "unable to", "✗", "❌"]
        text_lower = text.lower()
        return any(marker in text_lower for marker in failure_markers)
```

---

## The Kiwi Proxy

All tool calls go through Kiwi, even from spawned executors:

```python
# kiwi_mcp/runtime/proxy.py

class KiwiProxy:
    """
    Proxy for executor tool calls.

    Enforces permissions, logs operations, routes to actual tools.
    """

    def __init__(
        self,
        directive_context: dict,
        tool_manifest: list[ToolDefinition],
        mcp_pool: MCPClientPool,
        session_id: str,
    ):
        self.context = directive_context
        self.manifest = {t.name: t for t in tool_manifest}
        self.mcp_pool = mcp_pool
        self.session_id = session_id
        self.call_log: list[dict] = []

    async def call_tool(self, tool_name: str, params: dict) -> Any:
        """
        Call a tool with permission enforcement.
        """
        # 1. Check tool is in manifest
        if tool_name not in self.manifest:
            raise PermissionError(f"Tool '{tool_name}' not in executor manifest")

        # 2. Log the call
        self._log_call(tool_name, params)

        # 3. Route to appropriate handler
        if "." in tool_name:
            # MCP tool (e.g., supabase.apply_migration)
            return await self._call_mcp_tool(tool_name, params)
        elif tool_name.startswith("filesystem."):
            return await self._call_filesystem(tool_name, params)
        elif tool_name.startswith("shell."):
            return await self._call_shell(tool_name, params)
        else:
            # Local script/tool
            return await self._call_local_tool(tool_name, params)

    async def _call_mcp_tool(self, tool_name: str, params: dict) -> Any:
        """Call external MCP tool."""
        mcp_name, mcp_tool = tool_name.split(".", 1)
        return await self.mcp_pool.call_tool(mcp_name, mcp_tool, params)

    async def _call_filesystem(self, tool_name: str, params: dict) -> Any:
        """Call filesystem operation with path enforcement."""
        operation = tool_name.split(".")[1]  # read, write, list, etc.
        path = params.get("path", "")

        # Check path against allowed paths in manifest
        tool_def = self.manifest[tool_name]
        allowed_paths = tool_def.input_schema.get("allowed_paths", ["**/*"])

        if not self._path_allowed(path, allowed_paths):
            raise PermissionError(f"Path '{path}' not allowed for {tool_name}")

        # Execute
        executor = FilesystemExecutor(self.context.get("project_path"))
        return await executor.execute(operation, params, self.context)

    async def _call_shell(self, tool_name: str, params: dict) -> Any:
        """Call shell command with command enforcement."""
        command = params.get("command", "")

        # Check command against allowed commands
        tool_def = self.manifest[tool_name]
        allowed_commands = tool_def.input_schema.get("allowed_commands", [])

        base_command = command.split()[0] if command else ""
        if base_command not in allowed_commands:
            raise PermissionError(f"Command '{base_command}' not allowed")

        # Execute
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
        }

    async def _call_local_tool(self, tool_name: str, params: dict) -> Any:
        """Call local Kiwi script/tool."""
        # Route through ToolHandler
        from kiwi_mcp.handlers.tool.handler import ToolHandler
        handler = ToolHandler(self.context.get("project_path"))
        return await handler.execute("run", tool_name, params)

    def _log_call(self, tool_name: str, params: dict):
        """Log call for audit."""
        self.call_log.append({
            "session": self.session_id,
            "tool": tool_name,
            "params": params,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def _path_allowed(self, path: str, allowed_patterns: list[str]) -> bool:
        """Check if path matches allowed patterns."""
        from fnmatch import fnmatch
        return any(fnmatch(path, pattern) for pattern in allowed_patterns)
```

---

## Building the Executor from Directive

When a directive is "run", Kiwi builds the executor config:

```python
# kiwi_mcp/runtime/builder.py

class ExecutorBuilder:
    """Builds executor configuration from directive."""

    def __init__(self, mcp_pool: MCPClientPool):
        self.mcp_pool = mcp_pool

    async def build(
        self,
        directive_data: dict,
        inputs: dict,
        project_path: Path,
    ) -> ExecutorConfig:
        """
        Build executor config from parsed directive.
        """
        # Extract tool declarations
        tools_decl = directive_data.get("tools", {})

        # Build tool definitions
        tools = []

        # Filesystem tools
        if "filesystem" in tools_decl:
            fs_tools = self._build_filesystem_tools(tools_decl["filesystem"])
            tools.extend(fs_tools)

        # Shell tools
        if "shell" in tools_decl:
            shell_tools = self._build_shell_tools(tools_decl["shell"])
            tools.extend(shell_tools)

        # MCP tools
        for mcp_decl in tools_decl.get("mcp", []):
            mcp_tools = await self._build_mcp_tools(mcp_decl)
            tools.extend(mcp_tools)

        # Local scripts
        for script_decl in tools_decl.get("script", []):
            script_tool = await self._build_script_tool(script_decl, project_path)
            tools.append(script_tool)

        # Determine model from directive
        model = self._select_model(directive_data.get("model", {}))

        # Build directive content for system prompt
        directive_content = self._format_directive_for_prompt(directive_data)

        return ExecutorConfig(
            directive_name=directive_data["name"],
            directive_content=directive_content,
            inputs=inputs,
            tools=tools,
            model=model,
            max_steps=self._get_max_steps(directive_data),
        )

    def _build_filesystem_tools(self, fs_decl: dict) -> list[ToolDefinition]:
        """Build filesystem tool definitions."""
        tools = []

        # Read tool
        if "read" in fs_decl:
            read_paths = fs_decl["read"].get("paths", ["**/*"])
            tools.append(ToolDefinition(
                name="filesystem.read",
                description="Read file contents",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path to read"}
                    },
                    "required": ["path"],
                    "allowed_paths": read_paths,  # For enforcement
                },
                handler=None,  # Handled by proxy
            ))

        # Write tool
        if "write" in fs_decl:
            write_paths = fs_decl["write"].get("paths", [])
            tools.append(ToolDefinition(
                name="filesystem.write",
                description="Write content to file",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                    "allowed_paths": write_paths,
                },
                handler=None,
            ))

        # List tool
        tools.append(ToolDefinition(
            name="filesystem.list",
            description="List directory contents",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"],
                "allowed_paths": fs_decl.get("read", {}).get("paths", ["**/*"]),
            },
            handler=None,
        ))

        return tools

    def _build_shell_tools(self, shell_decl: dict) -> list[ToolDefinition]:
        """Build shell tool definition."""
        allowed_commands = []
        for cmd in shell_decl.get("command", []):
            if isinstance(cmd, dict):
                allowed_commands.append(cmd.get("name", cmd))
            else:
                allowed_commands.append(cmd)

        return [ToolDefinition(
            name="shell.run",
            description=f"Run shell command. Allowed: {', '.join(allowed_commands)}",
            input_schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command to run"}
                },
                "required": ["command"],
                "allowed_commands": allowed_commands,
            },
            handler=None,
        )]

    async def _build_mcp_tools(self, mcp_decl: dict) -> list[ToolDefinition]:
        """Build MCP tool definitions by fetching schemas."""
        mcp_name = mcp_decl["name"]
        tool_filter = mcp_decl.get("tool", [])  # List of tool names

        # Fetch schemas from MCP
        schemas = await self.mcp_pool.get_tool_schemas(mcp_name)

        tools = []
        for schema in schemas:
            # Filter if specified
            if tool_filter and schema.name not in tool_filter:
                continue

            tools.append(ToolDefinition(
                name=f"{mcp_name}.{schema.name}",
                description=schema.description,
                input_schema=schema.inputSchema,
                handler=None,  # Handled by proxy
            ))

        return tools

    async def _build_script_tool(
        self,
        script_decl: dict,
        project_path: Path
    ) -> ToolDefinition:
        """Build local script tool definition."""
        script_name = script_decl.get("name", script_decl)

        # Load script metadata
        from kiwi_mcp.utils.parsers import parse_script_metadata
        from kiwi_mcp.utils.resolvers import ScriptResolver

        resolver = ScriptResolver(project_path)
        script_path = resolver.resolve(script_name)

        if script_path:
            metadata = parse_script_metadata(script_path)
        else:
            metadata = {"name": script_name, "description": f"Script: {script_name}"}

        return ToolDefinition(
            name=script_name,
            description=metadata.get("description", f"Execute {script_name}"),
            input_schema={
                "type": "object",
                "properties": {
                    param["name"]: {"type": param.get("type", "string")}
                    for param in metadata.get("parameters", [])
                },
            },
            handler=None,
        )

    def _select_model(self, model_decl: dict) -> str:
        """Select LLM model based on directive tier."""
        tier = model_decl.get("tier", "balanced")

        MODEL_MAP = {
            "fast": "claude-3-5-haiku-20241022",
            "balanced": "claude-sonnet-4-20250514",
            "reasoning": "claude-sonnet-4-20250514",  # or o1 for complex
            "expert": "claude-sonnet-4-20250514",
        }

        return model_decl.get("id") or MODEL_MAP.get(tier, "claude-sonnet-4-20250514")

    def _get_max_steps(self, directive_data: dict) -> int:
        """Get max steps from directive metadata."""
        context_budget = directive_data.get("context_budget", {})
        step_count = context_budget.get("step_count", 50)
        return int(step_count) if step_count else 50

    def _format_directive_for_prompt(self, directive_data: dict) -> str:
        """Format directive content for system prompt."""
        lines = []

        lines.append(f"## Description")
        lines.append(directive_data.get("description", ""))
        lines.append("")

        lines.append(f"## Process Steps")
        for step in directive_data.get("process", []):
            lines.append(f"### Step: {step.get('name', 'unnamed')}")
            lines.append(step.get("description", ""))
            if step.get("action"):
                lines.append(f"**Action:** {step['action']}")
            lines.append("")

        if directive_data.get("success_criteria"):
            lines.append("## Success Criteria")
            for criterion in directive_data["success_criteria"]:
                lines.append(f"- {criterion}")

        return "\n".join(lines)
```

---

## The Run Flow

When `execute(item_type="directive", action="run", ...)` is called:

```python
# kiwi_mcp/handlers/directive/handler.py

async def _run_directive(
    self,
    directive_name: str,
    params: dict,
    spawn_executor: bool = True,  # NEW: control execution mode
) -> dict:
    """
    Run a directive.

    If spawn_executor=True (default for automation):
        Spawns a purpose-built executor with minimal tools.
        Returns when executor completes.

    If spawn_executor=False (legacy/interactive):
        Returns directive content for calling agent to execute.
    """
    # Load directive
    file_path = self.resolver.resolve(directive_name)
    directive_data = parse_directive_file(file_path)

    # Validate permissions
    permission_check = self._check_permissions(directive_data.get("permissions", []))
    if not permission_check["valid"]:
        return {"error": "Permission check failed", "details": permission_check["issues"]}

    # NEW: Spawn executor mode
    if spawn_executor:
        return await self._spawn_executor(directive_data, params)

    # Legacy: Return content for caller to execute
    return await self._return_for_caller(directive_data, params)

async def _spawn_executor(self, directive_data: dict, inputs: dict) -> dict:
    """Spawn a purpose-built executor for this directive."""

    # Build executor config
    builder = ExecutorBuilder(self.mcp_pool)
    config = await builder.build(
        directive_data=directive_data,
        inputs=inputs,
        project_path=self.project_path,
    )

    # Create proxy for tool calls
    session_id = str(uuid.uuid4())
    proxy = KiwiProxy(
        directive_context={
            "directive_name": directive_data["name"],
            "project_path": str(self.project_path),
            "permissions": directive_data.get("permissions", []),
        },
        tool_manifest=config.tools,
        mcp_pool=self.mcp_pool,
        session_id=session_id,
    )

    # Create and run executor
    executor = DirectiveExecutor(config, proxy)

    try:
        result = await executor.execute()

        # Handle result
        if result["status"] == "success":
            return {
                "status": "success",
                "directive": directive_data["name"],
                "result": result["result"],
                "steps_taken": result["steps_taken"],
                "session_id": session_id,
            }

        elif result["status"] == "failure":
            # Trigger annealing?
            if self._should_anneal(result):
                anneal_result = await self._anneal_and_retry(
                    directive_data, inputs, result
                )
                return anneal_result

            return {
                "status": "failure",
                "directive": directive_data["name"],
                "error": result["error"],
                "steps_taken": result["steps_taken"],
                "audit_log": result["audit_log"],
                "session_id": session_id,
            }

        else:  # timeout
            return {
                "status": "timeout",
                "directive": directive_data["name"],
                "error": result["error"],
                "steps_taken": result["steps_taken"],
                "session_id": session_id,
            }

    finally:
        # Persist audit log
        await self._save_audit_log(session_id, proxy.call_log, executor.audit_log)

def _should_anneal(self, result: dict) -> bool:
    """Check if we should attempt annealing."""
    # Don't anneal if too many steps taken (likely stuck)
    if result.get("steps_taken", 0) > 40:
        return False

    # Check for annealable errors
    error = result.get("error", "").lower()
    annealable = ["missing", "not found", "invalid", "unexpected"]
    return any(marker in error for marker in annealable)

async def _anneal_and_retry(
    self,
    directive_data: dict,
    inputs: dict,
    failure_result: dict
) -> dict:
    """Anneal the directive and retry execution."""
    # Run anneal_directive
    anneal_result = await self.execute(
        action="run",
        directive_name="anneal_directive",
        parameters={
            "directive_name": directive_data["name"],
            "failure_context": failure_result["error"],
            "audit_log": failure_result["audit_log"],
        }
    )

    if anneal_result.get("status") == "success":
        # Reload directive and retry (once)
        file_path = self.resolver.resolve(directive_data["name"])
        updated_directive = parse_directive_file(file_path)

        # Retry with updated directive
        return await self._spawn_executor(updated_directive, inputs)

    # Annealing failed, return original failure
    return {
        "status": "failure",
        "directive": directive_data["name"],
        "error": failure_result["error"],
        "anneal_attempted": True,
        "anneal_result": anneal_result,
    }
```

---

## Load Flow: Pre-Loading Environment

The `load` tool can pre-load directives and tools into an executor environment:

```python
# kiwi_mcp/runtime/environment.py

class ExecutorEnvironment:
    """
    Pre-configured environment for running multiple directives.

    Load directives, tools, knowledge upfront.
    Spawn executors from this environment.
    """

    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.loaded_directives: dict[str, dict] = {}
        self.loaded_tools: dict[str, ToolDefinition] = {}
        self.loaded_knowledge: dict[str, str] = {}
        self.mcp_pool = MCPClientPool()

    async def load_directive(self, directive_name: str, source: str = "project"):
        """Pre-load a directive into the environment."""
        from kiwi_mcp.handlers.directive.handler import DirectiveHandler

        handler = DirectiveHandler(str(self.project_path))
        result = await handler.load(directive_name, source=source)

        if "error" not in result:
            self.loaded_directives[directive_name] = result

            # Also pre-load any tools declared
            tools_decl = result.get("tools", {})
            await self._preload_tools(tools_decl)

        return result

    async def load_tools_from_mcp(self, mcp_name: str, tools: list[str] = None):
        """Pre-load tools from an MCP."""
        schemas = await self.mcp_pool.get_tool_schemas(mcp_name, tools)

        for schema in schemas:
            tool_id = f"{mcp_name}.{schema.name}"
            self.loaded_tools[tool_id] = ToolDefinition(
                name=tool_id,
                description=schema.description,
                input_schema=schema.inputSchema,
                handler=None,
            )

    async def load_knowledge(self, zettel_id: str, source: str = "project"):
        """Pre-load knowledge entry."""
        from kiwi_mcp.handlers.knowledge.handler import KnowledgeHandler

        handler = KnowledgeHandler(str(self.project_path))
        result = await handler.load(zettel_id, source=source)

        if "error" not in result:
            self.loaded_knowledge[zettel_id] = result.get("content", "")

        return result

    async def spawn_executor(
        self,
        directive_name: str,
        inputs: dict
    ) -> DirectiveExecutor:
        """
        Spawn an executor for a pre-loaded directive.

        Uses pre-loaded tools instead of fetching fresh.
        """
        if directive_name not in self.loaded_directives:
            raise ValueError(f"Directive '{directive_name}' not loaded")

        directive_data = self.loaded_directives[directive_name]

        # Build config using pre-loaded tools
        config = await self._build_config_from_loaded(directive_data, inputs)

        # Create proxy
        session_id = str(uuid.uuid4())
        proxy = KiwiProxy(
            directive_context={
                "directive_name": directive_name,
                "project_path": str(self.project_path),
            },
            tool_manifest=config.tools,
            mcp_pool=self.mcp_pool,
            session_id=session_id,
        )

        return DirectiveExecutor(config, proxy)

    async def _preload_tools(self, tools_decl: dict):
        """Pre-load tools from declaration."""
        for mcp_decl in tools_decl.get("mcp", []):
            mcp_name = mcp_decl["name"]
            tool_names = mcp_decl.get("tool", [])
            await self.load_tools_from_mcp(mcp_name, tool_names or None)
```

### Using Pre-Loaded Environment

```python
# Example: Set up environment, then run multiple directives

# 1. Create environment
env = ExecutorEnvironment(Path("/home/user/project"))

# 2. Pre-load everything needed
await env.load_directive("validate_schema", source="project")
await env.load_directive("apply_migrations", source="project")
await env.load_directive("deploy_functions", source="project")
await env.load_tools_from_mcp("supabase", ["apply_migration", "deploy_edge_function"])
await env.load_knowledge("supabase_best_practices")

# 3. Run directives in sequence (or parallel)
validator = await env.spawn_executor("validate_schema", {"schema_path": "..."})
result1 = await validator.execute()

if result1["status"] == "success":
    migrator = await env.spawn_executor("apply_migrations", {"project_id": "..."})
    result2 = await migrator.execute()

    if result2["status"] == "success":
        deployer = await env.spawn_executor("deploy_functions", {})
        result3 = await deployer.execute()
```

---

## Comparison: Current vs Proposed

| Aspect              | Current (Return to Caller)     | Proposed (Spawn Executor)       |
| ------------------- | ------------------------------ | ------------------------------- |
| **Tool Access**     | All caller's tools             | Only directive's declared tools |
| **Context**         | Polluted with caller's history | Fresh, focused                  |
| **Isolation**       | None                           | Complete                        |
| **Parallelism**     | Limited by caller              | True parallel spawning          |
| **Model Selection** | Caller's model                 | Per-directive model             |
| **Annealing**       | Manual                         | Automatic on failure            |
| **Audit**           | Scattered                      | Unified per-execution           |
| **Cost**            | Single expensive agent         | Right-sized agents              |

---

## Minimal MVP Implementation

What's the absolute minimum to prove this works?

### MVP Scope

1. **ExecutorConfig dataclass** - ✅ Done above
2. **DirectiveExecutor with Anthropic API** - ✅ Done above
3. **Simple KiwiProxy** - Just filesystem + shell
4. **ExecutorBuilder** - Parse directive, build tools
5. **Modified `_run_directive`** - Add `spawn_executor` flag

### MVP Files

```
kiwi_mcp/
├── runtime/           # NEW directory
│   ├── __init__.py
│   ├── executor.py    # DirectiveExecutor class
│   ├── proxy.py       # KiwiProxy class
│   └── builder.py     # ExecutorBuilder class
└── handlers/
    └── directive/
        └── handler.py  # Modified _run_directive
```

### MVP Effort: ~2-3 days

1. Day 1: Executor + Proxy classes
2. Day 2: Builder + integration with handler
3. Day 3: Testing + annealing integration

---

## Future Extensions

### 1. Executor Pool

Pre-spawn executors for hot directives. Reuse connections.

### 2. Streaming Results

Stream executor progress back to caller in real-time.

### 3. Checkpointing

Save executor state. Resume after crash.

### 4. Resource Limits

Memory/CPU limits per executor. Kill runaway agents.

### 5. Multi-Model Orchestration

Some steps use fast model, others use reasoning model.

---

## Open Questions & Recommendations

### 1. Async vs Sync execution? Should `run` wait for completion or return immediately with a session ID?

**Recommendation: Both modes, caller chooses.**

```python
# Sync mode (default for simple directives)
result = await execute(item_type="directive", action="run", item_id="validate_schema")
# Returns when complete

# Async mode (for long-running directives)
session = await execute(item_type="directive", action="run", item_id="deploy_all", 
                        parameters={"async": True})
# Returns immediately with session_id

# Check status later
status = await execute(item_type="directive", action="status", item_id=session["session_id"])

# Or stream progress
async for update in execute(item_type="directive", action="stream", item_id=session["session_id"]):
    print(update)
```

- Simple directives (<30s expected): Sync by default
- Long directives (>30s or unknown): Async with `async: True`
- Directive can declare preference: `<execution mode="async" />`

### 2. Executor lifecycle? How long do we keep executor state? When do we cleanup?

**Recommendation: Tiered retention with explicit cleanup.**

| State Type | Retention | Location |
|------------|-----------|----------|
| Active executor | Until completion | Memory |
| Session result | 24 hours | `.ai/sessions/{id}.json` |
| Audit log | 7 days | `.ai/logs/audit/{date}/` |
| Checkpoints | Until resumed or 24h | `.ai/checkpoints/` |

Cleanup triggers:
- On session completion: Archive to logs, remove from active
- Cron job: Clean sessions older than 24h
- Manual: `execute(action="cleanup", parameters={"older_than": "7d"})`

```python
class SessionManager:
    async def cleanup_old_sessions(self, max_age: timedelta = timedelta(days=1)):
        for session_file in self.sessions_dir.glob("*.json"):
            age = datetime.now() - datetime.fromtimestamp(session_file.stat().st_mtime)
            if age > max_age:
                # Archive to logs before deleting
                await self._archive_session(session_file)
                session_file.unlink()
```

### 3. Nested spawning? Can an executor spawn another executor?

**Recommendation: Yes, with scoped permissions.**

- Executor can spawn sub-executors via `run_directive` tool
- Sub-executor inherits parent's tools by default
- Parent can restrict: Only pass subset of tools
- Sub-executor CANNOT exceed parent's permissions
- Depth limit: 5 levels (configurable)
- All nested sessions linked in audit log

```python
# In executor, when encountering nested directive call
async def _handle_nested_run(self, directive_name: str, inputs: dict):
    # Create scoped proxy for child
    child_tools = self._get_declared_tools_for(directive_name)
    
    # Validate child tools are subset of parent
    for tool in child_tools:
        if tool not in self.tool_manifest:
            raise PermissionError(f"Cannot grant '{tool}' to child - parent lacks access")
    
    # Spawn child executor
    child = await self._spawn_child_executor(directive_name, inputs, child_tools)
    result = await child.execute()
    
    # Link audit logs
    self.audit_log.append({
        "type": "nested_spawn",
        "child_session": child.session_id,
        "child_directive": directive_name,
        "child_result": result["status"],
    })
    
    return result
```

### 4. Cost tracking? Track tokens/cost per execution for billing/budgeting?

**Recommendation: Built-in token tracking with budget limits.**

```python
@dataclass
class ExecutorConfig:
    ...
    max_tokens: int = 100_000  # Budget limit
    track_cost: bool = True

class DirectiveExecutor:
    def __init__(self, ...):
        self.token_usage = {"input": 0, "output": 0}
    
    async def execute(self):
        while self.step_count < self.config.max_steps:
            # Check budget before each step
            if self._exceeds_budget():
                return {"status": "budget_exceeded", "usage": self.token_usage}
            
            response = await self._call_llm()
            
            # Track usage
            self.token_usage["input"] += response.usage.input_tokens
            self.token_usage["output"] += response.usage.output_tokens
            ...
        
        return {
            "status": "success",
            "usage": self.token_usage,
            "estimated_cost": self._calculate_cost(),
        }
    
    def _calculate_cost(self) -> float:
        # Based on model pricing
        rates = {"claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015}}
        rate = rates.get(self.config.model, {"input": 0.01, "output": 0.03})
        return (self.token_usage["input"] * rate["input"] + 
                self.token_usage["output"] * rate["output"]) / 1000
```

### 5. Human approval integration? Pause executor, wait for human, resume?

**Recommendation: Checkpoint-based pause/resume.**

See [MCP_ORCHESTRATION_DESIGN.md](./MCP_ORCHESTRATION_DESIGN.md#5-human-approval-integration) for full implementation.

Summary:
1. Executor hits `require_approval` tool
2. Create checkpoint, persist state
3. Notify human via configured channel
4. Human approves: `kiwi approve {session_id}`
5. Resume from checkpoint
6. Timeout after configurable period (default 1 hour)

---

## Cross-Reference

This document is part of the Kiwi MCP evolution:

- [TOOLS_EVOLUTION_PROPOSAL.md](./TOOLS_EVOLUTION_PROPOSAL.md) - Scripts → Tools upgrade
- [MCP_ORCHESTRATION_DESIGN.md](./MCP_ORCHESTRATION_DESIGN.md) - MCP routing and proxy
- [KIWI_HARNESS_ROADMAP.md](./KIWI_HARNESS_ROADMAP.md) - Implementation roadmap
