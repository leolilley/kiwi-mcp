**Source:** Original implementation: `kiwi_mcp/schemas/tool_schema.py` in kiwi-mcp

# Tool Schema Details

## Purpose

Define and extract tool parameters using JSON Schema definitions. Tool schemas describe what inputs a tool accepts and what outputs it produces.

## Schema Components

### Tool Definition Schema

```python
{
    "tool_id": "string",           # Unique identifier
    "version": "string",           # Semantic version
    "name": "string",              # Human-readable name
    "description": "string",       # What this tool does
    "executor": "string",          # Executor type
    "config": {                    # Tool-specific config
        "command": "string",
        ...
    },
    "inputs": {...},               # Input schema (JSON Schema)
    "outputs": {...}               # Output schema (JSON Schema)
}
```

## Executor-Specific Schemas

### Subprocess Tool

```python
{
    "tool_id": "run_script",
    "executor": "subprocess",
    "config": {
        "command": "python",
        "args": ["script.py"],
        "env": {
            "DEBUG": "1"
        }
    },
    "inputs": {
        "type": "object",
        "properties": {
            "data": {"type": "string"}
        }
    },
    "outputs": {
        "type": "object",
        "properties": {
            "result": {"type": "string"},
            "errors": {"type": "array"}
        }
    }
}
```

### HTTP Client Tool

```python
{
    "tool_id": "api_call",
    "executor": "http_client",
    "config": {
        "method": "POST",
        "url": "https://api.example.com/data",
        "headers": {
            "Content-Type": "application/json"
        }
    },
    "inputs": {
        "type": "object",
        "properties": {
            "payload": {"type": "object"},
            "timeout": {"type": "integer", "default": 30}
        },
        "required": ["payload"]
    },
    "outputs": {
        "type": "object",
        "properties": {
            "status": {"type": "integer"},
            "body": {}
        }
    }
}
```

## Parameter Validation

### Simple Validation

```python
from kiwi_mcp.schemas import validate_parameters

schema = {
    "type": "object",
    "properties": {
        "file": {"type": "string"},
        "format": {
            "type": "string",
            "enum": ["csv", "json"]
        }
    },
    "required": ["file"]
}

# Valid
result = validate_parameters(
    parameters={"file": "data.csv", "format": "csv"},
    schema=schema
)
assert result.valid

# Invalid - missing required
result = validate_parameters(
    parameters={"format": "csv"},
    schema=schema
)
assert not result.valid
```

### Complex Validation

```python
schema = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"}
                },
                "required": ["id"]
            },
            "minItems": 1
        }
    },
    "required": ["items"]
}

result = validate_parameters(
    parameters={
        "items": [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"}
        ]
    },
    schema=schema
)
```

## Common Patterns

### Optional Field with Default

```json
{
  "properties": {
    "retries": {
      "type": "integer",
      "default": 3,
      "minimum": 0
    }
  }
}
```

### Constrained String

```json
{
  "properties": {
    "status": {
      "type": "string",
      "enum": ["pending", "active", "done"],
      "description": "Task status"
    },
    "email": {
      "type": "string",
      "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
    }
  }
}
```

### Nested Objects

```json
{
  "properties": {
    "config": {
      "type": "object",
      "properties": {
        "timeout": {"type": "integer"},
        "retries": {"type": "integer"}
      },
      "required": ["timeout"]
    }
  }
}
```

### Arrays

```json
{
  "properties": {
    "files": {
      "type": "array",
      "items": {"type": "string"},
      "minItems": 1,
      "description": "List of file paths"
    },
    "configs": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "key": {"type": "string"},
          "value": {"type": "string"}
        }
      }
    }
  }
}
```

## Parser Support

Tool schema supports different content parsers:

### Text Parser (Built-in)

```python
# No processing
parser = get_parser("text")
result = parser(file_content)
# Returns: {"content": file_content}
```

### Custom Parsers

Load custom parsers from `.ai/parsers/`:

