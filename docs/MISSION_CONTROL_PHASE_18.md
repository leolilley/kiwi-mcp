# Phase 18: Embedded Kiwi MCP & Self-Management

**Duration:** 3 weeks  
**Status:** Planning  
**Last Updated:** 2026-01-22

---

## Overview

Phase 18 embeds a **Kiwi MCP instance directly into Mission Control**, enabling the platform to:

1. **Self-manage** → Use directives to automate its own operations
2. **Self-heal** → Detect issues and execute recovery directives
3. **Self-improve** → Learn from patterns and optimize behavior
4. **Intelligent automation** → Run complex tasks via directive orchestration
5. **Extensibility** → Users can write custom directives for their workflows

**Core Insight:** Mission Control becomes a Kiwi MCP _client_ and _orchestrator_, using the same directive-driven approach to manage itself that it uses to observe external MCPs.

---

## Architecture: Recursive MCP Design

```
┌────────────────────────────────────────────────────────────┐
│                    MISSION CONTROL                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              UI Layer (React)                        │  │
│  │  Dashboard | Inspector | Logs | Terminal            │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │        DIRECTIVE EXECUTION LAYER (NEW)               │  │
│  │  ┌─────────────────────────────────────────────────┐ │  │
│  │  │   Embedded Kiwi MCP (Internal)                  │ │  │
│  │  │   ┌─────────────────┐  ┌─────────────────────┐ │ │  │
│  │  │   │  Directives     │  │  Scripts            │ │ │  │
│  │  │   │  (self-manage)  │  │  (auto-healing)     │ │ │  │
│  │  │   └─────────────────┘  └─────────────────────┘ │ │  │
│  │  │                                                 │ │  │
│  │  │   ┌──────────────────────────────────────────┐ │ │  │
│  │  │   │  Knowledge Base (patterns, learnings)    │ │ │  │
│  │  │   └──────────────────────────────────────────┘ │ │  │
│  │  └─────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          OBSERVATION LAYER                          │  │
│  │  WebSocket Server | Log Aggregator | Query API      │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │          EXTERNAL MCPs                              │  │
│  │  MCP #1 | MCP #2 | MCP #N                           │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

---

## Phase 18 Breakdown

### Week 1: Embed Kiwi MCP

**Goals:**

- [ ] Integrate Kiwi MCP core into Mission Control backend
- [ ] Create internal directive registry
- [ ] Create internal script registry
- [ ] Build internal knowledge base
- [ ] Wire up directive execution to backend services

**Deliverables:**

#### 1.1 Internal Kiwi MCP Instance

```python
# app/kiwi_mcp/internal_mcp.py

from kiwi_mcp import KiwiMCP, DirectiveRegistry, ScriptRegistry
from app.services import session_manager, log_aggregator, query_api

class InternalKiwiMCP:
    """Kiwi MCP instance running inside Mission Control"""

    def __init__(self):
        self.mcp = KiwiMCP()
        self.directive_registry = DirectiveRegistry()
        self.script_registry = ScriptRegistry()
        self.knowledge_base = KnowledgeBase()

    async def initialize(self):
        """Load built-in directives, scripts, knowledge"""
        # Load system directives
        await self.directive_registry.load_system_directives([
            'monitor_thread_health',
            'detect_anomalies',
            'optimize_log_retention',
            'cleanup_stale_sessions',
            'heal_mcp_connection',
            'generate_performance_report',
            'analyze_permission_patterns',
        ])

        # Load system scripts
        await self.script_registry.load_system_scripts([
            'detect_slow_threads',
            'find_permission_escalations',
            'cleanup_old_logs',
            'generate_summary',
        ])

    async def execute_directive(
        self,
        directive_name: str,
        inputs: dict,
        context: dict = None
    ):
        """Execute a directive with access to Mission Control services"""
        # Directives have access to:
        # - session_manager (threads)
        # - log_aggregator (logs)
        # - query_api (historical data)
        # - mcp_gateway (external MCPs)

        return await self.mcp.execute(
            directive_name=directive_name,
            inputs=inputs,
            context={
                **(context or {}),
                'session_manager': session_manager,
                'log_aggregator': log_aggregator,
                'query_api': query_api,
            }
        )

internal_mcp = InternalKiwiMCP()
```

#### 1.2 System Directives

```yaml
# app/kiwi_mcp/directives/monitor_thread_health.yaml

