**Source:** Original implementation: `kiwi_mcp/primitives/http_client.py` in kiwi-mcp

# HttpClientPrimitive

## Purpose

Make HTTP requests with retry logic, authentication, streaming support, and comprehensive error handling.

## Key Classes

### HttpResult

Result of HTTP request execution:

```python
@dataclass
class HttpResult:
    success: bool                      # Whether request succeeded
    status_code: int                   # HTTP status code
    body: Any                          # Response body (JSON or text)
    headers: Dict[str, str]            # Response headers
    duration_ms: int                   # Total request time
    error: Optional[str] = None        # Error message if failed
    stream_events_count: Optional[int] = None  # For streaming mode
    stream_destinations: Optional[List[str]] = None  # Sinks used
```

### HttpClientPrimitive

The HTTP executor:

```python
class HttpClientPrimitive:
    async def execute(
        self, 
        config: Dict[str, Any], 
        params: Dict[str, Any]
    ) -> HttpResult:
        """Execute an HTTP request."""
```

## Configuration

### Required

- **`url`** (str): Target URL
  - Example: `"https://api.example.com/data"`

### Optional

- **`method`** (str): HTTP method
  - Default: `"GET"`
  - Values: `GET`, `POST`, `PUT`, `DELETE`, `PATCH`

- **`headers`** (dict): Request headers
  - Example: `{"Authorization": "Bearer token123", "Content-Type": "application/json"}`

- **`body`** (any): Request body
  - For POST/PUT: dict (serialized to JSON) or string
  - Example: `{"key": "value"}`

- **`retry_max`** (int): Maximum retries
  - Default: 3
  - Exponential backoff: 1s, 2s, 4s, etc.

- **`timeout`** (int): Request timeout in seconds
  - Default: 30
  - Example: `60`

- **`verify_ssl`** (bool): Verify SSL certificates
  - Default: `True`
  - Set to `False` only for testing

- **`auth_type`** (str): Authentication method
  - Values: `"bearer"`, `"api_key"`, `"basic"`, `"oauth2"`

- **`auth_token`** (str): Authentication token/key
  - For bearer: JWT token
  - For API key: API key value
  - For basic: base64 encoded credentials
  - For OAuth2: access token

## Example Usage

### Simple GET Request

```python
from lilux.primitives import HttpClientPrimitive

client = HttpClientPrimitive()

result = await client.execute(
    config={
        "url": "https://api.example.com/users"
    },
    params={}
)

assert result.success == True
assert result.status_code == 200
users = result.body  # Already parsed JSON
```

### POST with JSON Body

```python
result = await client.execute(
    config={
        "method": "POST",
        "url": "https://api.example.com/users",
        "body": {
            "name": "Alice",
            "email": "alice@example.com"
        }
    },
    params={}
)

assert result.success == True
assert result.status_code == 201
new_user = result.body
```

### With Authentication

```python
result = await client.execute(
    config={
        "method": "GET",
        "url": "https://api.example.com/private",
        "auth_type": "bearer",
        "auth_token": "eyJhbGc..."
    },
    params={}
)

assert result.success == True
```

### With Retries

```python
result = await client.execute(
    config={
        "method": "GET",
        "url": "https://flaky-api.example.com/data",
        "retry_max": 5,
        "timeout": 10
    },
    params={}
)

# Will retry on 5xx errors with exponential backoff
# If all retries fail, returns result.success=False
```

### Custom Headers

```python
result = await client.execute(
    config={
        "method": "POST",
        "url": "https://api.example.com/data",
        "headers": {
            "Authorization": "Bearer token123",
            "X-Custom-Header": "value",
            "Content-Type": "application/json"
        },
        "body": {"data": "payload"}
    },
    params={}
)
```

## Streaming Mode

HttpClientPrimitive supports streaming for long-running requests (Server-Sent Events, WebSockets):

### Streaming Configuration

```python
config = {
    "method": "POST",
    "url": "https://api.example.com/stream",
    "stream_config": {
        "transport": "sse",  # or "websocket"
        "destinations": [
            {
                "type": "return",  # Buffer in result
                "format": "jsonl"
            }
        ],
        "buffer_events": True,
        "max_buffer_size": 10000
    }
}

result = await client.execute(config, {})

# result.stream_events_count = 1234
# result.body = [event1, event2, ...]
```

### Streaming Destinations

- **`"return"`** - Built-in, buffers events in memory
- **`"file_sink"`** - Data-driven tool (writes to file)
- **`"null_sink"`** - Data-driven tool (discards events)
- **`"websocket_sink"`** - Data-driven tool (forwards to WebSocket)

See Appendix A.7 in architecture docs for sink configuration.

## Architecture Role

