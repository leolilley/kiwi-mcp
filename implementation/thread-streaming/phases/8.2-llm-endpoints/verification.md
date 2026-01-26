# Phase 8.2 Verification Checklist

## Pre-Verification

- [ ] All tasks are marked complete
- [ ] All YAML files validate
- [ ] Tool chain resolution works

## Functional Verification

### Tool Configs
- [ ] `anthropic_messages.yaml` exists and is valid
- [ ] `anthropic_thread.yaml` exists and is valid
- [ ] `openai_chat.yaml` exists and is valid
- [ ] `openai_thread.yaml` exists and is valid

### Tool Chain Resolution
- [ ] `anthropic_thread` resolves to `anthropic_messages` → `http_client`
- [ ] Config merging works (child overrides parent)
- [ ] Parameters are correctly inherited

### Streaming Integration
- [ ] Thread tools stream to file_sink correctly
- [ ] Transcript files are created in `.ai/threads/{thread_id}/`
- [ ] Return sink buffers events for harness
- [ ] Both sinks receive events (fan-out works)

### Body Templating
- [ ] Parameters are substituted correctly
- [ ] `{thread_id}` is templated in transcript path
- [ ] Message arrays are passed correctly

## Integration Test

Run end-to-end test:
```bash
pytest tests/integration/test_thread_tools.py -v
```

Test should:
1. Execute `anthropic_thread` with mock LLM response
2. Verify transcript file is created
3. Verify events are buffered in return sink
4. Verify tool chain resolution works

## Next Phase

Once verified, proceed to **Phase 8.3: JSON-RPC Protocol Handling**
