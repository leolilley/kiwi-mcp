# Mission Control: System Architecture

**Version:** 1.0.0  
**Status:** Design  
**Last Updated:** 2026-01-22

---

## Executive Summary

Mission Control is the observability & control plane for Kiwi MCP. It provides:

1. **Real-time data pipeline** connecting multiple MCP instances
2. **Session & thread state management** for tracking agent execution
3. **Comprehensive audit logging** with permission enforcement visibility
4. **Interactive visualization** of system relationships and execution flows
5. **Terminal interface** for live interaction with running MCPs

The system is split into:

- **Frontend:** React-based UI with real-time WebSocket updates
- **Backend:** FastAPI server managing MCP connections, sessions, logs
- **MCPs:** Existing Kiwi MCP instances instrumented for observability

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    MISSION CONTROL UI                        │
│  (Next.js 14, React 18, TanStack Query, Zustand)            │
│  ┌──────────────┬──────────────┬──────────────┐             │
│  │  Dashboard   │  Inspector   │  Log Stream  │ ...         │
│  │  Graph Viz   │  Terminal    │  Settings    │             │
│  └──────────────┴──────────────┴──────────────┘             │
│                       ↓ WebSocket + HTTP                     │
├──────────────────────────────────────────────────────────────┤
│             MISSION CONTROL BACKEND (FastAPI)                │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ WebSocket Server (asyncio)                          │    │
│  │ - Connection pool manager                           │    │
│  │ - Message routing & broadcast                       │    │
│  │ - Connection lifecycle management                   │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ MCP Gateway                                         │    │
│  │ - Multi-MCP connection manager                      │    │
│  │ - MCP discovery & health checks                     │    │
│  │ - Tool call routing & result streaming              │    │
│  │ - MCP instance lifecycle                            │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Session Manager                                     │    │
│  │ - Thread creation & tracking                        │    │
│  │ - Execution state snapshots                         │    │
│  │ - Parent/child agent relationships                  │    │
│  │ - Execution timeline building                       │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Log Aggregator                                      │    │
│  │ - Collect logs from all MCP instances               │    │
│  │ - Buffer & stream to UI clients                     │    │
│  │ - Filter by thread/MCP/level/service                │    │
│  │ - Persist to database                               │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Query API (REST + GraphQL)                          │    │
│  │ - Historical data retrieval                         │    │
│  │ - Search & filter across all data                   │    │
│  │ - Relationship graph queries                        │    │
│  │ - Permission audit trail                            │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Audit & Permission Logger                           │    │
│  │ - Log all permission checks                         │    │
│  │ - Track permission grants/denials                   │    │
│  │ - Permission inheritance tracing                    │    │
│  │ - Privilege escalation detection                    │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Database                                            │    │
│  │ - Sessions, threads, events                         │    │
│  │ - Logs, transcripts, artifacts                      │    │
│  │ - Permission audit trail                            │    │
│  │ - User preferences & saved views                    │    │
│  └─────────────────────────────────────────────────────┘    │
├──────────────────────────────────────────────────────────────┤
│                        MCP INSTANCES                         │
│  ┌──────────────┬──────────────┬──────────────┐             │
│  │   MCP #1     │   MCP #2     │   MCP #N     │             │
│  │ localhost    │ localhost    │ prod.io      │             │
│  │ :9000        │ :9001        │ :443         │             │
│  └──────────────┴──────────────┴──────────────┘             │
│                Instrumented with:                           │
│                - Structured logging                         │
│                - Event publishing (tool calls, results)     │
│                - Session tracking hooks                     │
└──────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. WebSocket Server

**Responsibility:** Real-time bidirectional communication between frontend and backend.

**Architecture:**

```python
class WebSocketServer:
    """Main WebSocket entry point"""

    async def connect(client_id: str):
        # Add client to pool
        # Send connection confirmation
        # Subscribe to default channels

    async def disconnect(client_id: str):
        # Remove client from pool
        # Clean up subscriptions

    async def broadcast(message: Message, channels: List[str]):
        # Send to all clients subscribed to channels
        # Validate message schema
        # Log broadcast event

    async def handle_client_message(client_id: str, msg: Message):
        # Route to appropriate handler
        # Could be: subscribe, unsubscribe, command, query
```

**Message Types:**

