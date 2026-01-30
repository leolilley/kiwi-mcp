# Lilux Kernel & RYE Tools: Repository Split Architecture

**Date:** 2026-01-27  
**Version:** 0.1.0  
**Status:** Design Document

---

## Executive Summary

This document outlines the architectural split between **Lilux** (the kernel) and **RYE** (the content layer) into separate git repositories. The kernel provides the foundational execution infrastructure including MCP tools, handlers, and primitives. RYE provides the essential content (directives, tools, knowledge) that lives in `.ai/` directories and makes the kernel useful for AI agents.

---

## The Split Philosophy

### Lilux: The Kernel

**"Everything you need, nothing you don't"**

Lilux is the minimal, stable core that provides:

- Execution primitives (subprocess, HTTP, chain resolution)
- Integrity verification and validation
- Runtime services (auth, environment resolution, lockfiles)
- Storage backends (vector, local filesystem)
- Type handlers (directive, tool, knowledge)
- MCP server infrastructure
- **The 4 unified MCP tools** (search, load, execute, help)

**Lilux is the operating system kernel**—it provides the infrastructure and interfaces to work with content. It includes the MCP tools that allow agents to search, load, and execute directives, tools, and knowledge. It knows about:

- Chain resolution
- Integrity verification
- Primitive execution
- Handler dispatch
- MCP tool interfaces

### RYE: The Content

**"RYE Your Execution" - The essential content that makes the kernel useful**

RYE provides the **core directives, tools, and knowledge** that live in `.ai/` directories:

- **Directives** (`.ai/directives/`) - Workflow instructions like `init`, `bootstrap`, `sync_*`, `run_*`
- **Tools** (`.ai/tools/` or `.ai/scripts/`) - Executable Python scripts and utilities
- **Knowledge** (`.ai/knowledge/`) - Domain knowledge, patterns, and learnings
- **Patterns** (`.ai/patterns/`) - Templates and conventions

**RYE is the essential content**—the directives, tools, and knowledge that make Lilux useful. Without RYE, Lilux is a powerful engine with no content to operate on. RYE provides the core tools needed for the kernel to work at a fundamental level.

---

## Repository Structure

### `lilux/` Repository (Kernel)

