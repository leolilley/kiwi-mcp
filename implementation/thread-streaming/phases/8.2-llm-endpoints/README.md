# Phase 8.2: LLM Endpoint / Thread Tools

**Estimated Time:** 1-2 days  
**Dependencies:** Phase 8.1  
**Status:** 📋 Planning

## Overview

Create data-driven tool configurations for LLM endpoints (Anthropic, OpenAI) and thread wrappers. These are pure YAML configs that chain to `http_client` - no code, just data.

## What This Phase Accomplishes

- Creates `anthropic_messages` tool config (base LLM endpoint)
- Creates `anthropic_thread` tool config (thread wrapper with transcript)
- Creates `openai_chat` and `openai_thread` equivalents
- Tests streaming to file + return sinks

## Files to Create

- `.ai/tools/llm/anthropic_messages.yaml` (new - HTTP tool, YAML config)
- `.ai/tools/llm/openai_chat.yaml` (new - HTTP tool, YAML config)
- `.ai/tools/threads/anthropic_thread.yaml` (new - HTTP tool, YAML config)
- `.ai/tools/threads/openai_thread.yaml` (new - HTTP tool, YAML config)
- `tests/integration/test_thread_tools.py` (new)

**Note:** LLM endpoint tools are HTTP tools (YAML configs), not runtime tools. Only runtime tools (like sinks) are Python-only.

## Architecture Notes

**Key Principle:** These are pure config tools. They chain to `http_client` primitive. No Python code needed - just YAML configuration.

**Tool Chain:**
```
anthropic_thread → anthropic_messages → http_client (primitive)
```

**Config Merging:** Child configs override parent configs. `anthropic_thread` inherits from `anthropic_messages` and adds thread-specific config (transcript path, etc.).

## Task Order

1. Create anthropic_messages tool config
2. Create anthropic_thread tool config
3. Create openai_chat tool config
4. Create openai_thread tool config
5. Write integration tests

## Success Criteria

- [ ] All four tool configs exist
- [ ] Tool chains resolve correctly
- [ ] Streaming works with file + return sinks
- [ ] Body templating works with parameters
- [ ] Transcript storage works for thread tools
- [ ] Tests verify end-to-end streaming

## Related Sections

- Doc lines 505-630: Layer 2 (LLM Endpoint Tools)
- Doc lines 632-696: Layer 3 (Thread Tools)
