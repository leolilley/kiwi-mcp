# Technical Implementation: Lilux/RYE Integration

**Date:** 2026-01-28  
**Version:** 0.1.0  
**Purpose:** Technical details for developers implementing the split

---

## Part 1: Repository Structure Migration

### Current State → Target State

**Current (kiwi-mcp):**
```
kiwi-mcp/
├── kiwi_mcp/          # Package code
├── .ai/               # Content
├── tests/
└── docs/
```

**Target (lilux/rye split):**
```
lilux-rye/  (or migrate existing to lilux/)
├── lilux/             # Kernel code
├── .ai/               # RYE content (included in package)
├── tests/
├── pyproject.toml
└── setup.py
```

### Migration Path (Keep existing in transition)

**Phase 1: Parallel Structure**
```
kiwi-mcp/
├── lilux/             # NEW: Kernel (refactored from kiwi_mcp)
├── kiwi_mcp/          # OLD: Keep for backward compat (0.1.0 only)
├── .ai/               # RYE content
├── pyproject.toml     # Updated to build both
└── ...
```

**Phase 2: Single Source of Truth**
```
lilux-rye/ (or just rename to lilux)
├── lilux/             # Kernel
├── .ai/               # Content
├── pyproject.toml
└── ...
```

**Phase 3: Optional Split (if needed)**
```
lilux/                 # Kernel repo
  └── lilux/
  
rye/                   # Content repo
  └── .ai/
```

---

## Part 2: Package Configuration

### `pyproject.toml` - Single Package

```toml
[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "rye"
version = "0.1.0"
description = "Lilux kernel + RYE content: AI-native execution"
requires-python = ">=3.9"

authors = [
    {name = "Lilux Team", email = "team@lilux.dev"}
]

license = {text = "MIT"}

readme = "README.md"
keywords = ["mcp", "agent", "execution", "directives"]

classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

dependencies = [
    "pydantic>=2.0",
    "pyyaml>=6.0",
    "requests>=2.28",
    "click>=8.0",
]

[project.optional-dependencies]
vector = [
    "numpy>=1.21",
    "sentence-transformers>=2.2",
    "scikit-learn>=1.0",
]

dev = [
    "pytest>=7.0",
    "pytest-cov>=3.0",
    "black>=22.0",
    "ruff>=0.0.200",
    "mypy>=0.990",
]

docs = [
    "sphinx>=4.5",
    "sphinx-rtd-theme>=1.0",
]

[project.urls]
Homepage = "https://github.com/leolilley/lilux-rye"
Repository = "https://github.com/leolilley/lilux-rye.git"
Issues = "https://github.com/leolilley/lilux-rye/issues"

[project.scripts]
# Kernel CLI
lilux = "lilux.cli:main"
lilux-serve = "lilux.server:main"

# Content/demo CLI
rye-init = "lilux.cli.init:main"
rye-demo = "lilux.cli.demo:main"

[tool.setuptools]
packages = ["lilux"]

[tool.setuptools.package-data]
lilux = [
    "py.typed",
    "**/*.py",
]
# Include .ai directory
"" = [
    ".ai/**/*",
]

[tool.setuptools.package-dir]
"" = "."

[tool.black]
line-length = 100
target-version = ["py39"]

[tool.ruff]
line-length = 100
target-version = "py39"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
addopts = "-v --cov=lilux --cov-report=term-with-missing"

[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
```

---

## Part 3: Import Migration

### From `kiwi_mcp` → `lilux`

**Search & Replace Pattern:**
```
kiwi_mcp → lilux
KIWI_MCP → LILUX
KiwiMCP → Lilux
```

**Example:**
```python
# Before
from kiwi_mcp.primitives import Executor
from kiwi_mcp.handlers import DirectiveHandler
from kiwi_mcp.tools import SearchTool

# After
from lilux.primitives import Executor
from lilux.handlers import DirectiveHandler
from lilux.tools import SearchTool
```

**Test imports:**
```python
# Before
from kiwi_mcp.tests.fixtures import create_test_directive

# After
from lilux.tests.fixtures import create_test_directive
```

---

## Part 4: MCP Server Setup

### Server Bootstrap

File: `lilux/server.py`

