# Kiwi MCP - Unified AI Agent Tools

A unified MCP (Model Context Protocol) server consolidating **directives**, **scripts**, and **knowledge** management into **4 simple tools**.

**Version:** 0.1.0  
**Coverage:** 30% (tests in progress)

---

## Overview

Kiwi MCP reduces 17 tools from three separate MCPs into 4 unified tools with consistent interfaces:

| Tool        | Purpose                                                            |
| ----------- | ------------------------------------------------------------------ |
| **search**  | Find directives, scripts, or knowledge entries (local or registry) |
| **load**    | Download items from registry to local storage                      |
| **execute** | Run operations: publish, delete, create, update, run               |
| **help**    | Get usage guidance and troubleshooting                             |

**Supported Types:**

- `directive` - Workflow guides and configurations
- `script` - Python execution scripts
- `knowledge` - Zettelkasten knowledge entries

---

## Installation

### Prerequisites

- Python ≥3.11
- pip or poetry

### From Source

```bash
cd kiwi-mcp
pip install -e ".[dev]"
```

### Dependencies

- `mcp>=1.0.0` - Model Context Protocol
- `pydantic>=2.0.0` - Data validation
- `httpx>=0.27.0` - HTTP client
- `supabase>=2.0.0` - Registry backend
- `python-dotenv>=1.0.0` - Environment configuration
- `pyyaml>=6.0.0` - YAML parsing
- `aiofiles>=23.0.0` - Async file I/O

---

## Quick Start

### Initialize

```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SECRET_KEY="your-secret-key"

# Run server
python -m kiwi_mcp.server
```

### Usage Examples

#### Search for Directives

```json
{
  "tool": "search",
  "arguments": {
    "item_type": "directive",
    "query": "authentication setup",
    "source": "registry",
    "limit": 10,
    "project_path": "/home/user/myproject"
  }
}
```

**Response:**

```json
{
  "results": [
    {
      "name": "oauth_setup",
      "category": "authentication",
      "description": "Setup OAuth with Google and GitHub",
      "quality_score": 95.0
    }
  ]
}
```

#### Load a Script

```json
{
  "tool": "load",
  "arguments": {
    "item_type": "script",
    "item_id": "google_maps_scraper",
    "destination": "project",
    "project_path": "/home/user/myproject"
  }
}
```

**Response:**

```json
{
  "status": "loaded",
  "name": "google_maps_scraper",
  "version": "2.1.0",
  "destination": "project",
  "path": "/home/user/myproject/.ai/scripts/scraping/google_maps_scraper.py"
}
```

#### Run a Directive

```json
{
  "tool": "execute",
  "arguments": {
    "item_type": "directive",
    "action": "run",
    "item_id": "bootstrap_project",
    "parameters": {
      "project_name": "my_app",
      "language": "python"
    },
    "project_path": "/home/user/myproject"
  }
}
```

**Response:**

```json
{
  "action": "run",
  "name": "bootstrap_project",
  "source": "local",
  "content": "# Bootstrap Directive\n1. Create project structure...",
  "instructions": "Follow the directive steps above."
}
```

#### Publish to Registry

```json
{
  "tool": "execute",
  "arguments": {
    "item_type": "knowledge",
    "action": "publish",
    "item_id": "001-email-deliverability",
    "parameters": {
      "version": "1.0.0",
      "changelog": "Initial release with best practices"
    },
    "project_path": "/home/user/myproject"
  }
}
```

---

## Tools Reference

### search

Find items by natural language query across local and registry sources.

**Parameters:**

- `item_type` (required): `"directive"`, `"script"`, or `"knowledge"`
- `query` (required): Natural language search query
- `project_path` (required): Absolute path to project root
- `source` (optional): `"local"`, `"registry"`, or `"all"` (default: `"local"`)
- `limit` (optional): Max results (default: 10)

**Returns:** JSON with `results` array or `error`

**Examples:**

```python
# Search for email-related knowledge
search(
    item_type="knowledge",
    query="email deliverability",
    source="registry",
    project_path="/home/user/myproject"
)

# Search local scripts
search(
    item_type="script",
    query="scrape Google Maps",
    limit=5,
    project_path="/home/user/myproject"
)
```

---

### load

Download items from registry to local storage.

**Parameters:**

- `item_type` (required): `"directive"`, `"script"`, or `"knowledge"`
- `item_id` (required): Item identifier
- `project_path` (required): Absolute path to project root
- `destination` (optional): `"project"` or `"user"` (default: `"project"`)
- `version` (optional): Specific version to load

**Returns:** JSON with `status`, `path`, and metadata

**Examples:**

