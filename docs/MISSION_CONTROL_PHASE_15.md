# Phase 15: Core UI Screens

**Duration:** 3 weeks (Weeks 5-7)  
**Status:** Planning  
**Last Updated:** 2026-01-22  

---

## Overview

Phase 15 builds the minimal, clean UI that connects to the Phase 14 backend. The UI is a Next.js 14 app with real-time WebSocket updates that displays:

- **Dashboard:** Active threads, MCP health, recent events
- **Thread Inspector:** Execution timeline, LLM transcript, live metrics
- **Log Stream:** Filterable real-time logs
- **Terminal:** Embedded Kiwi CLI
- **Project Settings:** Configure MCPs, manage connections

**Key Goal:** Get a functional, responsive UI that displays real-time data with zero latency perception.

---

## Design Principles

1. **Minimal & Clean:** No clutter, pure design, information density
2. **Real-time First:** Updates feel instant (< 200ms)
3. **Keyboard-Friendly:** Full keyboard navigation
4. **Dark Mode Native:** Dark by default, light as option
5. **Mobile Responsive:** Works on tablets & phones
6. **Accessible:** WCAG 2.1 AA compliant

---

## Architecture

```
mission_control_ui/
├── src/
│   ├── app/
│   │   ├── layout.tsx           # Root layout
│   │   ├── page.tsx             # Home/dashboard
│   │   ├── dashboard/
│   │   │   └── page.tsx         # Dashboard tab
│   │   ├── threads/
│   │   │   ├── page.tsx         # Threads list
│   │   │   └── [id]/
│   │   │       └── page.tsx     # Thread inspector
│   │   ├── logs/
│   │   │   └── page.tsx         # Log stream
│   │   ├── terminal/
│   │   │   └── page.tsx         # Terminal
│   │   └── settings/
│   │       └── page.tsx         # Project settings
│   │
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Navbar.tsx
│   │   │   └── TabBar.tsx
│   │   │
│   │   ├── dashboard/
│   │   │   ├── ActiveThreads.tsx
│   │   │   ├── MCPHealth.tsx
│   │   │   ├── RecentEvents.tsx
│   │   │   └── Stats.tsx
│   │   │
│   │   ├── thread/
│   │   │   ├── ThreadHeader.tsx
│   │   │   ├── Timeline.tsx
│   │   │   ├── Transcript.tsx
│   │   │   └── Metrics.tsx
│   │   │
│   │   ├── logs/
│   │   │   ├── LogFilter.tsx
│   │   │   ├── LogViewer.tsx
│   │   │   └── LogEntry.tsx
│   │   │
│   │   ├── terminal/
│   │   │   └── TerminalEmulator.tsx
│   │   │
│   │   └── common/
│   │       ├── Badge.tsx
│   │       ├── Card.tsx
│   │       ├── Button.tsx
│   │       ├── Loading.tsx
│   │       └── ...
│   │
│   ├── hooks/
│   │   ├── useWebSocket.ts      # WebSocket connection
│   │   ├── useThreads.ts        # Fetch & cache threads
│   │   ├── useLogs.ts           # Fetch & cache logs
│   │   ├── useMCPs.ts           # Fetch & cache MCPs
│   │   └── useKeyboard.ts       # Global keyboard shortcuts
│   │
│   ├── store/
│   │   ├── websocket.ts         # WebSocket state
│   │   ├── threads.ts           # Thread state
│   │   ├── ui.ts                # UI state (theme, layout, etc)
│   │   └── settings.ts          # User settings
│   │
│   ├── services/
│   │   ├── api.ts               # REST API client
│   │   └── ws.ts                # WebSocket client
│   │
│   ├── styles/
│   │   ├── globals.css
│   │   ├── theme.css
│   │   └── components.css
│   │
│   └── lib/
│       ├── utils.ts
│       └── types.ts
│
├── public/
├── package.json
├── tsconfig.json
├── tailwind.config.js
├── next.config.js
└── README.md
```

---

## Deliverables by Week

### Week 5: Project Setup & Layout

**Goals:**
- [ ] Next.js 14 project scaffolding
- [ ] Tailwind CSS setup
- [ ] Core layout (sidebar, navbar, main)
- [ ] Tab navigation (Dashboard, Threads, Logs, Terminal, Settings)
- [ ] Dark mode toggle
- [ ] Mobile responsive grid

**Components:**
- Root layout with sidebar + content area
- Tab-based routing
- Theme provider (dark/light)
- Responsive breakpoints

**Code Example:**

```typescript
// src/app/layout.tsx
export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-slate-950 text-white">
        <div className="flex h-screen">
          {/* Sidebar */}
          <Sidebar />
          
          {/* Main */}
          <div className="flex-1 flex flex-col overflow-hidden">
            <Navbar />
            <div className="flex-1 overflow-auto">
              {children}
            </div>
          </div>
        </div>
      </body>
    </html>
  )
}
```

### Week 6: Dashboard & Thread List

**Goals:**
- [ ] Dashboard screen (active threads, MCP health, stats)
- [ ] Thread list with live updates
- [ ] WebSocket integration (real-time thread status)
- [ ] Thread inspector screen (timeline, transcript, metrics)
- [ ] Click thread to inspect

