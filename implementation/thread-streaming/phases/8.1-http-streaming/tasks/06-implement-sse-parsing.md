# Task: Implement SSE Parsing in _execute_stream

## Context
Implement the `_execute_stream` method that parses Server-Sent Events (SSE) and fans out events to configured sinks. This is the core streaming functionality.

## Dependencies
- Must complete: `05-add-execution-modes.md`

## Files to Modify
- `kiwi_mcp/primitives/http_client.py`

## Implementation Steps

1. Implement `_execute_stream` method
2. Extract pre-instantiated sinks from `params["__sinks"]` (provided by tool executor)
3. Use httpx streaming client (`async with client.stream(...)`)
4. Parse SSE format: lines starting with `data:`
5. Fan-out events to all sinks
6. Buffer events if `ReturnSink` is present
7. Close all sinks after streaming completes
8. Return `HttpResult` with streaming metadata

## Code Snippet

From doc lines 330-375:

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

    # Build request (same as sync, but use stream)
    method = config.get("method", "GET")
    url = config.get("url")
    headers = config.get("headers", {})
    # ... build request kwargs ...

    async with self._client.stream(method, url, **kwargs) as response:
        event_count = 0

        async for line in response.aiter_lines():
            if line.startswith("data:"):
                event_data = line[5:].strip()  # Remove "data: " prefix
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

    # Get buffered events from ReturnSink if present
    body = None
    if should_buffer:
        return_sink = next(s for s in sinks if isinstance(s, ReturnSink))
        body = return_sink.get_events()

    return HttpResult(
        success=True,
        status_code=response.status_code,
        body=body,
        headers=dict(response.headers),
        duration_ms=duration_ms,  # Calculate from start time
        stream_events_count=event_count,
        stream_destinations=[type(s).__name__ for s in sinks],
    )
```

## Success Criteria
- [ ] `_execute_stream` method implemented
- [ ] SSE format parsed correctly (`data:` prefix)
- [ ] Events fan-out to all sinks
- [ ] ReturnSink buffers events correctly
- [ ] All sinks are closed after completion
- [ ] HttpResult includes streaming metadata
- [ ] Handles empty sinks list gracefully

## Verification Command
```bash
# Create a simple test
pytest tests/primitives/test_http_streaming.py::test_sse_parsing -v
```

## Notes
- Sinks are pre-instantiated by tool executor (not http_client's job)
- SSE format: `data: <json>\n\n` (double newline separates events)
- Only lines starting with `data:` are processed (ignore `event:`, `id:`, etc.)
- `max_buffer_size` prevents OOM
- Duration calculation should track start/end time
