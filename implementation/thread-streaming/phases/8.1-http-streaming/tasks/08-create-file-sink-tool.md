# Task: Create file_sink Tool (Python Only)

## Context
Create the `file_sink` data-driven tool that appends streaming events to a file in JSONL format. This is used for transcript storage and audit logs.

## Dependencies
- Must complete: `07-add-recursive-body-templating.md`

## Files to Create
- `.ai/tools/sinks/file_sink.py` (Python-only, no YAML)

## Implementation Steps

1. Create `.ai/tools/sinks/` directory if it doesn't exist
2. Create `file_sink.py` with metadata at the top
3. Add required metadata: `__tool_type__`, `__version__`, `__executor_id__`, `__category__`
4. Implement `FileSink` class with `write` and `close` methods
5. Handle JSONL format (parse SSE event, write as JSON line)
6. Implement periodic flushing
7. Create parent directory if needed

## Code Snippet

**Python (from doc lines 5854-5906, updated pattern):**

```python
# .ai/tools/sinks/file_sink.py
__tool_type__ = "runtime"
__version__ = "1.0.0"
__executor_id__ = "python"
__category__ = "sinks"

import json
import io
from pathlib import Path
from typing import Optional


class FileSink:
    """Append streaming events to file."""

    def __init__(self, path: str, format: str = "jsonl", flush_every: int = 10):
        self.path = Path(path)
        self.format = format
        self.flush_every = flush_every
        self.event_count = 0
        self.file_handle: Optional[io.TextIOWrapper] = None

        # Ensure parent directory exists
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def write(self, event: str) -> None:
        """Write event to file."""
        if not self.file_handle:
            self.file_handle = open(self.path, "a", encoding="utf-8")

        if self.format == "jsonl":
            # Parse SSE event and write as JSONL
            try:
                data = json.loads(event)
                self.file_handle.write(json.dumps(data) + "\n")
            except json.JSONDecodeError:
                # Write raw if not valid JSON
                self.file_handle.write(event + "\n")
        else:
            # Raw format
            self.file_handle.write(event + "\n")

        self.event_count += 1

        # Periodic flush for safety
        if self.event_count % self.flush_every == 0:
            self.file_handle.flush()

    async def close(self) -> None:
        """Close file handle."""
        if self.file_handle:
            self.file_handle.flush()
            self.file_handle.close()
            self.file_handle = None
```

## Success Criteria
- [ ] `file_sink.py` exists with metadata at top
- [ ] Metadata includes: `__tool_type__`, `__version__`, `__executor_id__`, `__category__`
- [ ] `FileSink` class implements `write` and `close` methods
- [ ] JSONL format works correctly
- [ ] Parent directory is created if needed
- [ ] Periodic flushing works
- [ ] File handle is properly closed

## Verification Command
```bash
# Test file_sink directly
python -c "
import asyncio
import json
from pathlib import Path
import sys
sys.path.insert(0, '.ai/tools/sinks')
from file_sink import FileSink

async def test():
    test_file = Path('/tmp/test_sink.jsonl')
    if test_file.exists():
        test_file.unlink()
    
    sink = FileSink(str(test_file), format='jsonl', flush_every=2)
    await sink.write(json.dumps({'type': 'test', 'data': 'hello'}))
    await sink.write(json.dumps({'type': 'test', 'data': 'world'}))
    await sink.close()
    
    # Verify file contents
    lines = test_file.read_text().strip().split('\n')
    assert len(lines) == 2
    assert json.loads(lines[0])['data'] == 'hello'
    print('file_sink test passed!')

asyncio.run(test())
"
```

## Notes
- **No YAML file needed** - metadata is in Python file at top
- This is a data-driven tool (not built into http_client)
- EnvManager will handle Python dependencies if needed
- JSONL format: one JSON object per line
- Flushing ensures data is written even if process crashes
- Path templating (e.g., `{thread_id}`) happens at tool instantiation time
- Tool discovery reads metadata from Python file using AST parsing
