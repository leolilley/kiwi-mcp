# Lilux/RYE: Packaging & Distribution Strategy

**Date:** 2026-01-28  
**Version:** 0.1.0  
**Status:** Design Document

---

## Overview

This document outlines the **packaging, distribution, and user onboarding strategy** for Lilux (kernel) and RYE (core content). The goal is a seamless single-package installation that provides both kernel infrastructure and essential content, with progressive learning from basic to advanced capabilities.

---

## Part 1: Packaging Strategy

### Directory Structure in Repository

```
lilux-rye/  (or keep as kiwi-mcp, transition over time)
├── lilux/                          # Kernel code (Python package root)
│   ├── __init__.py
│   ├── server.py                   # MCP server
│   ├── tools/
│   ├── primitives/
│   ├── handlers/
│   ├── runtime/
│   ├── storage/
│   ├── utils/
│   ├── config/
│   └── safety_harness/
├── .ai/                            # RYE content (git submodule or folder)
│   ├── directives/
│   │   ├── core/
│   │   │   ├── init.md
│   │   │   ├── bootstrap.md
│   │   │   └── ...
│   │   └── meta/
│   ├── tools/
│   └── knowledge/
├── pyproject.toml                  # Single package definition
├── setup.py
└── README.md
```

### PyPI Package: `rye`

**Package name:** `rye` (user-facing)  
**Internal Python module:** `lilux` (kernel implementation)  
**Content path:** `.ai/` (essential directives, tools, knowledge)

#### `pyproject.toml` Configuration

```toml
[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "rye"
version = "0.1.0"
description = "Lilux kernel + RYE content: Execute directives, tools, and knowledge with AI agents"
requires-python = ">=3.9"
dependencies = [
    "pydantic>=2.0",
    "pyyaml>=6.0",
    "requests>=2.28",
]

[project.optional-dependencies]
vector = ["numpy>=1.21", "sentence-transformers>=2.2"]
dev = ["pytest>=7.0", "black>=22.0", "ruff>=0.0.200"]

[project.scripts]
# User-facing CLI tools
lilux = "lilux.cli:main"
rye-init = "lilux.scripts.init:main"
rye-demo = "lilux.scripts.demo:main"

[tool.setuptools.packages.find]
where = ["."]
include = ["lilux*"]

[tool.setuptools.package-data]
lilux = [
    "**/*.py",
    "**/*.md",
]
"" = [
    ".ai/**/*",
]
```

### Installation via `pipx`

```bash
# Install (one command)
pipx install rye

# What it does:
# 1. Installs lilux Python package
# 2. Bundles .ai/ directory with core content
# 3. Sets up MCP server
# 4. Creates CLI entry points
# 5. Makes `lilux` and `rye-*` commands available
```

### Content Bundling

The `.ai/` directory is bundled as **package data** in the wheel:

```python
# In lilux/__init__.py
import importlib.resources
import json
from pathlib import Path

def get_content_root():
    """Get path to bundled .ai/ content"""
    try:
        # Python 3.9+
        files = importlib.resources.files("lilux")
        ai_path = files.joinpath("..", ".ai")
        return Path(str(ai_path))
    except:
        # Fallback: look relative to package
        return Path(__file__).parent.parent / ".ai"

CORE_CONTENT_ROOT = get_content_root()
```

---

## Part 2: User Installation Flow

### Step 1: Installation

```bash
$ pipx install rye
Installing collected packages: rye
Successfully installed rye-0.1.0

✓ Lilux kernel installed
✓ RYE content bundled
✓ MCP server ready
```

### Step 2: Agent Configuration

User configures their AI agent (Claude, Cursor, etc.) with MCP tools:

```json
{
  "mcpServers": {
    "lilux": {
      "command": "lilux",
      "args": ["serve"],
      "env": {
        "USER_SPACE": "/home/user/.local/share/lilux"
      }
    }
  }
}
```

