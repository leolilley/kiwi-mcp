# Phase 14: Backend & WebSocket Server

**Duration:** 4 weeks (Weeks 1-4)  
**Status:** Planning  
**Last Updated:** 2026-01-22  

---

## Overview

Phase 14 builds the real-time data pipeline that connects MCP instances to the UI. The backend is a FastAPI server that:

- Accepts WebSocket connections from the frontend
- Manages multiple MCP instance connections
- Aggregates logs, session data, and events
- Broadcasts real-time updates to connected clients
- Provides REST API for historical queries

**Key Goal:** Get real-time data flowing from MCPs → Backend → UI with < 100ms latency.

---

## Deliverables

### Week 1: Project Setup & WebSocket Basics

- [ ] FastAPI project scaffolding
- [ ] WebSocket server with connection management
- [ ] Basic message routing
- [ ] Development Docker Compose setup
- [ ] Database schema & migrations
- [ ] Structured logging setup

**Acceptance Criteria:**
- Can connect from browser via WebSocket
- Can receive/send messages
- Database initializes cleanly
- All containers run via `docker-compose up`

---

### Week 2: MCP Gateway & Discovery

- [ ] MCP connection manager (connect to one or more MCPs)
- [ ] MCP discovery service (find MCPs on network)
- [ ] Health monitoring (periodic pings)
- [ ] Reconnection logic with exponential backoff
- [ ] Tool routing (forward tool calls to correct MCP)

**Acceptance Criteria:**
- Can connect to 3+ MCPs simultaneously
- Detects MCP disconnect/reconnect
- Tool calls routed correctly
- Health status visible in logs

---

### Week 3: Session & Log Management

- [ ] Thread/session tracking
- [ ] Execution timeline building
- [ ] Log aggregation from all MCPs
- [ ] LLM transcript collection
- [ ] Permission event logging
- [ ] Database persistence

**Acceptance Criteria:**
- Thread lifecycle tracked end-to-end
- Logs arrive < 100ms after generation
- Transcripts collected in order
- Queries return consistent data

---

### Week 4: Query API & Audit

- [ ] REST API endpoints (threads, logs, MCPs, graph)
- [ ] Historical data queries with filters
- [ ] Audit trail queries
- [ ] Search implementation
- [ ] Error handling & resilience
- [ ] API documentation

**Acceptance Criteria:**
- All endpoints tested & documented
- Queries return < 500ms
- Comprehensive error messages
- Ready for Phase 15 UI integration

---

## Implementation Plan

### Week 1: Scaffolding

#### 1.1 Project Structure

```
mission_control_backend/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── models.py                # Data models
│   ├── database.py              # Database setup
│   │
│   ├── websocket/
│   │   ├── __init__.py
│   │   ├── manager.py           # WebSocket connection pool
│   │   ├── messages.py          # Message types
│   │   ├── handlers.py          # Message handlers
│   │   └── broadcaster.py       # Event broadcast logic
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── session.py           # Thread/session tracking
│   │   ├── log_aggregator.py    # Log collection
│   │   ├── mcp_gateway.py       # MCP connections
│   │   ├── query.py             # Query API logic
│   │   └── audit.py             # Permission logging
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── threads.py           # /api/threads endpoints
│   │   ├── logs.py              # /api/logs endpoints
│   │   ├── mcps.py              # /api/mcps endpoints
│   │   ├── graph.py             # /api/graph endpoints
│   │   ├── permissions.py       # /api/permissions endpoints
│   │   └── search.py            # /api/search endpoints
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logging.py           # Structured logging
│       └── errors.py            # Custom exceptions
│
├── tests/
│   ├── test_websocket.py
│   ├── test_mcp_gateway.py
│   ├── test_session.py
│   ├── test_api.py
│   └── fixtures.py
│
├── migrations/
│   └── 001_initial_schema.sql
│
├── docker-compose.dev.yml
├── Dockerfile
├── requirements.txt
├── pyproject.toml
└── README.md
```

#### 1.2 Core Models

