# Telemetry Design (Centralized)

**Status:** Design Draft  
**Target:** v0.2.0  
**Author:** Leo  
**Date:** 2026-01-29

---

## Overview

Telemetry is stored centrally in `~/.ai/telemetry.yaml`, keyed by item ID. Items remain clean and unchanged after execution—no re-signing, no file churn.

**Key Principles:**

- **Centralized**: All stats in one file, not scattered across items
- **Clean items**: Directives/tools/knowledge stay unchanged after execution
- **No churn**: No git dirty state, no merge conflicts from telemetry
- **Privacy-safe**: Stats never accidentally committed to repos
- **Simple**: One schema, one write path, no per-format extractors
- **Optional export**: Bake stats into items explicitly before publish (if desired)

### What Changed from Embedded Design

| Aspect | Embedded (old) | Centralized (new) |
|--------|----------------|-------------------|
| Storage | In each item's frontmatter | `~/.ai/telemetry.yaml` |
| After execution | Item modified + re-signed | Item unchanged |
| Git impact | Constant dirty state | No impact |
| Implementation | Complex (3 formats) | Simple (1 YAML file) |
| Publish | Stats travel with item | Stats sent separately (or exported) |

---

## Architecture

```
User: "run directive X"
           │
           ▼
┌─────────────────────────────────────────┐
│ 1. Load & Execute Item                  │
│    • Parse directive/tool               │
│    • Run with tracked primitives        │
│    • Item file NOT modified             │
└─────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│ 2. Update Telemetry Store               │
│    • Increment counters in telemetry.yaml│
│    • Atomic write (temp + rename)       │
│    • 0600 permissions                   │
└─────────────────────────────────────────┘
```

---

## Telemetry Storage

### Location

```
~/.ai/telemetry.yaml  # Or $USER_PATH/telemetry.yaml
```

### Schema

```yaml
# ~/.ai/telemetry.yaml
# Auto-managed by Lilux MCP - do not edit manually

version: 1
updated: 2026-01-29T10:30:00Z

items:
  # Keyed by item_id (registry format) or content hash
  "core/create_tool":
    type: directive
    total_runs: 47
    success_count: 45
    failure_count: 2
    timeout_count: 0
    avg_duration_ms: 1250
    http_calls: 12
    subprocess_calls: 3
    last_run: 2026-01-29T10:30:00Z
    last_outcome: success
    last_error: null
    paths:
      - ~/.ai/directives/core/create_tool.md
      - /home/leo/project/.ai/directives/create_tool.md

  "leo/web_scraper@2.0.0":
    type: tool
    total_runs: 123
    success_count: 118
    failure_count: 5
    timeout_count: 0
    avg_duration_ms: 3400
    http_calls: 892
    subprocess_calls: 0
    last_run: 2026-01-28T14:22:00Z
    last_outcome: success
    last_error: null
    paths:
      - ~/.ai/tools/web_scraper.py

  "kb-api-youtube-proxy":
    type: knowledge
    access_count: 89
    last_accessed: 2026-01-29T09:15:00Z
    paths:
      - ~/.ai/knowledge/api-facts/youtube-proxy.md
```

### Key Strategy

Items are keyed by stable identifier:

1. **Registry ID** (preferred): `category/item_name@version` (e.g., `leo/my-tool@1.0.0`)
2. **Local ID**: `item_name` from frontmatter/metadata
3. **Content hash**: `sha256(content_without_telemetry)` as fallback

The `paths` array tracks where the item has been seen, for discovery and deduplication.

---

## Telemetry Tools & Directives

### Core Tools (Protected)

| Tool | Location | Purpose |
|------|----------|---------|
| `configure_telemetry` | `.ai/tools/core/configure_telemetry.py` | Toggle telemetry on/off |
| `clear_telemetry` | `.ai/tools/core/clear_telemetry.py` | Clear stats for item(s) |
| `export_telemetry` | `.ai/tools/core/export_telemetry.py` | Bake stats into item for publish |

### Core Directives (Shadowable)

| Directive | Purpose |
|-----------|---------|
| `telemetry_enable` | Enable telemetry tracking |
| `telemetry_disable` | Disable telemetry tracking |
| `telemetry_status` | Show current config + stats summary |
| `telemetry_clear` | Clear telemetry for item(s) |
| `telemetry_export` | Export stats to item before publish |

### Telemetry Configuration

Telemetry is configured in `~/.ai/config.yaml` (or `$USER_PATH/config.yaml`).

**Default: off** - telemetry disabled until user explicitly enables via `configure_telemetry` tool.

```yaml
# ~/.ai/config.yaml
telemetry:
  enabled: true
```

