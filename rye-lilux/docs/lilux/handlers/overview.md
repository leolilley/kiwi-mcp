**Source:** Original implementation: `kiwi_mcp/handlers/` in kiwi-mcp

# Handlers Overview

## Purpose

Lilux handlers provide dumb routing based on file paths—no content intelligence. They know how to dispatch operations (search, load, execute) to the right place, but don't understand the content itself.

## Architecture

Handlers are **stateless routers**:

```
TypeHandlerRegistry
├── DirectiveHandler
│   └── Routes directive operations
├── ToolHandler
│   └── Routes tool operations
└── KnowledgeHandler
    └── Routes knowledge operations
```

**Key principle:** Handlers just map names to paths. They don't parse, validate, or understand content.

## Key Classes

### TypeHandlerRegistry

Central dispatcher:

```python
class TypeHandlerRegistry:
    def __init__(self, project_path: str):
        """Initialize all type handlers."""
    
    async def search(self, item_type: str, query: str, **kwargs) -> Dict[str, Any]:
        """Search for items (directives, tools, knowledge)."""
    
    async def load(self, item_type: str, name: str) -> Dict[str, Any]:
        """Load item by name."""
    
    async def execute(self, item_type: str, name: str, **kwargs) -> Dict[str, Any]:
        """Execute item (for directives, tools)."""
```

### Individual Handlers

Each handler knows its type:

```python
class DirectiveHandler:
    def __init__(self, project_path: str):
        """Initialize directive handler."""
    
    async def search(self, query: str, **kwargs) -> List[Dict]:
        """Find directives matching query."""
    
    async def load(self, name: str) -> Dict:
        """Load directive file."""
    
    async def execute(self, name: str, **kwargs) -> Dict:
        """Execute directive."""

class ToolHandler:
    # Same interface for tools
    
class KnowledgeHandler:
    # Same interface for knowledge
```

## Handler Operations

### Search

Find items by keyword:

```python
registry = TypeHandlerRegistry(project_path="/home/user/project")

# Search directives
results = await registry.search(
    item_type="directive",
    query="research",
    limit=10
)

# Results: [directive1, directive2, ...]

# Search tools
results = await registry.search(
    item_type="tool",
    query="csv",
    limit=10
)

# Search knowledge
results = await registry.search(
    item_type="knowledge",
    query="API patterns",
    limit=10
)
```

**What it does:** Keyword match on file names/paths

**What it doesn't do:** Understand content, semantic search, ranking

### Load

Retrieve item by name:

```python
# Load directive
result = await registry.load(
    item_type="directive",
    name="research_topic"
)

# Returns: Raw file content

# Load tool
result = await registry.load(
    item_type="tool",
    name="csv_reader"
)

# Load knowledge
result = await registry.load(
    item_type="knowledge",
    name="20260130-api-patterns"
)
```

**What it does:** Find and read file

**What it doesn't do:** Parse, validate, understand structure

### Execute

Execute item:

```python
# Execute directive
result = await registry.execute(
    item_type="directive",
    name="research_topic",
    inputs={"query": "Python"}
)

# Execute tool
result = await registry.execute(
    item_type="tool",
    name="csv_reader",
    inputs={"file": "data.csv"}
)
```

**What it does:** Route to executor

**What it doesn't do:** Understand execution rules, validate parameters

## File Layout

Handlers map to file structure:

```
.ai/
├── directives/
│   ├── research_topic.md
│   └── process_data.md
├── tools/
│   ├── csv_reader/
│   └── api_caller/
└── knowledge/
    ├── 20260130-api-patterns.md
    └── 20260131-best-practices.md

~/.ai/
├── directives/
├── tools/
└── knowledge/
```

Handler resolution:
1. Check project directories
2. If not found, check user directories
3. Return first match or None

## Architecture Role

Handlers are part of the **routing and dispatch layer**:

1. **File resolution** - Map names to paths
2. **Dispatch** - Route to type-specific logic
3. **Simple routing** - No content understanding
4. **Dumb** - Intentionally minimal

## RYE Relationship

RYE's **smart handlers** do the intelligence:
- Parse directive XML
- Understand tool schemas
- Validate knowledge frontmatter
- Rank search results
- Understand execution flow

