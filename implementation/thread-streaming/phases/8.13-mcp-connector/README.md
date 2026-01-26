# Phase 8.13: MCP Connector Pattern

**Estimated Time:** 1-2 days  
**Dependencies:** Phases 8.4, 8.10  
**Status:** 📋 Planning

## Overview

Implement the MCP connector pattern that discovers external MCP tools and generates child tool schemas with proper capability requirements.

## What This Phase Accomplishes

- `mcp_connector` tool type
- Connector tool that runs `tools/list` and generates child tool schemas
- Generated tools include proper `requires` capabilities
- Auto-signing of generated tools
- Example connector for one MCP (e.g., Supabase)

## Files to Create

- `.ai/tools/mcp/supabase_connector.py` (new - Python-only runtime tool, example connector)
- `tests/runtime/test_mcp_connector.py` (new)

**Note:** MCP connector tools are runtime tools (Python-only, no YAML) following the same pattern as sink tools. The connector tool discovers external MCP tools and generates child tool YAML files. All connector logic is contained within the tool file. Metadata is declared at the top using module-level variables. This keeps the core kernel "dumb" - connectors are just data-driven tools, not hardcoded infrastructure.

## Task Breakdown

1. Create `.ai/tools/mcp/supabase_connector.py` with metadata at top
2. Implement connector discovery logic (connect to MCP, call tools/list)
3. Implement tool schema generation (create YAML files for discovered tools)
4. Add capability requirements to generated tools (from connector config)
5. Implement auto-signing of generated tools
6. Write comprehensive tests

## Success Criteria

- [ ] Connector tool type works
- [ ] Tool discovery works (tools/list)
- [ ] Generated tools have correct structure
- [ ] Capability requirements are correct
- [ ] Tools are auto-signed
- [ ] Example connector works end-to-end
- [ ] Tests cover all scenarios

## Related Sections

- Doc lines 3964-3977: Phase 8.13 description
- Doc lines 5625-5773: Appendix A.6 (External MCP Integration & Tool Discovery)
