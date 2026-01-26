# Task: Create anthropic_thread Tool Config

## Context
Create the thread wrapper tool that adds thread-specific concerns (transcript storage, thread IDs) to the base `anthropic_messages` tool.

## Dependencies
- Must complete: `01-create-anthropic-messages-tool.md`

## Files to Create
- `.ai/tools/threads/anthropic_thread.yaml`

## Implementation Steps

1. Create `.ai/tools/threads/` directory if it doesn't exist
2. Create `anthropic_thread.yaml` that chains to `anthropic_messages`
3. Add thread-specific config (transcript path with `{thread_id}` template)
4. Add `thread_id` parameter
5. Configure streaming with file_sink + return

## Code Snippet

From doc lines 644-682:

```yaml
# .ai/tools/threads/anthropic_thread.yaml
tool_id: anthropic_thread
tool_type: http
version: "1.0.0"
description: "Run a conversation thread with Claude"
executor_id: anthropic_messages

config:
  # Inherit from anthropic_messages, add thread-specific config
  stream:
    destinations:
      - type: file_sink
        path: ".ai/threads/{thread_id}/transcript.jsonl" # Per-thread directory
        format: jsonl
      - type: return

parameters:
  - name: thread_id
    type: string
    required: true
    description: "Unique thread identifier (permissive: alphanumeric, underscore, hyphen)"
    # Note: safety_harness auto-generates this; base layer just validates format
  - name: model
    type: string
    default: "claude-sonnet-4-20250514"
  - name: max_tokens
    type: integer
    default: 4096
  - name: stream
    type: boolean
    default: true
  - name: system_prompt
    type: string
    required: false
  - name: messages
    type: array
    required: true
```

## Success Criteria
- [ ] YAML file exists with correct structure
- [ ] Chains to `anthropic_messages` (executor_id)
- [ ] Transcript path uses `{thread_id}` template
- [ ] Both file_sink and return are configured
- [ ] thread_id parameter is required
- [ ] Other parameters inherit from parent

## Verification Command
```bash
# Validate YAML and check chain resolution
python -c "
import yaml
with open('.ai/tools/threads/anthropic_thread.yaml') as f:
    config = yaml.safe_load(f)
    assert config['executor_id'] == 'anthropic_messages'
    assert 'thread_id' in [p['name'] for p in config['parameters']]
    assert any(d['type'] == 'file_sink' for d in config['config']['stream']['destinations'])
    print('anthropic_thread config validation passed!')
"
```

## Notes
- This tool chains to `anthropic_messages` (not directly to http_client)
- Config merging: child overrides parent
- Transcript path is per-thread directory
- `{thread_id}` is templated at execution time
- Default `stream=true` for thread tools