```python
"""Lilux MCP Server

Provides 4 unified tools for working with directives, tools, and knowledge:
  - search: Find items by keyword/category
  - load: Load item content and metadata
  - execute: Run directives/tools, create items
  - help: Get usage and guidance
"""

import os
import logging
from pathlib import Path
from typing import Optional

from lilux.tools import SearchTool, LoadTool, ExecuteTool, HelpTool
from lilux.handlers import TypeHandlerRegistry
from lilux.utils.env_loader import load_env

# Logging setup
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=os.getenv("LILUX_LOG_LEVEL", "INFO"),
    format=os.getenv("LILUX_LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)


class LiluxServer:
    """MCP Server for Lilux kernel"""
    
    def __init__(self, user_space: Optional[str] = None):
        """Initialize server
        
        Args:
            user_space: Path to user .ai directory
                       Default: $USER_SPACE env var or ~/.local/share/lilux
        """
        # Load environment
        self.env = load_env()
        
        # User space (where custom directives/tools/knowledge live)
        self.user_space = Path(
            user_space or 
            os.getenv("USER_SPACE", 
                     Path.home() / ".local/share/lilux")
        )
        
        # Core content (bundled with package)
        self.core_content = self._get_core_content_root()
        
        # Initialize handlers
        self.handlers = TypeHandlerRegistry(
            core_root=self.core_content,
            user_root=self.user_space
        )
        
        # Initialize tools
        self.tools = {
            "search": SearchTool(self.handlers),
            "load": LoadTool(self.handlers),
            "execute": ExecuteTool(self.handlers),
            "help": HelpTool(),
        }
        
        logger.info(f"Lilux server initialized")
        logger.info(f"  Core content: {self.core_content}")
        logger.info(f"  User space: {self.user_space}")
    
    def _get_core_content_root(self) -> Path:
        """Get path to bundled .ai directory"""
        try:
            # Try importlib.resources (Python 3.9+)
            import importlib.resources
            files = importlib.resources.files("lilux")
            return Path(str(files.parent / ".ai"))
        except (ImportError, AttributeError):
            # Fallback: relative to this file
            return Path(__file__).parent.parent / ".ai"
    
    async def handle_tool_call(self, tool_name: str, arguments: dict) -> str:
        """Handle MCP tool call"""
        if tool_name not in self.tools:
            return f"Unknown tool: {tool_name}"
        
        tool = self.tools[tool_name]
        try:
            result = await tool.call(**arguments)
            return result
        except Exception as e:
            logger.error(f"Error in {tool_name}: {e}", exc_info=True)
            return f"Error: {e}"


def main():
    """Entry point for `lilux serve` command"""
    import sys
    import asyncio
    
    # Parse arguments
    user_space = None
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--user-space" and i + 1 < len(sys.argv) - 1:
            user_space = sys.argv[i + 2]
        elif arg == "--help":
            print("Usage: lilux serve [--user-space PATH]")
            sys.exit(0)
    
    # Initialize and run server
    server = LiluxServer(user_space=user_space)
    
    # For now, print server info
    # In production, this would start the MCP server
    print(f"Lilux MCP Server")
    print(f"Core content: {server.core_content}")
    print(f"User space: {server.user_space}")
    print(f"Ready to serve MCP connections")


if __name__ == "__main__":
    main()
```

### CLI Entry Points

File: `lilux/cli/__init__.py`

```python
"""Lilux CLI Commands"""

import click
from lilux.server import LiluxServer
from lilux.cli.init import init
from lilux.cli.demo import demo


@click.group()
def cli():
    """Lilux - AI-native execution kernel"""
    pass


@cli.command()
@click.option("--user-space", default=None, help="User space path")
def serve(user_space):
    """Start Lilux MCP server"""
    server = LiluxServer(user_space=user_space)
    # Implementation continues...
    click.echo(f"Lilux server running")
    click.echo(f"User space: {server.user_space}")


@cli.group()
def rye():
    """RYE commands (core content and utilities)"""
    pass


rye.add_command(init, name="init")
rye.add_command(demo, name="demo")


def main():
    cli()
```

---

## Part 5: Content Bundling

### Include .ai/ in Package

File: `MANIFEST.in`

```
# Include .ai directory in distributions
recursive-include .ai *

# Include docs
recursive-include docs *.md
recursive-include docs *.rst

# Include licenses
include LICENSE
include README.md
```

### Verify Bundling

```python
# In tests/test_bundling.py
def test_core_content_bundled():
    """Verify .ai directory is bundled"""
    from lilux import get_content_root
    
    root = get_content_root()
    assert root.exists(), "Core content not found"
    
    # Check for essential directories
    assert (root / "directives").exists()
    assert (root / "tools").exists()
    assert (root / "knowledge").exists()


def test_core_directives_accessible():
    """Verify core directives are accessible"""
    from lilux.handlers import DirectiveHandler
    
    handler = DirectiveHandler()
    
    # Should find init directive
    init = handler.load("core/init")
    assert init is not None
    assert init.metadata["name"] == "init"
```

