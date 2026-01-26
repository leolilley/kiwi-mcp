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

- `.ai/tools/threads/thread_registry.py` (new - Python-only runtime tool, no YAML)
- `tests/runtime/test_thread_registry.py` (new)

**Note:** `thread_registry` is a runtime tool (Python-only, no YAML) following the same pattern as sink tools. All implementation (SQLite registry, transcript writer) is contained within the single Python file. Metadata is declared at the top of the file using module-level variables (`__tool_type__`, `__version__`, `__executor_id__`, `__category__`). This keeps the core kernel "dumb" - thread registry is just another data-driven tool, not hardcoded infrastructure.

## Task Breakdown

1. Create `.ai/tools/threads/thread_registry.py` with metadata at top
2. Implement SQLite schema (threads, thread_events tables) - all in the tool file
3. Implement ThreadRegistry class (registration, status updates, queries)
4. Implement TranscriptWriter class (JSONL append-only writer) - helper in same file
5. Implement tool entry point function that handles actions (register, update_status, query, get_status, log_event)
6. Write comprehensive tests

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
