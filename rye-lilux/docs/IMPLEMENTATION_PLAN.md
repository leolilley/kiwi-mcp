# Lilux/RYE Implementation Plan: Data-Driven Architecture Migration

**Date:** 2026-01-30
**Status:** Ready for Implementation
**Purpose:** Comprehensive step-by-step plan to migrate to data-driven microkernel + OS architecture

**References:**

- Architecture: See `docs/ARCHITECTURE.md` for data-driven microkernel + OS design
- Data-Driven Analysis: See `docs/COMPLETE_DATA_DRIVEN_ARCHITECTURE.md` for complete architecture breakdown
- Current Status: See git status for existing files

---

## Phase 0: Current State Assessment

### 0.1: Audit Current State

**Status:** ✅ Already Done (Phase 1 complete)

```bash
cd /home/leo/projects/kiwi-mcp/rye-lilux

# Clean up unused files (already done)
rm lilux/utils/env_manager.py
rm lilux/utils/file_search.py
rm lilux/utils/files.py
rm lilux/utils/search/scoring.py
rm lilux/utils/signature_formats.py
rm lilux/utils/xml_error_helper.py

# Rename for clarity (already done)
git mv lilux/handlers/registry.py lilux/handlers/handler_registry.py
```

**Phase 1 Already Completed:**

- ✅ 1.1: Lilux handlers dumbed down (86/130/130 lines, no intelligence)
- ✅ 1.2: Lilux parsers simplified (minimal helpers only)
- ✅ 1.3: Lilux validators simplified (primitive validation only)
- ✅ 1.4: Lilux utils init updated
- ✅ 1.5: Lilux handlers init updated

**Current Lilux State:**

- Handlers are dumb routers (no content intelligence)
- Primitives are clean and minimal
- Ready for Phase 2

### 0.2: Verify MCP Server Entry Point

**Status:** 🔄 To Do
**Priority:** P0 (Depends on Phase 1)
**Estimated Time:** 30 min

**Required:** Verify MCP server can start after removing content intelligence and implementing universal executor.

---

## Phase 1: Fix Kernel Dependencies (Dumb Routing)

**Status:** ✅ Already Complete

### 1.1-1.5: Complete (See Phase 0.1 above)

All Lilux handlers are now dumb routers that:

- Resolve file paths
- List files in project/user spaces
- Copy files between spaces
- No parsing, no validation, no intelligence

---

## Phase 2: Add Primitive Schemas to RYE Bundle (NEW)

### 2.1: Create RYE Primitive Schemas Directory

**Status:** 🔄 To Do
**Priority:** P0 (Blocks universal executor)
**Estimated Time:** 30 min

**Create:**

```bash
cd /home/leo/projects/kiwi-mcp/rye-lilux/rye
mkdir -p .ai/tools/rye/primitives
```

### 2.2: Copy Primitive Schemas from kiwi-mcp

**Status:** 🔄 To Do
**Priority:** P0 (Blocks tool execution)
**Estimated Time:** 15 min

**Copy:**

```bash
cd /home/leo/projects/kiwi-mcp

# Copy primitive schemas (data/metadata only)
cp .ai/tools/primitives/subprocess.py /home/leo/projects/kiwi-mcp/rye-lilux/rye/.ai/tools/rye/primitives/
cp .ai/tools/primitives/http_client.py /home/leo/projects/kiwi-mcp/rye-lilux/rye/.ai/tools/rye/primitives/
cp .ai/tools/primitives/lockfile.py /home/leo/projects/kiwi-mcp/rye-lilux/rye/.ai/tools/rye/primitives/
cp .ai/tools/primitives/auth.py /home/leo/projects/kiwi-mcp/rye-lilux/rye/.ai/tools/rye/primitives/
cp .ai/tools/primitives/chain_validator.py /home/leo/projects/kiwi-mcp/rye-lilux/rye/.ai/tools/rye/primitives/
```

**Note:** These are SCHEMA FILES only (CONFIG_SCHEMA + metadata). Actual execution code remains in `lilux/primitives/*.py`.