```python
# Load directive to project
load(
    item_type="directive",
    item_id="oauth_setup",
    destination="project",
    project_path="/home/user/myapp"
)

# Load knowledge to user space
load(
    item_type="knowledge",
    item_id="001-jwt-auth",
    destination="user",
    project_path="/home/user/myapp"
)
```

---

### execute

Run operations on items: run, publish, delete, create, update.

**Parameters:**

- `item_type` (required): `"directive"`, `"script"`, or `"knowledge"`
- `action` (required): `"run"`, `"publish"`, `"delete"`, `"create"`, `"update"`
- `item_id` (required): Item identifier
- `project_path` (required): Absolute path to project root
- `parameters` (optional): Action-specific parameters dict
- Additional parameters: `dry_run`, etc.

**Returns:** JSON with operation result or `error`

**Supported Actions (All Types):**

All item types support the same 6 actions for consistency:

- `run` - Execute/load the item (directives return parsed content, scripts execute with params, knowledge returns entry)
- `publish` - Publish to registry with version
- `delete` - Remove from local or registry (requires `confirm: true`)
- `create` - Create new item locally
- `update` - Modify existing item

**Type-Specific Behavior:**

| Action    | Directive                         | Script                         | Knowledge             |
| --------- | --------------------------------- | ------------------------------ | --------------------- |
| `run`     | Returns parsed XML content        | Executes in venv with params   | Returns entry content |
| `publish` | Creates version with content_hash | Uploads .py file with metadata | Publishes with tags   |

**Examples:**

```python
# Run a directive
execute(
    item_type="directive",
    action="run",
    item_id="setup_auth",
    parameters={"provider": "google"},
    project_path="/home/user/myproject"
)

# Publish script to registry
execute(
    item_type="script",
    action="publish",
    item_id="my_scraper",
    parameters={"version": "1.0.0"},
    project_path="/home/user/myproject"
)

# Delete with confirmation
execute(
    item_type="knowledge",
    action="delete",
    item_id="001-old-entry",
    parameters={"confirm": True},
    project_path="/home/user/myproject"
)
```

---

### help

Get usage guidance, examples, and troubleshooting.

**Parameters:**

- `topic` (optional): Specific topic for help

**Returns:** JSON with help text

**Examples:**

```python
# General help
help()

# Help for search tool
help(topic="search")

# Help for directive workflows
help(topic="directive")
```

---

## Configuration

### Environment Variables

```bash
# Supabase registry (optional)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SECRET_KEY=your-secret-key

# User space directory (optional, defaults to ~/.ai if not provided)
# Set this in your MCP client configuration (e.g., Cursor's mcp.json)
# If not provided, defaults to ~/.ai
USER_SPACE=~/.ai

# Log level
LOG_LEVEL=INFO
```

