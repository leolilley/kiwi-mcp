**Source:** Original implementation: `.ai/tools/rye/utility/` in kiwi-mcp

# Utility Category

## Purpose

Utility tools provide **general-purpose helpers** for common tasks.

**Location:** `.ai/tools/rye/utility/`  
**Count:** 3 tools  
**Executor:** Varies (http_client, python_runtime)

## Core Utility Tools

### 1. HTTP Test (`http_test.py`)

**Purpose:** Test HTTP requests and endpoints

```python
__tool_type__ = "python"
__executor_id__ = "http_client"
__category__ = "utility"

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]},
        "url": {"type": "string"},
        "headers": {"type": "object"},
        "body": {"type": "string"},
        "assert_status": {"type": "integer"},
        "assert_contains": {"type": "string"},
    },
    "required": ["method", "url"]
}
```

**Features:**
- Test HTTP endpoints
- Validate responses
- Check status codes
- Verify content

### 2. Hello World (`hello_world.py`)

**Purpose:** Simple demo/test tool

```python
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "utility"

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "default": "World"},
        "greeting": {"type": "string", "default": "Hello"},
    },
}
```

**Features:**
- Basic functionality test
- Sanity check tool
- Learning example

### 3. Test Proxy Pool (`test_proxy_pool.py`)

**Purpose:** Test proxy pool functionality

```python
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "utility"

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["test", "benchmark", "validate"]},
        "proxy_list": {"type": "array", "items": {"type": "string"}},
        "test_url": {"type": "string"},
        "timeout": {"type": "integer", "default": 10},
    },
    "required": ["action"]
}
```

**Features:**
- Test proxy connectivity
- Benchmark proxy performance
- Validate proxy configuration

## Metadata Pattern

All utility tools follow this pattern:

```python
# .ai/tools/rye/utility/{name}.py

__version__ = "1.0.0"
__tool_type__ = "python"
__executor_id__ = "http_client" | "python_runtime"
__category__ = "utility"

CONFIG_SCHEMA = { ... }

def main(**kwargs) -> dict:
    """Utility operation."""
    pass
```

## Usage Examples

### Test HTTP Endpoint

```bash
Call http_test with:
  method: "GET"
  url: "https://api.example.com/health"
  assert_status: 200
  assert_contains: "ok"
```

### Say Hello

```bash
Call hello_world with:
  name: "RYE"
  greeting: "Welcome to"
```

### Test Proxies

```bash
Call test_proxy_pool with:
  action: "benchmark"
  proxy_list:
    - "http://proxy1:8080"
    - "http://proxy2:8080"
  test_url: "https://example.com"
  timeout: 15
```

## Key Characteristics

| Aspect | Detail |
|--------|--------|
| **Count** | 3 tools |
| **Location** | `.ai/tools/rye/utility/` |
| **Executor** | Varies (http_client, python_runtime) |
| **Purpose** | General-purpose helpers |
| **Use Cases** | Testing, validation, demos |

## Related Documentation

- [[overview]] - All categories
- [[../bundle/structure]] - Bundle organization
