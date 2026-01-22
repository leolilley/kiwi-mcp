# Mission Control UI Roadmap

**Version:** 1.0.0  
**Status:** Planning  
**Last Updated:** 2026-01-22

---

## Overview

Mission Control is a full-stack observability and control platform for Kiwi MCP. It enables humans to observe, debug, and interact with multi-agent systems running across distributed MCP instances in real-time.

**Core Vision:**

- Real-time visibility into all agent threads and their execution
- Interactive debugging & inspection of LLM transcripts
- Live log streaming from multiple MCP instances
- Relationship visualization across all Kiwi artifacts (directives, scripts, knowledge)
- Terminal interface directly hooked into running MCPs
- Complete audit trail & permission enforcement visibility

---

## Phases Overview

| Phase  | Name                       | Duration | Focus                                                               |
| ------ | -------------------------- | -------- | ------------------------------------------------------------------- |
| **14** | Backend & WebSocket Server | 4 weeks  | MCP connections, session management, real-time streaming            |
| **15** | Core UI Screens            | 3 weeks  | Dashboard, thread inspector, log stream, terminal                   |
| **16** | Visualization & Graphs     | 2 weeks  | Relationship graphs, schema explorer, execution timeline            |
| **17** | Polish & Observability     | 2 weeks  | Exports, saved views, metrics, audit viewer                         |
| **18** | Advanced Features (Future) | TBD      | Predictive debugging, AI-assisted analysis, collaborative debugging |

---

## Phase 14: Backend & WebSocket Server (Weeks 1-4)

**Goal:** Build the real-time data pipeline connecting MCPs to the UI.

### Deliverables

- [ ] WebSocket server (FastAPI)
- [ ] Multi-MCP connection manager
- [ ] Session & thread state manager
- [ ] Log aggregator with buffering
- [ ] Query API for historical data
- [ ] MCP discovery & health monitoring
- [ ] Permission check logging
- [ ] Audit trail persistence

### Dependencies

- Kiwi MCP core system (Phases 1-13 completed)
- Existing KiwiProxy permission system
- Session tracking from Phase 3

### Success Metrics

- Handle 10+ concurrent MCP connections
- Log streaming latency < 100ms
- Thread state consistency across reconnects
- Zero data loss on WebSocket disconnects

---

## Phase 15: Core UI Screens (Weeks 5-7)

**Goal:** Build minimal, clean interface for real-time observation.

### Screens

- **Dashboard:** Active threads, MCP health, recent events
- **Thread Inspector:** Execution timeline, LLM transcript, live metrics
- **Log Stream:** Real-time filterable logs from all MCPs
- **Terminal:** Embedded Kiwi CLI connected to running MCPs
- **Project Manager:** Switch between projects, configure MCPs

### Deliverables

- [ ] Next.js 14 app scaffold
- [ ] Tab-based navigation system
- [ ] Real-time WebSocket client
- [ ] State management (TanStack Query + Zustand)
- [ ] Terminal emulation (Xterm.js)
- [ ] Mobile-responsive layout
- [ ] Dark mode support

### Dependencies

- Phase 14 (Backend) complete

### Success Metrics

- UI loads in < 1s
- Real-time updates visible < 200ms after MCP event
- Terminal responsive & usable
- Mobile layout functional

---

## Phase 16: Visualization & Graphs (Weeks 8-9)

**Goal:** Enable deep understanding of system relationships and execution flow.

### Visualizations

- **Relationship Graph:** Interactive visualization of directives, scripts, knowledge, and their connections
- **DB Schema Explorer:** Browse all entities, filters, search
- **Execution Timeline:** Per-thread execution flow with timing
- **Permission Flow:** Visualize permission checks and inheritance

### Deliverables

- [ ] Cytoscape.js graph rendering
- [ ] D3.js timeline/flamegraph
- [ ] Graph query layer (traversal, filtering)
- [ ] Schema introspection API
- [ ] Execution trace collection & formatting
- [ ] Interactive legend & filters

### Dependencies

- Phase 15 (Core UI) complete

### Success Metrics

- Graph renders 10k+ nodes smoothly
- Interactive zoom/pan/search working
- Timeline shows causality correctly
- Permission traces are accurate & auditable

---

## Phase 17: Polish & Observability (Weeks 10-11)

**Goal:** Production-ready observability platform.

### Deliverables

- [ ] Export logs/transcripts as JSON, CSV, PDF
- [ ] Saved dashboards & views
- [ ] Performance metrics dashboard (memory, CPU, latency)
- [ ] Audit trail viewer with filters
- [ ] Search across all logs, transcripts, events
- [ ] User preferences & settings
- [ ] API documentation
- [ ] Deployment guide (Docker, K8s)

### Dependencies

- Phase 16 (Visualization) complete

### Success Metrics

- Exports work reliably
- Search returns results in < 500ms
- UI feels polished & responsive
- Ready for production deployment

---

