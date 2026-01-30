**Source:** Original implementation: `kiwi_mcp/primitives/chain_validator.py` in kiwi-mcp

# ChainValidator Primitive

## Purpose

Validate parent→child relationships in execution chains. Each tool can define what children it accepts, and ChainValidator verifies compatibility before execution.

## Key Classes

### ChainValidationResult

Result of chain validation:

```python
@dataclass
class ChainValidationResult:
    valid: bool                    # Whether chain is valid
    issues: List[str]             # Fatal validation errors
    warnings: List[str]           # Non-fatal warnings
    validated_pairs: int          # Number of (parent, child) pairs checked
```

### ChainValidator

The validator:

```python
class ChainValidator:
    def validate_chain(
        self, 
        chain: List[Dict[str, Any]]
    ) -> ChainValidationResult:
        """Validate each (child, parent) pair in the chain."""
```

## The Problem: Incompatible Tools

Without validation:

```
Tool A outputs: JSON object
Tool B expects: JSON array

A → B → Crash!
```

With validation:

```
Tool A outputs: JSON object
Tool B expects: JSON array

Validator detects mismatch → Error before execution
```

## Execution Chain Structure

Tools form a chain from leaf to root:

```
[leaf_script, runtime, middleware, primitive]
    ↓           ↓         ↓          ↓
 "Python"   "Resolver"  "Validator" "Subprocess"
  
Chain[0] ← called by
Chain[1] ← called by
Chain[2] ← called by
Chain[3] (primitive, root of chain)
```

ChainValidator checks:
1. Can `chain[1]` (runtime) call `chain[0]` (leaf)?
2. Can `chain[2]` (middleware) call `chain[1]` (runtime)?
3. Etc.

## Example: Validate a Chain

### Simple Valid Chain

```python
from lilux.primitives import ChainValidator

validator = ChainValidator()

chain = [
    {
        "tool_id": "csv_reader",
        "outputs": ["json_array"]
    },
    {
        "tool_id": "json_processor",
        "inputs": ["json_array"],
        "outputs": ["json_object"]
    },
    {
        "tool_id": "subprocess",
        "inputs": ["json_object"]
    }
]

result = validator.validate_chain(chain)

assert result.valid == True
assert len(result.issues) == 0
assert result.validated_pairs == 2
```

### Invalid Chain (Incompatible Types)

```python
chain = [
    {
        "tool_id": "csv_reader",
        "outputs": ["json_array"]  # Outputs array
    },
    {
        "tool_id": "json_processor",
        "inputs": ["json_object"],  # Expects object!
        "outputs": ["json_object"]
    }
]

result = validator.validate_chain(chain)

assert result.valid == False
assert len(result.issues) > 0
assert "json_object" in result.issues[0]
```

## How Validation Works

### 1. Define Child Schemas

Each tool can define acceptable children:

```python
tool_definition = {
    "tool_id": "processor",
    "validation": {
        "child_schemas": [
            {
                "tool_id": "reader",
                "outputs_must_include": ["json"]
            },
            {
                "tool_id": "formatter",
                "outputs_must_include": ["string"]
            }
        ]
    }
}
```

### 2. Check Each Adjacent Pair

```python
# For each (child, parent) pair:
# 1. Get parent's expected inputs
# 2. Get child's actual outputs
# 3. Check if outputs match inputs

child = chain[i]      # "csv_reader" outputs ["json_array"]
parent = chain[i+1]   # "processor" expects inputs ["json_array"]

if child.outputs matches parent.inputs:
    print("✓ Compatible")
else:
    print("✗ Incompatible")
```

### 3. Collect Results

```python
result = ChainValidationResult(
    valid=True,
    issues=[],          # No fatal errors
    warnings=[],        # No warnings
    validated_pairs=2   # Checked 2 pairs
)
```

## Architecture Role

ChainValidator is part of the **execution safety layer**:

1. **Pre-execution validation** - Catch errors early
2. **Type checking** - Ensure compatible I/O
3. **Chain verification** - Full chain is correct
4. **Early failure** - Fail fast, not during execution

## RYE Relationship

RYE uses ChainValidator when:
- Executing a multi-tool chain
- Need to verify parent-child compatibility
- Prevent runtime type errors

**Pattern:**
```python
# RYE builds chain from tool definitions
chain = build_chain(root_tool)

# Validate before execution
result = validator.validate_chain(chain)
if not result.valid:
    raise ValueError(f"Chain validation failed: {result.issues}")

# Then execute
result = await executor.execute(chain)
```

See `[[rye/universal-executor/overview]]` for executor integration.

## Validation Rules

### Input/Output Matching

Child's outputs must match or exceed parent's inputs:

