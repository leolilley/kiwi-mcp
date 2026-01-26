# Thread and Streaming Architecture Design

**Date:** 2026-01-25  
**Status:** Draft  
**Author:** Kiwi Team  
**Phase:** 8 (Deep Implementation Plan)

---

## Executive Summary

This document defines how Kiwi MCP implements **Threads** (LLM agent conversations) as **data-driven tools built on HTTP primitives**, NOT as hardcoded chat logic embedded in the MCP core.

**Core Principle:** The MCP stays dumb. Threads are just tools. Agent loops live in the harness.

**Key Architectural Clarifications:**

1. **Thread ID Handling (Three Layers)** - Base `spawn_thread` requires thread_id, `safety_harness` auto-generates, `thread_directive` tool wraps it all
2. **Harness Lives IN Thread** - spawn_thread tool instantiates the harness; harness then calls MCP tools to execute
3. **Sink Instantiation** - Tool executor instantiates sinks at chain resolution time; http_client stays pure primitive
4. **Cost Budget Termination** - ANY limit exceeded = terminate (OR logic across max_turns, tokens, USD, context)
5. **Thread Registry** - Regular MCP tool requiring system capabilities (registry.write/read), only accessible to core directives with these permissions
6. **MCP Connectors** - Manual/directive execution (not automatic); tools decide when to run
7. **Spawn Returns Immediately** - Async spawn; thread runs in background, caller gets thread_id for monitoring
8. **Context vs Cost** - Separate concerns: context = current input tokens per call (model limit, e.g., 200k), cost = cumulative usage across thread lifetime (budget limit, e.g., $10 total). Both tracked independently, either can trigger termination.
9. **Spawning Guidance** - AGENTS.md and run_directive directive provide spawning patterns; kernel just returns data

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    WHAT WE'RE NOT DOING (Anti-Pattern)                   │
│                                                                          │
│   async def _run_directive(self, directive_name: str, inputs: dict):    │
│       system_prompt = self._build_system_prompt(directive_data)  # ❌    │
│       tool_schemas = self._build_tool_schemas(directive_data)    # ❌    │
│       # Hardcoding LLM conversation in MCP = BAD                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                    WHAT WE ARE DOING (Correct Pattern)                   │
│                                                                          │
│   thread.run  →  llm.anthropic.messages  →  http_client                 │
│                                                                          │
│   Just HTTP calls. Agent loop lives in harness.                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## The Kiwi Philosophy: Everything → Something

### Traditional Agent Building (Nothing → Something)

Standard agent building today works like this:

> "Imagine your LLM can't do anything. You empower it by giving it tools, instructions, and identity (system prompt) to do something."

This is **additive empowerment**. Start with nothing, add capabilities.

### Kiwi Agent Building (Everything → Something)

Kiwi inverts this:

> "Imagine your LLM can do everything. You then **restrict** it to only what you want through explicit directives and permissions."

This is **subtractive restriction**. Start with everything, constrain to specific capability.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      PHILOSOPHICAL COMPARISON                            │
│                                                                          │
│  Traditional (nothing → something):                                      │
│    LLM + tools[] + system_prompt = Agent with those capabilities         │
│                                                                          │
│  Kiwi (everything → something):                                          │
│    LLM + Kiwi MCP + directive = Agent restricted to directive scope      │
│                                                                          │
│  Why Kiwi is superior:                                                   │
│  • Explicit permission boundaries (not implicit tool lists)              │
│  • Hard enforcement (not prompt-based suggestions)                       │
│  • Composable (directives can require/extend other directives)           │
│  • Auditable (every action logged against permission context)            │
│  • Annealable (failures feed back into directive improvement)            │
└─────────────────────────────────────────────────────────────────────────┘
```

### Why This Matters

In traditional systems, you must enumerate every capability. Miss one? Agent can't do it.

In Kiwi, the LLM has access to **the entire Kiwi ecosystem** (all tools, MCPs, knowledge). The directive **constrains** what subset it can actually use. This means:

1. **No schema bloat** - LLM uses `search()` to find what it needs
2. **Dynamic capability** - New tools available instantly if permissions allow
3. **Security by default** - Unpermitted actions are denied, not missing
4. **Clear audit trail** - Every action tied to permission context

---

## Key Terms & Concepts

Before diving in, let's define the core components:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              GLOSSARY                                        │
│                                                                              │
│  MCP Kernel                                                                  │
│  • The core Kiwi MCP server (kiwi_mcp/*.py)                                  │
│  • Handles search, load, execute calls                                       │
│  • Has NO thread logic - just loads and returns data                         │
│  • Think: "dumb data router"                                                 │
│                                                                              │
│  Harness (safety_harness package)                                              │
│  • Python library that implements the agent loop                             │
│  • Instantiated by spawn_thread tool                                         │
│  • Lives IN a thread context (not outside it)                                │
│  • Calls MCP kernel to execute tools                                         │
│  • Think: "agent loop runner"                                                │
│                                                                              │
│  Primitive                                                                   │
│  • Base execution tools (http_client, subprocess)                            │
│  • Contain actual execution code                                             │
│  • Terminal nodes in tool chains                                             │
│  • Think: "does the actual work"                                             │
│                                                                              │
│  Tool Layer                                                                  │
│  • Data-driven tools (YAML configs)                                          │
│  • Chain to primitives or other tools                                        │
│  • Include: LLM endpoints, threads, MCPs, sinks                              │
│  • Think: "composable configuration"                                         │
│                                                                              │
│  Thread                                                                      │
│  • An execution context for running a directive                              │
│  • Has its own harness instance                                              │
│  • Isolated permissions, cost tracking, transcript                           │
│  • Think: "managed conversation session"                                     │
│                                                                              │
│  Directive                                                                   │
│  • Workflow instructions (HOW to accomplish tasks)                           │
│  • Declares permissions, cost budget, process steps                          │
│  • Executed by spawning a thread (managed) or following directly (simple)    │
│  • Think: "recipe for the LLM"                                               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Architectural Principles

1. **Kernel Stays Dumb**:
   - MCP kernel has NO thread logic - it only loads and returns data
   - Thread spawning is a tool call, not kernel behavior
   - Kernel forwards capability tokens opaquely, never interprets them
   - All decision-making happens in harness or tools, not kernel
   - Example: `execute(directive, run, X)` always returns directive data
2. **Data-Driven Tools**: Everything is a tool with YAML config (except primitives)
3. **Harness IN Thread**: The harness is instantiated BY spawn_thread, lives in the thread
4. **Guidance in AGENTS.md**: Spawning patterns documented in system prompt, not kernel
5. **Permissions via Tokens**: Capability tokens minted by harness, validated by tools (see [PERMISSION_MODEL.md](./PERMISSION_MODEL.md) for complete details)

---

## The Problem

### Why Not Embed Agent Logic in MCP?

The roadmap doc (Phase 7) showed this anti-pattern:

```python
# WRONG - This embeds LLM orchestration in MCP core
async def _run_directive(self, directive_name: str, inputs: dict) -> dict:
    directive_data = await self.load(directive_name)
    system_prompt = self._build_system_prompt(directive_data)
    tool_schemas = self._build_tool_schemas(directive_data)
    permission_context = self._build_permission_context(directive_data)

    # Now MCP "knows" about chat conversations...
```

Problems:

1. **MCP becomes an LLM client** - violates "only primitives contain execution code"
2. **Not composable** - can't stack agents, can't pipe between them
3. **Hard to test** - agentic loops have complex state
4. **Provider-specific** - each LLM has different APIs/formats
5. **Security surface** - more code in trusted MCP core

### What We Want Instead

The Amp agent pattern from [How to Build an Agent](https://ampcode.com/how-to-build-an-agent):

```
Agent = LLM + Loop + Tools
```

Our insight: **Each of these should be a separate, composable piece**:

1. **LLM** = HTTP tool calling an API endpoint
2. **Loop** = Harness runner (NOT in MCP core)
3. **Tools** = Kiwi MCP (4 meta-tools: search, load, execute, help)

This means:

- Threads are just HTTP calls (tool chains ending at `http_client`)
- Agent loops live in the harness
- Streaming output goes to configurable destinations
- One thread can spawn another via thread tools

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         KIWI THREAD ARCHITECTURE                             │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                     Harness (Agent Loop Runner)                         │ │
│  │                                                                          │ │
│  │  Generic harness:                                                        │ │
│  │  • Runs the agentic loop (call LLM → interpret → execute → repeat)      │ │
│  │  • Philosophy-agnostic (can be nothing→something or everything→something)│ │
│  │                                                                          │ │
│  │  safety_harness (our implementation):                                      │ │
│  │  • Uses Kiwi's everything→something philosophy                          │ │
│  │  • System prompt = AGENTS.md (universal)                                │ │
│  │  • Permissions = from directive being executed                          │ │
│  │  • Tools = 4 Kiwi meta-tools (search, load, execute, help)              │ │
│  └───────────────────────────────────────┬────────────────────────────────┘ │
│                                          │                                   │
│                                          ▼                                   │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         Kiwi MCP (Data-Driven Core)                     │ │
│  │                                                                          │ │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────┐ │ │
│  │  │  Thread Tools   │    │  LLM Endpoint   │    │   Other MCP Tools   │ │ │
│  │  │  (config only)  │    │  Tools (config) │    │   (read, edit, etc) │ │ │
│  │  └────────┬────────┘    └────────┬────────┘    └─────────────────────┘ │ │
│  │           │                      │                                       │ │
│  │           └───────────┬──────────┘                                       │ │
│  │                       ▼                                                  │ │
│  │  ┌────────────────────────────────────────────────────────────────────┐ │ │
│  │  │                      http_client Primitive                          │ │ │
│  │  │                                                                      │ │ │
│  │  │  Modes:                                                              │ │ │
│  │  │  • sync: Standard request → response (current behavior)             │ │ │
│  │  │  • stream: SSE/WebSocket with destination fan-out                   │ │ │
│  │  │                                                                      │ │ │
│  │  │  Streaming Destinations (data-driven sinks):                         │ │ │
│  │  │  • file_sink: Append JSONL to path (tool)                           │ │ │
│  │  │  • null_sink: Discard for fire-and-forget (tool)                    │ │ │
│  │  │  • websocket_sink: Forward to socket (tool)                         │ │ │
│  │  │  • return: Buffer and include in result (built-in)                  │ │ │
│  │  └────────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                          │ │
│  └──────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Layer 1: Extended http_client Primitive

### Current State

`http_client.py` does synchronous HTTP with retry:

```python
async def execute(self, config: Dict, params: Dict) -> HttpResult:
    response = await client.request(method, url, headers, content, timeout)
    return HttpResult(success, status_code, body, headers, duration_ms)
```

### Extended State: Add Streaming Support

```python
@dataclass
class StreamConfig:
    """Configuration for streaming HTTP."""
    transport: str  # "sse" | "websocket"
    destinations: List[StreamDestination]
    buffer_events: bool = False  # Include in result.body?
    max_buffer_size: int = 10_000  # Prevent OOM

@dataclass
class StreamDestination:
    """Where streaming events go.

    NOTE (A.7): Only 'return' is a built-in http_client sink (buffers in memory).
    All other sinks (file_sink, null_sink, websocket_sink) are data-driven tools.
    See Appendix A.7 for sink architecture and tool configurations.
    """
    type: str  # "return" (built-in), or tool-based: "file_sink", "null_sink", "websocket_sink"
    path: Optional[str] = None  # For file_sink
    config: Optional[Dict[str, Any]] = None  # For tool-based sinks
    format: str = "jsonl"  # "jsonl" | "raw"

@dataclass
class HttpResult:
    """Extended with streaming support."""
    success: bool
    status_code: int
    body: Any  # Can be buffered events if stream mode
    headers: Dict[str, str]
    duration_ms: int
    error: Optional[str] = None

    # New streaming fields
    stream_events_count: Optional[int] = None
    stream_destinations: Optional[List[str]] = None
```

### Execution Modes

```python
async def execute(self, config: Dict, params: Dict) -> HttpResult:
    mode = params.get("mode", "sync")

    if mode == "sync":
        return await self._execute_sync(config, params)
    elif mode == "stream":
        return await self._execute_stream(config, params)
```

### SSE Streaming Implementation

The http_client receives pre-instantiated sink objects from the tool executor and fans out events:

```python
async def _execute_stream(self, config: Dict, params: Dict) -> HttpResult:
    """Execute streaming HTTP request with destination fan-out.

    Sinks are pre-instantiated by the tool executor BEFORE http_client execution
    (during chain resolution). They are passed to http_client via __sinks parameter.
    See tool chain resolution section above for sink instantiation logic.
    """

    # Extract pre-instantiated sinks from params (provided by tool executor)
    sinks = params.pop("__sinks", [])

    # Determine if we should buffer for return
    should_buffer = any(isinstance(s, ReturnSink) for s in sinks)
    buffered_events = [] if should_buffer else None

    async with self._client.stream(method, url, **kwargs) as response:
        event_count = 0

        async for line in response.aiter_lines():
            if line.startswith("data:"):
                event_data = line[5:].strip()
                event_count += 1

                # Fan-out to all pre-instantiated sinks
                for sink in sinks:
                    await sink.write(event_data)

                # Buffer if return sink is present
                if buffered_events is not None:
                    if len(buffered_events) < config.get("max_buffer_size", 10000):
                        buffered_events.append(event_data)

    # Close all sinks
    for sink in sinks:
        await sink.close()

    return HttpResult(
        success=True,
        status_code=response.status_code,
        body=buffered_events if buffered_events else None,
        headers=dict(response.headers),
        duration_ms=duration_ms,
        stream_events_count=event_count,
        stream_destinations=[type(s).__name__ for s in sinks],
    )
```

**Key points:**

- http_client is a pure primitive - it receives sinks, doesn't load/instantiate them
- Sinks passed via `__sinks` parameter from tool executor
- EnvManager handles Python dependencies (websockets, etc.) at instantiation time
- See `kiwi_mcp/utils/env_manager.py` and caching implementation in `kiwi_mcp/utils/cache.py`

### Sink Architecture (Data-Driven)

Sinks are **data-driven Python tools** (except `return` which is built into http_client). This follows the same pattern as extractors and capabilities - tools with Python implementations.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SINK TOOL HIERARCHY                                │
│                                                                              │
│  Built-in (http_client):           Data-Driven Tools (.ai/tools/sinks/):    │
│  ┌─────────────────────┐           ┌─────────────────────────────────────┐  │
│  │   return            │           │   file_sink.py                      │  │
│  │   (memory buffer)   │           │   null_sink.py                      │  │
│  │                     │           │   websocket_sink.py                 │  │
│  └─────────────────────┘           └─────────────────────────────────────┘  │
│                                                                              │
│  Why data-driven?                                                            │
│  • Consistent with extractors, capabilities pattern                          │
│  • Dependencies managed by EnvManager (websockets, etc.)                     │
│  • Users can add custom sinks without modifying http_client                  │
│  • Configuration in YAML, implementation in Python                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Built-in `return` sink** (http_client internal):

```python
class ReturnSink:
    """Buffer events for inclusion in result. Built into http_client."""

    def __init__(self, max_size: int = 10000):
        self.buffer: List[str] = []
        self.max_size = max_size

    async def write(self, event: str) -> None:
        if len(self.buffer) < self.max_size:
            self.buffer.append(event)

    async def close(self) -> None:
        pass

    def get_events(self) -> List[str]:
        return self.buffer
```

**Data-driven sinks** are Python runtime tools. See Appendix A.7 for full implementations:

```yaml
# .ai/tools/sinks/file_sink.yaml
tool_id: file_sink
tool_type: runtime
executor_id: python
config:
  module: "sinks.file_sink"
  format: jsonl
  flush_every: 10

# .ai/tools/sinks/null_sink.yaml
tool_id: null_sink
tool_type: runtime
executor_id: python
config:
  module: "sinks.null_sink"

# .ai/tools/sinks/websocket_sink.yaml
tool_id: websocket_sink
tool_type: runtime
executor_id: python
dependencies: ["websockets"]
config:
  module: "sinks.websocket_sink"
  reconnect_attempts: 3
  buffer_on_disconnect: true
```

**Where Sinks Are Instantiated:**

Sink instantiation happens **before http_client execution** by the tool executor during chain resolution. Sinks are passed to http_client via `__sinks` parameter. This keeps http_client a pure primitive with no tool system dependencies:

```python
# In tool executor during chain resolution
async def resolve_tool_chain(self, tool_id: str, params: dict) -> Any:
    """Resolve and execute tool chain with sink instantiation."""

    # Load the tool chain (e.g., anthropic_thread → anthropic_messages → http_client)
    tool_config = await self.load_tool(tool_id)

    # If this tool uses streaming, instantiate sinks
    if tool_config.get("config", {}).get("stream"):
        destinations = tool_config["config"]["stream"]["destinations"]
        sinks = []

        for dest in destinations:
            if dest["type"] == "return":
                # Built-in sink (no tool loading needed)
                sinks.append(ReturnSink(max_size=dest.get("max_size", 10000)))
            else:
                # Load sink tool and instantiate with EnvManager
                sink_tool = await self.load_tool(dest["type"])
                sink_instance = await self.env_manager.instantiate_python_tool(
                    module=sink_tool["config"]["module"],
                    config=dest.get("config", {}),
                    dependencies=sink_tool.get("dependencies", [])
                )
                sinks.append(sink_instance)

        # Add sinks to params for http_client
        params["__sinks"] = sinks

    # Execute the tool chain
    return await self.execute_primitive(tool_config, params)
```

This approach:

- Keeps `http_client` primitive pure (no tool system dependencies)
- Allows tool executor to manage sink lifecycle
- EnvManager handles dependencies (websockets, etc.)
- Sinks are closed properly after streaming completes

---

## Layer 2: LLM Endpoint Tools (Config Only)

These are pure config tools that chain to `http_client`. No code, just data.

### Example: Anthropic Messages Endpoint

```yaml
# .ai/tools/llm/anthropic_messages.yaml
tool_id: anthropic_messages
tool_type: http
version: "1.0.0"
description: "Call Anthropic Messages API"
executor_id: http_client

config:
  method: POST
  url: "https://api.anthropic.com/v1/messages"

  auth:
    type: bearer
    token: "${ANTHROPIC_API_KEY}"

  headers:
    Content-Type: application/json
    anthropic-version: "2023-06-01"

  # Body is templated with params
  body:
    model: "{model}"
    max_tokens: "{max_tokens}"
    stream: "{stream}"
    system: "{system_prompt}"
    messages: "{messages}"
    tools: "{tools}"

  # Streaming config (used when stream=true)
  stream:
    transport: sse
    destinations:
      - type: return # Buffer for caller

parameters:
  - name: model
    type: string
    required: true
    default: "claude-sonnet-4-20250514"
  - name: max_tokens
    type: integer
    required: true
    default: 4096
  - name: stream
    type: boolean
    default: false
  - name: system_prompt
    type: string
    required: false
  - name: messages
    type: array
    required: true
    description: "Array of {role, content} message objects"
  - name: tools
    type: array
    required: false
    description: "Tool definitions for function calling"

# A.3: Retry configuration is data-driven in tool YAML
retry:
  max_attempts: 3
  backoff_ms: [250, 1000, 3000] # Exponential backoff
  retryable_errors:
    - STREAM_INCOMPLETE
    - CONNECTION_RESET
    - TIMEOUT
```

### Example: OpenAI Chat Completions

```yaml
# .ai/tools/llm/openai_chat.yaml
tool_id: openai_chat
tool_type: http
version: "1.0.0"
description: "Call OpenAI Chat Completions API"
executor_id: http_client

config:
  method: POST
  url: "https://api.openai.com/v1/chat/completions"

  auth:
    type: bearer
    token: "${OPENAI_API_KEY}"

  headers:
    Content-Type: application/json

  body:
    model: "{model}"
    max_tokens: "{max_tokens}"
    stream: "{stream}"
    messages: "{messages}"
    tools: "{tools}"
    tool_choice: "{tool_choice}"

parameters:
  - name: model
    type: string
    default: "gpt-4o"
  - name: max_tokens
    type: integer
    default: 4096
  - name: stream
    type: boolean
    default: false
  - name: messages
    type: array
    required: true
  - name: tools
    type: array
    required: false
  - name: tool_choice
    type: string
    required: false
```

---

## Layer 3: Thread Tools (Composable Wrappers)

Thread tools add thread-specific concerns: transcript storage, thread IDs, defaults.

**Thread ID Handling (Three Layers):** Thread ID handling has three distinct layers. See Appendix A.1 for details.

- **Base spawn_thread tool**: Accepts `thread_id` as **required** parameter with permissive validation (alphanumeric, underscore, hyphen)
- **safety_harness tool**: Safety harness implementation entry point, auto-generates structured IDs (`directive_name_YYYYMMDD_HHMMSS`), does NOT expose thread_id parameter
- **thread_directive tool**: High-level directive→thread orchestrator that LLMs call, does NOT expose thread_id parameter

This layering allows flexibility: other harnesses can use base spawn_thread with their own ID schemes, while safety_harness enforces structured IDs.

```yaml
# .ai/tools/threads/anthropic_thread.yaml
tool_id: anthropic_thread
tool_type: http
version: "1.0.0"
description: "Run a conversation thread with Claude"
executor_id: anthropic_messages

config:
  # Inherit from anthropic_messages, add thread-specific config
  stream:
    destinations:
      - type: file
        path: ".ai/threads/{thread_id}/transcript.jsonl" # Per-thread directory
        format: jsonl
      - type: return

parameters:
  - name: thread_id
    type: string
    required: true
    description: "Unique thread identifier (permissive: alphanumeric, underscore, hyphen)"
    # Note: safety_harness auto-generates this; base layer just validates format
  - name: model
    type: string
    default: "claude-sonnet-4-20250514"
  - name: max_tokens
    type: integer
    default: 4096
  - name: stream
    type: boolean
    default: true
  - name: system_prompt
    type: string
    required: false
  - name: messages
    type: array
    required: true