Agent now has 4 tools available:
- **search** - Search directives, tools, knowledge
- **load** - Load item content
- **execute** - Run directives, tools, scripts
- **help** - Get usage guidance

### Step 3: First Directive

Agent executes: `execute action run directive core init`

The **init directive** performs:

1. **Detects environment:**
   - OS, shell, Python version
   - Ray/vector search capability available?
   - Existing `.ai/` content?

2. **Sets up user space:**
   ```
   ~/.local/share/lilux/
   ├── user/                   # User's custom content
   │   ├── directives/
   │   ├── tools/
   │   ├── knowledge/
   │   └── state/              # State files
   ├── cache/                  # Vector embeddings, search indices
   └── config.yaml             # User config
   ```

3. **Optional: RAG setup**
   - Detects if user wants local vector search
   - Downloads core knowledge base embeddings (versioned)
   - Sets up vector store
   - Configures search plugin

4. **Verification**
   - Tests directives can be found
   - Tests tools can execute
   - Tests knowledge search works

5. **Interactive choice:**
   ```
   ✓ User space initialized at ~/.local/share/lilux

   Would you like to:
   [1] Run demo walkthroughs (recommended for new users)
   [2] Start with your own directives
   [3] Just explore the help system
   ```

---

## Part 3: Demo Progression Strategy

### Phase 1: Meta Tools (Basic User Interface)

**Goal:** Learn the 4 core MCP tools and command pattern

#### Demo 1: Search Directives
```
execute action run directive core demo search directives
```

Shows:
- How to find directives by name
- Listing available core directives
- Understanding directive metadata

**Output:**
```
Available directives:
  - core/init (Initialize workspace)
  - core/bootstrap (Setup project)
  - core/sync_directives (Sync from registry)
  - meta/search_directives (This tool)
  - meta/load_directives
  - meta/run_directives
  - ...

Try: execute action load directive core init
```

#### Demo 2: Load Directives
```
execute action run directive core demo load directives
```

Shows:
- Loading full directive content
- Reading instructions and metadata
- Understanding execution steps
- Inspecting tool calls

**Output:**
```
DIRECTIVE: core/init
Type: Setup
Category: Core

INSTRUCTIONS:
1. Validate user environment
2. Create user space directories
3. [Optional] Set up vector search
4. Generate initial config
5. Test connectivity

METADATA:
  version: 0.1.0
  author: rye
  requires: [python>=3.9]
```

#### Demo 3: Create Directives
```
execute action run directive core demo create directives
```

Shows:
- Directive structure and format
- Metadata requirements
- Step definitions
- Tool invocations
- Creating first simple directive

**Guided creation:**
```
Let's create a simple directive together.

Name: hello-world
What should it do? Create a greeting file
What directives/tools should it invoke? 
  - shell create file /tmp/greeting.txt "Hello World"
  
Would you like to save this? [Y/n]
✓ Saved to ~/.local/share/lilux/user/directives/hello-world.md
```

#### Demo 4: Execute & Sign
```
execute action run directive core demo execute directives
execute action run directive core demo sign directives
```

Shows:
- Running created directives
- Validation and integrity checks
- Signing content
- Understanding safety mechanisms

---

### Phase 2: Core RYE Infrastructure

**Goal:** Understand the harness layer that sits on top of Lilux

#### Demo 5: Permissions & Cost Control
```
execute action run directive rye demo permissions cost control
```

Shows:
- Permission tokens and capabilities
- Cost estimation for operations
- Budget constraints
- Approval workflows

**Walkthrough:**
```
PERMISSION SYSTEM

Task: Execute shell command
Required permissions: [shell.execute]

Your capabilities: [file.read, file.write]
⚠ BLOCKED: You don't have shell.execute permission

To enable: Use `execute action run directive rye grant permissions`
Cost: This operation would cost ~0.05 credits
```

#### Demo 6: State Files & Mutation
```
execute action run directive rye demo state files
```

