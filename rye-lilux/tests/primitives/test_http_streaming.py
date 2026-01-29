"""
Tests for http_client streaming functionality.
"""
import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from lilux.primitives.http_client import (
    HttpClientPrimitive,
    StreamConfig,
    StreamDestination,
    ReturnSink,
    HttpResult,
)


class TestStreaming:
    """Tests for http_client streaming functionality."""

    @pytest.mark.asyncio
    async def test_sse_parsing(self):
        """Test that SSE events are parsed correctly."""
        client = HttpClientPrimitive()
        
        # Create async generator for SSE lines
        async def sse_lines():
            yield "data: {\"type\": \"message_start\"}\n"
            yield "\n"
            yield "data: {\"type\": \"content_block_delta\", \"text\": \"Hello\"}\n"
            yield "\n"
        
        # Mock SSE response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        # aiter_lines() is a method that returns an async iterator
        mock_response.aiter_lines = MagicMock(return_value=sse_lines())
        
        # Mock stream context manager - stream() returns an async context manager
        class StreamContextManager:
            async def __aenter__(self):
                return mock_response
            async def __aexit__(self, *args):
                return None
        
        with patch.object(client, '_get_client') as mock_get_client:
            mock_httpx_client = AsyncMock()
            mock_httpx_client.stream = MagicMock(return_value=StreamContextManager())
            mock_get_client.return_value = mock_httpx_client
            
            # Create ReturnSink to capture events
            return_sink = ReturnSink()
            params = {
                "mode": "stream",
                "__sinks": [return_sink],
            }
            config = {
                "method": "POST",
                "url": "https://api.example.com/stream",
                "headers": {},
            }
            
            result = await client.execute(config, params)
            
            # Verify events were captured
            events = return_sink.get_events()
            assert len(events) == 2
            assert 'message_start' in events[0]
            assert 'content_block_delta' in events[1]
            assert result.stream_events_count == 2

    @pytest.mark.asyncio
    async def test_sink_fanout(self):
        """Test that events fan-out to all sinks."""
        client = HttpClientPrimitive()
        
        # Create multiple sinks
        return_sink = ReturnSink()
        null_sink = MagicMock()
        null_sink.write = AsyncMock()
        null_sink.close = AsyncMock()
        
        # Create async generator for SSE lines
        async def sse_lines():
            yield "data: {\"event\": \"test\"}\n"
            yield "\n"
        
        # Mock SSE response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        # aiter_lines() is a method that returns an async iterator
        mock_response.aiter_lines = MagicMock(return_value=sse_lines())
        
        # Mock stream context manager
        class StreamContextManager:
            async def __aenter__(self):
                return mock_response
            async def __aexit__(self, *args):
                return None
        
        with patch.object(client, '_get_client') as mock_get_client:
            mock_httpx_client = AsyncMock()
            mock_httpx_client.stream = MagicMock(return_value=StreamContextManager())
            mock_get_client.return_value = mock_httpx_client
            
            params = {
                "mode": "stream",
                "__sinks": [return_sink, null_sink],
            }
            config = {
                "method": "POST",
                "url": "https://api.example.com/stream",
            }
            
            await client.execute(config, params)
            
            # Verify both sinks received the event
            assert len(return_sink.get_events()) == 1
            null_sink.write.assert_called_once()
            null_sink.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_return_sink_buffering(self):
        """Test ReturnSink buffers events correctly."""
        sink = ReturnSink(max_size=5)
        
        # Write events
        for i in range(3):
            await sink.write(f"event{i}")
        
        events = sink.get_events()
        assert len(events) == 3
        assert events == ["event0", "event1", "event2"]
        
        # Test max_size limit
        for i in range(10):
            await sink.write(f"event{i}")
        
        # Should be capped at max_size
        events = sink.get_events()
        assert len(events) == 5

    @pytest.mark.asyncio
    async def test_file_sink_writing(self):
        """Test file_sink writes events to file."""
        import sys
        from pathlib import Path
        
        # Add .ai/tools/sinks to path for import
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".ai" / "tools" / "sinks"))
        from file_sink import FileSink
        
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.jsonl"
            sink = FileSink(str(test_file), format="jsonl", flush_every=2)
            
            # Write events
            await sink.write(json.dumps({"type": "test", "data": "hello"}))
            await sink.write(json.dumps({"type": "test", "data": "world"}))
            await sink.close()
            
            # Verify file contents
            lines = test_file.read_text().strip().split("\n")
            assert len(lines) == 2
            assert json.loads(lines[0])["data"] == "hello"
            assert json.loads(lines[1])["data"] == "world"

    @pytest.mark.asyncio
    async def test_mode_routing(self):
        """Test that mode parameter routes correctly."""
        client = HttpClientPrimitive()
        
        # Test sync mode (should call _execute_sync)
        with patch.object(client, '_execute_sync', new_callable=AsyncMock) as mock_sync:
            mock_sync.return_value = HttpResult(
                success=True,
                status_code=200,
                body={"test": "data"},
                headers={},
                duration_ms=100,
            )
            
            result = await client.execute({}, {"mode": "sync"})
            mock_sync.assert_called_once()
            assert result.success
        
        # Test stream mode (should call _execute_stream)
        with patch.object(client, '_execute_stream', new_callable=AsyncMock) as mock_stream:
            mock_stream.return_value = HttpResult(
                success=True,
                status_code=200,
                body=[],
                headers={},
                duration_ms=100,
                stream_events_count=5,
            )
            
            result = await client.execute({}, {"mode": "stream"})
            mock_stream.assert_called_once()
            assert result.stream_events_count == 5
        
        # Test invalid mode
        with pytest.raises(ValueError, match="Unknown mode"):
            await client.execute({}, {"mode": "invalid"})

    @pytest.mark.asyncio
    async def test_body_templating_stream(self):
        """Test body templating works with streaming."""
        client = HttpClientPrimitive()
        
        # Test nested structure
        body = {
            "model": "{model}",
            "messages": [{"role": "user", "content": "{message}"}],
        }
        params = {"model": "claude-3", "message": "Hello"}
        
        result = client._template_body(body, params)
        assert result["model"] == "claude-3"
        assert result["messages"][0]["content"] == "Hello"
        
        # Test missing parameter
        with pytest.raises(ValueError, match="Missing parameter"):
            client._template_body({"key": "{missing}"}, {})

    @pytest.mark.asyncio
    async def test_stream_interruption(self):
        """Test handling of stream interruptions."""
        client = HttpClientPrimitive()
        
        return_sink = ReturnSink()
        null_sink = MagicMock()
        null_sink.write = AsyncMock()
        null_sink.close = AsyncMock()
        
        # Mock interrupted stream
        async def interrupted_lines():
            yield "data: {\"event\": \"1\"}\n"
            yield "\n"
            raise ConnectionError("Stream interrupted")
        
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {}
        # aiter_lines() is a method that returns an async iterator
        mock_response.aiter_lines = MagicMock(return_value=interrupted_lines())
        
        # Mock stream context manager
        class StreamContextManager:
            async def __aenter__(self):
                return mock_response
            async def __aexit__(self, *args):
                return None
        
        with patch.object(client, '_get_client') as mock_get_client:
            mock_httpx_client = AsyncMock()
            mock_httpx_client.stream = MagicMock(return_value=StreamContextManager())
            mock_get_client.return_value = mock_httpx_client
            
            params = {
                "mode": "stream",
                "__sinks": [return_sink, null_sink],
            }
            config = {
                "method": "POST",
                "url": "https://api.example.com/stream",
            }
            
            # Should handle error gracefully
            result = await client.execute(config, params)
            
            # Sinks should still be closed (in error handler)
            # Note: close() is called in the exception handler
            # At least one event should be captured before interruption
            assert len(return_sink.get_events()) >= 1
