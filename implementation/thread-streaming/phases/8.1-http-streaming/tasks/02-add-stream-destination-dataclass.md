# Task: Add StreamDestination Dataclass

## Context
Add the `StreamDestination` dataclass to define where streaming events go. This works with `StreamConfig` to configure streaming destinations.

## Dependencies
- Must complete: `01-add-stream-config-dataclass.md`

## Files to Modify
- `kiwi_mcp/primitives/http_client.py`

## Implementation Steps

1. Add `Optional` and `Dict` to imports if not already present
2. Add `StreamDestination` dataclass after `StreamConfig`
3. Add fields: `type`, `path`, `config`, `format`
4. Update `StreamConfig.destinations` type hint to use `StreamDestination`

## Code Snippet

From doc lines 285-296:

```python
@dataclass
class StreamDestination:
    """Where streaming events go.

    NOTE (A.7): Only 'return' is a built-in http_client sink (buffers in memory).
    All other sinks (file_sink, null_sink, websocket_sink) are data-driven tools.
    See Appendix A.7 for sink architecture and tool configurations.
    """
    type: str  # "return" (built-in), or tool-based: "file_sink", "null_sink", "websocket_sink"
    path: Optional[str] = None  # For file_sink
    config: Optional[Dict[str, Any]] = None  # For tool-based sinks
    format: str = "jsonl"  # "jsonl" | "raw"
```

## Success Criteria
- [ ] `StreamDestination` dataclass exists
- [ ] All fields are correctly typed with defaults
- [ ] `StreamConfig.destinations` uses `List[StreamDestination]`
- [ ] Code compiles without errors

## Verification Command
```bash
python -m py_compile kiwi_mcp/primitives/http_client.py
```

## Notes
- The `type` field distinguishes built-in vs data-driven sinks
- `path` is only used by `file_sink`
- `config` is for tool-based sinks (websocket_sink, etc.)
- The docstring explains the architecture clearly