```

### Tool Chain Resolution

```
anthropic_thread → anthropic_messages → http_client (primitive)
```

When executing:

1. `anthropic_thread` config merged with params
2. `anthropic_messages` config merged (child overrides parent)
3. `http_client` executes with final merged config

---

## Layer 4: Harness Architecture

The agent loop lives **outside MCP core**. The harness is a library/CLI that:

1. Calls thread tools via standard MCP execution
2. Parses LLM responses (provider-specific)
3. Executes tool calls by calling MCP tools
4. Feeds results back into next LLM call
5. Handles termination conditions

### Generic Harness vs safety_harness

**Generic harness**: Philosophy-agnostic. Can be configured either way:

- **Nothing → something**: Provide explicit tool list, custom system prompt
- **Everything → something**: Provide directive, inherit from Kiwi

**safety_harness**: Our opinionated implementation using Kiwi philosophy:

- System prompt: Always `AGENTS.md` (universal identity)
- Tools exposed to LLM: Always 4 meta-tools (search, load, execute, help)
- Permissions: Always from directive's `<permissions>` tag
- All tool calls route through Kiwi for permission enforcement

### Mental Model: Run Directive, LLM Decides Execution

The user says "run directive X". The kernel **always returns the directive**. The LLM decides how to execute:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  User: "run directive deploy_staging"                                    │
│                                                                          │
│  Step 1: execute(directive, run, deploy_staging)                         │
│    → Kernel returns directive data (process steps, permissions, etc)     │
│    → No thread logic in kernel (stays dumb)                              │
│                                                                          │
│  Step 2: LLM chooses execution approach (guided by AGENTS.md)            │
│                                                                          │
│  Option A: Follow here (simple, no thread)                               │
│    → LLM follows directive steps in current context                      │
│    → No new thread spawned                                               │
│    → No capability token enforcement (LLM runs outside MCP)              │
│                                                                          │
│  Option B: Spawn managed thread                                          │
│    → LLM calls: execute(tool, run, thread_directive, {...})              │
│    → Thread ID auto-generated: deploy_staging_20260125_103045            │
│    → New thread spawns with full Safety harness                            │
│    → Capability tokens enforced (LLM runs inside MCP)                    │
│    → Cost tracking, loop detection, intervention available               │
│    → Caller can monitor/intervene via thread tools                       │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key distinction:** Kernel always returns directive data. LLM decides whether to follow steps directly or spawn a managed thread by calling `spawn_thread` tool.

### Thread ID: Auto-Generated by Harness

**safety_harness auto-generates thread IDs.** The LLM does NOT provide thread IDs. This ensures:

- **Consistent naming**: All threads follow `directive_name_YYYYMMDD_HHMMSS` pattern
- **Sortable by time**: Easy to find recent threads
- **Directive traceability**: Clear which directive spawned each thread
- **No LLM input required**: Harness controls the ID, preventing collisions

```python
# safety_harness generates thread IDs automatically
def generate_thread_id(directive_name: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{directive_name}_{timestamp}"
    # Example: "deploy_staging_20260125_103045"
```

The **base tool layer** (spawn_thread) accepts any valid ID with permissive sanitization, allowing other harnesses to use their own ID schemes:

```yaml
# spawn_thread base tool - permissive validation
parameters:
  - name: directive_name
    type: string
    required: true
  - name: thread_id
    type: string
    required: true
    description: "Thread identifier (alphanumeric, underscore, hyphen allowed)"
    # safety_harness auto-generates this; other harnesses can provide their own
  - name: initial_message
    type: string
    required: true
```

### safety_harness Implementation

```python
# safety_harness/runner.py (EXTERNAL to MCP core)

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import json

from base_harness.runner import BaseHarnessRunner, HarnessResult, TokenUsage
from base_harness.stream_parser import ContentBlock
from safety_harness.capabilities import permissions_to_caps, mint_token, CapabilityDeniedError
from safety_harness.cost import CostBudget, CostTracker
from safety_harness.context import ThreadContext, ContextTracker


# Response messages extracted for easier management
class ResponseMessages:
    DIRECTIVE_CONTEXT = """You are executing directive: {name}

Description: {description}

Process steps:
{steps}

User request: {initial_message}

Follow the directive steps to complete this task."""

    CONTEXT_WARNING = """⚠️ CONTEXT LIMIT WARNING ⚠️
Current context usage: {current_tokens:,} / {max_tokens:,} tokens ({percentage:.1f}%)
Remaining: {remaining_tokens:,} tokens

Consider:
- Completing current task and ending conversation
- Using help(action="checkpoint") to save progress
- Spawning a sub-thread for remaining work"""

    CONTEXT_EXCEEDED = """❌ CONTEXT LIMIT EXCEEDED ❌
Context usage has exceeded the limit: {current_tokens:,} / {max_tokens:,} tokens
Thread must terminate. Use help(action="checkpoint") or complete immediately."""


@dataclass
class ContextCheckResult:
    """Result of context budget check - structured instead of string matching."""
    exceeded: bool
    warning: bool
    percentage: float
    current_tokens: int
    max_tokens: int
    remaining_tokens: int
    message: Optional[str] = None  # Human-readable message for LLM injection


@dataclass
class ContextBudget:
    """Context window budget from directive metadata.

    Tracks context token usage (input tokens per call) to prevent
    exceeding model context limits.
    """
    max_context_tokens: int  # Model context window limit
    warning_threshold: float = 0.8  # Warn at 80% usage

    @classmethod
    def from_directive(cls, cost_data: dict, model: str = "claude-sonnet-4-20250514") -> "ContextBudget":
        """Create context budget from directive metadata."""
        # Default context limits by model
        model_context_limits = {
            "claude-sonnet-4-20250514": 200_000,
            "claude-opus-4-20250514": 200_000,
            "gpt-4o": 128_000,
        }
        default_limit = model_context_limits.get(model, 200_000)

        return cls(
            max_context_tokens=cost_data.get("max_context_tokens", default_limit),
            warning_threshold=cost_data.get("context_warning_threshold", 0.8),
        )

    def check_context(self, current_input_tokens: int) -> ContextCheckResult:
        """Check context usage. Returns structured result."""
        percentage = current_input_tokens / self.max_context_tokens
        remaining = self.max_context_tokens - current_input_tokens
        exceeded = percentage >= 1.0
        warning = not exceeded and percentage >= self.warning_threshold

        message = None
        if exceeded:
            message = ResponseMessages.CONTEXT_EXCEEDED.format(
                current_tokens=current_input_tokens,
                max_tokens=self.max_context_tokens,
            )
        elif warning:
            message = ResponseMessages.CONTEXT_WARNING.format(
                current_tokens=current_input_tokens,
                max_tokens=self.max_context_tokens,
                percentage=percentage * 100,
                remaining_tokens=remaining,
            )

        return ContextCheckResult(
            exceeded=exceeded,
            warning=warning,
            percentage=percentage,
            current_tokens=current_input_tokens,
            max_tokens=self.max_context_tokens,
            remaining_tokens=remaining,
            message=message,
        )


class SafetyHarnessRunner(BaseHarnessRunner):
    """
    Safety harness using the "everything → something" philosophy with guardrails.

    Features:
    - System prompt = AGENTS.md (universal)
    - Tools = 4 Kiwi meta-tools (search, load, execute, help)
    - Permissions enforced via capability tokens (A.2)
    - Cost budget from directive's <cost> (REQUIRED - A.4)
    - Context tracking to prevent exceeding model limits
    - Thread registry via data-driven tool (A.5)
    - Loop detection and intervention signals

    Permissions are hierarchical:
    - Core system directives (thread_directive) have broad permissions
    - User directives run with their own (more limited) permissions
    - Harness enforces whatever token the current directive minted
    """

    def __init__(self, mcp_executor: "ToolExecutor", project_path: Optional[str] = None):
        super().__init__(mcp_executor)
        self.project_path = project_path
        self.context: Optional[ThreadContext] = None
        self.cost_tracker: Optional[CostTracker] = None
        self.context_budget: Optional[ContextBudget] = None

    async def run_directive(
        self,
        directive_name: str,
        initial_message: str,
        model: str = "claude-sonnet-4-20250514",
    ) -> "ThreadResult":
        """
        Run a directive on a new thread.

        This is the safety harness entry point that:
        1. Auto-generates thread_id from directive_name + timestamp (A.1)
        2. Loads and parses the directive
        3. Mints capability token from <permissions> (A.2)
        4. Validates and extracts cost budget (A.4)
        5. Initializes context tracking
        6. Uses AGENTS.md as system prompt
        7. Runs the agent loop with enforcement
        """
        # A.1: Auto-generate thread ID
        thread_id = self._generate_thread_id(directive_name)

        # Load and parse directive (not raw load - extract structured data)
        directive_result = await self.executor.execute(
            tool_id="execute",
            params={
                "item_type": "directive",
                "action": "run",
                "item_id": directive_name,
                "parameters": {},  # No inputs yet, just loading
            }
        )

        if not directive_result.success:
            raise ValueError(f"Failed to load directive: {directive_result.error}")

        directive_data = directive_result.data

        # A.2: Mint capability token from directive permissions
        capability_token = self._mint_capability_token(
            permissions=directive_data["permissions"],
            directive_id=directive_name,
            thread_id=thread_id,
        )

        # A.4: Extract cost budget (REQUIRED)
        cost_data = directive_data.get("cost")
        if not cost_data:
            raise ValueError(
                f"Directive '{directive_name}' is missing required <cost> tag. "
                "Add <cost><max_turns>30</max_turns><on_exceeded>escalate</on_exceeded></cost>"
            )

        cost_budget = CostBudget.from_directive(cost_data)
        self.cost_tracker = CostTracker(cost_budget, model)

        # Context budget for tracking context window usage
        self.context_budget = ContextBudget.from_directive(cost_data, model)

        # Build thread context
        self.context = ThreadContext(
            thread_id=thread_id,
            directive_name=directive_name,
            capability_token=capability_token,
            cost_budget=cost_budget,
        )

        # Note: Thread registry registration is OPTIONAL
        # If directive has registry.write capability, it can register itself
        # Otherwise, external monitoring tools can query thread state via other means

        # Load AGENTS.md as system prompt
        agents_md = await self._load_agents_md()

        # Build first message with directive context
        first_message = ResponseMessages.DIRECTIVE_CONTEXT.format(
            name=directive_data["name"],
            description=directive_data.get("description", ""),
            steps=self._format_process_steps(directive_data.get("process", [])),
            initial_message=initial_message,
        )

        try:
            # Run the base harness loop
            result = await super().run(
                system_prompt=agents_md,
                initial_message=first_message,
            )

            return ThreadResult(
                thread_id=thread_id,
                directive_name=directive_name,
                messages=result.messages,
                turn_count=result.turn_count,
                total_usage=result.total_usage,
                cost_summary=self.cost_tracker.get_summary() if self.cost_tracker else None,
            )

        finally:
            # Thread cleanup happens here
            # Registry updates are optional (if directive has registry.write)
            final_status = "completed" if not self._termination_reason else self._termination_reason
            # No automatic registry calls - directives opt-in to registry if needed
                tool_id="thread_registry",
                params={
                    "action": "update_status",
                    "thread_id": thread_id,
                    "status": final_status,
                    "usage": self.total_usage.__dict__ if self.total_usage else None,
                    "cost_summary": self.cost_tracker.get_summary() if self.cost_tracker else None,
                }
            )

    def _get_tools(self) -> List[dict]:
        """Return the 4 Kiwi meta-tools."""
        return [
            {
                "name": "search",
                "description": "Find directives, tools, knowledge, or MCPs",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "item_type": {"type": "string", "enum": ["directive", "tool", "knowledge"]},
                        "query": {"type": "string"},
                        "source": {"type": "string", "enum": ["local", "registry", "all"]},
                    },
                    "required": ["item_type", "query"]
                }
            },
            {
                "name": "load",
                "description": "Get item details or copy between locations",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "item_type": {"type": "string"},
                        "item_id": {"type": "string"},
                        "source": {"type": "string"},
                        "destination": {"type": "string"},
                    },
                    "required": ["item_type", "item_id"]
                }
            },
            {
                "name": "execute",
                "description": "Run a tool with parameters (permission checked)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "item_type": {"type": "string"},
                        "action": {"type": "string"},
                        "item_id": {"type": "string"},
                        "parameters": {"type": "object"},
                    },
                    "required": ["item_type", "action", "item_id"]
                }
            },
            {
                "name": "help",
                "description": "Get guidance, signal stuck, escalate, or checkpoint",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["guidance", "stuck", "escalate", "checkpoint"]},
                        "topic": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["action"]
                }
            },
        ]

    async def _execute_tool_calls(self, tool_calls: List[ContentBlock]) -> list:
        """Execute tool calls via Kiwi MCP with capability tokens."""
        results = []

        for tool_call in tool_calls:
            # Record for loop detection
            loop_signal = self.context.record_tool_call(tool_call)
            if loop_signal:
                await self._handle_loop_detected(loop_signal)

            try:
                # Execute via Kiwi with capability token (A.2)
                result = await self.executor.execute(
                    tool_id=tool_call.tool_name,
                    params={
                        **tool_call.input_parsed,
                        "__auth": self.context.capability_token,
                        "__thread_id": self.context.thread_id,
                        "__directive_id": self.context.directive_name,
                    }
                )

                results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.tool_id,
                    "content": json.dumps(result.data) if result.success else json.dumps({"error": result.error}),
                    **({"is_error": True} if not result.success else {}),
                })

            except CapabilityDeniedError as e:
                results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.tool_id,
                    "content": json.dumps({
                        "error": "Capability denied",
                        "missing_caps": e.missing_capabilities,
                        "suggestion": "Use help(action='escalate') to request capability"
                    }),
                    "is_error": True,
                })

        return results

    def _should_terminate(self) -> bool:
        """Check if agent should stop (cost + context limits)."""
        self._termination_reason = None

        # Check cost budget
        if self.cost_tracker:
            exceeded = self.cost_tracker.budget.exceeded(
                self.cost_tracker.usage,
                self.cost_tracker.model,
                self.cost_tracker.turns
            )
            if exceeded:
                self._termination_reason = f"cost_exceeded: {exceeded}"
                return True

        # Check context budget (based on last turn's input tokens)
        if self.context_budget and self.total_usage:
            context_result = self.context_budget.check_context(self.total_usage.input_tokens)
            if context_result.exceeded:
                self._termination_reason = "context_exceeded"
                return True

        # Standard max turns check
        if self.context and self.context.cost_budget.max_turns:
            if self.turn_count >= self.context.cost_budget.max_turns:
                self._termination_reason = "max_turns_exceeded"
                return True

        return False

    async def _call_llm(self, messages: list, tools: list) -> dict:
        """Call LLM via Kiwi's thread tool with streaming."""
        result = await self.executor.execute(
            tool_id="anthropic_thread",
            params={
                "thread_id": self.context.thread_id,
                "messages": messages,
                "tools": tools,
                "mode": "stream",
                "stream": True,
            }
        )
        return result.data

    def _generate_thread_id(self, directive_name: str) -> str:
        """A.1: Generate structured thread ID from directive name + timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{directive_name}_{timestamp}"

    def _mint_capability_token(
        self,
        permissions: List[dict],
        directive_id: str,
        thread_id: str
    ) -> str:
        """A.2: Mint signed capability token from directive permissions."""
        caps = permissions_to_caps(permissions)
        return mint_token(
            caps=caps,
            aud="kiwi-mcp",
            directive_id=directive_id,
            thread_id=thread_id,
            ttl_minutes=30,
        )

    async def _load_agents_md(self) -> str:
        """Load AGENTS.md as system prompt."""
        result = await self.executor.execute(
            tool_id="read_file",
            params={"path": "AGENTS.md"}
        )
        return result.data.get("content", "") if result.success else ""

    def _format_process_steps(self, steps: list) -> str:
        """Format process steps for context."""
        if not steps:
            return "(No explicit steps defined)"
        return "\n".join(
            f"- {step.get('name', 'Step')}: {step.get('description', '')}"
            for step in steps
        )

    async def _handle_loop_detected(self, signal: "LoopSignal"):
        """Handle detected loop pattern."""
        await self.executor.execute(
            tool_id="thread_registry",
            params={
                "action": "log_event",
                "thread_id": self.context.thread_id,
                "event_type": "loop_detected",
                "data": {"pattern": signal.pattern, "count": signal.count}
            }
        )


@dataclass
class ThreadResult:
    """Result from running a directive on a thread."""
    thread_id: str
    directive_name: str
    messages: List[dict]
    turn_count: int
    total_usage: TokenUsage
    cost_summary: Optional[dict] = None
```

---

## Layer 4.5: Execute Directive Action (Kernel Stays Dumb)

### Design Principle: No Thread Logic in Kernel

The kernel has **no knowledge of threads**. When `execute(directive, run, ...)` is called, it **always** returns the directive to the caller. The LLM/harness decides whether to:

1. Follow the directive steps in the current context, OR
2. Spawn a new thread using the `spawn_thread` tool directly

This keeps the kernel truly dumb - thread spawning is just another tool call, not special kernel behavior.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  DIRECTIVE EXECUTION (Kernel Stays Dumb)                 │
│                                                                          │
│  execute(directive, run, deploy_staging)                                 │
│                 │                                                        │
│                 ▼                                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  Kernel: Parse, validate, return directive data                     │ │
│  │  (No thread logic, no mode parameter, no spawn dependency)          │ │
│  └───────────────────────────────────┬─────────────────────────────────┘ │
│                                      │                                   │
│                                      ▼                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  LLM receives directive data + instructions                         │ │
│  │                                                                      │ │
│  │  Option A: Follow steps in current context                          │ │
│  │    → Just do the work (no thread spawn)                             │ │
│  │                                                                      │ │
│  │  Option B: Spawn a managed thread                                   │ │
│  │    → execute(tool, run, thread_directive, {directive_name: ...})    │ │
│  │    → LLM explicitly calls the directive→thread orchestrator         │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Execute Directive Handler (Simple)

The execute handler for directives is now simple - it just loads, validates, and returns:

```python
# Inside execute handler for directive.run
from kiwi_mcp.handlers.directive.messages import ResponseMessages

async def _run_directive(self, directive_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Run directive: always returns directive data to caller.

    Kernel has NO thread logic. If caller wants a thread, they use
    the spawn_thread tool directly.
    """
    # Find and parse directive file
    file_path = self.resolver.resolve(directive_name)
    if not file_path:
        return {
            "error": f"Directive '{directive_name}' not found locally",
            "suggestion": "Use load() to download from registry first",
        }

    # Parse directive (extracts structured data, not raw load)
    directive_data = parse_directive_file(file_path)

    # Validate (integrity, permissions, model, version, cost)
    validation_result = await ValidationManager.validate_and_embed(
        "directive", file_path, directive_data
    )
    if not validation_result["valid"]:
        return {"error": "Directive validation failed", "details": validation_result["issues"]}

    # Extract process steps, inputs, etc.
    process_steps = self._extract_process_steps(directive_data)
    inputs_spec = self._extract_inputs_spec(directive_data)

    # Validate required inputs are provided
    missing_inputs = self._check_missing_inputs(inputs_spec, params.get("inputs", {}))
    if missing_inputs:
        return {
            "error": "Required directive inputs are missing",
            "missing_inputs": missing_inputs,
        }

    # Check if directive can be spawned as a thread (has cost tag)
    can_spawn = bool(directive_data.get("cost"))

    return {
        "status": "ready",
        "directive": {
            "name": directive_data["name"],
            "description": directive_data["description"],
            "process": process_steps,
            "inputs": inputs_spec,
            "permissions": directive_data.get("permissions", []),
            "cost": directive_data.get("cost", {}),
        },
        "can_spawn_thread": can_spawn,
        "message": ResponseMessages.DIRECTIVE_LOADED,
    }
```

```python
# kiwi_mcp/handlers/directive/messages.py
# Extracted for easier management and localization

class ResponseMessages:
    DIRECTIVE_LOADED = "Directive loaded. Follow the process steps, or spawn a thread for managed execution. See AGENTS.md and run_directive directive for thread spawning guidance."
```

### The run_directive Directive (Orchestration Pattern)

**Terminology Note:** `run_directive` and `thread_directive` are distinct in Kiwi:

1. **run_directive directive** - `.ai/directives/run_directive.md` - Workflow instructions that guide LLMs on how to run directives (when to spawn thread vs follow directly)
2. **thread_directive tool** - `.ai/tools/orchestration/thread_directive.yaml` - Executable tool for spawning directives on managed threads

**Critical distinction:**

- `run_directive` is a DIRECTIVE that provides guidance to LLMs about directive execution patterns
- `thread_directive` is the TOOL that LLMs actually call to spawn managed threads
- There is NO tool named `run_directive` - this would cause confusion with the directive
- LLMs read the run_directive directive for guidance, but call the thread_directive tool for execution

This section covers the **directive** (workflow instructions). For the tool, see Appendix A.1 Layer 3.

---

The `run_directive` directive provides LLMs with detailed guidance on running directives and choosing execution modes:

```xml
<!-- .ai/directives/run_directive.md -->
<directive name="run_directive" version="1.0.0">
  <metadata>
    <description>Guide for running directives with execution mode selection</description>
    <category>core</category>
    <author>kiwi-mcp</author>

    <model tier="general" fallback="reasoning" parallel="false">
      Directive execution orchestration with mode selection logic
    </model>

    <cost>
      <max_turns>10</max_turns>
      <max_total_tokens>50000</max_total_tokens>
      <on_exceeded>stop</on_exceeded>
    </cost>

    <permissions>
      <read resource="filesystem" path="**/*"/>
      <execute resource="kiwi-mcp" action="execute"/>
      <execute resource="kiwi-mcp" action="load"/>
      <execute resource="kiwi-mcp" action="search"/>
    </permissions>

    <relationships>
      <suggests>thread_directive</suggests>
      <suggests>create_directive</suggests>
    </relationships>
  </metadata>

  <inputs>
    <input name="directive_name" type="string" required="true">
      Name of the directive to run
    </input>
    <input name="initial_message" type="string" required="false">
      Initial message/task for the directive
    </input>
  </inputs>

  <process>
    <step name="load_directive">
      <description>Load and validate the directive</description>
      <action>
        execute(item_type="directive", action="run", item_id="{directive_name}")
      </action>
    </step>

    <step name="decide_execution">
      <description>Decide execution mode based on directive complexity</description>
      <action>
        Analyze directive metadata:

        For simple directives (1-3 steps, no orchestration):
          → Follow steps in current context (Pattern A)
          → No thread spawning needed

        For complex directives (has &lt;cost&gt;, orchestrator tier):
          → Spawn managed thread using thread_directive tool (Pattern B)
          → Provides cost tracking, isolation, intervention

        Required for spawning:
          • &lt;cost&gt; tag with max_turns and on_exceeded (REQUIRED)
          • &lt;permissions&gt; tag (REQUIRED)
          • &lt;model&gt; tier (REQUIRED)
          • version (REQUIRED)
      </action>
    </step>

    <step name="spawn_managed_thread">
      <description>Spawn thread for complex directives</description>
      <condition>Directive requires managed execution</condition>
      <action>
        execute(
            item_type="tool",
            action="run",
            item_id="thread_directive",
            parameters={
                "directive_name": "{directive_name}",
                "initial_message": "{initial_message}"
            }
        )

        Returns: thread_id immediately (async execution)
        Monitor via: thread_registry tool or transcript file
      </action>
    </step>

    <step name="follow_steps">
      <description>Execute simple directives directly</description>
      <condition>Directive is simple (no managed thread needed)</condition>
      <action>Follow the directive's process steps in current context</action>
    </step>
  </process>
</directive>
```

### Why This Is Cleaner

| Aspect            | Old Design (thread param)           | New Design (kernel stays dumb) |
| ----------------- | ----------------------------------- | ------------------------------ |
| Kernel complexity | Has thread spawning logic           | No thread knowledge            |
| Dependencies      | Kernel depends on spawn_thread tool | No tool dependencies           |
| Thread spawning   | Special case in execute handler     | Normal tool call by LLM        |
| Flexibility       | Kernel decides spawn behavior       | LLM/harness decides            |
| Testing           | Must test spawn logic in kernel     | Spawn is just a tool test      |

The kernel stays truly dumb - it returns data, the LLM makes decisions.

---

### Directive Execution: Two Patterns

LLMs have two distinct ways to execute directives, depending on complexity and requirements:

#### **Pattern A: Direct Execution (Current Thread)**

```python
execute(directive, run, "deploy_staging", {
    inputs: {...}
})
```

**What happens:**

- Kernel returns directive data immediately (process steps, permissions, etc.)
- LLM follows steps in current context
- No new thread spawned
- No cost tracking or isolation
- No capability token enforcement (if LLM is already outside MCP)

**Use when:**

- Simple directives (1-3 steps)
- Already in a managed thread context
- No need for isolation or intervention
- Directive doesn't have `<cost>` tag

**Example:**

```python
# Load and follow a simple formatting directive
result = execute(directive, run, "format_code", {
    inputs: {"language": "python", "file": "main.py"}
})
# LLM receives directive and follows its steps immediately
```

#### **Pattern B: Managed Thread Execution**

```python
execute(tool, run, "thread_directive", {
    directive_name: "deploy_staging",
    initial_message: "Deploy v1.2.3 to staging"
})
```

**What happens:**

- `thread_directive` tool validates directive has ALL required metadata
- Spawns new managed thread with safety_harness
- Full harness with cost tracking and capability tokens
- Returns thread_id immediately (async execution)
- Thread runs independently in background

**Use when:**

- Complex directives (orchestrators, multi-step workflows)
- Need cost tracking and budget enforcement
- Want isolation and permission enforcement
- Potential for long-running execution
- Directive has `<cost>` tag (REQUIRED for spawning)

**Example:**

```python
# Spawn a long-running deployment on a managed thread
result = execute(tool, run, "thread_directive", {
    directive_name: "deploy_staging",
    initial_message: "Deploy v1.2.3 to staging"
})
# Returns: {"thread_id": "deploy_staging_20260125_103045", "status": "spawned"}
# Monitor via thread_registry or transcript file
```

**Comparison:**

| Aspect             | Pattern A (Direct)    | Pattern B (Managed Thread) |
| ------------------ | --------------------- | -------------------------- |
| Execution          | Synchronous, inline   | Asynchronous, background   |
| Cost tracking      | No                    | Yes (REQUIRED)             |
| Capability tokens  | No enforcement        | Full enforcement           |
| Isolation          | Shares caller context | Isolated thread context    |
| Intervention       | Not available         | Can pause/resume/monitor   |
| Returns            | Directive data        | thread_id                  |
| Use case           | Simple, quick tasks   | Complex, long-running      |
| Directive `<cost>` | Optional              | REQUIRED                   |

---

### The spawn_thread Tool (Data-Driven, Three Layers)

Thread spawning has three tool layers (see Appendix A.1 for full details):

1. **Base spawn_thread** - Primitive tool requiring `thread_id` parameter
2. **safety_harness** - Safety harness implementation entry point that auto-generates thread IDs
3. **thread_directive** - High-level directive→thread orchestrator (what LLMs call)

#### Base spawn_thread Tool

The base `spawn_thread` tool requires the caller to provide a thread_id:

```yaml
# .ai/tools/threads/spawn_thread.yaml (BASE LAYER)
tool_id: spawn_thread
tool_type: runtime
version: "1.0.0"
description: "Spawn a new managed thread to execute a directive"
executor_id: python