**Key Features:**

1. Define `__tool_type__ = "primitive"`
2. Define `__executor_id__ = None` (base executor)
3. Define `__category__ = "primitives"`
4. Define `CONFIG_SCHEMA` (JSON Schema for parameters)
5. Define `__version__` for tracking

---

## Phase 3: Add Runtime Schemas to RYE Bundle (NEW)

### 3.1: Create RYE Runtime Schemas Directory

**Status:** 🔄 To Do
**Priority:** P0 (Blocks Python tools)
**Estimated Time:** 15 min

**Create:**

```bash
cd /home/leo/projects/kiwi-mcp/rye-lilux/rye
mkdir -p .ai/tools/rye/runtimes
```

### 3.2: Copy Runtime Schemas from kiwi-mcp

**Status:** 🔄 To Do
**Priority:** P0 (Blocks Python tools)
**Estimated Time:** 15 min

**Copy:**

```bash
cd /home/leo/projects/kiwi-mcp

# Copy runtime schemas (ENV_CONFIG + metadata)
cp .ai/tools/runtimes/python_runtime.py /home/leo/projects/kiwi-mcp/rye-lilux/rye/.ai/tools/rye/runtimes/
cp .ai/tools/runtimes/node_runtime.py /home/leo/projects/kiwi-mcp/rye-lilux/rye/.ai/tools/rye/runtimes/
cp .ai/tools/runtimes/mcp_http_runtime.py /home/leo/projects/kiwi-mcp/rye-lilux/rye/.ai/tools/rye/runtimes/
```

**Key Features:**

1. Define `__tool_type__ = "runtime"`
2. Define `__executor_id__` pointing to primitive (e.g., "subprocess")
3. Define `ENV_CONFIG` for environment resolution
4. Define `__category__ = "runtimes"`
5. Define `CONFIG` with template variables (`${VAR}`)

---

## Phase 4: Create Universal Executor in RYE

### 4.1: Create RYE Executor Directory

**Status:** 🔄 To Do
**Priority:** P1 (Depends on Phase 2-3)
**Estimated Time:** 30 min

**Create:**

```bash
cd /home/leo/projects/kiwi-mcp/rye-lilux/rye
mkdir -p executor
```

### 4.2: Create Universal Executor

**Status:** 🔄 To Do
**Priority:** P1 (Core of RYE)
**Estimated Time:** 3 hours

**File:** `rye/executor/universal_executor.py`

**Requirements:**

1. Parse tool metadata (`__tool_type__`, `__executor_id__`, `CONFIG_SCHEMA`)
2. Route via **data-driven recursive resolution** (NO hardcoded lists!):
   - Primitives (`__tool_type__ == "primitive"`, `__executor_id__ == None`)
   - Runtimes (`__tool_type__ == "runtime"`)
   - Tools (any type with `__executor_id__`)
3. Resolve executor chains via filesystem search (`.ai/tools/**/`)
4. Resolve environment variables via EnvResolver at execution time
5. Validate parameters against CONFIG_SCHEMA
6. Support YAML config files
7. Handle tool dependencies
8. Support multiple categorys (rye, user, etc.)

**Architecture Flow:**

```
RYE Universal Executor (Data-Driven)
    ↓ Parse metadata from tool file in .ai/tools/{category}/
    ↓ Check __executor_id__
    ↓
    if __executor_id__ is None:
        # LAYER 1: Primitive - execute directly
        Load Lilux primitive code via dynamic import
        Execute: lilux.primitives.{name}.execute(parameters)
    else:
        # LAYER 2+: Delegate via executor_id
        _resolve_executor_path(executor_id)  # ✅ Search filesystem
        ↓
        Load executor metadata from .ai/tools/...
        ↓
        if executor_type == "runtime":
            Resolve ENV_CONFIG via env_resolver
            Merge resolved env into parameters
        ↓
        RECURSIVE: execute(executor_path, parameters)
        # Continues until __executor_id__ is None (primitive)
```

