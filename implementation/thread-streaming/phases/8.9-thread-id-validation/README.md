# Phase 8.9: Thread ID Validation

**Estimated Time:** 0.5 days  
**Dependencies:** Phase 8.5  
**Status:** 📋 Planning

## Overview

Implement thread ID validation with snake_case regex, auto-suggestion for invalid IDs, and clear error messages.

## What This Phase Accomplishes

- `validate_thread_id()` function with snake_case regex
- Validation in spawn_thread.yaml schema
- Validation in MCP execute handler
- Auto-suggestion for invalid IDs
- Clear error messages with examples

## Files to Create

- `kiwi_mcp/runtime/validation.py` (new)
- `tests/runtime/test_validation.py` (new)

## Task Breakdown

1. Implement validate_thread_id() function
2. Add validation to spawn_thread.yaml schema
3. Add validation to execute handler
4. Implement auto-suggestion
5. Write tests

## Success Criteria

- [ ] Thread ID validation works
- [ ] Invalid IDs are rejected with clear errors
- [ ] Auto-suggestion works
- [ ] Validation happens at multiple layers
- [ ] Tests cover all cases

## Related Sections

- Doc lines 3908-3920: Phase 8.9 description
- Doc lines 4131-4488: Appendix A.1 (Thread ID Handling)
