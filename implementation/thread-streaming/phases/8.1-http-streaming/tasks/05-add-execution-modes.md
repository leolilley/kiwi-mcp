# Task: Add Execution Mode Routing

## Context
Modify the `execute` method to route between sync and stream modes based on a `mode` parameter. This is the entry point for streaming support.

## Dependencies
- Must complete: `04-add-returnsink-class.md`

## Files to Modify
- `kiwi_mcp/primitives/http_client.py`

## Implementation Steps

1. Find the existing `execute` method
2. Extract `mode` from params (default to "sync" for backward compatibility)
3. Add conditional routing: `_execute_sync` vs `_execute_stream`
4. Create stub `_execute_stream` method (will be implemented in next task)

## Code Snippet

From doc lines 315-323:

```python
async def execute(self, config: Dict, params: Dict) -> HttpResult:
    mode = params.get("mode", "sync")

    if mode == "sync":
        return await self._execute_sync(config, params)
    elif mode == "stream":
        return await self._execute_stream(config, params)
    else:
        raise ValueError(f"Unknown mode: {mode}. Must be 'sync' or 'stream'")
```

**Note:** `_execute_sync` should be the existing sync implementation. If it doesn't exist as a separate method, extract it from the current `execute` method.

## Success Criteria
- [ ] `execute` method routes based on `mode` parameter
- [ ] Default mode is "sync" (backward compatible)
- [ ] Invalid mode raises clear error
- [ ] Existing sync behavior unchanged
- [ ] `_execute_stream` stub exists (will be implemented next)

## Verification Command
```bash
# Test that sync mode still works
pytest tests/primitives/test_http_client.py::test_sync_request -v

# Test that invalid mode raises error
python -c "
from kiwi_mcp.primitives.http_client import HttpClient
import asyncio

async def test():
    client = HttpClient()
    try:
        await client.execute({}, {'mode': 'invalid'})
        assert False, 'Should have raised ValueError'
    except ValueError as e:
        assert 'Unknown mode' in str(e)
        print('Mode validation test passed!')

asyncio.run(test())
"
```

## Notes
- This is a simple routing change
- Backward compatibility is critical - default to "sync"
- `_execute_stream` will be implemented in the next task
- The existing sync implementation should be moved to `_execute_sync` if it's currently inline
