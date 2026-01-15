# Handler Architecture

## Overview

The kiwi-mcp handlers implement a clear separation between LOCAL and REMOTE operations:

- **Handlers**: Handle LOCAL file operations (.ai/ folders)
- **Registries**: Handle REMOTE Supabase operations only

## Architecture Principles

### 1. Local Operations (Handlers)

Handlers implement these operations directly WITHOUT delegating to registries:

- `search()` - Search local files (project + user space)
- `load()` - Load from local files
- `run()` / `execute()` - Execute from local files
- `create()` - Create local files
- `update()` - Update local files
- `delete()` - Delete local files (with optional registry sync)

### 2. Remote Operations (Registries)

Handlers delegate to registries ONLY for:

- `publish()` - Upload to Supabase
- `download()` - Download from Supabase (in `load()` when local not found)
- `search(source="registry")` - Search Supabase

### 3. Mixed Operations

Some operations handle both local and remote:

- `search(source="all")` - Search local THEN registry, merge results
- `delete(source="all")` - Delete local AND registry
- `load(destination="...")` - Load local OR download from registry

## Implementation Pattern

Each handler should follow this structure:

```python
class DirectiveHandler:
    def __init__(self, project_path: Optional[str] = None):
        self.project_path = Path(project_path) if project_path else None
        self.logger = get_logger("directive_handler")
        self.registry = DirectiveRegistry()  # Only for remote ops
        
        # LOCAL file handling
        self.resolver = DirectiveResolver(self.project_path)
        self.search_paths = [
            self.project_path / ".ai" / "directives",
            Path.home() / ".context-kiwi" / "directives"
        ]
    
    async def search(self, query, source="local", **kwargs):
        """Search local AND/OR registry."""
        results = []
        
        # LOCAL search
        if source in ("local", "all"):
            results.extend(self._search_local(query, **kwargs))
        
        # REMOTE search
        if source in ("registry", "all"):
            registry_results = await self.registry.search(query, **kwargs)
            results.extend(registry_results)
        
        return results
    
    async def load(self, directive_name, **kwargs):
        """Load from local OR download from registry."""
        # Try local first
        file_path = self.resolver.resolve(directive_name)
        if file_path:
            return self._parse_directive_file(file_path)
        
        # Not found locally - download from registry
        registry_data = await self.registry.get(directive_name)
        if registry_data and kwargs.get("destination"):
            self._save_local(directive_name, registry_data, kwargs["destination"])
            return registry_data
        
        return {"error": "Not found"}
    
    async def execute(self, action, item_id, params):
        """Dispatch to local operation methods."""
        if action == "run":
            return await self._run_directive(item_id, params)
        elif action == "publish":
            return await self._publish_directive(item_id, params)
        elif action == "delete":
            return await self._delete_directive(item_id, params)
        elif action == "create":
            return await self._create_directive(item_id, params)
        elif action == "update":
            return await self._update_directive(item_id, params)
        elif action == "link":
            return await self._link_directive(item_id, params)
        else:
            return {"error": f"Unknown action: {action}"}
    
    async def _run_directive(self, directive_name, params):
        """Execute directive - LOCAL ONLY."""
        file_path = self.resolver.resolve(directive_name)
        if not file_path:
            return {"error": "Directive not found locally"}
        
        # Parse and return directive for agent to execute
        return self._parse_directive_file(file_path)
    
    async def _publish_directive(self, directive_name, params):
        """Publish directive - REMOTE (uses registry)."""
        # Find local file
        file_path = self.resolver.resolve(directive_name)
        if not file_path:
            return {"error": "Directive not found locally"}
        
        # Read content
        content = file_path.read_text()
        
        # Delegate to registry
        return await self.registry.publish(
            name=directive_name,
            content=content,
            version=params.get("version")
        )
    
    async def _delete_directive(self, directive_name, params):
        """Delete directive - LOCAL AND/OR REMOTE."""
        source = params.get("source", "all")
        results = {"deleted": []}
        
        if source in ("local", "all"):
            file_path = self.resolver.resolve(directive_name)
            if file_path:
                file_path.unlink()
                results["deleted"].append("local")
        
        if source in ("registry", "all"):
            await self.registry.delete(directive_name)
            results["deleted"].append("registry")
        
        return results
    
    def _search_local(self, query, **kwargs):
        """Search local files - PRIVATE helper."""
        from kiwi_mcp.utils.file_search import search_markdown_files, score_relevance
        from kiwi_mcp.utils.parsers import parse_directive_file
        
        results = []
        query_terms = query.lower().split()
        
        # Search in all search paths
        files = search_markdown_files(self.search_paths)
        
        for file_path in files:
            try:
                directive = parse_directive_file(file_path)
                score = score_relevance(
                    directive["name"] + " " + directive["description"],
                    query_terms
                )
                
                if score > 0:
                    results.append({
                        "name": directive["name"],
                        "description": directive["description"],
                        "version": directive["version"],
                        "score": score,
                        "source": "project" if ".ai/" in str(file_path) else "user"
                    })
            except Exception as e:
                self.logger.warning(f"Error parsing {file_path}: {e}")
        
        return results
    
    def _parse_directive_file(self, file_path: Path):
        """Parse directive file - PRIVATE helper."""
        from kiwi_mcp.utils.parsers import parse_directive_file
        return parse_directive_file(file_path)
```

## File Structure

### Handlers

- `kiwi_mcp/handlers/directive/handler.py` - DirectiveHandler
- `kiwi_mcp/handlers/script/handler.py` - ScriptHandler
- `kiwi_mcp/handlers/knowledge/handler.py` - KnowledgeHandler

### Utilities (LOCAL operations)

- `kiwi_mcp/utils/resolvers.py` - Path resolution
- `kiwi_mcp/utils/parsers.py` - File parsing
- `kiwi_mcp/utils/file_search.py` - File searching

### Registries (REMOTE operations)

- `kiwi_mcp/api/directive_registry.py` - DirectiveRegistry
- `kiwi_mcp/api/script_registry.py` - ScriptRegistry
- `kiwi_mcp/api/knowledge_registry.py` - KnowledgeRegistry

## Path Resolution

### Project Space

- Directives: `{project_path}/.ai/directives/**/*.md`
- Scripts: `{project_path}/.ai/scripts/**/*.py`
- Knowledge: `{project_path}/.ai/knowledge/**/*.md`

### User Space

**Unified user space at `~/.ai` (configurable via `USER_SPACE` env var)**

- Directives: `~/.ai/directives/**/*.md`
- Scripts: `~/.ai/scripts/**/*.py`
- Knowledge: `~/.ai/knowledge/**/*.md`

**Environment Variable:**
Set `USER_SPACE` to customize the user space location:
```bash
export USER_SPACE="/home/leo/.ai"
```

Priority: Project > User > Registry

## Search Algorithm

1. Split query into terms
2. For each file in search paths:
   - Parse file
   - Calculate relevance score
   - Add to results if score > 0
3. Sort by score
4. Return top N results

## Error Handling

- Local operations: Return error dict if file not found
- Remote operations: Propagate Supabase errors
- Parse errors: Log warning and skip file

## Testing

Local operations should work WITHOUT Supabase:
- No SUPABASE_URL needed
- No SUPABASE_KEY needed
- No internet connection required

Only remote operations require Supabase configuration.