```python
# From UI → Backend
class UIMessage(BaseModel):
    type: Literal["subscribe", "unsubscribe", "command", "query"]
    payload: dict
    request_id: str  # For matching responses

# From Backend → UI
class ServerMessage(BaseModel):
    type: Literal["event", "response", "error"]
    channel: str
    payload: dict
    timestamp: datetime
    request_id: Optional[str]  # Matches request if response
```

**Channels:**

```
- "global"                    # System events
- "thread:{thread_id}"        # Thread-specific events
- "mcp:{mcp_id}"              # MCP instance events
- "logs:{thread_id}"          # Logs for specific thread
- "logs:*"                    # All logs
- "permission:{thread_id}"    # Permission checks for thread
```

---

### 2. MCP Gateway

**Responsibility:** Manage connections to multiple MCP instances, route tool calls, collect responses.

**Architecture:**

```python
class MCPGateway:
    """Multi-MCP connection manager"""

    mcp_instances: Dict[str, MCPConnection] = {}
    discovery_service: MCPDiscoveryService
    health_monitor: HealthMonitor

    async def register_mcp(endpoint: str, config: MCPConfig):
        # Discover MCP at endpoint
        # Establish connection
        # Start health monitoring
        # Broadcast "mcp.registered" event

    async def call_tool(tool_name: str, params: dict) -> Result:
        # Find MCP with tool
        # Route call
        # Stream results back
        # Log call & result

    async def health_check():
        # Ping all MCPs
        # Report status changes
        # Attempt reconnect if down
```

**Example Flow:**

```
UI calls /query API with MCP endpoint
  ↓
Backend queries backend_service.get_mcp(endpoint)
  ↓
MCPGateway routes to correct MCP
  ↓
MCP executes (returns stream of events)
  ↓
Backend broadcasts each event to subscribed clients
  ↓
UI updates in real-time
```

---

### 3. Session Manager

**Responsibility:** Track agent threads, build execution timeline, manage parent-child relationships.

**Data Models:**

```python
class Thread(BaseModel):
    id: str
    parent_id: Optional[str]  # Parent thread if subagent
    mcp_id: str  # Which MCP is running this
    status: Literal["running", "paused", "complete", "error", "cancelled"]

    started_at: datetime
    ended_at: Optional[datetime]

    user_input: str
    execution_context: dict

    current_step: Optional[ExecutionStep]
    timeline: List[ExecutionStep]

    memory_usage: int  # bytes
    cpu_usage: float  # percent

    llm_transcript: List[LLMMessage]  # Streaming as it happens

class ExecutionStep(BaseModel):
    sequence: int
    timestamp: datetime
    duration_ms: float
    type: Literal["directive", "script", "tool_call", "tool_result", "check_permission"]
    description: str
    details: dict
    status: Literal["pending", "running", "complete", "error"]

class LLMMessage(BaseModel):
    role: Literal["user", "agent", "tool", "directive"]
    content: str
    timestamp: datetime
    metadata: dict
```

**Session Lifecycle:**

```
1. Agent starts (e.g., directive execution)
   → Backend receives "session.started" from MCP
   → Session Manager creates Thread record
   → Broadcasts "thread.created" to UI

2. Agent executes steps
   → Each step logged as ExecutionStep
   → LLM messages streamed to transcript
   → Real-time updates broadcast

3. Agent completes / errors / pauses
   → Final state captured
   → Timeline finalized
   → "thread.ended" broadcast
```

---

### 4. Log Aggregator

**Responsibility:** Collect structured logs from all MCPs, buffer, stream to clients, persist.

**Architecture:**

```python
class LogAggregator:
    """Collect & stream logs from MCPs"""

    log_buffer: asyncio.Queue  # Unbounded queue
    subscribers: Dict[str, Set[str]] = {}  # channel → clients

    async def ingest_log(log: StructuredLog):
        # Add to buffer
        # Determine channels (thread_id, mcp_id, level, service)
        # Broadcast to subscribed clients
        # Persist to database (async)

    async def subscribe_logs(client_id: str, filter: LogFilter):
        # Add client to channel subscriptions
        # Stream historical logs (last N)
        # Stream new logs as they arrive

class StructuredLog(BaseModel):
    timestamp: datetime
    level: Literal["DEBUG", "INFO", "WARN", "ERROR"]
    service: str  # "auth", "parser", "executor", etc
    thread_id: Optional[str]
    mcp_id: str
    message: str
    context: dict
    exception: Optional[str]

class LogFilter(BaseModel):
    threads: Optional[List[str]]  # Filter to threads
    mcps: Optional[List[str]]      # Filter to MCPs
    levels: List[str] = ["INFO", "WARN", "ERROR"]
    services: Optional[List[str]]
    search: Optional[str]           # Full-text search
    from_timestamp: Optional[datetime]
    to_timestamp: Optional[datetime]
```