**Note:** `USER_SPACE` is typically provided via your MCP client configuration (e.g., Cursor's `mcp.json`). If not set, it defaults to `~/.ai`.

### .env Files

Environment variables can be loaded from hierarchical `.env` files:

```bash
# Userspace defaults (applies to all projects)
~/.ai/.env

# Project-specific overrides
.ai/.env
```

Scripts automatically load both files in order (userspace → project → runtime).

---

## Script Execution Features

### Virtual Environment Isolation

Scripts run in isolated virtual environments:

- **Script from userspace** (`~/.ai/scripts/`): always uses `~/.ai/.venv/`
- **Script from project** (`.ai/scripts/`): uses `.ai/scripts/.venv/` if it exists; otherwise falls back to `~/.ai/.venv/`

The userspace venv is created on first use if missing. The project venv is not auto-created; if absent, execution uses the userspace venv.

### Dependency Auto-Install

Dependencies are automatically detected and installed:

- From script `import` statements
- From lib module imports
- Supports version constraints

```python
# Script automatically installs: requests, beautifulsoup4
import requests
from bs4 import BeautifulSoup
from lib.http_session import get_session  # Also installs lib dependencies
```

### Shared Libraries

Scripts can import from shared library modules:

```python
# Project lib (priority)
from lib.project_utils import helper

# Userspace lib (fallback)
from lib.http_session import get_session
from lib.youtube_utils import extract_video_id
```

Library locations:

- `.ai/scripts/lib/` (project)
- `~/.ai/scripts/lib/` (userspace)

### Output Management

Large script outputs are automatically saved:

- **Project**: `.ai/outputs/scripts/{script_name}/`
- **Userspace**: `~/.ai/outputs/scripts/{script_name}/`
- Keeps last 10 outputs per script
- Auto-truncates MCP responses >1MB

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     MCP Server                              │
├──────────────┬──────────────┬──────────────┬────────────────┤
│   search     │     load     │   execute    │      help      │
└──────┬───────┴──────┬───────┴──────┬───────┴────────┬───────┘
       │              │              │                │
       └──────────────┴──────────────┴────────────────┘
              TypeHandlerRegistry
       ┌──────────┬──────────┬──────────┐
       │          │          │          │
   Directive   Script    Knowledge    (Future)
   Handler     Handler    Handler
       │          │          │
       ├──────────┼──────────┤
       │  Local + Registry Storage
```

### Project Structure

```
kiwi-mcp/
├── kiwi_mcp/
│   ├── __init__.py              # Package
│   ├── server.py                # MCP server entry
│   ├── tools/                   # 4 unified tools
│   │   ├── base.py              # BaseTool abstract class
│   │   ├── search.py            # SearchTool
│   │   ├── load.py              # LoadTool
│   │   ├── execute.py           # ExecuteTool
│   │   └── help.py              # HelpTool
│   ├── handlers/                # Type-specific handlers
│   │   ├── registry.py          # TypeHandlerRegistry
│   │   ├── directive/           # Directive handlers
│   │   ├── script/              # Script handlers
│   │   └── knowledge/           # Knowledge handlers
│   ├── api/                     # Registry clients
│   │   ├── directive_registry.py
│   │   ├── script_registry.py
│   │   └── knowledge_registry.py
│   └── utils/                   # Shared utilities
├── tests/
│   ├── unit/
│   │   ├── test_tools.py        # Tool tests (20+)
│   │   └── test_handlers.py     # Handler tests (20+)
│   └── integration/
├── docs/                        # Documentation
├── README.md                    # This file
├── pytest.ini
└── pyproject.toml
```

---

## Testing

### Run All Tests

```bash
pytest tests/ -v
```

### Run Unit Tests Only

```bash
pytest tests/unit/ -v
```

### Coverage Report

```bash
pytest tests/ -v --cov=kiwi_mcp --cov-report=html
# Open htmlcov/index.html
```

### Coverage Target

- **Goal:** >85% code coverage
- **Current:** 30% (tests in progress)

---

## Development

### Install Dev Dependencies

```bash
pip install -e ".[dev]"
```

### Code Quality

```bash
# Linting
ruff check kiwi_mcp/

# Format
ruff format kiwi_mcp/

# Type checking
mypy kiwi_mcp/ --ignore-missing-imports
```

### Running Locally

```bash
# Development server
python -m kiwi_mcp.server

# Or with auto-reload
pytest-watch tests/
```

---

## API Reference

### Item Types

**directive**

- Location: `.ai/directives/` (project) or `~/.ai/directives/` (user)
- Format: Markdown with YAML frontmatter
- Operations: search, load, run, publish, delete, create, update

**script**

- Location: `.ai/scripts/` (project) or `~/.ai/scripts/` (user)
- Format: Python (.py)
- Operations: search, load, run, publish, delete
- Features: venv isolation, auto-install dependencies, lib imports, .env loading

**knowledge**

- Location: `.ai/knowledge/` (project) or `~/.ai/knowledge/` (user)
- Format: Markdown with metadata
- Operations: search, load, create, update, delete, publish

### Sources

- **local** - Search only in `.ai/` directories
- **registry** - Search only in Supabase registry
- **all** - Search both local and registry (registry items marked separately)

### Error Handling

All tools return consistent error responses:

```json
{
  "error": "Description of what went wrong",
  "item_type": "directive",
  "message": "Human-readable message"
}
```

---

## Troubleshooting

### Import Errors

```python
from kiwi_mcp import KiwiMCP
from kiwi_mcp.server import main
```

If imports fail:

1. Check Python version: `python --version` (need ≥3.11)
2. Reinstall: `pip install -e .`

### No Supabase Connection

If registry is unavailable, local operations still work:

- Search: Use `source="local"`
- Load: Downloads from registry disabled
- Execute: Local operations only

### Slow Search

- Use `limit` parameter to reduce results
- Add more specific keywords
- Filter by category/tags (see handler docs)

---

## Contributing

1. Write tests first
2. Implement feature
3. Run: `pytest tests/ -v --cov=kiwi_mcp`
4. Check coverage >85%
5. Lint: `ruff check kiwi_mcp/`

---

## License

MIT License - see LICENSE file

---

## Support

- **Documentation:** `docs/ARCHITECTURE.md`, `docs/API.md`
- **Examples:** See quick start above
- **Issues:** GitHub issues

---

## Roadmap

- [ ] GraphQL registry queries
- [ ] Authentication/authorization
- [ ] Webhooks and real-time updates
- [ ] Web UI for management
- [ ] Plugin system for custom handlers
- [ ] Vector search with RAG
