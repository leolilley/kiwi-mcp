**Source:** Original implementation: `kiwi_mcp/utils/` in kiwi-mcp

# Utilities Overview

## Purpose

Lilux utilities provide minimal helper functions: path resolution, logging, and extensions. **Deliberately minimal**—no content intelligence, no parsing, no validation logic.

## Key Utilities

### Path Resolution (`resolvers.py`)

Thin wrappers around PathService for finding files:

```python
from lilux.utils.resolvers import DirectiveResolver, ToolResolver, KnowledgeResolver

# Find directive file
resolver = DirectiveResolver(project_path="/home/user/project")
path = resolver.resolve("research_topic")
# Returns: /home/user/project/.ai/directives/research_topic.md

# Find tool file
tool_resolver = ToolResolver(project_path="/home/user/project")
path = tool_resolver.resolve("csv_reader")
# Returns: /home/user/project/.ai/tools/csv_reader/

# Find knowledge entry
knowledge_resolver = KnowledgeResolver(project_path="/home/user/project")
path = knowledge_resolver.resolve("20260130-api-patterns")
# Returns: /home/user/project/.ai/knowledge/20260130-api-patterns.md
```

**What it does:** Maps names to file paths (project > user resolution)

**What it doesn't do:** Parse files, understand content, validate

### Logging (`logger.py`)

Simple logging configuration:

```python
import logging
from lilux.utils.logger import setup_logger

# Configure logging
logger = setup_logger(
    name="lilux.tools",
    level=logging.DEBUG,
    log_file="~/.ai/logs/lilux.log"
)

logger.info("Tool execution started")
logger.debug(f"Parameters: {params}")
logger.error(f"Execution failed: {error}")
```

**What it does:** Set up structured logging

**What it doesn't do:** Log parsing, log analysis, alerting

### Extensions (`extensions.py`)

Minimal extension support:

```python
from lilux.utils.extensions import load_extension

# Load extension
extension = load_extension("custom_resolver")

# Extension must define: execute(config) -> result
result = extension.execute(config)
```

**What it does:** Load and call extension modules

**What it doesn't do:** Discover, validate, or manage extensions

### File Utilities (`files.py`, `file_search.py`)

Basic file operations:

```python
from lilux.utils.files import list_files, find_file

# List files in directory
files = list_files("/home/user/project/.ai/tools")

# Find file by pattern
result = find_file("/home/user/project", pattern="*.md", recursive=True)
```

**What it does:** List and find files

**What it doesn't do:** Parse, validate, understand content

## Resolver Pattern

### How Path Resolution Works

1. **Project-first lookup**
   ```
   Check: .ai/{type}/{name}
   If found → return
   If not found → check user space
   ```

2. **User fallback**
   ```
   Check: ~/.ai/{type}/{name}
   If found → return
   If not found → return None
   ```

3. **Search order**
   ```
   Directives: .ai/directives/ > ~/.ai/directives/
   Tools:      .ai/tools/ > ~/.ai/tools/
   Knowledge:  .ai/knowledge/ > ~/.ai/knowledge/
   ```

## Usage Examples

### Resolve Directive

```python
from lilux.utils.resolvers import DirectiveResolver

resolver = DirectiveResolver(project_path="/home/user/project")

# Find directive
path = resolver.resolve("research_topic")

if path:
    print(f"Found: {path}")
    with open(path) as f:
        content = f.read()
else:
    print("Not found")
```

### Setup Logging

```python
import logging
from lilux.utils.logger import setup_logger

logger = setup_logger(name="my_tool", level=logging.INFO)

logger.info("Starting execution")
logger.warning("This might fail")
logger.error("It failed!")
```

### List Project Files

```python
from lilux.utils.files import list_files

tools_dir = "/home/user/project/.ai/tools"
files = list_files(tools_dir)

for file in files:
    print(f"Tool: {file.name}")
```

## Architecture Role

Utilities are part of the **infrastructure layer**:

1. **Path resolution** - Find files without content understanding
2. **Logging** - Track execution
3. **Extensions** - Load pluggable code
4. **File operations** - Basic filesystem operations

**Deliberate limitations:**
- No parsing
- No validation
- No content understanding
- RYE handles all content intelligence

## Contrast with RYE Utils

