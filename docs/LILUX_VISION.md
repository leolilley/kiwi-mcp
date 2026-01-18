# 🐧 Lilux: The AI-Native Operating System

**The Seed of Something Revolutionary**

_"What if Linux was built for AI agents instead of humans?"_

---

## The Realization

You're looking at **Kiwi MCP** and thinking it's a developer tool. You're wrong.

This is the **embryo of an AI-native operating system**. What you call the `.ai/` folder isn't a configuration directory—it's `/usr`, `/lib`, `/etc`, and `/home` combined. What you call "directives" aren't just markdown files—they're **programs written in natural language** that AI agents execute as fluidly as bash executes shell scripts.

This is **Lilux**—Linux reimagined for a world where the primary operator is artificial intelligence.

---

## The Paradigm Shift

### From Human-Centered to AI-Centered

```
Traditional OS (Linux):
┌─────────────────────────────────────────────────────────────┐
│                         HUMAN                               │
│                           ↓                                 │
│                        SHELL                                │
│                           ↓                                 │
│                        KERNEL                               │
│                           ↓                                 │
│                   HARDWARE/RESOURCES                        │
└─────────────────────────────────────────────────────────────┘

AI-Native OS (Lilux):
┌─────────────────────────────────────────────────────────────┐
│                      AI AGENT                               │
│                          ↓                                  │
│                   DIRECTIVE LAYER                           │
│                    (Natural Language)                       │
│                          ↓                                  │
│                  MCP SERVER (Kernel)                        │
│                          ↓                                  │
│               SCRIPTS + APIs + KNOWLEDGE                    │
│                          ↓                                  │
│                  REAL WORLD ACTIONS                         │
└─────────────────────────────────────────────────────────────┘
```

### The Core Insight

In Linux, everything is a file.

In Lilux, **everything is a prompt**.

- Programs are directives (structured prompts that instruct AI)
- Configuration is knowledge (context that informs AI decisions)
- Processes are subagents (spawned AI instances with isolated context)
- The kernel is the MCP server (the interface between AI and resources)

---

## Component Mapping: Linux → Lilux

| Linux Concept                     | Lilux Equivalent               | Description                                     |
| --------------------------------- | ------------------------------ | ----------------------------------------------- |
| **Kernel**                        | MCP Server                     | The core interface between agents and resources |
| **Shell**                         | Agent Prompt                   | How the AI interprets and dispatches commands   |
| **Programs** (`/bin`, `/usr/bin`) | Directives (`.ai/directives/`) | Instructions that accomplish tasks              |
| **Binaries**                      | Scripts (`.ai/scripts/`)       | Deterministic executable code                   |
| **Libraries** (`/lib`)            | Libs (`.ai/scripts/lib/`)      | Shared code for scripts                         |
| **Man Pages**                     | Knowledge (`.ai/knowledge/`)   | Documentation, patterns, learnings              |
| **Config** (`/etc`)               | Patterns (`.ai/patterns/`)     | System-wide conventions                         |
| **Home** (`~`)                    | User Space (`~/.ai/`)          | User-specific items                             |
| **Package Manager** (apt/npm)     | Registry (Supabase)            | Centralized repository                          |
| **Processes**                     | Subagents                      | Isolated execution contexts                     |
| **.bashrc**                       | AGENTS.md                      | Agent configuration                             |
| **Symlinks**                      | Relationships                  | Connections between knowledge                   |
| **Systemd**                       | Orchestration Directives       | Meta-coordination                               |
| **Logs**                          | Outputs (`.ai/outputs/`)       | Execution history                               |
| **Self-healing**                  | Self-annealing                 | Systems improve from failures                   |

---

## The Lilux Filesystem

```
/                                    (Project Root)
├── .ai/                             (The AI "Filesystem")
│   ├── directives/                  /bin, /usr/bin - Programs
│   │   ├── core/                    System utilities
│   │   │   ├── init.md             Like /sbin/init
│   │   │   ├── context.md          Like /bin/env
│   │   │   ├── bootstrap.md        Like /sbin/setup
│   │   │   ├── search_*.md         Like /bin/find, /bin/grep
│   │   │   ├── run_*.md            Like /bin/exec
│   │   │   └── sync_*.md           Like /bin/rsync
│   │   ├── meta/                    Like /sbin - System administration
│   │   │   ├── orchestrate_*.md    Coordination daemons
│   │   │   ├── validate_*.md       System checks
│   │   │   └── migrate_*.md        Upgrade utilities
│   │   ├── workflows/               Like /usr/share/applications
│   │   └── patterns/                Like /etc/skel templates
│   │
│   ├── scripts/                     /opt, /usr/local/bin - Executables
│   │   ├── scraping/               Domain-specific tools
│   │   ├── enrichment/             Data processing
│   │   ├── extraction/             Content retrieval
│   │   ├── validation/             Quality checks
│   │   ├── lib/                    /lib, /usr/lib - Shared libraries
│   │   │   ├── http_session.py     Like libcurl
│   │   │   ├── proxy_pool.py       Like libproxy
│   │   │   └── checkpoint.py       Like libpersist
│   │   └── .venv/                  Isolated runtime environment
│   │
│   ├── knowledge/                   /usr/share/doc, /usr/share/man
│   │   ├── concepts/               Theory and fundamentals
│   │   ├── patterns/               Design patterns
│   │   ├── procedures/             How-to guides
│   │   ├── learnings/              Captured experience
│   │   ├── sources/                Referenced documentation
│   │   ├── index.json              Like /var/cache/man/index
│   │   ├── relationships.json      Knowledge graph
│   │   └── embeddings/             Vector representations
│   │
│   ├── patterns/                    /etc/skel, /etc/defaults
│   │   ├── imports.md              Standard import patterns
│   │   ├── tool.md                 Tool creation template
│   │   └── types.md                Type conventions
│   │
│   ├── plans/                       /var/lib/dpkg, /var/log/apt
│   │   └── PLAN_*.md               Roadmaps and status
│   │
│   ├── outputs/                     /var/log
│   │   └── scripts/                Execution outputs
│   │
│   └── project_context.md          /etc/motd - Project summary
│
├── ~/.ai/                          $HOME for AI - User space
│   ├── directives/                 User's custom directives
│   ├── scripts/                    User's custom scripts
│   ├── knowledge/                  User's knowledge base
│   └── .env                        User environment variables
│
└── AGENTS.md                       Like .bashrc - Agent configuration
```