**Key Data-Driven Methods:**

```python
class UniversalExecutor:
    # NO self.primitives or self.runtimes registries!

    def _resolve_executor_path(self, executor_id: str) -> Path:
        """Search .ai/tools/**/ for executor_id (data-driven)"""
        for category_dir in self.ai_tools_path.iterdir():
            # Search root and subdirectories
            for py_file in category_dir.rglob("*.py"):
                if py_file.stem == executor_id:
                    return py_file
        raise ValueError(f"Executor not found: {executor_id}")

    def execute_tool(self, tool_path: Path, parameters: dict) -> Any:
        """Recursive executor resolution (data-driven)"""
        metadata = self._load_metadata(tool_path)
        executor_id = metadata.get("__executor_id__")

        if executor_id is None:
            return self._execute_primitive(tool_path, parameters)

        # Resolve executor path (data-driven)
        executor_path = self._resolve_executor_path(executor_id)
        executor_metadata = self._load_metadata(executor_path)

        # Handle runtime environment resolution
        if executor_metadata.get("__tool_type__") == "runtime":
            resolved_env = self.env_resolver.resolve(
                executor_metadata.get("ENV_CONFIG")
            )
            parameters = {**parameters, **resolved_env}

        # Recursively execute (runtime → runtime → ... → primitive)
        return self.execute_tool(executor_path, parameters)
```

### 4.3: Create Metadata Parser

**Status:** 🔄 To Do
**Priority:** P1 (Depends on 4.2)
**Estimated Time:** 2 hours

**File:** `rye/executor/metadata_parser.py`

**Requirements:**

1. Parse metadata from Python files
2. Parse metadata from YAML configs
3. Extract `__tool_type__`, `__executor_id__`, `__category__`
4. Extract `CONFIG_SCHEMA`, `ENV_CONFIG`, `CONFIG`
5. Validate metadata structure

### 4.4: Create Schema Validator

**Status:** 🔄 To Do
**Priority:** P1 (Depends on 4.3)
**Estimated Time:** 1 hour

**File:** `rye/executor/schema_validator.py`

**Requirements:**

1. Validate CONFIG_SCHEMA (JSON Schema)
2. Validate ENV_CONFIG structure
3. Validate required metadata fields
4. Return detailed error messages

### 4.5: Create Environment Resolver

**Status:** 🔄 To Do
**Priority:** P1 (Depends on 4.4)
**Estimated Time:** 1 hour

**File:** `rye/executor/env_resolver.py`

**Requirements:**

1. Resolve template variables (${VAR_NAME})
2. Resolve runtime interpreters (Python, Node, etc.)
3. Apply ENV_CONFIG rules (search order, fallbacks)
4. Set environment variables

---

## Phase 5: Create RYE Utils (Intelligence Layer)

### 5.1: Create Metadata Manager

**Status:** 🔄 To Do
**Priority:** P1 (Depends on Phase 4)
**Estimated Time:** 3 hours

**File:** `rye/utils/metadata_manager.py`

**Requirements:**

1. Signature strategies (DirectiveStrategy, ToolStrategy, KnowledgeStrategy)
2. Hash computation (SHA-256)
3. Signature extraction/addition
4. Metadata extraction from all content types
5. Unified interface for all operations

### 5.2: Create Parsers

**Status:** 🔄 To Do
**Priority:** P1 (Depends on Phase 4)
**Estimated Time:** 3 hours

**File:** `rye/utils/parsers.py`

**Requirements:**

1. Directive XML parser (full schema)
2. Tool metadata parser (header + body)
3. Knowledge frontmatter parser (YAML)
4. YAML parser (for configs)
5. Error handling and validation

### 5.3: Create Validators

**Status:** 🔄 To Do
**Priority:** P1 (Depends on Phase 5.2)
**Estimated Time:** 2 hours

**File:** `rye/utils/validators.py`

**Requirements:**

