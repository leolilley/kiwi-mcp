# Phase 16: Visualization & Graphs

**Duration:** 2 weeks (Weeks 8-9)  
**Status:** Planning  
**Last Updated:** 2026-01-22  

---

## Overview

Phase 16 transforms Mission Control from a monitoring tool into a comprehensive visualization platform. It enables deep exploration of system relationships, execution flows, and permission hierarchies through interactive visualizations.

**Core Screens:**
- **Relationship Graph:** Directives, scripts, knowledge, and their connections
- **DB Schema Explorer:** Browse all entities, search, filter
- **Execution Timeline:** Per-thread execution flow with flamegraph
- **Permission Flow:** Visualize permission checks and inheritance

**Key Goal:** Visualize complex system relationships in ways that enable quick understanding and debugging.

---

## Visualization Components

### 1. Relationship Graph

**Purpose:** Show how directives, scripts, knowledge items, and permissions interconnect.

**Features:**
- Interactive node-and-edge graph
- Zoom, pan, drag, search
- Color-coded by type (directive=blue, script=green, knowledge=orange)
- Glow effect for validated items
- Click node to inspect
- Click edge to show relationship details
- Hover to highlight connections

**Technology:** Cytoscape.js

```typescript
// src/components/graph/RelationshipGraph.tsx
'use client'

import { useEffect, useRef } from 'react'
import cytoscape from 'cytoscape'

interface GraphNode {
  id: string
  label: string
  type: 'directive' | 'script' | 'knowledge'
  validated: boolean
  scope: 'project' | 'user' | 'registry'
}

interface GraphEdge {
  source: string
  target: string
  type: string // 'uses', 'references', 'inherits', etc
}

export function RelationshipGraph({ 
  nodes, 
  edges 
}: { 
  nodes: GraphNode[]
  edges: GraphEdge[]
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<cytoscape.Core | null>(null)
  
  useEffect(() => {
    if (!containerRef.current) return
    
    const cy = cytoscape({
      container: containerRef.current,
      elements: [
        ...nodes.map(n => ({
          data: {
            id: n.id,
            label: n.label,
            type: n.type,
            validated: n.validated,
          },
        })),
        ...edges.map(e => ({
          data: {
            source: e.source,
            target: e.target,
            type: e.type,
          },
        })),
      ],
      style: [
        {
          selector: 'node',
          style: {
            'background-color': (node: any) => {
              const type = node.data('type')
              if (type === 'directive') return '#3b82f6'
              if (type === 'script') return '#10b981'
              if (type === 'knowledge') return '#f59e0b'
              return '#64748b'
            },
            'label': 'data(label)',
            'width': '50px',
            'height': '50px',
            'font-size': '12px',
            'text-halign': 'center',
            'text-valign': 'center',
            'color': '#ffffff',
            'border-width': (node: any) => node.data('validated') ? 2 : 0,
            'border-color': '#10b981',
            'box-shadow': (node: any) => 
              node.data('validated') ? '0 0 20px rgba(16, 185, 129, 0.8)' : 'none',
          },
        },
        {
          selector: 'edge',
          style: {
            'line-color': '#64748b',
            'target-arrow-color': '#64748b',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            'width': '2px',
          },
        },
        {
          selector: 'node:selected',
          style: {
            'background-color': '#fbbf24',
            'box-shadow': '0 0 30px rgba(251, 191, 36, 1)',
          },
        },
      ],
      layout: {
        name: 'cose',
        directed: true,
        animate: false,
        animationDuration: 0,
      },
    })
    
    // Interactions
    cy.on('tap', 'node', (evt) => {
      const node = evt.target
      // Show node details in panel
      console.log('Selected:', node.data())
    })
    
    // Zoom/pan controls
    cy.userZoomingEnabled(true)
    cy.userPanningEnabled(true)
    
    cyRef.current = cy
    
    return () => cy.destroy()
  }, [nodes, edges])
  
  return (
    <div 
      ref={containerRef} 
      className="w-full h-full bg-slate-950 rounded-lg"
    />
  )
}
```

**Data Source:**

```typescript
// src/services/graphQuery.ts
export async function fetchRelationshipGraph(scope?: string) {
  const response = await fetch(`/api/graph/entities?scope=${scope || 'all'}`)
  const { nodes, edges } = await response.json()
  return { nodes, edges }
}
```

---

### 2. DB Schema Explorer

**Purpose:** Browse the complete entity database, with filtering and search.