---

## The DOE Kernel: Directive-Orchestration-Execution

The heart of Lilux is the **DOE Framework**, separating concerns like a modern microkernel:

```
┌─────────────────────────────────────────────────────────────┐
│                    DIRECTIVE LAYER                          │
│           "WHAT" - Intent, Goals, Constraints               │
│                                                             │
│  • XML-structured instructions                              │
│  • Human-readable, AI-executable                            │
│  • Versioned, self-documenting                              │
│  • Declares permissions required                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  ORCHESTRATION LAYER                        │
│          "HOW" - Decision Making, Routing                   │
│                                                             │
│  • The AI agent itself                                      │
│  • Reads directives, interprets context                     │
│  • Routes to appropriate execution                          │
│  • Handles errors, self-anneals                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   EXECUTION LAYER                           │
│           "DO" - Deterministic Action                       │
│                                                             │
│  • Python scripts with 100% reliability                     │
│  • API calls, data processing                               │
│  • Testable, versioned, isolated                            │
│  • Returns structured results                               │
└─────────────────────────────────────────────────────────────┘
```

### Why This Architecture?

The fundamental insight: **LLMs are probabilistic** (90% per step), **code is deterministic** (100% per step).

```
5-step task with pure LLM:     90%^5 = 59% success
5-step task with DOE pattern:  90% × 100% × 100% × 100% × 90% = 81% success
```

Push complexity into deterministic scripts. Let AI focus on decision-making—what it's actually good at.

---

## Process Model: Subagents as Processes

### Linux Processes vs Lilux Subagents

| Linux Process         | Lilux Subagent                      |
| --------------------- | ----------------------------------- |
| fork()                | Task() or spawn()                   |
| Isolated memory       | Isolated context window             |
| Returns exit code     | Returns result summary              |
| PID namespace         | Fresh context                       |
| IPC for communication | Cannot communicate during execution |
| Parent waits          | Main agent receives summary         |

### The Context Window Multiplication

The killer feature of subagents:

```
Traditional (one agent):
┌─────────────────────────────────────────────────────────────┐
│  Main Agent Context Window                                  │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Attempt 1: Failed (500 tokens wasted)                   ││
│  │ Attempt 2: Failed (800 tokens wasted)                   ││
│  │ Attempt 3: Success (1200 tokens)                        ││
│  │ ─────────────────────────────────────────               ││
│  │ Total: 2500 tokens consumed, context polluted           ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘

With Subagents (Lilux):
┌─────────────────────────────────────────────────────────────┐
│  Main Agent Context (only 50 tokens used)                   │
│  ├─ "Spawn subagent to debug test"                         │
│  └─ "Result: Fixed import path in line 42"                 │
│                                                             │
│  Subagent Context (isolated, discarded after):              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ All 2500 tokens of debugging happen here                ││
│  │ Isolated. Thrown away. Main context stays clean.        ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

## Self-Annealing: The Self-Improving OS

This is where Lilux diverges from all prior computing paradigms:

**Traditional software doesn't learn from failures. Lilux does.**

### The Annealing Loop

```
Directive Execution
        │
        ▼
    ┌───────┐
    │Success│───────────────────────────┐
    └───────┘                           │
        │                               ▼
        │                       Store in Knowledge
        │                               │
        ▼                               │
    ┌───────┐                           │
    │Failure│                           │
    └───────┘                           │
        │                               │
        ▼                               │
    Capture Error                       │
        │                               │
        ▼                               │
    anneal_directive()                  │
        │                               │
        ▼                               │
    Directive Improves                  │
        │                               │
        ▼                               │
    Store Learning ◄────────────────────┘
        │
        ▼
    SYSTEM IS SMARTER
```

### What Gets Annealed?

```xml
<!-- Before annealing -->
<step name="install_deps">
  <action>Run npm install</action>
</step>

<!-- After failure: "EACCES permission denied" -->
<step name="install_deps">
  <action>
    Check for write permissions.
    If permission denied, try with --legacy-peer-deps.
    If still failing, check if running with correct user.
    Run npm install (or npm install --legacy-peer-deps if needed).
  </action>
  <error_handling>
    EACCES: Check directory ownership
    EPERM: May need elevated permissions
  </error_handling>
</step>
```

The directive literally gets smarter. **The next agent doesn't hit the same issue.**

---

## The Four Primitives

Lilux has exactly **4 system calls** (tools):

| Tool      | Linux Equivalent         | Purpose                 |
| --------- | ------------------------ | ----------------------- |
| `search`  | `find`, `locate`, `grep` | Discover items          |
| `load`    | `cat`, `cp`, `wget`      | Retrieve and copy items |
| `execute` | `exec`, `run`, `install` | Run operations          |
| `help`    | `man`, `--help`          | Get guidance            |

### Universal Interface

```python
# Everything uses the same pattern
tool(
    item_type="directive|script|knowledge",
    action="run|create|update|delete|publish",
    item_id="name",
    parameters={...},
    project_path="/path/to/project"
)
```

This is like having a universal syscall interface where everything—files, processes, devices—is handled through a unified API.

---

## The Registry: Universal Package Management

Like apt repositories but for AI knowledge:

```
┌─────────────────────────────────────────────────────────────┐
│                    REGISTRY (Cloud)                         │
│                                                             │
│  Directives:  "oauth_setup", "deploy_kubernetes", ...      │
│  Scripts:     "google_maps_scraper", "email_validator"     │
│  Knowledge:   "jwt-auth-patterns", "email-deliverability"  │
│                                                             │
│  Each item has: version, author, quality_score, downloads  │
└─────────────────────────────────────────────────────────────┘
                    │                      │
          load()    │                      │  publish()
                    ▼                      ▲
┌─────────────────────────────────────────────────────────────┐
│                   LOCAL (.ai/)                              │
│                                                             │
│  Downloaded directives, customized scripts, local knowledge │
│  Runs offline. Syncs when connected.                        │
└─────────────────────────────────────────────────────────────┘
```

### Package Commands

```bash
# Linux equivalents in Lilux
apt search → search(item_type="directive", query="...", source="registry")
apt install → load(item_type="script", item_id="...", destination="project")
apt publish → execute(item_type="knowledge", action="publish", ...)
apt upgrade → sync_directives()
```

---

## Multi-Agent Architecture: Distributed Computing for AI

```
┌─────────────────────────────────────────────────────────────┐
│                    PRIMARY AGENT                            │
│                (High-level orchestrator)                    │
│                                                             │
│  Runs: AGENTS.md (like .bashrc)                            │
│  Has:  Command dispatch table                               │
│  Does: Parse intent → Route to directive → Coordinate       │
└─────────────────────────────────────────────────────────────┘
                    │
     ┌──────────────┼──────────────┐
     │              │              │
     ▼              ▼              ▼
