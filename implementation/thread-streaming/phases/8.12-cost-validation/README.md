# Phase 8.12: Cost Tracking Validation

**Estimated Time:** 1 day  
**Dependencies:** None  
**Status:** 📋 Planning

## Overview

Add `<cost>` tag to required directive metadata with validation. Enforces cost budget configuration for all directives.

## What This Phase Accomplishes

- `<cost>` tag required in directive metadata
- Validation in `DirectiveValidator.validate_metadata()`
- Helpful error messages with examples
- No defaults - strict enforcement

## Files to Modify

- `kiwi_mcp/utils/validators.py` (extend DirectiveValidator)
- `kiwi_mcp/utils/parsers.py` (extract cost from XML)
- `tests/utils/test_cost_validation.py` (new)

## Task Breakdown

1. Add cost extraction to parser
2. Add cost validation to DirectiveValidator
3. Add helpful error messages
4. Write comprehensive tests

## Success Criteria

- [ ] Cost tag is required
- [ ] Validation catches missing cost tags
- [ ] Error messages are helpful
- [ ] No defaults (strict enforcement)
- [ ] Tests cover all validation cases

## Related Sections

- Doc lines 3951-3963: Phase 8.12 description
- Doc lines 5347-5537: Appendix A.4 (Cost and Context Tracking Enforcement)
