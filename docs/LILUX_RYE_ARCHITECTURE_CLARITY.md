# Lilux/RYE Architecture: Repository & Packaging Clarity

**Date:** 2026-01-28  
**Status:** Clarification Document  
**Purpose:** Clear explanation of how lilux kernel and rye content are organized and shipped

---

## The Two Repositories

### Repository 1: `lilux/` (Kernel - GitHub)

```
github.com/leolilley/lilux/
├── lilux/                          # Python package (the kernel)
│   ├── __init__.py
│   ├── server.py                   # MCP server
│   ├── tools/                      # Search, Load, Execute, Help
│   ├── primitives/                 # Executor, subprocess, HTTP
│   ├── handlers/                   # Directive, Tool, Knowledge handlers
│   ├── runtime/                    # Auth, env, lockfile mgmt
│   ├── storage/                    # Vector stores
│   ├── utils/                      # Helper utilities
│   ├── config/                     # Configuration
│   └── safety_harness/             # Capability tokens
│
├── tests/                          # Tests for kernel
├── pyproject.toml                  # Kernel package config
├── setup.py
└── README.md
```

**What it provides:**
- Execution primitives
- MCP server infrastructure
- The 4 unified MCP tools
- Handlers for directives/tools/knowledge
- No content included (just infrastructure)

**Published to PyPI as:** `lilux`

### Repository 2: `rye/` (Content - GitHub)

```
github.com/leolilley/rye/
├── .ai/                            # RYE content (git folder or submodule)
│   ├── directives/
│   │   ├── core/
│   │   │   ├── init.md
│   │   │   ├── bootstrap.md
│   │   │   ├── sync_directives.md
│   │   │   └── ...
│   │   └── meta/
│   │       ├── search_*.md
│   │       └── ...
│   ├── tools/
│   │   └── core/
│   │       ├── collection_manager.py
│   │       ├── registry_manager.py
│   │       └── ...
│   └── knowledge/
│       ├── concepts/
│       ├── patterns/
│       └── procedures/
│
├── tests/                          # Content validation tests
├── pyproject.toml                  # RYE package config
├── setup.py
└── README.md
```

**What it contains:**
- Essential directives (init, bootstrap, sync, search, load, run, etc.)
- Essential tools (collection manager, registry ops, etc.)
- Core knowledge base
- Nothing about kernel infrastructure

**Published to PyPI as:** `rye`

---

## The Package Dependency: How They Link

### `rye` Package Depends on `lilux`

**`rye/pyproject.toml`:**

```toml
[project]
name = "rye"
version = "0.1.0"
description = "RYE content layer + Lilux kernel"

dependencies = [
    "lilux>=0.1.0",        # ← Depends on kernel
    "pydantic>=2.0",
    "pyyaml>=6.0",
]

[project.scripts]
lilux = "lilux.cli:main"         # From lilux package
rye-init = "lilux.scripts.init:main"
rye-demo = "lilux.scripts.demo:main"

[tool.setuptools.package-data]
lilux = ["**/*.py"]              # From lilux package (via dependency)
"" = [".ai/**/*"]                # RYE content (this repo)
```

### What Happens When You `pipx install rye`

```
$ pipx install rye

1. Fetch 'rye' package from PyPI
2. Dependencies:
   └── lilux>=0.1.0
   
3. Install lilux package (first)
   ├── Installs ~/site-packages/lilux/
   │   ├── __init__.py
   │   ├── server.py
   │   ├── tools/
   │   ├── primitives/
   │   ├── handlers/
   │   ├── etc.
   │   └── (all kernel code)
   └── Registers CLI: lilux, lilux-serve

4. Install rye package (second)
   ├── Installs ~/site-packages/rye/
   │   ├── __init__.py (minimal, just package marker)
   │   └── (rye package metadata)
   └── Bundles .ai/ folder:
       ├── directives/ (copied to wheel)
       ├── tools/      (copied to wheel)
       └── knowledge/  (copied to wheel)

5. Result: Full system available
   ├── lilux kernel (from lilux package)
   ├── RYE content (from rye package)
   ├── Both integrated
   └── All 4 tools available: search, load, execute, help
```

---

## File Organization in `rye/pyproject.toml`

**The `.ai/` folder is bundled as package data:**

```toml
[tool.setuptools.package-data]
"" = [".ai/**/*"]  # ← Package the entire .ai/ directory
```

This means when the `rye` wheel is built:
```
rye-0.1.0-py3-none-any.whl
├── lilux/                   (from lilux dependency)
├── rye/
│   ├── __init__.py
│   └── .ai/                 ← .ai/ folder bundled here
│       ├── directives/
│       ├── tools/
│       └── knowledge/
└── rye-0.1.0.dist-info/
```

---

## How `lilux` Finds the `.ai/` Content

**In `lilux/__init__.py` or a config module:**

```python
import importlib.resources
from pathlib import Path

def get_content_root():
    """Get path to bundled .ai/ content from rye package"""
    try:
        # Try to import rye and find its .ai folder
        import rye
        rye_path = Path(rye.__file__).parent
        ai_path = rye_path / ".ai"
        if ai_path.exists():
            return ai_path
    except ImportError:
        pass
    
    # Fallback: look relative to lilux
    return Path(__file__).parent.parent / ".ai"

CONTENT_ROOT = get_content_root()
```