┌─────────┐   ┌─────────┐   ┌─────────┐
│Subagent │   │Subagent │   │Subagent │
│ Task A  │   │ Task B  │   │ Task C  │
│         │   │         │   │         │
│ Fresh   │   │ Fresh   │   │ Fresh   │
│ context │   │ context │   │ context │
└────┬────┘   └────┬────┘   └────┬────┘
     │              │              │
     │   (execute scripts,        │
     │    query knowledge,        │
     │    modify files)           │
     │              │              │
     └──────────────┼──────────────┘
                    │
                    ▼
            Summary returns
            to primary agent
```

### Model Class Routing

Lilux directives declare their computational requirements:

```xml
<model_class tier="fast" fallback="balanced" parallel="true">
  Simple template substitution. Use cheap model.
</model_class>

<model_class tier="reasoning" fallback="expert" parallel="false">
  Complex architecture decision. Use powerful model.
</model_class>
```

This is like **nice levels** and **scheduler hints** in Linux—telling the kernel how to allocate resources.

| Tier        | Linux Equivalent   | Use Case                     |
| ----------- | ------------------ | ---------------------------- |
| `fast`      | `nice -n 19`       | Simple transforms, templates |
| `balanced`  | Default priority   | Standard tasks               |
| `reasoning` | `nice -n -10`      | Complex analysis             |
| `expert`    | Real-time priority | Novel research problems      |

---

## The Permission Model

Every directive declares its required permissions:

```xml
<permissions>
  <!-- File system access -->
  <read resource="filesystem" path="src/**/*.ts" />
  <write resource="filesystem" path="dist/**/*" />

  <!-- Network access -->
  <read resource="network" endpoint="https://api.example.com" />

  <!-- Environment variables -->
  <read resource="env" var="API_KEY" />

  <!-- Execution -->
  <execute resource="shell" command="npm" />
  <execute resource="python" module="requests" />
</permissions>
```

This is **capability-based security** meets **Android-style permission declarations**. The agent can verify before execution that it has necessary permissions.

---

## Knowledge as Living Documentation

Traditional documentation is static. Lilux knowledge **grows and evolves**:

```
┌─────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE BASE                           │
│                                                             │
│  Concepts      ← What things ARE                           │
│  Patterns      ← How to DO things                          │
│  Procedures    ← Step-by-step guides                       │
│  Learnings     ← What we've DISCOVERED                     │
│  Sources       ← External REFERENCES                       │
│                                                             │
│  Connected via:                                             │
│  - relationships.json (explicit links)                      │
│  - embeddings.json (semantic similarity)                    │
│  - index.json (fast lookup)                                │
└─────────────────────────────────────────────────────────────┘
```

### Knowledge Accumulation Loop

Every successful execution can add knowledge:

```python
# After successfully setting up OAuth
knowledge.create(
    zettel_id="learning-oauth-gotcha-2026",
    title="Google OAuth requires consent screen review for production",
    content="...",
    entry_type="learning"
)
```

The next agent benefits. **The system remembers what it learns.**

---

## Boot Sequence

When a new project initializes (like system boot):

```
1. init.md                  # Initialize .ai/ structure
        │
        ▼
2. bootstrap.md             # Set up project-specific config
        │
        ▼
3. context.md               # Generate project understanding
        │
        ▼
4. AGENTS.md loaded         # Configure agent behavior
        │
        ▼
5. Ready for commands       # Agent awaits natural language
```

---

## The Vision: What Lilux Becomes

### Phase 1: Foundation (Now - Q2 2026)

**The Kernel Era**

- ✅ Unified MCP server with 4 primitives
- ✅ Directive-Orchestration-Execution framework
- ✅ Self-annealing improvement loop
- ✅ Registry for package distribution
- 🔄 Dual-model architecture (router + reasoning)
- 🔄 Edge router fine-tuning pipeline

### Phase 2: Edge Computing (Q3 2026 - Q1 2027)

**The Hardware Era**

- Trained FunctionGemma routers for instant tool calls
- Multi-platform deployment (macOS, iOS, Linux, Android)
- Speculative execution for sub-100ms responses
- Confidence-based routing for cost optimization
- Offline-first operation with cloud enhancement
- Self-hosted router marketplace

### Phase 3: Distributed Intelligence (Q2 2027 - Q4 2027)

**The Network Era**

- Multi-agent coordination protocols
- Federated knowledge sharing (privacy-preserving)
- Cross-project directive inheritance
- Real-time sync and collaboration
- Agent-to-agent communication standards
- Distributed task execution across devices

### Phase 4: Ambient AI (2028+)

**The Ubiquitous Era**

- **The Standard AI Operating Environment**
- Lilux on every device (phones, watches, cars, infrastructure)
- Interoperable agents from different vendors
- Composable AI capabilities like Unix pipes
- Self-organizing agent networks
- AI as invisible as electricity

### The Milestones

```
2024: AI is a cloud service you call
        ↓
2026: AI is software that runs locally (Lilux v1)
        ↓
2027: AI is infrastructure that coordinates (Lilux v2)
        ↓
2028: AI is the environment itself (Lilux v3)
        ↓
2030+: AI is indistinguishable from reality
```

```
lilux 6.18.4-lilux1-1
Welcome to Lilux GNU/AI

agent@project:~/.ai$ search("deploy to kubernetes")
Found: deploy_kubernetes v2.3.1 (quality: 98%)

agent@project:~/.ai$ run("deploy_kubernetes", env="production")
✓ Loaded directive
✓ Verified permissions
✓ Spawned 3 subagents for parallel preparation
✓ Executing deployment sequence...
```

---

## The Philosophy: Directives All The Way Down

The core principle:

> **LLMs instructing LLMs, removing humans from the loop.**

```
Every piece of work should have a directive.

