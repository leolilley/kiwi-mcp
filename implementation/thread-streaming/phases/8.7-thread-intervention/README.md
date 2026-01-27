# Phase 8.7: Thread Intervention Tools

**Estimated Time:** 3 days  
**Dependencies:** Phase 8.5 (Phase 8.6 skipped)  
**Status:** 📋 Planning

## Overview

Enable thread-to-thread intervention for annealing. Tools for reading transcripts, injecting messages, pausing/resuming threads.

## What This Phase Accomplishes

- `thread.read_transcript` - Read another thread's history
- `thread.inject_message` - Write into another thread
- `thread.pause` / `thread.resume` - Deterministic control
- Permissions: only privileged contexts can intervene

## Files to Create

- `.ai/tools/threads/read_transcript.py` (new - Python-only runtime tool)
- `.ai/tools/threads/inject_message.py` (new - Python-only runtime tool)
- `.ai/tools/threads/pause_thread.py` (new - Python-only runtime tool)
- `.ai/tools/threads/resume_thread.py` (new - Python-only runtime tool)
- `tests/runtime/test_thread_intervention.py` (new)

**Note:** Thread intervention tools are runtime tools (Python-only, no YAML) following the same pattern as sink tools. All implementation is contained within each tool file. Metadata is declared at the top using module-level variables. This keeps the core kernel "dumb" - intervention tools are just data-driven tools, not hardcoded infrastructure.

## Task Breakdown

1. Create `.ai/tools/threads/read_transcript.py` with metadata at top
2. Create `.ai/tools/threads/inject_message.py` with metadata at top
3. Create `.ai/tools/threads/pause_thread.py` with metadata at top
4. Create `.ai/tools/threads/resume_thread.py` with metadata at top
5. Implement permission checks in each tool (validate capability tokens)
6. Write comprehensive tests

## Success Criteria

- [ ] All intervention tools work
- [ ] Permission checks enforce access control
- [ ] Transcript reading works
- [ ] Message injection works
- [ ] Pause/resume works deterministically
- [ ] Tests cover all operations

## Related Sections

- Doc lines 3876-3889: Phase 8.7 description
- Doc lines 3683-3758: Thread Intervention Tools section