```python
# Valid
child.outputs = ["json"]
parent.inputs = ["json"]  # Exact match

# Valid
child.outputs = ["json", "xml"]
parent.inputs = ["json"]  # Parent gets what it needs

# Invalid
child.outputs = ["xml"]
parent.inputs = ["json"]  # Parent doesn't get what it needs
```

### Schema Validation

If tools define schemas, they're checked:

```python
child_schema = {
    "outputs": {
        "data": {
            "type": "array",
            "items": {"type": "object"}
        }
    }
}

parent_schema = {
    "inputs": {
        "data": {
            "type": "array",
            "items": {"type": "object"}
        }
    }
}

# Schemas must be compatible
```

### Version Constraints

Tools can specify version requirements:

```python
parent_def = {
    "tool_id": "processor",
    "child_constraints": {
        "reader": {
            "min_version": "1.0.0",
            "max_version": "2.0.0"
        }
    }
}

# If reader is v0.9.0 or v2.1.0, validation fails
```

## Error Types

### Missing Output

```python
chain = [
    {"tool_id": "reader", "outputs": ["data"]},
    {"tool_id": "processor", "inputs": ["data", "config"]}
]

# processor expects "config" but reader doesn't provide it
result = validator.validate_chain(chain)
assert result.valid == False
assert "config" in result.issues[0]
```

### Type Mismatch

```python
chain = [
    {"tool_id": "reader", "outputs": ["json_array"]},
    {"tool_id": "processor", "inputs": ["json_object"]}
]

result = validator.validate_chain(chain)
assert result.valid == False
assert "type mismatch" in result.issues[0].lower()
```

### Version Incompatibility

```python
chain = [
    {"tool_id": "reader", "version": "0.9.0", "outputs": ["json"]},
    {
        "tool_id": "processor",
        "child_constraints": {
            "reader": {"min_version": "1.0.0"}
        }
    }
]

result = validator.validate_chain(chain)
assert result.valid == False
assert "version" in result.issues[0].lower()
```

## Warning Conditions

Warnings are non-fatal (chain still valid):

```python
chain = [
    {"tool_id": "reader", "outputs": ["json"]},
    {"tool_id": "processor", "inputs": ["json"]}
]

result = validator.validate_chain(chain)
assert result.valid == True
assert len(result.warnings) > 0
# e.g., "reader is version 1.0.0, newer 2.0.0 available"
```

## Best Practices

### 1. Define Schemas in Tools

```python
tool_def = {
    "tool_id": "csv_reader",
    "outputs": {
        "schema": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"}
                }
            }
        }
    }
}
```

### 2. Validate Early

```python
# Validate before execution starts
result = validator.validate_chain(chain)
if not result.valid:
    # Fail fast
    for issue in result.issues:
        logger.error(f"Chain error: {issue}")
    raise ChainValidationError(result)
```

### 3. Log Warnings

```python
result = validator.validate_chain(chain)
for warning in result.warnings:
    logger.warning(f"Chain warning: {warning}")
```

## Testing

```python
import pytest
from lilux.primitives import ChainValidator

def test_valid_chain():
    validator = ChainValidator()
    
    chain = [
        {"tool_id": "reader", "outputs": ["json"]},
        {"tool_id": "processor", "inputs": ["json"], "outputs": ["result"]}
    ]
    
    result = validator.validate_chain(chain)
    assert result.valid
    assert result.validated_pairs == 1

def test_invalid_chain():
    validator = ChainValidator()
    
    chain = [
        {"tool_id": "reader", "outputs": ["xml"]},
        {"tool_id": "processor", "inputs": ["json"]}
    ]
    
    result = validator.validate_chain(chain)
    assert not result.valid
    assert len(result.issues) > 0
```

## Lazy Loading

ChainValidator uses lazy loading for SchemaValidator:

```python
# First use - loads SchemaValidator
validator = ChainValidator()
result = validator.validate_chain(chain)  # Loads now

# Second use - already loaded
result = validator.validate_chain(other_chain)  # Fast
```

If SchemaValidator is unavailable, ChainValidator still works (basic validation only).

## Limitations and Design

### By Design (Not a Bug)

1. **No runtime enforcement**
   - Validates chain structure
   - Doesn't monitor actual execution
   - See `[[lilux/primitives/integrity]]` for runtime verification

2. **Schema optional**
   - Works with or without detailed schemas
   - Basic I/O matching always available
   - Detailed schema validation if provided

3. **No ordering**
   - Doesn't validate that tools are in correct order
   - RYE executor handles ordering
   - Validator just checks adjacent pairs

## Next Steps

- See integrity: `[[lilux/primitives/integrity]]`
- See lockfile: `[[lilux/primitives/lockfile]]`
- See RYE executor: `[[rye/universal-executor/overview]]`
