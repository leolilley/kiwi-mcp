# Registry API Quick Start

## Import

```python
from kiwi_mcp.api import (
    DirectiveRegistry,
    ScriptRegistry,
    KnowledgeRegistry
)
```

## Basic Usage

### DirectiveRegistry

```python
registry = DirectiveRegistry()

# Search for directives
results = await registry.search("auth setup", category="security")

# Get a specific directive
directive = await registry.get("bootstrap", version="1.0.0")

# List all directives
all_directives = await registry.list(category="setup")

# Publish a new directive
result = await registry.publish(
    name="my_directive",
    version="1.0.0",
    content="# My Directive\n...",
    category="utilities",
    description="A useful directive"
)

# Delete a directive
result = await registry.delete("my_directive", version="1.0.0")
```

### ScriptRegistry

```python
registry = ScriptRegistry()

# Search for scripts
results = await registry.search("scrape google maps", category="scraping")

# Get a specific script
script = await registry.get("google_maps_scraper", version="2.0.0")

# List all scripts
all_scripts = await registry.list()

# Publish a new script
result = await registry.publish(
    name="my_script",
    version="1.0.0",
    content="#!/usr/bin/env python3\n...",
    category="utility",
    tech_stack=["Python", "Selenium"]
)

# Delete a script
result = await registry.delete("my_script")
```

### KnowledgeRegistry

```python
registry = KnowledgeRegistry()

# Search for knowledge entries
results = await registry.search(
    "email deliverability",
    entry_type="pattern",
    tags=["email"]
)

# Get a specific entry
entry = await registry.get("001-email-best-practices")

# List all entries
all_entries = await registry.list(category="email-infrastructure")

# Publish a new entry
result = await registry.publish(
    zettel_id="003-new-entry",
    title="New Knowledge Entry",
    content="# New Entry\n...",
    entry_type="learning",
    category="testing",
    tags=["testing", "new"]
)

# Get relationships
rels = await registry.get_relationships("001-email-best-practices")

# Create a relationship
result = await registry.create_relationship(
    from_zettel_id="001",
    to_zettel_id="002",
    relationship_type="references"
)

# Delete an entry
result = await registry.delete("003-new-entry", cascade_relationships=True)
```

## Search Features

### Multi-Term Search (AND Logic)
All terms must match:
```python
# Only returns results with BOTH "email" AND "validation"
results = await registry.search("email validation")
```

### Category Filter
```python
results = await registry.search("bootstrap", category="setup")
```

### Entry Type Filter (Knowledge Only)
```python
results = await registry.search("auth", entry_type="pattern")
```

### Tags Filter (Knowledge Only)
```python
results = await registry.search("security", tags=["auth", "oauth"])
```

## Relevance Scoring

All searches return results with `relevance_score` (0-100):
- Exact name match: 100
- All terms in name: 80
- Some terms in name: 60 * (matches/total)
- All terms in description: 40
- Some terms in description: 20 * (matches/total)

Results are sorted by score descending.

## Configuration

Set environment variables:
```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SECRET_KEY="your-secret-key"  # or SUPABASE_ANON_KEY
```

## Error Handling

All methods are safe to call:

```python
# search() returns empty list on error
results = await registry.search("test")  # [] if error

# get() returns None on error
entry = await registry.get("nonexistent")  # None if error

# publish()/delete() return error dict
result = await registry.publish(...)
if "error" in result:
    print(f"Error: {result['error']}")
else:
    print(f"Success: {result['status']}")
```

## Testing

Run integration tests:
```bash
cd /home/leo/projects/kiwi-mcp
. .venv/bin/activate
pytest tests/ -v
```

All 21 tests should pass.
