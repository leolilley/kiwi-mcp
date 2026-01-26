# Phase 8.11: Tool Chain Error Handling

**Estimated Time:** 1 day  
**Dependencies:** Phase 8.1  
**Status:** 📋 Planning

## Overview

Implement comprehensive error handling for tool chains with full context (chain path, config source, validation errors).

## What This Phase Accomplishes

- `ToolChainError` with chain context
- Config validation at tool load time
- Error wrapping at each execution layer
- Include config_path and validation_errors in responses

## Files to Modify/Create

- `kiwi_mcp/core/errors.py` (extend)
- `kiwi_mcp/core/executor.py` (extend)
- `tests/core/test_tool_chain_errors.py` (new)

## Task Breakdown

1. Implement ToolChainError dataclass
2. Add error wrapping in executor
3. Add config validation at load time
4. Include full context in error responses
5. Write comprehensive tests

## Success Criteria

- [ ] ToolChainError includes full context
- [ ] Errors are wrapped at each layer
- [ ] Config validation happens at load time
- [ ] Error responses are LLM-actionable
- [ ] Tests cover all error scenarios

## Related Sections

- Doc lines 3938-3950: Phase 8.11 description
- Doc lines 6128-6186: Appendix A.8 (Error Handling in Tool Chains)