**Components:**
- ActiveThreadsCard: List of running threads with status
- MCPHealthCard: Connected MCPs with health status
- RecentEventsCard: Latest events log
- ThreadTimeline: Execution steps with timing
- TranscriptViewer: LLM conversation scrollable

**Code Example:**

```typescript
// src/components/dashboard/ActiveThreads.tsx
'use client'

import { useWebSocket } from '@/hooks/useWebSocket'
import { Thread } from '@/lib/types'
import { useEffect, useState } from 'react'

export function ActiveThreads() {
  const [threads, setThreads] = useState<Thread[]>([])
  const { subscribe, unsubscribe } = useWebSocket()
  
  useEffect(() => {
    const unsubscribeFn = subscribe('threads:running', (msg) => {
      if (msg.type === 'thread.updated') {
        setThreads(prev => 
          prev.map(t => t.id === msg.thread.id ? msg.thread : t)
        )
      }
    })
    
    return unsubscribeFn
  }, [subscribe])
  
  return (
    <div className="space-y-2">
      {threads.map(thread => (
        <ThreadCard key={thread.id} thread={thread} />
      ))}
    </div>
  )
}
```

### Week 7: Logs & Terminal

**Goals:**
- [ ] Log stream screen with real-time updates
- [ ] Log filtering (by thread, MCP, level, service)
- [ ] Search functionality
- [ ] Terminal emulator (Xterm.js)
- [ ] Terminal connected to backend CLI
- [ ] Settings screen (theme, MCPs, preferences)

**Components:**
- LogViewer: Scrollable, virtualized log list
- LogFilter: Dropdowns for filtering
- TerminalEmulator: Xterm instance + input/output
- SettingsPanel: Theme, MCP management, user prefs

**Code Example:**

```typescript
// src/components/terminal/TerminalEmulator.tsx
'use client'

import { useEffect, useRef } from 'react'
import { Terminal } from 'xterm'
import { WebLinksAddon } from 'xterm-addon-web-links'

export function TerminalEmulator() {
  const containerRef = useRef<HTMLDivElement>(null)
  const terminalRef = useRef<Terminal | null>(null)
  
  useEffect(() => {
    if (!containerRef.current) return
    
    const term = new Terminal({
      cursorBlink: true,
      theme: {
        background: '#0f172a',
        foreground: '#e2e8f0',
      },
    })
    
    term.loadAddon(new WebLinksAddon())
    term.open(containerRef.current)
    terminalRef.current = term
    
    // Connect to WebSocket for CLI
    // term.onData(data => { send to backend })
    
    return () => term.dispose()
  }, [])
  
  return <div ref={containerRef} className="w-full h-full" />
}
```

---

## Component Library

### Layout Components

```typescript
// Card - Minimal container
<Card className="p-4 border border-slate-800">
  <h3 className="font-semibold mb-2">Title</h3>
  <p className="text-slate-400">Content</p>
</Card>

// Badge - Status indicators
<Badge variant="success">Running</Badge>
<Badge variant="error">Failed</Badge>

// Button - Minimal styling
<Button variant="primary" size="sm">Action</Button>
<Button variant="secondary" disabled>Disabled</Button>

// Loading - Skeleton
<Loading rows={3} />
```

### Data Display

```typescript
// ThreadCard - Single thread
<ThreadCard thread={thread} onClick={() => navigate(`/threads/${thread.id}`)} />

// LogEntry - Single log line
<LogEntry 
  level="ERROR"
  message="Permission denied"
  timestamp="15:34:23.451"
  context={{ thread_id: "T-123" }}
/>

// Timeline - Execution flow
<Timeline steps={thread.timeline} />

// Transcript - Chat-like LLM messages
<Transcript messages={thread.messages} />
```

---

## State Management (Zustand)

```typescript
// src/store/threads.ts
import { create } from 'zustand'

interface ThreadsState {
  threads: Record<string, Thread>
  selectedThreadId: string | null
  
  addThread: (thread: Thread) => void
  updateThread: (id: string, thread: Partial<Thread>) => void
  setSelectedThread: (id: string) => void
}

export const useThreadsStore = create<ThreadsState>((set) => ({
  threads: {},
  selectedThreadId: null,
  
  addThread: (thread) => set((state) => ({
    threads: { ...state.threads, [thread.id]: thread }
  })),
  
  updateThread: (id, updates) => set((state) => ({
    threads: {
      ...state.threads,
      [id]: { ...state.threads[id], ...updates }
    }
  })),
  
  setSelectedThread: (id) => set({ selectedThreadId: id }),
}))
```

## Real-time Hooks

```typescript
// src/hooks/useWebSocket.ts
import { useEffect, useCallback } from 'react'

export function useWebSocket() {
  const subscribe = useCallback((channel: string, handler: (msg: any) => void) => {
    const ws = new WebSocket('ws://localhost:8000/ws')
    
    ws.onopen = () => {
      ws.send(JSON.stringify({
        type: 'subscribe',
        channel: channel,
      }))
    }
    
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      handler(msg)
    }
    
    return () => ws.close()
  }, [])
  
  return { subscribe }
}
```

