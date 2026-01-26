# Phase 8.3: JSON-RPC Protocol Handling

**Estimated Time:** 2 days  
**Dependencies:** None  
**Status:** 📋 Planning

## Overview

Create JSON-RPC request builder and response parser that works with both subprocess (stdin/stdout) and http_client. This enables MCP protocol support.

## What This Phase Accomplishes

- JSON-RPC request builder (template-based, data-driven)
- JSON-RPC response parser
- Works with both subprocess and http_client
- Tests for JSON-RPC protocol

## Files to Create

- `kiwi_mcp/primitives/jsonrpc.py` (new)
- `tests/primitives/test_jsonrpc.py` (new)

## Task Breakdown

1. Create JSON-RPC request builder
2. Create JSON-RPC response parser
3. Add subprocess integration
4. Add http_client integration
5. Write comprehensive tests

## Success Criteria

- [ ] JSON-RPC requests are built correctly
- [ ] JSON-RPC responses are parsed correctly
- [ ] Works with subprocess (stdio)
- [ ] Works with http_client (HTTP)
- [ ] Error handling is robust
- [ ] Tests cover all cases

## Related Sections

- Doc lines 3822-3833: Phase 8.3 description
