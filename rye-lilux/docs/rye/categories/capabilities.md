**Source:** Original implementation: `.ai/tools/rye/capabilities/` in kiwi-mcp

# Capabilities Category

## Purpose

Capabilities are **system feature providers** that expose operating system and infrastructure capabilities to users and tools.

**Location:** `.ai/tools/rye/capabilities/`  
**Count:** 6 tools  
**Executor:** All use `python_runtime`

## Core Capabilities

### 1. Git (`git.py`)

**Purpose:** Execute git commands

```python
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "capabilities"

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "command": {"type": "string", "description": "git command (clone, pull, push, etc.)"},
        "args": {"type": "array", "items": {"type": "string"}},
        "repo": {"type": "string", "description": "Repository path"},
    },
    "required": ["command"]
}
```

**Typical Operations:**
- `git clone <url>`
- `git pull`
- `git push`
- `git status`
- `git log`

### 2. Filesystem (`fs.py`)

**Purpose:** Filesystem operations

```python
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "capabilities"

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "operation": {"type": "string", "enum": ["read", "write", "delete", "list", "mkdir"]},
        "path": {"type": "string"},
        "content": {"type": "string"},  # For write
        "recursive": {"type": "boolean", "default": False},
    },
    "required": ["operation", "path"]
}
```

**Typical Operations:**
- Read file
- Write file
- Delete file/directory
- List directory
- Create directory

### 3. Database (`db.py`)

**Purpose:** Database operations

```python
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "capabilities"

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "operation": {"type": "string", "enum": ["query", "execute", "create", "drop"]},
        "connection": {"type": "string"},
        "sql": {"type": "string"},
        "params": {"type": "object"},
    },
    "required": ["operation", "sql"]
}
```

**Typical Operations:**
- Execute SQL query
- Insert/update/delete
- Create/drop tables
- Database transactions

### 4. Network (`net.py`)

**Purpose:** Network operations

```python
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "capabilities"

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "operation": {"type": "string", "enum": ["ping", "dns", "port_scan", "traceroute"]},
        "target": {"type": "string"},
        "timeout": {"type": "integer", "default": 10},
    },
    "required": ["operation", "target"]
}
```

**Typical Operations:**
- Ping host
- DNS resolution
- Port scanning
- Network diagnostics

### 5. Process (`process.py`)

**Purpose:** Process management

```python
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "capabilities"

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "operation": {"type": "string", "enum": ["list", "kill", "info", "start", "stop"]},
        "pid": {"type": "integer"},
        "name": {"type": "string"},
    },
}
```

**Typical Operations:**
- List running processes
- Get process information
- Kill/stop process
- Monitor resource usage

### 6. MCP (`mcp.py`)

**Purpose:** MCP protocol operations

```python
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "capabilities"

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "operation": {"type": "string", "enum": ["call", "subscribe", "unsubscribe", "list_resources"]},
        "resource": {"type": "string"},
        "method": {"type": "string"},
        "params": {"type": "object"},
    },
    "required": ["operation"]
}
```

**Typical Operations:**
- Call MCP resource
- Subscribe to events
- List available resources
- Unsubscribe from events

## Metadata Pattern

All capabilities follow this pattern:

```python
# .ai/tools/rye/capabilities/{name}.py

__version__ = "1.0.0"
__tool_type__ = "python"
__executor_id__ = "python_runtime"  # All use Python runtime
__category__ = "capabilities"       # All in capabilities

CONFIG_SCHEMA = { ... }

def main(**kwargs) -> dict:
    """Capability implementation."""
    pass
```

## Usage Examples

### Git Capability

```bash
Call git with:
  command: "status"
  repo: "/path/to/repo"
```

### Filesystem Capability

```bash
Call fs with:
  operation: "read"
  path: "/path/to/file.txt"
```

### Database Capability

```bash
Call db with:
  operation: "query"
  sql: "SELECT * FROM users WHERE id = ?"
  params: {"id": 123}
```

## Key Characteristics

| Aspect | Detail |
|--------|--------|
| **Count** | 6 tools |
| **Location** | `.ai/tools/rye/capabilities/` |
| **Executor** | All use `python_runtime` |
| **Purpose** | Expose system features |
| **Discoverability** | Auto-discovered |
| **Extensibility** | Add new capability → immediately available |

## Capability Relationships

```
User/Tool
    │
    ├─→ git capability (version control)
    ├─→ fs capability (file operations)
    ├─→ db capability (data operations)
    ├─→ net capability (network operations)
    ├─→ process capability (system processes)
    └─→ mcp capability (protocol operations)
```

## How Capabilities Work

### Execution Flow

```
Tool calls: git(command="status")
    │
    ├─→ RYE loads git.py from capabilities/
    ├─→ Sees __executor_id__ = "python_runtime"
    │
    ├─→ Load python_runtime metadata
    ├─→ Resolve environment (find Python, set vars)
    │
    └─→ Execute via subprocess:
        │
        python3 -c "
            import subprocess
            result = subprocess.run(['git', 'status'])
            return result
        "
```

## Related Documentation

- [[overview]] - All categories
- [[runtimes]] - Python runtime that all capabilities use
- [[../bundle/structure]] - Bundle organization
- [[../universal-executor/routing]] - How routing works