1. DirectiveValidator (XML structure, required fields, permissions, models)
2. ToolValidator (metadata, executor config, inputs)
3. KnowledgeValidator (frontmatter, required fields)
4. ValidationManager (unified interface)
5. compare_versions() function
6. Detailed error messages

### 5.4: Create Content Handlers

**Status:** 🔄 To Do
**Priority:** P2 (Can use stubs initially)
**Estimated Time:** 4 hours

**Files:**

- `rye/handlers/directive/handler.py`
- `rye/handlers/tool/handler.py`
- `rye/handlers/knowledge/handler.py`

**Requirements:**

1. Parse specific content types
2. Extract metadata
3. Validate structure
4. Return enriched data

### 5.5: Update RYE Utils Init

**Status:** 🔄 To Do
**Priority:** P2 (After 5.1-5.4)
**Estimated Time:** 15 min

**File:** `rye/utils/__init__.py`

**Updates:**

```python
"""RYE utils - Intelligence layer."""

from rye.utils.metadata_manager import MetadataManager
from rye.utils.parsers import (
    parse_directive,
    parse_tool,
    parse_knowledge,
    parse_yaml,
)
from rye.utils.validators import (
    DirectiveValidator,
    ToolValidator,
    KnowledgeValidator,
    ValidationManager,
    compare_versions,
)
from rye.utils.resolvers import (
    DirectiveResolver,
    ToolResolver,
    KnowledgeResolver,
)

__all__ = [
    "MetadataManager",
    "parse_directive",
    "parse_tool",
    "parse_knowledge",
    "parse_yaml",
    "DirectiveValidator",
    "ToolValidator",
    "KnowledgeValidator",
    "ValidationManager",
    "compare_versions",
    "DirectiveResolver",
    "ToolResolver",
    "KnowledgeResolver",
]
```

---

## Phase 6: Bundle RYE Content (.ai/)

### 6.1: Create RYE .ai/ Directory Structure

**Status:** 🔄 To Do
**Priority:** P1 (Depends on Phase 4)
**Estimated Time:** 30 min

**Create:**

```bash
cd /home/leo/projects/kiwi-mcp/rye-lilux/rye
mkdir -p .ai/tools/rye
mkdir -p .ai/tools/rye/primitives
mkdir -p .ai/tools/rye/runtimes
mkdir -p .ai/tools/rye/capabilities
mkdir -p .ai/tools/rye/telemetry
mkdir -p .ai/tools/rye/extractors
mkdir -p .ai/tools/rye/extractors/directive
mkdir -p .ai/tools/rye/extractors/knowledge
mkdir -p .ai/tools/rye/extractors/tool
mkdir -p .ai/tools/rye/protocol
mkdir -p .ai/tools/rye/sinks
mkdir -p .ai/tools/rye/threads
mkdir -p .ai/tools/rye/mcp
mkdir -p .ai/tools/rye/llm
mkdir -p .ai/tools/rye/registry
mkdir -p .ai/tools/rye/python/lib
mkdir -p .ai/tools/rye/python
mkdir -p .ai/tools/rye/utility
mkdir -p .ai/directives/core
mkdir -p .ai/directives/implementation
mkdir -p .ai/directives/operations
mkdir -p .ai/directives/workflows
mkdir -p .ai/knowledge/system
mkdir -p .ai/knowledge/patterns
```

### 6.2: Copy Content from kiwi-mcp

**Status:** 🔄 To Do
**Priority:** P1 (Copy all categories)
**Estimated Time:** 30 min

**Copy Commands:**