```
lilux/
├── README.md
├── pyproject.toml
├── LICENSE
├── .github/
│   └── workflows/
│       └── ci.yml
├── lilux/
│   ├── __init__.py
│   ├── server.py                    # MCP server with 4 tools (search, load, execute, help)
│   │
│   ├── tools/                        # The 4 unified MCP tools
│   │   ├── __init__.py
│   │   ├── base.py                  # BaseTool abstract class
│   │   ├── search.py                # SearchTool
│   │   ├── load.py                  # LoadTool
│   │   ├── execute.py               # ExecuteTool
│   │   └── help.py                  # HelpTool
│   │
│   ├── primitives/                  # Execution primitives
│   │   ├── __init__.py
│   │   ├── executor.py              # PrimitiveExecutor, ChainResolver
│   │   ├── subprocess.py            # SubprocessPrimitive
│   │   ├── http_client.py           # HttpClientPrimitive
│   │   ├── chain_validator.py       # ChainValidator
│   │   ├── integrity_verifier.py    # IntegrityVerifier
│   │   ├── integrity.py             # Hash computation
│   │   ├── lockfile.py              # Lockfile management
│   │   └── errors.py                # Execution errors
│   │
│   ├── runtime/                     # Runtime services
│   │   ├── __init__.py
│   │   ├── auth.py                  # AuthStore (OS keychain)
│   │   ├── env_resolver.py          # Environment variable resolution
│   │   └── lockfile_store.py        # Lockfile persistence
│   │
│   ├── storage/                     # Storage backends
│   │   └── vector/
│   │       ├── __init__.py
│   │       ├── base.py              # Base interfaces
│   │       ├── local.py              # LocalVectorStore
│   │       ├── api_embeddings.py    # Embedding service
│   │       ├── embedding_registry.py
│   │       ├── manager.py           # ThreeTierVectorManager
│   │       ├── hybrid.py            # Hybrid search
│   │       ├── pipeline.py          # Embedding pipeline
│   │       └── simple_store.py      # Simple in-memory store
│   │
│   ├── handlers/                    # Type-specific handlers
│   │   ├── __init__.py
│   │   ├── registry.py              # TypeHandlerRegistry
│   │   ├── directive/
│   │   │   ├── __init__.py
│   │   │   └── handler.py           # DirectiveHandler
│   │   ├── tool/
│   │   │   ├── __init__.py
│   │   │   └── handler.py          # ToolHandler
│   │   └── knowledge/
│   │       ├── __init__.py
│   │       └── handler.py          # KnowledgeHandler
│   │
│   ├── schemas/                      # Schema definitions
│   │   ├── __init__.py
│   │   └── tool_schema.py           # Tool metadata extraction
│   │
│   ├── utils/                        # Utility modules
│   │   ├── __init__.py
│   │   ├── resolvers.py             # ToolResolver, PathResolver
│   │   ├── parsers.py               # XML, YAML, frontmatter parsing
│   │   ├── validators.py            # ValidationManager
│   │   ├── metadata_manager.py      # Metadata extraction
│   │   ├── file_search.py           # File search utilities
│   │   ├── paths.py                 # Path utilities
│   │   ├── logger.py                # Logging setup
│   │   ├── env_loader.py            # Environment loading
│   │   ├── env_manager.py           # Environment management
│   │   ├── extensions.py            # Extension utilities
│   │   ├── files.py                 # File operations
│   │   ├── output_manager.py        # Output management
│   │   ├── schema_validator.py      # Schema validation
│   │   ├── signature_formats.py     # Signature format handling
│   │   └── xml_error_helper.py      # XML error helpers
│   │
│   ├── config/                       # Configuration
│   │   ├── __init__.py
│   │   └── vector_config.py         # Vector store configuration
│   │
│   └── safety_harness/               # Safety mechanisms
│       ├── __init__.py
│       └── capabilities.py            # Capability tokens
│
├── tests/
│   ├── primitives/
│   │   ├── test_chain_execution.py
│   │   ├── test_chain_resolver.py
│   │   ├── test_chain_validation.py
│   │   ├── test_executor_auth_integration.py
│   │   ├── test_executor_lockfile.py
│   │   ├── test_http_client.py
│   │   ├── test_integrity_verifier.py
│   │   ├── test_subprocess.py
│   │   └── ...
│   ├── runtime/
│   │   ├── test_auth_store.py
│   │   ├── test_env_resolver.py
│   │   ├── test_lockfile_store.py
│   │   └── ...
│   ├── storage/
│   │   └── vector/
│   │       ├── test_local_store.py
│   │       └── test_hybrid.py
│   └── handlers/
│       └── ...
│
└── docs/
    ├── ARCHITECTURE.md
    ├── PRIMITIVES.md
    └── API.md
```

**Key Characteristics:**

- **Includes MCP tools** - Provides search, load, execute, help as part of kernel
- **Complete infrastructure** - Handlers, primitives, storage, runtime services
- **Stable API surface** - Changes require careful consideration
- **Minimal dependencies** - Core Python stdlib + essential packages
- **Content-agnostic** - Works with any `.ai/` content structure

### `rye/` Repository (Content)