**Features:**
- Tabbed interface (Directives, Scripts, Knowledge)
- Search by name, type, scope
- Filter by validation status, scope, modified date
- Card view with metadata
- Click to view full details
- Relationship badges showing connections

```typescript
// src/components/graph/SchemaExplorer.tsx
'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'

type EntityType = 'directive' | 'script' | 'knowledge'

export function SchemaExplorer() {
  const [tab, setTab] = useState<EntityType>('directive')
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState({
    validated: undefined as boolean | undefined,
    scope: undefined as string | undefined,
  })
  
  const { data: entities, isLoading } = useQuery({
    queryKey: ['entities', tab, search, filters],
    queryFn: async () => {
      const params = new URLSearchParams({
        type: tab,
        search,
        ...(filters.validated !== undefined && { 
          validated: String(filters.validated) 
        }),
        ...(filters.scope && { scope: filters.scope }),
      })
      const res = await fetch(`/api/graph/entities?${params}`)
      return res.json()
    },
  })
  
  return (
    <div className="flex flex-col h-full">
      {/* Search & Filters */}
      <div className="p-4 border-b border-slate-800 space-y-3">
        <input
          type="text"
          placeholder="Search entities..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded text-sm"
        />
        
        <div className="flex gap-2">
          <select 
            value={filters.scope || ''}
            onChange={(e) => setFilters(f => ({ 
              ...f, 
              scope: e.target.value || undefined 
            }))}
            className="px-2 py-1 bg-slate-900 border border-slate-700 rounded text-sm"
          >
            <option value="">All Scopes</option>
            <option value="project">Project</option>
            <option value="user">User</option>
            <option value="registry">Registry</option>
          </select>
          
          <button
            onClick={() => setFilters(f => ({
              ...f,
              validated: f.validated === undefined ? true : 
                        f.validated ? false : undefined
            }))}
            className={`px-3 py-1 rounded text-sm ${
              filters.validated === true 
                ? 'bg-green-600 text-white'
                : filters.validated === false
                ? 'bg-red-600 text-white'
                : 'bg-slate-700 text-slate-300'
            }`}
          >
            Validated {filters.validated === undefined ? '' : 
              filters.validated ? '✓' : '✗'}
          </button>
        </div>
      </div>
      
      {/* Tabs */}
      <div className="flex border-b border-slate-800">
        {(['directive', 'script', 'knowledge'] as EntityType[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 py-2 text-sm font-medium border-b-2 transition ${
              tab === t
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-slate-400 hover:text-slate-300'
            }`}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}s
          </button>
        ))}
      </div>
      
      {/* Results */}
      <div className="flex-1 overflow-auto p-4 space-y-3">
        {isLoading ? (
          <div className="text-slate-500">Loading...</div>
        ) : entities?.length === 0 ? (
          <div className="text-slate-500">No entities found</div>
        ) : (
          entities.map(entity => (
            <EntityCard key={entity.id} entity={entity} />
          ))
        )}
      </div>
    </div>
  )
}

function EntityCard({ entity }: { entity: any }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded p-3 hover:border-slate-700 cursor-pointer transition">
      <div className="flex items-start justify-between mb-2">
        <h4 className="font-medium text-sm">{entity.name}</h4>
        <div className="flex gap-1">
          {entity.validated && (
            <span className="px-2 py-0.5 bg-green-900 text-green-300 rounded text-xs">
              ✓
            </span>
          )}
          <span className="px-2 py-0.5 bg-slate-800 text-slate-300 rounded text-xs">
            {entity.scope}
          </span>
        </div>
      </div>
      <p className="text-xs text-slate-500 mb-2">{entity.description}</p>
      <div className="flex gap-2 text-xs text-slate-400">
        {entity.relationshipCount > 0 && (
          <span>🔗 {entity.relationshipCount} connections</span>
        )}
        <span>Modified {entity.modifiedAgo}</span>
      </div>
    </div>
  )
}
```

---

### 3. Execution Timeline (Flamegraph)

**Purpose:** Visualize the execution flow of a thread with timing and nesting.

**Features:**
- Horizontal timeline showing steps
- Nesting shows parent-child calls (e.g., directive → script → tool call)
- Color-coded by step type
- Hover for details (duration, memory, CPU)
- Click to inspect step details
- Total duration shown
- Bottleneck detection (slow steps highlighted)

```typescript
// src/components/thread/ExecutionTimeline.tsx
'use client'

import { ExecutionStep } from '@/lib/types'

interface TimelineProps {
  steps: ExecutionStep[]
  totalDuration: number
}

