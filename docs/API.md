# Kiwi MCP API Reference

Complete API documentation for all 4 tools and 3 item types.

---

## Tools Overview

| Tool | Purpose | Item Types | Operations |
|------|---------|-----------|------------|
| **search** | Find items across sources | All | Query, filter, sort |
| **load** | Download from registry | All | Get, destination |
| **execute** | Run operations | All | CRUD, run, publish, link |
| **help** | Usage guidance | N/A | Get help |

---

## 1. search Tool

**Purpose:** Find items by natural language query.

### Schema

```json
{
  "name": "search",
  "description": "Search for directives, tools, or knowledge entries",
  "inputSchema": {
    "type": "object",
    "properties": {
      "item_type": {
        "type": "string",
        "enum": ["directive", "tool", "knowledge"],
        "description": "Type of item to search for"
      },
      "query": {
        "type": "string",
        "description": "Search query (natural language or keywords)"
      },
      "source": {
        "type": "string",
        "enum": ["local", "registry", "all"],
        "default": "local",
        "description": "Search source"
      },
      "limit": {
        "type": "integer",
        "default": 10,
        "description": "Maximum results to return"
      }
    },
    "required": ["item_type", "query"]
  }
}
```

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `item_type` | string | ✓ | - | `directive`, `tool`, or `knowledge` |
| `query` | string | ✓ | - | Natural language search query |
| `source` | string | | `local` | `local`, `registry`, or `all` |
| `limit` | integer | | `10` | Max results (1-100) |

### Returns

**Success:**
```json
{
  "results": [
    {
      "id": "item_id",
      "name": "Item Name",
      "category": "category_name",
      "description": "Item description",
      "quality_score": 95.0,
      "source": "local"
    }
  ],
  "total": 1,
  "query": "search terms"
}
```

**Error:**
```json
{
  "error": "Error description",
  "supported_types": ["directive", "tool", "knowledge"]
}
```

### Examples

#### Search Directives in Registry

```bash
curl -X POST http://localhost:3000/tools/search \
  -H "Content-Type: application/json" \
  -d '{
    "item_type": "directive",
    "query": "authentication oauth setup",
    "source": "registry",
    "limit": 5
  }'
```

**Response:**
```json
{
  "results": [
    {
      "id": "oauth_setup",
      "name": "OAuth Authentication Setup",
      "category": "authentication",
      "description": "Configure OAuth with Google and GitHub",
      "quality_score": 96.5,
      "source": "registry",
      "version": "2.1.0"
    },
    {
      "id": "jwt_auth",
      "name": "JWT Authentication",
      "category": "authentication",
      "description": "JWT token-based authentication",
      "quality_score": 92.0,
      "source": "registry",
      "version": "1.5.0"
    }
  ],
  "total": 2
}
```

#### Search Tools Locally

```bash
curl -X POST http://localhost:3000/tools/search \
  -H "Content-Type: application/json" \
  -d '{
    "item_type": "tool",
    "query": "scrape web data",
    "source": "local"
  }'
```

#### Search Knowledge Everywhere

```bash
curl -X POST http://localhost:3000/tools/search \
  -H "Content-Type: application/json" \
  -d '{
    "item_type": "knowledge",
    "query": "email deliverability SMTP",
    "source": "all",
    "limit": 20
  }'
```

---

## 2. load Tool

**Purpose:** Download items from registry to local storage.

### Schema

```json
{
  "name": "load",
  "description": "Download or retrieve items from registry",
  "inputSchema": {
    "type": "object",
    "properties": {
      "item_type": {
        "type": "string",
        "enum": ["directive", "tool", "knowledge"],
        "description": "Type of item"
      },
      "item_id": {
        "type": "string",
        "description": "Item identifier (name or zettel_id)"
      },
      "destination": {
        "type": "string",
        "enum": ["project", "user"],
        "default": "project",
        "description": "Where to save"
      },
      "project_path": {
        "type": "string",
        "description": "Required if destination=project"
      },
      "version": {
        "type": "string",
        "description": "Specific version (defaults to latest)"
      }
    },
    "required": ["item_type", "item_id"]
  }
}
```

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `item_type` | string | ✓ | - | `directive`, `tool`, or `knowledge` |
| `item_id` | string | ✓ | - | Item identifier |
| `destination` | string | | `project` | `project` or `user` |
| `project_path` | string | ✓* | - | Required if `destination=project` |
| `version` | string | | `latest` | Specific semver version |

