# Phase 8.4: MCP Base Tools

**Estimated Time:** 2 days  
**Dependencies:** Phase 8.3  
**Status:** 📋 Planning

## Overview

Create the two base MCP tools that wrap the primitives: `mcp_stdio` (JSON-RPC over subprocess) and `mcp_http` (JSON-RPC over http_client).

## What This Phase Accomplishes

- `mcp_stdio` tool (for local MCPs)
- `mcp_http` tool (for remote MCPs)
- Foundation for all MCP connections

## Files to Create

- `.ai/tools/mcp/mcp_stdio.yaml` (new)
- `.ai/tools/mcp/mcp_http.yaml` (new)
- `tests/integration/test_mcp_tools.py` (new)

## Task Breakdown

1. Create mcp_stdio tool config
2. Create mcp_http tool config
3. Write integration tests

## Success Criteria

- [ ] Both tool configs exist
- [ ] Tool chains resolve correctly
- [ ] JSON-RPC protocol works
- [ ] Tests verify end-to-end MCP calls

## Related Sections

- Doc lines 2997-3065: Layer 7 (MCP Base Tools)
