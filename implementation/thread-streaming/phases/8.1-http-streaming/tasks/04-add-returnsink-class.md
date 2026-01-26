# Task: Add ReturnSink Class (Built-in)

## Context
Implement the built-in `ReturnSink` class that buffers events in memory for inclusion in the `HttpResult.body`. This is the only sink built into `http_client` - all others are data-driven tools.

## Dependencies
- Must complete: `03-extend-httpresult-dataclass.md`

## Files to Modify
- `kiwi_mcp/primitives/http_client.py`

## Implementation Steps

1. Add `ReturnSink` class after the dataclass definitions
2. Implement `__init__`, `write`, `close`, and `get_events` methods
3. Use `List[str]` for the buffer
4. Enforce `max_size` limit in `write` method

## Code Snippet

From doc lines 409-426:

```python
class ReturnSink:
    """Buffer events for inclusion in result. Built into http_client."""

    def __init__(self, max_size: int = 10000):
        self.buffer: List[str] = []
        self.max_size = max_size

    async def write(self, event: str) -> None:
        if len(self.buffer) < self.max_size:
            self.buffer.append(event)

    async def close(self) -> None:
        pass

    def get_events(self) -> List[str]:
        return self.buffer
```

## Success Criteria
- [ ] `ReturnSink` class exists with all methods
- [ ] `write` respects `max_size` limit
- [ ] `get_events` returns the buffer
- [ ] Methods are async where specified
- [ ] Code compiles without errors

## Verification Command
```bash
python -c "
from kiwi_mcp.primitives.http_client import ReturnSink
import asyncio

async def test():
    sink = ReturnSink(max_size=5)
    await sink.write('event1')
    await sink.write('event2')
    assert len(sink.get_events()) == 2
    assert sink.get_events() == ['event1', 'event2']
    # Test max_size limit
    for i in range(10):
        await sink.write(f'event{i}')
    assert len(sink.get_events()) == 5  # Should be capped

asyncio.run(test())
print('ReturnSink test passed!')
"
```

## Notes
- This is a simple in-memory buffer
- `max_size` prevents OOM from unbounded streaming
- `close` is a no-op but included for interface consistency
- All other sinks will follow this same interface pattern