HttpClientPrimitive is part of the **Lilux microkernel execution layer**:

1. **Network abstraction** - Handles HTTP details
2. **Retry intelligence** - Exponential backoff, idempotency
3. **Auth abstraction** - Multiple auth schemes
4. **Streaming support** - SSE and WebSocket handling
5. **Dumb routing** - No content understanding

## RYE Relationship

RYE's universal executor calls HttpClientPrimitive when:
- Tool's `executor` field is `"http_client"`
- Tool's config defines an HTTP request

**Pattern:**
```python
# RYE does this
tool = get_tool("api_call_tool")
assert tool.executor == "http_client"

result = await http_client.execute(
    config=tool.config,
    params=rye_params
)
```

See `[[rye/categories/primitives]]` for tool definitions.

## Authentication Methods

### Bearer Token (JWT/OAuth)

```python
config = {
    "method": "GET",
    "url": "https://api.example.com/data",
    "auth_type": "bearer",
    "auth_token": "eyJhbGciOiJIUzI1NiIs..."
}

# Results in: Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### API Key

```python
config = {
    "method": "GET",
    "url": "https://api.example.com/data",
    "auth_type": "api_key",
    "auth_token": "sk_live_abc123..."
}

# Results in: X-API-Key: sk_live_abc123...
```

### Basic Auth

```python
config = {
    "method": "GET",
    "url": "https://api.example.com/data",
    "auth_type": "basic",
    "auth_token": "dXNlcm5hbWU6cGFzc3dvcmQ="  # base64
}

# Results in: Authorization: Basic dXNlcm5hbWU6cGFzc3dvcmQ=
```

### OAuth2

```python
config = {
    "method": "GET",
    "url": "https://api.example.com/data",
    "auth_type": "oauth2",
    "auth_token": "access_token_value"
}

# Results in: Authorization: Bearer access_token_value
```

## Retry Strategy

HttpClientPrimitive retries on:
- Network errors (connection refused, timeout, DNS)
- 5xx server errors (500, 502, 503, 504)
- Some 4xx errors (408, 429)

Retry strategy:
1. Wait 1 second, retry
2. Wait 2 seconds, retry
3. Wait 4 seconds, retry
4. ... exponential backoff
5. After max retries, return failure

```python
# Example with 3 retries (default)
# Total time: 1 + 2 + 4 = 7 seconds max
result = await client.execute(
    config={
        "url": "...",
        "retry_max": 3
    },
    params={}
)
```

## Error Handling

All errors are returned as `HttpResult`, never thrown:

### Network Error

```python
result = await client.execute(
    config={"url": "https://invalid-domain-9999.com"},
    params={}
)

assert result.success == False
assert result.error is not None
assert "connection" in result.error.lower()
```

### Timeout

```python
result = await client.execute(
    config={
        "url": "https://slow-api.example.com",
        "timeout": 1  # 1 second
    },
    params={}
)

assert result.success == False
assert "timeout" in result.error.lower()
```

### HTTP Error (4xx, 5xx)

```python
result = await client.execute(
    config={"url": "https://api.example.com/notfound"},
    params={}
)

assert result.success == False
assert result.status_code == 404
# Note: 4xx errors don't retry, 5xx do
```

## Performance Metrics

`duration_ms` field tracks total request time:

```python
result = await client.execute(config, params)
print(f"Request took {result.duration_ms}ms")

# Includes:
# - DNS lookup
# - TLS handshake
# - Request transmission
# - Response download
# - JSON parsing
```

## Testing

HttpClientPrimitive is testable with mock servers:

```python
import pytest
from lilux.primitives import HttpClientPrimitive
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_get_request():
    client = HttpClientPrimitive()
    result = await client.execute(
        config={"url": "https://httpbin.org/json"},
        params={}
    )
    assert result.success
    assert result.status_code == 200
    assert isinstance(result.body, dict)
```

## Limitations and Design

### By Design (Not a Bug)

1. **Synchronous pattern**
   - Request/response cycle
   - For async streaming, use streaming mode

2. **JSON body only**
   - No multipart, no binary upload
   - Use `[[lilux/primitives/subprocess]]` for file upload scripts

3. **No certificate management**
   - Relies on system CA bundle
   - For custom certs, use subprocess primitive

4. **No connection pooling**
   - New connection per request (default)
   - Pooling handled by underlying httpx library

### Security Notes

- SSL verification enabled by default
- Auth tokens stored safely (via `[[lilux/runtime-services/auth-store]]`)
- No logging of sensitive headers
- Timeout prevents hanging connections

## Next Steps

- See subprocess: `[[lilux/primitives/subprocess]]`
- See lockfile: `[[lilux/primitives/lockfile]]`
- See runtime services: `[[lilux/runtime-services/overview]]`
