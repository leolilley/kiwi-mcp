# Task: Create websocket_sink Tool (Python Only)

## Context
Create the `websocket_sink` data-driven tool that forwards streaming events to a WebSocket endpoint in real-time. Used for thread intervention, live monitoring, and CLI streaming.

## Dependencies
- Must complete: `09-create-null-sink-tool.md`

## Files to Create
- `.ai/tools/sinks/websocket_sink.py` (Python-only, no YAML)

## Implementation Steps

1. Create `websocket_sink.py` in `.ai/tools/sinks/`
2. Add metadata at top: `__tool_type__`, `__version__`, `__executor_id__`, `__category__`
3. Add `DEPENDENCIES = ["websockets"]` list (managed by EnvManager)
4. Implement `WebSocketSink` class with connection retry logic
5. Implement buffering on disconnect
6. Handle reconnection with exponential backoff
7. Forward events to WebSocket

## Code Snippet

**Python (from doc lines 5978-6056, updated pattern):**

```python
# .ai/tools/sinks/websocket_sink.py
__tool_type__ = "runtime"
__version__ = "1.0.0"
__executor_id__ = "python"
__category__ = "sinks"

# Dependencies handled by EnvManager
DEPENDENCIES = ["websockets"]

import asyncio
import json
from typing import List, Optional
import websockets

class WebSocketSink:
    """Forward events to WebSocket endpoint with reconnection support."""

    def __init__(
        self,
        url: str,
        reconnect_attempts: int = 3,
        buffer_on_disconnect: bool = True,
        buffer_max_size: int = 1000
    ):
        self.url = url
        self.reconnect_attempts = reconnect_attempts
        self.buffer_on_disconnect = buffer_on_disconnect
        self.buffer_max_size = buffer_max_size

        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.buffer: List[str] = []
        self.connected = False

    async def _connect(self) -> bool:
        """Establish WebSocket connection with retry."""
        for attempt in range(self.reconnect_attempts):
            try:
                self.ws = await websockets.connect(self.url)
                self.connected = True

                # Flush buffer if we have events
                if self.buffer:
                    for event in self.buffer:
                        await self.ws.send(event)
                    self.buffer.clear()

                return True
            except Exception as e:
                if attempt < self.reconnect_attempts - 1:
                    await asyncio.sleep(0.5 * (2 ** attempt))  # Exponential backoff
                continue

        return False

    async def write(self, event: str) -> None:
        """Write event to WebSocket."""
        # Ensure connection
        if not self.connected or not self.ws:
            if not await self._connect():
                if self.buffer_on_disconnect:
                    if len(self.buffer) < self.buffer_max_size:
                        self.buffer.append(event)
                return

        try:
            await self.ws.send(event)
        except websockets.ConnectionClosed:
            self.connected = False
            if self.buffer_on_disconnect:
                if len(self.buffer) < self.buffer_max_size:
                    self.buffer.append(event)

    async def close(self) -> None:
        """Close WebSocket connection."""
        if self.ws:
            await self.ws.close()
            self.ws = None
            self.connected = False
```

## Success Criteria
- [ ] `websocket_sink.py` exists with metadata at top
- [ ] Metadata includes: `__tool_type__`, `__version__`, `__executor_id__`, `__category__`
- [ ] `DEPENDENCIES` list includes `["websockets"]`
- [ ] `WebSocketSink` class implements all methods
- [ ] Connection retry logic works
- [ ] Buffering on disconnect works
- [ ] Events are forwarded correctly
- [ ] Connection is properly closed

## Verification Command
```bash
# Note: This requires a WebSocket server for full testing
# For now, just verify the code compiles
python -m py_compile .ai/tools/sinks/websocket_sink.py
```

## Notes
- **No YAML file needed** - metadata is in Python file at top
- Dependencies declared as `DEPENDENCIES = ["websockets"]` (managed by EnvManager)
- Reconnection is important for reliability
- Buffering prevents event loss during disconnects
- Exponential backoff prevents connection storms
- Used for thread intervention and live monitoring
- Tool discovery reads metadata from Python file using AST parsing
