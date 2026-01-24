# Task: Language-Aware Signature Format

## Problem Statement

The `MetadataManager` currently hardcodes Python `#` comment syntax for validation signatures:

```python
# kiwi-mcp:validated:2026-01-24T02:53:50Z:accaa6ffdcdf
```

This breaks JavaScript files:
```javascript
#!/usr/bin/env node
# kiwi-mcp:validated:2026-01-24T02:53:50Z:accaa6ffdcdf  // ← SYNTAX ERROR
/**
 * Hello Node Test Tool
 */
```

**Each file type needs its own comment syntax:**
- Python: `# kiwi-mcp:validated:...`
- JavaScript: `// kiwi-mcp:validated:...`
- YAML: `# kiwi-mcp:validated:...` (same as Python)

## Current Implementation

**File: `kiwi_mcp/utils/metadata_manager.py`**

```python
class MetadataSignatureManager:
    def format_signature(self, timestamp: str, hash: str) -> str:
        """Format signature as Python comment."""
        return f"# kiwi-mcp:validated:{timestamp}:{hash}\n"
    
    def extract_signature(self, file_content: str) -> Optional[Dict[str, str]]:
        """Extract signature from Python comment (after optional shebang)."""
        sig_pattern = r"^(?:#!/[^\n]*\n)?# kiwi-mcp:validated:(.*?):([a-f0-9]{12})"
        sig_match = re.match(sig_pattern, file_content)
        # ...
    
    def remove_signature(self, content: str) -> str:
        """Remove signature Python comment from file."""
        content_without_sig = re.sub(r"^# kiwi-mcp:validated:[^\n]+\n", "", content)
        # ...
```

**Issues:**
1. Hardcoded `#` comment prefix
2. Hardcoded regex pattern for extraction
3. No file-type awareness

## Proposed Solution

### Add Signature Format to Extractors

Each extractor defines how signatures work for its file type:

```python
# In extractor tools
SIGNATURE_FORMAT = {
    "prefix": "//",        # Comment syntax
    "after_shebang": True, # Place after shebang line if present
}
```

### Examples

**`python_extractor.py`**
```python
EXTENSIONS = [".py"]
PARSER = "python_ast"

SIGNATURE_FORMAT = {
    "prefix": "#",
    "after_shebang": True,
}

EXTRACTION_RULES = {
    # ... existing rules
}
```

**`javascript_extractor.py`**
```python
EXTENSIONS = [".js", ".mjs", ".cjs"]
PARSER = "text"

SIGNATURE_FORMAT = {
    "prefix": "//",
    "after_shebang": True,
}

EXTRACTION_RULES = {
    # ... existing rules
}
```

**`yaml_extractor.py`**
```python
EXTENSIONS = [".yaml", ".yml"]
PARSER = "yaml"

SIGNATURE_FORMAT = {
    "prefix": "#",
    "after_shebang": False,  # YAML doesn't use shebangs
}

EXTRACTION_RULES = {
    # ... existing rules
}
```

## Implementation

### 1. Update Bootstrap to Load Signature Format

**File: `kiwi_mcp/schemas/tool_schema.py`**

```python
class Bootstrap:
    @staticmethod
    def load_extractor(file_path: Path) -> Optional[Dict[str, Any]]:
        """Load extractor with EXTENSIONS, PARSER, SIGNATURE_FORMAT, and EXTRACTION_RULES."""
        try:
            content = file_path.read_text()
            tree = ast.parse(content)
            
            extensions = None
            parser = "text"
            signature_format = None  # ← New
            rules = None
            
            for node in tree.body:
                if isinstance(node, ast.Assign) and len(node.targets) == 1:
                    target = node.targets[0]
                    if isinstance(target, ast.Name):
                        if target.id == "EXTENSIONS":
                            try:
                                extensions = ast.literal_eval(node.value)
                            except (ValueError, TypeError):
                                pass
                        elif target.id == "PARSER":
                            try:
                                parser = ast.literal_eval(node.value)
                            except (ValueError, TypeError):
                                pass
                        elif target.id == "SIGNATURE_FORMAT":  # ← New
                            try:
                                signature_format = ast.literal_eval(node.value)
                            except (ValueError, TypeError):
                                pass
                        elif target.id == "EXTRACTION_RULES":
                            try:
                                rules = ast.literal_eval(node.value)
                            except (ValueError, TypeError):
                                pass
            
            if extensions and rules:
                return {
                    "extensions": extensions,
                    "parser": parser,
                    "signature_format": signature_format or {"prefix": "#", "after_shebang": True},  # ← Default
                    "rules": rules,
                    "path": file_path,
                }
            return None
            
        except Exception:
            return None
```

