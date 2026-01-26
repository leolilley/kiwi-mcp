# Task: Create anthropic_messages Tool Config

## Context
Create the base Anthropic Messages API tool configuration. This is a pure YAML config that chains to `http_client` primitive.

## Dependencies
- Must complete: Phase 8.1 (streaming support)

## Files to Create
- `.ai/tools/llm/anthropic_messages.yaml`

## Implementation Steps

1. Create `.ai/tools/llm/` directory if it doesn't exist
2. Create `anthropic_messages.yaml` with tool metadata
3. Configure HTTP request (method, url, headers, auth)
4. Configure body template with parameters
5. Configure streaming (SSE transport, return sink)
6. Add retry configuration

## Code Snippet

From doc lines 512-578:

```yaml
# .ai/tools/llm/anthropic_messages.yaml
tool_id: anthropic_messages
tool_type: http
version: "1.0.0"
description: "Call Anthropic Messages API"
executor_id: http_client

config:
  method: POST
  url: "https://api.anthropic.com/v1/messages"

  auth:
    type: bearer
    token: "${ANTHROPIC_API_KEY}"

  headers:
    Content-Type: application/json
    anthropic-version: "2023-06-01"

  # Body is templated with params
  body:
    model: "{model}"
    max_tokens: "{max_tokens}"
    stream: "{stream}"
    system: "{system_prompt}"
    messages: "{messages}"
    tools: "{tools}"

  # Streaming config (used when stream=true)
  stream:
    transport: sse
    destinations:
      - type: return # Buffer for caller

parameters:
  - name: model
    type: string
    required: true
    default: "claude-sonnet-4-20250514"
  - name: max_tokens
    type: integer
    required: true
    default: 4096
  - name: stream
    type: boolean
    default: false
  - name: system_prompt
    type: string
    required: false
  - name: messages
    type: array
    required: true
    description: "Array of {role, content} message objects"
  - name: tools
    type: array
    required: false
    description: "Tool definitions for function calling"

# A.3: Retry configuration is data-driven in tool YAML
retry:
  max_attempts: 3
  backoff_ms: [250, 1000, 3000] # Exponential backoff
  retryable_errors:
    - STREAM_INCOMPLETE
    - CONNECTION_RESET
    - TIMEOUT
```

## Success Criteria
- [ ] YAML file exists with correct structure
- [ ] All required fields are present
- [ ] Body templating uses `{param}` syntax
- [ ] Streaming config is correct
- [ ] Retry configuration is included
- [ ] YAML validates without errors

## Verification Command
```bash
# Validate YAML syntax
python -c "
import yaml
with open('.ai/tools/llm/anthropic_messages.yaml') as f:
    config = yaml.safe_load(f)
    assert config['tool_id'] == 'anthropic_messages'
    assert config['executor_id'] == 'http_client'
    print('YAML validation passed!')
"
```

## Notes
- This is pure config - no Python code needed
- Body templating uses `{param}` placeholders
- Streaming is configured but only used when `stream=true`
- Retry config is data-driven (not hardcoded)
- Auth token comes from environment variable
