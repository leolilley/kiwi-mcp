**Source:** Original implementation: `.ai/tools/rye/` bundled tools in kiwi-mcp

# RYE Category

## Purpose

The "rye" category contains **bundled tools** that ship with RYE. These are the core tools auto-installed when you `pip install rye-lilux`.

## What is "RYE" Category?

The **RYE category** is special because:

1. **Bundled with RYE package** - Included in `rye-lilux` PyPI distribution
2. **Auto-installed** - Users get these tools automatically
3. **Well-maintained** - Core tools maintained by RYE team
4. **Organized into 14 subcategories** - Different tool types under `.ai/tools/rye/`

## Relationship to Other Categories

| Category | Location | Bundled | Maintained |
|----------|----------|---------|-----------|
| **rye** | `.ai/tools/rye/` | ✓ Yes | RYE team |
| **python** | `.ai/tools/python/` | ✗ No | User |
| **Other** | `.ai/tools/{name}/` | ✗ No | User |

## RYE Subcategories

The `.ai/tools/rye/` directory contains 14 subcategories:

### 1. Primitives (2 execution primitives)
Base execution engines - `__executor_id__ = None`

See: [[primitives]]

### 2. Runtimes (3 tools)
Language runtimes - `__executor_id__` points to primitives

See: [[runtimes]]

### 3. Capabilities (6 tools)
System capabilities - git, filesystem, database, network, process, MCP

### 4. Telemetry (7 tools)
System monitoring and diagnostics

### 5. Extractors (3 subdirectories)
Data extraction - directive/, knowledge/, tool/

### 6. Parsers (4 tools)
Data format parsing

### 7. Protocol (1 tool)
Protocol implementations

### 8. Sinks (3 tools)
Event sinks

### 9. Threads (12 tools + YAML)
Async execution and threading

### 10. MCP (Tools + YAML)
MCP protocol tools

### 11. LLM (YAML configs)
LLM provider configurations

### 12. Registry (1 tool)
Registry operations

### 13. Utility (3 tools)
General utilities

### 14. Examples (2 tools)
Reference implementations

### 15. Python/Lib
Shared Python libraries

## Bundling and Distribution

### What Gets Bundled

When you install RYE:

```bash
pip install rye-lilux
```

You get:

1. **Lilux microkernel** - Execution primitives
2. **RYE OS layer** - Universal executor
3. **RYE `.ai/` bundle** - All 14 RYE tool categories

### How It's Packaged

```toml
# rye/pyproject.toml
[tool.setuptools]
packages = ["rye"]
package-data = { "rye" = [".ai/**/*"] }  # ← Bundle .ai/ content
```

All files in `rye/.ai/` are packaged and installed with RYE.

### Access in Installed Package

```python
import rye
import pkg_resources

# Access bundled tools
bundle_path = pkg_resources.resource_filename('rye', '.ai/tools/rye/')
```

## Tool Organization

All RYE tools are organized under `.ai/tools/rye/`:

```
.ai/tools/rye/
├── primitives/          # 2 execution primitive schemas
├── runtimes/            # 3 runtime schemas
├── capabilities/        # 6 system capability tools
├── telemetry/           # 7 telemetry tools
├── extractors/          # Data extraction tools
├── parsers/             # 4 parser tools
├── protocol/            # Protocol tools
├── sinks/               # 3 event sink tools
├── threads/             # 12 thread management tools
├── mcp/                 # MCP tools + configs
├── llm/                 # LLM configs (YAML)
├── registry/            # Registry operations tool
├── utility/             # 3 utility tools
├── examples/            # 2 example tools
└── python/
    └── lib/             # Shared Python libraries
```

## Metadata Pattern

All RYE tools follow the metadata pattern:

```python
__version__ = "X.Y.Z"
__tool_type__ = "primitive" | "runtime" | "python" | "python_lib"
__executor_id__ = None | "subprocess" | "python_runtime" | ...
__category__ = "primitives" | "runtimes" | "capabilities" | ...  # Subcategory
```

## Installation and Usage

### User Perspective

```bash
# Install RYE (gets both Lilux + RYE + all bundled tools)
pip install rye-lilux

# Configure for Claude Desktop
{
  "mcpServers": {
    "rye": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "rye.server"],
      "enabled": true
    }
  }
}

# Start chatting - all RYE tools available
```

### Developer Perspective

```python
# In your tool
__executor_id__ = "python_runtime"  # Use RYE's Python runtime
__category__ = "capabilities"       # Put in capabilities category

def main(command: str) -> dict:
    """Your implementation."""
    pass
```

## Key Characteristics of RYE Category

| Aspect | Detail |
|--------|--------|
| **What** | Core tools bundled with RYE |
| **Location** | `.ai/tools/rye/` |
| **Distribution** | Included in `rye-lilux` PyPI package |
| **Subcategories** | 14 different tool groups |
| **Total Tools** | ~80+ tools + configs |
| **Maintainer** | RYE team |
| **User Category** | Installed automatically |
| **Extensibility** | Users create tools in other categories |

## Extending RYE

Users extend RYE by creating tools in OTHER categories:

```
.ai/tools/
├── rye/              # Bundled (auto-installed)
│   ├── primitives/
│   ├── capabilities/
│   └── ...
│
└── myproject/        # User category (custom tools)
    ├── my_tool_1.py
    └── my_tool_2.py
```

All tools (RYE and user-defined) are auto-discovered by the universal executor.

## Comparison: RYE vs Other Categories

### RYE Category (`.ai/tools/rye/`)
```
✓ Bundled with RYE
✓ Auto-installed
✓ Team-maintained
✓ Well-tested
✓ 14 subcategories
✓ ~80+ tools
```

### Python Category (`.ai/tools/python/`)
```
✗ Not bundled
✗ User-created
✗ User-maintained
✓ Good for Python tools
```

### User Categories (`.ai/tools/{user}/`)
```
✗ Not bundled
✓ Completely user-defined
✓ Flexible organization
```

## Related Documentation

- [[primitives]] - Layer 1: Base executors
- [[runtimes]] - Layer 2: Language runtimes
- [[capabilities]] - System capabilities
- [[telemetry]] - Telemetry tools
- [[overview]] - All categories
- [[../bundle/structure]] - Bundle organization