### Returns

**Success:**
```json
{
  "status": "loaded",
  "name": "item_id",
  "version": "1.0.0",
  "destination": "project",
  "path": "/home/user/myproject/.ai/directives/auth/oauth_setup.md",
  "size_bytes": 2048
}
```

**Error:**
```json
{
  "error": "Item not found in registry",
  "item_type": "directive",
  "item_id": "oauth_setup"
}
```

### Examples

#### Load Directive to Project

```bash
curl -X POST http://localhost:3000/tools/load \
  -H "Content-Type: application/json" \
  -d '{
    "item_type": "directive",
    "item_id": "oauth_setup",
    "destination": "project",
    "project_path": "/home/user/myapp"
  }'
```

**Response:**
```json
{
  "status": "loaded",
  "name": "oauth_setup",
  "version": "2.1.0",
  "destination": "project",
  "path": "/home/user/myapp/.ai/directives/auth/oauth_setup.md",
  "size_bytes": 3456
}
```

#### Load Tool to User Space

```bash
curl -X POST http://localhost:3000/tools/load \
  -H "Content-Type: application/json" \
  -d '{
    "item_type": "tool",
    "item_id": "google_maps_scraper",
    "destination": "user"
  }'
```

#### Load Specific Version

```bash
curl -X POST http://localhost:3000/tools/load \
  -H "Content-Type: application/json" \
  -d '{
    "item_type": "knowledge",
    "item_id": "001-email-deliverability",
    "version": "1.5.0",
    "destination": "user"
  }'
```

---

## 3. execute Tool

**Purpose:** Run operations: run, publish, delete, create, update, link.

### Schema

```json
{
  "name": "execute",
  "description": "Execute operations on items",
  "inputSchema": {
    "type": "object",
    "properties": {
      "item_type": {
        "type": "string",
        "enum": ["directive", "tool", "knowledge"],
        "description": "Type of item"
      },
      "action": {
        "type": "string",
        "enum": [
          "run", "publish", "delete", "create", "update", "link"
        ],
        "description": "Operation to perform"
      },
      "item_id": {
        "type": "string",
        "description": "Item identifier"
      },
      "parameters": {
        "type": "object",
        "description": "Action-specific parameters"
      },
      "dry_run": {
        "type": "boolean",
        "default": false,
        "description": "Validate without executing"
      },
      "project_path": {
        "type": "string",
        "description": "Project path for local operations"
      }
    },
    "required": ["item_type", "action", "item_id"]
  }
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `item_type` | string | ✓ | `directive`, `tool`, or `knowledge` |
| `action` | string | ✓ | Operation: `run`, `publish`, `delete`, `sign`, `link` |
| `item_id` | string | ✓ | Item identifier |
| `parameters` | object | | Action-specific params |
| `dry_run` | boolean | | Validate without executing |
| `project_path` | string | | Project path for file operations |

### Supported Actions by Type

#### directive

| Action | Description | Parameters |
|--------|-------------|-----------|
| `run` | Execute directive | `{}` |
| `publish` | Publish to registry | `version`, `changelog` |
| `delete` | Remove | `confirm`, `source` |
| `sign` | Validate and sign | `location`, `category` |

#### tool

| Action | Description | Parameters |
|--------|-------------|-----------|
| `run` | Execute with inputs | `inputs`, `dry_run` |
| `publish` | Publish to registry | `version`, `changelog` |
| `delete` | Remove | `confirm`, `source` |
| `sign` | Validate and sign | `location`, `category` |

#### knowledge

| Action | Description | Parameters |
|--------|-------------|-----------|
| `run` | Load entry content | `{}` |
| `sign` | Validate and sign entry | `location`, `category` |
| `delete` | Remove | `confirm`, `source` |
| `link` | Link to another entry | `target_id`, `relationship_type` |
| `publish` | Publish to registry | `version` |

### Returns

**Success (varies by action):**
```json
{
  "status": "executed|published|deleted|signed|linked",
  "name": "item_id",
  "action": "action_name",
  "result": {}
}
```

**Error:**
```json
{
  "error": "Error description",
  "item_type": "directive",
  "action": "run",
  "item_id": "test",
  "message": "Failed to execute run on directive"
}
```

### Examples

#### Run a Directive

```bash
curl -X POST http://localhost:3000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "item_type": "directive",
    "action": "run",
    "item_id": "oauth_setup",
    "parameters": {
      "provider": "google",
      "callback_url": "http://localhost:3000/auth/callback"
    }
  }'