export function ExecutionTimeline({ steps, totalDuration }: TimelineProps) {
  return (
    <div className="flex flex-col gap-2">
      {/* Legend */}
      <div className="flex gap-4 text-xs text-slate-400 mb-4">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-blue-500 rounded" />
          <span>Directive</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-green-500 rounded" />
          <span>Script</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-purple-500 rounded" />
          <span>Tool Call</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-amber-500 rounded" />
          <span>Permission</span>
        </div>
      </div>
      
      {/* Timeline */}
      <div className="space-y-1">
        {steps.map((step, idx) => (
          <TimelineStep 
            key={idx} 
            step={step} 
            totalDuration={totalDuration}
          />
        ))}
      </div>
      
      {/* Summary */}
      <div className="text-sm text-slate-400 mt-4">
        Total: {(totalDuration / 1000).toFixed(2)}s
      </div>
    </div>
  )
}

function TimelineStep({ 
  step, 
  totalDuration 
}: { 
  step: ExecutionStep
  totalDuration: number
}) {
  const percentWidth = (step.duration_ms / totalDuration) * 100
  
  const color = {
    'directive': 'bg-blue-500',
    'script': 'bg-green-500',
    'tool_call': 'bg-purple-500',
    'check_permission': 'bg-amber-500',
  }[step.type] || 'bg-slate-500'
  
  return (
    <div className="group">
      <div className="flex items-center gap-2 mb-1">
        <div className="w-24 text-xs text-slate-400">
          {step.sequence}. {step.type}
        </div>
        <div className="flex-1 bg-slate-900 rounded h-6 relative overflow-hidden">
          <div
            className={`${color} h-full rounded transition-all group-hover:opacity-80`}
            style={{ width: `${percentWidth}%` }}
            title={`${step.duration_ms.toFixed(1)}ms`}
          />
        </div>
        <div className="w-16 text-xs text-slate-400 text-right">
          {step.duration_ms.toFixed(1)}ms
        </div>
      </div>
      <p className="text-xs text-slate-500 pl-26">{step.description}</p>
    </div>
  )
}
```

---

### 4. Permission Flow

**Purpose:** Visualize permission checks and inheritance hierarchy.

**Features:**
- Hierarchical tree showing inheritance
- Color: green = granted, red = denied, yellow = warning
- Click to see permission rule details
- Show escalation detection
- Timeline of all permission checks

```typescript
// src/components/graph/PermissionFlow.tsx
'use client'

import { useQuery } from '@tanstack/react-query'

export function PermissionFlow({ threadId }: { threadId: string }) {
  const { data: permissionEvents } = useQuery({
    queryKey: ['permission-events', threadId],
    queryFn: async () => {
      const res = await fetch(`/api/permissions/audit/${threadId}`)
      return res.json()
    },
  })
  
  if (!permissionEvents) return <div>Loading...</div>
  
  return (
    <div className="space-y-3">
      {/* Summary */}
      <div className="bg-slate-900 border border-slate-800 rounded p-3">
        <div className="text-sm font-medium mb-2">Permission Summary</div>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <div className="text-2xl font-bold text-green-400">
              {permissionEvents.filter((e: any) => e.granted).length}
            </div>
            <div className="text-slate-500">Granted</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-red-400">
              {permissionEvents.filter((e: any) => !e.granted).length}
            </div>
            <div className="text-slate-500">Denied</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-amber-400">
              {permissionEvents.filter((e: any) => e.escalation_detected).length}
            </div>
            <div className="text-slate-500">Escalations</div>
          </div>
        </div>
      </div>
      
      {/* Permission Timeline */}
      <div className="space-y-2">
        {permissionEvents.map((event: any, idx: number) => (
          <PermissionEvent key={idx} event={event} />
        ))}
      </div>
    </div>
  )
}

