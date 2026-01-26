# Tool Patterns Reference

**Source:** Corrected implementation pattern from Phase 8.1

## Tool Type Patterns

### Runtime Tools (Python-Only, No YAML)

**Pattern:**
- Single Python file (`.py`)
- Metadata declared at top of file using module-level variables
- No YAML sidecar file
- Tool discovery via AST parsing

**Metadata Required:**
```python
__tool_type__ = "runtime"
__version__ = "1.0.0"
__executor_id__ = "python"  # or "subprocess", etc.
__category__ = "sinks"  # or "threads", "capabilities", etc.
```

**Optional:**
```python
DEPENDENCIES = ["websockets", "httpx"]  # If external packages needed
CONFIG_SCHEMA = {...}  # If validation schema needed
```

**Examples:**
- `.ai/tools/sinks/file_sink.py`
- `.ai/tools/sinks/null_sink.py`
- `.ai/tools/sinks/websocket_sink.py`
- `.ai/tools/threads/thread_registry.py`
- `.ai/tools/capabilities/fs.py`

**Discovery:** Tools are discovered by scanning `.ai/tools/` directories and parsing Python files for metadata using AST.

### HTTP Tools (YAML Configs)

**Pattern:**
- Single YAML file (`.yaml`)
- Pure configuration, no Python code
- Chains to `http_client` primitive
- Tool discovery via YAML parsing

**Metadata Required:**
```yaml
tool_id: anthropic_messages
tool_type: http
version: "1.0.0"
executor_id: http_client
```

**Examples:**
- `.ai/tools/llm/anthropic_messages.yaml`
- `.ai/tools/llm/openai_chat.yaml`
- `.ai/tools/threads/anthropic_thread.yaml`
- `.ai/tools/mcp/mcp_stdio.yaml`

**Discovery:** Tools are discovered by scanning `.ai/tools/` directories and parsing YAML files.

## Key Distinctions

| Aspect | Runtime Tools | HTTP Tools |
|--------|---------------|------------|
| Format | Python file only | YAML file only |
| Metadata | Module-level variables | YAML keys |
| Discovery | AST parsing | YAML parsing |
| Dependencies | `DEPENDENCIES = [...]` | N/A (no code) |
| Implementation | Python class/function | Config only |
| Executor | `python`, `subprocess`, etc. | `http_client` |

## When to Use Which Pattern

**Use Runtime Tool (Python-only):**
- Tool needs Python code execution
- Tool needs external dependencies
- Tool implements complex logic
- Examples: sinks, extractors, capabilities, thread_registry

**Use HTTP Tool (YAML-only):**
- Tool is just an HTTP API call
- No custom logic needed
- Pure configuration
- Examples: LLM endpoints, MCP base tools

## Implementation Notes

- **No YAML sidecars for runtime tools** - All metadata in Python file
- **Tool discovery is automatic** - System scans directories and parses files
- **Dependencies managed by EnvManager** - Declared in `DEPENDENCIES` list
- **Signature validation** - Tools are signed for integrity (see metadata_manager.py)