```python
# app/models.py

from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel
from enum import Enum

# WebSocket
class WSMessage(BaseModel):
    type: str
    payload: dict
    request_id: Optional[str] = None

# Thread/Session
class ThreadStatus(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETE = "complete"
    ERROR = "error"
    CANCELLED = "cancelled"

class ExecutionStep(BaseModel):
    sequence: int
    timestamp: datetime
    duration_ms: float
    type: str
    description: str
    details: dict
    status: str

class Thread(BaseModel):
    id: str
    parent_id: Optional[str]
    mcp_id: str
    status: ThreadStatus
    user_input: str
    execution_context: dict
    
    started_at: datetime
    ended_at: Optional[datetime]
    
    memory_usage: int
    cpu_usage: float
    
    timeline: List[ExecutionStep]

# Logging
class StructuredLog(BaseModel):
    timestamp: datetime
    level: Literal["DEBUG", "INFO", "WARN", "ERROR"]
    service: str
    thread_id: Optional[str]
    mcp_id: str
    message: str
    context: dict
    exception: Optional[str]

# MCP
class MCPInstance(BaseModel):
    id: str
    endpoint: str
    status: Literal["connected", "connecting", "disconnected"]
    last_seen: datetime
    tools: List[str]
    version: str

# Permissions
class PermissionEvent(BaseModel):
    id: str
    timestamp: datetime
    thread_id: str
    user_id: str
    resource: str
    action: str
    granted: bool
    reason: str
```

#### 1.3 Database Setup

```python
# app/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

DATABASE_URL = "postgresql://user:pass@postgres:5432/mission_control"

# Use StaticPool for development (SQLite)
# Use NullPool for production (PostgreSQL)
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    echo=True,  # Log SQL (disable in production)
)

SessionLocal = sessionmaker(bind=engine)

async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

#### 1.4 WebSocket Manager

```python
# app/websocket/manager.py

import asyncio
import json
from typing import Set, Dict, List
from datetime import datetime
import uuid

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, "WebSocketConnection"] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # channel → client_ids
        
    async def connect(self, client_id: str, websocket):
        self.active_connections[client_id] = websocket
        print(f"Client {client_id} connected. Total: {len(self.active_connections)}")
        
    async def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            # Remove from all subscriptions
            for channel in list(self.subscriptions.keys()):
                self.subscriptions[channel].discard(client_id)
        print(f"Client {client_id} disconnected. Total: {len(self.active_connections)}")
    
    async def subscribe(self, client_id: str, channel: str):
        if channel not in self.subscriptions:
            self.subscriptions[channel] = set()
        self.subscriptions[channel].add(client_id)
        
    async def unsubscribe(self, client_id: str, channel: str):
        if channel in self.subscriptions:
            self.subscriptions[channel].discard(client_id)
    
    async def broadcast(self, channel: str, message: dict):
        """Broadcast to all clients subscribed to channel"""
        if channel not in self.subscriptions:
            return
            
        clients = list(self.subscriptions[channel])
        for client_id in clients:
            if client_id in self.active_connections:
                try:
                    await self.active_connections[client_id].send_json(message)
                except Exception as e:
                    print(f"Error sending to {client_id}: {e}")
                    await self.disconnect(client_id)

manager = ConnectionManager()
```

#### 1.5 Main App

```python
# app/main.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import uuid

from app.config import settings
from app.database import engine
from app.websocket.manager import manager
from app.api import threads, logs, mcps, graph, permissions, search

# Database startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up...")
    yield
    # Shutdown
    print("Shutting down...")

app = FastAPI(title="Mission Control", lifespan=lifespan)