config:
  module: "safety_harness.spawn"
  function: "spawn_thread_base"
  timeout: 3600 # 1 hour max
  background: true # Don't block caller

parameters:
  - name: thread_id
    type: string
    required: true # REQUIRED at base layer
    description: "Thread identifier (alphanumeric, underscore, hyphen allowed)"
  - name: directive_name
    type: string
    required: true
    description: "Name of the directive to execute"
  - name: initial_message
    type: string
    required: false
    default: "Execute this directive."
    description: "Initial message for the LLM"
  - name: inputs
    type: object
    required: false
    description: "Directive input parameters"
  - name: project_path
    type: string
    required: false
    description: "Project path for .ai/ resolution"
# Returns (success):
# {
#   "success": true,
#   "thread_id": "<provided_id>",
#   "status": "spawned",
#   "transcript_path": ".ai/threads/<thread_id>/transcript.jsonl",
#   "registry_id": 123,
#   "started_at": "2026-01-25T10:30:45Z"
# }
#
# Returns (failure):
# {
#   "success": false,
#   "error": "Thread ID already exists",
#   "code": "THREAD_ID_COLLISION",
#   "thread_id": "<attempted_id>"
# }
```

#### safety_harness Tool (Safety Harness Implementation Layer)

The `safety_harness` tool is the entry point for the Safety harness implementation. It auto-generates thread IDs and instantiates SafetyHarnessRunner:

```yaml
# safety_harness/tools/safety_harness.yaml (or included in harness package)
tool_id: safety_harness
tool_type: runtime
version: "1.0.0"
description: "Safety harness implementation - spawns directive on managed thread"
executor_id: python

config:
  module: "safety_harness.spawn"
  function: "spawn_with_safety_harness"

parameters:
  - name: directive_name
    type: string
    required: true
  - name: initial_message
    type: string
    required: false
  - name: inputs
    type: object
    required: false
  - name: project_path
    type: string
    required: false
  # Note: NO thread_id parameter - auto-generated as directive_name_YYYYMMDD_HHMMSS
# Returns (success):
# {
#   "success": true,
#   "thread_id": "deploy_staging_20260125_103045",
#   "status": "spawned",
#   "transcript_path": ".ai/threads/deploy_staging_20260125_103045/transcript.jsonl",
#   "registry_id": 123,
#   "started_at": "2026-01-25T10:30:45Z"
# }
#
# Returns (failure):
# {
#   "success": false,
#   "error": "Failed to spawn thread: <reason>",
#   "code": "SPAWN_FAILED",
#   "directive_name": "deploy_staging"
# }
```

When LLMs use safety_harness, they typically call `thread_directive` (Layer 3), which validates and calls `safety_harness`.

**Important:** Both `spawn_thread` and `safety_harness` are **async spawn operations**. They return immediately after starting the thread in the background. The spawned thread runs independently, and the caller gets a thread_id for monitoring/intervention.

To wait for thread completion, use thread monitoring tools or check the thread registry for status updates (see Layer 8.5).

### Thread Spawning Flow (LLM-Driven)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                  Thread Spawning (LLM Calls Tool Directly)                   │
│                                                                              │
│  1. LLM calls: execute(directive, run, deploy_staging)                       │
│                 │                                                            │
│                 ▼                                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  Kernel: Returns directive data (process steps, permissions, cost, etc)  │ │
│  │  (No thread logic, no spawn instructions, just data)                     │ │
│  └───────────────────────────────────┬─────────────────────────────────────┘ │
│                                      │                                       │
│                                      ▼                                       │
│  2. LLM decides to spawn (guided by AGENTS.md), calls:                      │
│     execute(tool, run, spawn_thread, {...})                                 │
│                 │                                                            │
│                 ▼                                                            │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  ToolExecutor resolves spawn_thread                                      │ │
│  │                                                                           │ │
│  │  spawn_thread.yaml → executor_id: python                                 │ │
│  │                    → python primitive (venv execution)                   │ │
│  └───────────────────────────────────┬─────────────────────────────────────┘ │
│                                      │                                       │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  safety_harness.spawn.spawn_with_safety_harness():                           │ │
│  │                                                                           │ │
│  │  1. Generate thread_id = "deploy_staging_20260125_103045"                │ │
│  │  2. Instantiate SafetyHarnessRunner(project_path, mcp_client)              │ │
│  │  3. Call spawn_thread tool with runner_instance                          │ │
│  │  4. Return {"thread_id": "...", "status": "spawned"}                     │ │
│  └───────────────────────────────────┬─────────────────────────────────────┘ │
│                                      │                                       │
│                                      ▼                                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  Inside spawned thread: runner.run()                                      │ │
│  │                                                                           │ │
│  │  1. Load directive via MCP                                                │ │
│  │  2. Extract <permissions> from directive                                  │ │
│  │  3. Mint capability token                                                 │ │
│  │  4. Build system prompt from AGENTS.md                                    │ │
│  │  5. Start agent loop (call LLM → execute tools → repeat)                 │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### The Tool Chain for Thread Spawning

```
LLM decides to spawn
    │
    ▼
execute(tool, run, thread_directive, {...})  ← LLM makes this call explicitly
    │
    ▼
spawn_thread.yaml (data-driven config)
    │
    ▼
python primitive (safety_harness.spawn)
    │
    ▼
safety_harness.runner (agent loop)
    │
    ├──► anthropic_thread.yaml (LLM calls)
    │        │
    │        ▼
    │    anthropic_messages.yaml
    │        │
    │        ▼
    │    http_client primitive (streaming)
    │
    └──► Kiwi MCP (for tool calls from the new thread)
             │
             ▼
         Permission enforcement from directive
```

### Execute Handler Implementation (Simple)

```python
# kiwi_mcp/handlers/execute_handler.py

class ExecuteHandler:
    """Handles execute action for all item types.

    NOTE: Kernel has NO thread logic. Thread spawning is done by LLM
    calling the spawn_thread tool directly.
    """

    def __init__(
        self,
        tool_executor: ToolExecutor,
        directive_loader: DirectiveLoader,
    ):
        self.tool_executor = tool_executor
        self.directive_loader = directive_loader

    async def execute_directive(
        self,
        item_id: str,
        action: str,
        parameters: dict
    ) -> dict:
        """Execute a directive action."""

        if action == "run":
            return await self._run_directive(item_id, parameters)
        elif action == "create":
            # ... create logic
        # ... other actions

    async def _run_directive(
        self,
        directive_name: str,
        parameters: dict
    ) -> dict:
        """Run a directive: ALWAYS returns directive to caller.

        No thread logic here. If caller wants to spawn, they call
        spawn_thread tool themselves.
        """
        from kiwi_mcp.handlers.directive.messages import ResponseMessages

        # Load and parse directive data (structured, not raw)
        directive_data = await self.directive_loader.load_and_parse(directive_name)

        # Check if directive can be spawned (has cost tag)
        can_spawn = bool(directive_data.get("cost"))

        # Always return directive to caller
        return {
            "status": "ready",
            "directive": directive_data,
            "can_spawn_thread": can_spawn,
            "message": ResponseMessages.DIRECTIVE_LOADED,
            "spawn_instructions": ResponseMessages.SPAWN_INSTRUCTIONS if can_spawn else None,
        }
```

### Summary: Kernel Stays Truly Dumb

The kernel has **zero thread awareness**:

| Action            | Who Decides | What Kernel Does           |
| ----------------- | ----------- | -------------------------- |
| Run directive     | LLM         | Returns directive data     |
| Spawn thread      | LLM         | Executes spawn_thread tool |
| Call LLM          | Harness     | Executes anthropic_thread  |
| Call external MCP | LLM         | Executes mcp tool          |

The kernel is a pure data router - it never makes thread decisions.

---

## Layer 5: Composable Thread Patterns

### Pattern 1: Run Directive Locally

```
User → Frontend Agent (with AGENTS.md) → load directive → follow steps
                                       ↓
                                    MCP Tools
```

### Pattern 2: Run Directive on New Thread

```
User → Frontend Agent → spawn_thread(directive, thread_id) → New Thread
                                                                  ↓
                                                    Kiwi MCP (permission enforced)
                                                                  ↓
                                                           Directive scope
```

### Pattern 3: Thread Spawning Thread

```
Thread A → spawn_thread(directive_B, "subtask_xyz") → Thread B
                                                          ↓
                                                 Thread B completes
                                                          ↓
                                               Result returned to Thread A
```

### Pattern 4: Streaming to Remote Client

```
User → Harness → Thread Tool → http_client (stream)
                                    ↓
                    ┌───────────────┼───────────────┐
                    ↓               ↓               ↓
              file sink     websocket sink    return buffer
                                    ↓
                         Remote WebSocket Client
```

### Pattern 5: Parallel Thread Coordination

```
                    ┌─ spawn_thread (Thread B) ─→ result B
                    │
Thread A ───────────┼─ spawn_thread (Thread C) ─→ result C
                    │
                    └─ spawn_thread (Thread D) ─→ result D
                                    │
                         Thread A aggregates results
```

---

## Layer 5.5: Streaming Agent Loop & Cost Tracking

### Harness Hierarchy

The harness architecture has two layers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         HARNESS HIERARCHY                                    │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    Generic Base Harness (Base)                         │ │
│  │                                                                          │ │
│  │  • Stream parsing (SSE events → structured data)                        │ │
│  │  • Tool call detection and accumulation                                  │ │
│  │  • Token usage extraction                                                │ │
│  │  • Agent loop mechanics (call LLM → execute tools → repeat)             │ │
│  │  • Philosophy-agnostic (works with any tool set)                        │ │
│  │                                                                          │ │
│  │  Package: base_harness/                                                │ │
│  │  Anyone can use this to build their own agent                           │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                  │                                           │
│                                  │ extends                                   │
│                                  ▼                                           │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    Safety Harness (Our Implementation)                    │ │
│  │                                                                          │ │
│  │  • Uses Kiwi's "everything → something" philosophy                      │ │
│  │  • System prompt = AGENTS.md (universal)                                │ │
│  │  • Tools = 4 Kiwi meta-tools (search, load, execute, help)              │ │
│  │  • Permissions from directive's <permissions>                           │ │
│  │  • Cost budget from directive's <cost>                                  │ │
│  │  • Loop detection and intervention signals                              │ │
│  │  • Annealing integration                                                │ │
│  │                                                                          │ │
│  │  Package: safety_harness/                                                 │ │
│  │  Built on top of base_harness for safety features (cost, permissions) │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Why this separation?**

- The generic harness is useful for anyone building agents with streaming LLMs
- The Safety harness adds our philosophy without polluting the base
- Others can build their own harness implementations on top of the generic base
- Testing is easier (test base mechanics separately from Kiwi logic)

### The Streaming Challenge

When any harness calls the LLM, the response is **streamed via SSE**. This creates several challenges:

1. **Tool calls arrive incrementally** - The `tool_use` content blocks come as partial JSON in `content_block_delta` events
2. **The LLM doesn't wait** - It keeps generating while we're parsing the stream
3. **We must buffer and parse** - Tool call parameters must be accumulated and parsed when complete
4. **Cost data arrives at the end** - Token usage comes in `message_delta` events (cumulative)
5. **Directive context must be maintained** - For permission checking on each tool call

### SSE Event Flow from LLM

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Claude SSE Stream Event Sequence                          │
│                                                                              │
│  event: message_start                                                        │
│  data: {"type":"message_start","message":{"id":"msg_01X...","usage":{...}}} │
│                                                                              │
│  event: content_block_start                                                  │
│  data: {"type":"content_block_start","index":0,"content_block":              │
│         {"type":"text","text":""}}                                           │
│                                                                              │
│  event: content_block_delta                                                  │
│  data: {"type":"content_block_delta","index":0,                              │
│         "delta":{"type":"text_delta","text":"I'll read the file"}}          │
│                                                                              │
│  event: content_block_stop                                                   │
│  data: {"type":"content_block_stop","index":0}                              │
│                                                                              │
│  event: content_block_start                                                  │
│  data: {"type":"content_block_start","index":1,"content_block":              │
│         {"type":"tool_use","id":"toolu_01X...","name":"execute",            │
│          "input":{}}}                                                        │
│                                                                              │
│  event: content_block_delta  (partial JSON!)                                 │
│  data: {"type":"content_block_delta","index":1,                              │
│         "delta":{"type":"input_json_delta",                                  │
│                  "partial_json":"{\"tool_id\":"}}                           │
│                                                                              │
│  event: content_block_delta  (more partial JSON)                             │
│  data: {"type":"content_block_delta","index":1,                              │
│         "delta":{"type":"input_json_delta",                                  │
│                  "partial_json":"\"read_file\",\"params\":"}}               │
│                                                                              │
│  event: content_block_delta  (final JSON piece)                              │
│  data: {"type":"content_block_delta","index":1,                              │
│         "delta":{"type":"input_json_delta",                                  │
│                  "partial_json":"{\"path\":\"src/main.py\"}}"}}             │
│                                                                              │
│  event: content_block_stop                                                   │
│  data: {"type":"content_block_stop","index":1}                              │
│                                                                              │
│  event: message_delta  (contains usage!)                                     │
│  data: {"type":"message_delta","delta":{"stop_reason":"tool_use"},          │
│         "usage":{"output_tokens":47}}                                        │
│                                                                              │
│  event: message_stop                                                         │
│  data: {"type":"message_stop"}                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Generic Stream Parser (Base Layer)

The generic harness provides stream parsing that works with any LLM provider. This is **not Kiwi-specific**:

```python
# base_harness/stream_parser.py
# GENERIC - Can be used by anyone building an base harness

from dataclasses import dataclass, field
from typing import Optional, List, Protocol
import json

@dataclass
class ContentBlock:
    """Accumulated content block from stream."""
    index: int
    type: str  # "text" or "tool_use"
    text: str = ""
    tool_id: Optional[str] = None
    tool_name: Optional[str] = None
    input_json: str = ""  # Accumulated partial JSON
    input_parsed: Optional[dict] = None

    # A.3: Completion tracking for error recovery
    is_complete: bool = False  # True only if JSON parsed successfully
    parse_error: Optional[str] = None  # Error message if parse failed

@dataclass
class StreamState:
    """State accumulated from SSE stream."""
    message_id: str = ""
    content_blocks: List[ContentBlock] = field(default_factory=list)
    stop_reason: Optional[str] = None
    clean_finish: bool = False  # A.3: Did stream end cleanly?

    # Usage tracking (cumulative from message_delta)
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0

    def get_tool_calls(self) -> List[ContentBlock]:
        """Get all COMPLETED tool_use blocks (A.3).

        Only returns blocks where is_complete=True, meaning JSON parsed successfully.
        Partial/failed tool calls are excluded.
        """
        return [b for b in self.content_blocks
                if b.type == "tool_use" and b.is_complete and b.input_parsed]

    def get_partial_tool_calls(self) -> List[ContentBlock]:
        """Get partial/failed tool_use blocks for error reporting (A.3)."""
        return [b for b in self.content_blocks
                if b.type == "tool_use" and not b.is_complete]

    def get_text_content(self) -> str:
        """Get accumulated text content."""
        return "".join(b.text for b in self.content_blocks if b.type == "text")

@dataclass
class TokenUsage:
    """Token usage from LLM calls."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0

    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class StreamParser:
    """
    Parse SSE stream from LLM into structured state.

    GENERIC: Works with Anthropic Claude SSE format.
    Could be extended/subclassed for OpenAI or other providers.
    """

    def __init__(self):
        self.state = StreamState()
        self._current_blocks: dict[int, ContentBlock] = {}

    def process_event(self, event_type: str, data: dict) -> Optional[str]:
        """
        Process a single SSE event.

        Returns:
        - "tool_calls_ready" when message complete with tool calls
        - "message_complete" when message complete without tool calls
        - None for intermediate events
        """

        if event_type == "message_start":
            self.state.message_id = data["message"]["id"]
            usage = data["message"].get("usage", {})
            self.state.input_tokens = usage.get("input_tokens", 0)
            return None

        elif event_type == "content_block_start":
            index = data["index"]
            block_data = data["content_block"]

            block = ContentBlock(
                index=index,
                type=block_data["type"],
            )

            if block.type == "tool_use":
                block.tool_id = block_data.get("id")
                block.tool_name = block_data.get("name")

            self._current_blocks[index] = block
            return None

        elif event_type == "content_block_delta":
            index = data["index"]
            delta = data["delta"]
            block = self._current_blocks.get(index)

            if not block:
                return None

            if delta["type"] == "text_delta":
                block.text += delta["text"]
            elif delta["type"] == "input_json_delta":
                block.input_json += delta["partial_json"]

            return None

        elif event_type == "content_block_stop":
            index = data["index"]
            block = self._current_blocks.get(index)

            if block and block.type == "tool_use":
                try:
                    block.input_parsed = json.loads(block.input_json)
                    block.is_complete = True  # Mark as complete (A.3)
                except json.JSONDecodeError:
                    # A.3: Do NOT create a pseudo-input dict. Mark as incomplete.
                    # Partial tool calls are discarded, not executed.
                    block.input_parsed = None
                    block.is_complete = False
                    block.parse_error = "Failed to parse tool input JSON"

            if block:
                self.state.content_blocks.append(block)

            return None

        elif event_type == "message_delta":
            self.state.stop_reason = data["delta"].get("stop_reason")
            usage = data.get("usage", {})
            self.state.output_tokens = usage.get("output_tokens", 0)
            self.state.cache_read_tokens = usage.get("cache_read_input_tokens", 0)
            self.state.cache_creation_tokens = usage.get("cache_creation_input_tokens", 0)
            return None

        elif event_type == "message_stop":
            if self.state.stop_reason == "tool_use":
                return "tool_calls_ready"
            else:
                return "message_complete"

        return None

    def get_state(self) -> StreamState:
        return self.state

    def get_usage(self) -> TokenUsage:
        return TokenUsage(
            input_tokens=self.state.input_tokens,
            output_tokens=self.state.output_tokens,
            cache_read_tokens=self.state.cache_read_tokens,
            cache_creation_tokens=self.state.cache_creation_tokens,
        )

    def reset(self):
        self.state = StreamState()
        self._current_blocks = {}
```

### Generic Harness Runner (Base Layer)

The base harness runner provides the agent loop mechanics without any specific tool philosophy:

```python
# base_harness/runner.py
# GENERIC - Base class for building base harnesses

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Any

@dataclass
class TurnResult:
    """Result from one LLM turn."""
    content_blocks: List[ContentBlock]
    tool_calls: List[ContentBlock]
    usage: TokenUsage
    stop_reason: Optional[str]

@dataclass
class HarnessResult:
    """Final result from harness execution."""
    messages: List[dict]
    turn_count: int
    total_usage: TokenUsage
    final_response: str


class ToolExecutor(Protocol):
    """Protocol for tool execution - implement this for your system."""

    async def execute(self, tool_id: str, params: dict) -> Any:
        """Execute a tool and return result."""
        ...


class BaseHarnessRunner(ABC):
    """
    Base base harness runner.

    GENERIC: Provides the agent loop mechanics.
    Subclass this to add your specific tool set and philosophy.
    """

    def __init__(self, tool_executor: ToolExecutor):
        self.executor = tool_executor
        self.messages: List[dict] = []
        self.turn_count = 0
        self.total_usage = TokenUsage()

    async def run(
        self,
        system_prompt: str,
        initial_message: str,
        **kwargs
    ) -> HarnessResult:
        """Run the agent loop."""

        # Initialize messages
        self.messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": initial_message},
        ]

        # The agent loop
        while not self._should_terminate():
            self.turn_count += 1

            # Call LLM (subclass provides the tools)
            turn_result = await self._execute_turn()

            # Track usage
            self._add_usage(turn_result.usage)

            # Add assistant response
            self.messages.append({
                "role": "assistant",
                "content": self._format_assistant_content(turn_result.content_blocks)
            })

            if turn_result.tool_calls:
                # Execute tool calls (subclass handles this)
                tool_results = await self._execute_tool_calls(turn_result.tool_calls)

                self.messages.append({
                    "role": "user",
                    "content": tool_results
                })
            else:
                break  # No tool calls = done

        return HarnessResult(
            messages=self.messages,
            turn_count=self.turn_count,
            total_usage=self.total_usage,
            final_response=self._get_final_response(),
        )

    @abstractmethod
    def _get_tools(self) -> List[dict]:
        """Return tool schemas for LLM. Override in subclass."""
        pass

    @abstractmethod
    async def _execute_tool_calls(self, tool_calls: List[ContentBlock]) -> list:
        """Execute tool calls. Override in subclass to add your logic."""
        pass

    @abstractmethod
    def _should_terminate(self) -> bool:
        """Check if agent should stop. Override for custom termination."""
        pass

    async def _execute_turn(self) -> TurnResult:
        """Execute one LLM turn with streaming."""
        tools = self._get_tools()

        # Call LLM (implementation depends on provider)
        stream_result = await self._call_llm(self.messages, tools)

        # Parse stream
        parser = StreamParser()
        for event in stream_result.get("events", []):
            parser.process_event(event["type"], event["data"])

        state = parser.get_state()

        return TurnResult(
            content_blocks=state.content_blocks,
            tool_calls=state.get_tool_calls(),
            usage=parser.get_usage(),
            stop_reason=state.stop_reason,
        )

    @abstractmethod
    async def _call_llm(self, messages: list, tools: list) -> dict:
        """Call the LLM. Override to use your preferred method."""
        pass

    def _add_usage(self, usage: TokenUsage):
        self.total_usage.input_tokens += usage.input_tokens
        self.total_usage.output_tokens += usage.output_tokens
        self.total_usage.cache_read_tokens += usage.cache_read_tokens
        self.total_usage.cache_creation_tokens += usage.cache_creation_tokens

    def _format_assistant_content(self, blocks: List[ContentBlock]) -> list:
        """Format content blocks for message history."""
        return [
            {"type": b.type, "text": b.text} if b.type == "text"
            else {"type": "tool_use", "id": b.tool_id, "name": b.tool_name, "input": b.input_parsed}
            for b in blocks
        ]

    def _get_final_response(self) -> str:
        """Extract final text response."""
        for msg in reversed(self.messages):
            if msg["role"] == "assistant":
                content = msg.get("content", [])
                if isinstance(content, str):
                    return content
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        return block.get("text", "")
        return ""
```

### Safety Harness Runner (Our Implementation)

The Safety harness extends the generic base with our "everything → something" philosophy.

**See Layer 4 above for the canonical `SafetyHarnessRunner` implementation**, which includes:

- Full `run_directive()` method with cost and context tracking
- All abstract method implementations (`_get_tools`, `_execute_tool_calls`, `_should_terminate`, `_call_llm`)
- Helper methods for AGENTS.md loading, thread ID generation, and capability token minting

The key differences from `BaseHarnessRunner`:

| Method                  | Base Harness | Safety Harness                      |
| ----------------------- | ------------ | --------------------------------- |
| `_get_tools()`          | Abstract     | Returns 4 Kiwi meta-tools         |
| `_execute_tool_calls()` | Abstract     | Adds `__auth` capability token    |
| `_should_terminate()`   | Abstract     | Checks cost + context budgets     |
| `_call_llm()`           | Abstract     | Uses `anthropic_thread` tool      |
| Entry point             | `run()`      | `run_directive()` (wraps `run()`) |

### Package Structure Summary

Both harness packages live in the **kiwi-mcp repository** and are bootstrapped to userspace during `init`. See `INIT_PROCESS_DESIGN.md` for the full init flow.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PACKAGE STRUCTURE                                    │
│                                                                              │
│  In kiwi-mcp repo (source of truth):                                         │
│  ────────────────────────────────────                                        │
│                                                                              │
│  base_harness/                  # GENERIC - Anyone can use this            │
│  ├── __init__.py                                                            │
│  ├── stream_parser.py            # SSE parsing, tool call accumulation      │
│  │   ├── ContentBlock            # Single content block from stream         │
│  │   ├── StreamState             # Accumulated state from stream            │
│  │   ├── TokenUsage              # Token usage tracking                     │
│  │   └── StreamParser            # Parses SSE events into structured data   │
│  │                                                                          │
│  └── runner.py                   # Base agent loop mechanics                │
│      ├── TurnResult              # Result from one LLM turn                 │
│      ├── HarnessResult           # Final result from harness execution      │
│      ├── ToolExecutor            # Protocol for tool execution              │
│      └── BaseHarnessRunner       # Abstract base class for harnesses        │
│          ├── run()               # Main entry point                         │
│          ├── _get_tools()        # Abstract: return tool schemas            │
│          ├── _execute_tool_calls()  # Abstract: execute tools              │
│          ├── _should_terminate() # Abstract: termination check              │
│          └── _call_llm()         # Abstract: call LLM provider              │
│                                                                              │
│  safety_harness/                   # SAFETY - Adds guardrails and enforcement │
│  ├── __init__.py                                                            │
│  ├── runner.py                   # SafetyHarnessRunner (extends base)         │
│  │   └── SafetyHarnessRunner                                                  │
│  │       ├── run_directive()     # Safety harness entry point (loads directive) │
│  │       ├── _get_tools()        # Returns 4 Kiwi meta-tools (via base)    │
│  │       ├── _execute_tool_calls()  # Permission-checked execution         │
│  │       ├── _should_terminate() # Checks cost budget                       │
│  │       └── _call_llm()         # Uses anthropic_thread tool              │
│  │                                                                          │
│  ├── context.py                  # ThreadContext                            │
│  ├── capabilities.py             # Token minting, permissions_to_caps (A.2) │
│  └── cost.py                     # CostBudget, CostTracker                  │
│                                                                              │
│  After init (bootstrapped to ~/.ai/):                                        │
│  ─────────────────────────────────────                                       │
│                                                                              │
│  ~/.ai/                                                                      │
│  ├── harness/                    # Harness packages installed here          │
│  │   ├── base_harness/          # Generic base harness                     │
│  │   └── safety_harness/           # Safety harness (adds guardrails)         │
│  ├── tools/                      # Core tools (sinks, threads, etc.)        │
│  ├── directives/                 # User-level directives                    │
│  └── ...                                                                     │
│                                                                              │
│  # Others could build their own harnesses:                                  │
│  my_custom_harness/              # CUSTOM - Your implementation             │
│  └── runner.py                                                              │
│      └── MyHarnessRunner(BaseHarnessRunner)                                │
│          ├── _get_tools()        # Your custom tool set                    │
│          └── ...                 # Your philosophy                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Directive Context Extraction (Safety-Specific)

The Safety harness maintains a `ThreadContext` that holds the directive being executed. This is critical for:

1. **Capability tokens (A.2)** - Minted from directive's `<permissions>`, attached to all tool calls
2. **Cost tracking (A.4)** - Token usage is tracked against the directive's cost budget (REQUIRED)
3. **Loop detection** - Repeated calls are analyzed in context
4. **Annealing** - Failures are attributed to the specific directive

```python
# safety_harness/context.py

@dataclass
class ThreadContext:
    """Execution context maintained throughout thread lifetime."""

    thread_id: str  # Auto-generated (A.1)
    directive_name: str
    capability_token: str  # A.2: Signed JWT/PASETO with granted capabilities
    cost_budget: CostBudget  # A.4: REQUIRED - no defaults

    # Accumulated state
    turn_count: int = 0
    total_usage: TokenUsage = field(default_factory=TokenUsage)
    tool_call_history: List[ToolCallRecord] = field(default_factory=list)

    def add_usage(self, usage: TokenUsage) -> None:
        """Add usage from a turn to totals."""
        self.total_usage.input_tokens += usage.input_tokens
        self.total_usage.output_tokens += usage.output_tokens
        self.total_usage.cache_read_tokens += usage.cache_read_tokens
        self.total_usage.cache_creation_tokens += usage.cache_creation_tokens

    def record_tool_call(self, tool_call: ContentBlock) -> Optional[LoopSignal]:
        """Record tool call and check for loop patterns."""
        record = ToolCallRecord(
            tool_name=tool_call.tool_name,
            input_hash=self._hash_input(tool_call.input_parsed),
            timestamp=time.time(),
        )
        self.tool_call_history.append(record)

        # Check for loops (last N calls identical)
        return self._detect_loop_pattern()

    def _detect_loop_pattern(self, window: int = 5, threshold: int = 3) -> Optional[LoopSignal]:
        """Detect if agent is stuck in a loop."""
        if len(self.tool_call_history) < threshold:
            return None

        recent = self.tool_call_history[-window:]
        hashes = [r.input_hash for r in recent]

        # Check for exact repetition
        last_hash = hashes[-1]
        repeat_count = sum(1 for h in hashes if h == last_hash)

        if repeat_count >= threshold:
            return LoopSignal(
                pattern="exact_repeat",
                count=repeat_count,
                tool_name=recent[-1].tool_name,
            )

        return None
```

### Cost Tracking in Directive Metadata (REQUIRED)

**Cost tracking is mandatory.** All directives MUST include a `<cost>` section. This follows the same validation pattern as `<permissions>`, `<model>`, and `version` - required metadata with no defaults.

**Two Independent Budget Systems:**

1. **Cost Budget** - Tracks cumulative resource usage across ALL turns:
   - Total input tokens consumed
   - Total output tokens generated
   - Total dollar cost
   - Number of turns/calls made
2. **Context Budget** - Tracks current turn's input tokens to prevent exceeding model context window:
   - Input tokens in THIS turn only
   - Warning threshold (e.g., 80% of model's context limit)
   - Hard limit (model's max context window)

These are **separate concerns** with different termination semantics:

- **Cost budget exceeded:** Depends on `on_exceeded` setting (stop/warn/escalate)
- **Context budget exceeded:** Always terminates (cannot continue with full context)

See **Appendix A.4** for validation details and error message patterns.

```xml
<directive name="deploy_staging" version="1.0.0">
  <metadata>
    <description>Deploy to staging environment</description>
    <category>ops</category>

    <!-- Cost and context budget for this directive (REQUIRED) -->
    <cost>
      <!-- Token limits (per execution) -->
      <max_input_tokens>100000</max_input_tokens>
      <max_output_tokens>50000</max_output_tokens>
      <max_total_tokens>150000</max_total_tokens>

      <!-- Context window limit (prevents exceeding model context) -->
      <max_context_tokens>180000</max_context_tokens>  <!-- Default: model's max -->
      <context_warning_threshold>0.8</context_warning_threshold>  <!-- Warn at 80% -->

      <!-- Dollar budget (per execution) -->
      <max_cost_usd>5.00</max_cost_usd>

      <!-- Turn limits (REQUIRED) -->
      <max_turns>30</max_turns>

      <!-- On budget exceeded (REQUIRED: "stop" | "warn" | "escalate") -->
      <on_exceeded>escalate</on_exceeded>
    </cost>

    <permissions>
      <!-- ... -->
    </permissions>
  </metadata>
</directive>
```

### Cost Budget Implementation (Safety-Specific)

```python
# safety_harness/cost.py
# SAFETY-SPECIFIC - Cost tracking for directive budgets

from dataclasses import dataclass
from typing import Optional

# Pricing per model (per 1M tokens) - configurable
PRICING = {
    "claude-sonnet-4-20250514": {
        "input": 3.00,
        "output": 15.00,
        "cache_read": 0.30,
        "cache_creation": 3.75,
    },
    "claude-opus-4-20250514": {
        "input": 15.00,
        "output": 75.00,
        "cache_read": 1.50,
        "cache_creation": 18.75,
    },
}

@dataclass
class TokenUsage:
    """Token usage from LLM calls."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0

    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def cost_usd(self, model: str) -> float:
        """Calculate cost in USD."""
        prices = PRICING.get(model, PRICING["claude-sonnet-4-20250514"])

        cost = 0.0
        cost += (self.input_tokens / 1_000_000) * prices["input"]
        cost += (self.output_tokens / 1_000_000) * prices["output"]
        cost += (self.cache_read_tokens / 1_000_000) * prices["cache_read"]
        cost += (self.cache_creation_tokens / 1_000_000) * prices["cache_creation"]

        return cost


