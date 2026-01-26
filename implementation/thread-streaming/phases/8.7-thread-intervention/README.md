# Phase 8.7: Thread Intervention Tools

**Estimated Time:** 3 days  
**Dependencies:** Phase 8.6  
**Status:** 📋 Planning

## Overview

Enable thread-to-thread intervention for annealing. Tools for reading transcripts, injecting messages, pausing/resuming threads.

## What This Phase Accomplishes

- `thread.read_transcript` - Read another thread's history
- `thread.inject_message` - Write into another thread
- `thread.pause` / `thread.resume` - Deterministic control
- Permissions: only privileged contexts can intervene

## Files to Create

- `kiwi_mcp/tools/thread_control.py` (new)
- `tests/tools/test_thread_intervention.py` (new)

## Task Breakdown

1. Implement read_transcript tool
2. Implement inject_message tool
3. Implement pause/resume tools
4. Add permission checks
5. Write comprehensive tests

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