Lilux handlers are **fallback path-based routing**:
- Find files by name
- No content parsing
- No validation
- No ranking

**Pattern:**
```python
# Lilux (dumb) handler
lilux_handler = DirectiveHandler(project_path)
file_content = await lilux_handler.load("research_topic")
# Returns: raw file content

# RYE (smart) handler
rye_handler = DirectiveContentHandler(project_path)
directive = await rye_handler.load("research_topic")
# Returns: parsed directive object
```

See `[[rye/content-handlers/overview]]` for intelligent routing.

## Usage Examples

### Search Directives

```python
from kiwi_mcp.handlers import TypeHandlerRegistry

registry = TypeHandlerRegistry(project_path="/home/user/project")

# Find all directives matching "research"
results = await registry.search(
    item_type="directive",
    query="research"
)

for result in results:
    print(f"Found: {result['name']}")
```

### Load Tool

```python
# Get tool file
result = await registry.load(
    item_type="tool",
    name="csv_reader"
)

if result['success']:
    content = result['content']
    print(f"Tool content: {content}")
else:
    print(f"Error: {result['error']}")
```

### Execute Directive

```python
# Run directive
result = await registry.execute(
    item_type="directive",
    name="research_topic",
    inputs={
        "query": "Python best practices",
        "limit": 5
    }
)

if result['success']:
    print(f"Execution result: {result['result']}")
else:
    print(f"Execution failed: {result['error']}")
```

## Error Handling

### Not Found

```python
result = await registry.load(
    item_type="directive",
    name="nonexistent"
)

if not result['success']:
    print(f"Not found: {result['error']}")
```

### Bad Item Type

```python
result = await registry.load(
    item_type="invalid_type",  # Must be directive, tool, or knowledge
    name="something"
)

# Raises ValueError: Unknown item type
```

## Testing

```python
import pytest
from kiwi_mcp.handlers import TypeHandlerRegistry

@pytest.mark.asyncio
async def test_search_directives(tmp_path):
    """Test directive search."""
    # Create test directive
    directives_dir = tmp_path / ".ai" / "directives"
    directives_dir.mkdir(parents=True)
    (directives_dir / "test_directive.md").write_text("# Test")
    
    # Test search
    registry = TypeHandlerRegistry(project_path=str(tmp_path))
    results = await registry.search(
        item_type="directive",
        query="test"
    )
    
    assert len(results) > 0
    assert "test_directive" in results[0]['name']

@pytest.mark.asyncio
async def test_load_tool(tmp_path):
    """Test tool loading."""
    # Create test tool
    tools_dir = tmp_path / ".ai" / "tools"
    tools_dir.mkdir(parents=True)
    (tools_dir / "my_tool.yaml").write_text("tool_id: my_tool")
    
    # Test load
    registry = TypeHandlerRegistry(project_path=str(tmp_path))
    result = await registry.load(
        item_type="tool",
        name="my_tool"
    )
    
    assert result['success']
    assert "tool_id" in result['content']
```

## Limitations and Design

### By Design (Not a Bug)

1. **No content parsing**
   - Just file I/O
   - RYE parses content

2. **No validation**
   - No schema checking
   - No content validation

3. **Keyword search only**
   - Simple filename matching
   - RYE does semantic search

4. **Dumb routing**
   - Path-based only
   - No intelligence

## What Handlers DON'T Do

❌ **Lilux handlers don't:**
- Parse XML/YAML
- Validate schemas
- Understand content
- Rank search results
- Execute directives (beyond routing)
- Manage knowledge base

✅ **RYE handlers do all of this**

## Handler Limits

| Aspect | Lilux | RYE |
|--------|-------|-----|
| **Parsing** | None | Full |
| **Validation** | None | Schema-based |
| **Search** | Keyword only | Keyword + semantic |
| **Content understanding** | None | Full |
| **Routing** | Path-based | Content-based |

## Next Steps

- See legacy tools: `[[lilux/tools/overview]]`
- See RYE handlers: `[[rye/content-handlers/overview]]`
- See utilities: `[[lilux/utils/overview]]`
