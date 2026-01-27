# Path Structure & Categorization System

## Overview

**The Problem We're Solving:**
Currently, `category` is extracted from file path during parsing but isn't anchored during signing. This creates an integrity gap: a lockfile (or any signed artifact) can be moved to the wrong folder location, and validation won't catch it.

**The Solution:**
Items (directives, tools, knowledge, lockfiles) should embed their expected location (category path + scope) during signing. Validation must verify the item exists at its declared location.

---

## Storage Hierarchy

### Scope Levels (lowest to highest precedence)

1. **Registry** (Remote - Supabase)
   - Global shared items
   - Distributed via HTTP/API
   
2. **User Space** (`~/.ai/` or `$USER_SPACE/.ai/`)
   - User-owned, locally-installed items
   - Precedence: User < Project
   
3. **Project Space** (`.ai/` in project root)
   - Project-scoped, checked into Git
   - Precedence: Project > User (overrides user items)

### Type Directories

Each scope contains type-specific directories:

```
.ai/
├── directives/
│   └── {category}/{subcategory}/.../my_directive.md
├── tools/
│   └── {category}/{subcategory}/.../my_tool.py
├── knowledge/
│   └── {category}/{subcategory}/.../my_knowledge.md
├── lockfiles/
│   └── {category}/tool_name@version.lock.json
└── .index.json
```

### Category Path Structure

Items are organized in **hierarchical categories**, expressed as slash-separated paths:

```
Examples:
  .ai/directives/core/workflow.md
    → category_path: "core"
  
  .ai/tools/api/auth/jwt_verifier.py
    → category_path: "api/auth"
  
  .ai/knowledge/patterns/security/authentication.md
    → category_path: "patterns/security"
  
  .ai/lockfiles/data/scraper@1.2.0.lock.json
    → category_path: "data"
```

**Format Rules:**
- `/` separates levels
- Always relative to the type directory (directives/, tools/, etc.)
- Empty string `""` = directly in type directory (no subcategories)

---

## Current Path Finding Implementation

### Files Involved

- **`kiwi_mcp/utils/paths.py`** - Core path utilities
  - `resolve_item_path()` - Find items by ID
  - `extract_category_path()` - Extract category from file path
  - `validate_path_structure()` - Validate path compliance
  
- **`kiwi_mcp/utils/parsers.py`** - Parsing with path extraction
  - `parse_directive_file()` - Line 226: extracts category
  - `parse_script_metadata()` - Line 307: extracts category  
  - `parse_knowledge_entry()` - Line 546: extracts category

- **`kiwi_mcp/utils/resolvers.py`** - Resolution with precedence
  - `DirectiveResolver.resolve()` - Project > User lookup
  - `ToolResolver.resolve()` - Project > User lookup

### Current Issues (Code Smells)

#### 1. **No Validation of Path Integrity**
   - Category extracted but not verified at validation time
   - Moving a file to wrong folder goes undetected
   - **Impact**: File integrity can't be trusted

#### 2. **Path Extraction Happens at Parse Time**
   - Category extracted during `parse_directive_file()` etc.
   - But validation happens separately (no guarantee they match)
   - **Pattern**: Parsing ≠ Validation (violation of SRP)

#### 3. **Resolver Search is Unstructured**
   - `resolve_item_path()` searches via glob + iter
   - Inefficient for deep hierarchies
   - **Pattern**: Linear search instead of indexed lookup