Shows:
- State file format and location
- Reading/writing state
- Knowledge mutation patterns
- Versioning and rollback

**Walkthrough:**
```
STATE FILES: Your persistent memory

Location: ~/.local/share/lilux/user/state/
Structure:
  - execution_history.yaml
  - learning_log.json
  - project_state.json
  - custom_state.yaml

Example: Track attempts at a math problem
state.attempts = 15
state.best_solution = "..."
state.learnings = ["Pattern found in...", "Failed approach..."]
```

#### Demo 7: Knowledge Evolution
```
execute action run directive rye demo knowledge evolution
```

Shows:
- Creating knowledge entries
- Using frontmatter for relationships
- Updating based on learnings
- Knowledge graph connections

**Walkthrough:**
```
KNOWLEDGE MUTATION

Initial entry: "Erdős Numbers in Graph Theory"
As you solve problems, you add:
  - learnings: ["Connected components matter", "...]
  - references: ["proof_attempt_1", "proof_attempt_2"]
  - evolves: ["earlier_understanding"]

Knowledge becomes a living system that improves.
```

#### Demo 8: Hooks & Plugins
```
execute action run directive rye demo hooks plugins
```

Shows:
- Pre/post execution hooks
- Plugin registration
- Custom validations
- Integration points

---

### Phase 3: Advanced Orchestration

**Goal:** Master complex multi-step execution with safety guarantees

#### Demo 9: Deep Recursion & Safety
```
execute action run directive rye demo deep recursion
```

Shows:
- Recursive directive calls
- Depth limiting
- Context preservation
- Preventing runaway execution
- Resource cleanup

**Example:**
```
Directive: solve_problem_recursively
  - Define base case (when to stop)
  - Define recursive case (how to simplify)
  - Set depth limit: max_depth=50
  - Safety: each call validates cost/permissions
  - Result: guaranteed termination
```

#### Demo 10: Parallel Orchestration
```
execute action run directive rye demo parallel orchestration
```

Shows:
- Spawning multiple directives
- Coordinating execution
- Collecting results
- Handling failures
- Resource pooling

**Example:**
```
PARALLEL SEARCH

Tasks: [search_1, search_2, search_3, search_4]
Execution: All 4 run concurrently
Coordination: Wait for all to complete
Collection: Merge results by priority
Cleanup: Release resources

Total time: ~5s vs 20s sequential
```

#### Demo 11: Tight Context Packing
```
execute action run directive rye demo tight context
```

Shows:
- Deterministic stopping conditions
- Minimal context injection
- Exact prompt engineering
- Predictable LLM behavior

**Example:**
```
TIGHT CONTEXT PATTERN

Instead of: "Here's everything about the problem..."
Use: "You are at step 3 of 7. Your task: validate the proof.
     Input: [exact 200 tokens]. Output format: JSON."

Result: LLM focuses precisely, no hallucination
```

---

### Phase 4: Advanced Capabilities Showcase

**Goal:** Demonstrate full power of Lilux/RYE system

#### Demo 12: Self-Evolving Systems
```
execute action run directive rye demo self evolving systems
```

Shows:
- Using state files to track progress
- Mutating knowledge based on results
- Improving over multiple runs
- Learning curves and convergence

**Full example:**
```
MATH EXPLORATION: Solving an Erdős Problem

Iteration 1: Random approach
  state.attempts = 1
  state.time = 2.5s
  → Knowledge: "Random walk fails quickly"
  → Save learning to knowledge base

Iteration 2: Use previous learning
  state.attempts = 2
  state.time = 1.8s (faster!)
  → Knowledge: "Graph property X is critical"
  
Iteration 3: Focus on property X
  state.attempts = 3
  state.time = 0.9s
  → Solution found!

Total: 3 attempts, each learning from previous
```

#### Demo 13: Genome-Type Evolution
```
execute action run directive rye demo genome evolution
```

Shows:
- Encoding solutions as "DNA"
- Crossover and mutation
- Fitness selection
- Population evolution

