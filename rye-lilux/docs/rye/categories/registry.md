**Source:** Original implementation: `rye-lilux/rye/.ai/tools/core/registry.py` in kiwi-mcp

# Registry Category

## Purpose

Registry tools provide **tool distribution and package management** functionality.

**Location:** `.ai/tools/rye/registry/`  
**Count:** 1 tool  
**Executor:** `http_client`

## Core Registry Tool

### Registry Operations (`registry.py`)

**Purpose:** Manage tool registry (publish, pull, search)

```python
__tool_type__ = "python"
__executor_id__ = "http_client"  # Uses HTTP for remote operations
__category__ = "registry"

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "operation": {
            "type": "string",
            "enum": ["publish", "pull", "search", "auth", "key"]
        },
        "package": {"type": "string", "description": "Package name"},
        "version": {"type": "string", "description": "Package version (semver)"},
        "registry": {"type": "string", "description": "Registry endpoint"},
    },
    "required": ["operation", "registry"]
}
```

## Operations

### Publish

**Push tool to registry**

```bash
Call registry with:
  operation: "publish"
  package: "my-tool"
  version: "1.0.0"
  registry: "https://registry.rye-lilux.dev"
```

**Process:**
1. Validate tool format
2. Create package bundle
3. Sign with credentials
4. Upload to registry
5. Update registry index

### Pull

**Fetch tool from registry**

```bash
Call registry with:
  operation: "pull"
  package: "my-tool"
  version: "1.0.0"
  registry: "https://registry.rye-lilux.dev"
```

**Process:**
1. Query registry for package
2. Verify signatures
3. Download tool
4. Install to .ai/tools/
5. Update local registry

### Search

**Search registry for tools**

```bash
Call registry with:
  operation: "search"
  package: "git*"
  registry: "https://registry.rye-lilux.dev"
```

**Returns:**
```json
{
  "results": [
    {
      "name": "git",
      "version": "1.0.0",
      "author": "rye-team",
      "description": "Git operations",
      "downloads": 1234
    },
    {
      "name": "git-advanced",
      "version": "2.0.0",
      "author": "community",
      "description": "Advanced git features",
      "downloads": 456
    }
  ]
}
```

### Auth

**Manage registry authentication**

```bash
Call registry with:
  operation: "auth"
  action: "login"
  registry: "https://registry.rye-lilux.dev"
  username: "user@example.com"
```

**Actions:**
- `login` - Authenticate with registry
- `logout` - Remove credentials
- `whoami` - Show current user
- `token` - Manage API tokens

### Key

**Manage registry keys**

```bash
Call registry with:
  operation: "key"
  action: "create"
  name: "signing-key"
  registry: "https://registry.rye-lilux.dev"
```

**Actions:**
- `create` - Generate new key
- `list` - List all keys
- `delete` - Remove key
- `export` - Export public key

## Registry Architecture

```
Local .ai/tools/
    │
    ├─→ registry pull
    │   └─→ Remote Registry
    │       ├─ Package index
    │       ├─ Package files
    │       └─ Signatures
    │
    ├─→ registry push
    │   └─→ Remote Registry
    │       ├─ Upload files
    │       ├─ Sign package
    │       └─ Update index
    │
    └─→ registry search
        └─→ Remote Registry
            └─ Query index
```

## Package Metadata

Tools in registry include:

```yaml
name: git
version: 1.0.0
description: Git operations tool
author: rye-team
license: MIT

tool_type: python
executor_id: python_runtime
category: capabilities

config_schema: {...}
env_config: {...}

signatures:
  sha256: "..."
  pgp: "..."

dependencies:
  - subprocess:>=1.0.0
  - python_runtime:>=2.0.0
```

## Registry Endpoints

### Public Registry

```
https://registry.rye-lilux.dev
```

Discover and install community tools

### Private Registry

```
https://registry.mycompany.com
```

Host internal tools

### Local Registry

```
file:///home/user/.local/rye-registry
```

Offline package management

## Metadata Pattern

Registry is a single special tool:

```python
# .ai/tools/rye/registry/registry.py

__version__ = "1.0.0"
__tool_type__ = "python"
__executor_id__ = "http_client"  # Remote operations
__category__ = "registry"

CONFIG_SCHEMA = { ... }

def main(**kwargs) -> dict:
    """Registry operations."""
    pass
```

## Usage Examples

### Publish Custom Tool

```bash
Call registry with:
  operation: "publish"
  package: "my-custom-tool"
  version: "1.0.0"
  registry: "https://registry.rye-lilux.dev"
```

### Install Tool from Registry

```bash
Call registry with:
  operation: "pull"
  package: "community-tool"
  version: "2.0.0"
  registry: "https://registry.rye-lilux.dev"
```

### Search for Tools

```bash
Call registry with:
  operation: "search"
  package: "*database*"
  registry: "https://registry.rye-lilux.dev"
```

## Key Characteristics

| Aspect | Detail |
|--------|--------|
| **Count** | 1 tool |
| **Location** | `.ai/tools/rye/registry/` |
| **Executor** | `http_client` |
| **Purpose** | Tool distribution & management |
| **Operations** | publish, pull, search, auth, key |
| **Remote** | HTTP-based registry endpoints |

## Related Documentation

- [[overview]] - All categories
- [[../bundle/structure]] - Bundle organization
- [[../universal-executor/routing]] - How HTTP executor works