```python
# From paths.py line 108-112
for category_dir in base_path.glob("*"):
    if category_dir.is_dir():
        file_path = category_dir / f"{item_id}{ext}"
        if file_path.exists():
            return file_path
```
   **Issues**:
   - Only searches 1 level deep (won't find `api/auth/jwt.py`)
   - `glob("*")` returns all entries (no index)
   - Repeated `exists()` checks = multiple FS calls

#### 4. **Missing Lock Files Path Anchoring**
   - `lockfile_store.py` uses `category` in `save()` (line 144)
   - But `freeze()` doesn't store it (line 103-139)
   - **Impact**: Lockfile category isn't embedded, can't validate after load

#### 5. **Inconsistent Parent Path Resolution**
   - Multiple places compute "expected base"
   - Logic duplicated in `extract_category_path()`, `validate_path_structure()`, parsers
   - **Pattern**: DRY violation

```python
# Duplicated in multiple places:
if location == "project":
    expected_base = project_path / ".ai" / folder_name
else:
    expected_base = get_user_space() / folder_name
```

#### 6. **No Scope Metadata in Items**
   - Items know their category but not their scope ("project" or "user")
   - Can't verify they're in the right scope when loaded
   - **Example**: Lockfile from user space can't be distinguished from project space

---

## Proposed Changes

### 1. **Embed Scope & Category During Signing**

Every signable item should include:
```python
@dataclass
class ItemMetadata:
    item_id: str
    item_type: str  # directive, tool, knowledge, lockfile
    version: str
    category: str   # "core/api" or ""
    scope: Literal["project", "user", "registry"]  # Where it lives
    parent_path: Path  # .ai/ folder path it anchors to
    integrity_hash: str  # Content hash
    signature: str
```

### 2. **Validation Must Check Location**

When loading/validating:
```python
def validate_location(item: SignedItem, actual_path: Path) -> bool:
    """Verify item is at its declared location."""
    expected_path = item.parent_path / item.category / f"{item.item_id}{ext}"
    if actual_path.resolve() != expected_path.resolve():
        raise IntegrityError(
            f"Item {item.item_id} at wrong location.\n"
            f"  Expected: {expected_path}\n"
            f"  Found: {actual_path}"
        )
```

### 3. **Consolidate Parent Path Resolution**

Single source of truth for path construction:
```python
class ScopedPath:
    """Represents an item's location within the hierarchy."""
    
    def __init__(self, scope: Literal["project", "user", "registry"], 
                 project_path: Optional[Path] = None):
        self.scope = scope
        self.project_path = project_path
    
    @property
    def parent(self) -> Path:
        """Get parent .ai/ folder for this scope."""
        if self.scope == "project":
            return self.project_path / ".ai"
        elif self.scope == "user":
            return get_user_space()
        elif self.scope == "registry":
            return Path("registry://")  # Virtual path
    
    def item_base(self, item_type: str) -> Path:
        """Get base directory for item type."""
        folder = {"directive": "directives", "tool": "tools", 
                  "knowledge": "knowledge", "lockfile": "lockfiles"}[item_type]
        return self.parent / folder
    
    def resolve(self, item_id: str, category: str, item_type: str, 
                ext: str = ".md") -> Path:
        """Resolve full path for an item."""
        base = self.item_base(item_type)
        if category:
            return base / category / f"{item_id}{ext}"
        return base / f"{item_id}{ext}"
```

### 4. **Indexed Lookup Instead of Glob Search**

Use `.index.json` for fast lookups:
```python
# .index.json structure
{
  "version": "1",
  "items": {
    "directive:core": {
      "path": "directives/core/workflow.md",
      "category": "core",
      "item_id": "workflow",
      "scope": "project"
    }
  }
}
```

### 5. **Lockfile Storage Integration**

Update `lockfile_store.py`:
```python
def freeze(
    self,
    tool_id: str,
    version: str,
    category: str,
    chain: List[Dict[str, Any]],
    scope: Literal["project", "user"] = "project",
    registry_url: Optional[str] = None,
) -> Lockfile:
    """Create lockfile with scope & category."""
    lockfile = self.manager.freeze(chain, registry_url)
    
    # Embed location metadata
    lockfile.metadata = {
        "tool_id": tool_id,
        "version": version,
        "category": category,
        "scope": scope,
        "parent_path": str(
            self.project_lockfiles if scope == "project" 
            else self.user_lockfiles
        )
    }
    
    return lockfile
```

---

## Testing Strategy

### Path Validation Tests

```python
def test_item_at_wrong_location():
    """Verify validation fails if item moved to wrong folder."""
    item = load_signed_item("project", "directives/core/my_dir.md")
    
    # Move file to user space
    user_copy = Path.home() / ".ai/directives/wrong/my_dir.md"
    
    # Validation should fail
    with pytest.raises(IntegrityError):
        validate_item_location(item, user_copy)

def test_category_in_metadata():
    """Verify category embedded in signature."""
    signed = sign_item(item, category="core/api")
    
    assert signed.metadata["category"] == "core/api"
    assert signed.metadata["scope"] == "project"

def test_scoped_path_resolution():
    """Verify ScopedPath generates correct paths."""
    project_scope = ScopedPath("project", Path("/myproject"))
    
    path = project_scope.resolve("my_directive", "core/api", "directive")
    assert path == Path("/myproject/.ai/directives/core/api/my_directive.md")
```

---

## Backward Compatibility

1. Items without embedded location metadata can still load
2. But they won't be validated for location integrity
3. Warn users when loading unverified items
4. Migration: Re-sign items with location metadata

---

## Registry Considerations

**Virtual Scopes for Registry:**
- Registry items use `scope: "registry"`
- Parent path = virtual registry URL or registry-specific marker
- Downloaded items become `scope: "project"` or `scope: "user"`
- Category preserved from registry metadata

---

## Summary

**Key Changes:**
1. ✅ Embed `category` + `scope` in signatures
2. ✅ Validate location during load
3. ✅ Consolidate path construction in `ScopedPath` class
4. ✅ Use indexed `.index.json` instead of glob search
5. ✅ Integrate lockfile storage with category anchoring

**Benefits:**
- 🔒 Integrity: Items can't be moved undetected
- 🚀 Performance: Index-based lookups vs. glob searches
- 📐 Consistency: Single source of truth for path logic
- 🔄 Precedence: Clear project > user > registry ordering