1st time: Do manually, note steps
2nd time: Create directive
3rd time: Run directive
```

The goal is **exit velocity**—the system becomes capable of handling tasks without human intervention.

```
Traditional automation:
  Human writes code → Code runs → Human monitors
  (Human always in the loop)

Lilux automation:
  Directive instructs LLM → LLM executes → LLM stores learnings
  (Human only for novel situations)
```

---

## Call to Action: Building the Future

You're looking at the seed.

The Kiwi MCP project isn't a tool—it's the foundation of something much larger. Every directive written, every script created, every piece of knowledge stored is building toward a future where:

1. **AI agents have a standard operating environment**
2. **Capabilities compose like Unix pipes**
3. **Systems improve themselves through use**
4. **Knowledge accumulates across the network**
5. **Anyone can package and share AI workflows**

This is the **Linux of AI**.

And like Linux, it starts with a small kernel, a few utilities, and a vision.

The vision is **Lilux**.

---

## The Hardware Layer: Dual-Brain Architecture

This is where Lilux transcends traditional software. Just as modern chips combine CPUs with NPUs (Neural Processing Units), Lilux implements a **dual-model architecture** that runs AI at two speeds simultaneously.

### The Two Brains

```
┌─────────────────────────────────────────────────────────────────────┐
│                      USER INTERACTION                                │
│       "Find that email enrichment script we built last week"        │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
          ┌────────────────┴────────────────┐
          │                                 │
          ▼                                 ▼
┌─────────────────────┐          ┌─────────────────────────┐
│    LOCAL BRAIN      │          │      CLOUD BRAIN        │
│   (Edge Router)     │          │    (Reasoning Model)    │
│                     │          │                         │
│ FunctionGemma 270M  │          │ Claude Sonnet / GPT-4o  │
│                     │          │                         │
│ • 30-50ms latency   │          │ • 800-2000ms latency    │
│ • $0.00 per request │          │ • $0.08-0.15 per req    │
│ • 100% offline      │          │ • Infinite knowledge    │
│ • 98% accuracy      │          │ • 99.5% accuracy        │
│ • Privacy-first     │          │ • Complex reasoning     │
│ • Deterministic     │          │ • Creative synthesis    │
└──────────┬──────────┘          └───────────┬─────────────┘
           │                                 │
           └────────────┬────────────────────┘
                        │
                        ▼
              ┌─────────────────────┐
              │    KIWI MCP CORE    │
              │   (Tool Execution)  │
              └─────────────────────┘
```

### Why Two Brains?

| Single Model Problem       | Dual Model Solution           |
| -------------------------- | ----------------------------- |
| Slow (1.5-3s latency)      | Fast (40-80ms for tool calls) |
| Expensive ($0.15+/request) | Cheap ($0.008 average)        |
| Cloud-dependent            | Offline-capable               |
| Privacy concerns           | Local-first routing           |
| 85% consistency            | 98% consistency               |

### The Math of Speed

```
Single Model (Traditional):
┌──────────────────────────────────────────────────────────────────┐
│ User → Cloud API (50-200ms network) → Model (500ms) → Parse     │
│                                                                  │
│ Total: 750-1200ms per tool call                                 │
└──────────────────────────────────────────────────────────────────┘

Dual Model (Lilux):
┌──────────────────────────────────────────────────────────────────┐
│ User → Local Router (40ms) → Execute → Done!                    │
│       ↘ Cloud Brain (parallel) → Synthesizes explanation        │
│                                                                  │
│ Total: 50-100ms for tool execution                              │
│        (User sees results before explanation finishes)          │
└──────────────────────────────────────────────────────────────────┘
```

### Speculative Execution: The Future Arrives Early

Lilux doesn't wait for certainty. It **speculates**:

```
Query: "find email scripts"

t=0ms:    Start streaming tokens
t=15ms:   Token: "search" → Confidence: 45%

t=30ms:   Token: '{"item_type":' → Confidence: 65%

t=40ms:   Token: '"script"' → Confidence: 72%
          ✅ SPECULATION THRESHOLD CROSSED
          → Start preparing search tool in background

t=55ms:   Token: ',"query":"email"' → Confidence: 85%

t=65ms:   Confidence: 91%
          ✅ COMMITMENT THRESHOLD CROSSED
          → Preparation complete!
          → EXECUTE IMMEDIATELY
          → Stop generating tokens (early exit!)

t=70ms:   Tool execution started

Savings: 30-50ms by not waiting for full generation
```

This is **CPU branch prediction for AI**—start down a likely path before you're certain, commit when confident, rollback if wrong.

---

## Edge-First Computing: Your Device, Your AI

### The Sovereignty Principle

In traditional cloud AI:

- Your data travels to remote servers
- Someone else's hardware processes your thoughts
- You pay per token, forever
- No internet = no AI

In Lilux edge computing:

- **Your device processes locally**
- **Your data never leaves**
- **One-time training cost, infinite use**
- **Offline-first, cloud-enhanced**

### Platform Support Matrix

| Platform    | Runtime   | Accelerator   | Latency   | Power  |
| ----------- | --------- | ------------- | --------- | ------ |
| **macOS**   | Metal     | Apple Silicon | 30-50ms   | <1W    |
| **iOS**     | CoreML    | Neural Engine | 25-40ms   | 0.4W   |
| **Linux**   | CUDA/ROCm | GPU           | 30-60ms   | 5-30W  |
| **Windows** | DirectML  | GPU           | 40-80ms   | 5-30W  |
| **Android** | NNAPI     | NPU           | 50-100ms  | 1-2W   |
| **Web**     | WebGPU    | GPU           | 100-200ms | Varies |

### The Router: Your Personal AI Chip

The FunctionGemma 270M model is trained specifically for **your** command patterns:

```python
# Your patterns become hardwired
COMMAND_PATTERNS = {
    "search directives {X}": → search(item_type="directive", query="{X}")
    "run {X}": → execute(action="run", item_id="{X}")
    "sync scripts": → execute(action="run", item_id="sync_scripts")
    "find {X} scripts": → search(item_type="script", query="{X}")
}
```

The model learns **your vocabulary**, **your project structure**, **your workflow patterns**.

### Fine-Tuning: Teaching Your Device

```python
# Generate training data from your actual usage
examples = [
    {"user": "find email scripts",
     "tool": "search",
     "params": {"item_type": "script", "query": "email"}},

    {"user": "run sync directives",
     "tool": "execute",
     "params": {"action": "run", "item_id": "sync_directives"}},

    # ... 1000+ examples from your patterns
]