### 2. Create Signature Format Registry

**File: `kiwi_mcp/utils/signature_formats.py`** (NEW)

```python
"""Registry for language-specific signature formats."""

from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Global cache: extension -> signature format
_signature_formats: Optional[Dict[str, Dict[str, Any]]] = None


def get_signature_format(file_path: Path, project_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Get signature format for a file based on its extension.
    
    Args:
        file_path: Path to the file
        project_path: Optional project path for extractor discovery
        
    Returns:
        Signature format dict with 'prefix' and 'after_shebang'
    """
    global _signature_formats
    
    # Load formats if not cached
    if _signature_formats is None:
        _signature_formats = _load_signature_formats(project_path)
    
    ext = file_path.suffix.lower()
    format_config = _signature_formats.get(ext)
    
    if format_config:
        return format_config
    
    # Default to Python-style
    logger.warning(f"No signature format found for '{ext}', using default '#'")
    return {"prefix": "#", "after_shebang": True}


def _load_signature_formats(project_path: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Load signature formats from all extractors."""
    from kiwi_mcp.schemas.tool_schema import Bootstrap
    from kiwi_mcp.utils.resolvers import get_user_space
    
    formats = {}
    
    search_paths = []
    if project_path:
        search_paths.append(project_path / ".ai" / "tools" / "extractors")
    search_paths.append(Path.cwd() / ".ai" / "tools" / "extractors")
    search_paths.append(get_user_space() / "tools" / "extractors")
    
    for extractors_dir in search_paths:
        if extractors_dir.exists():
            for file_path in extractors_dir.glob("*.py"):
                if file_path.name.startswith("_"):
                    continue
                
                extractor_data = Bootstrap.load_extractor(file_path)
                if extractor_data:
                    sig_format = extractor_data.get("signature_format", {"prefix": "#", "after_shebang": True})
                    for ext in extractor_data["extensions"]:
                        formats[ext.lower()] = sig_format
    
    return formats


def clear_signature_formats_cache():
    """Clear signature formats cache. Useful for testing."""
    global _signature_formats
    _signature_formats = None
```

### 3. Update MetadataManager to Use Format Registry

**File: `kiwi_mcp/utils/metadata_manager.py`**

```python
from kiwi_mcp.utils.signature_formats import get_signature_format

class MetadataSignatureManager:
    def __init__(self, item_type: str, project_path: Optional[Path] = None):
        self.item_type = item_type
        self.project_path = project_path
    
    def format_signature(self, timestamp: str, hash: str, file_path: Path) -> str:
        """Format signature using file-type-specific comment syntax."""
        sig_format = get_signature_format(file_path, self.project_path)
        prefix = sig_format["prefix"]
        return f"{prefix} kiwi-mcp:validated:{timestamp}:{hash}\n"
    
    def extract_signature(self, file_content: str, file_path: Path) -> Optional[Dict[str, str]]:
        """Extract signature using file-type-specific pattern."""
        sig_format = get_signature_format(file_path, self.project_path)
        prefix = re.escape(sig_format["prefix"])
        
        if sig_format.get("after_shebang", True):
            # Pattern: optional shebang, then signature
            sig_pattern = rf"^(?:#!/[^\n]*\n)?{prefix} kiwi-mcp:validated:(.*?):([a-f0-9]{{12}})"
        else:
            # Pattern: signature at start (no shebang expected)
            sig_pattern = rf"^{prefix} kiwi-mcp:validated:(.*?):([a-f0-9]{{12}})"
        
        sig_match = re.match(sig_pattern, file_content)
        if not sig_match:
            return None
        
        return {
            "timestamp": sig_match.group(1),
            "hash": sig_match.group(2),
            "status": "valid",
        }
    
    def remove_signature(self, content: str, file_path: Path) -> str:
        """Remove signature using file-type-specific pattern."""
        sig_format = get_signature_format(file_path, self.project_path)
        prefix = re.escape(sig_format["prefix"])
        
        # Remove shebang if present
        content_without_shebang = re.sub(r"^#!/[^\n]*\n", "", content)
        
        # Remove signature line
        sig_pattern = rf"^{prefix} kiwi-mcp:validated:[^\n]+\n"
        content_without_sig = re.sub(sig_pattern, "", content_without_shebang)
        
        # Restore shebang if it was there
        shebang_match = re.match(r"^(#!/[^\n]*\n)", content)
        if shebang_match:
            return shebang_match.group(1) + content_without_sig
        return content_without_sig
    
    def add_signature(self, content: str, file_path: Path) -> tuple[str, str]:
        """Add signature to content using file-type-specific format."""
        sig_format = get_signature_format(file_path, self.project_path)
        
        # Remove old signature first
        content_clean = self.remove_signature(content, file_path)
        
        # Compute hash
        content_hash = self.compute_hash(content_clean)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        # Format new signature
        signature_line = self.format_signature(timestamp, content_hash, file_path)
        
        # Insert signature after shebang if present and configured
        if sig_format.get("after_shebang", True):
            shebang_match = re.match(r"^(#!/[^\n]*\n)", content_clean)
            if shebang_match:
                return (
                    shebang_match.group(1) + signature_line + content_clean[len(shebang_match.group(1)):],
                    content_hash
                )
        
        # Otherwise insert at start
        return (signature_line + content_clean, content_hash)
```