@dataclass
class CostBudget:
    """Cost budget from directive metadata.

    REQUIRED: All directives must have <cost> with at least max_turns and on_exceeded.
    Validation happens at directive load time (see DirectiveValidator).
    """
    max_input_tokens: Optional[int]
    max_output_tokens: Optional[int]
    max_total_tokens: Optional[int]
    max_cost_usd: Optional[float]
    max_turns: int  # REQUIRED - no default
    on_exceeded: str  # REQUIRED - must be "stop", "warn", or "escalate"

    @classmethod
    def from_directive(cls, cost_data: dict) -> "CostBudget":
        """Parse cost budget from directive metadata.

        NOTE: Validation already happened at load time. Missing cost_data
        would have failed validation, so we can assume required fields exist.
        """
        if not cost_data:
            raise ValueError(
                "No <cost> tag found in directive metadata. "
                "Add a <cost> tag with at least max_turns and on_exceeded."
            )
        if "max_turns" not in cost_data:
            raise ValueError("cost.max_turns is required")
        if cost_data.get("on_exceeded") not in ["stop", "warn", "escalate"]:
            raise ValueError("cost.on_exceeded must be 'stop', 'warn', or 'escalate'")

        return cls(
            max_input_tokens=cost_data.get("max_input_tokens"),
            max_output_tokens=cost_data.get("max_output_tokens"),
            max_total_tokens=cost_data.get("max_total_tokens"),
            max_cost_usd=cost_data.get("max_cost_usd"),
            max_turns=cost_data["max_turns"],  # Required
            on_exceeded=cost_data["on_exceeded"],  # Required
        )

    def exceeded(self, usage: TokenUsage, model: str = "claude-sonnet-4-20250514", turns: int = 0) -> Optional[str]:
        """Check if budget is exceeded. Returns reason or None."""

        if self.max_input_tokens and usage.input_tokens > self.max_input_tokens:
            return f"Input token limit exceeded: {usage.input_tokens} > {self.max_input_tokens}"

        if self.max_output_tokens and usage.output_tokens > self.max_output_tokens:
            return f"Output token limit exceeded: {usage.output_tokens} > {self.max_output_tokens}"

        if self.max_total_tokens and usage.total_tokens() > self.max_total_tokens:
            return f"Total token limit exceeded: {usage.total_tokens()} > {self.max_total_tokens}"

        if self.max_cost_usd:
            current_cost = usage.cost_usd(model)
            if current_cost > self.max_cost_usd:
                return f"Cost limit exceeded: ${current_cost:.4f} > ${self.max_cost_usd}"

        if self.max_turns and turns > self.max_turns:
            return f"Turn limit exceeded: {turns} > {self.max_turns}"

        return None


class CostTracker:
    """Track costs across thread lifetime."""

    def __init__(self, budget: CostBudget, model: str):
        self.budget = budget
        self.model = model
        self.usage = TokenUsage()
        self.turns = 0
        self.per_turn_usage: List[TokenUsage] = []

    def add_turn(self, usage: TokenUsage) -> Optional[str]:
        """
        Add usage from a turn and check budget.
        Returns budget exceeded reason or None.
        """
        self.usage.input_tokens += usage.input_tokens
        self.usage.output_tokens += usage.output_tokens
        self.usage.cache_read_tokens += usage.cache_read_tokens
        self.usage.cache_creation_tokens += usage.cache_creation_tokens
        self.turns += 1
        self.per_turn_usage.append(usage)

        return self.budget.exceeded(self.usage, self.model, self.turns)

    def get_summary(self) -> dict:
        """Get cost summary for logging/reporting."""
        return {
            "turns": self.turns,
            "input_tokens": self.usage.input_tokens,
            "output_tokens": self.usage.output_tokens,
            "total_tokens": self.usage.total_tokens(),
            "cache_read_tokens": self.usage.cache_read_tokens,
            "cache_creation_tokens": self.usage.cache_creation_tokens,
            "cost_usd": self.usage.cost_usd(self.model),
            "model": self.model,
            "budget_remaining_usd": (
                self.budget.max_cost_usd - self.usage.cost_usd(self.model)
                if self.budget.max_cost_usd else None
            ),
        }
```

### The Complete Data Flow (Safety Harness)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Kiwi Thread Execution with Cost Tracking                  │
│                                                                              │
│  1. Harness spawns, loads directive                                          │
│     ├── Auto-generate thread_id (A.1)                                       │
│     ├── Mint capability token from <permissions> (A.2)                      │
│     ├── Extract CostBudget from <cost> (REQUIRED - A.4)                     │
│     └── Create ThreadContext with token + budget                            │
│                                                                              │
│  2. Each turn:                                                               │
│     ├── Call LLM via streaming http_client                                  │
│     ├── StreamParser accumulates SSE events                                  │
│     │   ├── content_block_delta → accumulate partial JSON                   │
│     │   ├── content_block_stop → parse, mark complete/partial (A.3)         │
│     │   └── message_delta → capture token usage                             │
│     │                                                                        │
│     ├── On message_stop:                                                    │
│     │   ├── CostTracker.add_turn(usage) → check budget                      │
│     │   ├── If budget exceeded → handle per on_exceeded                     │
│     │   │   ├── "stop" → return immediately                                 │
│     │   │   ├── "warn" → log warning, continue                              │
│     │   │   └── "escalate" → help(action="escalate", reason="budget")       │
│     │   │                                                                    │
│     │   └── If tool_calls present (complete only - A.3):                    │
│     │       ├── For each tool_call:                                         │
│     │       │   ├── Context.record_tool_call() → check loop                 │
│     │       │   ├── Attach __auth token (A.2) → tool validates              │
│     │       │   └── Execute via Kiwi MCP                                    │
│     │       └── Format results for next turn                                │
│     │                                                                        │
│     └── If no tool_calls → agent done                                       │
│                                                                              │
│  3. On completion:                                                           │
│     ├── Log final CostTracker.get_summary()                                 │
│     ├── Update thread registry via tool (A.5)                               │
│     └── Return ThreadResult                                                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Feeding Results Back to the LLM

After executing tool calls, the harness formats results as `tool_result` content blocks and sends them in the next API call:

```python
def _format_tool_results_for_api(self, results: list) -> list:
    """Format tool results for Anthropic API format."""
    return [
        {
            "type": "tool_result",
            "tool_use_id": r["tool_use_id"],
            "content": r["content"],
            **({"is_error": True} if r.get("is_error") else {})
        }
        for r in results
    ]

# In the next API call:
messages.append({
    "role": "user",  # tool_results go in a user message
    "content": self._format_tool_results_for_api(tool_results)
})
```

### Summary: Stream Processing Pipeline

| Stage           | What Happens                       | Data Captured                 |
| --------------- | ---------------------------------- | ----------------------------- |
| SSE Start       | `message_start`                    | message_id, initial usage     |
| Text Content    | `content_block_delta` (text)       | Accumulated text              |
| Tool Call Start | `content_block_start` (tool_use)   | tool_id, tool_name            |
| Tool Params     | `content_block_delta` (input_json) | Partial JSON accumulated      |
| Tool Complete   | `content_block_stop`               | Parse complete JSON           |
| Message End     | `message_delta`                    | stop_reason, cumulative usage |
| Stream End      | `message_stop`                     | Signal to process tool calls  |

Key insight: **The LLM doesn't wait for us.** It streams its entire response. We parse the stream, accumulate tool calls, and only after `message_stop` do we execute them and send results in the next turn.

---

## Layer 6: Kiwi MCP as the Microkernel

### The Key Insight

**Kiwi MCP IS the agent kernel.** Any LLM loop with Kiwi MCP access is a full agent because:

1. **LLM only sees 4 meta-tools**: `search`, `load`, `execute`, `help`
2. **Directive provides context**: Permissions and contextual instructions
3. **AGENTS.md provides identity**: Universal system prompt
4. **Kernel stays dumb**: Forwards opaque capability tokens (see A.2)
5. **Tool-layer enforcement**: Tools validate `requires` against tokens
6. **On-demand resolution**: LLM searches for what it needs, Kiwi resolves and executes

### Capability Token Model

**Permission enforcement uses capability tokens**, NOT in-kernel permission checking.

See **[PERMISSION_MODEL.md](./PERMISSION_MODEL.md)** for complete token lifecycle and enforcement details.

**Complete documentation includes:**

- Token lifecycle and structure
- Thread-scoped vs nested directive execution
- Path-based permission scoping
- System vs user capabilities
- Project sandboxing
- Extractor modification security

**Quick overview:**

1. **Harness extracts `<permissions>`** from directive → converts to capability list with scopes
2. **Harness mints signed capability token** (JWT/PASETO with caps, scopes, expiry, audience)
3. **All tool calls include token** (via `__auth` metadata)
4. **Kernel forwards opaquely** (does NOT interpret/validate)
5. **Tools validate token** against their `requires:` declaration AND scope patterns

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          LLM (Claude, GPT, etc.)                             │
│                                                                              │
│  Tools available: search | load | execute | help                             │
│  System prompt: AGENTS.md (universal)                                        │
│  Context: From directive being executed                                      │
│  Permissions: Enforced at tool layer via capability tokens                   │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    KIWI MCP (The Microkernel - Stays Dumb)                   │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │  Opaque Metadata Pass-Through                                           │ │
│  │  • __auth: Capability token (kernel does NOT interpret)                 │ │
│  │  • __thread_id: For audit/logging only                                  │ │
│  │  • __directive_id: For annealing feedback                               │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                  │                                           │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                    4 Meta-Tools (LLM's interface)                       │ │
│  │                                                                          │ │
│  │  search   → Find directives, tools, knowledge, MCPs                     │ │
│  │  load     → Get details, copy between locations                         │ │
│  │  execute  → Run tools (forwards token to tool layer)                    │ │
│  │  help     → Guidance, stuck signal, escalate, checkpoint                │ │
│  └────────────────────────────────┬───────────────────────────────────────┘ │
│                                   │                                          │
│  ┌────────────────────────────────▼───────────────────────────────────────┐ │
│  │                    Tool Layer (Enforcement Here)                        │ │
│  │                                                                          │ │
│  │  Each tool declares: requires: [fs.write, net.http]                     │ │
│  │  Tool validates token: are required caps present & valid?               │ │
│  │  ALLOWED → execute | DENIED → error + audit                             │ │
│  └────────────────────────────────┬───────────────────────────────────────┘ │
│                                   │                                          │
│  ┌────────────────────────────────▼───────────────────────────────────────┐ │
│  │                    Capabilities (Data-Driven Tools)                     │ │
│  │                                                                          │ │
│  │  .ai/tools/capabilities/                                                 │ │
│  │  ├── fs.py      # fs.read, fs.write                                     │ │
│  │  ├── net.py     # net.http, net.websocket                               │ │
│  │  ├── db.py      # db.query, db.migrate                                  │ │
│  │  ├── git.py     # git.read, git.push                                    │ │
│  │  ├── process.py # process.spawn                                         │ │
│  │  └── mcp.py     # mcp.connect                                           │ │
│  └────────────────────────────────┬───────────────────────────────────────┘ │
│                                   │                                          │
│  ┌────────────────────────────────▼───────────────────────────────────────┐ │
│  │                    Primitives (only execution code)                     │ │
│  │                                                                          │ │
│  │  subprocess: Commands, scripts, stdio MCPs                              │ │
│  │  http_client: APIs, HTTP MCPs, LLM endpoints, streaming                 │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

### LLM Execution Contexts: Inside vs Outside MCP

Understanding where the LLM runs is critical for permission enforcement:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LLM EXECUTION CONTEXT HIERARCHY                           │
│                                                                              │
│  1. LLM OUTSIDE MCP (Claude Code, Amp, Cursor calling MCP tools)             │
│     ├── LLM runs in frontend's context                                       │
│     ├── Frontend handles its own permissions                                 │
│     ├── Kiwi MCP is just a tool provider                                     │
│     └── NO capability token enforcement possible                             │
│                                                                              │
│  2. LLM INSIDE MCP - Base Harness (custom implementations)                   │
│     ├── LLM runs INSIDE MCP via a harness loop                               │
│     ├── Harness could be permissive (no token minting)                       │
│     ├── Still useful for thread management, cost tracking                    │
│     └── Permission enforcement is OPTIONAL (not recommended)                 │
│                                                                              │
│  3. LLM INSIDE MCP - Safety Harness (our opinionated implementation)           │
│     ├── LLM runs INSIDE MCP via safety_harness                                 │
│     ├── Capability tokens REQUIRED                                           │
│     ├── Tool-layer validation of tokens                                      │
│     ├── Cost tracking, loop detection, intervention                          │
│     └── FULL permission enforcement                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key insight:** Permission enforcement is only possible when the LLM runs **inside** our harness. When frontends like Claude Code call MCP tools directly, the LLM runs outside our control and we cannot enforce capability tokens.

This is not a limitation - it's by design. Frontends have their own permission systems. Our enforcement layer is for **threads spawned and managed by Kiwi itself**.

### Critical: LLM Only Sees 4 Tools

The LLM doesn't get a list of all available tools. It gets **exactly 4 meta-tools**:

```python
# What Kiwi exposes to any connected LLM client
KIWI_TOOLS = [
    {
        "name": "search",
        "description": "Find directives, tools, knowledge, or MCPs"
        "inputSchema": {...}
    },
    {
        "name": "load",
        "description": "Get item details or copy between locations",
        "inputSchema": {...}
    },
    {
        "name": "execute",
        "description": "Run a tool with parameters",
        "inputSchema": {...}
    },
    {
        "name": "help",
        "description": "Get guidance, signal stuck, escalate, or checkpoint",
        "inputSchema": {...}
    }
]
```

The LLM discovers what's available via `search()` and runs things via `execute()`. This means:

- **No schema bloat** - LLM doesn't need 1000 tool schemas in context
- **On-demand** - Tools are resolved when executed
- **Scalable** - Can have unlimited tools/MCPs registered

---

## Layer 7: MCP Architecture (Registry-Based)

### MCPs as Tools from Registry

MCPs are **not** configured in a central `mcps.yaml`. Instead, they are **tools loaded from the remote registry**, just like any other tool.

Each MCP is a single tool that inherits from the appropriate primitive MCP base type (`mcp_stdio` or `mcp_http`).

### MCP Base Tools (Primitives)

```yaml
# .ai/tools/mcp/mcp_stdio.yaml - Base tool for stdio MCPs
tool_id: mcp_stdio
tool_type: primitive_wrapper
version: "1.0.0"
description: "Execute JSON-RPC call over stdio MCP connection"
executor_id: subprocess

config:
  # Subprocess handles the stdio I/O
  input_format: jsonrpc
  output_format: jsonrpc

parameters:
  - name: command
    type: string
    required: true
    description: "Command to spawn MCP server"
  - name: args
    type: array
    required: false
  - name: env
    type: object
    required: false
  - name: method
    type: string
    required: true
    description: "JSON-RPC method (e.g., tools/call)"
  - name: params
    type: object
    required: true
    description: "JSON-RPC params"
```

```yaml
# .ai/tools/mcp/mcp_http.yaml - Base tool for HTTP MCPs
tool_id: mcp_http
tool_type: primitive_wrapper
version: "1.0.0"
description: "Execute JSON-RPC call over HTTP MCP connection"
executor_id: http_client

config:
  method: POST
  headers:
    Content-Type: application/json
  body:
    jsonrpc: "2.0"
    id: "{request_id}"
    method: "{rpc_method}"
    params: "{rpc_params}"

parameters:
  - name: url
    type: string
    required: true
  - name: auth
    type: object
    required: false
  - name: rpc_method
    type: string
    required: true
  - name: rpc_params
    type: object
    required: true
```

### Two-Layer MCP Connector Pattern (See A.6)

External MCPs integrate through a **two-layer tool system**:

1. **Connector tool** - Establishes connection, runs `tools/list`, generates child tool schemas
2. **Generated tool schemas** - One per MCP tool, with proper `requires` capabilities

This matches our capability token model (A.2) - generated tools declare their `requires` and validate tokens.

```
.ai/tools/mcp/
├── supabase_connector.yaml    # Discovery/connection tool
├── supabase_query.yaml        # Generated: individual MCP tool
├── supabase_migrate.yaml      # Generated: individual MCP tool
└── ...
```

### Example: Supabase MCP Connector

```yaml
# .ai/tools/mcp/supabase_connector.yaml - Connector tool
tool_id: supabase_connector
tool_type: mcp_connector
executor_id: python
version: "1.0.0"

config:
  mcp_url: "https://mcp.supabase.com/mcp"
  auth:
    type: bearer
    token: "${SUPABASE_SERVICE_KEY}"
  output_dir: ".ai/tools/mcp/"
  tool_prefix: "supabase_"

requires:
  - mcp.connect # Permission to connect to external MCPs

retry:
  max_attempts: 3
  backoff_ms: [250, 1000, 3000]
```

When run, this connector:

1. Connects to the MCP
2. Calls `tools/list` to discover available tools
3. Generates individual tool YAML files with proper `requires` capabilities
4. Signs the generated tools

### Example: Generated MCP Tool

```yaml
# .ai/tools/mcp/supabase_query.yaml (GENERATED by connector)
tool_id: supabase_query
tool_type: mcp_tool
executor_id: mcp_http
version: "1.0.0"

config:
  mcp_url: "https://mcp.supabase.com/mcp"
  mcp_tool: "query" # The actual MCP tool name