# Fine-tune in 1-4 hours on consumer GPU
# Result: 98%+ accuracy on YOUR commands
```

**Training cost**: ~$50 one-time (GPU rental)
**Inference cost**: $0.00 forever

---

## Parallel Racing: The Art of Concurrent Intelligence

### The Race Pattern

Both models run simultaneously. Whoever finishes first, wins:

```
t=0ms:    Query arrives
          ├─ Router starts streaming (local)
          └─ Reasoning model starts thinking (cloud)

t=50ms:   Router: High confidence reached!
          → Execute tool immediately
          → Push result to queue

t=100ms:  Reasoning model: Checks for results
          → Result already available!
          → Starts synthesizing explanation WITH the result

t=150ms:  User sees: "✅ Found 3 email scripts"
          (Tool already executed, waiting for explanation)

t=800ms:  Reasoning: "I found 3 scripts that handle email..."
          (User gets rich explanation, but action was instant)
```

### Confidence-Based Routing

Not all queries are equal. Route based on certainty:

```
HIGH CONFIDENCE (>90%):
  Router → Execute immediately
  Cost: $0.00
  Latency: 50ms

MEDIUM CONFIDENCE (70-90%):
  Router → Ask reasoning to verify → Execute
  Cost: $0.02
  Latency: 200ms

LOW CONFIDENCE (<70%):
  Router → Defer to reasoning model
  Cost: $0.15
  Latency: 1000ms

Average (with typical distribution):
  70% high + 20% medium + 10% low
  = 0.70×$0 + 0.20×$0.02 + 0.10×$0.15
  = $0.019 per request (87% savings!)
```

---

## Multi-Model Orchestration: The Conductor Pattern

### Specialized Routers for Different Domains

```
                      Query
                        ↓
              ┌─────────────────┐
              │ Meta Classifier │
              │   (tiny model)  │
              └────────┬────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
         ▼             ▼             ▼
    ┌────────┐    ┌────────┐    ┌────────┐
    │ Kiwi   │    │ File   │    │ Git    │
    │ Router │    │ Router │    │ Router │
    │ 270M   │    │ 270M   │    │ 270M   │
    └───┬────┘    └───┬────┘    └───┬────┘
        │             │             │
        ▼             ▼             ▼
    Kiwi MCP      File Ops      Git Ops
```

Each router is a **specialist**—trained on specific domains, running on the same hardware, activated on demand.

### The Orchestra Analogy

| Role            | Traditional Orchestra | Lilux Multi-Model  |
| --------------- | --------------------- | ------------------ |
| **Conductor**   | Human conductor       | Meta classifier    |
| **Sections**    | Strings, winds, brass | Domain routers     |
| **Musicians**   | Individual players    | Specialized models |
| **Score**       | Musical notation      | Directives         |
| **Performance** | Synchronized music    | Coordinated AI     |

---

## Streaming Architecture: Tokens as Events

### The Token Stream Philosophy

Lilux treats token generation as an **event stream**, not a blocking call:

```python
class TokenEventStream:
    async def stream_with_hooks(self, query: str):
        """Emit events at key points during generation"""

        async for token in self.model.stream(query):
            # Event: Every token
            await self.emit("on_token", token)

            # Event: Tool detected
            if self.detect_tool_prefix(partial):
                await self.emit("on_tool_detected", tool_name)
                # Start preparation in background!

            # Event: Confidence threshold
            if confidence > 0.85:
                await self.emit("on_confident", tool_call)
                # May trigger early execution!

            # Event: Complete
            if tool_call.is_complete:
                await self.emit("on_complete", tool_call)
                return  # Early exit!
```

### Hook System: React to Intelligence

External systems can subscribe to AI events:

```python
@router.on("on_tool_detected")
async def start_preparation(event):
    """Tool name known, start preparing before full call"""
    await prepare_tool_environment(event.tool)

@router.on("on_confident")
async def execute_early(event):
    """High confidence, execute before generation completes"""
    result = await execute_tool(event.tool_call)
    return result

@router.on("on_complete")
async def log_completion(event):
    """Generation complete, log for analytics"""
    await metrics.record(event)
```

This is **reactive AI**—the system responds to intelligence as it emerges, not after it's fully formed.

---

## The Hardware Vision: Lilux Everywhere

### From Cloud to Edge to Everywhere

```
2024: Cloud-only AI
┌─────────────────────────────────────────┐
│ Your Device → Internet → Cloud → Back  │
│ (Latency: 500-2000ms, Cost: $$$)       │
└─────────────────────────────────────────┘

2026: Hybrid AI (Lilux Today)
┌─────────────────────────────────────────┐
│ Your Device → Local Router (50ms)       │
│            ↘ Cloud for complex (800ms) │
│ (Smart routing, 90% local)             │
└─────────────────────────────────────────┘

2028: Edge-Dominant AI (Lilux Future)
┌─────────────────────────────────────────┐
│ Your Device: Runs everything locally    │
│ Cloud: Sync, updates, rare edge cases   │
│ (99% local, <100ms, zero cost)         │
└─────────────────────────────────────────┘