name: monitor_thread_health
version: 1.0.0
description: Monitor active threads and detect stalled/crashed ones

inputs:
  check_interval:
    type: integer
    description: Check interval in seconds
    default: 60

permissions:
  - read:threads
  - write:logs

steps:
  - name: fetch_active_threads
    script: query_active_threads.py

  - name: check_each_thread
    foreach: active_threads
    steps:
      - script: check_thread_health.py
        inputs:
          thread_id: "{{ item.id }}"
          timeout_seconds: 300

      - conditional:
          if: "{{ result.status == 'stalled' }}"
          then:
            script: alert_stalled_thread.py
            inputs:
              thread_id: "{{ item.id }}"

  - name: log_summary
    script: log_health_check.py
    inputs:
      healthy: "{{ healthy_count }}"
      stalled: "{{ stalled_count }}"
      failed: "{{ failed_count }}"
```

#### 1.3 System Scripts

```python
# app/kiwi_mcp/scripts/detect_slow_threads.py

import asyncio
from typing import List
from app.services import query_api

async def execute(context: dict, params: dict) -> dict:
    """
    Detect threads that are running slower than P95.
    Returns list of slow threads for investigation.
    """

    # Get recent thread metrics
    threads = await query_api.get_threads_with_metrics(
        limit=100,
        order_by='duration',
    )

    # Calculate P95 duration
    durations = [t['duration_ms'] for t in threads if t['duration_ms']]
    durations.sort()
    p95_duration = durations[int(len(durations) * 0.95)]

    # Find slow threads (above P95 * 1.5)
    slow_threads = [
        t for t in threads
        if t['duration_ms'] > (p95_duration * 1.5)
    ]

    # Log finding
    context['log_aggregator'].ingest_log({
        'level': 'WARN' if len(slow_threads) > 5 else 'INFO',
        'message': f"Detected {len(slow_threads)} slow threads (>{p95_duration * 1.5}ms)",
        'context': {
            'p95_duration': p95_duration,
            'slow_thread_ids': [t['id'] for t in slow_threads],
        }
    })

    return {
        'slow_threads': slow_threads,
        'p95_duration': p95_duration,
        'count': len(slow_threads),
    }
```

---

### Week 2: Self-Management Workflows

**Goals:**

- [ ] Implement automatic health monitoring
- [ ] Implement automatic cleanup routines
- [ ] Implement performance optimization
- [ ] Implement anomaly detection
- [ ] Build admin dashboard to manage internal operations

**Deliverables:**

#### 2.1 Automatic Health Monitoring

```python
# app/services/health_monitor.py

from datetime import datetime, timedelta
import asyncio

class HealthMonitor:
    """Automatic health monitoring & self-healing"""

    def __init__(self, internal_mcp):
        self.internal_mcp = internal_mcp
        self.check_interval = 60  # seconds

    async def start(self):
        """Start background health checks"""
        while True:
            try:
                await self.run_health_checks()
            except Exception as e:
                print(f"Health check error: {e}")

            await asyncio.sleep(self.check_interval)

    async def run_health_checks(self):
        """Execute health monitoring directives"""

        # Check 1: Monitor thread health
        await self.internal_mcp.execute_directive(
            'monitor_thread_health',
            inputs={'check_interval': self.check_interval}
        )

        # Check 2: Detect anomalies
        anomalies = await self.internal_mcp.execute_directive(
            'detect_anomalies',
            inputs={'lookback_minutes': 10}
        )

        if anomalies['count'] > 0:
            # Automatically alert
            await self._send_alert(anomalies)

        # Check 3: Monitor log growth
        await self.internal_mcp.execute_directive(
            'optimize_log_retention',
            inputs={'max_age_days': 7}
        )

        # Check 4: Cleanup stale sessions
        await self.internal_mcp.execute_directive(
            'cleanup_stale_sessions',
            inputs={'timeout_hours': 24}
        )

    async def _send_alert(self, anomalies: dict):
        """Send alert to users about detected anomalies"""
        # Could integrate with Slack, email, etc
        pass
```

#### 2.2 Self-Healing Directives

```yaml
# app/kiwi_mcp/directives/heal_mcp_connection.yaml

name: heal_mcp_connection
version: 1.0.0
description: Detect and heal broken MCP connections

