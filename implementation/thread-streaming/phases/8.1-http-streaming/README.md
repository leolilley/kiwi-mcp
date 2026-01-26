# Phase 8.1: Extend http_client with Streaming

**Estimated Time:** 3-4 days  
**Dependencies:** None  
**Status:** 📋 Planning

## Overview

Extend the `http_client` primitive to support Server-Sent Events (SSE) streaming with configurable destination sinks. This is the foundation for all streaming features.

## What This Phase Accomplishes

- Adds streaming support to `http_client` primitive
- Implements SSE parsing and event fan-out
- Creates data-driven sink architecture (file_sink, null_sink, websocket_sink)
- Adds built-in `return` sink for buffering
- Enables recursive body templating for parameter substitution

## Files to Create/Modify

- `kiwi_mcp/primitives/http_client.py` (extend - add ReturnSink class + _execute_stream)
- `.ai/tools/sinks/file_sink.py` (new - Python-only, no YAML)
- `.ai/tools/sinks/null_sink.py` (new - Python-only, no YAML)
- `.ai/tools/sinks/websocket_sink.py` (new - Python-only, no YAML)
- `tests/primitives/test_http_streaming.py` (new)

## Architecture Notes

**Key Principle:** `http_client` is a pure primitive. It receives pre-instantiated sink objects from the tool executor (during chain resolution). Sinks are passed via `__sinks` parameter.

**Sink Types:**
- `return` (built-in): Buffers events in memory for inclusion in result
- `file_sink` (data-driven): Appends events to file in JSONL format
- `null_sink` (data-driven): Discards events (fire-and-forget)
- `websocket_sink` (data-driven): Forwards events to WebSocket endpoint

**Sink Instantiation:** Happens in tool executor during chain resolution, BEFORE http_client execution. See doc section "Sink Architecture (Data-Driven)" for details.

**Tool Pattern:** Sink tools are Python-only files (no YAML sidecars). Metadata is declared at the top of the Python file using module-level variables: `__tool_type__`, `__version__`, `__executor_id__`, `__category__`. Dependencies are declared as `DEPENDENCIES = [...]` if needed.

## Task Order

1. Add StreamConfig and StreamDestination dataclasses to http_client.py
2. Add ReturnSink class to http_client.py (built-in primitive)
3. Implement _execute_stream method with SSE parsing
4. Add recursive body templating
5. Write tests for http_client streaming
6. Create file_sink tool (Python-only) - data-driven tool
7. Create null_sink tool (Python-only) - data-driven tool
8. Create websocket_sink tool (Python-only) - data-driven tool

## Success Criteria

- [ ] http_client supports `mode="stream"` parameter
- [ ] SSE events are parsed correctly
- [ ] Events fan-out to all configured sinks
- [ ] Built-in `return` sink buffers events
- [ ] All three data-driven sinks work correctly
- [ ] Body templating works recursively (dict/list/str)
- [ ] Tests cover sync, stream, and error cases

## Related Sections

- Doc lines 262-504: Layer 1 (Extended http_client Primitive)
- Doc lines 5775-6125: Appendix A.7 (Sink Architecture)
