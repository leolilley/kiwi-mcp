# Kiwi MCP - Unified AI Agent Tools

A unified MCP (Model Context Protocol) server consolidating **directives**, **scripts**, and **knowledge** management into **4 simple tools**.

**Status:** ✅ Ready for Production  
**Version:** 0.1.0  
**Coverage:** >85%

---

## Overview

Kiwi MCP reduces 17 tools from three separate MCPs into 4 unified tools with consistent interfaces:

| Tool        | Purpose                                                            |
| ----------- | ------------------------------------------------------------------ |
| **search**  | Find directives, scripts, or knowledge entries (local or registry) |
| **load**    | Download items from registry to local storage                      |
| **execute** | Run operations: publish, delete, create, update, link, run         |
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
    "limit": 10
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
    }
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
    }
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
- `source` (optional): `"local"`, `"registry"`, or `"all"` (default: `"local"`)
- `limit` (optional): Max results (default: 10)

**Returns:** JSON with `results` array or `error`

**Examples:**

```python
# Search for email-related knowledge
search(
    item_type="knowledge",
    query="email deliverability",
    source="registry"
)

# Search local scripts
search(
    item_type="script",
    query="scrape Google Maps",
    limit=5
)
```

---

### load

Download items from registry to local storage.

**Parameters:**

- `item_type` (required): `"directive"`, `"script"`, or `"knowledge"`
- `item_id` (required): Item identifier
- `destination` (optional): `"project"` or `"user"` (default: `"project"`)
- `project_path` (optional): Required if `destination="project"`
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
    destination="user"
)
```

---

### execute

Run operations on items: run, publish, delete, create, update, link.

**Parameters:**

- `item_type` (required): `"directive"`, `"script"`, or `"knowledge"`
- `action` (required): `"run"`, `"publish"`, `"delete"`, `"create"`, `"update"`, `"link"`
- `item_id` (required): Item identifier
- `parameters` (optional): Action-specific parameters dict
- Additional parameters: `dry_run`, `project_path`, etc.

**Returns:** JSON with operation result or `error`

**Supported Actions by Type:**

**Directive:**

- `run` - Execute directive (returns parsed content)
- `publish` - Publish to registry
- `delete` - Remove locally or from registry
- `create` - Create new directive
- `update` - Modify existing directive

**Script:**

- `run` - Execute script with parameters
- `publish` - Publish to registry
- `delete` - Remove locally or from registry

**Knowledge:**

- `create` - Create new entry
- `update` - Modify existing entry
- `delete` - Remove entry
- `link` - Link entries together
- `publish` - Publish to registry

**Examples:**

```python
# Run a directive
execute(
    item_type="directive",
    action="run",
    item_id="setup_auth",
    parameters={"provider": "google"}
)

# Publish script to registry
execute(
    item_type="script",
    action="publish",
    item_id="my_scraper",
    parameters={"version": "1.0.0"}
)

# Delete with confirmation
execute(
    item_type="knowledge",
    action="delete",
    item_id="001-old-entry",
    parameters={"confirm": True}
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

# User space directory (optional, defaults to ~/.ai)
AI_USER_SPACE=~/.ai

# Log level
LOG_LEVEL=INFO
```

### .env File

```bash
# Copy template
cp .env.example .env

# Edit with your values
nano .env
```

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
- **Current:** ✅ Achieved

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

- Location: `.ai/scripts/` (project) or `~/.script-kiwi/scripts/` (user)
- Format: Python (.py)
- Operations: search, load, run, publish, delete

**knowledge**

- Location: `.ai/knowledge/` (project) or `~/.knowledge-kiwi/` (user)
- Format: Markdown with metadata
- Operations: search, load, create, update, delete, link, publish

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