```python
# .ai/parsers/csv_parser.py
def parse(content):
    import csv
    from io import StringIO
    
    reader = csv.DictReader(StringIO(content))
    return {"rows": list(reader)}

# Use in tool schema
parser = get_parser("csv_parser", project_path="/project")
result = parser(file_content)
# Returns: {"rows": [...]}
```

Parser search order:
1. Project `.ai/parsers/`
2. Working directory `.ai/parsers/`
3. User `~/.ai/parsers/`
4. Fallback: text parser

## Dynamic Extraction

Tool schema can extract parameters dynamically:

```python
EXTRACTION_RULES = {
    "tool_id": {
        "pattern": r"^([a-z_]+)$",
        "source": "filename"
    },
    "version": {
        "default": "1.0.0"
    },
    "executor": {
        "pattern": r"executor[\"']\s*:\s*[\"'](\w+)[\"']",
        "source": "config"
    }
}
```

## Architecture Role

Tool schemas are part of the **validation and description layer**:

1. **Parameter validation** - Check inputs
2. **Type definition** - Document types
3. **MCP interface** - Expose to LLM
4. **Documentation** - Generate docs

## RYE Relationship

RYE uses tool schemas for:
- Tool definition validation
- Parameter validation before execution
- MCP schema publication
- Documentation generation
- Tool discovery and filtering

See `[[rye/categories/primitives]]` for complete schema structure.

## Best Practices

### 1. Define Input Schema

Always define what your tool accepts:

```json
{
  "tool_id": "process",
  "inputs": {
    "type": "object",
    "properties": {
      "data": {
        "type": "string",
        "description": "Input data to process"
      }
    },
    "required": ["data"]
  }
}
```

### 2. Define Output Schema

Document what your tool returns:

```json
{
  "outputs": {
    "type": "object",
    "properties": {
      "result": {
        "type": "string",
        "description": "Processing result"
      },
      "status": {
        "type": "string",
        "enum": ["success", "error"]
      }
    }
  }
}
```

### 3. Use Enums for Constrained Values

```json
{
  "properties": {
    "format": {
      "type": "string",
      "enum": ["csv", "json", "xml"],
      "default": "json"
    }
  }
}
```

### 4. Add Constraints

```json
{
  "properties": {
    "max_items": {
      "type": "integer",
      "minimum": 1,
      "maximum": 10000,
      "default": 100
    }
  }
}
```

## Testing

```python
import pytest
from kiwi_mcp.schemas import tool_schema

def test_validate_subprocess_tool():
    """Test validation of subprocess tool schema."""
    tool = {
        "tool_id": "test_script",
        "executor": "subprocess",
        "config": {
            "command": "python",
            "args": ["script.py"]
        },
        "inputs": {
            "type": "object",
            "properties": {
                "input_file": {"type": "string"}
            },
            "required": ["input_file"]
        }
    }
    
    # Validate schema structure
    assert tool["tool_id"]
    assert tool["executor"] == "subprocess"
    assert "inputs" in tool

def test_validate_tool_parameters():
    """Test parameter validation against schema."""
    schema = {
        "type": "object",
        "properties": {
            "file": {"type": "string"},
            "count": {"type": "integer"}
        },
        "required": ["file"]
    }
    
    # Valid parameters
    from kiwi_mcp.schemas import validate_parameters
    result = validate_parameters(
        {"file": "data.csv", "count": 10},
        schema
    )
    assert result.valid
    
    # Invalid - missing required
    result = validate_parameters(
        {"count": 10},
        schema
    )
    assert not result.valid
```

## Limitations and Design

### By Design (Not a Bug)

1. **Lilux has minimal schema support**
   - JSON Schema validation only
   - No custom validators

2. **RYE validates content**
   - Directive XML validation
   - Knowledge frontmatter validation
   - Tool manifest validation

3. **No code generation**
   - Schemas are declarative only
   - Generate code in RYE if needed

## Next Steps

- See overview: `[[lilux/schemas/overview]]`
- See utils: `[[lilux/utils/overview]]`
- See RYE: `[[rye/categories/primitives]]`
