# Phase 17: Polish & Observability

**Duration:** 2 weeks (Weeks 10-11)  
**Status:** Planning  
**Last Updated:** 2026-01-22  

---

## Overview

Phase 17 transforms Mission Control from a feature-complete tool into a production-ready, polished observability platform. Focus areas:

1. **Export & Reporting:** Download logs, transcripts, graphs as multiple formats
2. **Saved Views:** User-defined dashboards and filters
3. **Performance Metrics:** System health, latency, throughput metrics
4. **Audit Trail Browser:** Comprehensive permission & action history
5. **Full-Text Search:** Search across all data types
6. **UX Polish:** Animations, transitions, error states
7. **Production Hardening:** Security, resilience, monitoring
8. **Documentation:** API docs, deployment guides, user guides

**Key Goal:** Mission Control ready for production use with 99.9% uptime, complete audit trail, and excellent UX.

---

## Deliverables by Week

### Week 10: Export, Search & Saved Views

#### 10.1 Export Functionality

**Purpose:** Download logs, transcripts, graphs for external analysis or compliance.

**Supported Formats:**
- JSON: Raw structured data
- CSV: Tabular format for Excel
- PDF: Pretty-printed reports
- JSONL: Streaming format for large exports

```typescript
// src/components/common/ExportButton.tsx
'use client'

import { useState } from 'react'
import { Download } from 'lucide-react'

interface ExportOptions {
  format: 'json' | 'csv' | 'pdf' | 'jsonl'
  includeMetadata: boolean
  dateRange?: [string, string]
}

export function ExportButton({ 
  data, 
  filename 
}: { 
  data: any
  filename: string
}) {
  const [isOpen, setIsOpen] = useState(false)
  
  const handleExport = async (format: string) => {
    const response = await fetch('/api/export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        data,
        format,
        filename,
      }),
    })
    
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${filename}.${format}`
    a.click()
    window.URL.revokeObjectURL(url)
  }
  
  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 bg-slate-800 hover:bg-slate-700 rounded transition"
      >
        <Download size={16} />
        Export
      </button>
      
      {isOpen && (
        <div className="absolute top-full right-0 mt-1 bg-slate-900 border border-slate-800 rounded shadow-lg z-10">
          {['JSON', 'CSV', 'PDF', 'JSONL'].map(fmt => (
            <button
              key={fmt}
              onClick={() => {
                handleExport(fmt.toLowerCase())
                setIsOpen(false)
              }}
              className="block w-full text-left px-4 py-2 hover:bg-slate-800 transition text-sm"
            >
              {fmt}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
```

**Backend Endpoints:**

```python
# app/api/export.py

from fastapi import APIRouter, HTTPException
from datetime import datetime
import json
import csv
import io

router = APIRouter()

@router.post("/export")
async def export_data(request: ExportRequest):
    """Export data in various formats"""
    
    if request.format == 'json':
        content = json.dumps(request.data, indent=2, default=str)
        media_type = 'application/json'
    
    elif request.format == 'csv':
        output = io.StringIO()
        # Flatten data for CSV
        rows = flatten_for_csv(request.data)
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
        content = output.getvalue()
        media_type = 'text/csv'
    
    elif request.format == 'pdf':
        # Use reportlab or similar
        content = generate_pdf_report(request.data)
        media_type = 'application/pdf'
    
    elif request.format == 'jsonl':
        lines = []
        for item in request.data:
            lines.append(json.dumps(item, default=str))
        content = '\n'.join(lines)
        media_type = 'application/x-ndjson'
    
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")
    
    return {
        'content': content,
        'media_type': media_type,
        'filename': f"{request.filename}.{request.format}"
    }
```

#### 10.2 Saved Views/Dashboards

**Purpose:** Users can create and save custom dashboards with specific filters and layouts.

**Features:**
- Save current view with name & description
- List saved views
- Load/edit/delete views
- Share view with others
- Default views (dashboard, logs, threads)

```typescript
// src/components/common/SaveViewDialog.tsx
'use client'

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'

interface SaveViewInput {
  name: string
  description: string
  config: ViewConfig
}

export function SaveViewButton({ currentConfig }: { currentConfig: ViewConfig }) {
  const [isOpen, setIsOpen] = useState(false)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  
  const saveMutation = useMutation({
    mutationFn: async (input: SaveViewInput) => {
      const res = await fetch('/api/views', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(input),
      })
      return res.json()
    },
    onSuccess: () => {
      setIsOpen(false)
      setName('')
      setDescription('')
    },
  })
  
  const handleSave = () => {
    saveMutation.mutate({
      name,
      description,
      config: currentConfig,
    })
  }
  
  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="px-3 py-2 bg-blue-700 hover:bg-blue-600 rounded transition text-sm"
      >
        Save View
      </button>
      
      {isOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-slate-900 border border-slate-800 rounded p-6 w-96 space-y-4">
            <h2 className="font-semibold text-lg">Save View</h2>
            
            <input
              type="text"
              placeholder="View name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
            />
            
            <textarea
              placeholder="Description (optional)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
              rows={3}
            />
            
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setIsOpen(false)}
                className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded transition"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={!name || saveMutation.isPending}
                className="px-4 py-2 bg-blue-700 hover:bg-blue-600 rounded transition disabled:opacity-50"
              >
                {saveMutation.isPending ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
```

**Backend:**

```python
# app/api/views.py

from fastapi import APIRouter, HTTPException
from app.models import SavedView

router = APIRouter()

@router.get("/")
async def list_views(user_id: str):
    """List saved views for user"""
    # Query database
    return []

@router.post("/")
async def create_view(request: CreateViewRequest, user_id: str):
    """Create new saved view"""
    view = SavedView(
        id=uuid.uuid4(),
        user_id=user_id,
        name=request.name,
        description=request.description,
        config=request.config,
        created_at=datetime.now(),
    )
    # Save to database
    return view

@router.put("/{view_id}")
async def update_view(view_id: str, request: UpdateViewRequest):
    """Update saved view"""
    # Update in database
    return {}

@router.delete("/{view_id}")
async def delete_view(view_id: str):
    """Delete saved view"""
    # Delete from database
    return {"status": "deleted"}
```

#### 10.3 Full-Text Search

**Purpose:** Search across all logs, transcripts, threads, entities.

**Features:**
- Global search box
- Filter by type (logs, threads, entities)
- Filter by date range
- Recent searches
- Search highlighting in results

```typescript
// src/components/common/GlobalSearch.tsx
'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, X } from 'lucide-react'

export function GlobalSearch() {
  const [query, setQuery] = useState('')
  const [isOpen, setIsOpen] = useState(false)
  
  const { data: results, isLoading } = useQuery({
    queryKey: ['search', query],
    queryFn: async () => {
      if (!query) return []
      const res = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=10`)
      return res.json()
    },
    enabled: query.length > 2,
  })
  
  return (
    <div className="relative w-64">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={16} />
        <input
          type="text"
          placeholder="Search..."
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setIsOpen(true)
          }}
          className="w-full pl-9 pr-8 py-2 bg-slate-800 border border-slate-700 rounded text-sm"
        />
        {query && (
          <button
            onClick={() => setQuery('')}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1 hover:bg-slate-700 rounded"
          >
            <X size={14} />
          </button>
        )}
      </div>
      
      {isOpen && query && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-slate-900 border border-slate-800 rounded shadow-lg z-50 max-h-80 overflow-auto">
          {isLoading ? (
            <div className="p-4 text-slate-500 text-sm">Searching...</div>
          ) : results && results.length > 0 ? (
            <div className="space-y-1 p-1">
              {results.map((result: any) => (
                <SearchResult 
                  key={`${result.type}-${result.id}`} 
                  result={result}
                  query={query}
                  onSelect={() => setIsOpen(false)}
                />
              ))}
            </div>
          ) : (
            <div className="p-4 text-slate-500 text-sm">No results</div>
          )}
        </div>
      )}
    </div>
  )
}

function SearchResult({ 
  result, 
  query, 
  onSelect 
}: { 
  result: any
  query: string
  onSelect: () => void
}) {
  const highlight = (text: string) => {
    const regex = new RegExp(`(${query})`, 'gi')
    const parts = text.split(regex)
    return parts.map((part, i) => 
      regex.test(part) 
        ? <span key={i} className="bg-amber-900">{part}</span>
        : part
    )
  }
  
  return (
    <a
      href={`/${result.type}/${result.id}`}
      onClick={onSelect}
      className="block px-3 py-2 hover:bg-slate-800 transition text-sm"
    >
      <div className="text-slate-300">{highlight(result.title)}</div>
      <div className="text-xs text-slate-500">{result.type}</div>
    </a>
  )
}
```

**Backend:**

```python
# app/api/search.py

from fastapi import APIRouter, Query
from sqlalchemy import or_

router = APIRouter()

@router.get("/")
async def search(q: str = Query(..., min_length=2), limit: int = 10):
    """Full-text search across all data"""
    
    # Search threads
    threads = db.session.query(Thread).filter(
        or_(
            Thread.user_input.contains(q),
            Thread.id.contains(q),
        )
    ).limit(limit).all()
    
    # Search logs
    logs = db.session.query(Log).filter(
        or_(
            Log.message.contains(q),
            Log.thread_id.contains(q),
        )
    ).limit(limit).all()
    
    # Search entities
    entities = db.session.query(Entity).filter(
        Entity.name.contains(q)
    ).limit(limit).all()
    
    return [
        *[{'type': 'thread', 'id': t.id, 'title': t.user_input[:100]} for t in threads],
        *[{'type': 'log', 'id': l.id, 'title': l.message[:100]} for l in logs],
        *[{'type': 'entity', 'id': e.id, 'title': e.name} for e in entities],
    ]
```

---

### Week 11: Performance Metrics & Audit Trail

#### 11.1 Performance Metrics Dashboard

**Purpose:** Monitor Mission Control's own performance.

**Metrics:**
- WebSocket connections (current, peak)
- Message throughput (msgs/sec)
- API latency (p50, p95, p99)
- Database query times
- Memory usage
- Error rate
- MCP connection health

```typescript
// src/components/settings/PerformanceMetrics.tsx
'use client'

import { useQuery } from '@tanstack/react-query'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts'

export function PerformanceMetrics() {
  const { data: metrics } = useQuery({
    queryKey: ['performance-metrics'],
    queryFn: () => fetch('/api/metrics').then(r => r.json()),
    refetchInterval: 10000, // Update every 10s
  })
  
  if (!metrics) return <div>Loading metrics...</div>
  
  return (
    <div className="grid grid-cols-4 gap-4 mb-6">
      {/* Summary Cards */}
      <MetricCard 
        label="WebSocket Connections"
        value={metrics.ws_connections}
        peak={metrics.ws_connections_peak}
      />
      <MetricCard 
        label="Msg/Sec"
        value={metrics.throughput}
      />
      <MetricCard 
        label="API Latency (p95)"
        value={`${metrics.api_latency_p95.toFixed(0)}ms`}
      />
      <MetricCard 
        label="Error Rate"
        value={`${(metrics.error_rate * 100).toFixed(2)}%`}
      />
      
      {/* Graphs */}
      <div className="col-span-2 bg-slate-900 border border-slate-800 rounded p-4">
        <h3 className="text-sm font-medium mb-4">Latency Trend (5m)</h3>
        <LineChart width={400} height={200} data={metrics.latency_trend}>
          <CartesianGrid stroke="#334155" />
          <XAxis dataKey="time" />
          <YAxis />
          <Tooltip />
          <Line type="monotone" dataKey="p50" stroke="#3b82f6" />
          <Line type="monotone" dataKey="p95" stroke="#f59e0b" />
          <Line type="monotone" dataKey="p99" stroke="#ef4444" />
        </LineChart>
      </div>
      
      <div className="col-span-2 bg-slate-900 border border-slate-800 rounded p-4">
        <h3 className="text-sm font-medium mb-4">Throughput (5m)</h3>
        <LineChart width={400} height={200} data={metrics.throughput_trend}>
          <CartesianGrid stroke="#334155" />
          <XAxis dataKey="time" />
          <YAxis />
          <Tooltip />
          <Line type="monotone" dataKey="msgs_per_sec" stroke="#10b981" />
        </LineChart>
      </div>
    </div>
  )
}

function MetricCard({ label, value, peak }: { label: string; value: any; peak?: number }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded p-4">
      <div className="text-xs text-slate-500 mb-2">{label}</div>
      <div className="text-2xl font-bold">{value}</div>
      {peak && <div className="text-xs text-slate-500 mt-1">Peak: {peak}</div>}
    </div>
  )
}
```

**Backend Instrumentation:**

```python
# app/services/metrics.py

from prometheus_client import Counter, Histogram, Gauge
from datetime import datetime, timedelta

# Define metrics
ws_connections = Gauge('mc_ws_connections', 'Active WebSocket connections')
message_throughput = Counter('mc_messages_total', 'Total messages processed')
api_latency = Histogram('mc_api_latency_seconds', 'API request latency')
error_rate = Counter('mc_errors_total', 'Total errors')

class MetricsCollector:
    def get_metrics(self):
        return {
            'ws_connections': ws_connections._value.get(),
            'throughput': self._calculate_throughput(),
            'api_latency_p95': self._get_api_latency_percentile(0.95),
            'error_rate': self._calculate_error_rate(),
            'latency_trend': self._get_trend('latency', minutes=5),
            'throughput_trend': self._get_trend('throughput', minutes=5),
        }
```

#### 11.2 Audit Trail Browser

**Purpose:** Comprehensive log of all actions, permission checks, and events.

**Features:**
- Chronological list of all events
- Filter by type, user, resource
- Export audit log
- Search audit log
- Highlight suspicious activity

```typescript
// src/components/settings/AuditTrail.tsx
'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle } from 'lucide-react'

interface AuditEvent {
  id: string
  timestamp: string
  type: string  // 'permission_check', 'tool_call', 'thread_created', etc
  user: string
  resource: string
  action: string
  status: 'success' | 'denied' | 'error'
  severity: 'info' | 'warn' | 'critical'
  details: Record<string, any>
}

export function AuditTrail() {
  const [filters, setFilters] = useState({
    type: '',
    severity: '',
    fromDate: '',
    toDate: '',
  })
  
  const { data: events, isLoading } = useQuery({
    queryKey: ['audit-trail', filters],
    queryFn: async () => {
      const params = new URLSearchParams()
      Object.entries(filters).forEach(([k, v]) => {
        if (v) params.append(k, v)
      })
      const res = await fetch(`/api/audit?${params}`)
      return res.json()
    },
  })
  
  return (
    <div className="flex flex-col h-full">
      {/* Filters */}
      <div className="p-4 border-b border-slate-800 space-y-2">
        <div className="grid grid-cols-4 gap-2">
          <select
            value={filters.type}
            onChange={(e) => setFilters(f => ({ ...f, type: e.target.value }))}
            className="px-2 py-1 bg-slate-800 border border-slate-700 rounded text-sm"
          >
            <option value="">All Types</option>
            <option value="permission_check">Permission Check</option>
            <option value="tool_call">Tool Call</option>
            <option value="thread_created">Thread Created</option>
            <option value="error">Error</option>
          </select>
          
          <select
            value={filters.severity}
            onChange={(e) => setFilters(f => ({ ...f, severity: e.target.value }))}
            className="px-2 py-1 bg-slate-800 border border-slate-700 rounded text-sm"
          >
            <option value="">All Severities</option>
            <option value="info">Info</option>
            <option value="warn">Warning</option>
            <option value="critical">Critical</option>
          </select>
          
          <input
            type="date"
            value={filters.fromDate}
            onChange={(e) => setFilters(f => ({ ...f, fromDate: e.target.value }))}
            className="px-2 py-1 bg-slate-800 border border-slate-700 rounded text-sm"
          />
          
          <input
            type="date"
            value={filters.toDate}
            onChange={(e) => setFilters(f => ({ ...f, toDate: e.target.value }))}
            className="px-2 py-1 bg-slate-800 border border-slate-700 rounded text-sm"
          />
        </div>
      </div>
      
      {/* Events List */}
      <div className="flex-1 overflow-auto">
        {isLoading ? (
          <div className="p-4 text-slate-500">Loading audit trail...</div>
        ) : events && events.length > 0 ? (
          <div className="divide-y divide-slate-800">
            {events.map((event: AuditEvent) => (
              <AuditEventRow key={event.id} event={event} />
            ))}
          </div>
        ) : (
          <div className="p-4 text-slate-500">No audit events</div>
        )}
      </div>
    </div>
  )
}

function AuditEventRow({ event }: { event: AuditEvent }) {
  const statusColor = {
    success: 'text-green-400',
    denied: 'text-red-400',
    error: 'text-red-500',
  }[event.status]
  
  const severityIcon = event.severity === 'critical' && <AlertTriangle size={14} />
  
  return (
    <div className="p-3 hover:bg-slate-900/50 transition">
      <div className="flex items-start justify-between mb-2">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            {severityIcon}
            <span className="font-medium text-sm">{event.type}</span>
            <span className="text-xs text-slate-500">{event.timestamp}</span>
          </div>
          <div className="text-sm text-slate-400 mt-1">
            {event.action} {event.resource}
          </div>
        </div>
        <span className={`text-sm font-medium ${statusColor}`}>
          {event.status}
        </span>
      </div>
      {event.details && Object.keys(event.details).length > 0 && (
        <details className="text-xs text-slate-500">
          <summary className="cursor-pointer">Details</summary>
          <pre className="mt-2 bg-slate-950 p-2 rounded overflow-auto text-xs">
            {JSON.stringify(event.details, null, 2)}
          </pre>
        </details>
      )}
    </div>
  )
}
```

---

## Production Hardening

### Security

1. **Authentication:** JWT tokens with refresh
2. **HTTPS/WSS:** Encrypted connections
3. **CORS:** Strict origin validation
4. **Rate Limiting:** Per-user request limits
5. **Data Masking:** Redact sensitive data in logs
6. **Access Control:** RBAC for viewing/exporting

### Resilience

1. **Connection Pooling:** Database connection limits
2. **Circuit Breaker:** Fail gracefully if backend fails
3. **Retry Logic:** Exponential backoff on errors
4. **Timeouts:** All operations timeout
5. **Graceful Degradation:** Show cached data if fresh unavailable

### Monitoring

1. **Prometheus Metrics:** Export for monitoring
2. **Health Checks:** `/health` endpoints
3. **Error Tracking:** Sentry integration optional
4. **Logging:** Structured JSON logs
5. **Alerting:** Alert on error rate spike

---

## Documentation

### User Documentation
- Getting Started guide
- Dashboard walkthrough
- Thread inspection guide
- Advanced search tips
- Keyboard shortcuts reference
- FAQ

### API Documentation
- OpenAPI/Swagger spec at `/docs`
- WebSocket message reference
- Rate limiting info
- Authentication guide
- Code examples

### Deployment Guide
- Docker Compose setup
- Kubernetes deployment
- Environment variables
- Database migration
- Backup & restore
- Troubleshooting

---

## Testing

### Integration Tests
```typescript
// e2e/export.spec.ts
test('export logs as CSV', async ({ page }) => {
  await page.goto('/logs')
  await page.click('[aria-label="Export"]')
  await page.click('text=CSV')
  // Verify download
})
```

### Load Tests
```python
# load_test.py
from locust import HttpUser, task, between

class MissionControlUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def get_threads(self):
        self.client.get("/api/threads")
    
    @task
    def stream_logs(self):
        # WebSocket connection
        pass
```

---

## Launch Checklist

- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] Load tests completed (1000 concurrent users)
- [ ] Security audit completed
- [ ] Documentation complete
- [ ] Deployment guide tested
- [ ] Monitoring configured
- [ ] Backup strategy defined
- [ ] Disaster recovery tested
- [ ] Performance targets met (< 100ms latency, 99.9% uptime)

---

## Success Metrics

By end of Phase 17:

- [ ] Export working for all formats
- [ ] Saved views functioning
- [ ] Global search working < 500ms
- [ ] Performance dashboard showing real metrics
- [ ] Complete audit trail visible & searchable
- [ ] 95%+ test coverage
- [ ] Zero critical security issues
- [ ] Production-ready deployment
- [ ] Full documentation
- [ ] Ready for GA release

---

## Future Enhancements (Phase 18+)

- AI-assisted debugging (anomaly detection)
- Time-travel debugging (replay execution)
- Collaborative debugging (multiple users)
- Advanced analytics (trends, forecasting)
- Integration with external monitoring (DataDog, New Relic)
- Mobile app for monitoring on-the-go
- Slack/Discord alerts
- Custom alerting rules