requires:
  - db.query # Capability required to use this tool
  - mcp.supabase # Specific MCP capability

input_schema:
  # ... copied from MCP's tools/list response
```

### Workflow: Adding an MCP

1. LLM needs Supabase access
2. `search(item_type="tool", query="supabase connector", source="registry")`
3. `load(item_type="tool", item_id="supabase_connector", source="registry", destination="project")`
4. `execute(item_type="tool", action="run", item_id="supabase_connector")`
   - Connector runs, discovers tools, generates per-tool YAML files
5. `execute(item_type="tool", action="run", item_id="supabase_query", parameters={...})`
   - Calls the generated tool directly (no special prefix parsing)
   - Tool validates capability token against its `requires`

**No on-demand discovery.** Connector runs explicitly, generates static tool schemas. MCPs are just tools.

---

## Layer 8: Directive-Driven Execution

### How It Comes Together

The directive provides **context and permissions**, NOT system prompt:

```xml
<directive name="deploy_staging" version="1.0.0">
  <metadata>
    <description>Deploy application to staging environment</description>
    <category>ops</category>
    <author>kiwi-mcp</author>
    <model tier="balanced" fallback="reasoning" parallel="false">
      Infrastructure deployment with verification steps.
    </model>

    <!-- REQUIRED: Cost tracking (see A.4) -->
    <cost>
      <max_input_tokens>100000</max_input_tokens>
      <max_output_tokens>50000</max_output_tokens>
      <max_turns>30</max_turns>
      <on_exceeded>escalate</on_exceeded>
    </cost>

    <permissions>
      <!-- Filesystem capabilities -->
      <read resource="filesystem" path="**/*" />
      <write resource="filesystem" path="deploy/**" />

      <!-- Local tools -->
      <execute resource="tool" id="bash" />
      <execute resource="tool" id="docker" />

      <!-- MCPs (using generated tool IDs, not mcp.* prefixes) -->
      <execute resource="tool" id="supabase_query" />
      <execute resource="tool" id="supabase_migrate" />
      <execute resource="tool" id="github_*" />

      <!-- Meta-tools (usually always allowed) -->
      <execute resource="kiwi-mcp" action="search" />
      <execute resource="kiwi-mcp" action="load" />
      <execute resource="kiwi-mcp" action="execute" />
      <execute resource="kiwi-mcp" action="help" />

      <!-- Orchestration: this directive can spawn sub-threads (A.2) -->
      <orchestration enabled="true">
        <allow_categories>verify,test,deploy</allow_categories>
        <allow_directives>verify_*,health_check_*</allow_directives>
        <deny_directives>delete_*,drop_*</deny_directives>
      </orchestration>
    </permissions>

    <deviation_rules auto_fix="false" ask_first="true" escalate="true">
      On uncertainty, use help(action="escalate")
      On repeated failures, use help(action="stuck")
      Before destructive actions, use help(action="checkpoint")
    </deviation_rules>
  </metadata>

  <context>
    <tech_stack>docker, kubernetes</tech_stack>
  </context>

  <inputs>
    <input name="version" type="string" required="true">
      Version tag to deploy (e.g., "v1.2.3")
    </input>
    <input name="environment" type="string" default="staging">
      Target environment
    </input>
  </inputs>

  <process>
    <step name="verify_version">
      <description>Verify version exists and is ready</description>
      <action>Check that the version tag exists in the registry</action>
    </step>

    <step name="run_migrations">
      <description>Run database migrations</description>
      <action>Execute pending migrations via Supabase MCP</action>
    </step>

    <step name="deploy">
      <description>Deploy to staging</description>
      <action>Run deployment scripts</action>
    </step>

    <step name="verify">
      <description>Verify deployment</description>
      <action>Run health checks and smoke tests</action>
    </step>
  </process>

  <success_criteria>
    <criterion>Application responds to health check</criterion>
    <criterion>All migrations applied successfully</criterion>
  </success_criteria>

  <outputs>
    <success>Deployed {version} to {environment} successfully</success>
  </outputs>
</directive>
```

### Key Points

1. **No system prompt in directive** - System prompt is always `AGENTS.md`
2. **Directive provides context** - Description, steps, success criteria
3. **Permissions are in directive** - Enforced by Kiwi, not LLM knowledge
4. **LLM follows directive steps** - Using 4 meta-tools to accomplish each step

---

## Layer 8.5: Thread Monitoring & Async Spawn Pattern

### Spawn Returns Immediately

When a thread is spawned, the `spawn_thread` tool returns immediately with a thread_id. The actual thread execution happens asynchronously in the background:

```python
# spawn_thread tool implementation
async def spawn_thread_base(
    thread_id: str,
    directive_name: str,
    initial_message: str,
    project_path: Optional[str] = None
) -> dict:
    """Spawn a new managed thread (base implementation).

    Returns immediately with thread_id. Thread runs in background.
    """

    # 1. Validate thread_id doesn't exist
    existing = await thread_registry.get(thread_id)
    if existing:
        return {
            "success": False,
            "error": "Thread ID already exists",
            "code": "THREAD_ID_COLLISION",
            "thread_id": thread_id
        }

    # 2. Register thread immediately (status: spawning)
    registry_id = await thread_registry.register({
        "thread_id": thread_id,
        "directive_name": directive_name,
        "status": "spawning",
        "created_at": datetime.now().isoformat(),
        "project_path": project_path
    })

    # 3. Start thread in background (asyncio.create_task or subprocess)
    asyncio.create_task(
        _run_thread_async(thread_id, directive_name, initial_message, project_path)
    )

    # 4. Return immediately to caller
    return {
        "success": True,
        "thread_id": thread_id,
        "status": "spawned",
        "transcript_path": f".ai/threads/{thread_id}/transcript.jsonl",
        "registry_id": registry_id,
        "started_at": datetime.now().isoformat(),
        "message": "Thread spawned successfully. Monitor via thread_registry or transcript."
    }


async def _run_thread_async(
    thread_id: str,
    directive_name: str,
    initial_message: str,
    project_path: Optional[str]
):
    """Background task that runs the actual thread."""
    try:
        # Update status to running
        await thread_registry.update_status(thread_id, "running")

        # Instantiate and run harness
        harness = SafetyHarnessRunner(
            mcp_executor=get_mcp_client(),
            project_path=project_path
        )

        result = await harness.run_directive(
            directive_name=directive_name,
            initial_message=initial_message
        )

        # Update status to completed
        await thread_registry.update_status(thread_id, "completed", {
            "usage": result.total_usage.__dict__,
            "turn_count": result.turn_count
        })

    except Exception as e:
        # Update status to error
        await thread_registry.update_status(thread_id, "error", {
            "error": str(e),
            "traceback": traceback.format_exc()
        })
```

### Thread Monitoring Patterns

Once a thread is spawned, there are multiple ways to monitor its progress:

#### 1. Thread Registry Queries

The `thread_registry` tool provides query operations:

```python
# Get current thread status
status = await thread_registry.get_status(thread_id)
# Returns: {"thread_id": "...", "status": "running", "turn_count": 5, ...}

# Get recent threads by directive
threads = await thread_registry.query({
    "directive_name": "deploy_staging",
    "limit": 10,
    "order_by": "created_at DESC"
})

# Get thread events (tool calls, errors, warnings)
events = await thread_registry.get_events(thread_id, limit=50)
```

**Tool Configuration:**

```yaml
# .ai/tools/threads/thread_registry.yaml
tool_id: thread_registry
tool_type: runtime
executor_id: python
version: "1.0.0"
description: "Query and manage thread registry (privileged harness tool)"

# Note: This is a privileged tool - only harness can call it
# Directives cannot call it directly (would violate permissions)

config:
  db_path: ".ai/threads/registry.db"

actions:
  - name: get_status
    description: "Get current status of a thread"
    parameters:
      - name: thread_id
        type: string
        required: true

  - name: query
    description: "Query threads by criteria"
    parameters:
      - name: directive_name
        type: string
        required: false
      - name: status
        type: string
        required: false
      - name: limit
        type: integer
        default: 10

  - name: get_events
    description: "Get thread events (tool calls, errors, etc.)"
    parameters:
      - name: thread_id
        type: string
        required: true
      - name: limit
        type: integer
        default: 50
```

#### 2. Transcript File Reading

Threads write to `.ai/threads/{thread_id}/transcript.jsonl` in real-time. You can read this file while the thread is running:

```python
# Read transcript while thread is running
import json
from pathlib import Path

def read_transcript(thread_id: str):
    """Read thread transcript (works while thread is running)."""
    transcript_path = Path(f".ai/threads/{thread_id}/transcript.jsonl")

    if not transcript_path.exists():
        return []

    events = []
    with open(transcript_path, "r") as f:
        for line in f:
            events.append(json.loads(line))

    return events

# Get latest events
transcript = read_transcript("deploy_staging_20260125_103045")
latest_turn = max(e["turn"] for e in transcript if "turn" in e)
print(f"Thread is on turn {latest_turn}")
```

Example transcript format:

```jsonl
{"ts":"2026-01-25T10:00:00Z","type":"turn_start","turn":1}
{"ts":"2026-01-25T10:00:01Z","type":"user_message","content":"Deploy v1.2.3 to staging"}
{"ts":"2026-01-25T10:00:05Z","type":"assistant_message","content":"I'll check the version first..."}
{"ts":"2026-01-25T10:00:05Z","type":"tool_call","tool":"execute","args_hash":"abc123"}
{"ts":"2026-01-25T10:00:07Z","type":"tool_result","tool":"execute","success":true}
{"ts":"2026-01-25T10:00:10Z","type":"cost_update","input_tokens":1234,"output_tokens":567}
{"ts":"2026-01-25T10:00:15Z","type":"turn_end","turn":1}
```

#### 3. WebSocket Monitoring (Live Stream)

For real-time monitoring, use `websocket_sink` (see Appendix A.7):

```python
# Parent thread or CLI tool can subscribe to a spawned thread's stream
import asyncio
import websockets

async def monitor_thread(thread_id: str, ws_url: str):
    """Monitor a running thread via WebSocket."""
    async with websockets.connect(ws_url) as ws:
        # Subscribe to thread events
        await ws.send(json.dumps({
            "action": "subscribe",
            "thread_id": thread_id
        }))

        # Receive events in real-time
        async for message in ws:
            event = json.loads(message)

            if event["type"] == "tool_call":
                print(f"Thread calling: {event['tool']} with {event['args_hash']}")

            elif event["type"] == "cost_update":
                print(f"Cost: {event['input_tokens']} in, {event['output_tokens']} out")

            elif event["type"] == "error":
                print(f"ERROR: {event['error']}")
                break

            elif event["type"] == "completed":
                print(f"Thread completed in {event['turn_count']} turns")
                break

# Run monitor
asyncio.run(monitor_thread("deploy_staging_20260125_103045", "ws://localhost:8765"))
```

To enable WebSocket monitoring, configure the thread tool with `websocket_sink`:

```yaml
# .ai/tools/threads/anthropic_thread.yaml (with monitoring)
config:
  stream:
    destinations:
      - type: file_sink
        path: ".ai/threads/{thread_id}/transcript.jsonl"
      - type: websocket_sink
        url: "ws://localhost:8765/{thread_id}" # WebSocket server
      - type: return # Still buffer for harness
```

#### 4. Intervention Signals

Threads can be paused, resumed, or terminated using the thread_registry tool:

```python
# Pause a running thread
await thread_registry.update_status(thread_id, "paused")

# Resume a paused thread
await thread_registry.update_status(thread_id, "running")

# Request termination (graceful)
await thread_registry.update_status(thread_id, "terminating")

# Force kill (emergency only)
await thread_registry.update_status(thread_id, "killed")
```

The harness checks for intervention signals at each turn:

```python
# In SafetyHarnessRunner._should_terminate()
def _should_terminate(self) -> bool:
    """Check if agent should stop (cost + context + intervention)."""

    # Check for intervention signal
    status = await self.thread_registry.get_status(self.thread_id)
    if status["status"] in ["terminating", "paused", "killed"]:
        self._termination_reason = f"intervention: {status['status']}"
        return True

    # ... existing cost/context checks ...
```

### Complete Monitoring Example

Here's how a parent thread or CLI tool can spawn and monitor a child thread:

```python
async def spawn_and_monitor(directive_name: str, message: str):
    """Spawn a thread and monitor until completion."""

    # 1. Spawn thread (returns immediately)
    result = await mcp.execute(
        item_type="tool",
        action="run",
        item_id="thread_directive",
        parameters={
            "directive_name": directive_name,
            "initial_message": message
        }
    )

    thread_id = result["thread_id"]
    print(f"Spawned thread: {thread_id}")

    # 2. Monitor via registry polling
    while True:
        await asyncio.sleep(2)  # Poll every 2 seconds

        status = await mcp.execute(
            item_type="tool",
            action="run",
            item_id="thread_registry",
            parameters={
                "action": "get_status",
                "thread_id": thread_id
            }
        )

        print(f"Status: {status['status']}, Turn: {status.get('turn_count', 0)}")

        if status["status"] in ["completed", "error", "terminated"]:
            break

    # 3. Get final result
    transcript = read_transcript(thread_id)
    print(f"Thread completed with {len(transcript)} events")

    return status

# Usage
await spawn_and_monitor("deploy_staging", "Deploy v1.2.3 to staging")
```

---

## Layer 9: Help Tool & Thread Intervention

### The Help Tool's Dual Role

The `help` tool serves two critical functions:

1. **Guidance** - How does this MCP kernel work? What can I do?
2. **Signaling** - I'm stuck, need escalation, or want a checkpoint

This makes `help` the **control channel** for thread coordination and human-in-the-loop patterns.

### Help Actions

```python
help(action="guidance", topic="...")   # How do I use X?
help(action="stuck", reason="...")     # I'm stuck, need intervention
help(action="escalate", reason="...")  # I need a human decision
help(action="checkpoint", reason="...") # Save state before risky action
```

### Future: RAG-Based Help

The `help` tool will eventually use RAG for knowledge about how the system works:

- Query local vector store (user/project separated)
- Vector store populated from registry knowledge entries
- Scales better than keyword queries
- Works locally, no network required for guidance

See: `KNOWLEDGE_SYSTEM_DESIGN.md` (separate document)

### Why Streaming Matters for Intervention

When Thread A is stuck or looping, we need Thread B (or a human) to intervene. This requires:

1. **Thread A's stream is visible** - Another thread can see what A is doing
2. **Thread B can interrupt** - Send a message into A's context
3. **Deterministic control** - Not relying on LLM to "notice" it should stop

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Thread A (stuck in loop)                                                    │
│                                                                              │
│  1. LLM generates: "Let me try X again..."                                   │
│  2. execute(tool="some_tool") → fails                                        │
│  3. Loop detector triggers after 3 identical calls                           │
│  4. Kiwi injects: help(action="stuck") signal                               │
│  5. Signal routes to intervention handler                                    │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Intervention Handler                                                        │
│                                                                              │
│  Options:                                                                    │
│  1. Spawn Thread B to analyze and provide guidance                          │
│  2. Queue for human review                                                   │
│  3. Trigger annealing (auto-improve directive)                              │
│  4. Inject context into Thread A's message stream                           │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
              ┌─────────────────────┴─────────────────────┐
              ▼                                           ▼
┌─────────────────────────────────┐    ┌─────────────────────────────────────────┐
│  Thread B (analyzer)            │    │  Human Approval Queue                    │
│                                 │    │                                          │
│  Has access to:                 │    │  • Notification (webhook, CLI)           │
│  • Thread A's transcript        │    │  • Approval/Reject interface             │
│  • Same Kiwi MCP                │    │  • Inject response into Thread A         │
│  • Can write to Thread A        │    │                                          │
└─────────────────────────────────┘    └─────────────────────────────────────────┘
```

### Thread Intervention Tools

For Thread B to intervene on Thread A, we need:

1. **Thread Registry** - Track all active threads by thread_id
2. **Transcript Access** - Thread B can read Thread A's history
3. **Message Injection** - Thread B can write into Thread A's stream
4. **Deterministic Pause** - Thread A pauses until intervention resolves

```yaml
# Thread control tools
tool_id: thread.read_transcript
description: "Read another thread's conversation history"
parameters:
  - name: thread_id
    type: string
    required: true
  - name: last_n
    type: integer
    default: 10

tool_id: thread.inject_message
description: "Inject a message into another thread's context"
parameters:
  - name: thread_id
    type: string
    required: true
  - name: role
    type: string
    enum: ["system", "user"]
  - name: content
    type: string
    required: true

tool_id: thread.pause
description: "Pause a thread until resumed"
parameters:
  - name: thread_id
    type: string
    required: true
  - name: reason
    type: string

tool_id: thread.resume
description: "Resume a paused thread"
parameters:
  - name: thread_id
    type: string
    required: true
  - name: inject_message
    type: string
    description: "Optional message to inject on resume"
```

### Integration with Annealing

When a directive fails, the annealing system:

1. **Detects failure** - From execution result or stuck signal
2. **Analyzes** - Thread B reviews Thread A's transcript + audit log
3. **Proposes fix** - Modify the directive (permissions, process steps, etc.)
4. **Retries** - Thread A resumes with improved directive

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Annealing Flow                                                              │
│                                                                              │
│  1. Thread A fails executing directive "deploy_staging"                      │
│  2. Failure logged: "Permission denied: write to /etc/nginx"                │
│  3. Annealing thread spawns (privileged, can edit directives)               │
│  4. Analyzes: Directive missing write permission for /etc/                  │
│  5. Proposes: Add <write resource="filesystem" path="/etc/nginx/**" />      │
│  6. Human approval (if required) or auto-apply (if allowed)                 │
│  7. Retry deployment with fixed directive                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Summary Timeline

| Phase | Focus                         | Days | Dependencies |
| ----- | ----------------------------- | ---- | ------------ |
| 8.1   | http_client streaming + sinks | 3-4  | None         |
| 8.2   | LLM endpoint tools            | 1-2  | 8.1          |
| 8.3   | JSON-RPC protocol handling    | 2    | None         |
| 8.4   | MCP base tools (stdio + http) | 2    | 8.3          |
| 8.5   | Thread registry (SQLite)      | 2-3  | 8.1          |
| 8.6   | Help tool extensions          | 2    | 8.5          |
| 8.7   | Thread intervention tools     | 3    | 8.6          |
| 8.8   | Cleanup: remove kiwi_mcp/mcp/ | 1    | 8.4          |
| 8.9   | Thread ID sanitization        | 0.5  | 8.5          |
| 8.10  | Capability token system       | 1-2  | 8.5          |
| 8.11  | Tool chain error handling     | 1    | 8.1          |
| 8.12  | Cost tracking validation      | 1    | None         |
| 8.13  | MCP connector pattern         | 1-2  | 8.4, 8.10    |

**Total: ~21-26 days**

**Parallelization:**

- Phases 8.1-8.2 (streaming) and 8.3-8.4 (MCP primitives) can run in parallel
- Phase 8.5-8.7 (intervention) requires streaming complete

**Critical Path to Annealing:** 8.1 → 8.5 → 8.6 → 8.7 (threads required for thread intervention)

---

### Phase 8.1: Extend http_client with Streaming (3-4 days)

1. Add `StreamConfig` and `StreamDestination` dataclasses
2. Implement `_execute_stream` with SSE parsing
3. Implement sinks: `FileSink`, `NullSink`, `ReturnSink`, `WebSocketSink`
4. Add recursive body templating (walk dict/list/str)
5. Tests for streaming mode

**Files:**

- `kiwi_mcp/primitives/http_client.py` (extend)
- `kiwi_mcp/primitives/sinks.py` (new)
- `tests/primitives/test_http_streaming.py` (new)

### Phase 8.2: LLM Endpoint / Thread Tools (1-2 days)

1. Create `anthropic_messages` tool config
2. Create `anthropic_thread` tool config (with transcript storage)
3. Create `openai_chat` and `openai_thread` equivalents
4. Test streaming to file + return

**Files:**

- `.ai/tools/llm/anthropic_messages.yaml` (new)
- `.ai/tools/llm/openai_chat.yaml` (new)
- `.ai/tools/threads/anthropic_thread.yaml` (new)
- `.ai/tools/threads/openai_thread.yaml` (new)
- `tests/integration/test_thread_tools.py` (new)

### Phase 8.3: JSON-RPC Protocol Handling (2 days)

1. Create JSON-RPC request builder (template-based, data-driven)
2. Create JSON-RPC response parser
3. Works with both subprocess (stdin/stdout) and http_client
4. Tests for JSON-RPC protocol

**Files:**

- `kiwi_mcp/primitives/jsonrpc.py` (new)
- `tests/primitives/test_jsonrpc.py` (new)

### Phase 8.4: MCP Base Tools (2 days)

Create the two base MCP tools that wrap the primitives:

1. `mcp_stdio` - JSON-RPC over subprocess (for local MCPs)
2. `mcp_http` - JSON-RPC over http_client (for remote MCPs)
3. These are the foundation for all MCP connections

**Files:**

- `.ai/tools/mcp/mcp_stdio.yaml` (new)
- `.ai/tools/mcp/mcp_http.yaml` (new)
- `tests/integration/test_mcp_tools.py` (new)

### Phase 8.5: Thread Registry with SQLite (2-3 days)

1. SQLite database for thread registry (WAL mode for concurrency)
2. Tables: `threads`, `thread_events` (see Appendix A.5)
3. Thread state: running, paused, completed, error
4. JSONL transcript writer (append-only, human-readable)
5. Cleanup on completion/timeout
6. Thread context storage (permissions, cost budget)

**Files:**

- `kiwi_mcp/runtime/thread_registry.py` (new)
- `kiwi_mcp/runtime/transcript_writer.py` (new)
- `tests/runtime/test_thread_registry.py` (new)

### Phase 8.6: Help Tool Extensions (2 days)

1. Add `action` parameter: guidance, stuck, escalate, checkpoint
2. Guidance topics: kiwi-overview, permissions, mcps, stuck
3. Signal handlers: route stuck/escalate to appropriate handlers
4. Integration with loop detector

**Files:**

- `kiwi_mcp/tools/help.py` (extend)
- `kiwi_mcp/runtime/intervention.py` (new)
- `tests/tools/test_help_signals.py` (new)

### Phase 8.7: Thread Intervention Tools (3 days)

Enable thread-to-thread intervention for annealing:

1. `thread.read_transcript` - Read another thread's history
2. `thread.inject_message` - Write into another thread
3. `thread.pause` / `thread.resume` - Deterministic control
4. Permissions: only privileged contexts can intervene

**Files:**

- `kiwi_mcp/tools/thread_control.py` (new)
- `tests/tools/test_thread_intervention.py` (new)

### Phase 8.8: Cleanup - Remove kiwi_mcp/mcp/ (1 day)

1. Verify all MCP functionality works via new tools
2. Delete `kiwi_mcp/mcp/` package entirely
3. Update any imports/references
4. Final integration tests

**Files to Delete:**

```
kiwi_mcp/mcp/
├── __init__.py      # DELETE
├── client.py        # DELETE - replaced by mcp_stdio/mcp_http tools
├── pool.py          # DELETE - replaced by thread_registry.py
├── registry.py      # DELETE - replaced by registry-based tool loading
└── schema_cache.py  # DELETE - integrated into tool resolution
```

### Phase 8.9: Thread ID Validation (0.5 days)

1. Implement `validate_thread_id()` with snake_case regex
2. Add validation to spawn_thread.yaml schema
3. Add validation to MCP execute handler
4. Implement auto-suggestion for invalid IDs
5. Clear error messages with examples

**Files:**

- `kiwi_mcp/runtime/validation.py` (new)
- `tests/runtime/test_validation.py` (new)

### Phase 8.10: Capability Token System (1-2 days)

1. Create `.ai/tools/capabilities/` structure (fs.py, net.py, db.py, etc.)
2. Implement capability discovery (same pattern as extractors)
3. Implement `CapabilityToken` dataclass with signing
4. Add `requires` field to tool YAML schema
5. Harness mints tokens from directive permissions
6. Token attenuation on thread spawn (intersection)
7. Add `<orchestration>` to permissions schema for spawn policy

**Files:**

- `.ai/tools/capabilities/*.py` (new - fs, net, db, git, process, mcp)
- `safety_harness/capabilities.py` (new)
- `kiwi_mcp/utils/parsers.py` (extend for orchestration tag)
- `tests/harness/test_capability_tokens.py` (new)

### Phase 8.11: Tool Chain Error Handling (1 day)

1. Implement `ToolChainError` with chain context
2. Add config validation at tool load time
3. Error wrapping at each execution layer
4. Include config_path and validation_errors in responses

**Files:**

- `kiwi_mcp/core/errors.py` (extend)
- `kiwi_mcp/core/executor.py` (extend)
- `tests/core/test_tool_chain_errors.py` (new)