function PermissionEvent({ event }: { event: any }) {
  const statusColor = event.escalation_detected
    ? 'bg-red-900 text-red-300'
    : event.granted
    ? 'bg-green-900 text-green-300'
    : 'bg-red-900 text-red-300'
  
  return (
    <div className="bg-slate-900 border border-slate-800 rounded p-3 text-sm">
      <div className="flex items-start justify-between mb-2">
        <div>
          <div className="font-medium">
            {event.action.toUpperCase()} {event.resource}
          </div>
          <div className="text-xs text-slate-500">{event.reason}</div>
        </div>
        <span className={`px-2 py-1 rounded text-xs font-medium ${statusColor}`}>
          {event.granted ? 'GRANTED' : 'DENIED'}
          {event.escalation_detected && ' ⚠️'}
        </span>
      </div>
      {event.inheritance_chain && event.inheritance_chain.length > 0 && (
        <div className="text-xs text-slate-500">
          Inherited from: {event.inheritance_chain.join(' → ')}
        </div>
      )}
    </div>
  )
}
```

---

## Week 8: Cytoscape & Graph Rendering

**Goals:**
- [ ] Integrate Cytoscape.js
- [ ] Build RelationshipGraph component
- [ ] Implement node/edge styling
- [ ] Add zoom/pan/drag controls
- [ ] Add search functionality
- [ ] Style edges with relationship types

**Tasks:**
1. Fetch graph data from `/api/graph/entities`
2. Render nodes with proper coloring
3. Add click handlers to show node details
4. Implement search with highlighting
5. Test with 1000+ nodes performance

---

## Week 9: Timeline & Permission Visualization

**Goals:**
- [ ] Build ExecutionTimeline component
- [ ] Flamegraph rendering with proper timing
- [ ] PermissionFlow component
- [ ] Permission audit visualization
- [ ] Escalation detection highlighting
- [ ] Integration with Thread Inspector

**Tasks:**
1. Fetch execution steps from `/api/threads/{id}/timeline`
2. Calculate timing and nesting
3. Fetch permission events from `/api/permissions/audit/{id}`
4. Build hierarchical permission tree
5. Highlight escalations
6. Test with complex threads

---

## Performance Considerations

### Graph Rendering

- Lazy load nodes (virtualization for 10k+)
- Use WebGL renderer if > 5k nodes
- Debounce zoom/pan events
- Cache layout calculations

```typescript
// Use Cytoscape WebGL for large graphs
const cy = cytoscape({
  // ... other config
  renderer: { name: 'webgl' }, // Much faster for large graphs
})
```

### Timeline Rendering

- Virtualize long timelines
- Group steps by category
- Collapse/expand sections
- Lazy render step details

---

## Data Models

```typescript
// src/lib/types.ts

export interface GraphEntity {
  id: string
  type: 'directive' | 'script' | 'knowledge'
  name: string
  description: string
  scope: 'project' | 'user' | 'registry'
  validated: boolean
  createdAt: string
  modifiedAt: string
}

export interface GraphRelationship {
  id: string
  source: string
  target: string
  type: string // 'uses', 'references', 'inherits', 'depends_on'
  metadata: Record<string, any>
}

export interface ExecutionStep {
  sequence: number
  timestamp: string
  duration_ms: number
  type: 'directive' | 'script' | 'tool_call' | 'check_permission'
  description: string
  details: Record<string, any>
  status: 'pending' | 'running' | 'complete' | 'error'
}

export interface PermissionEvent {
  id: string
  timestamp: string
  thread_id: string
  resource: string
  action: string
  granted: boolean
  reason: string
  inheritance_chain: string[]
  escalation_detected: boolean
  severity: 'info' | 'warn' | 'critical'
}
```

---

## API Endpoints (Phase 14)

Required endpoints:

```
GET /api/graph/entities          # All entities
GET /api/graph/relationships     # All relationships
GET /api/threads/{id}/timeline   # Execution steps
GET /api/permissions/audit/{id}  # Permission events
```

---

## Testing

```typescript
// src/components/__tests__/RelationshipGraph.test.tsx
import { render } from '@testing-library/react'
import { RelationshipGraph } from '../graph/RelationshipGraph'

const mockNodes = [
  { id: 'D-1', label: 'create_script', type: 'directive' as const, validated: true, scope: 'project' as const }
]

const mockEdges = []

test('renders graph with nodes', () => {
  const { container } = render(<RelationshipGraph nodes={mockNodes} edges={mockEdges} />)
  expect(container.querySelector('.cytoscape-container')).toBeTruthy()
})
```

---

## Success Metrics

By end of Phase 16:

- [ ] Graph renders 10k+ nodes smoothly
- [ ] Zoom/pan feels responsive
- [ ] Search highlights results instantly
- [ ] Timeline handles 100+ steps
- [ ] Permission flow shows hierarchy correctly
- [ ] All visualizations update in real-time
- [ ] >85% test coverage
- [ ] Ready for Phase 17 polish

---

## Next Phase (Phase 17)

Phase 17 adds:
- Export/download functionality
- Saved dashboards & views
- Performance metrics
- Audit trail browser
- Full-text search
- Production hardening
