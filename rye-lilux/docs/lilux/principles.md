**Source:** Original implementation: `kiwi_mcp/` package structure in kiwi-mcp

# Lilux Microkernel Principles

## What is Lilux?

Lilux is a **microkernel** for AI agent systems. It provides generic execution primitives without any domain intelligence. Like a CPU provides instruction execution, Lilux provides tool execution—nothing more.

## The Microkernel Analogy: Lilux vs RYE

Just as a computer has:

- **Hardware Microkernel** → executes instructions, manages memory, handles IO
- **Operating System** → understands file systems, user permissions, application APIs

Lilux and RYE have:

- **Lilux (Microkernel)** → executes code, makes HTTP calls, manages locks, stores secrets
- **RYE (OS Layer)** → understands directives, parses XML, validates schemas, routes to tools

| Aspect             | Lilux (Microkernel)          | RYE (OS)                               |
| ------------------ | ---------------------------- | -------------------------------------- |
| **What**           | Generic execution primitives | Universal executor + data-driven tools |
| **Analogy**        | Hardware CPU                 | Operating system kernel                |
| **Intelligence**   | Dumb - just executes         | Smart - understands content shapes     |
| **Package**        | `lilux` library              | `rye-lilux` application                |
| **Entry Point**    | None (library dependency)    | `python -m rye.server`                 |
| **Responsibility** | Execute what's told          | Understand and orchestrate             |
| **MCP Tools**      | `mcp__lilux__*`              | `mcp__rye__*`                          |

## Core Principle: Separation of Concerns

### Lilux's Responsibility (Microkernel Layer)

Lilux provides **execution primitives only**:

- Execute subprocess commands in isolated environments
- Make HTTP requests with retry logic and auth
- Manage file locks and concurrency
- Store credentials securely in keychains
- Validate execution chain integrity
- **NO content intelligence**

Lilux never touches:

- XML parsing
- Metadata understanding
- Schema validation
- Configuration loading
- Tool discovery

### RYE's Responsibility (OS Layer)

RYE provides **content understanding and orchestration**:

- Parse and validate directive XML
- Understand tool metadata and schemas
- Validate knowledge frontmatter
- Load and interpret YAML configurations
- Discover and route to appropriate tools
- **ALL content intelligence**

## Why This Separation Matters

This design enables:

1. **Lilux as a library:** Any agent system can use Lilux, not just RYE
2. **Minimal microkernel:** Lilux stays under 5KB of core logic
3. **Smart OS layer:** RYE can evolve without touching Lilux
4. **Clear security boundaries:** Lilux handles auth/secrets safely, RYE handles logic

## Installation and Usage

```bash
# Lilux is installed as a library dependency
pip install lilux
```

Lilux is **not a standalone server**. It's a library used by RYE and other systems. To use Lilux:

```python
from lilux.primitives import SubprocessPrimitive
from lilux.runtime import AuthStore, EnvResolver

# Use primitives directly
subprocess_prim = SubprocessPrimitive(config={})
result = subprocess_prim.execute(command="echo hello")
```

RYE embeds and orchestrates Lilux:

```bash
# Start RYE (which uses Lilux internally)
python -m rye.server
```

## What Lilux Does NOT Do

❌ **Lilux does NOT understand:**

- XML format of directives
- Metadata of tools
- Frontmatter of knowledge
- YAML configurations
- Tool discovery or routing
- Content parsing or validation

✅ **All of this lives in RYE's handlers:** `[[rye/categories/primitives]]`, `[[rye/content-handlers/overview]]`

