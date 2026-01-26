# Task: Write Comprehensive Streaming Tests

## Context
Create comprehensive tests for the streaming functionality, covering SSE parsing, sink fan-out, error cases, and edge cases.

## Dependencies
- Must complete: All previous tasks (01-10)

## Files to Create
- `tests/primitives/test_http_streaming.py`

## Implementation Steps

1. Create test file with pytest structure
2. Test SSE parsing (valid events, malformed events)
3. Test sink fan-out (multiple sinks receive events)
4. Test ReturnSink buffering
5. Test file_sink writing
6. Test null_sink (no errors)
7. Test websocket_sink (mock WebSocket)
8. Test error cases (connection failures, stream interruptions)
9. Test body templating with streaming
10. Test mode parameter routing

## Test Structure

```python
# tests/primitives/test_http_streaming.py
import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from kiwi_mcp.primitives.http_client import (
    HttpClient, StreamConfig, StreamDestination, 
    ReturnSink, HttpResult
)
from .sinks.file_sink import FileSink
from .sinks.null_sink import NullSink

class TestStreaming:
    """Tests for http_client streaming functionality."""
    
    @pytest.mark.asyncio
    async def test_sse_parsing(self):
        """Test that SSE events are parsed correctly."""
        # Mock SSE response
        # Verify events are extracted
        
    @pytest.mark.asyncio
    async def test_sink_fanout(self):
        """Test that events fan-out to all sinks."""
        # Create multiple sinks
        # Verify all receive events
        
    @pytest.mark.asyncio
    async def test_return_sink_buffering(self):
        """Test ReturnSink buffers events correctly."""
        # Verify events are buffered
        # Verify max_size limit
        
    @pytest.mark.asyncio
    async def test_file_sink_writing(self):
        """Test file_sink writes events to file."""
        # Create temp file
        # Write events
        # Verify file contents
        
    @pytest.mark.asyncio
    async def test_mode_routing(self):
        """Test that mode parameter routes correctly."""
        # Test sync mode
        # Test stream mode
        # Test invalid mode
        
    @pytest.mark.asyncio
    async def test_stream_interruption(self):
        """Test handling of stream interruptions."""
        # Mock interrupted stream
        # Verify sinks are closed
        # Verify partial events handled
        
    @pytest.mark.asyncio
    async def test_body_templating_stream(self):
        """Test body templating works with streaming."""
        # Template body with params
        # Verify in stream request
```

## Success Criteria
- [ ] Test file exists with comprehensive coverage
- [ ] All sink types are tested
- [ ] Error cases are covered
- [ ] Edge cases (empty streams, interruptions) are tested
- [ ] Tests pass consistently
- [ ] Mocking is used appropriately (no real network calls)

## Verification Command
```bash
pytest tests/primitives/test_http_streaming.py -v
```

## Notes
- Use pytest-asyncio for async tests
- Mock httpx responses to avoid real network calls
- Test both success and failure paths
- Verify sink cleanup (close() is called)
- Test with multiple sinks simultaneously
- Cover edge cases: empty streams, malformed SSE, connection failures
