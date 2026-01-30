# UniversalExecutor Documentation Fix Summary

**Date:** 2026-01-30
**Purpose:** Fixed incorrect code-driven patterns in UniversalExecutor documentation

---

## Problem Identified

The `UniversalExecutor` code in documentation was **NOT data-driven** - it had hardcoded executor IDs and pre-loaded registries:

### ❌ Before (Code-Driven - Incorrect)

```python
class UniversalExecutor:
    def __init__(self):
        self.primitives = {...}  # ❌ Hardcoded registry
        self.runtimes = {...}    # ❌ Hardcoded registry

    def execute(self, tool_path, parameters):
        executor_id = getattr(tool_module, "__executor_id__")

        if executor_id is None:
            return self._execute_primitive(tool_module, parameters)

        elif executor_id in ["subprocess", "http_client"]:  # ❌ Hardcoded!
            return self._execute_via_runtime(executor_id, ...)

        elif executor_id in ["python_runtime", "node_runtime"]:  # ❌ Hardcoded!
            return self._execute_via_runtime(executor_id, ...)
```

### ✅ After (Data-Driven - Correct)

```python
class UniversalExecutor:
    def __init__(self, ai_tools_path: Path, env_resolver: EnvResolver):
        self.ai_tools_path = ai_tools_path  # ✅ Filesystem path
        self.env_resolver = env_resolver
        # ✅ NO self.primitives or self.runtimes registries!

    def execute(self, tool_path: Path, parameters: dict) -> Any:
        """Recursive executor resolution (data-driven)"""
        metadata = self._load_metadata(tool_path)
        executor_id = metadata.get("__executor_id__")

        if executor_id is None:
            return self._execute_primitive(tool_path, parameters)

        # ✅ DATA-DRIVEN: Resolve executor path from filesystem
        executor_path = self._resolve_executor_path(executor_id)
        executor_metadata = self._load_metadata(executor_path)

        # ✅ Handle runtime environment resolution
        if executor_metadata.get("__tool_type__") == "runtime":
            resolved_env = self.env_resolver.resolve(
                executor_metadata.get("ENV_CONFIG")
            )
            parameters = {**parameters, **resolved_env}

        # ✅ RECURSIVE: Execute executor (runtime → runtime → ... → primitive)
        return self.execute(executor_path, parameters)

    def _resolve_executor_path(self, executor_id: str) -> Path:
        """Search .ai/tools/**/ for executor_id (data-driven)"""
        for category_dir in self.ai_tools_path.iterdir():
            for py_file in category_dir.rglob("*.py"):
                if py_file.stem == executor_id:
                    return py_file
        raise ValueError(f"Executor not found: {executor_id}")
```

---

## Files Updated

### 1. `docs/ARCHITECTURE.md` (lines 235-275)

**Changes:**
- Removed hardcoded `self.primitives` and `self.runtimes` registries
- Removed hardcoded `if/elif` blocks for `["subprocess", "http_client", "python_runtime", "node_runtime"]`
- Added `_resolve_executor_path()` method for filesystem-based executor resolution
- Added recursive execution pattern
- Added comments emphasizing **DATA-DRIVEN** approach

### 2. `docs/rye/universal-executor/routing.md`

**Changes:**
- Updated "Routing Logic" section with full data-driven implementation
- Updated all execution flow examples to show recursive resolution
- Updated code path examples to show:
  - `_resolve_executor_path()` calls
  - Recursive `execute()` calls
  - Dynamic import from `lilux.primitives`
- Updated "Common Routing Patterns" to show filesystem-based resolution
- Updated "Executor ID Reference" table to clarify data-driven nature

### 3. `docs/rye/universal-executor/overview.md`

**Changes:**
- Updated "Executor Resolution Order" section
  - Changed "known primitive ID" to "search filesystem"
  - Added recursive resolution steps
- Updated "Key Benefits" table
  - Added "No hardcoded executors" benefit
  - Added "Recursive resolution" benefit

### 4. `docs/IMPLEMENTATION_PLAN.md` (Phase 4.2)

**Changes:**
- Updated "Requirements" to emphasize **data-driven recursive resolution**
- Updated "Architecture Flow" to show:
  - `_resolve_executor_path()` filesystem search
  - Recursive `execute()` calls
  - Removed hardcoded executor ID lists
- Added "Key Data-Driven Methods" section with:
  - `_resolve_executor_path()` implementation
  - Updated `execute_tool()` method with recursion

---

## Key Differences: Before vs After

| Aspect | Before (Incorrect) | After (Correct) |
|--------|-------------------|----------------|
| Executor lookup | `self.primitives.get(id)` | `_resolve_executor_path(id)` |
| Runtime lookup | `self.runtimes.get(id)` | `_resolve_executor_path(id)` |
| Route to primitive | `elif id in ["subprocess", ...]` | Recursive `execute()` call |
| Add new executor | Modify executor code | Add `.py` file to `.ai/tools/` |
| Primitives location | `self.primitives` registry | `lilux.primitives.{name}` |
| Extensibility | Limited to hardcoded IDs | Unlimited (any file in `.ai/tools/`) |

---

## Data-Driven Architecture Principles

Now the documentation correctly emphasizes:

1. **✅ No hardcoded executor IDs** - All resolved from filesystem
2. **✅ No pre-loaded registries** - `self.primitives` and `self.runtimes` removed
3. **✅ Recursive executor chains** - `tool → runtime → runtime → ... → primitive`
4. **✅ Filesystem-based discovery** - `_resolve_executor_path()` searches `.ai/tools/**/`
5. **✅ Environment resolution at execution time** - `env_resolver.resolve()` called during execution
6. **✅ Dynamic primitive imports** - `importlib.import_module(f"lilux.primitives.{name}")`

---

## How to Add a New Runtime (Data-Driven Example)

### ✅ Correct Way (Data-Driven)

1. Create file: `.ai/tools/rye/runtimes/rust_runtime.py`
2. Add metadata:
   ```python
   __tool_type__ = "runtime"
   __executor_id__ = "subprocess"
   __category__ = "runtimes"
   ENV_CONFIG = {...}
   ```
3. **That's it!** Universal executor automatically discovers it

### ❌ Old Way (Code-Driven - Wrong)

1. Modify `UniversalExecutor.__init__()` to add to `self.runtimes`
2. Add `rust_runtime` to hardcoded `elif executor_id in [...]` list
3. Restart system

---

## Summary

All UniversalExecutor documentation now correctly reflects the **data-driven architecture**:

- ✅ No hardcoded executor IDs
- ✅ No pre-loaded registries
- ✅ Filesystem-based discovery
- ✅ Recursive executor resolution
- ✅ Easy extensibility (just add files to `.ai/tools/`)

The docs are now fully aligned with the data-driven strategy outlined in `ARCHITECTURE.md` and `COMPLETE_DATA_DRIVEN_ARCHITECTURE.md`.

---

**Status:** ✅ Complete
**Files Updated:** 4
**Lines Changed:** ~150+
**Date:** 2026-01-30
