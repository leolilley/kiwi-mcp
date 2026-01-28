# Lilux/RYE Strategy: Complete Documentation Index

**Date:** 2026-01-28  
**Version:** 0.1.0  
**Purpose:** Master index and quick reference for the complete strategy

---

## What Is This?

Complete documentation for packaging and distributing **Lilux** (kernel) + **RYE** (core content) as a single user-friendly package.

**Goal:** Users can `pipx install rye` and start building AI-native execution systems within minutes.

---

## The Five Key Documents

### 1. [LILUX_RYE_SPLIT.md](./LILUX_RYE_SPLIT.md)
**Purpose:** Understand the architecture

**Contains:**
- What is Lilux? (kernel + infrastructure)
- What is RYE? (essential content)
- Why split them? (separation of concerns)
- Repository structure for each
- Benefits of the split
- Future possibilities

**Read this if:** You want to understand the overall design

**Key takeaway:** Lilux is the engine, RYE is the fuel

---

### 2. [PACKAGING_AND_DISTRIBUTION.md](./PACKAGING_AND_DISTRIBUTION.md)
**Purpose:** Understand packaging strategy and user onboarding

**Contains:**
- Single package strategy (`rye` on PyPI)
- Installation via `pipx` (one command)
- User installation flow
- Environment setup
- **17-demo progression system:**
  - Phase 1: Meta Tools (4 demos)
  - Phase 2: Core Harness (4 demos)
  - Phase 3: Advanced Orchestration (4 demos)
  - Phase 4: Advanced Showcase (5 demos)
- Configuration and environment variables

**Read this if:** You want to understand how users get and use the system

**Key takeaway:** From `pipx install rye` to advanced orchestration in 2-4 hours

---

### 3. [DEMO_STRUCTURE.md](./DEMO_STRUCTURE.md)
**Purpose:** Detailed structure of all 17 demos

**Contains:**
- Complete demo progression map
- Phase 1 demos: Search, Load, Create, Execute
- Phase 2 demos: Permissions, State, Knowledge, Hooks
- Phase 3 demos: Recursion, Parallel, Context, Evolution
- Phase 4 demos: Genome, Proofs, Software, Multi-agent, Version Control
- Implementation checklist
- Demo metadata standards
- Key principles for each demo

**Read this if:** You're implementing the demos or want detailed examples

**Key takeaway:** Each demo teaches one concept, builds on previous, and is fully runnable

---

### 4. [TECHNICAL_IMPLEMENTATION.md](./TECHNICAL_IMPLEMENTATION.md)
**Purpose:** Technical details for developers implementing the split

**Contains:**
- Migration path (current → target structure)
- Package configuration (`pyproject.toml`)
- Import migration guide (`kiwi_mcp` → `lilux`)
- MCP server setup
- Content bundling
- User space initialization
- Testing strategy
- Versioning & compatibility
- PyPI distribution checklist

**Read this if:** You're implementing the code changes

**Key takeaway:** Single package with bundled content, clean imports, ready to distribute

---

### 5. [USER_GUIDE.md](./USER_GUIDE.md)
**Purpose:** End-user documentation

**Contains:**
- Quick start (5 minutes)
- System overview (4 tools, 3 concepts)
- User space structure
- Creating your first directive
- State files & persistence
- Knowledge & learning
- Working through all demos
- Common workflows
- Best practices
- Troubleshooting

**Read this if:** You're a user or writing for users

**Key takeaway:** Clear path from installation to building sophisticated systems

---

## Quick Reference

### For Architects
```
Start → LILUX_RYE_SPLIT.md → PACKAGING_AND_DISTRIBUTION.md
  → IMPLEMENTATION_ROADMAP.md
```

### For Developers
```
Start → TECHNICAL_IMPLEMENTATION.md → DEMO_STRUCTURE.md
  → Code implementation
```

### For Users
```
Start → USER_GUIDE.md (Quick Start section)
  → Demos Phase 1 → Phase 2+ (as desired)
```

### For Project Managers
```
Start → IMPLEMENTATION_ROADMAP.md → PACKAGING_AND_DISTRIBUTION.md
  → Track progress against checklist
```

---

## The User Journey

### Day 1: Installation (5 minutes)
```bash
pipx install rye
rye-init  # Initialize user space
```

**Result:** Ready to use the system

### Day 1-2: Learning Phase 1 (30 minutes)
```
Demo 1: Search directives
Demo 2: Load directives
Demo 3: Create directives
Demo 4: Execute & sign
```

**Result:** Understand the 4 core tools