**Storage Strategy:**

- **Hot storage (1 week):** PostgreSQL for latest logs
- **Warm storage (1 month):** Compressed S3/Minio
- **Cold storage (archive):** Compressed backups

---

### 5. Query API

**Responsibility:** Provide REST/GraphQL endpoints for historical data retrieval and search.

**Key Endpoints:**

```python
# Threads
GET    /api/threads                    # List all threads
GET    /api/threads/{thread_id}        # Get thread details
GET    /api/threads/{thread_id}/transcript  # Get LLM transcript
GET    /api/threads/{thread_id}/timeline    # Get execution timeline

# Logs
GET    /api/logs                       # Query logs with filters
GET    /api/logs/export                # Export logs as JSON/CSV

# MCPs
GET    /api/mcps                       # List connected MCPs
GET    /api/mcps/{mcp_id}/health       # MCP health status
GET    /api/mcps/{mcp_id}/tools        # Available tools

# Relationships (Graph)
GET    /api/graph/entities             # All directives, scripts, knowledge
GET    /api/graph/relationships        # All connections
GET    /api/graph/search               # Search entities

# Permissions
GET    /api/permissions/audit          # All permission checks
GET    /api/permissions/audit/{thread_id}  # Permission checks for thread

# Search (Full-text + filters)
GET    /api/search                     # Cross-search all data

# Saved Views
GET    /api/views
POST   /api/views
PUT    /api/views/{view_id}
DELETE /api/views/{view_id}
```

---

### 6. Audit & Permission Logger

**Responsibility:** Comprehensive logging of all permission checks, grants, denials.

**Data Model:**

```python
class PermissionEvent(BaseModel):
    id: str
    timestamp: datetime

    thread_id: str
    user_id: str

    resource: str  # What they're accessing
    action: str    # "read", "write", "execute"

    granted: bool
    reason: str    # Why it was granted/denied

    permission_rules_checked: List[PermissionRule]  # Which rules matched
    inheritance_chain: List[str]  # Permission inheritance path

    escalation_detected: bool
    severity: Literal["info", "warn", "critical"]
```

**Features:**

- Trace permission inheritance across agent hierarchy
- Detect privilege escalation attempts
- Generate compliance reports
- Support fine-grained queries ("all denials in last 24h")

---

### 7. Database Schema

**Core Tables:**

```sql
-- Sessions/Threads
CREATE TABLE threads (
    id TEXT PRIMARY KEY,
    parent_id TEXT,
    mcp_id TEXT NOT NULL,
    status TEXT,
    user_input TEXT,
    execution_context JSONB,

    started_at TIMESTAMP,
    ended_at TIMESTAMP,

    memory_usage INT,
    cpu_usage FLOAT,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Execution Timeline
CREATE TABLE execution_steps (
    id TEXT PRIMARY KEY,
    thread_id TEXT REFERENCES threads(id),
    sequence INT,
    timestamp TIMESTAMP,
    duration_ms FLOAT,
    type TEXT,
    description TEXT,
    details JSONB,
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- LLM Transcript
CREATE TABLE llm_messages (
    id TEXT PRIMARY KEY,
    thread_id TEXT REFERENCES threads(id),
    role TEXT,
    content TEXT,
    timestamp TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Logs
CREATE TABLE logs (
    id TEXT PRIMARY KEY,
    timestamp TIMESTAMP,
    level TEXT,
    service TEXT,
    thread_id TEXT,
    mcp_id TEXT,
    message TEXT,
    context JSONB,
    exception TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Permission Audit
CREATE TABLE permission_events (
    id TEXT PRIMARY KEY,
    timestamp TIMESTAMP,
    thread_id TEXT REFERENCES threads(id),
    user_id TEXT,
    resource TEXT,
    action TEXT,
    granted BOOLEAN,
    reason TEXT,
    permission_rules JSONB,
    inheritance_chain JSONB,
    escalation_detected BOOLEAN,
    severity TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- User Preferences
CREATE TABLE user_preferences (
    user_id TEXT PRIMARY KEY,
    theme TEXT,
    log_filters JSONB,
    saved_views JSONB,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Saved Views/Dashboards
CREATE TABLE saved_views (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    name TEXT,
    description TEXT,
    view_config JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

---

## Real-Time Data Flow

### Scenario: User opens Dashboard

```
1. UI connects WebSocket
   → Backend: "connect" event
   → Server adds client to connection pool