```bash
cd /home/leo/projects/kiwi-mcp

# Copy primitives (schemas only - Phase 2 already did this)
# cp .ai/tools/primitives/* /home/leo/projects/kiwi-mcp/rye-lilux/rye/.ai/tools/rye/primitives/

# Copy runtimes (schemas only - Phase 3 already did this)
# cp .ai/tools/runtimes/* /home/leo/projects/kiwi-mcp/rye-lilux/rye/.ai/tools/rye/runtimes/

# Copy capabilities
cp -r .ai/tools/capabilities/* /home/leo/projects/kiwi-mcp/rye-lilux/rye/.ai/tools/rye/capabilities/

# Copy telemetry
cp -r .ai/tools/core/telemetry* /home/leo/projects/kiwi-mcp/rye-lilux/rye/.ai/tools/rye/telemetry/

# Copy extractors
cp -r .ai/tools/extractors/* /home/leo/projects/kiwi-mcp/rye-lilux/rye/.ai/tools/rye/extractors/

# Copy protocol
cp -r .ai/tools/protocol/* /home/leo/projects/kiwi-mcp/rye-lilux/rye/.ai/tools/rye/protocol/

# Copy sinks
cp -r .ai/tools/sinks/* /home/leo/projects/kiwi-mcp/rye-lilux/rye/.ai/tools/rye/sinks/

# Copy threads
cp -r .ai/tools/threads/* /home/leo/projects/kiwi-mcp/rye-lilux/rye/.ai/tools/rye/threads/

# Copy MCP tools and configs
cp -r .ai/tools/mcp/* /home/leo/projects/kiwi-mcp/rye-lilux/rye/.ai/tools/rye/mcp/

# Copy LLM configs
cp -r .ai/tools/llm/* /home/leo/projects/kiwi-mcp/rye-lilux/rye/.ai/tools/rye/llm/

# Copy Python tools and libraries
# Python tools not included in base RYE package

# Copy utility tools
cp -r .ai/tools/utility/* /home/leo/projects/kiwi-mcp/rye-lilux/rye/.ai/tools/rye/utility/

# Copy directives
cp -r .ai/directives/core/*.md /home/leo/projects/kiwi-mcp/rye-lilux/rye/.ai/directives/core/

# Copy knowledge
cp -r .ai/knowledge/*.md /home/leo/projects/kiwi-mcp/rye-lilux/rye/.ai/knowledge/
```

### 6.3: Sign Bundled Content

**Status:** 🔄 To Do
**Priority:** P2 (After 6.2)
**Estimated Time:** 30 min

**Command:**

```bash
cd /home/leo/projects/kiwi-mcp/rye-lilux/rye

# Sign all bundled content
find .ai -name "*.py" -o -name "*.yaml" | xargs python -c "
import sys
from pathlib import Path

# Check if file already has signature
content = Path(sys.argv[1]).read_text()
if 'kiwi-mcp:validated:' not in content:
    print(f'Signing {sys.argv[1]}')
    # Add signature
    import hashlib
    content_hash = hashlib.sha256(content.encode()).hexdigest()[:12]
    signature = f'<!-- kiwi-mcp:validated:{content_hash}:auto-bundle -->'
    content += '\n' + signature
    Path(sys.argv[1]).write_text(content)
else:
    print(f'Already signed: {sys.argv[1]}')
"
```

---

## Phase 7: Update RYE Package Configuration

### 7.1: Update RYE pyproject.toml

**Status:** 🔄 To Do
**Priority:** P1 (Depends on Phase 5)
**Estimated Time:** 15 min

**File:** `rye/pyproject.toml`

**Required Changes:**

```toml
[project]
name = "rye-lilux"
version = "0.1.0"
description = "RYE - Data-driven AI operating system with universal tool executor"

dependencies = [
    "lilux>=0.1.0",  # ← Depends on microkernel
    "httpx>=0.27.0",
    "jsonschema>=4.0.0",
    "pyyaml>=6.0.0",
]

[project.scripts]
rye = "rye.server:main"

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
packages = ["rye"]
package-data = { "rye" = [".ai/**/*"] }  # Bundle .ai/ content
```

### 7.2: Update Lilux pyproject.toml

**Status:** 🔄 To Do
**Priority:** P1 (Depends on Phase 2)
**Estimated Time:** 15 min

**File:** `lilux/pyproject.toml`

**Changes:**

