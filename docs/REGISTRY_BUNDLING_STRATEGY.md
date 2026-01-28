# Registry Bundling Strategy: Collections, Discovery, and Distribution

**Date:** 2026-01-28  
**Version:** 0.2.0  
**Purpose:** Design framework for bundling tools, directives, and knowledge into shareable collections

---

## Executive Summary

This document outlines how Lilux/RYE enables users to easily **bundle and share collections** of directives, tools, and knowledge—similar to GitHub, but for AI-native content. Users can:

1. **Create collections** - Bundle any mix of tools, directives, and knowledge
2. **Host collections** - On registry or personal git space
3. **Discover collections** - Via registry RAG + metadata search
4. **Install collections** - Into their project `.ai/` directories
5. **Contribute to collections** - Fork, extend, and merge back
6. **Mix sources** - Combine core RYE with domain-specific collections

---

## Part 1: Collection Architecture

### Collection Definition

A **collection** is a versioned bundle of related content:

```yaml
# .ai/collections/collection.toml
[metadata]
name = "data-processing"
version = "1.0.0"
description = "Tools and directives for data processing workflows"
author = "team@example.com"
license = "MIT"

# Git repository where this collection lives
source = "https://github.com/example/data-processing-collection"
registry = "rye"  # Which registry this publishes to

# RAG configuration
vector_config = "default"  # Which vector store to use for search

# Dependencies: other collections
[dependencies]
core = ">=0.1.0"  # Depends on core RYE
ml-utils = ">=1.0.0"  # Depends on another collection

# Content manifest
[content]
directives = [
    "directives/process-csv.md",
    "directives/validate-data.md",
    "directives/transform-pipeline.md",
]
tools = [
    "tools/csv-parser.py",
    "tools/validator.py",
    "tools/transformer.py",
]
knowledge = [
    "knowledge/patterns/batch-processing.md",
    "knowledge/patterns/error-handling.md",
]

# Tags for discovery
[tags]
categories = ["data", "processing", "automation"]
skill-level = ["intermediate", "advanced"]
domains = ["data-science", "ml-ops"]
```

### Collection Directory Structure

```
collections/data-processing/
├── collection.toml              # Metadata + manifest
├── README.md                    # Human-readable guide
├── directives/
│   ├── process-csv.md
│   ├── validate-data.md
│   └── transform-pipeline.md
├── tools/
│   ├── csv-parser.py
│   ├── validator.py
│   └── transformer.py
├── knowledge/
│   ├── patterns/
│   │   ├── batch-processing.md
│   │   └── error-handling.md
│   └── concepts/
│       └── data-validation.md
├── tests/
│   ├── test_directives.py
│   └── test_tools.py
└── examples/
    ├── example1.md
    └── example2.md
```

---

## Part 2: Registry Architecture

### Three-Tier Registry System

```
┌──────────────────────────────────────────────────────────────┐
│                   REGISTRY ECOSYSTEM                         │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Tier 1: CORE REGISTRY (Official)                           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ • RYE core directives, tools, knowledge               │ │
│  │ • Official collections (curated)                      │ │
│  │ • Vector embeddings (primary index)                   │ │
│  │ • RAG index (primary search)                          │ │
│  │ Repository: github.com/leolilley/rye                 │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  Tier 2: COMMUNITY REGISTRIES (Secondary)                   │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ • Domain-specific collections                         │ │
│  │ • Community-contributed packs                         │ │
│  │ • Optional vector embeddings                          │ │
│  │ • Can have own RAG indices                            │ │
│  │ Example URLs:                                          │ │
│  │   - github.com/org/ml-collection                      │ │
│  │   - github.com/user/personal-tools                    │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  Tier 3: LOCAL SPACE (Personal)                            │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ • User's own collections + mixes                      │ │
│  │ • Git-backed or local-only                            │ │
│  │ • Personal vector index (optional)                    │ │
│  │ Location: ~/.local/share/rye/collections/            │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### Registry URL Conventions

```
# Official Core Registry
rye://core            # Implicit: RYE core content
rye://core@0.1.0      # Pinned version