### Day 2-3: Learning Phase 2 (60 minutes)
```
Demo 5: Permissions & cost
Demo 6: State files
Demo 7: Knowledge evolution
Demo 8: Hooks & plugins
```

**Result:** Understand advanced features

### Day 3-4: Learning Phase 3 (90 minutes)
```
Demo 9: Deep recursion
Demo 10: Parallel orchestration
Demo 11: Tight context
Demo 12: Self-evolving systems
```

**Result:** Master orchestration patterns

### Day 4+: Phase 4 (As interested)
```
Demo 13-17: Advanced showcases
  - Genome evolution
  - Proof generation
  - Software building
  - Multi-agent systems
  - Version control
```

**Result:** Full system mastery

---

## Implementation Timeline

| Phase | Duration | What | Result |
|-------|----------|------|--------|
| 0 | 1-2 weeks | Refactoring, package setup | Ready to build |
| 1 | 1-2 weeks | Foundation, Phase 1 demos | v0.1.0 on PyPI |
| 2 | 1-2 weeks | Harness, Phase 2 demos | v0.2.0 on PyPI |
| 3 | 1-2 weeks | Orchestration, Phase 3 demos | v0.3.0 on PyPI |
| 4 | 1-2 weeks | Showcase, Phase 4 demos | v0.4.0 on PyPI |
| 5 | 1-2 weeks | Polish, launch | v1.0.0 on PyPI |

**Total:** 6-12 weeks to production

---

## Key Files & Concepts

### Core Concepts

**Lilux (Kernel)**
- MCP server with 4 tools (search, load, execute, help)
- Execution primitives (subprocess, HTTP)
- Handlers for directives, tools, knowledge
- Runtime services (auth, environment, state)
- Storage backends (vector search, local)
- Safety mechanisms (permissions, cost, recursion limits)

**RYE (Content)**
- Essential directives (.ai/directives/)
- Utility tools/scripts (.ai/tools/)
- Core knowledge base (.ai/knowledge/)
- Templates & patterns (.ai/patterns/)

### User Spaces

**Core (Bundled)**
```
.ai/
├── directives/core/  ← Bootstrap directives
├── tools/core/       ← Essential utilities
└── knowledge/core/   ← Core concepts
```

**User (Local)**
```
~/.local/share/lilux/user/
├── directives/       ← Custom directives
├── tools/           ← Custom tools
├── knowledge/       ← Custom knowledge
└── state/           ← Execution state files
```

### The 4 Core Tools

1. **search** - Find items by keyword/category
2. **load** - Read full item content
3. **execute** - Run directives/tools
4. **help** - Get usage guidance

### State Files

Persistent YAML/JSON files in user space that store:
- Execution progress
- Learnings from attempts
- Problem-solving history
- Self-improvement tracking

### Knowledge Entries

Markdown files with frontmatter that store:
- Learned techniques
- Proven strategies
- Problem solutions
- Pattern discoveries

---

## Success Metrics

### User Adoption
- [ ] 100+ users within 3 months of 1.0.0
- [ ] 50+ GitHub stars
- [ ] Active community discussions

### Feature Adoption
- [ ] >80% users reach Phase 2
- [ ] >50% users reach Phase 3
- [ ] >30% users reach Phase 4

### System Reliability
- [ ] 99%+ uptime for PyPI package
- [ ] <1% critical bug rate
- [ ] <24h response time for security issues

### User Satisfaction
- [ ] >4.5/5 average rating
- [ ] >80% would recommend
- [ ] <10% churn rate

---

## Architecture at a Glance

```
┌─────────────────────────────────────────────┐
│  User's LLM Agent (Claude, Cursor, etc.)    │
│                                             │
│  Tools:                                     │
│    - search: Find directives/tools/content  │
│    - load: Read full content                │
│    - execute: Run directives & tools        │
│    - help: Get usage guidance               │
└─────────────────┬───────────────────────────┘
                  │ MCP Protocol
                  ▼
┌─────────────────────────────────────────────┐
│         Lilux MCP Server (kernel)           │
│                                             │
│  ├─ Tools: search, load, execute, help      │
│  ├─ Handlers: Directive, Tool, Knowledge    │
│  ├─ Primitives: Execute subprocess, HTTP    │
│  ├─ Runtime: Auth, environment, state       │
│  ├─ Storage: Vector search, file system     │
│  └─ Safety: Permissions, cost, recursion    │
└─────────────────┬───────────────────────────┘
                  │
     ┌────────────┴────────────┐
     ▼                         ▼
┌──────────────┐        ┌──────────────┐
│ Core Content │        │ User Content │
│  (Bundled)   │        │   (Local)    │
│              │        │              │
│ .ai/:        │        │ ~/.local/... │
│ ├─directives │        │ ├─directives │
│ ├─tools      │        │ ├─tools      │
│ ├─knowledge  │        │ ├─knowledge  │
│ └─patterns   │        │ ├─state      │
└──────────────┘        │ └─logs       │
                        └──────────────┘
```