```toml
[project]
name = "lilux"
version = "0.1.0"
description = "Lilux Microkernel - Generic execution primitives for data-driven tools"

dependencies = [
    "mcp>=1.0.0",
    "httpx>=0.27.0",
    "keyring>=23.0.0",
    "python-dotenv>=1.0.0",
]
```

---

## Phase 8: Create RYE **init**.py

**Status:** 🔄 To Do
**Priority:** P1 (After Phase 7)
**Estimated Time:** 15 min

**File:** `rye/rye/__init__.py`

**Required:**

```python
"""RYE - Data-driven AI operating system running on Lilux microkernel."""

__version__ = "0.1.0"
__package_name__ = "rye"

import importlib.resources
from pathlib import Path


def get_content_path() -> Path:
    """Get path to RYE .ai content bundle."""
    with importlib.resources.as_file(
        importlib.resources.files("rye").joinpath(".ai")
    ) as path:
        return path


__all__ = ["__version__", "get_content_path"]
```

---

## Phase 9: Testing

### 9.1: Unit Tests for Lilux Primitives

**Status:** 🔄 To Do
**Priority:** P2 (After Phase 2)
**Estimated Time:** 3 hours

**Files to Write:**

- `tests/kernel/test_primitives.py` - Test subprocess, HTTP, chains
- `tests/kernel/test_runtimes.py` - Test Python runtime with ENV_CONFIG
- `tests/kernel/test_utils.py` - Test minimal parsers, validators

### 9.2: Unit Tests for RYE Universal Executor

**Status:** 🔄 To Do
**Priority:** P2 (After Phase 4)
**Estimated Time:** 4 hours

**Files to Write:**

- `tests/rye/test_universal_executor.py` - Test routing to primitives/runtimes
- `tests/rye/test_metadata_parser.py` - Test metadata parsing
- `tests/rye/test_schema_validator.py` - Test schema validation
- `tests/rye/test_env_resolver.py` - Test variable resolution

### 9.3: Unit Tests for RYE Tools

**Status:** 🔄 To Do
**Priority:** P2 (After Phase 5)
**Estimated Time:** 4 hours

**Files to Write:**

- `tests/rye/test_search.py` - Test tool discovery with categorys
- `tests/rye/test_load.py` - Test loading with different sources
- `tests/rye/test_execute.py` - Test execution via universal executor
- `tests/rye/test_sign.py` - Test signing with metadata manager
- `tests/rye/test_help.py` - Test tool listing

### 9.4: Integration Tests

**Status:** 🔄 To Do
**Priority:** P3 (After all unit tests)
**Estimated Time:** 4 hours

**Files to Write:**

- `tests/integration/test_rye_lilux_integration.py` - Test RYE → Lilux interaction
- `tests/integration/test_mcp_server.py` - Test full MCP server

---

## Phase 10: Documentation

### 10.1: Update Lilux README

**Status:** 🔄 To Do
**Priority:** P3 (After Phase 2)
**Estimated Time:** 1 hour

**File:** `lilux/README.md`

**Sections to Add:**

- Microkernel overview
- Primitives API reference
- Runtime layer description (NEW!)
- Usage examples (as dependency, not standalone)
- Installation: `pip install lilux`

### 10.2: Create RYE README

**Status:** 🔄 To Do
**Priority:** P3 (After Phase 5)
**Estimated Time:** 1 hour

**File:** `rye/README.md`

**Sections to Add:**

- OS overview (data-driven architecture)
- 5 MCP tools reference (auto-discovered)
- .ai/ bundle structure with categorys
- Installation: `pip install rye-lilux`
- Configuration guide

### 10.3: Create Monorepo README

**Status:** 🔄 To Do
**Priority:** P3 (After Phase 10.1-10.2)
**Estimated Time:** 30 min

**File:** `README.md` (root)

**Sections to Add:**

- Lilux + RYE relationship
- Quick start guide
- Development workflow
- Migration guide for existing users

---

## Implementation Timeline