```

**Response:**
```json
{
  "status": "executed",
  "action": "run",
  "name": "oauth_setup",
  "source": "local",
  "content": "# OAuth Setup Directive\n\n## Step 1: Configure...",
  "instructions": "Follow the directive steps above."
}
```

#### Publish Directive to Registry

```bash
curl -X POST http://localhost:3000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "item_type": "directive",
    "action": "publish",
    "item_id": "my_directive",
    "parameters": {
      "version": "1.0.0",
      "changelog": "Initial release"
    },
    "project_path": "/home/user/myproject"
  }'
```

**Response:**
```json
{
  "status": "published",
  "name": "my_directive",
  "version": "1.0.0",
  "registry": "supabase",
  "url": "https://registry.kiwi.ai/directives/my_directive"
}
```

#### Delete with Confirmation

```bash
curl -X POST http://localhost:3000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "item_type": "knowledge",
    "action": "delete",
    "item_id": "001-old-entry",
    "parameters": {
      "confirm": true,
      "source": "local"
    }
  }'
```

#### Create Knowledge Entry

**Note:** The file must exist first. Use `create_knowledge` directive or create the file manually, then use `create` action to validate and sign.

```bash
# Step 1: Create the file (via create_knowledge directive or manually)
# File should be at: .ai/knowledge/{category}/{zettel_id}.md

# Step 2: Validate and sign the file
curl -X POST http://localhost:3000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "item_type": "knowledge",
    "action": "create",
    "item_id": "003-new-pattern",
    "parameters": {
      "location": "project",
      "category": "patterns"
    },
    "project_path": "/home/user/myproject"
  }'
```

#### Link Knowledge Entries

```bash
curl -X POST http://localhost:3000/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "item_type": "knowledge",
    "action": "link",
    "item_id": "001-email-deliverability",
    "parameters": {
      "target_id": "002-smtp-config",
      "relationship_type": "references"
    }
  }'