# Community Collection (GitHub)
github://org/collection-name
github://org/collection-name@1.0.0

# Direct HTTPS
https://github.com/org/collection-name

# Local (user space)
local://collection-name
file:///path/to/collection
```

---

## Part 3: Vector Store & RAG Configuration

### Flexible Vector Config

Each registry/collection can have its own vector configuration:

```yaml
# lilux/config/vector_config.yaml
registries:
  # Core RYE registry
  rye:core:
    name: "RYE Core"
    embedding_model: "sentence-transformers/all-MiniLM-L6-v2"
    backend: "local" # or: openai, huggingface, pinecone
    cache_dir: "~/.local/share/rye/cache/embeddings/rye-core"
    vector_db_path: "~/.local/share/rye/cache/vector-stores/rye-core"
    description: "Official RYE core content index"

    # Fallback to BM25 if vector fails
    fallback_search: "bm25"

    # Metadata filtering
    filters:
      - field: "category"
        name: "Content Category"
      - field: "skill_level"
        name: "Skill Level"

  # Community ML registry
  ml-community:
    name: "ML Community Collection"
    embedding_model: "sentence-transformers/all-MiniLM-L6-v2"
    backend: "openai"
    api_key_env: "OPENAI_API_KEY"
    cache_dir: "~/.local/share/rye/cache/embeddings/ml-community"
    source_repo: "https://github.com/ml-community/collection"

  # User's personal space
  local:personal:
    name: "Personal Collections"
    embedding_model: "sentence-transformers/all-MiniLM-L6-v2"
    backend: "local"
    cache_dir: "~/.local/share/rye/cache/embeddings/personal"
    local_only: true
```

### Registry Discovery via RAG

**Search architecture:**

```
User Query
    ↓
┌─────────────────────────────────────────┐
│  Multi-Registry Search Pipeline          │
├─────────────────────────────────────────┤
│                                         │
│ 1. Query tokenization & embedding       │
│ 2. Query-specific registry selection    │
│    (which registries to search)         │
│ 3. Vector search in each registry       │
│    (parallel queries)                   │
│ 4. Metadata filtering                   │
│    (category, skill-level, etc.)        │
│ 5. Relevance ranking                    │
│ 6. Result aggregation                   │
│                                         │
└─────────────────────────────────────────┘
    ↓
Results (merged, ranked)
```

**Search examples:**

```python
# Search across all enabled registries
search "data processing"
→ Results from: rye:core, ml-community, personal

# Search specific registry
search "data processing" from:ml-community
→ Results from: ml-community only

# Filter by metadata
search "data processing" skill-level:advanced
→ Results matching skill level

# Complex query
search "batch processing patterns" category:data domain:ml-ops
→ Filtered results from all registries
```

---

## Part 4: Collection Publishing Workflow

### Step 1: Create Collection Locally

```bash
# Create collection structure
mkdir -p ~/.local/share/lilux/collections/my-data-tools
cd ~/.local/share/lilux/collections/my-data-tools

# Create collection.toml
cat > collection.toml << 'EOF'
[metadata]
name = "my-data-tools"
version = "0.1.0"
description = "My personal data processing tools"
author = "me@example.com"
license = "MIT"
registry = "local"

[content]
directives = ["directives/process.md"]
tools = ["tools/parser.py"]
knowledge = ["knowledge/patterns.md"]
EOF

# Create content directories
mkdir -p directives tools knowledge
```

### Step 2: Develop & Test

```bash
# Tools, directives, and knowledge work normally in user space
# They're automatically discoverable via local registry

# Test via execute tool
lilux execute action run directive my-data-tools/process
```

### Step 3: Version & Publish

**Option A: Publish to GitHub (Community Registry)**

```bash
# Initialize git repo
git init
git add .
git commit -m "Initial version 0.1.0"
git tag v0.1.0

# Push to GitHub
git remote add origin https://github.com/username/my-data-tools
git push -u origin main
git push origin v0.1.0

# Now discoverable as:
github://username/my-data-tools
github://username/my-data-tools@0.1.0
```

**Option B: Publish to Official Registry**

```bash
# Via CLI (for curated/official content)
lilux publish collection --name my-data-tools --registry rye

