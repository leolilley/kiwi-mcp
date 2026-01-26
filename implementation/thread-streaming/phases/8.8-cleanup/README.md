# Phase 8.8: Cleanup - Remove kiwi_mcp/mcp/

**Estimated Time:** 1 day  
**Dependencies:** Phase 8.4  
**Status:** 📋 Planning

## Overview

Remove the old `kiwi_mcp/mcp/` package entirely after verifying all MCP functionality works via new tools.

## What This Phase Accomplishes

- Verification that all MCP functionality works via new tools
- Deletion of `kiwi_mcp/mcp/` package
- Update any imports/references
- Final integration tests

## Files to Delete

```
kiwi_mcp/mcp/
├── __init__.py      # DELETE
├── client.py        # DELETE - replaced by mcp_stdio/mcp_http tools
├── pool.py          # DELETE - replaced by thread_registry.py
├── registry.py      # DELETE - replaced by registry-based tool loading
└── schema_cache.py  # DELETE - integrated into tool resolution
```

## Task Breakdown

1. Verify all MCP functionality works via new tools
2. Find and update all imports
3. Delete mcp/ package
4. Run full test suite
5. Update documentation

## Success Criteria

- [ ] All MCP functionality verified via new tools
- [ ] No imports reference old mcp/ package
- [ ] Package deleted
- [ ] All tests pass
- [ ] Documentation updated

## Related Sections

- Doc lines 3890-3907: Phase 8.8 description