2030+: Ambient AI
┌─────────────────────────────────────────┐
│ Every device has AI fabric              │
│ Lilux runs on: phones, watches, cars,  │
│   appliances, infrastructure           │
│ (AI as fundamental as electricity)     │
└─────────────────────────────────────────┘
```

### The Self-Hosting Promise

Traditional SaaS AI:

- You don't own your intelligence
- Models change without your consent
- Pricing changes without warning
- Your data trains their models

Lilux Self-Hosted:

- **You own your trained routers**
- **Models frozen to your version**
- **One-time training, free forever**
- **Your data stays yours**

---

## Performance Comparison: The Numbers

### Latency (Tool Decision)

| Architecture          | Latency | Improvement    |
| --------------------- | ------- | -------------- |
| Single Cloud Model    | 1,500ms | Baseline       |
| Dual Model (Parallel) | 50ms    | **30x faster** |
| Speculative Execution | 35ms    | **43x faster** |

### Cost (Per 1M Requests)

| Architecture            | Monthly Cost      | Savings    |
| ----------------------- | ----------------- | ---------- |
| All Cloud (GPT-4o)      | $150,000          | Baseline   |
| All Cloud (GPT-4o Mini) | $750              | 99.5%      |
| Dual Model (Hybrid)     | $190              | 99.87%     |
| All Local (Router Only) | $12 (electricity) | **99.99%** |

### Privacy

| Architecture | Data Exposure                   |
| ------------ | ------------------------------- |
| Cloud-only   | All queries visible to provider |
| Dual Model   | Only complex queries to cloud   |
| Local-only   | **Zero data exposure**          |

---

## Technical Reference

### Core Files

| File                     | Purpose                            |
| ------------------------ | ---------------------------------- |
| `AGENTS.md`              | Agent configuration (like .bashrc) |
| `.ai/project_context.md` | Generated project understanding    |
| `.ai/patterns/*.md`      | Project conventions                |
| `kiwi_mcp/server.py`     | The kernel                         |
| `kiwi_mcp/handlers/`     | Type-specific syscall handlers     |
| `kiwi_mcp/tools/`        | The 4 primitives                   |

### Key Directives

| Directive          | Purpose                        |
| ------------------ | ------------------------------ |
| `init`             | Bootstrap a new project        |
| `context`          | Generate project understanding |
| `run_directive`    | Execute a directive            |
| `anneal_directive` | Improve from failure           |
| `sync_*`           | Synchronize with registry      |
| `subagent`         | Spawned execution context      |

### Environment

```bash
# Required
SUPABASE_URL=https://project.supabase.co
SUPABASE_SECRET_KEY=your-key

# Optional
AI_USER_SPACE=~/.ai
LOG_LEVEL=INFO
```

---

## The Complete Architecture: All Layers Combined

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          USER / HUMAN LAYER                              │
│   Natural language: "find that email script and run it"                 │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────────┐
│                        APPLICATION LAYER                                 │
│   CLI / Desktop App / Mobile App / IDE Plugin / Web Interface           │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────────────┐
│                     DUAL-MODEL ORCHESTRATION                             │
│  ┌───────────────────────┐    ┌───────────────────────────────────┐    │
│  │     LOCAL ROUTER      │    │        CLOUD REASONING            │    │
│  │    (FunctionGemma)    │    │     (Claude/GPT/Gemini)          │    │
│  │                       │    │                                   │    │
│  │  • 40ms decisions     │◄──►│  • Complex planning              │    │
│  │  • $0 per request     │    │  • Creative synthesis            │    │
│  │  • 98% accuracy       │    │  • Fallback verification         │    │
│  │  • Offline-capable    │    │  • Novel problem solving         │    │
│  └───────────┬───────────┘    └─────────────┬─────────────────────┘    │
│              │                               │                          │
│              └───────────────┬───────────────┘                          │
│                              ▼                                          │
│            ┌────────────────────────────────────┐                       │
│            │      AGENT COORDINATOR              │                       │
│            │  (Parallel racing, confidence       │                       │
│            │   routing, speculative execution)   │                       │
│            └────────────────┬───────────────────┘                       │
└─────────────────────────────┼───────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────────┐
│                        MCP SERVER (KERNEL)                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                │
│  │  SEARCH  │  │   LOAD   │  │ EXECUTE  │  │   HELP   │                │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘                │
│       │             │             │             │                       │
│       └─────────────┴──────┬──────┴─────────────┘                       │
│                            │                                             │
│              ┌─────────────▼─────────────┐                              │
│              │  TYPE HANDLER REGISTRY    │                              │
│              └─────────────┬─────────────┘                              │
│       ┌────────────────────┼────────────────────┐                       │
│       ▼                    ▼                    ▼                       │
│ ┌───────────┐       ┌───────────┐       ┌───────────┐                  │
│ │ Directive │       │  Script   │       │ Knowledge │                  │
│ │  Handler  │       │  Handler  │       │  Handler  │                  │
│ └─────┬─────┘       └─────┬─────┘       └─────┬─────┘                  │
└───────┼───────────────────┼───────────────────┼─────────────────────────┘
        │                   │                   │
┌───────▼───────────────────▼───────────────────▼─────────────────────────┐
│                        STORAGE LAYER                                     │
│                                                                          │
│  ┌─────────────────────┐    ┌─────────────────────────────────────┐    │
│  │    LOCAL (.ai/)     │    │        REGISTRY (Cloud)              │    │
│  │                     │    │                                      │    │
│  │ directives/         │◄──►│  Versioned packages                  │    │
│  │ scripts/            │    │  Quality scores                      │    │
│  │ knowledge/          │    │  Author attribution                  │    │
│  │ patterns/           │    │  Dependency resolution               │    │
│  │ outputs/            │    │  Search + discovery                  │    │
│  └─────────────────────┘    └─────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
        │                   │                   │
┌───────▼───────────────────▼───────────────────▼─────────────────────────┐
│                        EXECUTION LAYER                                   │
│                                                                          │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────────────┐   │
│  │ Python venv   │  │    APIs       │  │      Shell Commands       │   │
│  │ (isolated)    │  │  (external)   │  │     (sandboxed)          │   │
│  └───────────────┘  └───────────────┘  └───────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────────────┐
│                         REAL WORLD                                       │
│   Files, APIs, Databases, Services, Infrastructure, The Internet        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## The MCP Bridge: Using Standard Infrastructure

### The Key Insight from Building Agents

As revealed by Amp's ["How to Build an Agent"](https://ampcode.com/how-to-build-an-agent):

> **"It's an LLM, a loop, and enough tokens. The secret is there is no secret."**

The agent loop is simple:

```python
while True:
    user_input → conversation
    response ← model(conversation)
    
    if tool_use_detected:
        result ← execute_tool()
        result → conversation
        continue  # Loop back
    else:
        display(response)
        break
```

**That's the core.** Everything else is optimization.

### MCP Infrastructure: What We Reuse (95%)

Lilux doesn't reinvent MCP (Model Context Protocol). We **use it**:

```
✅ MCP Servers (Kiwi, filesystem, git, weather...)
✅ stdio/SSE Protocol (standard communication)
✅ Tool Schemas (JSON Schema format)
✅ call_tool() API (execution interface)
✅ Server ecosystem (any MCP server works)
```

**All MCP servers work with Lilux unchanged.**

### The Innovation: Intent Routing (5%)

We only change ONE thing—**who decides which tool to call**:

```
Traditional MCP:
┌─────────────────────────────────────────────────┐
│ Cloud Model sees ALL tool schemas              │
│         ↓                                       │
│ Generates JSON tool call                       │
│         ↓                                       │
│ Execute via MCP protocol                       │
└─────────────────────────────────────────────────┘

Lilux MCP:
┌─────────────────────────────────────────────────┐
│ Frontend Model outputs: [TOOL: intent]         │
│         ↓                                       │
│ FunctionGemma routes (local, 50ms)            │
│         ↓                                       │
│ Execute via SAME MCP protocol                  │
└─────────────────────────────────────────────────┘
```

### The Architecture

```
User Input
    │
    ▼
┌─────────────────────────┐
│  Conversational Model   │  [TOOL: search for email scripts]
│  (Phi-3 Mini, 3B)       │  Does NOT see tool schemas
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Intent Router Harness  │  Intercepts [TOOL: ...] markers
│                         │  Routes to FunctionGemma
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  FunctionGemma Router   │  Intent → JSON tool call
│  (270M, local)          │  Trained on MCP schemas
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  MCP Client (Standard)  │  call_tool() via stdio
│                         │  Same as Claude Desktop
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  MCP Servers (Standard) │  Kiwi, filesystem, git...
│  UNCHANGED              │  ANY MCP server works
└─────────────────────────┘
```

### Benefits

| Aspect | Traditional MCP | Lilux Intent Routing |
| ------ | --------------- | -------------------- |
| **MCP Compatibility** | ✅ All servers | ✅ All servers (unchanged) |
| **Infrastructure** | ✅ stdio/SSE | ✅ stdio/SSE (unchanged) |
| **Model Sees** | All tool schemas | Just `[TOOL: intent]` syntax |
| **Privacy** | Schemas to cloud | Schemas stay local |
| **Routing Speed** | 1.5s cloud | 50ms local |
| **Model Size** | 70B+ cloud | 3B frontend + 270M router |
| **Cost** | $0.15/request | $0.001/request |
| **Works Offline** | ❌ No | ✅ Yes |

### Training on MCP

The FunctionGemma router trains on MCP server schemas:

```python
# Connect to ANY MCP server
await mcp_client.connect_to_server("kiwi", "python", ["-m", "kiwi_mcp.server"])

# Get tool schemas
tools = await mcp_client.list_tools()

# Generate training data
for tool in tools:
    training_data.append({
        "intent": generate_natural_variations(tool.description),
        "tool_call": {
            "name": tool.name,
            "arguments": extract_from_schema(tool.inputSchema)
        }
    })

# Fine-tune FunctionGemma
train_router(training_data)
```

**Result**: One router that works with ALL MCP servers.

### The Loop in Lilux

```python
# Amp-style loop with intent routing
async def lilux_agent_loop(user_message: str):
    conversation.append(user_message)
    
    # Stream from frontend model
    async for token in frontend.stream(conversation):
        # Detect [TOOL: intent] marker
        if marker_detected:
            intent = extract_intent(token)
            
            # Route through FunctionGemma (50ms)
            tool_call = router.predict(intent)
            
            # Execute via STANDARD MCP (unchanged)
            result = mcp_client.call_tool(
                name=tool_call["name"],
                arguments=tool_call["arguments"]
            )
            
            # Add result to conversation
            conversation.append(result)
            
            # Loop back to frontend
            continue
        
        yield token
```

Same loop. Same MCP. Just smarter routing.

---

## The Competitive Landscape: Why Lilux Wins

### vs. Traditional AI Assistants (ChatGPT, Claude, etc.)

| Aspect   | Traditional                | Lilux                            |
| -------- | -------------------------- | -------------------------------- |
| Memory   | Session-based, ephemeral   | Persistent knowledge base        |
| Tools    | Generic, same for everyone | Custom, trained on your patterns |
| Speed    | Cloud-latency (500ms+)     | Local-first (40ms)               |
| Cost     | Per-token, forever         | One-time training, free use      |
| Privacy  | Data sent to cloud         | Local-first, your data stays     |
| Learning | Static model               | Self-annealing improvement       |

### vs. Agent Frameworks (LangChain, AutoGPT, etc.)

| Aspect    | Agent Frameworks    | Lilux                           |
| --------- | ------------------- | ------------------------------- |
| Structure | Code-defined chains | Human-readable directives       |
| Sharing   | Copy code files     | Registry packages with versions |
| Discovery | Read documentation  | Semantic search                 |
| Evolution | Manual code updates | Self-annealing + sync           |
| Hardware  | Cloud-only          | Edge + cloud hybrid             |

### vs. IDE AI (Cursor, Copilot, etc.)

| Aspect        | IDE AI             | Lilux                           |
| ------------- | ------------------ | ------------------------------- |
| Scope         | Coding assistance  | Full workflow automation        |
| Knowledge     | Model training     | Your custom knowledge base      |
| Persistence   | Context window     | Permanent storage               |
| Customization | Prompt files       | Directives + patterns + scripts |
| Extension     | Fixed capabilities | Handler architecture            |

---

## Getting Started: Your First Steps in Lilux

### 1. Initialize (The Boot)

```bash
# Create the .ai/ filesystem
run("init", project_type="python")
```

### 2. Generate Context (Know Your World)

```bash
# Understand the project
run("context")
```

### 3. Search (Find Your Tools)

```bash
# Discover what exists
search("email enrichment", item_type="script")
```

### 4. Execute (Do The Work)

```bash
# Run a directive
run("create_script", script_name="my_tool", description="...")
```

### 5. Learn (Grow The System)

```bash
# Store what you learned
create("knowledge", zettel_id="learning-001", content="...")
```

### 6. Anneal (Improve From Failure)

```bash
# When something fails, make it smarter
run("anneal_directive", directive_name="failing_directive")
```

---

## Appendix: The Name

**Lilux** = **L**LM + L**i**nux + L**ux** (light)

- **LLM**: Large Language Models are the operators
- **Linux**: Inspired by the Unix philosophy
- **Lux**: Latin for "light"—bringing clarity to AI systems

_The light of structure in the chaos of prompts._

---

_"In the beginning was the command line. Now there is the prompt line."_

**Welcome to Lilux.**

---

## The Complete Dual-Brain: Both Sides Fine-Tuned

We've described the hardware layer with a fast router (FunctionGemma) and a high-reasoning model running in parallel. But the true power of Lilux comes when **both brains are fine-tuned for your system**.

### The Router Brain (Fast Intuition)

**FunctionGemma 270M** fine-tuned to:
- Translate natural language → tool calls in 40-80ms
- Understand your specific command patterns
- Infer parameters from context
- Provide confidence scores for decisions

Training: 1,000-5,000 examples of (input → tool_call) pairs

### The Orchestrator Brain (Deep Reasoning)

**Llama 3.3 70B** (or Qwen 72B, Mistral Large) fine-tuned to:
- Know that the router exists and runs in parallel
- Defer to router when confidence is high (>85%)
- Take control when router is uncertain (<60%)
- Deeply understand Kiwi MCP semantics
- Plan multi-step workflows
- Synthesize tool results into natural conversation
- Handle graceful handoffs when router results arrive mid-generation

Training: 1,500-3,000 examples covering:
- Router deference patterns
- Kiwi semantic understanding
- Multi-step orchestration
- Graceful handoffs
- Error handling

### The Synergy

```
User: "Find that email script we made last week and run it on the new leads"

┌─ Router (45ms) ─────────────────────────────────────────────┐
│ Prediction: search(item_type="script", query="email")       │
│ Confidence: 0.92 ✓                                          │
└─────────────────────────────────────────────────────────────┘

┌─ Orchestrator (500ms, but tool already executed!) ──────────┐
│ *Knows router suggested search with 92% confidence*         │
│ *Sees tool already executed, results available*             │
│ *Synthesizes natural response:*                             │
│                                                             │
│ "Found `email_enricher.py` from January 10th.               │
│  Running it on your new leads folder now...                 │
│  ✓ Processed 847 leads, enriched 612, 235 already current.  │
│  Report saved to .ai/outputs/"                              │
└─────────────────────────────────────────────────────────────┘
```

Both brains are **Kiwi-native**. They understand your system deeply and work together seamlessly—a slow thoughtful brain with a fast intuitive one, just like human cognition.

### The Vision: Your Personal AI That Knows You

With both models fine-tuned on **your** patterns:
- The router knows **your** common commands
- The orchestrator knows **your** workflow preferences
- Both improve as you use them (self-annealing)
- Complete privacy—runs locally on your hardware

This is the Lilux experience: AI that feels instant, understands your system, and keeps getting better.

---

## Appendix: Related Documents

| Document                                                                                                                         | Description                     |
| -------------------------------------------------------------------------------------------------------------------------------- | ------------------------------- |
| [**MCP Integration Bridge**](../../kiwi-fine-tune/MCP%20Integration%20-%20The%20Agent%20Loop%20Bridge.md)                       | How Lilux uses MCP infrastructure |
| [**Semantic Routing at Scale**](../../kiwi-fine-tune/Semantic%20Routing%20at%20Scale%20-%20Intent%20Discovery%20Layer.md) ⚡   | Scaling to infinite directives  |
| [**Multi-Net Architecture**](../../kiwi-fine-tune/Multi-Net%20Agent%20Architecture.md)                                           | Distributed intelligence layers |
| [Dual-Model Architecture](../../kiwi-fine-tune/Dual-Model-Architecture-Overview.md)                                             | Edge router + cloud reasoning   |
| [Why FunctionGemma](../../kiwi-fine-tune/Why%20FunctionGemma%20for%20Tool%20Routing.md)                                         | Model selection rationale       |
| [Training FunctionGemma](../../kiwi-fine-tune/Training%20FunctionGemma%20for%20Kiwi%20MCP.md)                                   | Fine-tuning your router         |
| [**Training the Orchestrator**](../../kiwi-fine-tune/Fine-Tuning%20the%20Reasoning%20Orchestrator.md)                           | Fine-tuning the reasoning brain |
| [Streaming Architecture](../../kiwi-fine-tune/Streaming%20Architecture%20%26%20Concurrent%20Execution.md)                       | Concurrent token generation     |
| [Edge Deployment](../../kiwi-fine-tune/Deployment%20Guide%20-%20Edge%20Device%20Implementation.md)                              | Deploy to devices               |
| [Integration Patterns](../../kiwi-fine-tune/Integration%20Patterns%20-%20Connecting%20All%20Components.md)                      | Connecting everything           |

---

## Appendix: Glossary

| Term             | Definition                                                     |
| ---------------- | -------------------------------------------------------------- |
| **Directive**    | A natural language program that instructs AI agents            |
| **Script**       | A deterministic Python script that executes actual work        |
| **Knowledge**    | Persistent information that informs AI decisions               |
| **Anneal**       | To improve a directive by learning from failure                |
| **Router**       | A small, fast model that translates intent to tool calls       |
| **Orchestrator** | The high-reasoning model that plans, converses, and synthesizes |
| **Subagent**     | A spawned AI process with isolated context                     |
| **MCP**          | Model Context Protocol—the standard for AI tool integration    |
| **Registry**     | Centralized package repository for sharing AI workflows        |
| **Edge**         | Computing that happens on your local device                    |
| **DOE**          | Directive-Orchestration-Execution framework                    |
| **Dual-Brain**   | Architecture with fast router + slow reasoning model in parallel |

---

## Appendix: The Manifesto

**We believe:**

1. **AI should run everywhere, not just in the cloud.**
   Your phone, your laptop, your car. Intelligence should be local.

2. **AI should learn from every interaction.**
   Systems that don't improve are wasting experience.

3. **AI workflows should be shareable like software.**
   What works for one should work for all.

4. **AI should understand intent, not syntax.**
   Natural language is the universal interface.

5. **Privacy is not optional.**
   Your thoughts, your device, your control.

6. **Speed matters.**
   Humans shouldn't wait for machines to think.

7. **Cost should approach zero.**
   Intelligence should be as cheap as computation.

8. **AI should compose like Unix pipes.**
   Simple tools, infinite combinations.

9. **The best AI is invisible.**
   Technology that disappears into usefulness.

10. **We're building the future.**
    Not waiting for it.

---

_"In the beginning was the command line. Now there is the prompt line."_

_"Everything is a file" becomes "Everything is a prompt."_

_"Do one thing well" becomes "Direct one thing well."_

**This is Lilux. This is the AI-native operating system. This is the seed.**

🐧✨

---

_Document generated: 2026-01-17_
_Version: 0.2.0-expanded_
_Status: Vision Document (Extended with Hardware Layer)_
_Authors: Kiwi MCP Team_
_License: Open Vision - Build Upon This_
