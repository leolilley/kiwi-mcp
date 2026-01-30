**Source:** Original implementation: `kiwi_mcp/schemas/tool_schema.py` in kiwi-mcp

# Schemas Overview

## Purpose

Lilux schemas define JSON Schema representations of tools. Schemas describe tool parameters, inputs, outputs, and validation rules.

## Key Classes

### Tool Schema

JSON Schema definition for a tool:

```python
{
    "tool_id": "csv_reader",
    "version": "1.0.0",
    "schema": {
        "type": "object",
        "properties": {
            "file": {
                "type": "string",
                "description": "Path to CSV file"
            },
            "delimiter": {
                "type": "string",
                "default": ",",
                "description": "Field delimiter"
            }
        },
        "required": ["file"]
    }
}
```

### Schema Validation

Validate parameters against tool schema:

```python
from kiwi_mcp.schemas import validate_tool_call

result = validate_tool_call(
    tool_id="csv_reader",
    parameters={"file": "data.csv", "delimiter": ";"}
)

assert result.valid  # True if parameters match schema
```

## Schema Structure

### Complete Tool Schema

```json
{
  "tool_id": "process_data",
  "version": "1.0.0",
  "name": "Data Processor",
  "description": "Process and transform data",
  "executor": "subprocess",
  "config": {
    "command": "python",
    "args": ["processor.py"]
  },
  "inputs": {
    "type": "object",
    "properties": {
      "input_file": {
        "type": "string",
        "description": "Input file path"
      },
      "format": {
        "type": "string",
        "enum": ["csv", "json", "parquet"],
        "default": "csv"
      },
      "validate": {
        "type": "boolean",
        "default": true
      }
    },
    "required": ["input_file"]
  },
  "outputs": {
    "type": "object",
    "properties": {
      "data": {
        "type": "array",
        "items": {"type": "object"}
      },
      "errors": {
        "type": "array",
        "items": {"type": "string"}
      }
    }
  }
}
```

## Schema Validation

### Validate Parameters

```python
from kiwi_mcp.utils.schema_validator import SchemaValidator

validator = SchemaValidator()

# Schema from tool
schema = {
    "type": "object",
    "properties": {
        "count": {"type": "integer"},
        "name": {"type": "string"}
    },
    "required": ["name"]
}

# Validate parameters
result = validator.validate(
    instance={"name": "Alice", "count": 10},
    schema=schema
)

assert result.valid  # True
```

### Validation Errors

```python
# Missing required field
result = validator.validate(
    instance={"count": 10},  # Missing "name"
    schema=schema
)

assert not result.valid
assert len(result.errors) > 0
# Error: 'name' is a required property
```

## Architecture Role

Schemas are part of the **validation and description layer**:

1. **Parameter validation** - Check tool inputs
2. **Type checking** - Ensure correct types
3. **Description** - Document tool usage
4. **MCP exposure** - Define tool interface

## RYE Relationship

RYE uses schemas for:
- Tool definition and validation
- MCP schema publication
- Parameter checking before execution
- Documentation generation

**Pattern:**
```python
# RYE's tool manager
schema = load_tool_schema(tool_id, version)

# Validate user parameters
result = validator.validate(user_params, schema.inputs)
if not result.valid:
    raise ValueError(f"Invalid parameters: {result.errors}")

# Execute with validated parameters
result = await execute_tool(tool_id, user_params)
```

See `[[rye/categories/primitives]]` for tool schema details.

## Best Practices

### 1. Define Clear Schemas

```json
{
  "properties": {
    "file_path": {
      "type": "string",
      "description": "Path to input file",
      "pattern": "^[/.].*\\.(csv|json|txt)$"
    },
    "encoding": {
      "type": "string",
      "default": "utf-8",
      "enum": ["utf-8", "latin-1", "ascii"]
    }
  },
  "required": ["file_path"]
}
```

### 2. Provide Default Values

```json
{
  "properties": {
    "timeout": {
      "type": "integer",
      "default": 300,
      "minimum": 1,
      "maximum": 3600
    },
    "retries": {
      "type": "integer",
      "default": 3
    }
  }
}
```

### 3. Document with Descriptions

```json
{
  "properties": {
    "api_key": {
      "type": "string",
      "description": "API key for authentication (from $API_KEY env var)"
    },
    "endpoint": {
      "type": "string",
      "description": "API endpoint URL (default: https://api.example.com)"
    }
  }
}
```

## JSON Schema Features Used

### Data Types

```json
{
  "properties": {
    "name": { "type": "string" },
    "age": { "type": "integer" },
    "score": { "type": "number" },
    "active": { "type": "boolean" },
    "tags": { "type": "array", "items": { "type": "string" } },
    "config": { "type": "object", "properties": {...} }
  }
}
```

### Constraints

```json
{
  "properties": {
    "age": {
      "type": "integer",
      "minimum": 0,
      "maximum": 150
    },
    "email": {
      "type": "string",
      "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
    },
    "format": {
      "type": "string",
      "enum": ["csv", "json", "xml"]
    }
  }
}
```

### Required Fields

```json
{
  "properties": {
    "file": { "type": "string" },
    "delimiter": { "type": "string", "default": "," }
  },
  "required": ["file"]  // file is required, delimiter is optional
}
```

## Testing

```python
import pytest
from kiwi_mcp.utils.schema_validator import SchemaValidator

def test_validate_tool_parameters():
    validator = SchemaValidator()
    
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "count": {"type": "integer", "minimum": 1}
        },
        "required": ["name"]
    }
    
    # Valid
    result = validator.validate(
        {"name": "test", "count": 5},
        schema
    )
    assert result.valid
    
    # Invalid - missing required
    result = validator.validate(
        {"count": 5},
        schema
    )
    assert not result.valid
    
    # Invalid - wrong type
    result = validator.validate(
        {"name": "test", "count": "five"},
        schema
    )
    assert not result.valid
```

## Limitations and Design

### By Design (Not a Bug)

1. **Lilux has minimal schemas**
   - Just JSON Schema support
   - No custom validation logic

2. **RYE handles content schemas**
   - Directive validation
   - Knowledge validation
   - Tool metadata

3. **No automatic generation**
   - Schemas must be written manually
   - Or generated by RYE tooling

## Next Steps

- See tool schema file: `[[lilux/schemas/tool-schema]]`
- See utils: `[[lilux/utils/overview]]`
- See RYE schemas: `[[rye/categories/primitives]]`
