# Kiwi MCP Tooling Guide - Corrected Implementation

**Date:** 2026-01-28  
**Status:** Current Implementation  
**Purpose:** Correct documentation based on actual code implementation

---

## Overview

Kiwi MCP provides **4 unified MCP tools** for managing directives, scripts, and knowledge:

| Tool | Purpose |
|------|---------|
| **search** | Find directives, tools, or knowledge entries (local only) |
| **load** | Load/read items from local storage |
| **execute** | Run or sign items |
| **help** | Get usage guidance |

---

## Key Differences from Documentation

The previous documentation was **incorrect**. Here's what's actually implemented:

### ❌ What's NOT implemented:
- No database (`tools`, `tool_versions`, `tool_version_files` tables) - these are future planned
- No registry support for tools (local-only operations currently)
- No `create` or `publish` actions for tools in the execute tool
- No separate MCP server management
- No automatic venv creation or dependency installation

### ✅ What IS implemented:
- **Python file-based tools** with metadata headers
- **Simple executor chain** using `__executor_id__` references
- **4 primitive tool types**: `primitive`, `python`, `api`, `mcp_tool`
- **Signature validation** using content hashing
- **Local file operations** only (`.ai/tools/` and `~/.ai/tools/`)
- **Metadata extraction** from Python docstrings and `__*__` variables

---

## How Tools Are Actually Structured

Tools are **Python files** with metadata headers, not stored in a database.

### Basic Tool Structure

```python
# kiwi-mcp:validated:2026-01-26T01:26:37Z:8f7b8d4ecf4d095f681cda272e62b81a8d8571a7877ac37790eae3b03f6b2e4b
"""
Tool Name

Description of what this tool does.

Config Schema:
- param1 (type): Description
- param2 (type): Description
"""

__version__ = "1.0.0"
__tool_type__ = "python"           # primitive, python, api, mcp_tool
__executor_id__ = "python_runtime"  # References another tool, NULL for primitives
__category__ = "utility"

def main(param1: str, param2: int = 10) -> dict:
    """
    Main function that runs when tool is executed.
    
    Args:
        param1: Description
        param2: Description
    
    Returns:
        Dictionary with results
    """
    result = {"status": "success", "data": param1}
    return result

if __name__ == "__main__":
    # For direct execution during development
    result = main("test")
    print(result)
```

### Required Metadata Fields

Every tool MUST have:

| Field | Type | Purpose |
|-------|------|---------|
| `__version__` | str | Semantic version (e.g., "1.0.0") |
| `__tool_type__` | str | Type: `primitive`, `python`, `api`, or `mcp_tool` |
| `__executor_id__` | str or None | Points to executor tool (NULL for primitives) |
| `__category__` | str | Category for organization (e.g., "utility", "primitives") |
| Docstring | str | Tool description and config schema |

### The Signature Header

The first line must be a **signature comment**:

```python
# kiwi-mcp:validated:2026-01-26T01:26:37Z:8f7b8d4ecf4d095f681cda272e62b81a8d8571a7877ac37790eae3b03f6b2e4b
```

Format: `# kiwi-mcp:validated:{ISO_TIMESTAMP}Z:{SHA256_HASH}`

