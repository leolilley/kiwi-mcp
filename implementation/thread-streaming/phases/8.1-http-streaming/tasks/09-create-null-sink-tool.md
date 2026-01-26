# Task: Create null_sink Tool (Python Only)

## Context
Create the `null_sink` data-driven tool that discards all streaming events. Used for fire-and-forget calls and performance testing.

## Dependencies
- Must complete: `08-create-file-sink-tool.md`

## Files to Create
- `.ai/tools/sinks/null_sink.py` (Python-only, no YAML)

## Implementation Steps

1. Create `null_sink.py` in `.ai/tools/sinks/`
2. Add metadata at top: `__tool_type__`, `__version__`, `__executor_id__`, `__category__`
3. Implement `NullSink` class with `write` and `close` as no-ops
4. Keep it simple - just discard everything

## Code Snippet

**Python (from doc lines 5929-5945, updated pattern):**

```python
# .ai/tools/sinks/null_sink.py
__tool_type__ = "runtime"
__version__ = "1.0.0"
__executor_id__ = "python"
__category__ = "sinks"


class NullSink:
    """Discard all events."""

    async def write(self, event: str) -> None:
        """Discard event."""
        pass

    async def close(self) -> None:
        """No-op close."""
        pass
```

## Success Criteria
- [ ] `null_sink.py` exists with metadata at top
- [ ] Metadata includes: `__tool_type__`, `__version__`, `__executor_id__`, `__category__`
- [ ] `NullSink` class implements `write` and `close` as no-ops
- [ ] Code is minimal and efficient
- [ ] No errors when used

## Verification Command
```bash
python -c "
import asyncio
import sys
sys.path.insert(0, '.ai/tools/sinks')
from null_sink import NullSink

async def test():
    sink = NullSink()
    # Should not raise any errors
    await sink.write('event1')
    await sink.write('event2')
    await sink.close()
    print('null_sink test passed!')

asyncio.run(test())
"
```

## Notes
- **No YAML file needed** - metadata is in Python file at top
- Simplest sink implementation
- Useful for performance testing (no I/O overhead)
- Fire-and-forget scenarios where you don't need the stream
- No configuration needed
- Tool discovery reads metadata from Python file using AST parsing