**Example:**
```
ALGORITHM EVOLUTION

Generation 1: Random sorting algorithms
  - Bubble sort variants (fitness: 2/10)
  - Quick sort variants (fitness: 7/10)
  - Merge sort variants (fitness: 5/10)

Generation 2: Breed best variants
  - Crossover quick+merge = Hybrid (fitness: 8/10)
  - Mutation: Add caching = Fast hybrid (fitness: 9/10)

Generation 3: Refine best
  - Optimized fast hybrid (fitness: 9.8/10)

Result: AI discovers algorithm variations
```

#### Demo 14: Proof Generation & Verification
```
execute action run directive rye demo math proofs
```

Shows:
- Formal proof structure
- Verification with tools
- Evolution of proof attempts
- Recording in knowledge base

**Example:**
```
THEOREM: Graph property X implies Y

Attempt 1: Direct proof
  → Dead end, save why

Attempt 2: Proof by contradiction
  → Progress made, knowledge updated
  
Attempt 3: Using induction
  → Complete proof found
  
Proof recorded:
  knowledge_entry: proof_by_induction_strategy
  references: [previous_attempts]
  complexity: O(n²)
  verified: true
```

#### Demo 15: Software Building with Tight Context
```
execute action run directive rye demo software building
```

Shows:
- Building complete systems incrementally
- Context isolation per module
- Testing as you go
- Integration steps

**Example:**
```
BUILDING A SEARCH ENGINE

Phase 1: Tokenizer module
  - Tight context: "Build a tokenizer for English text"
  - Output: tokenizer.py (exact spec)
  - Test: unit tests pass

Phase 2: Indexer module  
  - Tight context: "Build indexer using tokenizer"
  - Input: tokenizer.py (as context)
  - Output: indexer.py
  - Test: integration tests pass

Phase 3: Searcher module
  - Uses both previous modules
  - Tight context limits hallucination
  
Result: Complete system, each part verified
```

#### Demo 16: Multi-Agent Orchestration
```
execute action run directive rye demo multi agent
```

Shows:
- Spawning multiple LLM agents
- Role assignment
- Message passing
- Consensus/voting
- Results aggregation

**Example:**
```
PARALLEL PROBLEM SOLVING

Agents:
  - Mathematician: Prove theorem
  - Engineer: Design algorithm
  - Researcher: Find references

Each receives:
  - Specific task
  - Minimal context (tight packing)
  - Resource budget
  - Execution timeout

Results merged → Better solution through diverse approaches
```

#### Demo 17: State-Based Version Control
```
execute action run directive rye demo version control
```

Shows:
- Checkpointing execution
- Rolling back to known states
- Branch and merge semantics
- Reproducible exploration

**Example:**
```
EXPLORING SOLUTION SPACE

Checkpoint A: Initial solution attempt
  state.solution_id = "v1"
  state.score = 45%

Branch 1: Try optimization A
  state.solution_id = "v1_opt_a"
  state.score = 52%

Branch 2: Try optimization B
  state.solution_id = "v1_opt_b"
  state.score = 49%

Merge best: Checkpoint B with v1_opt_a
  state.solution_id = "v2"
  state.score = 52%
  state.parent = "Checkpoint A"
  
Reproducible exploration with version history
```

---

## Part 4: Advanced Demonstrations

### Mathematical Exploration Example

**Problem:** Solve Erdős Problem using tight orchestration

```
execute action run directive rye demo erdos problem
```

**Full walkthrough:**

1. **Setup**
   - Load problem definition from knowledge
   - Create state tracking
   - Set resource limits

2. **Agent 1: Graph Theorist**
   - Input: Problem + relevant theorems
   - Task: Identify critical graph properties
   - Output: Property analysis

3. **Agent 2: Proof Specialist**
   - Input: Properties from Agent 1
   - Task: Construct formal proof sketch
   - Output: Proof outline

4. **Agent 3: Code Generator**
   - Input: Proof outline
   - Task: Generate verification code
   - Output: Python code + test