```
rye/
├── README.md
├── LICENSE
├── .github/
│   └── workflows/
│       └── ci.yml
├── .ai/                              # The essential content
│   ├── directives/                   # Core directives
│   │   ├── core/
│   │   │   ├── init.md              # Initialize project
│   │   │   ├── bootstrap.md          # Bootstrap project
│   │   │   ├── context.md           # Generate context
│   │   │   ├── search_*.md          # Search directives
│   │   │   ├── load_*.md            # Load directives
│   │   │   ├── run_*.md             # Run directives
│   │   │   └── sync_*.md            # Sync directives
│   │   └── meta/
│   │       ├── orchestrate_*.md     # Orchestration
│   │       └── validate_*.md        # Validation
│   │
│   ├── tools/                        # Core tools/scripts
│   │   ├── core/                    # Essential utilities
│   │   └── lib/                     # Shared libraries
│   │
│   ├── knowledge/                   # Core knowledge
│   │   ├── concepts/                # Fundamental concepts
│   │   ├── patterns/                # Design patterns
│   │   ├── procedures/              # How-to guides
│   │   └── learnings/               # Captured experience
│   │
│   └── patterns/                     # Templates
│       ├── tool.md                  # Tool template
│       └── directive.md              # Directive template
│
├── tests/
│   └── content/                     # Content validation tests
│
└── docs/
    ├── QUICK_START.md
    ├── DIRECTIVES.md
    └── CONTENT_GUIDE.md
```

**Key Characteristics:**

- **Content repository** - Contains directives, tools, and knowledge
- **Essential core** - The minimum content needed for Lilux to be useful
- **Versioned content** - Directives and tools have versions
- **Can evolve rapidly** - Content can be updated frequently
- **Installable** - Can be installed into project `.ai/` directories

---

## Dependency Relationship

```
┌─────────────────────────────────────────┐
│         LILUX (Kernel)                  │
│  ┌──────────┐  ┌──────────┐           │
│  │ primitives│  │ handlers │           │
│  └────┬─────┘  └────┬─────┘           │
│       │             │                  │
│       └─────────────┘                  │
│         Core execution                  │
│  ┌────────┐  ┌────────┐  ┌────────┐  │
│  │ search │  │  load  │  │execute │  │
│  └────┬───┘  └────┬───┘  └────┬───┘  │
│       │           │           │       │
│       └───────────┴───────────┘       │
│                  │                     │
│         Operates on content            │
└──────────────────┼─────────────────────┘
                   │
                   │ uses
                   ▼
┌─────────────────────────────────────────┐
│            RYE (Content)                 │
│  ┌──────────┐  ┌──────────┐           │
│  │directives│  │  tools   │           │
│  └────┬─────┘  └────┬─────┘           │
│       │             │                  │
│       └─────────────┘                  │
│         Essential content               │
│  ┌──────────┐                          │
│  │knowledge │                          │
│  └──────────┘                          │
└─────────────────────────────────────────┘
```

**Lilux operates on RYE content. RYE is independent content that Lilux can work with.**

---

## Package Dependencies

### `lilux/pyproject.toml`

```toml
[project]
name = "lilux"
version = "0.1.0"
description = "AI-native execution kernel - primitives, handlers, and runtime services"
requires-python = ">=3.11"

dependencies = [
    "mcp>=1.0.0",                    # MCP protocol support
    "httpx>=0.27.0",                 # HTTP client primitive
    "pyyaml>=6.0.0",                 # YAML parsing
    "packaging>=24.0",                # Version handling
    "jsonschema>=4.0.0",             # Schema validation
    "keyring>=23.0.0",               # OS keychain integration
    "numpy>=1.20.0",                 # Vector operations (optional)
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.0.0",
    "ruff>=0.1.0",
]
```

**Minimal, stable dependencies.** Only what's needed for core execution.

### `rye/` Content Structure

RYE is a **content repository**, not a Python package. It contains:

- **Directives** - Core workflow instructions
- **Tools** - Essential executable scripts
- **Knowledge** - Fundamental knowledge base entries
- **Patterns** - Templates and conventions

**Installation:** RYE content can be:

- Copied into project `.ai/` directories
- Installed via a content manager script
- Synced from the RYE repository
- Versioned and distributed independently

**No Python dependencies** - RYE is pure content that Lilux operates on.

---

## Code Migration Plan

### Phase 1: Extract Kernel (Lilux)

1. **Create `lilux/` repository**

   ```bash
   mkdir lilux
   cd lilux
   git init
   ```