### Phase 8.12: Cost Tracking Validation (1 day)

1. Add `<cost>` to required directive metadata (like permissions, model)
2. Add validation to `DirectiveValidator.validate_metadata()`
3. Helpful error messages with examples
4. No defaults - strict enforcement

**Files:**

- `kiwi_mcp/utils/validators.py` (extend DirectiveValidator)
- `kiwi_mcp/utils/parsers.py` (extract cost from XML)
- `tests/utils/test_cost_validation.py` (new)

### Phase 8.13: MCP Connector Pattern (1-2 days)

1. Implement `mcp_connector` tool type
2. Create connector tool that runs `tools/list` and generates child tool schemas
3. Generated tools include proper `requires` capabilities
4. Auto-signing of generated tools
5. Example connector for one MCP (e.g., Supabase)

**Files:**

- `.ai/tools/mcp/supabase_connector.yaml` (new - example connector)
- `kiwi_mcp/primitives/mcp_connector.py` (new)
- `tests/primitives/test_mcp_connector.py` (new)

---

## Data Flow Diagrams

### Sync LLM Call

```
┌──────────────────────────────────────────────────────────────────────┐
│  execute(tool_id="anthropic_thread", params={...}, mode="sync")      │
└───────────────────────────────────┬──────────────────────────────────┘
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  ChainResolver.resolve("anthropic_thread")                           │
│  → [anthropic_thread, anthropic_messages, http_client]               │
└───────────────────────────────────┬──────────────────────────────────┘
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Merge configs (child overrides parent)                              │
│  Template body with params                                           │
└───────────────────────────────────┬──────────────────────────────────┘
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  http_client._execute_sync(merged_config, params)                    │
│  → POST https://api.anthropic.com/v1/messages                        │
│  → Wait for complete response                                        │
│  → Return HttpResult(body=response_json)                             │
└──────────────────────────────────────────────────────────────────────┘
```

### Streaming LLM Call

```
┌──────────────────────────────────────────────────────────────────────┐
│  execute(tool_id="anthropic_thread", params={...stream:true}, mode="stream")
└───────────────────────────────────┬──────────────────────────────────┘
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  http_client._execute_stream(config, params)                         │
│  → Open SSE connection                                               │
└───────────────────────────────────┬──────────────────────────────────┘
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  For each SSE event:                                                 │
│    ├─→ file_sink (tool) → .ai/threads/{thread_id}/transcript.jsonl   │
│    ├─→ websocket_sink (tool) → ws://remote-client:8080 (A.7)         │
│    └─→ return (built-in) → buffer[]                                  │
└───────────────────────────────────┬──────────────────────────────────┘
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Connection complete                                                 │
│  → Close all sinks                                                   │
│  → Return HttpResult(body=buffer, stream_events_count=N)             │
└──────────────────────────────────────────────────────────────────────┘
```

### Full Thread Loop (safety_harness)

```
┌──────────────────────────────────────────────────────────────────────┐
│  safety_harness.run(directive="deploy_staging")                        │
│  # Thread ID auto-generated: deploy_staging_20260125_103045 (A.1)    │
└───────────────────────────────────┬──────────────────────────────────┘
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Inside spawned thread: SafetyHarnessRunner.run()                      │
│    1. Load directive via MCP                                         │
│    2. Extract <permissions> and mint capability token (A.2)          │
│    3. Extract cost budget from <cost> (REQUIRED - A.4)               │
│    4. System prompt = AGENTS.md (always)                             │
│    5. First message = directive context + user request               │
└───────────────────────────────────┬──────────────────────────────────┘
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Turn 1: Call LLM with 4 Kiwi meta-tools                             │
│  → LLM responds: "I'll check the version first"                      │
│    + execute(tool_id="bash", params={cmd: "git tag -l v*"})          │
└───────────────────────────────────┬──────────────────────────────────┘
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Kernel receives execute(tool_id="bash", ...)                        │
│  → Kernel forwards __auth token opaquely (A.2)                       │
│  → bash tool validates: requires: [process.spawn] present in token   │
│  → ALLOWED: Execute bash command                                     │
│  → Return result to LLM                                              │
└───────────────────────────────────┬──────────────────────────────────┘
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Turn 2: Call LLM with tool result                                   │
│  → LLM responds: "Now running migrations"                            │
│    + execute(tool_id="supabase_migrate", ...)  (A.6: generated tool) │
└───────────────────────────────────┬──────────────────────────────────┘
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Kernel receives execute(tool_id="supabase_migrate", ...)            │
│  → Kernel forwards __auth token opaquely                             │
│  → supabase_migrate validates: requires: [db.migrate] in token       │
│  → ALLOWED: Execute via mcp_http primitive                           │
└───────────────────────────────────┬──────────────────────────────────┘
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Turn 3: LLM responds: "Deployment complete!" (no tool calls)        │
│  → Termination condition: no_tool_calls                              │
└───────────────────────────────────┬──────────────────────────────────┘
                                    ▼
┌──────────────────────────────────────────────────────────────────────┐
│  Return HarnessResult(messages, turn_count=3, thread_id)             │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Risks and Mitigations

| Risk                      | Impact | Mitigation                                           |
| ------------------------- | ------ | ---------------------------------------------------- |
| SSE parsing complexity    | Medium | Use well-tested SSE libraries, extensive tests       |
| SSE stream interruption   | Medium | Execute completed calls, discard partial (A.3)       |
| Provider-specific parsing | Medium | Keep parsing in harness, not MCP core                |
| Memory from `return` sink | High   | Cap buffer size, encourage file sink                 |
| Harness security          | High   | Capability tokens, enforcement at tool layer (A.2)   |
| Streaming cancellation    | Medium | Add timeout and graceful shutdown                    |
| Tool chain debugging      | Medium | Error wrapping with chain context (see A.8)          |
| Permission escalation     | High   | Token attenuation on spawn (A.2)                     |
| Thread ID collisions      | Low    | Harness generates IDs from directive+timestamp (A.1) |
| Registry concurrency      | Medium | SQLite with WAL mode (see A.5)                       |
| Kernel bloat              | High   | Keep kernel dumb, all logic in data-driven tools     |

---

## Success Metrics

- [ ] http_client supports SSE streaming with return (built-in) + 3 data-driven sink tools (file_sink, null_sink, websocket_sink)
- [ ] LLM endpoint tools work with Anthropic and OpenAI
- [ ] Thread tools store transcripts correctly (.ai/threads/{id}/transcript.jsonl)
- [ ] safety_harness completes 10-turn conversation
- [ ] Thread IDs auto-generated by harness (A.1)
- [ ] Capability tokens minted and validated (A.2)
- [ ] Category-based permissions for knowledge and directives (A.2)
- [ ] Signature protection prevents unauthorized modification (A.2)
- [ ] Cost tracking mandatory with validation (A.4)
- [ ] Context tracking with warning at threshold and termination at limit (A.4)
- [ ] Thread registry as data-driven tool (A.5)
- [ ] MCP connector pattern generates tool schemas (A.6)
- [ ] WebSocket sink as Python runtime tool (A.7)
- [ ] Tool chain errors include full context (A.8)
- [ ] No agent loop logic in MCP core
- [ ] Permissions enforced via capability tokens, not prompt
- [ ] Directive execute returns data only; spawning guidance in AGENTS.md/run_directive directive

---

## Appendix A: Implementation Details & Clarifications

### A.1: Thread ID Handling (Three Layers)

Thread ID handling has three distinct layers to provide flexibility while maintaining structure for safety_harness.

#### Layer 1: Base spawn_thread Tool (Harness-Agnostic OS Primitive)

The base `spawn_thread` tool is a **pure OS-level thread/process spawner**. It knows nothing about harnesses — it just receives a runner instance and spawns it.

```yaml
# .ai/tools/threads/base_spawn_thread.yaml
tool_id: spawn_thread
executor_id: python
config:
  module: "kiwi_mcp.runtime.thread_spawner"
  function: "spawn_thread"
  background: true # CRITICAL: Returns immediately, thread runs async

parameters:
  - name: thread_id
    type: string
    required: true
    description: "Thread identifier (alphanumeric, underscore, hyphen allowed)"
  - name: runner_instance
    type: object
    required: true
    description: "Pre-instantiated runner object (any harness type)"
  - name: directive_name
    type: string
    required: true
  - name: initial_message
    type: string
    required: false
```

```python
# kiwi_mcp/runtime/thread_spawner.py
import threading
import multiprocessing

async def spawn_thread(
    thread_id: str,
    runner_instance: Any,  # Pre-instantiated runner (SafetyHarnessRunner, CustomHarness, etc.)
    directive_name: str,
    initial_message: str = "",
    **kwargs
) -> dict:
    """Spawn OS-level thread/process with given runner.

    This is harness-agnostic. The runner is already instantiated
    by the caller (safety_harness, custom_harness, etc.).
    """
    # Validate thread_id
    thread_id = sanitize_thread_id(thread_id)

    # Check uniqueness in registry
    if await thread_exists(thread_id):
        return {"error": f"Thread {thread_id} already exists"}

    # Spawn the thread/process
    # The runner already knows what to do (agent loop, etc.)
    thread = threading.Thread(
        target=runner_instance.run,
        args=(directive_name, initial_message),
        daemon=True
    )
    thread.start()

    return {
        "success": True,
        "thread_id": thread_id,
        "status": "spawned",
        "runner_type": type(runner_instance).__name__,  # For logging only
    }
```

**Key insight:** The base `spawn_thread` tool is like `execve()` — it takes a runnable object and spawns it. It doesn't care what the object does.

|| Sanitization | Rule |
|| ---------------- | ---------------------------------------- |
|| Trim whitespace | Strip leading/trailing spaces |
|| No spaces | Replace internal spaces with underscores |
|| No special chars | Allow only `[a-zA-Z0-9_-]` |
|| Non-empty | Minimum 1 character after sanitization |
|| Uniqueness | Must not exist in registry |

#### Layer 2: safety_harness Tool (Safety Harness Implementation)

The `safety_harness` tool is the entry point for the Safety harness implementation. It **auto-generates** thread IDs and does NOT expose the `thread_id` parameter:

```yaml
# safety_harness/tools/safety_harness.yaml
tool_id: safety_harness
executor_id: python
config:
  module: "safety_harness.spawn"
  function: "spawn_with_safety_harness"
  background: true # CRITICAL: Returns immediately, thread runs async

parameters:
  - name: directive_name
    type: string
    required: true
  - name: initial_message
    type: string
    required: false
  # Note: NO thread_id parameter - auto-generated internally
