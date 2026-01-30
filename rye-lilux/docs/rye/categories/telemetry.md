**Source:** Original implementation: `.ai/tools/rye/telemetry/` and `core/telemetry*.py` in kiwi-mcp

# Telemetry Category

## Purpose

Telemetry tools provide **system monitoring, diagnostics, and observability** for RYE operations.

**Location:** `.ai/tools/rye/telemetry/`  
**Count:** 7 tools  
**Executor:** All use `python_runtime`

## Core Telemetry Tools

### 1. Telemetry Configure (`telemetry_configure.py`)

**Purpose:** Configure telemetry collection settings

```python
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "telemetry"

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "enabled": {"type": "boolean"},
        "level": {"type": "string", "enum": ["debug", "info", "warning", "error"]},
        "retention_days": {"type": "integer", "default": 30},
        "sampling_rate": {"type": "number", "minimum": 0, "maximum": 1},
    },
}
```

### 2. Telemetry Status (`telemetry_status.py`)

**Purpose:** Get current telemetry status

```python
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "telemetry"

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "detailed": {"type": "boolean", "default": False},
    },
}

# Returns: {
#   "enabled": true,
#   "level": "info",
#   "events_collected": 1234,
#   "storage_used": "2.5MB",
#   "last_sync": "2026-01-30T12:00:00Z"
# }
```

### 3. Telemetry Clear (`telemetry_clear.py`)

**Purpose:** Clear telemetry data

```python
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "telemetry"

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "older_than_days": {"type": "integer", "default": 30},
        "confirm": {"type": "boolean", "default": False},
    },
}
```

### 4. Telemetry Export (`telemetry_export.py`)

**Purpose:** Export telemetry data for analysis

```python
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "telemetry"

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "format": {"type": "string", "enum": ["json", "csv", "parquet"]},
        "output_path": {"type": "string"},
        "time_range": {
            "type": "object",
            "properties": {
                "start": {"type": "string", "format": "date-time"},
                "end": {"type": "string", "format": "date-time"},
            },
        },
    },
    "required": ["output_path"]
}
```

### 5. RAG Configure (`rag_configure.py`)

**Purpose:** Configure RAG (Retrieval-Augmented Generation) settings

```python
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "telemetry"

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "model": {"type": "string"},
        "embedding_model": {"type": "string"},
        "chunk_size": {"type": "integer", "default": 512},
        "overlap": {"type": "integer", "default": 50},
        "enabled": {"type": "boolean", "default": True},
    },
}
```

### 6. Library Configure (`lib_configure.py`)

**Purpose:** Configure library management and dependencies

```python
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "telemetry"

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "auto_update": {"type": "boolean", "default": False},
        "cache_enabled": {"type": "boolean", "default": True},
        "cache_ttl_hours": {"type": "integer", "default": 24},
    },
}
```

### 7. Health Check (`health_check.py`)

**Purpose:** Perform system health check

```python
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "telemetry"

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "detailed": {"type": "boolean", "default": False},
        "checks": {
            "type": "array",
            "items": {"type": "string", "enum": ["disk", "memory", "cpu", "network"]},
            "default": ["disk", "memory", "cpu"]
        },
    },
}

# Returns: {
#   "status": "healthy",
#   "disk": {"status": "ok", "used_percent": 45},
#   "memory": {"status": "ok", "used_percent": 60},
#   "cpu": {"status": "ok", "used_percent": 30},
#   "timestamp": "2026-01-30T12:00:00Z"
# }
```

## Telemetry Data Flow

```
RYE Operations
    │
    ├─→ Log events
    ├─→ Telemetry system captures
    │
    ├─→ Configure (telemetry_configure)
    ├─→ Monitor (telemetry_status, health_check)
    ├─→ Export (telemetry_export)
    └─→ Maintain (telemetry_clear)
```

## Metadata Pattern

All telemetry tools follow this pattern:

```python
# .ai/tools/rye/telemetry/{name}.py

__version__ = "1.0.0"
__tool_type__ = "python"
__executor_id__ = "python_runtime"
__category__ = "telemetry"

CONFIG_SCHEMA = { ... }

def main(**kwargs) -> dict:
    """Telemetry operation."""
    pass
```

## Usage Examples

### Check Health

```bash
Call health_check with:
  detailed: true
  checks: ["disk", "memory", "cpu", "network"]
```

### Export Telemetry

```bash
Call telemetry_export with:
  format: "json"
  output_path: "/home/user/telemetry.json"
  time_range:
    start: "2026-01-01T00:00:00Z"
    end: "2026-01-31T23:59:59Z"
```

### Configure Telemetry

```bash
Call telemetry_configure with:
  enabled: true
  level: "info"
  retention_days: 60
  sampling_rate: 0.8
```

## Key Characteristics

| Aspect | Detail |
|--------|--------|
| **Count** | 7 tools |
| **Location** | `.ai/tools/rye/telemetry/` |
| **Executor** | All use `python_runtime` |
| **Purpose** | Monitoring, diagnostics, observability |
| **Data Types** | Metrics, logs, events, health |
| **Extensibility** | Add new metrics → new telemetry tools |

## Related Documentation

- [[overview]] - All categories
- [[capabilities]] - System capabilities
- [[../bundle/structure]] - Bundle organization
