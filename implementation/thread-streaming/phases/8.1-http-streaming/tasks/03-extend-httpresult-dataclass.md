# Task: Extend HttpResult with Streaming Fields

## Context
Extend the existing `HttpResult` dataclass to include streaming-specific fields. This allows callers to know if streaming occurred and how many events were processed.

## Dependencies
- Must complete: `01-add-stream-config-dataclass.md`, `02-add-stream-destination-dataclass.md`

## Files to Modify
- `kiwi_mcp/primitives/http_client.py`

## Implementation Steps

1. Find the existing `HttpResult` dataclass
2. Add optional streaming fields: `stream_events_count`, `stream_destinations`
3. Ensure fields are optional (default to None) to maintain backward compatibility

## Code Snippet

From doc lines 298-311:

```python
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

## Success Criteria
- [ ] `HttpResult` includes new streaming fields
- [ ] Fields are optional (backward compatible)
- [ ] Type hints are correct
- [ ] Existing code still compiles

## Verification Command
```bash
python -m py_compile kiwi_mcp/primitives/http_client.py
# Run existing http_client tests to ensure no regressions
pytest tests/primitives/test_http_client.py -v
```

## Notes
- `stream_events_count` tracks how many SSE events were processed
- `stream_destinations` lists which sink types were used (for debugging)
- These fields are None for non-streaming requests (backward compatible)