---

## Part 6: User Space Initialization

### Init Directive Implementation

File: `.ai/directives/core/init.md`

```xml
<directive name="init" version="0.1.0">
  <metadata>
    <description>Initialize Lilux user space</description>
    <category>core</category>
    <requires_permission>file.write</requires_permission>
  </metadata>

  <process>
    <step name="detect_environment">
      <description>Detect system capabilities</description>
      <tool>core/detect_env</tool>
      <parameters>
        <output>environment.json</output>
      </parameters>
    </step>

    <step name="create_user_space">
      <description>Create user space directories</description>
      <tool>core/create_directories</tool>
      <parameters>
        <path>${USER_SPACE}</path>
        <structure>
          - user/directives
          - user/tools
          - user/knowledge
          - user/state
          - cache/embeddings
          - cache/indices
        </structure>
      </parameters>
    </step>

    <step name="generate_config">
      <description>Generate user config</description>
      <tool>core/generate_config</tool>
      <parameters>
        <template>default</template>
        <output>${USER_SPACE}/config.yaml</output>
        <environment_data>environment.json</environment_data>
      </parameters>
    </step>

    <step name="optional_vector_setup">
      <description>Optional: Set up vector search</description>
      <prompt>
        Would you like to set up local vector search for knowledge base?
        This requires: sentence-transformers package
      </prompt>
      <if_yes>
        <tool>rye/setup_vector_search</tool>
        <parameters>
          <config_path>${USER_SPACE}/config.yaml</config_path>
          <download_embeddings>true</download_embeddings>
        </parameters>
      </if_yes>
    </step>

    <step name="verification">
      <description>Verify setup</description>
      <tool>core/verify_setup</tool>
      <parameters>
        <user_space>${USER_SPACE}</user_space>
      </parameters>
    </step>

    <step name="next_steps">
      <description>Show next steps</description>
      <output>
        ✓ User space initialized at ${USER_SPACE}
        
        Next steps:
        [1] Run demo: execute action run directive core demo search directives
        [2] Explore help: execute action run directive core help
        [3] Create first directive: execute action run directive core demo create directives
      </output>
    </step>
  </process>
</directive>
```

### Init Script Implementation

File: `lilux/scripts/init.py`

```python
"""Initialize user space for Lilux"""

import os
import json
import tempfile
from pathlib import Path
from typing import Dict, Any

import click
import yaml

from lilux.utils import detect_environment, create_directories


def init_user_space(user_space: Path) -> Dict[str, Any]:
    """Initialize user space
    
    Args:
        user_space: Path to user space
        
    Returns:
        Initialization result dict
    """
    # Detect environment
    env_info = detect_environment()
    
    # Create directories
    dirs_created = create_directories(user_space, [
        "user/directives",
        "user/tools",
        "user/knowledge",
        "user/state",
        "cache/embeddings",
        "cache/indices",
    ])
    
    # Generate config
    config = {
        "version": "0.1",
        "user": {
            "created": str(datetime.now()),
        },
        "environment": env_info,
        "vector": {
            "enabled": False,
            "backend": "local",
        },
        "safety": {
            "max_depth": 50,
            "max_time": 300,
            "permission_mode": "strict",
        },
    }
    
    config_path = user_space / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)
    
    return {
        "user_space": str(user_space),
        "dirs_created": len(dirs_created),
        "config_created": str(config_path),
        "environment": env_info,
    }


@click.command()
@click.option("--user-space", default=None, help="User space path")
@click.option("--setup-vector", is_flag=True, help="Setup vector search")
def main(user_space, setup_vector):
    """Initialize Lilux user space"""
    from lilux import get_user_space
    
    space = Path(user_space or get_user_space())
    
    click.echo(f"Initializing Lilux user space at {space}")
    
    result = init_user_space(space)
    
    click.echo(f"✓ User space initialized")
    click.echo(f"  Created {result['dirs_created']} directories")
    click.echo(f"  Config: {result['config_created']}")
    
    if setup_vector:
        click.echo("Setting up vector search...")
        # Implementation


if __name__ == "__main__":
    main()
```

---

## Part 7: Testing Strategy

### Test Structure

