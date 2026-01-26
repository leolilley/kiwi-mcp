# Phase 8.1 Verification Checklist

## Pre-Verification

- [ ] All tasks (01-11) are marked complete
- [ ] Code compiles without errors
- [ ] All tests pass

## Functional Verification

### Basic Streaming
- [ ] `http_client.execute()` accepts `mode="stream"` parameter
- [ ] SSE events are parsed correctly from response
- [ ] Events are extracted from `data:` lines
- [ ] Non-data lines are ignored

### Sink Functionality
- [ ] Built-in `return` sink buffers events
- [ ] `file_sink` writes events to file in JSONL format (Python-only tool, no YAML)
- [ ] `null_sink` discards events without errors (Python-only tool, no YAML)
- [ ] `websocket_sink` forwards events (with mock server) (Python-only tool, no YAML)
- [ ] Multiple sinks receive events (fan-out works)
- [ ] Sink tools have correct metadata at top of Python files

### Integration
- [ ] Sinks are pre-instantiated by tool executor (not http_client)
- [ ] Sinks are passed via `__sinks` parameter
- [ ] All sinks are closed after streaming completes
- [ ] HttpResult includes `stream_events_count` and `stream_destinations`

### Body Templating
- [ ] Recursive templating works for nested dicts
- [ ] List templating works
- [ ] String templating works
- [ ] Missing parameters raise clear errors
- [ ] Works in both sync and stream modes

### Error Handling
- [ ] Invalid mode raises ValueError
- [ ] Stream interruptions close sinks gracefully
- [ ] Connection failures are handled
- [ ] Missing sinks parameter is handled (empty list)

## Test Coverage

Run the test suite:
```bash
pytest tests/primitives/test_http_streaming.py -v --cov=kiwi_mcp/primitives/http_client
```

- [ ] Test coverage > 80%
- [ ] All sink types have tests
- [ ] Error paths are tested
- [ ] Edge cases are covered

## Code Quality

- [ ] No linter errors
- [ ] Type hints are correct
- [ ] Docstrings are present
- [ ] Code follows project style

## Documentation

- [ ] Docstrings explain sink architecture
- [ ] Comments clarify SSE parsing logic
- [ ] README notes about sink instantiation

## Integration Test

Create a simple end-to-end test:

```python
# Test that streaming works with real tool chain
# 1. Create anthropic_messages tool config with stream:true
# 2. Execute with mode="stream"
# 3. Verify events are received
# 4. Verify sinks are called
```

## Rollback Point

Before moving to Phase 8.2, create a git tag:
```bash
git tag phase-8.1-complete
git push origin phase-8.1-complete
```

## Next Phase

Once verified, proceed to **Phase 8.2: LLM Endpoint Tools**
