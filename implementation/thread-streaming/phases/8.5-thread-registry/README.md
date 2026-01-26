# Phase 8.5: Thread Registry with SQLite

**Estimated Time:** 2-3 days  
**Dependencies:** Phase 8.1  
**Status:** 📋 Planning

## Overview

Implement SQLite-based thread registry for tracking thread state, events, and metadata. Includes JSONL transcript writer for human-readable logs.

## What This Phase Accomplishes

- SQLite database for thread registry (WAL mode for concurrency)
- Tables: `threads`, `thread_events`
- Thread state management (running, paused, completed, error)
- JSONL transcript writer (append-only)
- Cleanup on completion/timeout
- Thread context storage (permissions, cost budget)

## Files to Create

- `kiwi_mcp/runtime/thread_registry.py` (new - implementation module)
- `kiwi_mcp/runtime/transcript_writer.py` (new - implementation module)
- `.ai/tools/threads/thread_registry.py` (new - Python-only runtime tool, no YAML)
- `tests/runtime/test_thread_registry.py` (new)

**Note:** `thread_registry` is a runtime tool (Python-only, no YAML). Metadata is declared at the top of the Python file. The implementation modules (`kiwi_mcp/runtime/thread_registry.py`) contain the actual logic, while the tool file (`.ai/tools/threads/thread_registry.py`) is the discoverable tool entry point.

## Task Breakdown

1. Create SQLite schema (threads, thread_events tables)
2. Implement thread registration
3. Implement status updates
4. Implement query operations
5. Create transcript writer
6. Create thread_registry tool (Python-only runtime tool with metadata at top)
7. Write comprehensive tests

## Success Criteria

- [ ] SQLite database created with correct schema
- [ ] Thread registration works
- [ ] Status updates work
- [ ] Query operations work
- [ ] Transcript files are written correctly
- [ ] WAL mode enables concurrency
- [ ] Tests cover all operations

## Related Sections

- Doc lines 3848-3862: Phase 8.5 description
- Doc lines 5540-5623: Appendix A.5 (Thread Registry Persistence)