```
tests/
├── test_lilux_package.py          # Package installation tests
├── test_bundling.py               # .ai directory bundling
├── test_cli_commands.py           # CLI entry points
├── test_server_bootstrap.py       # Server initialization
├── test_user_space_init.py        # User space creation
├── test_content_access.py         # Access bundled content
└── integration/
    ├── test_full_init_flow.py     # End-to-end init
    └── test_demo_workflows.py     # Demo execution
```

### Key Tests

```python
# tests/test_bundling.py
def test_ai_directory_in_wheel():
    """Verify .ai is included in wheel"""
    import lilux
    core_root = lilux.get_content_root()
    assert core_root.exists()
    assert (core_root / "directives").exists()


def test_core_directives_loadable():
    """Verify core directives load"""
    from lilux.handlers import DirectiveHandler
    handler = DirectiveHandler()
    
    init = handler.load("core/init")
    assert init.metadata["name"] == "init"


# tests/test_user_space_init.py
def test_init_command():
    """Test rye-init command"""
    from lilux.cli.init import init_user_space
    
    with tempfile.TemporaryDirectory() as tmpdir:
        result = init_user_space(Path(tmpdir))
        assert result["dirs_created"] > 0
        assert Path(tmpdir).exists()


# tests/integration/test_full_init_flow.py
def test_full_init_workflow():
    """Test complete initialization flow"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Init user space
        result = init_user_space(Path(tmpdir))
        assert result["user_space"]
        
        # Start server
        server = LiluxServer(user_space=tmpdir)
        assert server.core_content.exists()
        assert server.user_space == Path(tmpdir)
```

---

## Part 8: Versioning & Compatibility

### Version File

File: `lilux/__version__.py`

```python
"""Version information for Lilux"""

__version__ = "0.1.0"
__kernel_version__ = "0.1.0"
__content_version__ = "0.1.0"

# Compatibility matrix
COMPATIBLE_KERNEL_VERSIONS = [">=0.1.0"]
COMPATIBLE_CONTENT_VERSIONS = [">=0.1.0"]


def check_compatibility(kernel_version: str, content_version: str) -> bool:
    """Check kernel/content compatibility"""
    # Implementation
    pass
```

### Tag Strategy

```bash
# Releases
v0.1.0          # Lilux kernel 0.1.0 + RYE content 0.1.0

# Future: if separated
lilux-0.2.0     # Kernel only
rye-0.2.0       # Content only
```

---

## Part 9: Distribution Checklist

### For PyPI (`rye` package)

- [ ] Package name registered: `rye`
- [ ] `pyproject.toml` configured
- [ ] `setup.py` created
- [ ] `MANIFEST.in` includes `.ai/`
- [ ] All imports updated: `kiwi_mcp` → `lilux`
- [ ] Tests pass locally
- [ ] Build wheel: `python -m build`
- [ ] Test wheel installation: `pip install dist/rye-0.1.0-py3-none-any.whl`
- [ ] Verify entry points work: `lilux`, `rye-init`, `rye-demo`
- [ ] Upload to PyPI: `twine upload dist/*`
- [ ] Test installation: `pipx install rye`

### Verification After Installation

```bash
# Test package installed
python -c "import lilux; print(lilux.__version__)"

# Test entry points
lilux serve --help
rye-init --help
rye-demo --help

# Test content bundled
python -c "from lilux import get_content_root; print(get_content_root())"

# Verify directives accessible
python -c "from lilux.handlers import DirectiveHandler; print(DirectiveHandler().load('core/init'))"
```

---

## Part 10: Backwards Compatibility (Optional)

### During Transition (0.1.0 only)

Keep `kiwi_mcp` package working:

```python
# lilux/__init__.py
# Export everything as lilux

# kiwi_mcp/__init__.py (for compatibility only)
# Re-export from lilux with deprecation warning
import warnings
warnings.warn(
    "kiwi_mcp is deprecated, use lilux instead",
    DeprecationWarning,
    stacklevel=2
)

from lilux import *  # noqa
```

### Deprecation Timeline

- 0.1.0: Both `lilux` and `kiwi_mcp` work (warning)
- 0.2.0: Only `lilux` available
- 1.0.0: No backwards compatibility

---

## Summary

This migration provides:

1. **Single package**: `pipx install rye` gets everything
2. **Clean imports**: `lilux` namespace
3. **Bundled content**: `.ai/` directory included
4. **Entry points**: `lilux`, `rye-init`, `rye-demo` commands
5. **User space**: Separate from core, managed via env var
6. **Clear evolution**: Easy to split later if needed

---

_Document Status: Technical specification_  
_Last Updated: 2026-01-28_  
_Next: Begin implementation_
