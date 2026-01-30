# Source Linking Documentation

This document explains the source linking pattern for all knowledge-base entries.

## Source Linking Pattern

Each knowledge-base entry should have a single source line that links to the original kiwi-mcp implementation.

### Format

```markdown
**Source:** Original implementation: `.ai/{category}/{file}.py` in kiwi-mcp
```

### Complete Example

```markdown
# Python Runtime

**Purpose:** Execute Python scripts via subprocess

**Source:** Original implementation: `.ai/tools/runtimes/python_runtime.py` in kiwi-mcp

## Overview

Python runtime uses ENV_CONFIG to declare Python interpreter resolution...
```

## Mapping: RYE Categories to kiwi-mcp

| rye Category | kiwi-mcp Location |
|--------------|-------------------|
| primitives | `.ai/tools/primitives/` |
| runtimes | `.ai/tools/runtimes/` |
| capabilities | `.ai/tools/capabilities/` |
| telemetry | `.ai/tools/core/telemetry*.py` |
| extractors | `.ai/extractors/|` |
| parsers | `.ai/parsers/` |
| protocol | `.ai/tools/protocol/` |
| sinks | `.ai/tools/sinks/` |
| threads | `.ai/tools/threads/` |
| mcp | `.ai/tools/mcp/` |
| llm | `.ai/tools/llm/` |
| registry | To be determined |
| utility | `.ai/tools/utility/` |
| python | `.ai/tools/python/` |

## Adding Source Links

When creating documentation entries:

1. Identify the corresponding file in kiwi-mcp
2. Add source line immediately after title
3. Use the format: `**Source:** Original implementation: <path>`
4. Keep it minimal - just one line per entry
