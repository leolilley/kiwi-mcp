# Error Handling Patterns Reference

**Source:** `docs/THREAD_AND_STREAMING_ARCHITECTURE.md` Appendix A.8

## Tool Chain Error Wrapping

Each execution layer catches errors and rethrows with context:

```python
@dataclass
class ToolChainError(Exception):
    code: str
    message: str
    chain: List[str]  # ["anthropic_thread", "anthropic_messages", "http_client"]
    failed_at: FailedToolContext
    cause: Optional[Exception]
```

## Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "TOOL_CHAIN_FAILED",
    "message": "Tool chain failed at 'anthropic_messages': invalid config.",
    "chain": ["anthropic_thread", "anthropic_messages", "http_client"],
    "failed_at": {
      "tool_id": "anthropic_messages",
      "config_path": ".ai/tools/llm/anthropic_messages.yaml",
      "validation_errors": [...]
    }
  }
}
```

## Proactive Validation

- Validate tool YAML configs at load/registration time
- Mark tools "unavailable" with clear diagnostic
- Avoids confusing runtime failures mid-thread

## Stream Error Recovery

- Completed tool calls ARE executed
- Partial tool calls are discarded (not executed)
- Mark stream as incomplete, return error with context

See doc Appendix A.3 for stream parsing error recovery details.
