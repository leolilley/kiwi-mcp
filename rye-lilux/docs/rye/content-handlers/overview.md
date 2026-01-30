**Source:** Original implementation: `kiwi_mcp/handlers/` in kiwi-mcp

# Content Handlers Overview

## Purpose

Content handlers provide **intelligent parsing and understanding** of different content formats used in RYE.

## Content Handler Architecture

```
RYE Content
    │
    ├─→ XML Content (Directives)
    │   └─→ XML Handler
    │       ├─ Parse XML structure
    │       ├─ Extract metadata
    │       └─ Validate schema
    │
    ├─→ Markdown Content (Knowledge)
    │   └─→ Frontmatter Handler
    │       ├─ Parse YAML frontmatter
    │       ├─ Parse Markdown body
    │       └─ Extract metadata
    │
    └─→ Python/YAML Content (Tools)
        └─→ Metadata Handler
            ├─ Parse Python AST
            ├─ Parse YAML config
            └─ Extract metadata
```

## Handler Types

### 1. XML Handler

**Purpose:** Parse XML directives

**Handles:**
- Directive definitions
- XML structure validation
- Element extraction

**Key Features:**
- Schema validation
- Category support
- Element traversal

### 2. Frontmatter Handler

**Purpose:** Parse YAML frontmatter + Markdown content

**Handles:**
- Knowledge entries
- YAML frontmatter
- Markdown body
- Metadata extraction

**Key Features:**
- Separator detection (---)
- YAML parsing
- Markdown parsing
- Frontmatter validation

### 3. Metadata Handler

**Purpose:** Extract metadata from Python and YAML tools

**Handles:**
- Python files
- YAML config files
- Metadata attributes
- Schema extraction

**Key Features:**
- AST parsing (Python)
- YAML structure reading
- Metadata validation
- Schema extraction

## Usage Pattern

Content handlers are used internally by extractors:

```
Content File (XML, Markdown, YAML, Python)
    │
    ├─→ Content Handler parses content
    │
    ├─→ Returns parsed structure
    │
    └─→ Extractor uses structure
        └─→ Returns metadata
```

## Parsing Pipeline

### Directive Parsing

```
.xml file
    │
    └─→ XML Handler
        ├─ Load XML
        ├─ Validate schema
        └─→ Extract:
            ├─ name
            ├─ version
            ├─ description
            ├─ inputs
            ├─ process
            └─ outputs
```

### Knowledge Parsing

```
.md file
    │
    └─→ Frontmatter Handler
        ├─ Split frontmatter & body
        ├─ Parse YAML frontmatter
        ├─ Parse Markdown body
        └─→ Extract:
            ├─ zettel_id
            ├─ title
            ├─ entry_type
            ├─ tags
            ├─ references
            └─ content
```

### Tool Metadata Extraction

```
.py or .yaml file
    │
    ├─→ Python AST Handler
    │   └─ Extract:
    │       ├─ __version__
    │       ├─ __tool_type__
    │       ├─ __executor_id__
    │       ├─ __category__
    │       ├─ CONFIG_SCHEMA
    │       └─ ENV_CONFIG
    │
    └─→ YAML Handler
        └─ Extract:
            ├─ name
            ├─ version
            ├─ tool_type
            ├─ executor_id
            ├─ config
            └─ env_config
```

## Handler Integration

Handlers work with Parsers and Extractors:

```
Content Files
    │
    ├─→ Handlers (parse format)
    │   ├─ XML Handler
    │   ├─ Frontmatter Handler
    │   └─ Metadata Handler
    │
    ├─→ Parsers (format-specific)
    │   ├─ Markdown XML Parser
    │   ├─ Frontmatter Parser
    │   ├─ Python AST Parser
    │   └─ YAML Parser
    │
    └─→ Extractors (content-specific)
        ├─ Directive Extractor
        ├─ Knowledge Extractor
        └─ Tool Extractor
```

## Key Characteristics

| Aspect | Detail |
|--------|--------|
| **Purpose** | Parse content formats |
| **Formats** | XML, Markdown, YAML, Python |
| **Integration** | Used by Parsers and Extractors |
| **Validation** | Schema validation included |
| **Metadata** | Extract structured metadata |

## Content Handler Standards

### Input

- File path or content string
- Optional validation schema

### Processing

1. Parse format
2. Validate structure
3. Extract metadata
4. Return structured data

### Output

```python
{
    "format": "xml" | "markdown" | "python" | "yaml",
    "valid": true | false,
    "metadata": {...},
    "content": {...},
    "errors": [],
    "warnings": []
}
```

## Error Handling

Handlers provide detailed error information:

```python
{
    "valid": False,
    "errors": [
        {
            "type": "ParseError",
            "message": "Invalid XML structure",
            "line": 5,
            "column": 12
        }
    ],
    "warnings": [
        {
            "type": "DeprecatedField",
            "message": "Field 'old_name' is deprecated"
        }
    ]
}
```

## Related Documentation

- [[../parsers]] - Data format parsers
- [[../extractors]] - Data extraction utilities
- [[../universal-executor/overview]] - Executor architecture
- [[../bundle/structure]] - Bundle organization