| Phase       | Tasks                                                                                                 | Estimated Time | Dependencies |
| ----------- | ----------------------------------------------------------------------------------------------------- | -------------- | ------------ |
| **Phase 0** | 0.1 Audit (DONE), 0.2 Verify MCP                                                                      | 30 min         | None         |
| **Phase 1** | 1.1-1.5 Complete (ALREADY DONE)                                                                       | -              | 0.1          |
| **Phase 2** | 2.1 Primitives dir, 2.2 Copy primitive schemas                                                        | 45 min         | 1            |
| **Phase 3** | 3.1 Runtimes dir, 3.2 Copy runtime schemas                                                            | 30 min         | 1            |
| **Phase 4** | 4.1 Executor dir, 4.2 Universal executor, 4.3 Metadata parser, 4.4 Schema validator, 4.5 Env resolver | 8 hours        | 2,3          |
| **Phase 5** | 5.1 Metadata manager, 5.2 Parsers, 5.3 Validators, 5.4 Handlers, 5.5 Utils init                       | 12 hours       | 4            |
| **Phase 6** | 6.1 Create .ai/, 6.2 Copy content, 6.3 Sign bundle                                                    | 1.5 hours      | 5            |
| **Phase 7** | 7.1 RYE pyproject, 7.2 Lilux pyproject, 7.3 RYE init                                                  | 30 min         | 2,3          |
| **Phase 8** | 9.1 Lilux tests, 9.2 RYE executor tests, 9.3 RYE tools tests, 9.4 Integration                         | 15 hours       | 7            |
| **Phase 9** | 10.1 Lilux README, 10.2 RYE README, 10.3 Monorepo README                                              | 2.5 hours      | 7            |

**Total Estimated Time:** ~40 hours (~5 days of focused work)

---

## Success Criteria

### Lilux (Microkernel)

✅ Primitives schemas in `.ai/tools/rye/primitives/` (metadata only)
✅ Primitives code in `lilux/primitives/` (implementation)
✅ Handlers are dumb routers (no content intelligence)
✅ Can be installed independently: `pip install lilux`
✅ No dependencies on RYE (provides primitives to RYE)

### RYE (OS)

✅ Universal executor routes to primitives/runtimes based on metadata
✅ Auto-discovers all tools from `.ai/tools/` (all categorys)
✅ Supports all tool categories under `.ai/tools/rye/`
✅ Bundles complete `.ai/rye/` content by category
✅ Supports YAML config files
✅ Provides 5 MCP tools that wrap universal executor
✅ Can be installed: `pip install rye-lilux` (includes Lilux)
✅ Intelligence is data-driven (not hardcoded)
✅ Supports category organization (rye, user, etc.)

### Data-Driven Architecture

✅ Three-layer separation: Primitives → Runtimes → Tools
✅ Schema/code separation: schemas in `.ai/tools/rye/`, code in `lilux/`
✅ Runtime independence via declarative ENV_CONFIG
✅ Library support via `.ai/tools/rye/python/lib/`
✅ Configuration-driven behavior via YAML configs
✅ Extensibility via new primitives/runtimes
✅ Universal discovery and execution
✅ Category organization for tool isolation

---

## Next Steps

1. **Start Phase 2:** Copy primitive schemas from kiwi-mcp to `.ai/tools/rye/primitives/`
2. **Begin Phase 3:** Copy runtime schemas from kiwi-mcp to `.ai/tools/rye/runtimes/`
3. **Follow phases in order:** Each phase depends on previous ones
4. **Test after each phase:** Ensure no import errors before proceeding
5. **Update this plan:** Mark off completed phases as done

---

**Implementation Status:** 🟡 Ready to Start
**Document Status:** Complete and aligned with data-driven architecture
**Architecture Reference:** `docs/ARCHITECTURE.md` (updated with category organization)
**Data-Driven Reference:** `docs/COMPLETE_DATA_DRIVEN_ARCHITECTURE.md` (full breakdown)

---

**Last Updated:** 2026-01-30
**Author:** Kiwi MCP Team