```

```python
# safety_harness/spawn.py
def generate_thread_id(directive_name: str) -> str:
    """Generate structured thread ID from directive name + timestamp.

    Format: directive_name_YYYYMMDD_HHMMSS
    Example: "deploy_staging_20260125_103045"

    Note: This format is used consistently throughout documentation examples.
    Any format changes should update all references (Lines 760, 1712, 4027, etc.)
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{directive_name}_{timestamp}"

async def spawn_with_safety_harness(directive_name: str, initial_message: str, **kwargs) -> dict:
    """Spawn thread with safety_harness - entry point for Safety harness implementation.

    This function IS the safety harness layer. When spawn_thread is called FROM HERE,
    it knows to instantiate SafetyHarnessRunner because this code imports and uses it.
    """
    thread_id = generate_thread_id(directive_name)

    # Import and instantiate SafetyHarnessRunner directly
    from safety_harness.runner import SafetyHarnessRunner

    # Create the runner
    runner = SafetyHarnessRunner(
        project_path=kwargs.get("project_path"),
        mcp_client=kwargs.get("mcp_client"),  # MCP client for calling back
    )

    # Spawn thread/process with the runner
    # The spawn_thread tool is just the OS-level thread/process spawner
    return await execute_tool("spawn_thread", {
        "thread_id": thread_id,
        "runner_instance": runner,  # Pass the instantiated runner
        "directive_name": directive_name,
        "initial_message": initial_message,
        **kwargs
    })
```

This gives us:

- **Consistent naming** - All kiwi threads follow `directive_name_YYYYMMDD_HHMMSS` pattern
- **Sortable by time** - Easy to find recent threads
- **Directive traceability** - Clear which directive spawned the thread
- **No LLM input required** - Harness controls the ID, preventing collisions

#### Layer 3: thread_directive Tool (Directive→Thread Orchestrator)

The `thread_directive` tool is the high-level orchestrator that LLMs call. It validates directive metadata and calls `safety_harness`. It does NOT expose `thread_id`:

```yaml
# .ai/tools/orchestration/thread_directive.yaml
tool_id: thread_directive
executor_id: python
config:
  module: "safety_harness.orchestration"
  function: "thread_directive_orchestrator"

parameters:
  - name: directive_name
    type: string
    required: true
  - name: initial_message
    type: string
    required: false
  # Note: NO thread_id parameter - delegated to safety_harness
  # Note: NO spawn_thread boolean - this tool ALWAYS spawns
```

```python
# safety_harness/orchestration.py
async def thread_directive_orchestrator(
    directive_name: str,
    initial_message: str,
    **kwargs
) -> dict:
    """Validate directive and spawn on managed thread.

    This is what LLMs call when they want to run a directive on a thread.
    """
    # Load directive to validate metadata
    directive_data = await load_directive(directive_name)

    # Validate ALL required metadata
    validation_errors = []

    if not directive_data.get("cost"):
        validation_errors.append("Missing <cost> tag (REQUIRED for spawning)")

    if not directive_data.get("permissions"):
        validation_errors.append("Missing <permissions> tag (REQUIRED)")

    if not directive_data.get("model"):
        validation_errors.append("Missing <model> tier (REQUIRED)")

    if not directive_data.get("version"):
        validation_errors.append("Missing version (REQUIRED)")

    if validation_errors:
        return {
            "success": false,
            "error": "Directive validation failed",
            "validation_errors": validation_errors,
            "directive_name": directive_name
        }

    # Validation passed - call safety_harness to spawn
    return await execute_tool("safety_harness", {
        "directive_name": directive_name,
        "initial_message": initial_message,
        **kwargs
    })
```

**Note:** The `run_directive` directive (`.ai/directives/run_directive.md`) is different - it's workflow instructions for LLMs on when to use thread_directive vs direct execution. The `thread_directive` tool is what gets called to actually spawn the thread.

#### Layer Summary

```
┌─────────────────────────────────────────────────────────────────────┐
│                     THREAD ID HANDLING LAYERS                        │
│                                                                      │
│  Layer 3: thread_directive tool                                     │
│    • Directive→Thread orchestrator (what LLMs call)                 │
│    • Validates ALL required metadata (cost, perms, model, version)  │
│    • NO thread_id parameter                                         │
│    • Calls → safety_harness (Layer 2)                                 │
│                                                                      │
│  Layer 2: safety_harness tool                                         │
│    • Safety harness implementation entry point                        │
│    • Auto-generates: directive_name_YYYYMMDD_HHMMSS                 │
│    • NO thread_id parameter                                         │
│    • Calls → spawn_thread (Layer 1)                                 │
│                                                                      │
│  Layer 1: spawn_thread tool (base)                                  │
│    • Base thread primitive (any harness)                            │
│    • REQUIRED thread_id parameter                                   │
│    • Permissive validation (alphanumeric, underscore, hyphen)       │
│    • Generic - works with any harness implementation                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### Thread Spawning Sequence (Complete Flow)

This diagram shows the complete execution flow across all three layers:

```
THREAD SPAWNING SEQUENCE (Three Layers)

LLM (in current thread)
  │
  │ execute(tool, run, thread_directive, {directive_name: "deploy"})
  ▼
Layer 3: thread_directive tool
  │ ├── Load directive metadata via MCP
  │ ├── Validate <cost>, <permissions>, <model>, version tags
  │ ├── If validation fails → return error
  │ └── If validation passes → call safety_harness tool
  ▼
Layer 2: safety_harness tool
  │ ├── Generate thread_id = f"{directive_name}_{timestamp}"
  │ │   Example: "deploy_20260125_103045"
  │ ├── Instantiate: runner = SafetyHarnessRunner(
  │ │                         project_path=...,
  │ │                         mcp_client=...
  │ │                       )
  │ └── Call spawn_thread tool with:
  │     • thread_id (generated)
  │     • runner_instance (instantiated SafetyHarnessRunner)
  │     • directive_name
  │     • initial_message
  ▼
Layer 1: spawn_thread tool (base OS primitive)
  │ ├── Validate thread_id format (alphanumeric, _, -)
  │ ├── Check thread_id uniqueness in registry
  │ ├── If collision → return error with collision details
  │ ├── Spawn OS thread: threading.Thread(
  │ │                       target=runner.run,
  │ │                       args=(directive_name, initial_message),
  │ │                       daemon=True
  │ │                     )
  │ ├── Register thread in thread_registry
  │ └── Return {"thread_id": "...", "status": "spawned"} immediately
  │
  │ [Async boundary - caller returns, thread runs independently]
  │
  ▼
INSIDE SPAWNED THREAD: runner.run(directive_name, initial_message)
  │ ├── Load directive via MCP: execute(directive, run, directive_name)
  │ ├── Extract <permissions> from returned directive data
  │ ├── Convert permissions to capability list with scopes:
  │ │   [{"cap": "fs.write", "scope": {"path": "dist/**"}}, ...]
  │ ├── Mint capability token (JWT/PASETO):
  │ │   • caps: capability list with scopes
  │ │   • aud: "kiwi-mcp"
  │ │   • exp: datetime + 1 hour
  │ │   • directive_id: directive_name
  │ │   • thread_id: thread_id
  │ ├── Store token in ThreadContext
  │ ├── Extract <cost> budget, setup cost tracker
  │ ├── Build system prompt from AGENTS.md
  │ ├── Build first message: directive context + initial_message
  │ └── Start agent loop:
  │     ┌─────────────────────────────────────────┐
  │     │ LOOP (until stop condition):            │
  │     │   1. Call LLM with messages + tools     │
  │     │   2. Parse LLM response                 │
  │     │   3. If tool calls:                     │
  │     │      • Attach __auth token to params    │
  │     │      • Execute via MCP                  │
  │     │      • Collect results                  │
  │     │   4. If stop_reason or budget exceeded: │
  │     │      • Break loop                       │
  │     │   5. Append results to messages         │
  │     │   6. Repeat                             │
  │     └─────────────────────────────────────────┘
  │
  ▼
Thread completes
  • Update thread_registry status → "completed"
  • Write final transcript entry
  • Clean up resources
```

**Key Observations:**

1. **Instantiation happens at Layer 2** - `safety_harness` creates the runner
2. **Layer 1 is harness-agnostic** - Accepts any runner, just spawns it
3. **Token minting happens INSIDE spawned thread** - Not before spawning
4. **Async spawn** - Caller gets thread_id immediately, thread runs independently
5. **Three validation points** - Layer 3 (metadata), Layer 1 (thread_id), Tool layer (permissions)

#### Error Response Format (Base Layer)

```json
{
  "success": false,
  "error": {
    "code": "INVALID_THREAD_ID",
    "message": "thread_id contains invalid characters. Allowed: alphanumeric, underscore, hyphen",
    "received": "Deploy Staging!",
    "sanitized": "deploy_staging"
  }
}
```

---

### A.2: Permission Enforcement Architecture

Permission enforcement uses a **capability token model** that keeps the MCP kernel dumb while enabling enforcement at multiple layers.

#### Core Principle: Kernel Stays Dumb

The MCP kernel does NOT:

- Know about "threads" (that's a harness concept)
- Look up permission registries
- Validate capability tokens

The kernel just forwards opaque metadata. **Enforcement happens at the tool layer**, not the kernel.

#### Key Architecture: spawn_thread Tool Instantiates Harness

The relationship between spawn_thread tool and safety_harness:

```
┌─────────────────────────────────────────────────────────────────────┐
│                   HARNESS INSTANTIATION FLOW                         │
│                                                                      │
│  1. LLM calls: execute(tool, run, thread_directive, {               │
│       directive_name: "deploy_staging",                             │
│       initial_message: "Deploy v1.2.3"                              │
│     })                                                               │
│                                                                      │
│  2. thread_directive tool (Layer 3):                                │
│     ├── Validates directive metadata (cost, perms, model, version)  │
│     └── Calls → safety_harness (Layer 2)                              │
│                                                                      │
│  3. safety_harness tool (Layer 2):                                    │
│     ├── Auto-generates thread_id                                    │
│     ├── Instantiates SafetyHarnessRunner(project_path, mcp_client)   │
│     └── Calls → spawn_thread with runner_instance (Layer 1)        │
│                                                                      │
│  4. spawn_thread tool (Layer 1 - Base OS primitive):                │
│     ├── Receives pre-instantiated runner_instance                   │
│     ├── Validates thread_id uniqueness                              │
│     ├── Starts new thread/process with runner.run()                 │
│     └── Returns thread_id to caller                                 │
│                                                                      │
│  5. Inside the new thread, SafetyHarnessRunner:                       │
│     ├── Loads directive from MCP                                    │
│     ├── Mints capability token from <permissions>                   │
│     ├── Runs agent loop (call LLM → execute tools → repeat)         │
│     └── Calls MCP kernel to execute tools                           │
│                                                                      │
│  6. MCP kernel services harness requests:                           │
│     ├── Receives execute() calls from harness                       │
│     ├── Forwards capability tokens opaquely                         │
│     └── Returns tool results                                        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Key insight:** The `safety_harness` tool (Layer 2) instantiates SafetyHarnessRunner and passes it to `spawn_thread` (Layer 1). The spawn_thread tool is harness-agnostic - it just receives a runner and spawns it. The harness lives INSIDE the thread context and calls MCP kernel to execute tools.

This means:

1. **spawn_thread is a base OS primitive** - Harness-agnostic, accepts any runner
2. **safety_harness is the safety implementation layer** - Instantiates SafetyHarnessRunner, passes to spawn_thread
3. **SafetyHarnessRunner is a Python class** - Provides the agent loop logic
4. **Harness calls MCP kernel** - Uses MCP client to execute tools with capability tokens
5. **Both layers validate** - Harness pre-validates, tools validate independently (defense in depth)

---

### Infrastructure Tools: Hierarchical Permission Model

Infrastructure tools like `thread_registry` are **regular MCP tools** that require capabilities. They follow the same enforcement model as all other tools.

**See [PERMISSION_MODEL.md](./PERMISSION_MODEL.md) for complete details on:**

- Hierarchical permissions (core vs user directives)
- System-only capabilities
- Path-based permission scoping
- Validation at directive creation
- Project sandboxing

**The hierarchy:**

1. **Core system directives** (e.g., `thread_directive`) grant broad permissions with system capabilities
2. **User directives** grant limited, project-scoped permissions specific to their task
3. **Each runs with its own token** based on its `<permissions>` with path scopes

#### Example: thread_directive (Core System Directive)

```xml
<!-- .ai/directives/core/thread_directive.md -->
<directive name="thread_directive" version="1.0.0">
  <metadata>
    <description>Spawn directive on managed thread with validation</description>
    <category>core</category>

    <permissions>
      <!-- Core system capabilities (SYSTEM_ONLY) -->
      <execute resource="registry" action="write"/>
      <execute resource="registry" action="read"/>
      <execute resource="spawn" action="thread"/>

      <!-- MCP operations -->
      <execute resource="kiwi-mcp" action="execute"/>
      <execute resource="kiwi-mcp" action="load"/>

      <!-- Filesystem for validation (project-scoped) -->
      <read resource="filesystem" path=".ai/directives/**"/>
    </permissions>

    <cost>
      <max_turns>5</max_turns>
      <max_total_tokens>10000</max_total_tokens>
    </cost>
  </metadata>

  <process>
    <step name="validate_directive">
      <description>Load and validate directive metadata</description>
      <action>execute(directive, run, {directive_name})</action>
    </step>

    <step name="spawn_thread">
      <description>Call safety_harness to spawn managed thread</description>
      <action>execute(tool, run, safety_harness, {...})</action>
    </step>
  </process>
</directive>
```

**When `thread_directive` runs:**

- Token minted with `[{cap: "registry.write", scope: {}}, {cap: "registry.read", scope: {}}, {cap: "spawn.thread", scope: {}}, ...]`
- Can call `thread_registry` tool ✅ (has `registry.write`)
- Can spawn threads ✅ (has `spawn.thread`)
- Paths are project-scoped (`.ai/directives/**` relative to project root)

#### Example: User Directive

```xml
<!-- .ai/directives/user/deploy_staging.md -->
<directive name="deploy_staging" version="1.0.0">
  <metadata>
    <category>user</category>
    <permissions>
      <!-- Project-scoped filesystem access -->
      <read resource="filesystem" path="src/**"/>
      <write resource="filesystem" path="dist/**"/>

      <!-- Scoped tool access -->
      <execute resource="tool" id="bash"/>

      <!-- MCP operations -->
      <execute resource="kiwi-mcp" action="execute"/>
    </permissions>
  </metadata>
</directive>
```

**When `deploy_staging` runs:**

- Token minted with `[{cap: "fs.read", scope: {path: "src/**"}}, {cap: "fs.write", scope: {path: "dist/**"}}, {cap: "tool.execute", scope: {id: "bash"}}, ...]`
- **Can** read files in `src/**` ✅ (project-scoped)
- **Can** write files in `dist/**` ✅ (project-scoped)
- **Cannot** read/write outside project ❌ (no `fs.absolute` capability)
- **Cannot** call `thread_registry` ❌ (no `registry.write`)
- **Cannot** spawn threads ❌ (no `spawn.thread`)
- **Cannot** modify extractors ❌ (no write access to `.ai/tools/extractors/**`)

#### thread_registry Tool (Regular MCP Tool)

```yaml
# .ai/tools/threads/thread_registry.yaml
tool_id: thread_registry
tool_type: runtime
executor_id: python
version: "1.0.0"
description: "Query and manage thread registry"

requires:
  - registry.write # For register, update_status
  - registry.read # For get_status, query

config:
  db_path: ".ai/threads/registry.db"

actions:
  - name: register
    description: "Register new thread"
  - name: update_status
    description: "Update thread status"
  - name: get_status
    description: "Get thread status"
  - name: query
    description: "Query threads by criteria"
```

**Enforcement (same as all tools):**

```python
# thread_registry tool implementation
async def register_thread(params: dict) -> dict:
    token = params.get("__auth")

    # Validate token has required capabilities (same as ANY tool)
    if not validate_token(token, required_caps=["registry.write"]):
        return {"error": "Missing required capability: registry.write"}

    # Token is valid - proceed
    # ...
```

#### How thread_directive Calls thread_registry

```
┌─────────────────────────────────────────────────────────────────────┐
│                HIERARCHICAL PERMISSION FLOW                          │
│                                                                      │
│  1. User calls: execute(tool, run, thread_directive, {              │
│       directive_name: "deploy_staging"                              │
│     })                                                               │
│                                                                      │
│  2. thread_directive spawns with its own token:                     │
│     Token: [registry.write, registry.read, spawn.thread, ...]       │
│                                                                      │
│  3. thread_directive validates deploy_staging directive:            │
│     execute(directive, run, deploy_staging)  ✅                      │
│                                                                      │
│  4. thread_directive calls safety_harness:                            │
│     execute(tool, run, safety_harness, {...})  ✅                      │
│                                                                      │
│  5. safety_harness spawns thread, calls thread_registry:              │
│     execute(tool, run, thread_registry, {                           │
│       action: "register",                                            │
│       __auth: thread_directive's token  ← Has registry.write ✅      │
│     })                                                               │
│                                                                      │
│  6. New thread runs with deploy_staging's token:                    │
│     Token: [fs.read, tool.bash, kiwi-mcp.execute]                   │
│     If deploy_staging tries to call thread_registry: ❌ DENIED      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### Summary: Clean Hierarchical Model

**See [PERMISSION_MODEL.md](./PERMISSION_MODEL.md) for complete documentation including:**

- System vs user capability validation
- Path-based permission scoping
- Project sandboxing (relative vs absolute paths)
- Extractor modification security
- Token attenuation for spawned threads
- Nested directive execution
- Complete examples

**Quick summary:**

1. **One token per thread** - Minted from directive's `<permissions>` with path scopes
2. **All tools enforce uniformly** - No special cases, same validation logic
3. **Hierarchical permissions** - Core directives have system capabilities + broader scopes
4. **Path scoping required** - Filesystem ops must specify path patterns (e.g., `src/**`)
5. **Project sandboxing** - User directives can only access project files (no `fs.absolute`)
6. **System capabilities** - Marked `SYSTEM_ONLY`, rejected for user directives at creation
7. **Validation at creation** - Prevents invalid permission combinations
8. **Extractor protection** - Modifying extractors requires both path scope AND `extractor.modify` capability

**The key insight:** Infrastructure tools aren't special. Core directives that call them are special (they have broader permissions with system capabilities).

```
┌─────────────────────────────────────────────────────────────────────┐
│                  PERMISSION ENFORCEMENT FLOW                         │
│                                                                      │
│  1. SafetyHarnessRunner instance (spawned thread) mints token         │
│     └── After directive is loaded from MCP                          │
│     └── Token contains: caps[], directive_id, thread_id, exp        │
│                                                                      │
│  2. LLM requests tool execution via harness                          │
│     └── Harness checks: Does token contain required capabilities?   │
│     └── If no: Return error immediately (fail fast)                 │
│                                                                      │
│  3. Harness calls tool with __auth metadata                          │
│     └── Kernel forwards opaquely (no validation)                    │
│                                                                      │
│  4. Tool validates capability token independently                    │
│     └── Defense in depth: Tool doesn't trust caller                 │
│     └── Each tool declares requires: [cap1, cap2] in YAML           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Clarification on token minting:**

- **thread_directive tool** (Layer 3) does NOT mint tokens - it just validates and orchestrates
- **safety_harness tool** (Layer 2) does NOT mint tokens - it just spawns the thread
- **spawn_thread tool** (Layer 1) instantiates SafetyHarnessRunner class
- **SafetyHarnessRunner.run_directive()** method is what actually:
  1. Loads the directive via MCP
  2. Extracts `<permissions>` from directive
  3. Mints the capability token
  4. Stores it in ThreadContext
  5. Attaches it to all subsequent tool calls

This happens INSIDE the spawned thread, not in the tools that spawned it.

**Why both layers?**

- **Harness validation:** Fail fast, better error messages for LLM
- **Tool validation:** Defense in depth, works even if called without harness
- **Kernel agnostic:** Kernel never needs to understand permissions

#### Capabilities as Data-Driven Tools

**See [PERMISSION_MODEL.md](./PERMISSION_MODEL.md) for complete capability system documentation.**

Following the same pattern as **extractors**, capabilities are defined as data-driven tools in `.ai/tools/capabilities/`:

```
.ai/tools/capabilities/
├── fs.py           # Filesystem capabilities (fs.read, fs.write)
├── net.py          # Network capabilities (net.http, net.websocket)
├── db.py           # Database capabilities (db.query, db.migrate)
├── git.py          # Git capabilities (git.read, git.push)
├── process.py      # Process capabilities (process.spawn)
└── mcp.py          # MCP capabilities (mcp.connect)
```

Each capability tool defines:

```python
# .ai/tools/capabilities/fs.py
__tool_type__ = "capability"
__version__ = "1.0.0"
__category__ = "capabilities"

CAPABILITIES = ["fs.read", "fs.write"]
DESCRIPTION = "Filesystem access capabilities"

# Optional: validation logic for the capability
def validate_scope(cap: str, scope: dict) -> bool:
    """Validate capability scope (e.g., path restrictions)."""
    if cap == "fs.write" and "path" in scope:
        return scope["path"].startswith(".ai/")
    return True
```

This means:

- **No hardcoded capability list** - discover from `.ai/tools/capabilities/`
- **Capabilities are signed and validated** like any other tool
- **New capabilities added by dropping in a file** - no code changes

#### How It Works

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PERMISSION FLOW (Capability Tokens)                     │
│                                                                             │
│  1. Harness loads directive                                                 │
│     └── Extracts <permissions> → converts to capability list                │
│                                                                             │
│  2. Harness mints signed capability token                                   │
│     └── JWT/PASETO with: caps[], exp, aud (tool namespace)                  │
│                                                                             │
│  3. All tool calls include token (via __auth metadata)                      │
│     └── Kernel forwards opaquely (doesn't validate)                         │
│                                                                             │
│  4. Tool implementation validates token + checks required caps              │
│     └── Each tool declares `requires: [cap1, cap2]` in YAML                 │
│                                                                             │
│  5. On spawn child thread: attenuate token (subset of parent caps)          │
│     └── Child can never exceed parent's capabilities                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Tool YAML with Required Capabilities

```yaml
# .ai/tools/filesystem/write_file.yaml
tool_id: write_file
executor_id: python
requires:
  - fs.write # Tool declares what it needs

parameters:
  - name: path
    type: string
  - name: content
    type: string
```

**Tool validates both capability AND scope:**

```python
async def write_file(path: str, content: str, __auth: str, __project_path: str) -> dict:
    token = verify_token(__auth)

    # 1. Check has fs.write capability
    fs_write_grants = [c for c in token.caps if c["cap"] == "fs.write"]
    if not fs_write_grants:
        return {"error": "Missing capability: fs.write"}

    # 2. Resolve path relative to project (with escape protection)
    project_root = Path(__project_path)
    full_path = (project_root / path).resolve()

    if not full_path.is_relative_to(project_root):
        return {"error": "Path outside project"}

    relative_path = str(full_path.relative_to(project_root))

    # 3. Check path matches granted scope
    for grant in fs_write_grants:
        if fnmatch.fnmatch(relative_path, grant["scope"]["path"]):
            with open(full_path, 'w') as f:
                f.write(content)
            return {"success": True}

    return {"error": f"Path not in granted scope: {relative_path}"}
```

The harness uses `requires` to:

1. Fail early if directive doesn't grant required capability
2. Provide clear error: "write_file requires fs.write with path scope, but directive only grants fs.read"

See [PERMISSION_MODEL.md](./PERMISSION_MODEL.md) for complete validation logic.

#### Token Structure

```python
@dataclass
class CapabilityToken:
    caps: List[dict]       # Granted capabilities with scopes: [{"cap": str, "scope": dict}, ...]
    aud: str               # Tool namespace (prevents cross-service replay)
    exp: datetime          # Short expiry (minutes/hours)
    parent_id: Optional[str]  # For delegation chain tracking
    directive_id: str      # Which directive minted this
    thread_id: str         # Which thread this belongs to
```

**Example token payload:**

```python
{
    "caps": [
        {"cap": "fs.read", "scope": {"path": "src/**"}},
        {"cap": "fs.write", "scope": {"path": "dist/**"}},
        {"cap": "tool.execute", "scope": {"id": "bash"}},
    ],
    "aud": "kiwi-mcp",
    "exp": "2026-01-25T12:00:00Z",
    "directive_id": "deploy_staging",
    "thread_id": "deploy_staging_20260125_103045",
}
```

See [PERMISSION_MODEL.md](./PERMISSION_MODEL.md) for complete details on scope validation.

#### Inheritance via Attenuation

When Thread A (directive X) spawns Thread B (directive Y):

```python
def attenuate_token(parent_token: CapabilityToken, child_directive: dict) -> CapabilityToken:
    """Child gets intersection of parent caps and directive caps."""
    parent_caps = set(parent_token.caps)
    child_caps = set(directive_to_caps(child_directive["permissions"]))

    return CapabilityToken(
        caps=list(parent_caps & child_caps),  # INTERSECTION
        aud=parent_token.aud,
        exp=datetime.now() + timedelta(minutes=30),
        parent_id=parent_token.id,
        directive_id=child_directive["name"],
    )
```

#### Nested Directive Execution (Same Thread, Same Token)

**Critical Scenario:** What happens when directive A (running on a thread) calls `execute(directive, run, directive_B)` to run another directive?

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              NESTED DIRECTIVE EXECUTION & PERMISSION FLOW                    │
│                                                                              │
│  1. Thread spawned with directive A                                          │
│     └── Token minted from directive A's <permissions>                       │
│     └── Token stored in ThreadContext (thread-scoped, not directive-scoped) │
│                                                                              │
│  2. Directive A's process steps instruct LLM:                                │
│     "execute(directive, run, directive_B)"                                    │
│                                                                              │
│  3. LLM generates tool call through harness:                                │
│     execute(item_type="directive", action="run", item_id="directive_B")      │
│     └── Harness checks: Does directive A's token allow this?                │
│     └── Requires: <execute resource="kiwi-mcp" action="execute"/>            │
│                                                                              │
│  4. Kernel returns directive B's data (kernel stays dumb)                  │
│     └── Returns: process steps, permissions, cost, etc.                      │
│     └── NO new token minted                                                 │
│                                                                              │
│  5. LLM follows directive B's process steps                                  │
│     └── All tool calls use directive A's token (same thread, same token)   │
│                                                                              │
│  6. When directive B's steps call tools:                                     │
│     └── Tool validates: Does directive A's token have required caps?       │
│     └── Example: directive B needs fs.write, but directive A only has fs.read│
│     └── Result: DENIED - no privilege escalation                            │
│                                                                              │
│  7. Cost tracking:                                                           │
│     └── All costs accumulate in directive A's budget                        │
│     └── directive B's execution is part of directive A's thread            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Principles:**

1. **Token is thread-scoped, not directive-scoped**

   - Token is minted ONCE when thread spawns (from directive A)
   - Token persists for entire thread lifetime
   - Nested directives use the SAME token

2. **No privilege escalation**

   - directive B can only do what directive A's token allows
   - directive B's declared permissions are IGNORED for enforcement
   - Only directive A's permissions matter

3. **Permission check for `execute(directive, run, ...)`**

   - Requires: `<execute resource="kiwi-mcp" action="execute"/>`
   - This allows calling the MCP execute action
   - Without this, directive A cannot call other directives

4. **Cost tracking is cumulative**
   - directive B's execution costs count toward directive A's budget
   - No separate budget for nested directives
   - If directive A's budget is exceeded, thread terminates

**Example:**

```xml
<!-- directive_A.md -->
<directive name="deploy_staging" version="1.0.0">
  <metadata>
    <permissions>
      <read resource="filesystem" path="src/**"/>
      <execute resource="kiwi-mcp" action="execute"/>  <!-- Allows calling other directives -->
      <execute resource="tool" id="bash"/>
    </permissions>
    <cost>
      <max_turns>50</max_turns>
      <max_total_tokens>100000</max_total_tokens>
    </cost>
  </metadata>
  <process>
    <step name="run_tests">
      <action>execute(directive, run, run_tests)</action>  <!-- Calls directive_B -->
    </step>
  </process>
</directive>

<!-- directive_B.md (run_tests) -->
<directive name="run_tests" version="1.0.0">
  <metadata>
    <permissions>
      <read resource="filesystem" path="tests/**"/>
      <write resource="filesystem" path="tests/output/**"/>  <!-- directive_A doesn't have this -->
      <execute resource="tool" id="pytest"/>
    </permissions>
  </metadata>
  <process>
    <step name="run_pytest">
      <action>execute(tool, run, pytest, {...})</action>
    </step>
    <step name="write_results">
      <action>execute(tool, run, write_file, {path: "tests/output/results.json"})</action>
      <!-- ❌ DENIED: directive_A's token doesn't have fs.write -->
    </step>
  </process>
</directive>
```

**What happens:**

1. Thread spawned with directive_A's token: `[fs.read, kiwi-mcp.execute, tool.bash]`
2. directive_A calls `execute(directive, run, run_tests)` ✅ (has `kiwi-mcp.execute`)
3. Kernel returns directive_B's data ✅
4. directive_B's step calls `pytest` ✅ (has `tool.bash`, pytest might work if bash covers it)
5. directive_B's step calls `write_file` ❌ **DENIED** (directive_A's token lacks `fs.write`)

**To allow directive_B to write files, directive_A must grant it:**

```xml
<!-- directive_A.md -->
<permissions>
  <read resource="filesystem" path="src/**"/>
  <write resource="filesystem" path="tests/output/**"/>  <!-- Add this -->
  <execute resource="kiwi-mcp" action="execute"/>
  <execute resource="tool" id="bash"/>
</permissions>
```

**Why this design?**

- **Prevents privilege escalation** - Child directives can't exceed parent's permissions
- **Simple mental model** - One token per thread, clear ownership
- **Cost tracking** - All nested execution counts toward parent's budget
- **Audit trail** - All actions traceable to original directive's token

**Alternative: Spawn New Thread**

If directive_B needs different permissions or separate cost tracking, directive_A should spawn a new thread:

```xml
<!-- directive_A.md -->
<process>
  <step name="run_tests_in_isolation">
    <action>execute(tool, run, thread_directive, {
      directive_name: "run_tests",
      initial_message: "Run full test suite"
    })</action>
    <!-- This spawns a NEW thread with directive_B's own token -->
  </step>
</process>
```

When spawning a new thread, token attenuation applies (see "Inheritance via Attenuation" above).

#### LLM Execution Context (Inside vs Outside MCP)

Permission enforcement depends on **where the LLM runs**:

| Context                           | Description                             | Permission Enforcement                 |
| --------------------------------- | --------------------------------------- | -------------------------------------- |
| **LLM Outside MCP**               | Claude Code, Amp, Cursor call MCP tools | None - frontend handles permissions    |
| **LLM Inside MCP (Base Harness)** | Custom harness without token minting    | Optional - not recommended             |
| **LLM Inside MCP (Safety Harness)** | Our opinionated harness                 | Full enforcement via capability tokens |

When using MCP as a tool provider for external LLMs (Claude Code, Amp), the LLM runs **outside** the MCP. We cannot enforce capability tokens because we don't control the LLM execution loop.

The safety_harness is the **primary enforcement mechanism** for LLMs running inside our control. It's not an "additional layer" - it IS the enforcement layer for Kiwi-managed threads.

#### Directive Run Location

A directive's "main thread" is relative to what's executing it:

| Term              | Meaning                                         |
| ----------------- | ----------------------------------------------- |
| **Main thread**   | The current directive's execution context       |
| **Parent thread** | The thread that spawned this one (if any)       |
| **Project space** | The `.ai/` folder the directive was loaded from |

When spawning a directive, the harness specifies:

```python
await spawn_thread(
    directive_id="deploy_staging",
    project_path="/home/user/project",  # Which .ai/ to use
    inherit_project=True,  # Use parent's project, or specify new one
)
```

Directives can be run from:

- **Current project** - `.ai/directives/` in current working directory
- **User space** - `~/.ai/directives/` (personal directives)
- **Different project** - Explicit `project_path` for cross-project orchestration

#### Orchestration Flag in Permissions

The `orchestration` flag and spawn restrictions live in the `<permissions>` section (not a separate tag):

```xml
<permissions>
  <!-- Standard permissions -->
  <read resource="filesystem" path="**/*" />
  <execute resource="tool" id="bash" />

  <!-- Orchestration: declares this directive spawns sub-threads -->
  <orchestration enabled="true">
    <allow_categories>audit,test,deploy</allow_categories>
    <allow_directives>verify_*,check_*</allow_directives>
    <deny_directives>delete_*,drop_*</deny_directives>
  </orchestration>
</permissions>
```

If `<orchestration enabled="true">` is present:

- Directive CAN spawn sub-threads
- Spawn policy is enforced per the nested rules

If `<orchestration>` is absent or `enabled="false"`:

- Directive CANNOT spawn sub-threads
- Any attempt to spawn fails immediately

Enforcement happens in the **harness** (not kernel) when spawn is requested.

#### Category-Based Permissions for All Item Types

While tool permissions use capability tokens, **knowledge and directives** use category-based access control. This follows the same pattern but applies to read/load operations on items:

```xml
<permissions>
  <!-- Tool capabilities (as before) -->
  <execute resource="tool" id="bash" />

  <!-- Knowledge access by category -->
  <knowledge>
    <allow_categories>patterns,reference,architecture</allow_categories>
    <deny_categories>secrets,internal</deny_categories>
  </knowledge>

  <!-- Directive access by category -->
  <directives>
    <allow_categories>deploy,test,audit</allow_categories>
    <deny_categories>admin,dangerous</deny_categories>
    <deny_directives>drop_*,delete_*,destroy_*</deny_directives>
  </directives>
</permissions>
```

**Default behavior:** If no `<knowledge>` or `<directives>` section is specified, all categories are allowed (permissive default). The `deny_*` rules act as a **blacklist** that overrides allows.

| Item Type | Access Controlled By                  | Default                 |
| --------- | ------------------------------------- | ----------------------- |
| Tool      | `requires: [cap1, cap2]` in tool YAML | Deny if no matching cap |
| Knowledge | `<knowledge>` allow/deny categories   | Allow all               |
| Directive | `<directives>` allow/deny categories  | Allow all               |

#### Signature Protection for Core Items

The combination of **integrity hashing** and **signature validation** provides protection against LLM abuse of core items:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    SIGNATURE PROTECTION MODEL                                │
│                                                                              │
│  When LLM runs INSIDE safety_harness:                                          │
│                                                                              │
│  1. LLM requests: execute(directive, create, item_id="evil_directive")       │
│                                                                              │
│  2. Harness checks: Does directive have <permissions> to execute create?     │
│     └── execute(item_type="directive", action="create") requires:            │
│         directive.modify capability                                          │
│                                                                              │
│  3. If allowed, validation runs:                                             │
│     └── Parses XML, validates structure                                      │
│     └── Signs with kiwi-mcp signature                                        │
│     └── Hash stored in signature comment                                     │
│                                                                              │
│  4. Any modification without re-signing invalidates:                         │
│     └── Run action fails: "Integrity mismatch"                               │
│     └── LLM cannot bypass by editing file directly                           │
│                                                                              │
│  5. Critical directives can deny modification:                               │
│     └── <deny_directives>core_*,system_*</deny_directives>                   │
│     └── Even with directive.modify cap, specific items blocked               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key insight:** Because we control the LLM execution loop (safety_harness), we can enforce that:

1. All create/update/delete operations go through our validation pipeline
2. Signatures are required for execution
3. Category restrictions can block access to sensitive items
4. Core system items can be protected from modification

This protection only applies when the LLM runs **inside** the safety_harness. External frontends (Claude Code, Amp) calling MCP directly have their own permission systems.

---

### A.3: Stream Parsing Error Recovery

When SSE stream is interrupted mid-tool-call during JSON accumulation, behavior depends on what was already executed.

#### Stream State Tracking

The SSE parser tracks three categories:

```python
@dataclass
class StreamState:
    # Tool calls that completed before interruption (JSON fully parsed)
    completed_tool_calls: List[ToolCall]

    # Tool call that was mid-parse when stream died
    partial_tool_call: Optional[PartialToolCall]

    # Text content accumulated (always usable)
    text_content: str

    # Was the stream cleanly terminated?
    clean_finish: bool
```

#### Behavior on Stream Interruption

| Scenario                                      | Behavior                                              |
| --------------------------------------------- | ----------------------------------------------------- |
| Stream ends cleanly                           | Normal processing                                     |
| Stream dies, no tool calls started            | Return text content, mark incomplete                  |
| Stream dies, N tool calls complete, 0 partial | Execute N completed, mark incomplete                  |
| Stream dies, N tool calls complete, 1 partial | Execute N completed, discard partial, mark incomplete |

**Key rule:** Completed tool calls ARE executed. Only the partial one is discarded.

#### Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "STREAM_INCOMPLETE",
    "message": "SSE stream ended mid-response. Partial tool call discarded.",
    "completed_tools": ["execute:abc123", "search:def456"],
    "discarded_partial": {
      "tool_name": "load",
      "bytes_collected": 412,
      "json_parse_error": "Unexpected end of JSON input"
    },
    "retryable": true
  }
}
```

#### Retry Configuration (Data-Driven)

Retry policy is defined in the **tool schema**, not hardcoded:

```yaml
# .ai/tools/llm/anthropic_messages.yaml
tool_id: anthropic_messages
executor_id: http_client
config:
  # ... other config ...

retry:
  max_attempts: 3
  backoff_ms: [250, 1000, 3000] # Exponential backoff
  retryable_errors:
    - STREAM_INCOMPLETE
    - CONNECTION_RESET
    - TIMEOUT
```

**Key principle:** Never "repair" or execute partial JSON. Complete tool calls are safe; partial ones are discarded.

---

### A.4: Cost and Context Tracking Enforcement

Cost and context tracking is **mandatory** for all directives. This follows the same validation pattern as `<permissions>`, `<model>`, and `version` - required metadata with helpful error messages, no defaults.

#### Two Independent Budget Systems

**Cost Budget** (cumulative across all turns) and **Context Budget** (current turn only) are separate concerns:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                  COST vs CONTEXT TRACKING (Separate Concerns)                │
│                                                                              │
│  Turn 1:                                                                     │
│    Input: 10K tokens, Output: 5K tokens                                     │
│    ├─ Cost Budget: +15K tokens (cumulative)                                 │
│    ├─ Context Budget: 10K tokens (current turn input)                       │
│    └─ Status: Both OK ✅                                                      │
│                                                                              │
│  Turn 2:                                                                     │
│    Input: 12K tokens, Output: 6K tokens                                     │
│    ├─ Cost Budget: +18K = 33K tokens total (cumulative)                     │
│    ├─ Context Budget: 12K tokens (current turn input)                       │
│    └─ Status: Both OK ✅                                                      │
│                                                                              │
│  Turn 3:                                                                     │
│    Input: 180K tokens, Output: 8K tokens                                    │
│    ├─ Cost Budget: +188K = 221K tokens total (cumulative) ⚠️                 │
│    ├─ Context Budget: 180K tokens (current turn input) ⚠️ EXCEEDS LIMIT!    │
│    └─ Status: TERMINATE (context limit exceeded at 180K max)                │
│                                                                              │
│  Why Separate?                                                               │
│  • Cost tracks resources consumed (billing, quota management)               │
│  • Context tracks model limits (can't continue with full context)           │
│  • Context exceeded = always fatal (cannot proceed)                         │
│  • Cost exceeded = configurable (stop/warn/escalate)                        │
│                                                                              │
│  Example: max_total_tokens=150K, max_context_tokens=180K                    │
│  • Turn 3 exceeds cost budget (221K > 150K total)                           │
│  • Turn 3 also exceeds context (180K input = at model limit)                │
│  • Either one would trigger termination                                     │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Required Directive Metadata

All directives MUST include a `<cost>` section with at least `max_turns` and `on_exceeded`. Optional limits provide additional safety:

```xml
<metadata>
  <!-- REQUIRED: Cost and context tracking configuration -->
  <cost>
    <!-- Token limits (optional individual limits) -->
    <max_input_tokens>100000</max_input_tokens>
    <max_output_tokens>50000</max_output_tokens>
    <max_total_tokens>150000</max_total_tokens>

    <!-- Context window limit (optional, defaults to model's max) -->
    <max_context_tokens>180000</max_context_tokens>
    <context_warning_threshold>0.8</context_warning_threshold>

    <!-- Dollar budget (optional) -->
    <max_cost_usd>5.00</max_cost_usd>

    <!-- REQUIRED: Turn limit -->
    <max_turns>30</max_turns>

    <!-- REQUIRED: Action on exceeded ("stop" | "warn" | "escalate") -->
    <on_exceeded>escalate</on_exceeded>
  </cost>
</metadata>
```

**Termination Logic:** Thread terminates when **ANY** of the following limits are exceeded (OR logic):

| Limit                | Description                                  | Checked After |
| -------------------- | -------------------------------------------- | ------------- |
| `max_turns`          | Number of LLM calls made                     | Each turn     |
| `max_input_tokens`   | Cumulative input tokens across all turns     | Each turn     |
| `max_output_tokens`  | Cumulative output tokens across all turns    | Each turn     |
| `max_total_tokens`   | Sum of input + output tokens                 | Each turn     |
| `max_cost_usd`       | Dollar cost based on model pricing           | Each turn     |
| `max_context_tokens` | Input tokens in current turn (context limit) | Each turn     |

The thread stops as soon as **any one** of these limits is exceeded.

#### Validation (Matches Existing Patterns)

Enforcement uses the existing `DirectiveValidator` in `kiwi_mcp/utils/validators.py`:

```python
# Added to DirectiveValidator.validate_metadata()
# Validate cost (REQUIRED) - same pattern as permissions, model, version
cost_data = parsed_data.get("cost")
if not cost_data:
    issues.append(
        "No <cost> tag found in directive metadata. "
        "Add a <cost> tag inside <metadata> with at least max_turns and on_exceeded. "
        "Example: <cost><max_turns>30</max_turns><on_exceeded>escalate</on_exceeded></cost>"
    )
else:
    if not cost_data.get("max_turns"):
        issues.append("cost.max_turns is required")
    if cost_data.get("on_exceeded") not in ["stop", "warn", "escalate"]:
        issues.append("cost.on_exceeded must be 'stop', 'warn', or 'escalate'")
    # context_warning_threshold must be 0-1 if specified
    threshold = cost_data.get("context_warning_threshold")
    if threshold is not None and (threshold < 0 or threshold > 1):
        issues.append("cost.context_warning_threshold must be between 0 and 1")
```

#### Error Response (LLM-Actionable)

```json
{
  "valid": false,
  "issues": [
    "No <cost> tag found in directive metadata. Add a <cost> tag inside <metadata> with at least max_turns and on_exceeded. Example: <cost><max_turns>30</max_turns><on_exceeded>escalate</on_exceeded></cost>"
  ]
}
```

**No defaults for required fields.** Strict enforcement with helpful error messages, matching how we already handle `<permissions>`, `<model>`, and `version`.

#### Runtime Cost and Context Enforcement

Cost and context enforcement runs in the harness after each LLM turn:

1. **Harness extracts budgets** from directive `<cost>` metadata
2. **Each LLM call reports usage** via token counts in response
3. **Harness checks all budgets** after each turn
4. **Termination on ANY limit exceeded** (OR logic):
   - **Cost budget**: Total tokens or USD spent across all turns
   - **Context budget**: Input tokens (context window usage)
   - **Turn limit**: Number of LLM calls made
5. **Context warning injected** when threshold reached (e.g., 80%)
6. **On exceeded**: Take action per `on_exceeded` setting

```python
# In safety_harness after each LLM turn
usage = parser.get_usage()

# Check cost budget (tokens, USD, turns)
cost_exceeded = self.cost_tracker.check_exceeded(usage, self.turn_count)

# Check context budget (prevents exceeding model context window)
context_result = self.context_budget.check_context(usage.input_tokens)

# Termination check: ANY limit exceeded = terminate
if cost_exceeded:
    reason = cost_exceeded  # e.g., "max_turns", "max_total_tokens", "max_cost_usd"
    if self.cost_budget.on_exceeded == "stop":
        return HarnessResult(status="cost_exceeded", reason=reason)
    elif self.cost_budget.on_exceeded == "warn":
        logger.warning(f"Cost budget exceeded: {reason}")
    elif self.cost_budget.on_exceeded == "escalate":
        await self.help(action="escalate", reason=f"cost_exceeded: {reason}")

if context_result.exceeded:
    # Context exceeded is always fatal (can't continue if context is full)
    return HarnessResult(status="context_exceeded", reason=context_result.message)
elif context_result.warning:
    # Inject warning into next LLM call
    self._inject_context_warning(context_result.message)
```

#### Context Warning Messages

When context usage approaches the limit, the harness injects a warning:

```
⚠️ CONTEXT LIMIT WARNING ⚠️
Current context usage: 144,000 / 180,000 tokens (80.0%)
Remaining: 36,000 tokens

Consider:
- Completing current task and ending conversation
- Using help(action="checkpoint") to save progress
- Spawning a sub-thread for remaining work
```

If context is exceeded:

```
❌ CONTEXT LIMIT EXCEEDED ❌
Context usage has exceeded the limit: 185,000 / 180,000 tokens
Thread must terminate. Use help(action="checkpoint") or complete immediately.
```

This keeps cost tracking in the **harness** (not kernel), consistent with our architecture.

---

### A.5: Thread Registry Persistence

Use **SQLite** as source-of-truth registry with **JSONL transcripts** for human-readable logs.

**Important:** The `thread_registry` is implemented as a **privileged internal tool** used by the harness. It is NOT subject to directive permission checks - the harness infrastructure needs it to function.

```yaml
# .ai/tools/threads/thread_registry.yaml
tool_id: thread_registry
tool_type: runtime
executor_id: python # Runtime tool using SQLite
config:
  db_path: ".ai/threads/registry.db"
  transcript_dir: ".ai/threads/transcripts"
# Note: This is a privileged harness tool
# Directives cannot call it directly; only safety_harness can
```

#### Why SQLite Over JSON Files

| Concern          | JSON Files                                      | SQLite                                             |
| ---------------- | ----------------------------------------------- | -------------------------------------------------- |
| Concurrency      | File locks, race conditions across subprocesses | WAL mode handles multi-process well                |
| Integrity        | Partial writes corrupt                          | Transactions, constraints                          |
| Queries          | Scan files, slow                                | Indexes, "threads by directive", "recent failures" |
| Schema evolution | Painful migrations                              | Standard ALTER/migrations                          |

opencode learned this: file locking + concurrent writes become the real complexity, not JSON parsing.

#### Hybrid Design

**1. SQLite Registry (raw storage)**

```sql
-- threads table
CREATE TABLE threads (
    thread_id TEXT PRIMARY KEY,
    directive_id TEXT NOT NULL,
    parent_thread_id TEXT,
    status TEXT NOT NULL,  -- running, paused, completed, error
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    permission_context_json TEXT,
    cost_budget_json TEXT,
    total_usage_json TEXT
);

-- events table (append-only for audit)
CREATE TABLE thread_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT,
    FOREIGN KEY (thread_id) REFERENCES threads(thread_id)
);

CREATE INDEX idx_events_thread ON thread_events(thread_id, ts);
CREATE INDEX idx_threads_directive ON threads(directive_id, created_at);
```

**2. JSONL Transcripts (human-readable)**

File per thread: `.ai/threads/{thread_id}/transcript.jsonl`

```jsonl
{"ts":"2026-01-25T10:00:00Z","type":"turn_start","turn":1}
{"ts":"2026-01-25T10:00:01Z","type":"user_message","content":"Deploy v1.2.3 to staging"}
{"ts":"2026-01-25T10:00:05Z","type":"assistant_message","content":"I'll check the version first..."}
{"ts":"2026-01-25T10:00:05Z","type":"tool_call","tool":"execute","args_hash":"abc123"}
{"ts":"2026-01-25T10:00:07Z","type":"tool_result","tool":"execute","success":true}
{"ts":"2026-01-25T10:00:10Z","type":"cost_update","input_tokens":1234,"output_tokens":567}
{"ts":"2026-01-25T10:00:15Z","type":"turn_end","turn":1}
```

Append-only to avoid corruption. Include:

- User/assistant messages
- Tool calls with args hash (not full args to avoid secrets)
- Tool result summaries
- Cost increments
- Stream errors

---

### A.6: External MCP Integration & Tool Discovery

**Note:** This appendix expands on Layer 7 above. Layer 7 covers the base MCP primitives (`mcp_stdio`, `mcp_http`); this section details the connector pattern and generated tool schemas.

External MCPs (like Supabase, GitHub, etc.) integrate through a two-layer tool system that maintains our permission model.

#### MCP Discovery Tool Pattern

For each external MCP, we create two tools:

1. **Connector tool** - Establishes connection, runs `tools/list`, generates child tool schemas
2. **Generated tool schemas** - One per MCP tool, with proper `requires` capabilities

The connector is **executed by the user or a directive** (not automatically). This gives full control over when MCP tools are discovered and integrated.

```
.ai/tools/mcp/
├── supabase_connector.yaml    # Discovery/connection tool (run manually or via directive)
├── supabase_query.yaml        # Generated: individual MCP tool
├── supabase_migrate.yaml      # Generated: individual MCP tool
└── ...
```

#### Connector Tool Example

```yaml
# .ai/tools/mcp/supabase_connector.yaml
tool_id: supabase_connector
tool_type: mcp_connector
executor_id: python
version: "1.0.0"

config:
  mcp_url: "https://mcp.supabase.com/mcp"
  auth:
    type: bearer
    token: "${SUPABASE_SERVICE_KEY}"
  output_dir: ".ai/tools/mcp/"
  tool_prefix: "supabase_"

requires:
  - mcp.connect # Permission to connect to external MCPs

retry:
  max_attempts: 3
  backoff_ms: [250, 1000, 3000]
```

When run, this:

1. Connects to the MCP
2. Calls `tools/list` to discover available tools
3. Generates individual tool YAML files with proper `requires` capabilities
4. Signs the generated tools

#### Generated Tool Example

```yaml
# .ai/tools/mcp/supabase_query.yaml (GENERATED)
tool_id: supabase_query
tool_type: mcp_tool
executor_id: mcp_http
version: "1.0.0"

config:
  mcp_url: "https://mcp.supabase.com/mcp"
  mcp_tool: "query" # The actual MCP tool name

requires:
  - db.query # Capability required to use this tool
  - mcp.supabase # Specific MCP capability

input_schema:
  # ... copied from MCP's tools/list response
```

#### Permission Integration

MCP tools integrate with our capability system:

- **Connector requires** `mcp.connect` capability
- **Generated tools require** appropriate capabilities (e.g., `db.query`, `db.migrate`)
- **Directive permissions** must grant these capabilities
- **Harness validates** before allowing execution

#### Reconnection & Updates

MCP connectors are **tools**, not automatic background processes. They run when explicitly called:

**Manual execution:**

```bash
# User runs connector directly
execute(tool, run, supabase_connector, {})
```

**Directive execution:**

```xml
<!-- In a setup/sync directive -->
<step name="sync_supabase_tools">
  <action>
    execute(tool, run, supabase_connector, {})
  </action>
</step>
```

**When to re-run:**

- MCP API changes (new tools added, schemas updated)
- Authentication credentials changed
- Manual request to refresh tool schemas

The connector tool itself manages:

1. Detecting schema changes (compare with existing generated tools)
2. Regenerating only changed tools
3. Re-signing all generated tools
4. Removing tools that no longer exist in MCP

#### Retry Configuration (Data-Driven)

```yaml
retry:
  max_attempts: 3
  backoff_ms: [250, 1000, 3000]
  retryable_errors:
    - CONNECTION_REFUSED
    - TIMEOUT
    - 503_SERVICE_UNAVAILABLE
```

#### Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "MCP_CONNECTION_FAILED",
    "message": "Failed to connect to external MCP server.",
    "endpoint": "https://mcp.supabase.com/mcp",
    "cause": "401 Unauthorized",
    "retryable": false,
    "remediation": "Re-authenticate or update SUPABASE_SERVICE_KEY."
  }
}
```

---

### A.7: Sink Architecture & Implementations

Sinks enable flexible output routing for streaming HTTP responses. All sinks (except `return`) are data-driven Python tools, following the same pattern as extractors and capabilities.

#### Sink Types Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           STREAMING SINK TOOLS                               │
│                                                                              │
│  Built-in (http_client):           Data-Driven Tools (.ai/tools/sinks/):    │
│  ┌─────────────────────┐           ┌─────────────────────────────────────┐  │
│  │   return            │           │   file_sink                         │  │
│  │   (memory buffer)   │           │   null_sink                         │  │
│  │                     │           │   websocket_sink                    │  │
│  └─────────────────────┘           └─────────────────────────────────────┘  │
│                                                                              │
│  Why data-driven?                                                            │
│  • Consistent with extractors, capabilities pattern                          │
│  • Dependencies managed by EnvManager (websockets, etc.)                     │
│  • Users can add custom sinks without modifying http_client                  │
│  • Configuration in YAML, implementation in Python                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Built-in: return Sink

The `return` sink buffers events for inclusion in the http_client result. It's built into http_client (not a separate tool) for simplicity:

```python
# kiwi_mcp/primitives/http_client.py

class ReturnSink:
    """Buffer events for inclusion in result. Built into http_client."""

    def __init__(self, max_size: int = 10000):
        self.buffer: List[str] = []
        self.max_size = max_size

    async def write(self, event: str) -> None:
        if len(self.buffer) < self.max_size:
            self.buffer.append(event)

    async def close(self) -> None:
        pass

    def get_events(self) -> List[str]:
        return self.buffer
```

#### Data-Driven: file_sink

Appends streaming events to disk in JSONL format. Used for transcript storage and audit logs.

**Tool Configuration:**

```yaml
# .ai/tools/sinks/file_sink.yaml
tool_id: file_sink
tool_type: runtime
executor_id: python
version: "1.0.0"
description: "Append streaming events to file in JSONL format"

config:
  module: "sinks.file_sink"
  format: jsonl
  flush_every: 10 # Flush after N events

parameters:
  - name: path
    type: string
    required: true
    description: "Output file path (supports {thread_id} template)"
```

**Python Implementation:**

```python
# .ai/tools/sinks/file_sink.py
__tool_type__ = "runtime"
__version__ = "1.0.0"
__executor_id__ = "python"
__category__ = "sinks"

import json
from pathlib import Path
from typing import Optional

class FileSink:
    """Append streaming events to file."""

    def __init__(self, path: str, format: str = "jsonl", flush_every: int = 10):
        self.path = Path(path)
        self.format = format
        self.flush_every = flush_every
        self.event_count = 0
        self.file_handle: Optional[io.TextIOWrapper] = None

        # Ensure parent directory exists
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def write(self, event: str) -> None:
        """Write event to file."""
        if not self.file_handle:
            self.file_handle = open(self.path, "a", encoding="utf-8")

        if self.format == "jsonl":
            # Parse SSE event and write as JSONL
            try:
                data = json.loads(event)
                self.file_handle.write(json.dumps(data) + "\n")
            except json.JSONDecodeError:
                # Write raw if not valid JSON
                self.file_handle.write(event + "\n")
        else:
            # Raw format
            self.file_handle.write(event + "\n")

        self.event_count += 1

        # Periodic flush for safety
        if self.event_count % self.flush_every == 0:
            self.file_handle.flush()

    async def close(self) -> None:
        """Close file handle."""
        if self.file_handle:
            self.file_handle.flush()
            self.file_handle.close()
            self.file_handle = None
```

#### Data-Driven: null_sink

Discards all events. Used for fire-and-forget streaming or performance testing.

**Tool Configuration:**

```yaml
# .ai/tools/sinks/null_sink.yaml
tool_id: null_sink
tool_type: runtime
executor_id: python
version: "1.0.0"
description: "Discard all streaming events (fire-and-forget)"

config:
  module: "sinks.null_sink"
```

**Python Implementation:**

```python
# .ai/tools/sinks/null_sink.py
__tool_type__ = "runtime"
__version__ = "1.0.0"
__executor_id__ = "python"
__category__ = "sinks"

class NullSink:
    """Discard all events."""

    async def write(self, event: str) -> None:
        """Discard event."""
        pass

    async def close(self) -> None:
        """No-op close."""
        pass
```

#### Data-Driven: websocket_sink

Forwards streaming events to a WebSocket endpoint in real-time. Used for thread intervention, live monitoring, and CLI streaming.

**Tool Configuration:**

```yaml
# .ai/tools/sinks/websocket_sink.yaml
tool_id: websocket_sink
tool_type: runtime
executor_id: python
version: "1.0.0"
description: "Forward streaming events to WebSocket endpoint"
dependencies: ["websockets"] # Managed by EnvManager

config:
  module: "sinks.websocket_sink"
  reconnect_attempts: 3
  buffer_on_disconnect: true
  buffer_max_size: 1000

parameters:
  - name: url
    type: string
    required: true
    description: "WebSocket endpoint URL (ws:// or wss://)"
```

**Python Implementation:**

```python
# .ai/tools/sinks/websocket_sink.py
__tool_type__ = "runtime"
__version__ = "1.0.0"
__executor_id__ = "python"
__category__ = "sinks"

# Dependencies handled by EnvManager
DEPENDENCIES = ["websockets"]

import asyncio
import json
from typing import List, Optional
import websockets

class WebSocketSink:
    """Forward events to WebSocket endpoint with reconnection support."""

    def __init__(
        self,
        url: str,
        reconnect_attempts: int = 3,
        buffer_on_disconnect: bool = True,
        buffer_max_size: int = 1000
    ):
        self.url = url
        self.reconnect_attempts = reconnect_attempts
        self.buffer_on_disconnect = buffer_on_disconnect
        self.buffer_max_size = buffer_max_size

        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.buffer: List[str] = []
        self.connected = False

    async def _connect(self) -> bool:
        """Establish WebSocket connection with retry."""
        for attempt in range(self.reconnect_attempts):
            try:
                self.ws = await websockets.connect(self.url)
                self.connected = True

                # Flush buffer if we have events
                if self.buffer:
                    for event in self.buffer:
                        await self.ws.send(event)
                    self.buffer.clear()

                return True
            except Exception as e:
                if attempt < self.reconnect_attempts - 1:
                    await asyncio.sleep(0.5 * (2 ** attempt))  # Exponential backoff
                continue

        return False

    async def write(self, event: str) -> None:
        """Write event to WebSocket."""
        # Ensure connection
        if not self.connected or not self.ws:
            if not await self._connect():
                if self.buffer_on_disconnect:
                    if len(self.buffer) < self.buffer_max_size:
                        self.buffer.append(event)
                return

        try:
            await self.ws.send(event)
        except websockets.ConnectionClosed:
            self.connected = False
            if self.buffer_on_disconnect:
                if len(self.buffer) < self.buffer_max_size:
                    self.buffer.append(event)

    async def close(self) -> None:
        """Close WebSocket connection."""
        if self.ws:
            await self.ws.close()
            self.ws = None
            self.connected = False
```

#### When to Use Each Sink

| Sink                | Use Case                                            | Configuration             |
| ------------------- | --------------------------------------------------- | ------------------------- |
| `return` (built-in) | Buffering for harness processing                    | Always explicit in config |
| `file_sink`         | Transcript storage, CI/CD logs, audit trail         | Path required             |
| `null_sink`         | Fire-and-forget calls, performance testing          | No config needed          |
| `websocket_sink`    | Thread intervention, live monitoring, CLI streaming | URL required              |

**Best Practice:** Always explicitly list `return` in destinations if the harness needs to process the stream. If `return` is not listed, the stream is purely side-effect based (file/websocket output only).

```yaml
# Example: Transcript + harness processing
stream:
  destinations:
    - type: file_sink
      path: ".ai/threads/{thread_id}/transcript.jsonl"
    - type: return  # Explicit: harness gets buffered events

# Example: Pure logging (no harness processing)
stream:
  destinations:
    - type: file_sink
      path: ".ai/threads/{thread_id}/transcript.jsonl"
    # No 'return' = harness gets empty body
```

#### Dependency Management with EnvManager

Runtime tools (like `websocket_sink`) that need external packages use the existing `EnvManager` (see `kiwi_mcp/utils/env_manager.py`):

- **Project venv**: `.ai/scripts/.venv/` - for project-specific tools
- **User venv**: `~/.ai/.venv/` - for user-space tools

Dependencies are declared in the tool YAML and installed on first use:

```python
# Tool declares what it needs
dependencies: ["websockets", "httpx"]

# EnvManager handles:
# 1. Creating venv if needed
# 2. Installing missing packages (with caching - see cache.py)
# 3. Running tool in correct venv context
```

This is the same system used for all Python runtime tools - no special handling for sinks.

#### WebSocket for Thread Intervention

The `websocket_sink` is used when **thread intervention tools** are active. Example use case:

1. Thread A is running a long deployment
2. Thread B (or a human) wants to monitor Thread A's progress in real-time
3. Thread A's configuration is updated to include `websocket_sink` pointing to an intervention endpoint
4. Thread B receives live stream of Thread A's activity

This is configured dynamically when intervention is requested:

```python
# In harness when intervention is requested
if intervention_requested:
    self.stream_destinations.append({
        "type": "websocket_sink",
        "config": {"url": intervention_ws_url}
    })
```

---

### A.8: Error Handling in Tool Chains

Tool chain errors include full context for debugging. A misconfig at `anthropic_messages` produces a single clear error showing the chain, config source, and root cause.

#### Error Wrapping Pattern

Each execution layer catches errors and rethrows with context:

```python
@dataclass
class ToolChainError(Exception):
    code: str
    message: str
    chain: List[str]  # ["anthropic_thread", "anthropic_messages", "http_client"]
    failed_at: FailedToolContext
    cause: Optional[Exception]

@dataclass
class FailedToolContext:
    tool_id: str
    config_path: str  # ".ai/tools/llm/anthropic_messages.yaml"
    validation_errors: List[ValidationError]
```

#### Example Error Response

```json
{
  "success": false,
  "error": {
    "code": "TOOL_CHAIN_FAILED",
    "message": "Tool chain failed at 'anthropic_messages': invalid config.",
    "chain": ["anthropic_thread", "anthropic_messages", "http_client"],
    "failed_at": {
      "tool_id": "anthropic_messages",
      "config_path": ".ai/tools/llm/anthropic_messages.yaml",
      "validation_errors": [
        { "field": "config.model", "error": "required" },
        { "field": "config.max_tokens", "error": "must be >= 1" }
      ]
    },
    "cause": {
      "code": "CONFIG_VALIDATION_ERROR",
      "message": "Missing required field 'model'"
    }
  }
}
```

#### Proactive Validation

Validate tool YAML configs at **load/registration time**, not just execution:

1. On MCP startup or tool discovery
2. Parse YAML, validate schema
3. Mark tool "unavailable" with clear diagnostic

This avoids confusing runtime failures mid-thread.

---

## Related Documents

- `RUNTIME_PERMISSION_DESIGN.md` - Permission enforcement architecture
- `KNOWLEDGE_SYSTEM_DESIGN.md` - RAG-based knowledge and help system (TODO)
- `SAFETY_HARNESS_ROADMAP.md` - Harness implementation details
