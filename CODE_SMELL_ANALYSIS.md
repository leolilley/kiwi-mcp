# Code Smell Analysis: Path Finding & Categorization

## Executive Summary

Analysis of path-related code across kiwi-mcp reveals **7 critical code smells** that compromise integrity, performance, and maintainability. Most stem from path logic being scattered across files without a unified contract.

---

## Code Smells Identified

### 1. **DRY Violation: Duplicated Path Construction** 🔴 Critical

**Location:** 5+ files
- `kiwi_mcp/utils/paths.py` (lines 149-150, 152-153, 220-225)
- `kiwi_mcp/utils/parsers.py` (line 226, 307, 546)
- `kiwi_mcp/handlers/directive/handler.py` (line 352+)

**Pattern:**
```python
# Found in 5 different places:
if location == "project":
    expected_base = project_path / ".ai" / folder_name
else:
    expected_base = get_user_space() / folder_name
```

**Risk:** If `.ai/` path changes, need to update 5+ locations. Already happened once (evidence: inconsistent folder naming).

**Fix:** `ScopedPath` class (single source of truth).

---

### 2. **Glob Search Performance Anti-Pattern** 🔴 Critical

**Location:** `kiwi_mcp/utils/paths.py` lines 78-90, 108-117

**Current Implementation:**
```python
for category_dir in base_path.glob("*"):
    if category_dir.is_dir():
        file_path = category_dir / f"{item_id}{ext}"
        if file_path.exists():
            return file_path
```