### 4. Update All MetadataManager Call Sites

Wherever `MetadataSignatureManager` is instantiated, pass the `project_path` and `file_path`:

```python
# Before
manager = MetadataSignatureManager("tool")
signed_content, hash = manager.add_signature(content)

# After
manager = MetadataSignatureManager("tool", project_path=self.project_path)
signed_content, hash = manager.add_signature(content, file_path=file_path)
```

### 5. Update Extractors with SIGNATURE_FORMAT

**`python_extractor.py`:**
```python
SIGNATURE_FORMAT = {
    "prefix": "#",
    "after_shebang": True,
}
```

**`javascript_extractor.py`:**
```python
SIGNATURE_FORMAT = {
    "prefix": "//",
    "after_shebang": True,
}
```

**`yaml_extractor.py`:**
```python
SIGNATURE_FORMAT = {
    "prefix": "#",
    "after_shebang": False,
}
```

## Testing

```bash
cd /home/leo/projects/kiwi-mcp
source .venv/bin/activate

# Test signature formats load
python -c "
from kiwi_mcp.utils.signature_formats import get_signature_format
from pathlib import Path

py_fmt = get_signature_format(Path('test.py'))
print(f'Python: {py_fmt}')
assert py_fmt['prefix'] == '#'

js_fmt = get_signature_format(Path('test.js'))
print(f'JavaScript: {js_fmt}')
assert js_fmt['prefix'] == '//'

yaml_fmt = get_signature_format(Path('test.yaml'))
print(f'YAML: {yaml_fmt}')
assert yaml_fmt['prefix'] == '#'

print('✓ Signature formats loaded correctly')
"

# Test signature addition to JS file
python -c "
from kiwi_mcp.utils.metadata_manager import MetadataSignatureManager
from pathlib import Path

manager = MetadataSignatureManager('tool', Path('.'))
js_content = '''#!/usr/bin/env node
console.log('hello');
'''

signed, hash = manager.add_signature(js_content, Path('test.js'))
print('Signed JS content:')
print(signed)
assert '// kiwi-mcp:validated:' in signed
assert '# kiwi-mcp:validated:' not in signed
print('✓ JS signature uses // prefix')
"

# Test hello_node execution
# (Restart MCP server first)
# execute(item_type='tool', action='update', item_id='hello_node', ...)
# execute(item_type='tool', action='run', item_id='hello_node', parameters={'name': 'Kiwi', 'excited': true})
```

## Expected Outcome

**Python file:**
```python
#!/usr/bin/env python3
# kiwi-mcp:validated:2026-01-24T03:00:00Z:abc123def456
"""My tool"""
```

**JavaScript file:**
```javascript
#!/usr/bin/env node
// kiwi-mcp:validated:2026-01-24T03:00:00Z:abc123def456
/**
 * My tool
 */
```

**YAML file:**
```yaml
# kiwi-mcp:validated:2026-01-24T03:00:00Z:abc123def456
tool_id: my_tool
version: 1.0.0
```

## Files to Create/Modify

1. **CREATE** `kiwi_mcp/utils/signature_formats.py` (~80 lines)
2. **MODIFY** `kiwi_mcp/schemas/tool_schema.py` (add signature_format to Bootstrap)
3. **MODIFY** `kiwi_mcp/utils/metadata_manager.py` (use signature_formats registry)
4. **MODIFY** `.ai/tools/extractors/python_extractor.py` (add SIGNATURE_FORMAT)
5. **MODIFY** `.ai/tools/extractors/javascript_extractor.py` (add SIGNATURE_FORMAT)
6. **MODIFY** `.ai/tools/extractors/yaml_extractor.py` (add SIGNATURE_FORMAT)
7. **FIND & UPDATE** All call sites of MetadataSignatureManager (pass file_path)

## Success Criteria

✅ JavaScript files get `//` prefix signatures  
✅ Python files get `#` prefix signatures  
✅ YAML files get `#` prefix signatures  
✅ hello_node.js runs without syntax errors  
✅ Signature validation works for all file types
