# Task: Add StreamConfig Dataclass

## Context
Add the `StreamConfig` dataclass to `http_client.py` to configure streaming HTTP requests. This is the first step in adding streaming support.

## Dependencies
- None (first task in phase)

## Files to Modify
- `kiwi_mcp/primitives/http_client.py`

## Implementation Steps

1. Import `dataclass` and `List` from typing if not already imported
2. Add `StreamConfig` dataclass after the existing `HttpResult` class
3. Add fields: `transport`, `destinations`, `buffer_events`, `max_buffer_size`

## Code Snippet

From doc lines 277-283:

```python
@dataclass
class StreamConfig:
    """Configuration for streaming HTTP."""
    transport: str  # "sse" | "websocket"
    destinations: List[StreamDestination]
    buffer_events: bool = False  # Include in result.body?
    max_buffer_size: int = 10_000  # Prevent OOM
```

**Note:** `StreamDestination` will be added in the next task. For now, you can use `List[Any]` or add a placeholder import.

## Success Criteria
- [ ] `StreamConfig` dataclass exists in `http_client.py`
- [ ] All fields are correctly typed
- [ ] Default values match the doc
- [ ] Code compiles without errors

## Verification Command
```bash
python -m py_compile kiwi_mcp/primitives/http_client.py
```

## Notes
- This is a simple dataclass addition
- `StreamDestination` will be defined in task 02
- The `transport` field currently only supports "sse" (websocket support is future work)
