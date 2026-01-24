# Task: Implement Local Chain Resolution for Tools

## Problem Statement

**Currently, executing any tool requires registry database access**, even for local development. This is a critical blocker because:

### Current Flow
```
execute(hello_node) 
  → ToolHandler._execute_tool()
  → PrimitiveExecutor.execute()
  → ChainResolver.resolve(hello_node)
  → ToolRegistry.resolve_chain(hello_node)
  → RPC call to Supabase: "resolve_executor_chain"
  → Returns: [] (not in registry)
  → Error: "Tool 'hello_node' not found or has no executor chain"
```

### Issues
1. **Can't test locally** - Every tool must be published to registry before testing
2. **No offline development** - Requires network/database for every execution
3. **Broken developer workflow** - Create → Validate → **Publish** → Test (publish step shouldn't be required)
4. **JS/YAML tools unusable** - Just added support but can't execute them locally

## Current Architecture

### Chain Resolution (Registry-Only)

**File: `kiwi_mcp/api/tool_registry.py`**
```python
async def resolve_chain(self, tool_id: str) -> List[Dict[str, Any]]:
    """Resolve executor chain for a tool."""
    if not self.is_configured:
        return []
    
    try:
        result = self.client.rpc(
            "resolve_executor_chain", {"p_tool_id": tool_id}
        ).execute()
        
        return result.data or []
    except Exception as e:
        print(f"Error resolving chain: {e}")
        return []
```

**File: `kiwi_mcp/primitives/executor.py`**
```python
class ChainResolver:
    def __init__(self, registry):
        self.registry = registry  # ← ONLY uses registry
        
    async def resolve(self, tool_id: str) -> List[Dict]:
        """Resolve chain from database or cache."""
        if tool_id in self._chain_cache:
            return self._chain_cache[tool_id]
        
        chain = await self.registry.resolve_chain(tool_id)  # ← Always hits DB
        self._chain_cache[tool_id] = chain
        return chain
```

### Example Chain Structure

For `hello_node.js`:
```json
[
  {
    "tool_id": "hello_node",
    "tool_type": "javascript",
    "executor_id": "node_runtime",
    "manifest": { "name": "hello_node", "version": "1.0.0", ... }
  },
  {
    "tool_id": "node_runtime", 
    "tool_type": "runtime",
    "executor_id": "subprocess",
    "manifest": { "name": "node_runtime", "version": "1.0.0", ... }
  },
  {
    "tool_id": "subprocess",
    "tool_type": "primitive",
    "executor_id": null,
    "manifest": { "name": "subprocess", "version": "1.0.0", ... }
  }
]
```

## Proposed Solution

### Local Chain Resolver

Create `kiwi_mcp/primitives/local_chain_resolver.py` that:
1. Walks the `executor_id` chain using local file resolution
2. Extracts metadata from each file using `SchemaExtractor`
3. Builds the same chain structure as registry
4. Falls back to registry if tool not found locally

### Hybrid ChainResolver

Update `ChainResolver` to try local first, then registry:

```python
class ChainResolver:
    def __init__(self, registry, project_path: Optional[Path] = None):
        self.registry = registry
        self.project_path = project_path
        self.local_resolver = LocalChainResolver(project_path) if project_path else None
        
    async def resolve(self, tool_id: str) -> List[Dict]:
        """Resolve chain from local files, then registry, then cache."""
        if tool_id in self._chain_cache:
            return self._chain_cache[tool_id]
        
        # Try local first
        if self.local_resolver:
            chain = await self.local_resolver.resolve_chain(tool_id)
            if chain:
                self._chain_cache[tool_id] = chain
                return chain
        
        # Fallback to registry
        chain = await self.registry.resolve_chain(tool_id)
        self._chain_cache[tool_id] = chain
        return chain
```

## Implementation

### 1. Create `kiwi_mcp/primitives/local_chain_resolver.py`

```python
"""Local filesystem chain resolution without registry."""

from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from kiwi_mcp.utils.resolvers import ToolResolver
from kiwi_mcp.schemas import extract_tool_metadata

logger = logging.getLogger(__name__)


class LocalChainResolver:
    """Resolve executor chains from local filesystem."""
    
    def __init__(self, project_path: Path):
        self.project_path = project_path
        self.resolver = ToolResolver(project_path)
    
    async def resolve_chain(self, tool_id: str) -> List[Dict[str, Any]]:
        """
        Resolve full executor chain by walking local files.
        
        Args:
            tool_id: Starting tool ID
            
        Returns:
            Chain from leaf to primitive (same structure as registry)
        """
        chain = []
        visited = set()
        current_id = tool_id
        
        while current_id:
            # Prevent infinite loops
            if current_id in visited:
                logger.warning(f"Circular dependency detected: {current_id}")
                break
            visited.add(current_id)
            
            # Resolve file path
            file_path = self.resolver.resolve(current_id)
            if not file_path:
                logger.debug(f"Tool '{current_id}' not found locally")
                break
            
            # Extract metadata
            try:
                metadata = extract_tool_metadata(file_path, self.project_path)
            except Exception as e:
                logger.warning(f"Failed to extract metadata for {current_id}: {e}")
                break
            
            # Build chain link
            chain_link = {
                "tool_id": current_id,
                "tool_type": metadata.get("tool_type"),
                "executor_id": metadata.get("executor_id"),
                "manifest": {
                    "name": metadata.get("name"),
                    "version": metadata.get("version"),
                    "description": metadata.get("description"),
                    "tool_type": metadata.get("tool_type"),
                    "executor_id": metadata.get("executor_id"),
                    "category": metadata.get("category"),
                    "config": metadata.get("config"),
                    "config_schema": metadata.get("config_schema"),
                    "mutates_state": metadata.get("mutates_state", False),
                },
                "file_path": str(file_path),  # Add local path for execution
            }
            
            chain.append(chain_link)
            
            # Move to next executor
            current_id = metadata.get("executor_id")
            
            # Stop at primitives (executor_id is None)
            if current_id is None:
                break
        
        return chain
    
    async def resolve_chains_batch(
        self, tool_ids: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Batch resolve multiple chains."""
        results = {}
        for tool_id in tool_ids:
            results[tool_id] = await self.resolve_chain(tool_id)
        return results
```

### 2. Update `kiwi_mcp/primitives/executor.py`

**Add local resolver support:**

```python
class ChainResolver:
    def __init__(self, registry, project_path: Optional[Path] = None):
        """
        Initialize with registry and optional project path for local resolution.
        
        Args:
            registry: ToolRegistry instance
            project_path: Optional path for local chain resolution
        """
        self.registry = registry
        self.project_path = project_path
        
        # Lazy-load local resolver
        self._local_resolver = None
        
        # Chain cache by tool_id
        self._chain_cache: Dict[str, List[Dict]] = {}
        
        # Verified integrity cache
        self._integrity_cache: Dict[str, float] = {}
        
        # Validation cache
        self._validation_cache: Dict[Tuple[str, str], Dict[str, Any]] = {}
    
    def _get_local_resolver(self):
        """Lazy-load local chain resolver."""
        if self._local_resolver is None and self.project_path:
            from .local_chain_resolver import LocalChainResolver
            self._local_resolver = LocalChainResolver(self.project_path)
        return self._local_resolver
    
    async def resolve(self, tool_id: str) -> List[Dict]:
        """Resolve chain from local files first, then database, then cache."""
        if tool_id in self._chain_cache:
            return self._chain_cache[tool_id]
        
        # Try local resolution first
        local_resolver = self._get_local_resolver()
        if local_resolver:
            chain = await local_resolver.resolve_chain(tool_id)
            if chain:
                self._chain_cache[tool_id] = chain
                return chain
        
        # Fallback to registry
        chain = await self.registry.resolve_chain(tool_id)
        self._chain_cache[tool_id] = chain
        return chain
```

**Update PrimitiveExecutor initialization:**

```python
class PrimitiveExecutor:
    def __init__(self, registry, project_path: Optional[Path] = None):
        """
        Initialize executor with registry and optional project path.
        
        Args:
            registry: ToolRegistry instance
            project_path: Optional project path for local resolution
        """
        self.registry = registry
        self.project_path = project_path
        self.resolver = ChainResolver(registry, project_path)  # ← Pass project_path
        
        # ... rest of initialization
```

### 3. Update `kiwi_mcp/handlers/tool/handler.py`

**Pass project_path to PrimitiveExecutor:**

```python
class ToolHandler:
    def __init__(self, project_path: str):
        """Initialize handler with project path."""
        self.project_path = Path(project_path)
        self.resolver = ToolResolver(project_path=self.project_path)
        self.registry = ToolRegistry()
        self.logger = get_logger("tool_handler")
        self.output_manager = OutputManager(project_path=self.project_path)
        
        # Initialize primitive executor WITH project_path
        self.primitive_executor = PrimitiveExecutor(
            self.registry, 
            project_path=self.project_path  # ← Add this
        )
```

## Testing

### Test 1: Local Chain Resolution

```bash
cd /home/leo/projects/kiwi-mcp
source .venv/bin/activate

python -c "
import asyncio
from pathlib import Path
from kiwi_mcp.primitives.local_chain_resolver import LocalChainResolver

async def test():
    resolver = LocalChainResolver(Path('.'))
    
    # Test hello_node chain
    chain = await resolver.resolve_chain('hello_node')
    print(f'Chain length: {len(chain)}')
    
    for i, link in enumerate(chain):
        print(f'{i+1}. {link[\"tool_id\"]} ({link[\"tool_type\"]}) → {link.get(\"executor_id\")}')
    
    assert len(chain) == 3
    assert chain[0]['tool_id'] == 'hello_node'
    assert chain[1]['tool_id'] == 'node_runtime'
    assert chain[2]['tool_id'] == 'subprocess'
    assert chain[2]['executor_id'] is None  # primitive
    
    print('✓ Local chain resolution works')

asyncio.run(test())
"
```

### Test 2: Execute Local Tool

```bash
# Via MCP (requires restart)
python -c "
import asyncio
from kiwi_mcp.handlers.tool.handler import ToolHandler

async def test():
    handler = ToolHandler('/home/leo/projects/kiwi-mcp')
    
    result = await handler.execute(
        tool_name='hello_node',
        params={'name': 'Kiwi', 'excited': True}
    )
    
    print(f'Status: {result[\"status\"]}')
    if result['status'] == 'success':
        print(f'Output: {result[\"data\"]}')
        print('✓ Local tool execution works')
    else:
        print(f'Error: {result.get(\"error\")}')

asyncio.run(test())
"
```

### Test 3: Registry Fallback

```bash
# Test tool that doesn't exist locally falls back to registry
python -c "
import asyncio
from pathlib import Path
from kiwi_mcp.primitives.executor import ChainResolver
from kiwi_mcp.api.tool_registry import ToolRegistry

async def test():
    registry = ToolRegistry()
    resolver = ChainResolver(registry, Path('.'))
    
    # hello_node should resolve locally
    local_chain = await resolver.resolve('hello_node')
    print(f'hello_node (local): {len(local_chain)} steps')
    
    # fake_tool should try registry
    registry_chain = await resolver.resolve('nonexistent_tool')
    print(f'nonexistent_tool (registry): {len(registry_chain)} steps')
    
    print('✓ Hybrid resolution works')

asyncio.run(test())
"
```

## Expected Outcome

✅ Local tools can be executed without publishing  
✅ Offline development works  
✅ Registry still used for published/shared tools  
✅ Developer workflow: Create → Validate → Test → (optionally) Publish  
✅ JS/YAML tools work locally  

## Files to Create/Modify

1. **CREATE** `kiwi_mcp/primitives/local_chain_resolver.py` (~150 lines)
2. **MODIFY** `kiwi_mcp/primitives/executor.py` (add project_path, local resolver)
3. **MODIFY** `kiwi_mcp/handlers/tool/handler.py` (pass project_path to executor)

## Migration Notes

- **Backward compatible** - if no project_path, falls back to registry-only
- **Cache still works** - local chains cached same as registry chains
- **No database changes** - purely client-side enhancement
- **Registry optional** - for published tools, still use registry; for local dev, use filesystem

## Success Criteria

Run hello_node.js locally without publishing:
```bash
# Via MCP
execute(
  item_type="tool",
  action="run", 
  item_id="hello_node",
  parameters={"name": "World", "excited": true},
  project_path="/home/leo/projects/kiwi-mcp"
)

# Expected output:
{
  "status": "success",
  "data": "Hello, World!!!",
  "metadata": {
    "duration_ms": 250,
    "tool_type": "javascript",
    "primitive_type": "subprocess"
  }
}
```