**When a user calls `lilux search` or `lilux execute`:**
1. lilux kernel loads
2. Looks for `.ai/` content
3. Finds it bundled in the rye package
4. Uses that content as the default search/execute source

---

## CLI Entry Points

When you `pipx install rye`, both sets of CLI commands are available:

**From lilux package:**
```bash
lilux serve              # Start MCP server
lilux search ...         # Search content
lilux load ...           # Load items
lilux execute ...        # Run directives/tools
lilux help ...           # Get help
```

**From rye package (convenience aliases):**
```bash
rye-init                 # Run init directive
rye-demo                 # Run demo directives
```

All backed by the same lilux kernel + rye content.

---

## Version Compatibility

### Independent Versioning

- **lilux 0.1.0**: Kernel stability, API contracts
- **rye 0.1.0**: Content stability, directive/tool versions

### Compatibility Matrix

```
rye 0.1.0 requires lilux >=0.1.0
rye 0.2.0 requires lilux >=0.1.0
rye 1.0.0 requires lilux >=0.2.0

lilux 0.2.0 compatible with rye >=0.1.0
lilux 1.0.0 not compatible with rye <1.0.0
```

### Release Cycle

- **lilux**: Slower releases (kernel stability)
- **rye**: Faster releases (content improvements)
- **Coordinated releases**: Only when breaking changes

---

## Development & Contribution

### Contributing to Lilux Kernel

```bash
git clone github.com/leolilley/lilux
cd lilux
pip install -e .
# Edit lilux/primitives/, lilux/handlers/, etc.
pytest
```

### Contributing to RYE Content

```bash
git clone github.com/leolilley/rye
cd rye
# Edit .ai/directives/, .ai/tools/, .ai/knowledge/
# Test against installed lilux
lilux search "my-directive"
lilux execute action run directive core my-directive
```

---

## Future: Optional Separate Repositories

If ever split into fully separate repos:

**Option 1: Monorepo (Current)**
```
lilux-rye/
├── lilux/    (kernel)
└── rye/      (content)
```

**Option 2: Separate repos (Future)
```
lilux/       (kernel only)
├── lilux/
├── pyproject.toml
└── publish to PyPI as 'lilux'

rye/         (content only)
├── .ai/
├── pyproject.toml (depends: lilux>=0.1.0)
└── publish to PyPI as 'rye'
```

Either way, the user experience is the same: `pipx install rye` gets everything.

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────┐
│                  User's Machine                          │
│                                                          │
│  $ pipx install rye                                     │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Virtual Environment (~/virtualenvs/rye/)           │ │
│  │                                                    │ │
│  │ ┌──────────────────────┐  ┌──────────────────────┐│ │
│  │ │   lilux Package      │  │   rye Package        ││ │
│  │ │  (from PyPI)         │  │  (from PyPI)         ││ │
│  │ │                      │  │                      ││ │
│  │ │ ├── lilux/           │  │ ├── rye/             ││ │
│  │ │ │   ├── server.py    │  │ │   └── __init__.py   ││ │
│  │ │ │   ├── tools/       │  │ ├── .ai/  ← bundled ││ │
│  │ │ │   ├── primitives/  │  │ │   ├── directives/  ││ │
│  │ │ │   ├── handlers/    │  │ │   ├── tools/       ││ │
│  │ │ │   └── ...          │  │ │   └── knowledge/   ││ │
│  │ │ └── bin/             │  │ └── bin/             ││ │
│  │ │     └── lilux        │  │     ├── lilux        ││ │
│  │ │                      │  │     ├── rye-init     ││ │
│  │ └──────────────────────┘  │     └── rye-demo     ││ │
│  │         ▲                 └─────────────────────────┘│
│  │         │                                            │
│  │         └── rye depends on lilux                     │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │ User Space: ~/.local/share/rye/                    │ │
│  │                                                    │ │
│  │ ├── collections/  (installed collections)          │ │
│  │ ├── cache/        (embeddings, search indices)     │ │
│  │ └── user/         (user's custom content)           │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## Summary

| Aspect | Lilux | RYE |
|--------|-------|-----|
| **What** | Kernel (execution engine) | Content (directives, tools, knowledge) |
| **Repository** | `github.com/leolilley/lilux` | `github.com/leolilley/rye` |
| **PyPI Package** | `lilux` | `rye` |
| **Dependency** | None (standalone) | Depends on `lilux>=0.1.0` |
| **Versioning** | Kernel semver | Content semver |
| **Release Cycle** | Stable, infrequent | Dynamic, frequent |
| **User Install** | `pip install lilux` | `pipx install rye` (gets both) |
| **CLI** | `lilux`, `lilux-serve` | `rye-init`, `rye-demo`, + lilux CLI |
| **Content** | None | `.ai/` folder with core directives/tools/knowledge |

**Bottom line:**
- User installs: `pipx install rye`
- Gets: lilux kernel + rye content
- Both work together seamlessly
- Independent evolution, coordinated release

---

_Document Status: Clarification_  
_Last Updated: 2026-01-28_