# Requires:
# - Passing content validation
# - Proper metadata
# - Tests passing
# - Admin approval (for curated collections)
```

### Step 4: Discovery & Installation

```bash
# Search for collections
lilux search "data processing"

# Get collection info
lilux info github://username/my-data-tools

# Install collection into project
cd /path/to/my-project
lilux install github://username/my-data-tools

# What happens:
# 1. Clone/download collection
# 2. Verify collection.toml
# 3. Install content into .ai/directives, .ai/tools, .ai/knowledge
# 4. Update local registry metadata
# 5. (Optional) Download + index embeddings
```

---

## Part 5: Collection Dependency Management

### Dependency Resolution

Collections can depend on other collections:

```toml
# collection.toml
[dependencies]
core = ">=0.1.0"              # RYE core
ml-utils = "1.0.0"            # Pinned version
"github.com/user/helpers" = "^0.5.0"  # Semver range
```

### Installation with Dependencies

```bash
# Install my-ml-app (depends on ml-utils, core, etc.)
lilux install github://username/my-ml-app

# Automatic resolution:
# 1. Fetch collection metadata
# 2. Resolve dependencies recursively
# 3. Check version compatibility
# 4. Install in dependency order
# 5. Verify all content loads

# Result structure:
~/.local/share/rye/collections/
├── rye-core/                 # Auto-installed
├── github-user-helpers/      # Auto-installed
├── github-user-ml-app/       # Explicitly requested
└── my-personal-tools/        # Previously installed
```

### Conflict Resolution

```yaml
# Two collections require different versions of a tool
# Solution: Namespace isolated, copy-on-write

~/.local/share/rye/tools/
├── core/                     # From rye:core
├── helpers_v0.5/             # From ml-utils
├── helpers_v1.0/             # From another collection
└── my-tools/                 # Personal

# Directives can explicitly import:
import: "helpers_v1.0/utility.py"
```

---

## Part 6: Collection Lifecycle & Versioning

### Semantic Versioning

```
Collections follow semver: MAJOR.MINOR.PATCH

0.1.0 = Initial release (alpha)
0.2.0 = Additions/improvements (pre-release)
1.0.0 = Stable, no breaking changes
1.1.0 = Additions
2.0.0 = Breaking changes

# Breaking changes:
- Renamed directives/tools
- Changed tool signatures
- Removed public content
- Major dependency version jumps
```

### Version Compatibility Matrix

```yaml
# collection.toml
[compatibility]
min_lilux_version = "0.1.0"
min_rye_version = "0.1.0"
python_version = ">=3.9"

# Declare which tools/directives work with which versions
[versioning]
directives:
  process-csv:
    breaking_changes:
      - version: "2.0.0"
        description: "Changed input signature"

tools:
  parser.py:
    deprecated_in: "1.5.0"
    removed_in: "2.0.0"
    replacement: "tools/parser-v2.py"
```

### Changelog Convention

```markdown
# Changelog

## [1.0.0] - 2026-02-01

### Added

- New directive: `transform-with-validation`
- Knowledge entry: `data-quality-patterns`

### Changed

- Improved `process-csv` performance
- Updated `validator.py` to support async

### Deprecated

- `process-old.md` (use `process-csv.md` instead)

### Fixed

- Bug in CSV parser with special characters

### Removed

- Legacy tool `old-parser.py`

## [0.2.0] - 2026-01-28

...
```

---

## Part 7: Mix & Match: Personal Collections

### Creating a Custom Mix

Users can create **meta-collections** that combine content from multiple sources:

```toml
# ~/.local/share/rye/collections/my-workspace/collection.toml

[metadata]
name = "my-workspace"
version = "1.0.0"
description = "My personal ML workspace"
type = "meta"  # This is a collection of collections

[includes]
# Include entire collections
core = "rye://core@>=0.1.0"
ml-tools = "github://user/ml-tools@^1.0.0"
data-processing = "github://org/data-processing@1.5.0"

# Include specific items from collections
selected-patterns = [
    "github://community/patterns/batch-processing.md",
    "github://community/patterns/async-chains.md",
]