5. **Verification**
   - Run verification code
   - Log results
   - Update knowledge

6. **Evolution**
   - If successful: Mark solution in knowledge
   - If failed: Record attempt, refine approach
   - Next iteration uses learnings

**Key demonstrating:**
- Tight context per agent
- Parallel execution
- Result aggregation
- Knowledge mutation
- Safety guarantees (timeouts, permissions)

### Software Engineering Example

**Problem:** Build an ML-powered content classifier

```
execute action run directive rye demo build ml classifier
```

**Architecture:**

1. **Phase 1: Data Module**
   ```
   Agent: Data Engineer
   Context: "Build data loader for CSV files
            Output: data_loader.py with tests"
   Output: Verified module
   ```

2. **Phase 2: Feature Engineering**
   ```
   Agent: ML Engineer
   Context: "Using data_loader.py, build feature extractor
            Output: feature_extractor.py with tests"
   Inputs: data_loader.py
   Output: Verified module
   ```

3. **Phase 3: Model Training**
   ```
   Agent: ML Specialist
   Context: "Build classifier using features
            Output: classifier.py with evaluation"
   Inputs: feature_extractor.py, data_loader.py
   Output: Verified module
   ```

4. **Phase 4: Integration**
   ```
   Agent: Integration Engineer
   Context: "Combine all modules into complete system
            Output: main.py, requirements.txt, README"
   Inputs: All previous modules
   Output: Complete system
   ```

5. **Testing**
   ```
   Agent: QA Engineer
   Context: "Write comprehensive tests
            Output: test_suite.py"
   Inputs: Complete system
   Output: Test suite
   ```

6. **Documentation**
   ```
   Agent: Technical Writer
   Context: "Document the system
            Output: docs/API.md, docs/USAGE.md"
   Inputs: Complete system, test suite
   Output: Documentation
   ```

**Key demonstrating:**
- Context isolation per phase
- Deterministic stopping conditions
- Modular verification
- Integration safety
- Complete system output

---

## Part 5: Implementation Roadmap

### Phase 1: Foundation (Initial Release 0.1.0)

- [ ] Package `lilux` + `.ai/` as single `rye` PyPI package
- [ ] Create `rye-init` command for user setup
- [ ] Implement Demo 1-3 (Search, Load, Create Directives)
- [ ] Documentation for packaging

### Phase 2: Harness (0.2.0)

- [ ] Permission system (Demo 5)
- [ ] State files & mutation (Demo 6)
- [ ] Knowledge evolution (Demo 7)
- [ ] Hooks & plugins (Demo 8)

### Phase 3: Advanced (0.3.0)

- [ ] Deep recursion safety (Demo 9)
- [ ] Parallel orchestration (Demo 10)
- [ ] Tight context packing (Demo 11)
- [ ] Self-evolving systems (Demo 12)

### Phase 4: Showcase (0.4.0)

- [ ] Genome evolution (Demo 13)
- [ ] Proof generation (Demo 14)
- [ ] Software building (Demo 15)
- [ ] Multi-agent examples (Demo 16-17)

### Phase 5: Polish (1.0.0)

- [ ] All demos complete
- [ ] Comprehensive guides
- [ ] Integration with major LLM platforms
- [ ] Production-ready safety harness

---

## Part 6: Configuration & Environment

### User Space Structure

```
~/.local/share/lilux/
├── user/
│   ├── directives/          # User's custom directives
│   ├── tools/               # User's custom tools
│   ├── knowledge/           # User's custom knowledge
│   └── state/               # Execution state files
├── cache/
│   ├── embeddings/          # Vector embeddings cache
│   └── indices/             # Search indices
├── config.yaml
└── .env
```

### Environment Variables

