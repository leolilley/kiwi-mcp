# Fix Tests for rye-lilux

## Context

The rye-lilux project has been restructured:
- **Kernel:** `lilux/` (Python package with 5 primitives)
- **RYE Content:** `rye/.ai/` (tools, directives, knowledge)
- **Tests:** `tests/` (copied from kiwi-mcp, need import fixes)

## Current Test Status

- `tests/test_lilux_tools.py` - 14 passing ✅
- `tests/primitives/` - 63 passing, 1 failing
- `tests/unit/` - Many failures due to import issues
- `tests/harness/` - Collection errors (path issues)
- `tests/handlers/` - Collection errors (import issues)
- `tests/integration/` - Not tested yet
- `tests/mcp/` - Not tested yet

## Import Mapping

Replace these imports throughout all test files:

| Old Import | New Import |
|------------|------------|
| `from kiwi_mcp.` | `from lilux.` |
| `import kiwi_mcp.` | `import lilux.` |
| `from safety_harness.` | `from lilux.safety_harness.` |

## New Tool Structure

The RYE tools are now at `rye/.ai/tools/`:

```
rye/.ai/tools/
├── core/                    # PROTECTED
│   ├── system.py
│   ├── rag.py
│   ├── telemetry/           # lib.py, configure.py, status.py, etc.
│   ├── mcp/                 # call.py, discover.py
│   ├── threads/             # safety_harness.py, spawn_thread.py, etc.
│   └── _internal/           # capabilities/, extractors/, parsers/
├── llm/                     # EXTENSIBLE (yaml configs)
├── threads/                 # EXTENSIBLE (templates)
└── mcp/                     # EXTENSIBLE (server configs)
```

## Tasks

### 1. Fix unit tests (`tests/unit/`)

Files to fix:
- `test_parsers.py` - imports `lilux.utils.parsers`
- `test_validators.py` - imports `lilux.utils.validators`
- `test_metadata_manager.py` - imports `lilux.utils.metadata_manager`
- `test_schema_validator.py` - imports `lilux.utils.schema_validator`
- `test_xml_parsing_issues.py` - imports parsers

These should already work if lilux has these in `lilux/utils/`. Verify the modules exist.

### 2. Fix harness tests (`tests/harness/`)

Files to fix:
- `test_capability_tokens.py` - needs `from lilux.safety_harness.capabilities import`
- `test_expression_evaluator.py` - expression_evaluator is now at `rye/.ai/tools/core/threads/`
- `test_safety_harness.py` - file path issues
- `test_integration.py` - file path issues

For tests that import from `.ai/tools/`, we need to either:
- Add `rye/.ai/tools/core/threads` to PYTHONPATH in conftest.py
- Or skip these tests for now (they test user-space tools)

### 3. Fix handler tests (`tests/handlers/`)

- Update imports from `kiwi_mcp.handlers` to `lilux.handlers`

### 4. Skip telemetry tests

`test_telemetry_tools.py` imports from user-space tools (`telemetry_lib`). Either:
- Keep it as `.skip` file
- Or set up proper import path for rye tools

### 5. Update conftest.py

Add path setup for rye tools if needed:

```python
import sys
from pathlib import Path

# Add rye tools to path for testing
rye_tools = Path(__file__).parent.parent / "rye" / ".ai" / "tools"
if rye_tools.exists():
    sys.path.insert(0, str(rye_tools / "core"))
    sys.path.insert(0, str(rye_tools / "core" / "threads"))
```

### 6. Update test_lilux_tools.py

Fix the knowledge structure test - we renamed `kernel/` to `lilux/`:
- Change `"kernel"` to `"lilux"` ✅ (already done)

## Verification

Run tests incrementally:

```bash
# Core tests
.venv/bin/pytest tests/test_lilux_tools.py -v

# Primitives
.venv/bin/pytest tests/primitives/ -v

# Unit tests
.venv/bin/pytest tests/unit/ -v

# All tests
.venv/bin/pytest tests/ -v --tb=short
```

## Expected Outcome

- 200+ tests passing
- Clear skip markers on tests that need user-space tool setup
- No import errors on collection