# Include from local
personal-tools = "local://my-scripts"

[overlays]
# Create aliases for commonly used items
"batch" = "data-processing/directives/batch-process.md"
"validate" = "data-processing/directives/validate-data.md"
```

### Collection Composition

```
Install meta-collection "my-workspace"
    ↓
Resolve dependencies:
    ├── rye:core (fully)
    ├── ml-tools (fully)
    ├── data-processing (fully)
    └── personal-tools (fully)
    ↓
Create overlay:
    ~/.local/share/rye/overlays/my-workspace/
    ├── batch → data-processing/directives/batch-process.md
    ├── validate → data-processing/directives/validate-data.md
    └── ...
    ↓
Available in searches:
    search "batch"  # Finds overlay
    search "data processing"  # Finds original
```

---

## Part 8: Implementation: Tools & Directives

### New Directives

```xml
<!-- .ai/directives/core/collection_publish.md -->
<directive name="collection/publish" version="1.0.0">
  <metadata>
    <description>Publish a collection to a registry</description>
    <inputs>
      <input name="collection_path" type="path" required="true">
        Path to collection directory
      </input>
      <input name="registry" type="string" default="local">
        Target registry (local, rye, github)
      </input>
      <input name="version" type="string" required="true">
        Version number (semver)
      </input>
      <input name="dry_run" type="bool" default="true">
        Validate without publishing
      </input>
    </inputs>
  </metadata>

  <process>
    <step name="validate">
      <!-- Validate collection.toml -->
      <!-- Check content exists -->
      <!-- Run tests -->
    </step>
    <step name="version">
      <!-- Update version in files -->
      <!-- Create git tag -->
    </step>
    <step name="publish">
      <!-- Push to registry -->
      <!-- Update metadata -->
      <!-- Index in vector store -->
    </step>
  </process>
