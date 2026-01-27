# Phase 8.8: Cleanup - Remove kiwi_mcp/mcp/

**Estimated Time:** 1 day  
**Dependencies:** Phase 8.4  
**Status:** ✅ Complete

## Overview

Remove the old `kiwi_mcp/mcp/` package entirely after verifying all MCP functionality works via new tools.

## What This Phase Accomplishes

- Verification that all MCP functionality works via new tools
- Deletion of `kiwi_mcp/mcp/` package
- Removal of MCP-specific code from directive handler (moved to tools)
- Creation of `mcp_discover.py` tool for MCP tool discovery using official MCP SDK
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

1. ✅ Verify all MCP functionality works via new tools
2. ✅ Remove MCP-specific code from directive handler
3. ✅ Create `mcp_discover.py` tool for MCP tool discovery
4. ✅ Find and update all imports
5. ✅ Delete mcp/ package
6. ✅ Run full test suite
7. ✅ Update documentation

## Success Criteria

- [x] All MCP functionality verified via new tools
- [x] No imports reference old mcp/ package (made optional in directive handler)
- [x] Package deleted
- [x] All tests pass (thread registry and intervention tests verified)
- [x] Documentation updated (this file)

## Related Sections

- Doc lines 3890-3907: Phase 8.8 description
