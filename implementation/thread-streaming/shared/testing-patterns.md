# Testing Patterns Reference

## Test Structure

- Use pytest with async support (`pytest-asyncio`)
- Mock external dependencies (httpx, websockets, etc.)
- Test both success and failure paths
- Cover edge cases (empty streams, interruptions, etc.)

## Async Testing Pattern

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_streaming():
    # Mock httpx response
    mock_response = AsyncMock()
    mock_response.aiter_lines.return_value = iter([
        "data: {\"type\": \"test\"}\n\n"
    ])
    
    # Test implementation
    result = await http_client._execute_stream(config, params)
    assert result.stream_events_count == 1
```

## Integration Testing

- Test tool chain resolution
- Test config merging
- Test end-to-end flows (tool → primitive)
- Use real file system for file_sink tests (cleanup after)

## Verification Checklist

- [ ] All tests pass
- [ ] Coverage > 80%
- [ ] Error paths tested
- [ ] Edge cases covered
- [ ] No real network calls (all mocked)