inputs:
  mcp_id:
    type: string
    description: MCP instance to heal

permissions:
  - read:mcps
  - write:logs
  - execute:mcp_gateway

steps:
  - name: check_status
    script: check_mcp_status.py
    inputs:
      mcp_id: "{{ inputs.mcp_id }}"

  - conditional:
      if: "{{ result.status == 'disconnected' }}"
      then:
        - name: attempt_reconnect
          script: reconnect_mcp.py
          inputs:
            mcp_id: "{{ inputs.mcp_id }}"
            max_attempts: 3
            backoff_seconds: 5

        - conditional:
            if: "{{ result.success }}"
            then:
              - name: notify_recovery
                script: log_recovery.py
                inputs:
                  mcp_id: "{{ inputs.mcp_id }}"
                  message: "MCP reconnected successfully"
            else:
              - name: notify_failure
                script: log_failure.py
                inputs:
                  mcp_id: "{{ inputs.mcp_id }}"
                  message: "Failed to reconnect MCP after 3 attempts"
                  escalate: true
```

#### 2.3 Admin Dashboard for Internal Operations

```typescript
// src/components/admin/InternalOperations.tsx
'use client'

import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'

export function InternalOperations() {
  const [selectedDirective, setSelectedDirective] = useState('')

  const { data: directives } = useQuery({
    queryKey: ['internal-directives'],
    queryFn: () => fetch('/api/internal/directives').then(r => r.json()),
  })

  const { data: executionHistory } = useQuery({
    queryKey: ['internal-executions'],
    queryFn: () => fetch('/api/internal/executions').then(r => r.json()),
  })

  const executeMutation = useMutation({
    mutationFn: async (directiveName: string) => {
      const res = await fetch('/api/internal/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ directive_name: directiveName }),
      })
      return res.json()
    },
  })

  return (
    <div className="grid grid-cols-2 gap-4">
      {/* Available Directives */}
      <div className="bg-slate-900 border border-slate-800 rounded p-4">
        <h3 className="font-semibold mb-4">Available Directives</h3>
        <div className="space-y-2">
          {directives?.map(d => (
            <button
              key={d.name}
              onClick={() => executeMutation.mutate(d.name)}
              disabled={executeMutation.isPending}
              className="w-full text-left px-3 py-2 bg-slate-800 hover:bg-slate-700 rounded text-sm transition"
            >
              <div className="font-medium">{d.name}</div>
              <div className="text-xs text-slate-500">{d.description}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Execution History */}
      <div className="bg-slate-900 border border-slate-800 rounded p-4">
        <h3 className="font-semibold mb-4">Recent Executions</h3>
        <div className="space-y-2 text-sm">
          {executionHistory?.map((exec: any) => (
            <div key={exec.id} className="bg-slate-800 p-2 rounded">
              <div className="font-medium">{exec.directive_name}</div>
              <div className="text-xs text-slate-500">
                {exec.status === 'success' ? '✓' : '✗'} {exec.executed_at}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
```

---

### Week 3: Advanced Self-Management Features

**Goals:**

- [ ] Intelligent performance optimization
- [ ] Pattern learning & adaptation
- [ ] Predictive maintenance
- [ ] User-defined automation workflows
- [ ] Internal knowledge base builder

**Deliverables:**

#### 3.1 Performance Optimization Directive

```python
# app/kiwi_mcp/scripts/optimize_queries.py

import asyncio
from app.services import query_api
from app.database import db_session

async def execute(context: dict, params: dict) -> dict:
    """
    Analyze slow queries and suggest optimizations.
    Auto-apply safe optimizations (indexes, etc).
    """

    slow_queries = await query_api.get_slow_queries(
        threshold_ms=1000,
        limit=10,
    )

    optimizations = []

    for query_info in slow_queries:
        # Analyze query plan
        plan = await db_session.execute(
            f"EXPLAIN ANALYZE {query_info['query']}"
        )

        # Suggest index if missing
        missing_indexes = await _suggest_indexes(plan)
        for idx in missing_indexes:
            optimizations.append({
                'type': 'create_index',
                'table': idx['table'],
                'columns': idx['columns'],
                'estimated_improvement': idx['est_improvement'],
            })

        # Log suggestion
        context['log_aggregator'].ingest_log({
            'level': 'INFO',
            'message': f"Query optimization suggestion: {idx['table']}.{idx['columns']}",
            'context': {
                'query': query_info['query'][:200],
                'current_duration_ms': query_info['duration_ms'],
                'estimated_duration_ms': query_info['duration_ms'] / (1 + idx['est_improvement']),
            }
        })

    return {
        'optimization_count': len(optimizations),
        'optimizations': optimizations,
    }

async def _suggest_indexes(plan: dict) -> list:
    """Analyze query plan and suggest missing indexes"""
    # Implementation uses EXPLAIN output
    pass
```

#### 3.2 Pattern Learning Directive

```yaml
# app/kiwi_mcp/directives/analyze_patterns.yaml

name: analyze_patterns
version: 1.0.0
description: Analyze thread patterns and learn from them

inputs:
  lookback_days:
    type: integer
    default: 30

permissions:
  - read:threads
  - read:logs
  - write:knowledge

steps:
  - name: fetch_threads
    script: fetch_thread_patterns.py
    inputs:
      days: "{{ inputs.lookback_days }}"

  - name: analyze_patterns
    script: ml_pattern_analyzer.py
    inputs:
      threads: "{{ result.threads }}"
      analysis_types:
        - execution_duration_distribution
        - permission_denial_patterns
        - mcp_connection_failures
        - error_clusters

  - name: store_learnings
    script: store_knowledge_entry.py
    inputs:
      patterns: "{{ result.patterns }}"
      confidence_scores: "{{ result.confidence }}"

  - name: generate_recommendations
    script: generate_recommendations.py
    inputs:
      patterns: "{{ result.patterns }}"
      output:
        - performance_tips
        - common_errors
        - permission_best_practices
```

#### 3.3 User-Defined Automation

Users can create custom automation workflows in the UI:

```typescript
// src/components/admin/AutomationBuilder.tsx
'use client'

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'

export function AutomationBuilder() {
  const [automation, setAutomation] = useState({
    name: '',
    trigger: 'schedule',  // 'schedule', 'alert', 'event'
    schedule: '0 * * * *',  // Cron format
    directive: '',
    enabled: true,
  })

  const saveMutation = useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/internal/automations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(automation),
      })
      return res.json()
    },
  })

  return (
    <div className="space-y-4 max-w-md">
      <div>
        <label className="text-sm font-medium">Automation Name</label>
        <input
          type="text"
          value={automation.name}
          onChange={(e) => setAutomation(a => ({ ...a, name: e.target.value }))}
          className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm mt-1"
          placeholder="e.g., Daily Performance Analysis"
        />
      </div>

      <div>
        <label className="text-sm font-medium">Trigger Type</label>
        <select
          value={automation.trigger}
          onChange={(e) => setAutomation(a => ({ ...a, trigger: e.target.value }))}
          className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm mt-1"
        >
          <option value="schedule">Schedule (Cron)</option>
          <option value="alert">On Alert</option>
          <option value="event">On Event</option>
        </select>
      </div>

      {automation.trigger === 'schedule' && (
        <div>
          <label className="text-sm font-medium">Cron Schedule</label>
          <input
            type="text"
            value={automation.schedule}
            onChange={(e) => setAutomation(a => ({ ...a, schedule: e.target.value }))}
            className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm mt-1"
            placeholder="0 * * * * (hourly)"
          />
        </div>
      )}

      <div>
        <label className="text-sm font-medium">Directive to Execute</label>
        <select
          value={automation.directive}
          onChange={(e) => setAutomation(a => ({ ...a, directive: e.target.value }))}
          className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm mt-1"
        >
          <option value="">Select a directive...</option>
          <option value="analyze_patterns">Analyze Patterns</option>
          <option value="optimize_queries">Optimize Queries</option>
          <option value="monitor_thread_health">Monitor Thread Health</option>
        </select>
      </div>

      <button
        onClick={() => saveMutation.mutate()}
        disabled={!automation.name || !automation.directive || saveMutation.isPending}
        className="w-full px-4 py-2 bg-blue-700 hover:bg-blue-600 rounded transition disabled:opacity-50"
      >
        {saveMutation.isPending ? 'Saving...' : 'Create Automation'}
      </button>
    </div>
  )
}
```

---

## API Endpoints (New)

```python
# app/api/internal.py

from fastapi import APIRouter
from app.kiwi_mcp.internal_mcp import internal_mcp

router = APIRouter(prefix="/internal")

@router.get("/directives")
async def list_directives():
    """List available internal directives"""
    return await internal_mcp.directive_registry.list_all()

@router.get("/scripts")
async def list_scripts():
    """List available internal scripts"""
    return await internal_mcp.script_registry.list_all()

@router.post("/execute")
async def execute_directive(request: ExecuteRequest):
    """Execute a directive manually"""
    result = await internal_mcp.execute_directive(
        directive_name=request.directive_name,
        inputs=request.inputs or {},
    )
    return result

@router.get("/executions")
async def list_executions(limit: int = 50):
    """List recent directive executions"""
    # Query execution history from database
    return []

@router.post("/automations")
async def create_automation(request: AutomationRequest):
    """Create new automation workflow"""
    # Save automation rule, will be triggered by scheduler
    return {}

@router.get("/knowledge")
async def list_knowledge():
    """List learned patterns & insights"""
    return await internal_mcp.knowledge_base.list_all()
```

---

## Database Tables

```sql
-- Directive executions
CREATE TABLE directive_executions (
    id TEXT PRIMARY KEY,
    directive_name TEXT NOT NULL,
    triggered_by TEXT,  -- 'manual', 'schedule', 'alert'
    inputs JSONB,
    result JSONB,
    status TEXT,  -- 'pending', 'running', 'success', 'error'
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Automations
CREATE TABLE automations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    directive_name TEXT NOT NULL,
    trigger_type TEXT,  -- 'schedule', 'alert', 'event'
    schedule TEXT,      -- Cron format
    enabled BOOLEAN DEFAULT true,
    last_executed_at TIMESTAMP,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- Internal knowledge/learnings
CREATE TABLE internal_knowledge (
    id TEXT PRIMARY KEY,
    title TEXT,
    category TEXT,  -- 'pattern', 'optimization', 'alert', 'best_practice'
    content TEXT,
    confidence FLOAT,
    source TEXT,    -- Which directive discovered this
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX idx_directive_executions_name ON directive_executions(directive_name);
CREATE INDEX idx_directive_executions_status ON directive_executions(status);
CREATE INDEX idx_automations_enabled ON automations(enabled);
```

---

## Integration with External MCPs

The embedded Kiwi MCP can also orchestrate external MCPs:

```yaml
# Example: Cross-MCP coordination directive

name: coordinate_mcps
version: 1.0.0
description: Coordinate work across multiple MCP instances

steps:
  - name: check_all_mcps
    script: check_mcp_health.py

  - name: load_balance
    foreach: healthy_mcps
    steps:
      - script: assign_work_to_mcp.py
        inputs:
          mcp_id: "{{ item.id }}"
          work_type: "log_ingestion"
```

---

## Benefits of Embedded Kiwi MCP

1. **Self-Awareness** → Mission Control understands its own state & constraints
2. **Automation** → Complex tasks automated via directives
3. **Extensibility** → Users write custom workflows
4. **Learning** → System learns from patterns & optimizes itself
5. **Resilience** → Can heal itself without human intervention
6. **Transparency** → All internal operations visible, auditable

---

## Success Metrics (Phase 18)

By end of Week 3:

- [ ] Embedded Kiwi MCP fully integrated
- [ ] 5+ system directives operational
- [ ] Automatic health monitoring running
- [ ] Self-healing workflows tested
- [ ] Admin dashboard functional
- [ ] User can create custom automations
- [ ] Internal knowledge base growing
- [ ] > 90% test coverage

---

## Open Questions

1. Should embedded MCP have separate permission scope from external MCPs?
2. Can users modify/delete system directives, or read-only?
3. How to prevent runaway automation (e.g., infinite loops)?
4. Should internal operations be visible in audit trail?
5. Can internal MCP delegate work to external MCPs?

---

## Next: Phase 19+ Vision

Phase 18 enables deeper features:

- **Phase 19: AI-Assisted Debugging** → Use ML to detect anomalies & suggest fixes
- **Phase 20: Predictive Optimization** → Forecast issues before they occur
- **Phase 21: Collaborative Intelligence** → Learn from patterns across users
- **Phase 22: Advanced Analytics** → Time-series analysis, trend detection

See [Phase 19 Vision](./MISSION_CONTROL_PHASE_19.md) for details.