### Tool Calls

Enable telemetry:

```python
mcp__lilux__execute(
    item_type="tool",
    item_id="core/configure_telemetry",
    project_path="/home/leo/project",
    params={"enabled": True}
)
```

View telemetry for an item:

```python
mcp__lilux__execute(
    item_type="tool",
    item_id="core/telemetry_status",
    project_path="/home/leo/project",
    params={"item_id": "core/create_tool"}
)
```

Clear telemetry:

```python
mcp__lilux__execute(
    item_type="tool",
    item_id="core/clear_telemetry",
    project_path="/home/leo/project",
    params={"item_id": "core/create_tool"}  # or "*" for all
)
```

---

## Telemetry Fields

### Directives & Tools

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | "directive" or "tool" |
| `total_runs` | int | Total execution count |
| `success_count` | int | Successful executions |
| `failure_count` | int | Failed executions |
| `timeout_count` | int | Timed out executions |
| `avg_duration_ms` | float | Running average duration |
| `http_calls` | int | Total HTTP primitive calls |
| `subprocess_calls` | int | Total subprocess primitive calls |
| `last_run` | ISO datetime | Timestamp of last execution |
| `last_outcome` | string | success, failure, timeout, cancelled |
| `last_error` | string | Error message if last failed |
| `paths` | list | Known file paths for this item |

### Knowledge Items

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | "knowledge" |
| `access_count` | int | Times accessed/loaded |
| `last_accessed` | ISO datetime | Last access timestamp |
| `paths` | list | Known file paths for this item |

---

## Implementation

### Primitive Call Tracking

The harness tracks calls to the two base primitives during execution:

```python
# primitives/http_client.py
class TrackedHttpClient:
    """HTTP primitive with call tracking for telemetry."""
    
    def __init__(self, telemetry_context: TelemetryContext):
        self.ctx = telemetry_context
    
    async def request(self, method: str, url: str, **kwargs) -> Response:
        self.ctx.http_calls += 1
        return await httpx.AsyncClient().request(method, url, **kwargs)


# primitives/subprocess.py
class TrackedSubprocess:
    """Subprocess primitive with call tracking for telemetry."""
    
    def __init__(self, telemetry_context: TelemetryContext):
        self.ctx = telemetry_context
    
    async def run(self, cmd: list[str], **kwargs) -> CompletedProcess:
        self.ctx.subprocess_calls += 1
        return await asyncio.create_subprocess_exec(*cmd, **kwargs)
```

### Telemetry Context

```python
@dataclass
class TelemetryContext:
    """Tracks primitive calls during a single execution."""
    http_calls: int = 0
    subprocess_calls: int = 0
    
    def reset(self):
        self.http_calls = 0
        self.subprocess_calls = 0
```

### Harness Integration

```python
async def execute_item(item_path: Path, params: dict) -> ExecuteResult:
    # 1. Check if telemetry enabled
    config = load_config()
    telemetry_enabled = config.get("telemetry", {}).get("enabled", False)
    
    # 2. Create telemetry context for primitive tracking
    ctx = TelemetryContext()
    
    # 3. Inject tracked primitives
    primitives = {
        "http": TrackedHttpClient(ctx),
        "subprocess": TrackedSubprocess(ctx),
    }
    
    # 4. Execute (item file NOT modified)
    start = time.time()
    try:
        result = await run_item(item_path, params, primitives=primitives)
        outcome = "success"
        error = None
    except TimeoutError:
        outcome = "timeout"
        error = "Execution timed out"
        result = None
    except Exception as e:
        outcome = "failure"
        error = str(e)
        result = None
    finally:
        duration_ms = int((time.time() - start) * 1000)
    
    # 5. Update centralized telemetry store (if enabled)
    if telemetry_enabled:
        item_id = get_item_id(item_path)
        telemetry_store.record_execution(
            item_id=item_id,
            item_type=get_item_type(item_path),
            outcome=outcome,
            duration_ms=duration_ms,
            http_calls=ctx.http_calls,
            subprocess_calls=ctx.subprocess_calls,
            error=error,
            path=str(item_path),
        )
    
    return ExecuteResult(outcome=outcome, result=result, error=error)
```

### Telemetry Store