2. **Copy kernel modules**

   ```bash
   # From kiwi-mcp/
   cp -r kiwi_mcp/primitives lilux/lilux/
   cp -r kiwi_mcp/runtime lilux/lilux/
   cp -r kiwi_mcp/storage lilux/lilux/
   cp -r kiwi_mcp/handlers lilux/lilux/
   cp -r kiwi_mcp/schemas lilux/lilux/
   cp -r kiwi_mcp/utils lilux/lilux/
   cp -r kiwi_mcp/config lilux/lilux/
   cp -r kiwi_mcp/safety_harness lilux/lilux/
   cp kiwi_mcp/server.py lilux/lilux/server_base.py  # Rename to indicate base
   ```

3. **Create minimal server base**

   ```python
   # lilux/lilux/server_base.py
   """
   Base MCP server infrastructure without tool registration.

   Provides:
   - Server initialization
   - Handler registry
   - Type routing
   - No tool registration (that's RYE's job)
   """
   from mcp.server import Server
   from lilux.handlers.registry import TypeHandlerRegistry

   class LiluxServerBase:
       """Base server that provides handler infrastructure."""

       def __init__(self, project_path=None):
           self.server = Server("lilux")
           self.registry = TypeHandlerRegistry(project_path=project_path)

       def get_registry(self):
           """Get the handler registry for tool registration."""
           return self.registry
   ```

4. **Update imports**

   - Change all `kiwi_mcp.` imports to `lilux.`
   - Update test imports
   - Fix circular dependencies

5. **Create `lilux/pyproject.toml`**

   - Minimal dependencies
   - Package name: `lilux`

6. **Migrate tests**
   - Copy relevant test files
   - Update imports
   - Ensure all kernel tests pass

### Phase 2: Create Content Repository (RYE)

1. **Create `rye/` repository**

   ```bash
   mkdir rye
   cd rye
   git init
   ```

2. **Extract core content from existing `.ai/` directories**

   ```bash
   # From projects using kiwi-mcp, extract essential content:
   # - Core directives (init, bootstrap, sync_*, run_*)
   # - Essential tools/scripts
   # - Core knowledge entries
   # - Pattern templates
   ```

3. **Organize RYE content structure**

   ```
   rye/
   ├── .ai/
   │   ├── directives/
   │   │   ├── core/
   │   │   │   ├── init.md
   │   │   │   ├── bootstrap.md
   │   │   │   ├── context.md
   │   │   │   ├── search_directives.md
   │   │   │   ├── search_tools.md
   │   │   │   ├── search_knowledge.md
   │   │   │   ├── load_directive.md
   │   │   │   ├── load_tool.md
   │   │   │   ├── load_knowledge.md
   │   │   │   ├── run_directive.md
   │   │   │   ├── run_tool.md
   │   │   │   ├── sync_directives.md
   │   │   │   ├── sync_tools.md
   │   │   │   └── sync_knowledge.md
   │   │   └── meta/
   │   │       └── ...
   │   ├── tools/
   │   │   └── core/
   │   │       └── ...
   │   ├── knowledge/
   │   │   ├── concepts/
   │   │   ├── patterns/
   │   │   └── procedures/
   │   └── patterns/
   │       ├── tool.md
   │       └── directive.md
   ```

4. **Create content installation script**

   ```python
   # rye/install.py
   """
   Install RYE content into a project's .ai/ directory.
   """
   import shutil
   from pathlib import Path

   def install_rye_content(project_path: Path, content_type: str = "all"):
       """Install RYE content into project."""
       rye_content = Path(__file__).parent / ".ai"
       project_ai = project_path / ".ai"

       if content_type == "all" or content_type == "directives":
           shutil.copytree(rye_content / "directives", project_ai / "directives", dirs_exist_ok=True)

       # ... install other content types
   ```

5. **Version content**

   - Tag releases in git
   - Document content versions
   - Track compatibility with Lilux versions

6. **Create content validation**

   - Validate directive XML structure
   - Validate tool metadata
   - Validate knowledge frontmatter

### Phase 3: Update Integration