**Issues:**
- 🚫 Only searches 1 level deep (won't find `api/auth/tool.py`)
- 🚫 Multiple redundant `exists()` checks
- 🚫 `glob("*")` returns ALL entries (files + dirs), filters after
- 🚫 No fallback to index for large structures

**Example Failure:**
```
.ai/tools/api/auth/jwt_verifier.py
                    ^ Only returns dirs 1 level deep
```

**Impact:** 
- Tools in nested categories (`api/auth/`+) aren't found
- Linear search = O(n) for each lookup
- Stat system calls scale with item count

**Fix:** Use indexed `.index.json` instead.

---

### 3. **Missing Path Validation on Load** 🔴 Critical

**Location:** All parsers, no validation enforcement

**Current:** Items parsed without verifying location matches declared category.

**Risk Scenario:**
```bash
# Attacker moves tool from project to user space
mv .ai/tools/admin/dangerous.py ~/.ai/tools/misc/

# When loaded:
tool = load_tool("dangerous")  # ✅ Found (glob search works)
# But category is now wrong! Originally "admin", now "misc"
```

**Current Code Path:**
1. `parse_script_metadata()` extracts `category_from_path` (line 307)
2. But NO validation that this matches actual file location
3. No integrity check on load

**Fix:** Embed scope + category in signature, validate on load.

---

### 4. **Split Responsibility: Parse ≠ Validate** 🟡 Medium

**Location:**
- Parsing: `kiwi_mcp/utils/parsers.py`
- Validation: `kiwi_mcp/utils/validators.py`
- No coordination between them

**Issue:**
```python
# parsers.py extracts category:
category_from_path = extract_category_path(file_path, "directive", location, project_path)

# validators.py validates separately:
def validate(self, file_path: Path, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    # No check that parsed_data["category"] == extracted_category
```

**Pattern Violation:** Single Responsibility Principle
- Category extracted in parse
- But validated separately (if at all)
- No feedback loop

**Fix:** Unify validation in single step.

---

### 5. **Lockfile Category Parameter Unused in freeze()** 🟡 Medium

**Location:** `kiwi_mcp/runtime/lockfile_store.py` lines 103-139

**Code:**
```python
def freeze(
    self,
    tool_id: str,
    version: str,
    category: str,  # ← Passed but NEVER used
    chain: List[Dict[str, Any]],
    registry_url: Optional[str] = None,
) -> Lockfile:
    # ...
    lockfile = self.manager.freeze(chain, registry_url)
    return lockfile  # ← category not embedded
```

**Issues:**
- Parameter accepted but unused (Dead Code)
- Category only matters in `save()`, not in `freeze()`
- No scope tracking in lockfile metadata
- Can't validate lockfile location when loaded

**Current Usage Pattern:**
```python
lockfile = store.freeze(tool_id, version, category, chain)
store.save(lockfile, category, scope="project")
```

Should be:
```python
lockfile = store.freeze(tool_id, version, category, chain, scope="project")
store.save(lockfile)  # ← category already in lockfile
```

**Fix:** Embed category + scope during `freeze()`, not `save()`.

---

### 6. **Scattered Resolver Logic** 🟡 Medium

**Location:**
- `kiwi_mcp/utils/resolvers.py` (DirectiveResolver, ToolResolver)
- `kiwi_mcp/utils/paths.py` (resolve_item_path)
- `kiwi_mcp/handlers/directive/handler.py` (custom resolution)

**Problem:** Multiple resolution strategies with no clear precedence.

**Resolvers Found:**
1. `DirectiveResolver.resolve()` - uses glob
2. `ToolResolver.resolve()` - uses glob
3. `resolve_item_path()` - different glob pattern
4. `DirectiveHandler._find_in_path()` - custom search

**Inconsistencies:**
```python
# resolvers.py - searches only top level
for file in base_path.glob(f"*/{self.item_id}.md"):

# paths.py - different pattern
for category_dir in base_path.glob("*"):
    if category_dir.is_dir():
        file_path = category_dir / f"{item_id}{ext}"
```

**Impact:** Behavior varies by which resolver is used.

**Fix:** Single `ScopedResolver` class with consistent precedence.

---

### 7. **No Index Structure for Fast Lookup** 🟡 Medium

**Location:** `kiwi_mcp/runtime/lockfile_store.py` (has index, others don't)

**Pattern:** Lockfile store has `.index.json` for metadata, but:
- Other stores (directives, tools, knowledge) don't
- Inconsistent approach across codebase
- Glob search is fallback, not primary lookup

**Current Architecture:**
```
lockfile_store:
  ✅ Has .index.json
  ✅ Uses it for lookups
  ✅ Tracks created_at, last_validated

directive/tool/knowledge stores:
  ❌ No index
  ❌ Fall back to glob
  ❌ No metadata tracking
```

**Fix:** Unified index structure for all item types.

---

## Severity Matrix

| Smell | Severity | Effort | Impact | Status |
|-------|----------|--------|--------|--------|
| DRY violation (path construction) | 🔴 | Low | High | TODO |
| Glob search pattern | 🔴 | Medium | High | TODO |
| Missing path validation | 🔴 | Medium | Critical | TODO |
| Parse ≠ Validate split | 🟡 | Medium | Medium | TODO |
| Lockfile freeze() unused param | 🟡 | Low | Medium | TODO |
| Scattered resolvers | 🟡 | High | Medium | TODO |
| Missing index structure | 🟡 | High | High | TODO |

---

## Recommended Refactoring Order

### Phase 1: Low-Risk Foundation (Week 1)
1. **Create `ScopedPath` class** - centralize path construction
2. **Embed category in lockfile metadata** - fix freeze() parameter
3. **Add unit tests** for path logic

### Phase 2: Validation (Week 2)
4. **Implement location validation** - check items are where they claim
5. **Unify parsers & validators** - single responsibility
6. **Add integrity checks** on load

### Phase 3: Performance (Week 3)
7. **Build `.index.json` for directives/tools/knowledge**
8. **Replace glob with index lookups**
9. **Consolidate resolvers** into single class

### Phase 4: Integration (Week 4)
10. **Update all handlers** to use new path system
11. **Migration script** for existing items
12. **Documentation** and examples

---

## Files Requiring Changes

| File | Changes | Priority |
|------|---------|----------|
| `utils/paths.py` | Add `ScopedPath` class, consolidate logic | P0 |
| `runtime/lockfile_store.py` | Embed category in freeze() | P1 |
| `utils/parsers.py` | Validate paths match metadata | P1 |
| `utils/validators.py` | Add location validation | P1 |
| `utils/resolvers.py` | Unified resolver using index | P2 |
| `handlers/directive/handler.py` | Use new resolver | P2 |
| `handlers/tool/handler.py` | Use new resolver | P2 |
| `handlers/knowledge/handler.py` | Use new resolver | P2 |

---

## Risk Assessment

### Without Fixes:
- ⚠️ Moved files go undetected (integrity issue)
- ⚠️ Nested categories not searchable (usability issue)
- ⚠️ Scattered path logic = future bugs (maintainability issue)
- ⚠️ Performance degrades with item count (scalability issue)

### With Fixes:
- ✅ Path integrity validated
- ✅ Index-based O(1) lookup
- ✅ Single source of truth
- ✅ Extensible for registry scope

---

## Validation Checklist

- [ ] All path construction uses `ScopedPath`
- [ ] Lockfile category embedded in metadata
- [ ] Location validation on every item load
- [ ] `.index.json` structure consistent across all types
- [ ] Resolvers consolidated into single class
- [ ] Tests for path integrity
- [ ] Tests for nested category lookup
- [ ] Tests for scope precedence (project > user > registry)