This validates file integrity. See [Signature Validation](#signature-validation) below.

---

## Tool Types

### 1. Primitives

Hard-coded implementations that execute directly. No executor chain below them.

```python
__tool_type__ = "primitive"
__executor_id__ = None  # MUST be None

# Examples: subprocess, http_client
```

**Examples:**
- `subprocess.py` - Spawns shell commands
- `http_client.py` - Makes HTTP requests

### 2. Python Tools

Executable Python scripts that use the `python_runtime` executor.

```python
__tool_type__ = "python"
__executor_id__ = "python_runtime"

def main(name: str) -> str:
    return f"Hello, {name}!"
```

**Location:** `.ai/tools/` or `~/.ai/tools/`  
**Execution:** Via PrimitiveExecutor → python_runtime → subprocess

### 3. API Tools

Direct HTTP API calls via the `http_client` primitive.

```python
__tool_type__ = "api"
__executor_id__ = "http_client"

CONFIG = {
    "method": "GET",
    "url": "https://api.example.com/endpoint",
    "timeout": 10,
    "headers": {"Authorization": "Bearer ${API_KEY}"}
}
```

### 4. MCP Tools

Tools exposed by an MCP server (future implementation).

```python
__tool_type__ = "mcp_tool"
__executor_id__ = "supabase_mcp"  # References an MCP server

CONFIG = {
    "mcp_tool_name": "execute_sql"
}
```

---

## Creating Tools

### Step 1: Create the Python File

Create a new file in `.ai/tools/category/your_tool.py`:

```python
# kiwi-mcp:validated:2026-01-28T00:00:00Z:0000000000000000000000000000000000000000000000000000000000000000
"""
My Custom Tool

Describes what this tool does.

Config Schema:
- input_text (str): The text to process
"""

__version__ = "1.0.0"
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "custom"

def main(input_text: str) -> dict:
    """
    Process input text.
    
    Args:
        input_text: Text to process
    
    Returns:
        Dictionary with results
    """
    processed = input_text.upper()
    return {"original": input_text, "processed": processed}

if __name__ == "__main__":
    result = main("hello world")
    print(result)
```

### Step 2: Sign the Tool

Before running, sign the tool to validate it:

```bash
# Using Kiwi MCP tools
kiwi-mcp-tool execute tool my_tool sign --project_path /path/to/project
```

Or via the MCP execute tool:

```json
{
  "item_type": "tool",
  "action": "sign",
  "item_id": "my_tool",
  "project_path": "/path/to/project"
}
```

This will:
1. Validate the Python syntax
2. Extract and validate metadata
3. Calculate SHA256 hash of content
4. Update the signature line

### Step 3: Run the Tool

```json
{
  "item_type": "tool",
  "action": "run",
  "item_id": "my_tool",
  "parameters": {
    "input_text": "hello"
  },
  "project_path": "/path/to/project"
}
```

---

## Executor Chain

Tools form a chain from bottom to top:

```
my_python_tool (python)
    ↓ executor_id
python_runtime (runtime)
    ↓ executor_id
subprocess (primitive)
    ↓ (hard-coded)
[EXECUTES: Python interpreter]
```

### Resolving Chains

The `PrimitiveExecutor` walks the chain:

```python
1. Resolve tool "my_python_tool"
   → __executor_id__ = "python_runtime"
   
2. Resolve tool "python_runtime"
   → __executor_id__ = "subprocess"
   
3. Resolve tool "subprocess"
   → __executor_id__ = None (PRIMITIVE)
   → Execute directly
```

---

## Signature Validation

### How Signatures Work

The signature header validates file integrity:

```python
# kiwi-mcp:validated:{TIMESTAMP}Z:{SHA256_HASH}
```

- **TIMESTAMP**: ISO 8601 format when signed
- **HASH**: SHA256 of file content (excluding signature line)

### Creating/Updating Signatures

Sign a tool using the execute tool:

```python
async def execute(
    item_type="tool",
    action="sign",
    item_id="my_tool",
    project_path="/path/to/project"
)
```

The system will:
1. Read the file
2. Calculate SHA256
3. Update or create the signature line
4. Validate the file structure

### Validation During Execution

When running a tool:
1. Read signature from first line
2. Calculate current hash
3. Compare with stored hash
4. Reject if mismatch (file was modified)

---

## Search and Discovery

### Search Local Tools

```json
{
  "item_type": "tool",
  "query": "http api request",
  "source": "local",
  "limit": 10,
  "project_path": "/path/to/project"
}
```

Returns:
- Tools matching query keywords
- Score based on relevance
- Metadata (name, description, category)
- File paths

### Search Algorithm

1. **Keyword matching** - Split query into words
2. **Relevance scoring** - Match against tool name + description
3. **Deduplication** - Remove duplicates by tool ID
4. **Sorting** - By relevance score, date, or name

---

## Tool Locations

| Type | Project | User |
|------|---------|------|
| Python Tools | `.ai/tools/` | `~/.ai/tools/` |
| Tool Search Dirs | `.ai/tools/` | `~/.ai/tools/` |

**Search Priority:**
1. Project tools (`.ai/tools/`)
2. User tools (`~/.ai/tools/`)

First match wins during resolution.

---

## Metadata Extraction

The `extract_tool_metadata()` function parses tools:

```python
from kiwi_mcp.schemas import extract_tool_metadata

meta = extract_tool_metadata(file_path, project_path)
# Returns: {
#   "name": "my_tool",
#   "description": "...",
#   "version": "1.0.0",
#   "tool_type": "python",
#   "executor_id": "python_runtime",
#   "category": "custom"
# }
```

**Extracts from:**
- Docstring (description)
- `__version__` variable
- `__tool_type__` variable
- `__executor_id__` variable
- `__category__` variable
- File path (tool name)

---

## Execution Flow

### 1. Resolve Tool

```python
resolver = ToolResolver(project_path)
file_path = resolver.resolve("my_tool")
# Returns path or None if not found
```

### 2. Extract Metadata

```python
meta = extract_tool_metadata(file_path, project_path)
# Validates structure and extracts all metadata
```

### 3. Build Executor Chain

```python
executor = PrimitiveExecutor(project_path)
chain = executor.build_chain("my_tool")
# Returns: [my_tool, python_runtime, subprocess]
```

### 4. Execute

```python
result = await executor.execute(
    tool_id="my_tool",
    action="run",
    parameters={"input_text": "hello"}
)
```

---

## Examples

### Example 1: Simple Python Tool

```python
# kiwi-mcp:validated:2026-01-28T00:00:00Z:0000000000000000000000000000000000000000000000000000000000000000
"""
Text Uppercase Tool

Converts text to uppercase.

Config Schema:
- text (str): Text to convert
"""

__version__ = "1.0.0"
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "text"

def main(text: str) -> dict:
    """Convert text to uppercase."""
    return {"input": text, "output": text.upper()}

if __name__ == "__main__":
    result = main("hello world")
    print(result)
```

### Example 2: API Tool

```python
# kiwi-mcp:validated:2026-01-28T00:00:00Z:0000000000000000000000000000000000000000000000000000000000000000
"""
Weather API Tool

Fetches weather for coordinates.

Config Schema:
- lat (number): Latitude
- lon (number): Longitude
"""

__version__ = "1.0.0"
__tool_type__ = "api"
__executor_id__ = "http_client"
__category__ = "weather"

CONFIG = {
    "method": "GET",
    "url_template": "https://api.weather.com/forecast?lat={lat}&lon={lon}",
    "timeout": 10,
    "headers": {
        "Authorization": "Bearer ${WEATHER_API_KEY}"
    }
}
```

### Example 3: Tool with Dependencies

```python
# kiwi-mcp:validated:2026-01-28T00:00:00Z:0000000000000000000000000000000000000000000000000000000000000000
"""
Data Analysis Tool

Analyzes CSV files using pandas.

Config Schema:
- csv_path (str): Path to CSV file
"""

__version__ = "1.0.0"
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "data"

# Dependencies will be auto-detected from imports
import pandas as pd
import numpy as np

def main(csv_path: str) -> dict:
    """Analyze CSV file."""
    df = pd.read_csv(csv_path)
    return {
        "rows": len(df),
        "columns": list(df.columns),
        "dtypes": df.dtypes.to_dict()
    }

if __name__ == "__main__":
    result = main("data.csv")
    print(result)
```

---

## Current Limitations

1. **No Database:** Tools stored as files, not in DB (future planned)
2. **Local Only:** No registry support for tools yet
3. **No Publishing:** Cannot publish tools to registry
4. **No Auto-Dependency Install:** Must declare dependencies in docstring
5. **No Venv Isolation:** Python tools run in system environment
6. **No Tool Creation API:** Must manually create files

---

## Future Roadmap

Based on `UNIFIED_TOOLS_ARCHITECTURE.md`:

1. **Phase 1: Database Tables**
   - `tools` - Tool registry
   - `tool_versions` - Versioned manifests
   - `tool_version_files` - Implementation files

2. **Phase 2: Full Executor Pattern**
   - All tool types (primitives, runtimes, MCP servers, MCP tools, scripts)
   - Complete chain resolution

3. **Phase 3: Tool Management**
   - Create/publish tools via API
   - Registry sync
   - Dependency management

4. **Phase 4: Advanced Features**
   - Venv isolation per tool
   - Auto-dependency installation
   - Thread spawning with permissions
   - Knowledge as tools

---

## Troubleshooting

### Tool Not Found

**Problem:** `Tool 'my_tool' not found locally`

**Solution:**
1. Check file exists: `.ai/tools/my_tool.py`
2. File must be executable Python
3. Use full path with category if needed: `category/my_tool`

### Signature Validation Failed

**Problem:** `Content hash mismatch`

**Solution:**
1. Re-sign the tool: `execute action=sign`
2. Check for hidden whitespace/encoding issues
3. Verify file wasn't modified after signing

### Execution Failed

**Problem:** Tool runs but returns error

**Solution:**
1. Check parameters match function signature
2. Verify Python syntax: `python -m py_compile tool.py`
3. Check dependencies are available

### Import Errors

**Problem:** `ModuleNotFoundError`

**Solution:**
1. Add imports to docstring for auto-detection
2. Install dependencies manually: `pip install package`
3. Check PYTHONPATH includes `.ai/tools/lib/`

---

## Best Practices

1. **Always include docstrings** - Used for metadata extraction
2. **Use semantic versioning** - Follow `X.Y.Z` format
3. **Sign before running** - Validates integrity
4. **Test locally first** - Run directly with `python tool.py`
5. **Add to category** - Organize tools in subdirectories
6. **Keep main() pure** - Avoid side effects
7. **Return JSON-serializable** - Results must be JSON-compatible

---

## See Also

- `UNIFIED_TOOLS_ARCHITECTURE.md` - Future architecture
- `kiwi_mcp/handlers/tool/handler.py` - Implementation
- `kiwi_mcp/primitives/executor.py` - Executor logic
- `kiwi_mcp/schemas.py` - Metadata extraction