1. **Update MCP client configurations**

   ```json
   {
     "mcpServers": {
       "lilux": {
         "command": "python",
         "args": ["-m", "lilux.server"]
       }
     }
   }
   ```

2. **Install RYE content**

   ```bash
   # Install RYE content into project
   python -m rye.install /path/to/project
   # Or manually copy .ai/ content from rye repository
   ```

3. **Update documentation**

   - Update README files
   - Update architecture docs
   - Update installation instructions
   - Document RYE content structure

4. **Version coordination**
   - Lilux: Semantic versioning (0.1.0, 0.2.0, 1.0.0)
   - RYE: Content versioning (can version independently, tracks compatibility with Lilux)

---

## Content Interface

### Lilux Content Interface

**What Lilux expects from RYE content:**

Lilux operates on content in `.ai/` directories with this structure:

```
.ai/
├── directives/          # XML directives
│   └── core/
│       └── init.md
├── tools/               # Python scripts with metadata
│   └── my_tool.py
└── knowledge/           # Markdown with frontmatter
    └── concept-001.md
```

**Lilux MCP tools operate on this content:**

- `search` - Finds directives, tools, knowledge in `.ai/`
- `load` - Loads items from `.ai/` directories
- `execute` - Executes directives and tools from `.ai/`
- `help` - Provides guidance about content

### RYE Content Structure

**What RYE provides:**

RYE is a curated collection of essential content:

- **Core directives** - `init`, `bootstrap`, `sync_*`, `run_*`, etc.
- **Essential tools** - Common utilities and scripts
- **Fundamental knowledge** - Core concepts and patterns
- **Templates** - Patterns for creating new content

**RYE content follows Lilux conventions:**

- Directives use XML format with metadata
- Tools have proper metadata and signatures
- Knowledge uses frontmatter and markdown
- All content is versioned and validated

---

## Benefits of the Split

### 1. **Separation of Concerns**

- **Lilux** focuses on: Execution infrastructure, integrity, validation, storage, MCP tools
- **RYE** focuses on: Essential content (directives, tools, knowledge) that makes the kernel useful

### 2. **Independent Evolution**

- **Lilux** can evolve slowly (kernel stability)
- **RYE** can iterate rapidly (content improvements, new directives)
- Different release cycles
- Different versioning strategies

### 3. **Alternative Content Sources**

Others can create alternative content repositories:

```
┌─────────────────────────────────────────┐
│      Alternative Content Sources        │
│  ┌──────────┐  ┌──────────┐           │
│  │   RYE    │  │ Domain-   │  ...      │
│  │  (Core)  │  │ Specific  │           │
│  └────┬─────┘  └────┬──────┘           │
│       │            │                    │
│       └────────────┘                   │
│              │                          │
│         Used by Lilux                   │
└──────────────┼──────────────────────────┘
               │
               ▼
         ┌──────────┐
         │  LILUX   │
         │ (Kernel) │
         └──────────┘
```

### 4. **Clearer Testing Boundaries**

- **Lilux tests**: Focus on primitives, handlers, integrity, MCP tools
- **RYE tests**: Focus on content validation, directive correctness, knowledge structure

### 5. **Easier Onboarding**

- **Lilux contributors**: Work on kernel internals, MCP tools, handlers
- **RYE contributors**: Work on content (directives, tools, knowledge)
- Clearer contribution paths

### 6. **Content Management**

- Install `lilux` as Python package for kernel
- Install RYE content into project `.ai/` directories
- Content can be versioned and distributed independently
- Projects can mix RYE content with custom content

---

## Migration Checklist

### Lilux Repository

- [ ] Create `lilux/` repository
- [ ] Copy kernel modules (primitives, runtime, storage, handlers, schemas, utils, config, safety_harness)
- [ ] Create `server_base.py` (minimal server without tools)
- [ ] Update all imports (`kiwi_mcp` → `lilux`)
- [ ] Create `pyproject.toml` with minimal dependencies
- [ ] Migrate kernel tests
- [ ] Update documentation
- [ ] Set up CI/CD
- [ ] Publish to PyPI as `lilux`

