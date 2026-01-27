# Phase 8.9: Thread ID Validation

**Estimated Time:** 0.5 days  
**Dependencies:** Phase 8.5 (thread_registry)  
**Status:** ✅ Complete

## Overview

Implement thread ID validation as part of the `spawn_thread` data-driven tool. Validation includes sanitization (alphanumeric, underscore, hyphen), uniqueness checking via `thread_registry`, auto-suggestion for invalid IDs, and clear error messages.

**Key Principle:** This is a **data-driven tool**, not hardcoded kernel logic. All validation happens in the `spawn_thread.py` tool itself.

## What This Phase Accomplishes

- `spawn_thread.py` Python runtime tool with built-in validation
- `sanitize_thread_id()` function with permissive regex `[a-zA-Z0-9_-]`
- Uniqueness checking via `thread_registry` tool
- Auto-suggestion for invalid IDs (e.g., suggest snake_case conversion)
- Clear error messages with examples
- Thread spawning logic (OS-level thread/process spawner)

## Files to Create

- `.ai/tools/threads/spawn_thread.py` (new - Python runtime tool)
- `tests/runtime/test_thread_spawner.py` (new)

## Task Breakdown

1. **Create `spawn_thread.py` tool** (Python runtime tool in `.ai/tools/threads/`)
   - Add metadata (`__tool_type__ = "python"`, `__executor_id__ = "python_runtime"`)
   - Implement `sanitize_thread_id()` function:
     - Trim whitespace
     - Replace internal spaces with underscores
     - Allow only `[a-zA-Z0-9_-]` characters
     - Ensure non-empty after sanitization
   - Implement `validate_thread_id()` function:
     - Call `sanitize_thread_id()`
     - Check uniqueness via `thread_registry.execute("get_status", ...)`
     - Return validation result with auto-suggestions if invalid
   - Implement `spawn_thread()` async function:
     - Validate and sanitize `thread_id`
     - Check uniqueness in registry
     - Spawn OS thread using `threading.Thread` or `multiprocessing.Process`
     - Register thread in `thread_registry`
     - Return success response
   - Add CLI entry point (`if __name__ == "__main__":`)

2. **Implement auto-suggestion**
   - For invalid characters: suggest replacement (e.g., spaces → underscores)
   - For invalid format: suggest snake_case pattern
   - Include examples in error messages

3. **Write tests**
   - Test sanitization rules (trim, spaces, special chars, non-empty)
   - Test uniqueness checking
   - Test thread spawning (mock threading)
   - Test error messages and auto-suggestions
   - Test integration with `thread_registry`

## Implementation Notes

- **Data-Driven Pattern:** This is a Python runtime tool, not kernel code. All logic is self-contained in the tool file.
- **Permissive Validation:** Accepts alphanumeric, underscore, and hyphen (not strict snake_case). This allows flexibility for different harnesses.
- **Uniqueness Check:** Uses `thread_registry` tool via `importlib.util` to check if thread_id already exists.
- **Thread Spawning:** Uses `threading.Thread` with `daemon=True` for background execution. Returns immediately after spawn.
- **No Kernel Changes:** All validation happens in the tool layer. The kernel stays "dumb" and just executes the tool.

## Success Criteria

- [x] `spawn_thread.py` tool created with proper metadata
- [x] Thread ID sanitization works (trim, spaces, special chars)
- [x] Uniqueness checking via `thread_registry` works
- [x] Invalid IDs are rejected with clear errors and auto-suggestions
- [x] Thread spawning works (OS-level thread creation)
- [x] Thread registration in `thread_registry` works
- [x] Tests cover all validation cases
- [x] No hardcoded validation in kernel (all in tool)

## Related Sections

- `docs/THREAD_AND_STREAMING_ARCHITECTURE.md` - Full architecture specification Doc
- Doc lines 3908-3920: Phase 8.9 description
- Doc lines 4131-4214: Appendix A.1 (Thread ID Handling - Layer 1: Base spawn_thread Tool)
- Doc lines 4165-4204: `thread_spawner.py` implementation reference (note: should be `.ai/tools/threads/spawn_thread.py` per data-driven pattern)