```bash
# MCP Server
export LILUX_SERVER_HOST=127.0.0.1
export LILUX_SERVER_PORT=9000

# User Space
export USER_SPACE=/home/user/.local/share/lilux

# Vector Search (optional)
export VECTOR_ENABLED=true
export VECTOR_BACKEND=local  # or: openai, huggingface

# Safety
export MAX_EXECUTION_DEPTH=50
export MAX_EXECUTION_TIME=300
export PERMISSION_MODE=strict  # or: moderate, permissive
```

### Config File: `config.yaml`

```yaml
version: "0.1"

# User preferences
user:
  name: "User Name"
  email: "user@example.com"

# Vector search
vector:
  enabled: true
  backend: local
  embedding_model: sentence-transformers/all-MiniLM-L6-v2
  cache_dir: ~/.local/share/lilux/cache/embeddings

# Safety
safety:
  max_depth: 50
  max_time: 300
  permission_mode: strict

# Logging
logging:
  level: INFO
  format: json
  output: ~/.local/share/lilux/logs

# Demo settings
demos:
  completed: ["core/init", "demo/search", "demo/load"]
  progress: "phase_1"
```

---

## Part 7: Key Design Principles

### 1. **Single Installation, Full Capability**
- `pipx install rye` gives you everything
- Kernel + essential content bundled
- No separate installs needed

### 2. **Progressive Learning**
- Start with 4 tools (search, load, execute, help)
- Learn patterns through guided demos
- Graduate to advanced orchestration
- Master full system potential

### 3. **Tight Execution Model**
- Deterministic stopping conditions
- Permission/cost checks
- Context packing for accuracy
- Safety guarantees (timeouts, recursion limits)

### 4. **Self-Improving System**
- State files track progress
- Knowledge mutates with learnings
- Proof of concept for AI-native execution
- Reproducible exploration

### 5. **Content Over Infrastructure**
- Lilux kernel is minimal, stable
- RYE directives + tools + knowledge are the focus
- User adds content in `.ai/` directories
- Mix core content with custom content

---

## Part 8: User Journeys

### Journey 1: New User (First 30 minutes)

```
1. Install: pipx install rye
2. Initialize: User runs `execute action run directive core init`
3. Choose: Pick demo or explore
4. Learn: Work through Demo 1-3
5. Try: Create first custom directive
6. Save: Store in user space
7. Understand: See how it works
```

### Journey 2: Experienced User (Building custom system)

```
1. Start: Learn phase 2 (harness features)
2. Build: Create complex multi-step directive
3. Orchestrate: Parallel execution + cost control
4. Iterate: Use state files + knowledge mutation
5. Showcase: Run advanced demos for ideas
6. Scale: Build production systems with tight packing
```

### Journey 3: Researcher (Mathematical exploration)

```
1. Learn: Demo 12-14 (self-evolving, proofs)
2. Setup: Configure state tracking
3. Explore: Run iterative attempts
4. Record: Knowledge entry for each discovery
5. Evolve: Use learnings in next iteration
6. Publish: Document solution path
```

### Journey 4: ML Engineer (Software building)

```
1. Learn: Demo 15-16 (software building, multi-agent)
2. Plan: Design system architecture
3. Decompose: Break into tight-context phases
4. Implement: Each phase uses previous outputs
5. Test: Integration tests between phases
6. Deploy: Complete verified system
```

---

## Conclusion

This strategy provides:

1. **Single package installation** - `pipx install rye`
2. **Progressive learning path** - 17 guided demos from basic to advanced
3. **Tight execution model** - Safety, cost control, deterministic behavior
4. **Self-improving systems** - State + knowledge mutation
5. **Complete showcases** - Math, software, multi-agent examples

**The power of Lilux + RYE:**

- **Lilux** = Kernel (stable, minimal)
- **RYE** = Content (essential, evolving)
- **Together** = AI-native execution with safety, accuracy, and scale

Users go from `pipx install rye` to building self-evolving, verified systems with complete context control.

---

_Document Status: Design for Implementation_  
_Last Updated: 2026-01-28_  
_Next: Create demo progression implementation plan_