### RYE Repository

- [ ] Create `rye/` repository
- [ ] Extract core content from existing `.ai/` directories
- [ ] Organize content structure (directives, tools, knowledge, patterns)
- [ ] Create content installation script
- [ ] Validate all content (directives, tools, knowledge)
- [ ] Version content and tag releases
- [ ] Update documentation
- [ ] Set up CI/CD for content validation
- [ ] Create content distribution mechanism

### Integration

- [ ] Update MCP client configurations
- [ ] Update all documentation references
- [ ] Create migration guide for existing users
- [ ] Update installation instructions
- [ ] Coordinate version releases

---

## Version Compatibility

### Compatibility Matrix

| RYE Version | Lilux Version | Notes                |
| ----------- | ------------- | -------------------- |
| 0.1.0       | >=0.1.0       | Initial split        |
| 0.2.0       | >=0.1.0       | Content improvements |
| 1.0.0       | >=0.2.0       | Stable content       |

### Breaking Changes

**Lilux breaking changes:**

- Require RYE version bump
- Coordinate releases
- Provide migration guide

**RYE breaking changes:**

- Independent of Lilux
- Only affect content structure/format
- Can release independently
- May require content migration for users

---

## Future Possibilities

### Alternative Content Repositories

1. **RYE-Domain**: Domain-specific content

   - Industry-specific directives
   - Specialized tools
   - Domain knowledge

2. **RYE-Enterprise**: Enterprise content

   - Corporate workflows
   - Compliance directives
   - Enterprise patterns

3. **RYE-Community**: Community-contributed content
   - User-submitted directives
   - Shared tools
   - Community knowledge

All compatible with Lilux kernel.

### Kernel Extensions

Lilux can be extended with:

- Additional primitives (gRPC, WebSocket, etc.)
- Additional storage backends (S3, Redis, etc.)
- Additional handlers (new item types)
- Performance optimizations
- Additional MCP tools (beyond the 4 core tools)

Without affecting RYE content.

---

## Questions & Answers

### Q: Why not keep them together?

**A:** Separation allows:

- Independent versioning and release cycles
- Alternative tool layers
- Clearer contribution boundaries
- Better package management

### Q: What if RYE needs kernel changes?

**A:**

- RYE can request kernel features
- Kernel changes go through Lilux repository
- RYE updates dependency version
- Coordinated releases when needed

### Q: Can I use Lilux without RYE?

**A:** Yes! Lilux can work with any `.ai/` content structure. However, RYE provides the essential core directives, tools, and knowledge that make Lilux immediately useful. You can:

- Use Lilux with only your own custom content
- Mix RYE content with custom content
- Use alternative content repositories
- Start with RYE and extend with your own content

### Q: What about the existing `kiwi-mcp` repository?

**A:** Options:

1. **Archive**: Keep as historical reference
2. **Rename**: Convert to `lilux-rye` meta-repo with submodules
3. **Deprecate**: Point to new repositories

### Q: How do I contribute?

**A:**

- **Kernel work**: Contribute to `lilux/` repository (MCP tools, handlers, primitives)
- **Content work**: Contribute to `rye/` repository (directives, tools, knowledge)
- **Both**: Contribute to both repositories

---

## Conclusion

The split between **Lilux** (kernel) and **RYE** (content) provides:

1. **Clear separation** of kernel infrastructure vs. essential content
2. **Independent evolution** with different release cycles
3. **Alternative content sources** possible with same kernel
4. **Better content management** with versioned, distributable content
5. **Clearer contribution paths** for different types of work

**Lilux is the engine. RYE is the essential fuel. Together, they make AI-native execution possible.**

---

**Next Steps:**

1. Review this document
2. Create `lilux/` repository structure
3. Create `rye/` repository structure
4. Begin migration process
5. Coordinate initial releases

---

_Document Status: Draft for Review_  
_Last Updated: 2026-01-27_  
_Authors: Kiwi MCP Team_
