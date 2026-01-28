# Path Finding Quality Analysis

**Date:** 2026-01-28  
**Status:** 🟡 MODERATE - Multiple paths, inconsistent resolution, gaps in error handling

---

## Executive Summary

Path finding across the kernel has **THREE independent resolution systems** that work but show signs of duplication, inconsistency, and incomplete error handling:

| Aspect | Status | Score |
|--------|--------|-------|
| **Project > User Priority** | ✅ Consistent | 9/10 |
| **Recursive Search** | ✅ Implemented | 9/10 |
| **Extension Handling** | ⚠️ Scattered | 6/10 |
| **Error Logging** | ❌ Sparse | 3/10 |
| **Deduplication** | ❌ Missing | 2/10 |
| **Test Coverage** | ⚠️ Partial | 5/10 |
| **Documentation** | ❌ Missing | 1/10 |

**Overall Quality: 5.3/10** (Functional but needs consolidation)

---

## Current Architecture

### Layer 1: Resolver Classes (utils/resolvers.py)
**File:** [kiwi_mcp/utils/resolvers.py](file:///home/leo/projects/kiwi-mcp/kiwi_mcp/utils/resolvers.py)  
**Lines:** 114 (3 classes)

```python
DirectiveResolver.resolve(name)    → Path | None
ToolResolver.resolve(name)         → Path | None
KnowledgeResolver.resolve(name)    → Path | None
```

**Characteristics:**
- ✅ Clean, focused classes
- ✅ Consistent project > user priority
- ✅ Recursive `rglob()` for all types
- ✅ Extension-aware (ToolResolver)
- ❌ Silent returns (no error context)
- ❌ Returns first match only (ambiguity ignored)
- ❌ No logging

**Pattern (all 3 resolvers):**
```python
def resolve(self, item_name: str) -> Optional[Path]:
    # Check project
    if self.project_path.exists():
        for file in self.project_path.rglob(f"{item_name}{ext}"):
            return file  # ⚠️ First match wins, no disambiguation
    
    # Check user
    if self.user_space.exists():
        for file in self.user_space.rglob(f"{item_name}{ext}"):
            return file  # ⚠️ Silent if not found
    
    return None
```

---

### Layer 2: Direct Handler Resolution

#### DirectiveHandler._find_in_path()
**File:** [kiwi_mcp/handlers/directive/handler.py:948](file:///home/leo/projects/kiwi-mcp/kiwi_mcp/handlers/directive/handler.py#L948-L960)  
**Lines:** 13

```python
def _find_in_path(self, directive_name: str, base_path: Path) -> Optional[Path]:
    # Exact match: rglob(f"{directive_name}.md")
    # Fallback: rglob("*.md") with stem check
```

**Issues:**
- ❌ **Duplicate logic** of DirectiveResolver
- ⚠️ Wildcard fallback is broader than resolver
- ✅ Used by load() to search explicit locations

---

#### DirectiveHandler._sign_directive()
**File:** [kiwi_mcp/handlers/directive/handler.py:964-1025](file:///home/leo/projects/kiwi-mcp/kiwi_mcp/handlers/directive/handler.py#L964-L1025)

**Flow:**
```
1. resolver.resolve(directive_name)
   ↓ If found → Validate & Sign
   ↓ If NOT found → Manual search fallback
2. Manual search by location:
   - Location="project" → rglob in project_directives with wildcard
   - Location="user"    → rglob in user_directives with wildcard
3. If STILL not found → Error with helpful hint
```

**Issues:**
- ❌ **Bypasses resolver on fallback** (lines 984-998)
- ❌ **Wildcard patterns** (`*{directive_name}.md`) broader than resolver
- ✅ Location-aware fallback is useful
- ⚠️ Stem check (`candidate.stem == directive_name`) handles ambiguity

---

#### ToolHandler._sign_tool()
**File:** [kiwi_mcp/handlers/tool/handler.py:440-500](file:///home/leo/projects/kiwi-mcp/kiwi_mcp/handlers/tool/handler.py#L440-L500)

**Similar pattern to directives:**
- ❌ Calls resolver, then manual fallback
- ❌ Fallback uses different search pattern than resolver
- ✅ Supports all tool extensions
- ✅ Correct location-aware search

---

### Layer 3: Path Utils (utils/paths.py)
**File:** [kiwi_mcp/utils/paths.py](file:///home/leo/projects/kiwi-mcp/kiwi_mcp/utils/paths.py)  
**Lines:** 243 (4 functions)

#### resolve_item_path()
**Lines:** 41-120

```python
resolve_item_path(item_id, item_type, source, project_path)
```

**Issues:**
- ❌ **Duplicate logic** of all three resolvers
- ✅ But also supports `resolve_item_path("*, source="local")` two-step search
- ✅ Multi-extension support for tools
- ✓ More discoverable via `utils.paths` module

#### validate_path_structure()
**Lines:** 167-243

```python
validate_path_structure(file_path, item_type, location, project_path)
    → {
        "valid": bool,
        "issues": List[str],
        "category_path": str,
        "expected_base": str,
        "actual_path": str
    }
```

**Quality:**
- ✅ Excellent error reporting
- ✅ Location-aware validation
- ✅ Used during signing (good)
- ✅ Comprehensive checks

---

## Issues Identified

### 🔴 Critical Issues

#### 1. **Three Independent Path Resolution Systems**
- `DirectiveResolver.resolve()` in resolvers.py
- `DirectiveHandler._find_in_path()` in directive handler
- `resolve_item_path()` in paths.py
- **Maintenance nightmare:** Bug fix in one won't fix others
- **Test burden:** Each needs independent tests

**Example:** If we decide to log resolved paths, we'd need to update 3+ places.

#### 2. **Inconsistent Fallback Strategies**
- **Resolver layer:** Returns None silently
- **Handler _sign layer:** Falls back to wildcard search with location filter
- **Behavior difference:** Same item_name might resolve differently in different code paths

**Code:**
```python
# resolvers.py - silent return
for file in self.project_directives.rglob(f"{name}.md"):
    return file
return None  # ⚠️ No logging, no context

# handlers/directive/handler.py - explicit fallback
if not file_path:
    for candidate in Path(path).rglob(f"*{name}.md"):  # Broader pattern!
        if candidate.stem == name:
            return candidate
```

#### 3. **Silent Failures in Resolver**
- `resolve()` returns `None` without context
- No way to know:
  - Was the directory searched not found?
  - Was the file not found?
  - What locations were checked?
- Forces handlers to re-search manually

#### 4. **No Disambiguation for Duplicate Names**
- If two files match the same name in different categories:
  ```
  .ai/directives/auth/login.md
  .ai/directives/core/login.md
  ```
- Resolver returns **first match only** (rglob order undefined)
- Silent ambiguity, no warning

---

### 🟡 Moderate Issues

#### 5. **Pattern Inconsistencies**
- `DirectiveResolver`: `rglob(f"{name}.md")`
- `_sign_directive()` fallback: `rglob(f"*{name}.md")`
- `_find_in_path()`: Both patterns
- **Means:** Different searches match different sets of files

#### 6. **Extension Handling Scattered**
- ToolResolver has extension logic
- ToolHandler._sign_tool also handles extensions
- resolve_item_path also handles extensions
- **3 separate implementations** of tool extension lookup

#### 7. **Location-Awareness Inconsistent**
- Resolvers have project/user paths but **no location parameter**
- Handlers add location awareness **on top**
- Result: Some code knows about location, some doesn't

---

### 🟢 Working Well

- ✅ Project > User priority consistent
- ✅ Recursive search works
- ✅ Most files get found (functional)
- ✅ validate_path_structure() is excellent
- ✅ Error messages are helpful (in handlers)

---

## Test Coverage

**Test files found:**
- `tests/handlers/test_directives.py` - Basic search/load tests
- `tests/primitives/test_chain_resolver*.py` - Chain resolution (not path finding)
- **Missing:**
  - ❌ resolve_item_path() tests
  - ❌ Duplicate name handling tests
  - ❌ Edge cases (missing dirs, empty dirs, symlinks)
  - ❌ Consistency tests (verify all layers find same file)
  - ❌ Error logging tests

**Coverage estimate:** ~40% of path finding logic

---

## Recommendations

### Phase 1: Consolidation (HIGH PRIORITY)

**Goal:** Single source of truth for path finding

**Steps:**
1. **Unify resolvers** into single resolution logic
   ```python
   # kiwi_mcp/utils/path_resolver.py
   class PathResolver:
       def resolve(
           self,
           item_id: str,
           item_type: str,
           location: Optional[str] = None,  # NEW: project/user/None=both
           project_path: Optional[Path] = None
       ) -> tuple[Path | None, dict]:  # Returns (path, metadata)
           # Single implementation
           # Rich error/context metadata
   ```

2. **Replace all usages:**
   - DirectiveResolver → PathResolver
   - ToolResolver → PathResolver
   - KnowledgeResolver → PathResolver
   - resolve_item_path() → PathResolver wrapper
   - Handler._find_in_path() → PathResolver
   - Handler._sign_*() fallbacks → PathResolver

3. **Add location parameter to resolvers**
   ```python
   resolver.resolve("directive_name", location="project")  # Only project
   resolver.resolve("directive_name", location="user")     # Only user
   resolver.resolve("directive_name")                       # Both (project first)
   ```

### Phase 2: Error Context (MEDIUM PRIORITY)

**Add metadata to resolution:**
```python
result = resolver.resolve(item_id, item_type)
# Returns:
{
    "path": Path,
    "found": bool,
    "searched_locations": ["project", "user"],
    "candidates": [Path, Path],  # If multiple matches
    "ambiguous": bool,
    "warnings": ["Duplicate 'login.md' found in auth/ and core/"]
}
```

### Phase 3: Logging (MEDIUM PRIORITY)

**Add context logging:**
```python
logger.debug(f"Resolving directive '{name}'")
logger.debug(f"  Checking project: {project_dir}")
logger.debug(f"  Found: {matches}")
logger.debug(f"  Returning: {path}")
```

### Phase 4: Tests (HIGH PRIORITY)

**Add comprehensive tests:**
```
tests/utils/
├── test_path_resolver.py          (core resolution)
├── test_path_resolver_edge_cases.py (duplicates, missing dirs, etc.)
└── test_path_validation.py         (location validation)
```

---

## Code Locations Summary

| Component | File | Lines | Quality |
|-----------|------|-------|---------|
| **Resolvers** | `utils/resolvers.py` | 114 | ⚠️ Duped |
| **Path Utils** | `utils/paths.py` | 243 | ⚠️ Duped |
| **Directive Resolution** | `handlers/directive/handler.py` | 948-1025 | ⚠️ Duped |
| **Tool Resolution** | `handlers/tool/handler.py` | 440-500 | ⚠️ Duped |
| **Knowledge Resolution** | `handlers/knowledge/handler.py` | Similar | ⚠️ Duped |
| **Path Validation** | `utils/paths.py:167-243` | 77 | ✅ Good |

---

## Immediate Action Items

1. **Document current behavior** (this file - ✅ DONE)
2. **Add logging to resolvers** (~30 mins)
3. **Create PathResolver consolidation** (~3 hours)
4. **Update all handlers to use PathResolver** (~2 hours)
5. **Add comprehensive tests** (~4 hours)
6. **Remove old resolver classes** (~1 hour)

**Total effort:** ~10 hours for full consolidation

---

## Decision: Single Unified Resolver

**Proposal:** Create `kiwi_mcp/utils/path_resolver.py` with:

```python
class PathResolver:
    """Unified path resolution for directives, tools, knowledge."""
    
    def resolve(
        self,
        item_id: str,
        item_type: str,  # "directive", "tool", "knowledge"
        location: Optional[str] = None,  # "project", "user", or None
        project_path: Optional[Path] = None
    ) -> tuple[Optional[Path], Dict[str, Any]]:
        """
        Resolve item path with comprehensive metadata.
        
        Returns:
            (path, metadata) where metadata includes:
            - found: bool
            - searched_locations: List[str]
            - candidates: List[Path] (if multiple matches)
            - ambiguous: bool
            - warnings: List[str]
        """
```

This would:
- ✅ Eliminate duplication
- ✅ Ensure consistency
- ✅ Enable rich error context
- ✅ Support all current use cases
- ✅ Make testing easier