</directive>
```

```xml
<!-- .ai/directives/core/collection_install.md -->
<directive name="collection/install" version="1.0.0">
  <metadata>
    <description>Install a collection into project</description>
    <inputs>
      <input name="collection_url" type="string" required="true">
        Collection URL (github://user/name, rye://core, etc.)
      </input>
      <input name="version" type="string" default="latest">
        Version constraint (e.g., ">=1.0.0")
      </input>
      <input name="target" type="path" default=".ai">
        Where to install content
      </input>
    </inputs>
  </metadata>
</directive>
```

```xml
<!-- .ai/directives/core/collection_search.md -->
<directive name="collection/search" version="1.0.0">
  <metadata>
    <description>Search registries for collections</description>
    <inputs>
      <input name="query" type="string" required="true">
        Search query (with optional filters)
      </input>
      <input name="registries" type="list" default="[]">
        Which registries to search (all if empty)
      </input>
      <input name="limit" type="int" default="10">
        Results limit
      </input>
    </inputs>
  </metadata>
</directive>
```

### Registry Tools

```python
# .ai/tools/registry/collection_manager.py
"""Collection management utilities"""

class CollectionManager:
    """Manage local and remote collections"""

    def load_collection(self, path: Path) -> Collection:
        """Load collection.toml and validate"""
        ...

    def publish_to_registry(self, collection: Collection, registry: str):
        """Publish to registry (github, rye, etc.)"""
        ...

    def install_from_url(self, url: str, version: str, target: Path):
        """Install collection from URL"""
        ...

    def resolve_dependencies(self, collection: Collection) -> List[Collection]:
        """Recursively resolve dependencies"""
        ...

    def search_registries(self, query: str, registries: List[str] = None):
        """Search across registries"""
        ...

    def validate_collection(self, collection: Collection) -> ValidationResult:
        """Validate collection structure and content"""
        ...
```

---

## Part 9: User Experience: Quick Start

### For Collection Authors

```bash
# 1. Create collection locally
mkdir -p ~/.local/share/rye/collections/my-data-tools
cd ~/.local/share/rye/collections/my-data-tools

# 2. Create collection.toml
cat > collection.toml << 'EOF'
[metadata]
name = "my-tools"
version = "0.1.0"
description = "My useful tools"
author = "me@example.com"
registry = "local"

[content]
tools = ["tools/helper.py"]
directives = ["directives/task.md"]
EOF

# 3. Create structure
mkdir -p tools directives

# 4. Add content (already tested in user space)
# Just move files here

# 5. Publish to GitHub
git init
git add .
git commit -m "Initial version"
git tag v0.1.0
git push github.com/username/my-tools

# 6. Now shareable!
# People install with:
# lilux install github://username/my-tools
```

### For Collection Users

```bash
# 1. Search for collections
lilux search "data processing"
# Shows: Collections from all registries

# 2. Get info
lilux info github://user/data-tools
# Shows: Description, versions, dependencies, etc.

# 3. Install
lilux install github://user/data-tools
# Auto-installs dependencies, indexes content

# 4. Use in projects
cd my-project
lilux search "process data"
# Finds tools from installed collections

# Use directly
lilux execute action run tool data-tools/process-csv

# Or in directives
<directive name="workflow" ...>
  <imports>
    <import from="data-tools/directives/validate.md" />
  </imports>
</directive>
```

---

## Part 10: Multi-Registry Expansion

### Future Support for Multiple Registries

The system is designed for easy expansion:

```yaml
# Eventually support multiple registries per environment
registries:
  - name: "rye:core"
    url: "https://registry.lilux.dev/core"
    priority: 100 # Primary registry

  - name: "huggingface"
    url: "https://huggingface.co/lilux-collections"
    priority: 50

  - name: "pinecone"
    url: "https://pinecone.io/lilux"
    priority: 40

  - name: "local"
    path: "~/.local/share/lilux/collections"
    priority: 10 # Lowest priority (local fallback)

# Search respects priority order
# Install auto-pulls from first available source
# User can override: lilux install @huggingface://collection
```

---

## Part 11: Summary & Benefits

### What Users Can Do

1. **Create** - Bundle their tools, directives, knowledge
2. **Host** - On GitHub, personal registry, or local
3. **Share** - Via git URL or registry publish
4. **Discover** - Via RAG + metadata search across registries
5. **Install** - Into any project, with dependency resolution
6. **Mix** - Combine collections into personal workspaces
7. **Contribute** - To community collections via PRs

### Core Design Principles

1. **Git-first** - Everything is version controlled
2. **Decentralized** - Content can live anywhere
3. **Discoverable** - Vector search + metadata
4. **Composable** - Collections depend on collections
5. **Flexible** - One core registry now, multiple later
6. **Safe** - Validation, testing, versioning built-in

### Architecture Benefits

- **Scalable**: Registry system doesn't become bottleneck
- **Extensible**: Easy to add new registries/sources
- **Independent**: Core kernel stable, collections evolve
- **Developer-friendly**: Familiar git workflows
- **AI-native**: RAG search, semantic discovery
- **Community-driven**: Anyone can publish collections

---

## Implementation Roadmap

### Phase 1: Foundation (0.2.0)

- [ ] Collection metadata format (TOML)
- [ ] Local collection discovery
- [ ] Collection installation from git URLs
- [ ] Basic dependency resolution

### Phase 2: Registry Integration (0.3.0)

- [ ] Vector indexing for collections
- [ ] RAG-based search across registries
- [ ] Official registry (rye:core)
- [ ] Publish directive

### Phase 3: Community (0.4.0)

- [ ] Community collection curation
- [ ] Registry UI/web interface
- [ ] Collection ratings/reviews
- [ ] Multiple registry support

### Phase 4: Advanced (1.0.0)

- [ ] Collection composition
- [ ] Advanced dependency resolution
- [ ] Conflict detection
- [ ] Migration tooling

---

## Conclusion

**Collections as distribution units** enable:

- **Creators**: Share curated, versioned content easily
- **Users**: Discover and mix content from multiple sources
- **Community**: Build ecosystem around Lilux/RYE
- **Scale**: Decentralized, git-backed, searchable

**One command to install everything you need:**

```bash
lilux install github://user/my-complete-system
```

---

_Document Status: Design for Implementation_  
_Last Updated: 2026-01-28_  
_Next: Implement collection metadata + discovery system_