---

## Common Questions

### Q: How is this different from kiwi-mcp?
**A:** This is the evolution of kiwi-mcp with better packaging, clearer learning path, and production-ready features.

### Q: Can I use Lilux without RYE?
**A:** Yes, but RYE provides essential directives that make it immediately useful.

### Q: Do I need to learn everything?
**A:** No. Phase 1 is sufficient for basic use. Phase 2-4 unlock advanced features.

### Q: Can I contribute?
**A:** Yes! Kernel contributions go to lilux, content contributions to rye content.

### Q: Will this work with my LLM?
**A:** Any LLM supporting MCP tools works (Claude, Cursor, custom agents, etc.)

---

## Getting Started

### As a User
1. Read: [USER_GUIDE.md](./USER_GUIDE.md) Quick Start
2. Install: `pipx install rye`
3. Initialize: `rye-init`
4. Run: `Demo 1: execute action run directive core demo search directives`

### As a Developer
1. Read: [TECHNICAL_IMPLEMENTATION.md](./TECHNICAL_IMPLEMENTATION.md)
2. Read: [DEMO_STRUCTURE.md](./DEMO_STRUCTURE.md)
3. Set up: Dev environment with Phase 0 tasks
4. Implement: Phase 1 tasks

### As an Architect
1. Read: [LILUX_RYE_SPLIT.md](./LILUX_RYE_SPLIT.md)
2. Read: [PACKAGING_AND_DISTRIBUTION.md](./PACKAGING_AND_DISTRIBUTION.md)
3. Read: [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md)
4. Plan: Timeline and resource allocation

---

## Document Locations

All documents in: `/docs/`

- [LILUX_RYE_SPLIT.md](./LILUX_RYE_SPLIT.md) - Architecture
- [PACKAGING_AND_DISTRIBUTION.md](./PACKAGING_AND_DISTRIBUTION.md) - Strategy & Onboarding
- [DEMO_STRUCTURE.md](./DEMO_STRUCTURE.md) - Demo Details
- [TECHNICAL_IMPLEMENTATION.md](./TECHNICAL_IMPLEMENTATION.md) - Code Implementation
- [USER_GUIDE.md](./USER_GUIDE.md) - User Documentation
- [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md) - Timeline & Tasks

---

## Quick Links

### To Users
- **Quick Start:** USER_GUIDE.md § Quick Start
- **Demos:** USER_GUIDE.md § Demos
- **Troubleshooting:** USER_GUIDE.md § Troubleshooting

### To Developers
- **Package Setup:** TECHNICAL_IMPLEMENTATION.md § Part 2
- **Demo Implementation:** DEMO_STRUCTURE.md § Implementation Checklist
- **Tests:** TECHNICAL_IMPLEMENTATION.md § Part 7

### To Project Managers
- **Timeline:** IMPLEMENTATION_ROADMAP.md § Implementation Phases
- **Milestones:** IMPLEMENTATION_ROADMAP.md § Key Milestones
- **Success Criteria:** IMPLEMENTATION_ROADMAP.md § Success Criteria

### To Architects
- **Design:** LILUX_RYE_SPLIT.md
- **Strategy:** PACKAGING_AND_DISTRIBUTION.md § Overview
- **Roadmap:** IMPLEMENTATION_ROADMAP.md

---

## The Vision

**Lilux + RYE = AI-Native Execution Made Practical**

Users should be able to:

1. **Install** in seconds: `pipx install rye`
2. **Initialize** in minutes: `rye-init`
3. **Learn** in hours: Work through 4 demo phases
4. **Build** in days: Create their own systems
5. **Master** in weeks: Advanced orchestration

With safety guarantees:
- ✓ Recursion limits (no runaway)
- ✓ Permission checks (no unauthorized access)
- ✓ Cost controls (no surprises)
- ✓ Context packing (accurate LLM behavior)
- ✓ State tracking (reproducible, self-improving)

---

## Next Steps

1. **Review** all 5 documents
2. **Approve** the architecture and approach
3. **Allocate** team and resources
4. **Begin** Phase 0 (refactoring)
5. **Track** progress against roadmap

---

_This strategy represents 2+ weeks of design work_  
_Ready for implementation_  
_Last Updated: 2026-01-28_