```python
import fcntl
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import yaml

class TelemetryStore:
    """Centralized telemetry storage with atomic writes.
    
    Usage:
        store = TelemetryStore()  # Uses ~/.ai/telemetry.yaml
        store.record_execution(
            item_id="core/create_tool",
            item_type="directive",
            outcome="success",  # or "failure" or "timeout"
            duration_ms=1250,
            http_calls=3,
            subprocess_calls=1,
            error=None,  # or error message string
            path="/home/leo/.ai/directives/core/create_tool.md",
        )
    """
    
    def __init__(self, path: Path | None = None):
        self.path = path or (get_user_path() / "telemetry.yaml")
    
    def record_execution(
        self,
        item_id: str,
        item_type: str,
        outcome: str,
        duration_ms: int,
        http_calls: int,
        subprocess_calls: int,
        error: str | None,
        path: str,
    ):
        """Record execution with file locking and atomic write.
        
        Args:
            item_id: Stable identifier (e.g., "core/create_tool" or "leo/scraper@1.0.0")
            item_type: "directive", "tool", or "knowledge"
            outcome: "success", "failure", or "timeout"
            duration_ms: Execution time in milliseconds
            http_calls: Number of HTTP requests made during execution
            subprocess_calls: Number of subprocess calls made during execution
            error: Error message if outcome is "failure" or "timeout", else None
            path: Absolute file path to the item
        """
        with self._lock():
            data = self._load()
            
            # Initialize item entry if first time seeing this item
            if item_id not in data["items"]:
                data["items"][item_id] = {
                    "type": item_type,
                    "total_runs": 0,
                    "success_count": 0,
                    "failure_count": 0,
                    "timeout_count": 0,
                    "avg_duration_ms": 0.0,
                    "http_calls": 0,
                    "subprocess_calls": 0,
                    "last_run": None,
                    "last_outcome": None,
                    "last_error": None,
                    "paths": [],
                }
            
            item = data["items"][item_id]
            
            # Update counters
            item["total_runs"] += 1
            item[f"{outcome}_count"] = item.get(f"{outcome}_count", 0) + 1
            item["http_calls"] += http_calls
            item["subprocess_calls"] += subprocess_calls
            
            # Running average for duration (Welford's algorithm)
            n = item["total_runs"]
            old_avg = item["avg_duration_ms"]
            item["avg_duration_ms"] = old_avg + (duration_ms - old_avg) / n
            
            # Last run info
            now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            item["last_run"] = now
            item["last_outcome"] = outcome
            item["last_error"] = error
            
            # Track paths (deduplicated)
            if path not in item["paths"]:
                item["paths"].append(path)
            
            data["updated"] = now
            
            self._save(data)
    
    def get(self, item_id: str) -> dict | None:
        """Get telemetry for a specific item. Returns None if not found."""
        data = self._load()
        return data["items"].get(item_id)
    
    def clear(self, item_id: str | None = None):
        """Clear telemetry. If item_id is None, clears all."""
        with self._lock():
            data = self._load()
            if item_id is None:
                data["items"] = {}
            elif item_id in data["items"]:
                del data["items"][item_id]
            data["updated"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            self._save(data)
    
    @contextmanager
    def _lock(self):
        """Advisory file lock for concurrent access.
        
        Uses fcntl.LOCK_EX for exclusive lock. Lock is released when
        context exits, and file handle is properly closed.
        """
        lock_path = self.path.with_suffix(".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_file = open(lock_path, "w")
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            yield lock_file
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()
    
    def _load(self) -> dict:
        """Load telemetry data from YAML file. Returns empty structure if missing."""
        if self.path.exists():
            content = self.path.read_text()
            if content.strip():
                return yaml.safe_load(content)
        return {"version": 1, "updated": None, "items": {}}
    
    def _save(self, data: dict):
        """Atomic write: write to temp file, then rename.
        
        This ensures readers never see partial writes.
        File permissions are set to 0600 (owner read/write only).
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(yaml.dump(data, sort_keys=False, default_flow_style=False))
        tmp.chmod(0o600)
        tmp.rename(self.path)
```

---

## Export for Publishing

When publishing to registry, you can optionally export telemetry stats:

### Option 1: Send Separately (Recommended)

Registry receives telemetry as a separate payload field, not embedded in item:

```python
async def publish_item(item_path: Path, registry_url: str):
    """Publish item with telemetry as separate field."""
    
    content = item_path.read_text()
    item_id = get_item_id(item_path)
    
    # Get telemetry from central store
    telemetry = telemetry_store.get(item_id)
    
    payload = {
        "content": content,  # Item unchanged
        "telemetry": {
            "total_runs": telemetry.get("total_runs", 0),
            "success_rate": calculate_success_rate(telemetry),
            "avg_duration_ms": telemetry.get("avg_duration_ms"),
        } if telemetry else None
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{registry_url}/api/items/publish",
            json=payload,
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        response.raise_for_status()
```

### Option 2: Bake Into Item (Explicit Export)

For portability, explicitly bake telemetry into item before publish:

```
User: "export telemetry to create_tool before publishing"
LLM: [calls export_telemetry tool]
     "Telemetry exported. Item re-signed."

User: "publish create_tool"
LLM: [calls publish - item now contains embedded stats]
```

This is a one-time action, not automatic on every run.

---

## Pull Behavior

When pulling from registry, telemetry is NOT included:

- Registry stores telemetry separately from item content
- Pull fetches clean item content only
- User's local telemetry starts fresh

---

## Benefits Over Embedded

| Aspect | Embedded | Centralized |
|--------|----------|-------------|
| Git hygiene | Constant dirty state | No impact |
| Merge conflicts | Frequent in telemetry blocks | None |
| Privacy | Easy to accidentally commit | Never in repos |
| Implementation | Complex (3 format patchers) | Simple (1 YAML) |
| Re-signing | Every execution | Never (for telemetry) |
| Item integrity | Mutable counters in signed content | Signed content stable |
| Concurrent runs | Risk of lost increments | File locking handles it |

---

## Privacy & Defaults

| Setting | Default | Reason |
|---------|---------|--------|
| Telemetry enabled | false | Opt-in only |
| File permissions | 0600 | Private to user |
| In git repos | Never | Stats stay in ~/.ai/ |
| On publish | Separate payload | Not embedded by default |

---

## Implementation Checklist

**Architecture:** All telemetry code lives in `.ai/tools/core/` as user-space tools. The core kernel remains untouched—telemetry is a layer on top, not baked in.

Follow these steps in order. Each step should be a separate commit.

### Step 1: Create shared telemetry library

**File:** `.ai/tools/core/telemetry_lib.py`

Contains all telemetry classes in one file:

1. `get_user_path()` - Returns `Path.home() / ".ai"`
2. `TelemetryContext` dataclass - Copy from above
3. `TrackedHttpClient` class - Copy from above
4. `TrackedSubprocess` class - Copy from above
5. `TelemetryStore` class - Copy from above (the big one)

This is a library file imported by the other tools, not executed directly.

### Step 2: Create wrapper execution tool

**File:** `.ai/tools/core/run_with_telemetry.py`

This tool wraps item execution with telemetry tracking:

1. Check if telemetry enabled in `~/.ai/config.yaml`
2. If disabled, just call normal execute and return
3. If enabled:
   - Create `TelemetryContext()`
   - Call the underlying MCP execute
   - Capture outcome ("success", "failure", "timeout")
   - Call `TelemetryStore().record_execution(...)`
4. Params: `item_type`, `item_id`, `project_path`, `params`

**Key:** This tool does NOT modify item files. Stats go to `~/.ai/telemetry.yaml` only.

### Step 3: Create configuration tool

**File:** `.ai/tools/core/configure_telemetry.py`

1. Read/write `~/.ai/config.yaml`
2. Set `telemetry.enabled` to true/false
3. Create config file if missing
4. Params: `enabled: bool`

### Step 4: Create status tool

**File:** `.ai/tools/core/telemetry_status.py`

1. Show current config (enabled/disabled)
2. If `item_id` provided, show stats for that item
3. If no `item_id`, show summary of all items
4. Params: `item_id: str | None`

### Step 5: Create clear tool

**File:** `.ai/tools/core/clear_telemetry.py`

1. Call `TelemetryStore().clear(item_id)`
2. If `item_id` is None, clear all
3. Params: `item_id: str | None`

### Step 6: Create export tool (optional)

**File:** `.ai/tools/core/export_telemetry.py`

1. Bake telemetry stats into item frontmatter before publish
2. This is a one-time explicit action, not automatic
3. Params: `item_id: str`

### Step 7: Tests

**File:** `tests/test_telemetry_tools.py`

Test cases (import from `telemetry_lib.py` directly):
1. `test_record_execution_creates_file` - First execution creates telemetry.yaml
2. `test_record_execution_increments_counters` - Multiple runs increment correctly
3. `test_running_average_calculation` - avg_duration_ms computed correctly
4. `test_clear_single_item` - Clears only specified item
5. `test_clear_all` - Clears entire items dict
6. `test_concurrent_writes` - Use threading to verify locking works
7. `test_telemetry_disabled_no_write` - No file written when disabled
8. `test_configure_creates_config` - Config file created if missing

---

## Future Enhancements

1. **Dashboards**: Parse telemetry.yaml for visualizations
2. **Quality badges**: Auto-generate from success rates
3. **Anomaly detection**: Flag degrading success rates
4. **Sync across machines**: Optional cloud backup of telemetry

---

_Document Status: Design Draft_  
_Last Updated: 2026-01-29_