## Phase 18: Advanced Features (Future)

**Goal:** AI-assisted debugging and collaborative features.

### Potential Features

- **Predictive Debugging:** ML model suggests breakpoints & inspection points
- **AI Analysis:** Automatically detect anomalies, bottlenecks, permission issues
- **Collaborative Debugging:** Multiple humans inspect same thread
- **Time-Travel Debugging:** Replay execution with state inspection
- **Performance Profiling:** Detailed flame graphs, bottleneck detection
- **Automated Alerts:** Watch for errors, permission violations, timeouts
- **Thread Comparison:** Diff two similar executions to find divergence

---

## Technology Stack

### Frontend

- **Framework:** Next.js 14 (App Router)
- **UI:** React 18 + Tailwind CSS
- **State:** TanStack Query v5 + Zustand
- **Real-time:** Native WebSocket + custom hooks
- **Visualization:** Cytoscape.js + D3.js
- **Terminal:** Xterm.js + mcp-cli
- **Dev Tools:** TypeScript, Vitest, Playwright

### Backend

- **Framework:** FastAPI (Python 3.11+)
- **Real-time:** WebSockets + asyncio
- **Database:** SQLite (dev) / PostgreSQL (prod)
- **Caching:** Redis (optional, for scaling)
- **Logging:** Structured JSON logs
- **Monitoring:** Prometheus + Grafana (optional)
- **Deploy:** Docker + Docker Compose

### Infrastructure

- **Local Dev:** Docker Compose (UI + Backend + MCPs)
- **Production:** Kubernetes (optional) or VPS
- **Observability:** ELK stack (Elasticsearch, Logstash, Kibana) optional

---

## Architecture Layers

```
┌─────────────────────────────────────────────┐
│         Mission Control UI (Next.js)        │
│    Dashboard | Inspector | Logs | Graphs    │
└─────────────────────────────────────────────┘
           ↓ WebSocket ↓ HTTP REST
┌─────────────────────────────────────────────┐
│    Mission Control Backend (FastAPI)        │
│  Sessions | Logs | Query | MCP Gateway      │
└─────────────────────────────────────────────┘
      ↓ WebSocket ↓ HTTP
  ┌─────────────────────┐
  │  MCP Instance #1    │
  │  MCP Instance #2    │
  │  MCP Instance #N    │
  └─────────────────────┘
```

---

## Development Setup (Phase 14+)

```bash
# Start development stack
docker-compose -f docker-compose.dev.yml up

# Services:
# - Backend API: http://localhost:8000
# - UI: http://localhost:3000
# - Docs: http://localhost:8000/docs
# - MCP #1: localhost:9000
# - MCP #2: localhost:9001
```

---

## Design Principles

1. **Minimal & Clean:** Pure design, no clutter, maximum information density
2. **Real-time First:** Every screen should update as events occur
3. **Observable:** All internal state visible, audit trail always on
4. **Composable:** Screens can be combined, exported, shared
5. **Keyboard-First:** Full keyboard navigation, terminal-like feel
6. **Dark Mode Native:** Dark is default, light is option
7. **Mobile-Friendly:** Works on tablets, responsive layout
8. **Accessible:** WCAG 2.1 AA compliance

---

## Success Criteria (End of Phase 17)

- [ ] Single-pane-of-glass for all agent threads
- [ ] Real-time log streaming < 100ms latency
- [ ] Full execution transcript for every thread
- [ ] Relationship graph with 10k+ nodes rendering smoothly
- [ ] Terminal working seamlessly for live CLI access
- [ ] Complete audit trail visible & searchable
- [ ] Permission checks traced & logged
- [ ] Production-ready deployment
- [ ] Documentation complete
- [ ] 95%+ test coverage on backend

---

## Related Documents

- [Mission Control Architecture](./MISSION_CONTROL_ARCHITECTURE.md) — System design deep dive
- [Phase 14: Backend & WebSocket](./MISSION_CONTROL_PHASE_14.md) — Backend implementation guide
- [Phase 15: Core UI Screens](./MISSION_CONTROL_PHASE_15.md) — UI component design
- [Phase 16: Visualization](./MISSION_CONTROL_PHASE_16.md) — Graph & visualization specs
- [Phase 17: Polish](./MISSION_CONTROL_PHASE_17.md) — Production hardening

---

## Timeline

```
Week 1-4:   Phase 14 (Backend)
Week 5-7:   Phase 15 (UI)
Week 8-9:   Phase 16 (Graphs)
Week 10-11: Phase 17 (Polish)
─────────────────────────────
~11 weeks total for Phases 14-17
```

---

## Questions to Revisit

1. Should Mission Control be embedded in Kiwi MCP, or separate service?
2. Do we need real-time sync to a remote registry?
3. Should we support multiple organizations/teams?
4. Do we need fine-grained RBAC for Mission Control access?
5. Should historical data be queryable (e.g., "show me all permission violations last week")?