| Aspect | Lilux Utils | RYE Utils |
|--------|-----------|-----------|
| **Path finding** | Simple file lookup | Content-aware routing |
| **Logging** | Basic setup | Structured with context |
| **Parsing** | None | XML, YAML, frontmatter |
| **Validation** | None | Schema validation |
| **Content** | No | Yes |

## Design Philosophy

### Why Lilux Utils Are Minimal

1. **Lilux is a microkernel**
   - Only generic primitives
   - No domain knowledge

2. **RYE is the OS**
   - Handles content
   - Handles intelligence
   - Handles domain logic

3. **Clear boundary**
   - Lilux = "dumb" execution
   - RYE = "smart" orchestration

## Testing

```python
import pytest
from lilux.utils.resolvers import DirectiveResolver
from pathlib import Path

def test_resolve_directive(tmp_path):
    """Test directive resolution."""
    # Create test structure
    directives_dir = tmp_path / ".ai" / "directives"
    directives_dir.mkdir(parents=True)
    
    test_file = directives_dir / "test_directive.md"
    test_file.write_text("# Test Directive")
    
    # Test resolution
    resolver = DirectiveResolver(project_path=str(tmp_path))
    path = resolver.resolve("test_directive")
    
    assert path is not None
    assert path.exists()
    assert path.name == "test_directive.md"

def test_project_takes_precedence(tmp_path, home_path):
    """Project directives override user directives."""
    # Create user directive
    user_dir = home_path / "directives"
    user_dir.mkdir(parents=True)
    (user_dir / "test.md").write_text("User version")
    
    # Create project directive
    project_dir = tmp_path / ".ai" / "directives"
    project_dir.mkdir(parents=True)
    (project_dir / "test.md").write_text("Project version")
    
    # Resolve - should get project version
    resolver = DirectiveResolver(project_path=str(tmp_path))
    path = resolver.resolve("test")
    
    assert path.parent == project_dir
```

## Common Pitfalls

### ❌ Don't use Lilux utils for content tasks

```python
# Wrong - Lilux can't parse XML
resolver = DirectiveResolver()
path = resolver.resolve("my_directive")
# Now what? Need to parse XML yourself
# Use RYE instead!
```

### ✅ Do use Lilux utils for file operations

```python
# Right - Just finding the file
from lilux.utils.resolvers import DirectiveResolver

resolver = DirectiveResolver()
path = resolver.resolve("my_directive")

# Then pass to RYE for parsing
from rye.handlers import DirectiveHandler
handler = DirectiveHandler()
directive = handler.parse(path)  # RYE parses content
```

## Best Practices

### 1. Use Path Resolution for Simple Lookups

```python
from lilux.utils.resolvers import ToolResolver

resolver = ToolResolver()
path = resolver.resolve("my_tool")

# Simple lookup, no content understanding
```

### 2. Use Logging for Observability

```python
from lilux.utils.logger import setup_logger
import logging

logger = setup_logger(name="my_component", level=logging.INFO)

logger.info(f"Execution started: {tool_id}")
logger.debug(f"Parameters: {params}")
```

### 3. Keep Utils Minimal

Don't add content intelligence to utils:

```python
# Wrong - don't add validation
def load_and_validate_tool(path):
    # Don't do this!
    content = path.read_text()
    validate_tool_schema(content)  # Wrong place!
    return parse_tool(content)  # Wrong place!

# Right - just file operations
def load_tool_file(path):
    return path.read_text()
```

## Limitations and Design

### By Design (Not a Bug)

1. **No content parsing**
   - File operations only
   - RYE handles content

2. **No validation**
   - Just path lookup
   - RYE validates

3. **Minimal configuration**
   - Simple logging setup
   - Defaults work for most cases

4. **No caching**
   - Each lookup is fresh
   - Keeps it simple

## What Not to Add

❌ **Don't add to Lilux utils:**
- XML/YAML parsing
- Schema validation
- Content understanding
- Business logic
- Directive interpretation
- Tool discovery (beyond file lookup)

✅ **These belong in RYE**

## Next Steps

- See schemas: `[[lilux/schemas/overview]]`
- See handlers: `[[lilux/handlers/overview]]`
- See legacy tools: `[[lilux/tools/overview]]`