---

## Styling Approach

**Tool:** Tailwind CSS (utility-first)  
**Dark Mode:** Enabled by default  
**Spacing:** 4px base unit (p-4 = 16px)  
**Colors:** Slate palette (slate-950 = bg, slate-100 = text in dark)

```css
/* src/styles/theme.css */

@layer base {
  :root {
    --bg-primary: rgb(15 23 42); /* slate-950 */
    --bg-secondary: rgb(30 41 59); /* slate-900 */
    --text-primary: rgb(226 232 240); /* slate-100 */
    --text-secondary: rgb(148 163 184); /* slate-400 */
    --border: rgb(51 65 85); /* slate-700 */
    --success: rgb(34 197 94); /* green-500 */
    --error: rgb(239 68 68); /* red-500 */
  }
}
```

---

## Keyboard Shortcuts

```
Ctrl+K       Open command palette
Ctrl+L       Toggle log stream
Ctrl+T       Toggle terminal
Ctrl+/       Toggle sidebar
?             Show help
J/K          Navigate threads (up/down)
Enter        Inspect selected thread
Esc          Close modals
```

---

## Testing Strategy

### Component Tests (Vitest + React Testing Library)

```typescript
// src/components/__tests__/ActiveThreads.test.tsx
import { render, screen } from '@testing-library/react'
import { ActiveThreads } from '../dashboard/ActiveThreads'

describe('ActiveThreads', () => {
  it('renders thread list', () => {
    render(<ActiveThreads />)
    expect(screen.getByRole('heading')).toHaveTextContent('Active Threads')
  })
})
```

### E2E Tests (Playwright)

```typescript
// e2e/dashboard.spec.ts
import { test, expect } from '@playwright/test'

test('dashboard shows active threads', async ({ page }) => {
  await page.goto('http://localhost:3000')
  await expect(page.locator('text=Active Threads')).toBeVisible()
  
  // Wait for thread list to populate
  await page.waitForSelector('[data-testid="thread-card"]')
  const threads = await page.locator('[data-testid="thread-card"]').count()
  expect(threads).toBeGreaterThan(0)
})
```

---

## Accessibility

- Semantic HTML (nav, main, section)
- ARIA labels on interactive elements
- Keyboard navigation throughout
- Color contrast > 4.5:1
- Focus indicators visible
- Reduced motion support

---

## Performance Optimization

1. **Code Splitting:** Route-based with next/dynamic
2. **Image Optimization:** next/image with responsive sizes
3. **Virtualization:** Large lists use windowing
4. **Memoization:** useMemo for expensive computations
5. **Caching:** TanStack Query with stale-while-revalidate
6. **Bundle:** < 500KB initial JS

---

## Dependencies

```json
{
  "dependencies": {
    "next": "^14.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "zustand": "^4.4.0",
    "@tanstack/react-query": "^5.0.0",
    "xterm": "^5.3.0",
    "tailwindcss": "^3.3.0",
    "typescript": "^5.2.0"
  },
  "devDependencies": {
    "vitest": "^0.34.0",
    "@testing-library/react": "^14.0.0",
    "@playwright/test": "^1.40.0"
  }
}
```

---

## File Structure Details

### Sidebar Component

```typescript
// src/components/layout/Sidebar.tsx
'use client'

import Link from 'next/link'
import { useState } from 'react'
import {
  LayoutDashboard,
  MessageSquare,
  Terminal,
  Settings,
  Zap,
} from 'lucide-react'

export function Sidebar() {
  return (
    <div className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col">
      {/* Logo */}
      <div className="p-4 border-b border-slate-800">
        <h1 className="font-bold text-lg">Mission Control</h1>
        <p className="text-xs text-slate-500">Kiwi MCP Observability</p>
      </div>
      
      {/* Nav */}
      <nav className="flex-1 p-4 space-y-1">
        <NavItem 
          icon={<LayoutDashboard size={18} />}
          label="Dashboard"
          href="/dashboard"
        />
        <NavItem 
          icon={<MessageSquare size={18} />}
          label="Threads"
          href="/threads"
        />
        <NavItem 
          icon={<Zap size={18} />}
          label="Logs"
          href="/logs"
        />
        <NavItem 
          icon={<Terminal size={18} />}
          label="Terminal"
          href="/terminal"
        />
      </nav>
      
      {/* Settings */}
      <div className="p-4 border-t border-slate-800">
        <NavItem 
          icon={<Settings size={18} />}
          label="Settings"
          href="/settings"
        />
      </div>
    </div>
  )
}
```

---

## Success Metrics

By end of Phase 15:

- [ ] UI loads in < 1s
- [ ] Real-time updates visible < 200ms
- [ ] All screens functional
- [ ] Mobile layout responsive
- [ ] Keyboard navigation working
- [ ] Dark mode polished
- [ ] >80% test coverage
- [ ] Ready for Phase 16 visualizations

---

## Next Phase (Phase 16)

Phase 16 adds:
- Relationship graph visualization
- DB schema explorer
- Execution timeline flamegraph
- Permission flow diagrams