2. UI: subscribe({ channel: "global", type: "threads" })
   → Server: sends list of active threads
   → Server: adds client to "global" channel subscribers

3. MCP #1 broadcasts: "thread.started" event
   → Backend Session Manager creates Thread record
   → Backend broadcasts: "thread.created" event
   → All subscribed clients receive update

4. Agent executes tools
   → MCP logs: { type: "tool_call", thread_id: "T-123", ... }
   → Log Aggregator ingests log
   → Broadcasts to "logs:T-123" and "logs:*" subscribers

5. User clicks on thread
   → UI: subscribe({ channel: "thread:T-123" })
   → Backend sends: thread details, transcript so far, timeline
   → UI switches to Thread Inspector screen
   → Continues receiving updates for this thread
```

---

## Deployment Topology

### Development

```
docker-compose.dev.yml:
- mission_control_backend:8000
- mission_control_ui:3000
- postgres:5432
- mcp_instance_1:9000
- mcp_instance_2:9001
```

### Production (Single Node)

```
Docker containers:
- mission_control_backend (FastAPI)
- mission_control_ui (Next.js)
- postgres (PostgreSQL)
- nginx (reverse proxy)

Volumes:
- postgres_data/
- logs/ (for archival)
```

### Production (Distributed)

```
- K8s cluster
- Helm charts for deployment
- Persistent volumes for logs
- Redis for log buffer (horizontal scaling)
- PostgreSQL with replication
- Prometheus + Grafana for monitoring
```

---

## Security Considerations

1. **WebSocket Security**

   - Require authentication (JWT in `?token=` or `Authorization` header)
   - Validate origin header
   - Rate limit connections per user
   - Encrypt sensitive data in transit (WSS)

2. **Permission Enforcement**

   - Mission Control respects Kiwi MCP's permission system
   - Can only see threads user is authorized to see
   - Can only issue commands user is authorized to issue
   - All access logged to audit trail

3. **Data Privacy**

   - Logs may contain sensitive data (API keys, PII)
   - Support log masking/redaction rules
   - Encrypt logs at rest
   - Support fine-grained access control

4. **DoS Protection**
   - Rate limit queries
   - Limit log retention per MCP
   - Limit concurrent WebSocket connections
   - Validate all inputs

---

## Error Handling

**MCP Connection Loss:**

- Attempt reconnect with exponential backoff
- Buffer logs locally
- Mark MCP as "degraded" in UI
- Once reconnected, sync logs & state

**WebSocket Disconnect:**

- Persist client subscriptions
- Reconnect resumes previous subscriptions
- Don't lose pending queries

**Database Unavailable:**

- Cache logs in memory with limited size
- Serve from cache when DB unavailable
- Once DB recovers, persist cached logs

---

## Monitoring & Observability

Mission Control itself should be observable:

```python
# Prometheus metrics
mission_control_websocket_connections       # Current active WS clients
mission_control_mcp_connections             # MCPs connected
mission_control_message_throughput          # Messages/sec
mission_control_query_latency               # API query p50/p95/p99
mission_control_db_connection_pool          # Pool utilization
mission_control_log_buffer_size             # Buffered logs
```

---

## Configuration

```yaml
# mission_control.yml
server:
  host: 0.0.0.0
  port: 8000
  workers: 4

websocket:
  ping_interval: 30
  ping_timeout: 10
  max_connections: 1000

database:
  url: postgresql://user:pass@localhost/mission_control
  pool_size: 20

log_retention:
  hot: 7 days # PostgreSQL
  warm: 30 days # S3/compressed
  cold: 365 days # Archive

auth:
  jwt_secret: ${JWT_SECRET}
  require_auth: true

mcps:
  discovery_interval: 30 # seconds
  health_check_interval: 60
  reconnect_backoff: exponential
```

---

## Questions & Future Considerations

1. Should Mission Control manage MCP deployment itself?
2. Multi-tenancy support?
3. Integration with external monitoring systems?
4. Time-travel debugging capability?
5. Performance budgeting & SLOs?
