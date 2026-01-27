# Quick Start: Creating and Running Tools

## 5-Minute Setup

### 1. Create a Tool File

Create `.ai/tools/my_category/my_tool.py`:

```python
# kiwi-mcp:validated:0000000000000000000000000000000000000000000000000000000000000000
"""
My First Tool

Does something useful.
"""

__version__ = "1.0.0"
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "my_category"

def main(name: str = "World") -> dict:
    return {"message": f"Hello, {name}!"}

if __name__ == "__main__":
    print(main("Alice"))
```

### 2. Sign the Tool

```bash
# Get the actual hash
sha256sum <<< $(cat .ai/tools/my_category/my_tool.py | tail -n +2)

# Update the signature line with that hash
# kiwi-mcp:validated:2026-01-28T00:00:00Z:{YOUR_HASH}
```

### 3. Run the Tool

```python
# Via Python API
from kiwi_mcp.tools.execute import ExecuteTool

tool = ExecuteTool()
result = await tool.execute({
    "item_type": "tool",
    "action": "run",
    "item_id": "my_tool",
    "parameters": {"name": "Alice"},
    "project_path": "/path/to/project"
})
```

## Common Patterns

### Pattern 1: Get Input, Return Result

```python
def main(input_data: str) -> dict:
    """Process input and return result."""
    result = process(input_data)
    return {"status": "success", "data": result}
```

### Pattern 2: API Tool

```python
__tool_type__ = "api"
__executor_id__ = "http_client"

CONFIG = {
    "method": "POST",
    "url": "https://api.example.com/endpoint",
    "headers": {"Authorization": "Bearer ${API_KEY}"},
    "body_template": {"input": "{text}"}
}
```

### Pattern 3: Tool with Imports

```python
# These imports are auto-detected and tracked
import requests
import json
from datetime import datetime

def main(url: str) -> dict:
    response = requests.get(url)
    return response.json()
```

## File Structure

```
.ai/
└── tools/
    ├── primitives/
    │   ├── subprocess.py
    │   └── http_client.py
    ├── utility/
    │   ├── hello_world.py
    │   └── test_tool.py
    └── my_category/
        └── my_tool.py
```

## Metadata Fields (Required)

| Field | Example |
|-------|---------|
| `__version__` | `"1.0.0"` |
| `__tool_type__` | `"python"` or `"api"` |
| `__executor_id__` | `"python_runtime"` or `None` |
| `__category__` | `"utility"` or `"custom"` |
| Docstring | Multi-line description |

## Tool Types

| Type | Executor | Use Case |
|------|----------|----------|
| `primitive` | None | Built-in capabilities |
| `python` | `python_runtime` | Python scripts |
| `api` | `http_client` | HTTP API calls |
| `mcp_tool` | MCP server | Remote tools |

## Search Tools

```python
from kiwi_mcp.tools.search import SearchTool

search = SearchTool()
result = await search.execute({
    "item_type": "tool",
    "query": "hello",
    "source": "local",
    "project_path": "/path/to/project"
})
```

## Troubleshoot

| Problem | Solution |
|---------|----------|
| Tool not found | Check `.ai/tools/` exists and file is there |
| Signature error | Re-sign with correct hash |
| Import error | Add missing dependency to docstring |
| Execution failed | Test with `python tool.py` directly |

## Next Steps

- Read `README.md` for full documentation
- Check `.ai/tools/` for example tools
- Review `kiwi_mcp/handlers/tool/handler.py` for implementation