```

---

## 4. help Tool

**Purpose:** Provide usage guidance and troubleshooting.

### Schema

```json
{
  "name": "help",
  "description": "Get usage help and guidance",
  "inputSchema": {
    "type": "object",
    "properties": {
      "topic": {
        "type": "string",
        "description": "Help topic (search, load, execute, directive, tool, knowledge)"
      }
    },
    "required": []
  }
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `topic` | string | | Help topic (optional) |

### Returns

```json
{
  "help": "Help text content...",
  "topic": "search"
}
```

### Examples

#### General Help

```bash
curl -X POST http://localhost:3000/tools/help \
  -H "Content-Type: application/json" \
  -d '{}'
```

#### Help for search Tool

```bash
curl -X POST http://localhost:3000/tools/help \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "search"
  }'
```

#### Help for Directives

```bash
curl -X POST http://localhost:3000/tools/help \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "directive"
  }'
```

---

## Item Type Details

### directive

**Storage:**
- Project: `.ai/directives/{category}/{name}.md`
- User: `~/.ai/directives/{category}/{name}.md`

**Format:** Markdown with YAML frontmatter
```yaml
---
name: directive_name
version: 1.0.0
category: setup
description: What this directive does
---

# Directive Content

Steps and instructions...
```

**Operations:**
- `search` - Find directives
- `load` - Download from registry
- `run` - Execute (returns content)
- `publish` - Publish to registry
- `delete` - Remove locally or from registry
- `create` - Create new locally
- `update` - Modify existing

**Metadata:**
- `name` - Directive identifier (required)
- `version` - Semantic version (required)
- `category` - Organization category (optional)
- `description` - What it does (optional)

---

### tool

**Storage:**
- Project: `.ai/tools/{category}/{tool_id}/`
- User: `~/.ai/tools/{category}/{tool_id}/`

**Format:** YAML manifest + source files
```yaml
# manifest.yaml
tool_id: my_tool
tool_type: script
executor_id: python_runtime
version: 1.0.0
category: scraping
description: What this tool does
manifest:
  entrypoint: main.py
  language: python
```

```python
# main.py
def main(**kwargs):
    # Implementation
    pass

if __name__ == "__main__":
    main()
```

**Operations:**
- `search` - Find tools
- `load` - Download from registry
- `run` - Execute with parameters (via chain resolution)
- `publish` - Publish to registry
- `delete` - Remove locally or from registry

**Metadata:**
- `tool_id` - Tool identifier (required)
- `tool_type` - Type of tool (script, mcp_server, runtime, etc.)
- `executor_id` - References another tool that executes this one
- `version` - Semantic version (required)
- `category` - Organization category (optional)
- `description` - What it does (optional)
- `dependencies` - Python packages (optional)
- `success_rate` - Execution success rate (optional)

---

### knowledge

**Storage:**
- Project: `.ai/knowledge/{category}/{zettel_id}.md`
- User: `~/.knowledge-kiwi/{category}/{zettel_id}.md`

**Format:** Markdown with frontmatter
```yaml
---
zettel_id: 001-email-deliverability
title: Email Deliverability Best Practices
entry_type: pattern
category: email-infrastructure
tags:
  - email
  - smtp
  - deliverability
---

# Content

Markdown content here...
```

**Operations:**
- `search` - Find entries
- `load` - Download from registry
- `create` - Create new
- `update` - Modify existing
- `delete` - Remove
- `link` - Link to another entry
- `publish` - Publish to registry

**Entry Types:**
- `api_fact` - API documentation facts
- `pattern` - Design/architecture patterns
- `concept` - Conceptual explanations
- `learning` - Lessons learned
- `experiment` - Experimental results
- `reference` - Reference material
- `template` - Reusable templates
- `workflow` - Process workflows

**Metadata:**
- `zettel_id` - Unique identifier (required)
- `title` - Entry title (required)
- `entry_type` - Type of entry (required)
- `category` - Organization category (optional)
- `tags` - Search tags (optional)

---

## Error Codes

| Code | Meaning | Example |
|------|---------|---------|
| 400 | Bad request | Missing required parameter |
| 404 | Not found | Item doesn't exist |
| 422 | Validation error | Invalid item_type |
| 500 | Server error | Unexpected exception |

---

## Status Responses

| Status | Meaning |
|--------|---------|
| `loaded` | Item successfully loaded |
| `published` | Item published to registry |
| `deleted` | Item deleted |
| `created` | Item created |
| `updated` | Item updated |
| `executed` | Operation completed |
| `linked` | Entries linked |

---

## Response Format

All responses are JSON strings wrapped in MCP TextContent.

**Standard Success:**
```json
{
  "status": "success_status",
  "name": "item_id",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "...": "additional fields depend on operation"
}
```

**Standard Error:**
```json
{
  "error": "Error description",
  "item_type": "type",
  "action": "operation",
  "message": "Human-readable message"
}
```

---

## Rate Limiting

Currently: None  
Future: Per-operation rate limiting via middleware

---

## Versioning

Current API version: **1.0.0**

Breaking changes will increment major version (2.0.0, etc.)