# Include routers
app.include_router(threads.router, prefix="/api/threads", tags=["threads"])
app.include_router(logs.router, prefix="/api/logs", tags=["logs"])
app.include_router(mcps.router, prefix="/api/mcps", tags=["mcps"])
app.include_router(graph.router, prefix="/api/graph", tags=["graph"])
app.include_router(permissions.router, prefix="/api/permissions", tags=["permissions"])
app.include_router(search.router, prefix="/api/search", tags=["search"])

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    client_id = str(uuid.uuid4())
    await websocket.accept()
    await manager.connect(client_id, websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            msg_type = message.get("type")
            if msg_type == "subscribe":
                channel = message.get("channel")
                await manager.subscribe(client_id, channel)
                await websocket.send_json({
                    "type": "subscribed",
                    "channel": channel,
                    "request_id": message.get("request_id")
                })
            elif msg_type == "unsubscribe":
                channel = message.get("channel")
                await manager.unsubscribe(client_id, channel)
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        await manager.disconnect(client_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        await manager.disconnect(client_id)

# Health check
@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

#### 1.6 Docker Compose

```yaml
# docker-compose.dev.yml

version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: kiwi
      POSTGRES_PASSWORD: kiwi_dev
      POSTGRES_DB: mission_control
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  mission_control_backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://kiwi:kiwi_dev@postgres:5432/mission_control
      JWT_SECRET: dev-secret-key
    depends_on:
      - postgres
    volumes:
      - .:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

volumes:
  postgres_data:
```

**Start:** `docker-compose -f docker-compose.dev.yml up`

---

### Week 2: MCP Gateway

#### 2.1 MCP Connection Manager

```python
# app/services/mcp_gateway.py

from typing import Dict, List, Optional
import asyncio
import aiohttp
from datetime import datetime

class MCPConnection:
    def __init__(self, endpoint: str, config: dict):
        self.endpoint = endpoint
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.status = "disconnected"
        self.last_seen = datetime.now()
        self.tools = []
        self.version = "unknown"
        self.reconnect_attempts = 0
        
    async def connect(self):
        try:
            self.session = aiohttp.ClientSession()
            # Ping MCP to verify connection
            async with self.session.get(f"{self.endpoint}/health") as resp:
                if resp.status == 200:
                    self.status = "connected"
                    self.reconnect_attempts = 0
                    # Fetch tools
                    await self._fetch_tools()
        except Exception as e:
            self.status = "disconnected"
            print(f"Failed to connect to {self.endpoint}: {e}")
            
    async def _fetch_tools(self):
        try:
            async with self.session.get(f"{self.endpoint}/tools") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.tools = data.get("tools", [])
        except Exception as e:
            print(f"Failed to fetch tools from {self.endpoint}: {e}")
            
    async def disconnect(self):
        if self.session:
            await self.session.close()
        self.status = "disconnected"

class MCPGateway:
    def __init__(self):
        self.connections: Dict[str, MCPConnection] = {}
        self.health_check_task = None
        
    async def register_mcp(self, endpoint: str, config: dict):
        """Register a new MCP instance"""
        mcp_id = config.get("id", endpoint)
        conn = MCPConnection(endpoint, config)
        await conn.connect()
        self.connections[mcp_id] = conn
        return mcp_id
        
    async def get_mcp(self, mcp_id: str) -> Optional[MCPConnection]:
        return self.connections.get(mcp_id)
        
    async def call_tool(self, mcp_id: str, tool_name: str, params: dict) -> dict:
        """Call a tool on an MCP"""
        conn = self.connections.get(mcp_id)
        if not conn or conn.status != "connected":
            raise RuntimeError(f"MCP {mcp_id} not connected")
            
        try:
            async with conn.session.post(
                f"{conn.endpoint}/call",
                json={"tool": tool_name, "params": params}
            ) as resp:
                return await resp.json()
        except Exception as e:
            print(f"Tool call failed: {e}")
            raise
            
    async def start_health_monitoring(self, interval: int = 60):
        """Periodically check MCP health"""
        while True:
            await asyncio.sleep(interval)
            for mcp_id, conn in self.connections.items():
                try:
                    async with conn.session.get(f"{conn.endpoint}/health") as resp:
                        if resp.status == 200:
                            conn.status = "connected"
                            conn.last_seen = datetime.now()
                        else:
                            conn.status = "disconnected"
                except:
                    conn.status = "disconnected"

gateway = MCPGateway()
```

#### 2.2 MCP Discovery

```python
# app/services/mcp_gateway.py (continued)

class MCPDiscovery:
    """Find MCP instances on network"""
    
    async def discover_mdns(self) -> List[str]:
        """Discover via mDNS"""
        # Implementation with zeroconf library
        pass
        
    async def discover_registry(self, registry_url: str) -> List[str]:
        """Discover via registry service"""
        # Query registry for known MCPs
        pass
        
    async def discover_config(self, config_path: str) -> List[str]:
        """Load MCPs from config file"""
        # Read YAML/JSON config
        pass
```

---

### Week 3: Session & Log Management

#### 3.1 Thread/Session Manager

```python
# app/services/session.py

from datetime import datetime
from typing import Optional, List, Dict
from app.models import Thread, ExecutionStep, ThreadStatus
import uuid

class SessionManager:
    def __init__(self):
        self.threads: Dict[str, Thread] = {}
        
    def create_thread(
        self,
        mcp_id: str,
        user_input: str,
        execution_context: dict,
        parent_id: Optional[str] = None
    ) -> Thread:
        """Create new thread"""
        thread_id = f"T-{uuid.uuid4()}"
        thread = Thread(
            id=thread_id,
            parent_id=parent_id,
            mcp_id=mcp_id,
            status=ThreadStatus.RUNNING,
            user_input=user_input,
            execution_context=execution_context,
            started_at=datetime.now(),
            ended_at=None,
            memory_usage=0,
            cpu_usage=0,
            timeline=[]
        )
        self.threads[thread_id] = thread
        return thread
        
    def add_step(self, thread_id: str, step: ExecutionStep):
        """Add step to thread timeline"""
        if thread_id in self.threads:
            self.threads[thread_id].timeline.append(step)
            
    def update_thread_status(self, thread_id: str, status: ThreadStatus):
        """Update thread status"""
        if thread_id in self.threads:
            self.threads[thread_id].status = status
            if status in [ThreadStatus.COMPLETE, ThreadStatus.ERROR, ThreadStatus.CANCELLED]:
                self.threads[thread_id].ended_at = datetime.now()
                
    def get_thread(self, thread_id: str) -> Optional[Thread]:
        return self.threads.get(thread_id)
        
    def list_threads(self, status: Optional[ThreadStatus] = None) -> List[Thread]:
        if status:
            return [t for t in self.threads.values() if t.status == status]
        return list(self.threads.values())

session_manager = SessionManager()
```

#### 3.2 Log Aggregator

```python
# app/services/log_aggregator.py

import asyncio
from typing import Dict, Set, List
from datetime import datetime
from app.models import StructuredLog
from app.websocket.manager import manager as ws_manager

class LogAggregator:
    def __init__(self):
        self.log_buffer = asyncio.Queue()  # Unbounded queue
        self.subscribers: Dict[str, Set[str]] = {}  # channel → client_ids
        
    async def ingest_log(self, log: StructuredLog):
        """Ingest a log from MCP"""
        await self.log_buffer.put(log)
        
        # Broadcast to subscribers
        channels = [
            "logs:*",  # All logs
            f"logs:{log.thread_id}" if log.thread_id else None,  # Thread-specific
            f"logs:mcp:{log.mcp_id}",  # MCP-specific
            f"logs:{log.level}",  # Level-specific
        ]
        
        for channel in [c for c in channels if c]:
            await ws_manager.broadcast(channel, {
                "type": "log",
                "log": log.dict()
            })
            
    async def persist_logs(self, db_session):
        """Persist buffered logs to database"""
        while True:
            log = await self.log_buffer.get()
            # Insert into database
            # db_session.add(LogRecord(log))
            # db_session.commit()
            await asyncio.sleep(0.1)  # Batch every 100ms

log_aggregator = LogAggregator()
```

---

### Week 4: Query API

#### 4.1 REST Endpoints

```python
# app/api/threads.py

from fastapi import APIRouter, HTTPException
from typing import List, Optional
from app.services.session import session_manager
from app.models import Thread, ThreadStatus

router = APIRouter()

@router.get("/")
async def list_threads(status: Optional[ThreadStatus] = None):
    return session_manager.list_threads(status)

@router.get("/{thread_id}")
async def get_thread(thread_id: str):
    thread = session_manager.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread

@router.get("/{thread_id}/transcript")
async def get_transcript(thread_id: str):
    thread = session_manager.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    # Return transcript
    return {"messages": []}

@router.get("/{thread_id}/timeline")
async def get_timeline(thread_id: str):
    thread = session_manager.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"steps": thread.timeline}
```

```python
# app/api/logs.py

from fastapi import APIRouter, Query
from typing import List, Optional
from datetime import datetime

router = APIRouter()

@router.get("/")
async def query_logs(
    thread_id: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    limit: int = Query(100),
    offset: int = Query(0)
):
    # Query database with filters
    return {"logs": []}

@router.post("/export")
async def export_logs(format: str = "json"):
    # Export logs in specified format
    return {"status": "pending", "export_id": "e-123"}
```

---

## Testing Strategy

### Unit Tests (Week 1-4)

```python
# tests/test_websocket.py

import pytest
from app.websocket.manager import ConnectionManager

def test_connect_disconnect():
    manager = ConnectionManager()
    
    # Simulate connection
    manager.connect("client-1", None)
    assert "client-1" in manager.active_connections
    
    # Simulate disconnection
    manager.disconnect("client-1")
    assert "client-1" not in manager.active_connections

def test_subscribe_broadcast():
    manager = ConnectionManager()
    # Test subscribe/broadcast
    pass
```

### Integration Tests (Week 3-4)

```python
# tests/test_integration.py

@pytest.mark.asyncio
async def test_end_to_end_thread():
    """Test full thread lifecycle"""
    # Create thread
    # Add steps
    # Query thread
    # Verify data consistency
    pass
```

---

## Database Migrations

```sql
-- migrations/001_initial_schema.sql

CREATE TABLE threads (
    id TEXT PRIMARY KEY,
    parent_id TEXT,
    mcp_id TEXT NOT NULL,
    status TEXT NOT NULL,
    user_input TEXT,
    execution_context JSONB,
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    memory_usage INTEGER,
    cpu_usage FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE execution_steps (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL REFERENCES threads(id),
    sequence INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    duration_ms FLOAT,
    type TEXT NOT NULL,
    description TEXT,
    details JSONB,
    status TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE logs (
    id TEXT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    level TEXT NOT NULL,
    service TEXT NOT NULL,
    thread_id TEXT REFERENCES threads(id),
    mcp_id TEXT NOT NULL,
    message TEXT,
    context JSONB,
    exception TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE permission_events (
    id TEXT PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    thread_id TEXT REFERENCES threads(id),
    user_id TEXT,
    resource TEXT,
    action TEXT,
    granted BOOLEAN,
    reason TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_threads_mcp_id ON threads(mcp_id);
CREATE INDEX idx_threads_status ON threads(status);
CREATE INDEX idx_execution_steps_thread_id ON execution_steps(thread_id);
CREATE INDEX idx_logs_timestamp ON logs(timestamp);
CREATE INDEX idx_logs_thread_id ON logs(thread_id);
CREATE INDEX idx_permission_events_thread_id ON permission_events(thread_id);
```

---

## Success Metrics

By end of Phase 14:

- [ ] WebSocket server accepts connections
- [ ] Can connect to 3+ MCPs simultaneously
- [ ] Log latency < 100ms
- [ ] All REST endpoints working
- [ ] Comprehensive test coverage (>80%)
- [ ] Docker setup runs cleanly
- [ ] Ready for Phase 15 UI integration

---

## Next Phase Dependencies

Phase 15 (Core UI Screens) requires:
- ✅ WebSocket server running
- ✅ Real-time message routing working
- ✅ Thread/log data persisting
- ✅ REST API functional
