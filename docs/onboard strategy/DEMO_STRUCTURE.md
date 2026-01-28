# RYE Demo System: Complete Structure

**Date:** 2026-01-28  
**Version:** 0.1.0  
**Purpose:** Define demo directives, progression, and implementation

---

## Overview

The demo system teaches users from basic (4 MCP tools) to advanced (self-evolving systems, multi-agent orchestration) through 17 guided walkthroughs, each runnable as a directive.

---

## Demo Progression Map

```
PHASE 1: Meta Tools (Learn the Interface) for directives, knowledge and tools
├─ Demo 1: help
├─ Demo 3: load
└─ Demo 2: sign
└─ Demo 4: execute
├─ Demo 5: search

PHASE 2: Core Harness (Learn the Infrastructure)
├─ Demo 6: threads & spawning threads with the mcp to use the mcp. spawn and observe a basic llm request thread spawn.
├─ Demo 5: permissions & cost control (after this you can crank it up)
├─ Demo 6: spawning threads to call other tools, file system, bash runnign, typical agent stuff.
└─ Demo 8: hooks

By this time user can now use the mcp to spawn agent threads that also have the mcp which they use to take classic agent actions.

not just how to orchestrate but also how to build up that plan doc of which you want to orchestrate

PHASE 3: Advanced Orchestration (Learn Patterns)
├─ Demo 9: parallel orchestration (building up the idea you want to orchestarte. what uqestions to ask when working our the kind of orchesrtaiotn you need, do you even need it at all)?
├─ Demo 9: recursion & safety
├─ Demo 11: tight context packing
└─ Demo 12: annealing (basic selve evolving)
├─ Demo 7: knowledge decision evolution
└─ Demo 12: self-evolving systems

PHASE 4: Advanced Showcase (See the Power)
├─ Demo 13: genome-type evolution
├─ Demo 14: proof generation & verification
├─ Demo 15: software building with tight context
├─ Demo 16: multi-agent orchestration
└─ Demo 17: state-based version control
```

---

## Phase 1: Meta Tools Demos

### Demo 1: Search Directives

**Directive:** `.ai/directives/core/demo_search_directives.md`

**Purpose:** Learn to find directives

```xml
<directive name="demo_search_directives" version="0.1.0">
  <metadata>
    <description>Walk through searching for directives</description>
    <category>core/demo</category>
    <phase>1</phase>
    <duration_minutes>5</duration_minutes>
  </metadata>

  <process>
    <step name="welcome">
      <description>Welcome message</description>
      <instruction>
        Let's learn how to FIND directives using the search tool.

        You have a tool called "search" that helps you find directives
        by keyword, category, or name.

        Let's try it!
      </instruction>
    </step>

    <step name="search_by_name">
      <description>Search for directives by name</description>
      <instruction>
        First, let's search for the "init" directive:

        execute action search directive init

        This should return all directives with "init" in the name.
      </instruction>
      <verification>
        Should find: core/init, rye/init, etc.
      </verification>
    </step>

    <step name="search_by_category">
      <description>Search by category</description>
      <instruction>
        Now let's search by category:

        execute action search directive category:core

        This returns all directives in the "core" category.
      </instruction>
    </step>

    <step name="list_all_demos">
      <description>List all demo directives</description>
      <instruction>
        Let's see all demos:

        execute action search directive category:core/demo

        You should see all 17 demos in the progression.
      </instruction>
    </step>

    <step name="explore">
      <description>Explore what you found</description>
      <instruction>
        Pick a directive from the results.

        Next step, we'll use the "load" tool to see what's inside.
      </instruction>
    </step>
  </process>

  <outcomes>
    <success>
      You understand:
      - The search tool searches directives, tools, knowledge
      - Search supports: keywords, categories, metadata
      - Results include metadata (version, author, description)
      - Next: Learn what's inside with "load"
    </success>
  </outcomes>
</directive>
```

### Demo 2: Load Directives

**Directive:** `.ai/directives/core/demo_load_directives.md`

**Purpose:** Learn to inspect directive contents

**Structure:**

1. Show how to load a directive
2. Explain directive anatomy (metadata, steps, instructions)
3. Show tool calls within directives
4. Explain execution flow

### Demo 3: Create Directives

**Directive:** `.ai/directives/core/demo_create_directives.md`

**Purpose:** Create your first directive

**Structure:**

1. Show directive template
2. Guided step-by-step creation
3. User creates "hello_world" directive
4. Save to user space
5. Verify it was created

### Demo 4: Execute & Sign

**Directive:** `.ai/directives/core/demo_execute_sign.md`

**Purpose:** Run directives and verify them

**Structure:**

1. Execute the created "hello_world" directive
2. Explain integrity checking
3. Learn about signing directives
4. Understand versioning

---

## Phase 2: Core Harness Demos

### Demo 5: Permissions & Cost Control

**Directive:** `.ai/directives/rye/demo_permissions_cost.md`

**Teaches:**

- Permission tokens and capabilities
- Cost estimation
- Budget constraints
- Approval workflows
- How to grant/revoke permissions

**Example walkthrough:**

```
Step 1: Attempt restricted operation
  → Get permission denied
  → See what's required

Step 2: Request permission
  → See cost estimation
  → Accept/reject

Step 3: Operation succeeds
  → Cost deducted
  → Logged to state

Step 4: Check budget
  → See spending history
  → Understand limits
```

### Demo 6: State Files & Mutation

**Directive:** `.ai/directives/rye/demo_state_files.md`

**Teaches:**

- State file format (YAML, JSON)
- Reading/writing state
- Persistence between runs
- Version tracking
- Rollback capabilities

**Hands-on:**

1. Create a state file
2. Write data to it
3. Update in next execution
4. See history
5. Rollback to previous version

### Demo 7: Knowledge Evolution

**Directive:** `.ai/directives/rye/demo_knowledge_evolution.md`

**Teaches:**

- Creating knowledge entries
- Frontmatter (metadata)
- Relationships between entries
- Updating knowledge over time
- Building knowledge graphs

**Example:**

1. Create initial knowledge entry
2. Run experiments
3. Update entry with learnings
4. Link related entries
5. See evolved knowledge

### Demo 8: Hooks & Plugins

**Directive:** `.ai/directives/rye/demo_hooks_plugins.md`

**Teaches:**

- Pre/post execution hooks
- Custom validations
- Integration points
- Plugin registration
- Event handlers

---

## Phase 3: Advanced Orchestration Demos

### Demo 9: Deep Recursion & Safety

**Directive:** `.ai/directives/rye/demo_deep_recursion.md`

**Example:** Tower of Hanoi solver

```xml
<directive name="solve_hanoi_recursive">
  <!-- Demonstrates safe recursion -->
  <step name="setup">
    <instruction>Hanoi problem: Move n disks with constraints</instruction>
  </step>

  <step name="solve_recursive">
    <instruction>
      Base case: n=1, move disk directly
      Recursive case: break problem into smaller pieces
      Depth limit: max_depth=10 (prevents infinite recursion)
      Timeout: 60 seconds (prevents runaway)
    </instruction>
  </step>

  <step name="verify_solution">
    <instruction>Each recursive call is validated</instruction>
  </step>
</directive>
```

**Teaches:**

- Recursive directives
- Base case definition
- Depth limiting
- Resource cleanup
- Guaranteed termination

### Demo 10: Parallel Orchestration

**Directive:** `.ai/directives/rye/demo_parallel.md`

**Example:** Parallel search across multiple repositories

```
Task: Search for pattern in 4 different knowledge bases

Sequential: Takes 20 seconds
Parallel: Takes 5 seconds

Orchestration:
1. Spawn 4 search directives (one per KB)
2. Each runs independently
3. Collect results as they complete
4. Merge and deduplicate
5. Return aggregated results
```

**Teaches:**

- Spawning multiple directives
- Wait strategies (all vs. first-complete)
- Result aggregation
- Error handling in parallel
- Resource pooling

### Demo 11: Tight Context Packing

**Directive:** `.ai/directives/rye/demo_tight_context.md`

**Contrast:**

```
LOOSE CONTEXT (Causes hallucination):
"Here's everything about cryptography...
 [5000 tokens of background info]
 Your task: Implement AES encryption"

Problem: LLM gets confused, generates irrelevant code

TIGHT CONTEXT (Prevents hallucination):
"You are implementing Step 3 of AES: SubBytes transformation.
 Input: 4x4 byte matrix (see sbox_table.py)
 Output: Transformed 4x4 matrix
 Format: Python function with type hints
 Length: ~20 lines
 Example: transform([[0x19, ...], ...]) -> [[0x15, ...], ...]"

Result: LLM focuses precisely, produces exact output
```

**Teaches:**

- Minimal context injection
- Explicit step definition
- Output format specification
- Example-driven prompting
- Predictable LLM behavior

### Demo 12: Self-Evolving Systems

**Directive:** `.ai/directives/rye/demo_self_evolving.md`

**Example:** Iterative problem solver

```
Iteration tracking:
  state.iteration = 1
  state.attempts = []
  state.learnings = []
  state.best_solution = null

Iteration 1:
  - Attempt random approach
  - Log result
  - Extract learnings: "Random search is too slow"
  - Save to knowledge

Iteration 2:
  - Use learnings from iteration 1
  - Try guided search
  - Faster! Log improvement
  - Extract new learnings: "Heuristic X helps"

Iteration 3:
  - Use learnings from iterations 1-2
  - Try heuristic-guided search with optimization
  - Found solution!

Each iteration:
- Uses knowledge from previous runs
- Gets faster/better
- Feeds improvements back into knowledge
```

**Teaches:**

- Loop structure with state tracking
- Learning capture
- Knowledge mutation
- Convergence patterns
- Reproducible iteration

---

## Phase 4: Advanced Showcase Demos

### Demo 13: Genome-Type Evolution

**Directive:** `.ai/directives/rye/demo_genome_evolution.md`

**Example:** Algorithm evolution

```
Encoding: "algorithm DNA"
  Each algorithm = sequence of operations
  Fitness = performance score

Generation 1: Random algorithms
  [algo_1: random bubble sort variant] → fitness: 2/10
  [algo_2: random quick sort variant] → fitness: 7/10
  [algo_3: random merge sort variant] → fitness: 5/10

Selection: Keep best 50%
  Keep algo_2 (7/10)
  Cull the rest

Crossover: Breed best variants
  algo_2 + algo_3 = hybrid algorithm → fitness: 8/10

Mutation: Random changes
  Hybrid + caching optimization = fast hybrid → fitness: 9/10

Generation 2: Refined population
  [fast hybrid] → 9/10
  [algorithm 2 variant] → 7.5/10
  [new mutation] → 6/10

Evolution:
  G1 best: 7/10
  G2 best: 9/10
  G3 best: 9.8/10
  → System discovers better algorithms
```

**Teaches:**

- Encoding solutions as "DNA"
- Fitness evaluation
- Selection strategies
- Crossover/mutation operators
- Population evolution
- Convergence to optimal solutions

### Demo 14: Proof Generation & Verification

**Directive:** `.ai/directives/rye/demo_proofs.md`

**Example:** Proving graph properties

```
Theorem: "In connected graph G, X implies Y"

Attempt 1: Direct proof
  Approach: Show X → Y directly
  Result: Dead end (saved to knowledge)
  Learning: "Direct approach insufficient"

Attempt 2: Proof by contradiction
  Approach: Assume ¬Y and derive contradiction
  Result: Partial progress
  Learning: "Contradiction method helpful but incomplete"

Attempt 3: Induction on graph size
  Base case: Proven for n=1
  Inductive step: If true for n, true for n+1
  Result: Complete proof!

Record in knowledge:
  entry_id: proof_graph_property_x_implies_y
  status: verified
  method: mathematical_induction
  complexity: O(n²) verification
  references: [attempt_1, attempt_2]
  learnings: ["Induction most effective", "Contradiction helpful for insight"]
```

**Teaches:**

- Formal proof structure
- Multiple proof strategies
- Verification with code
- Recording proofs in knowledge
- Building proof libraries

### Demo 15: Software Building with Tight Context

**Directive:** `.ai/directives/rye/demo_software_building.md`

**Example:** Building ML classifier

```
Architecture: 5 modules, built sequentially

Module 1: DataLoader
  Specification:
    Input: CSV file path
    Output: Pandas DataFrame
    Interface: DataLoader.load(path) → DataFrame
    Tests: Load, validate schema, handle errors

  Tight Context:
    "Write a DataLoader class that loads CSV files.
     Input: path (str)
     Output: pd.DataFrame
     Methods: load(path), validate_schema(), handle_missing()
     Write tests.
     Total: ~50 lines"

  Agent: Creates data_loader.py with tests
  Verification: Tests pass ✓

Module 2: FeatureExtractor
  Depends on: data_loader.py
  Specification:
    Input: DataFrame from DataLoader
    Output: Feature matrix (numpy array)
    Methods: extract_features(df) → array

  Tight Context:
    "Write FeatureExtractor using DataLoader.
     Input: DataFrame from module 1
     Output: numpy array of features
     Methods: extract_features(df)
     Include tests that use DataLoader.
     Total: ~75 lines"

  Agent: Creates feature_extractor.py
  Verification: Integration test with DataLoader ✓

Module 3: Classifier
  Depends on: feature_extractor.py, data_loader.py
  Specification:
    Input: Feature matrix from FeatureExtractor
    Output: Class predictions
    Methods: train(), predict()

  Tight Context:
    "Write Classifier using FeatureExtractor.
     train(X, y): Train classifier
     predict(X): Return predictions
     Use modules 1-2 for integration test.
     Total: ~100 lines"

  Agent: Creates classifier.py
  Verification: E2E test ✓

Module 4: API
  Depends on: All previous modules
  Specification:
    Expose prediction service
    REST API with Flask

  Tight Context:
    "Write Flask API exposing classifier.
     GET /predict?data=...
     POST /batch_predict with CSV
     Use all previous modules.
     Total: ~60 lines"

  Agent: Creates api.py
  Verification: API tests ✓

Module 5: Tests & Docs
  Depends on: All modules
  Specification:
    Comprehensive test suite
    API documentation
    Usage guide

  Agent: Creates tests.py, docs/
  Verification: All tests pass, docs complete ✓

Result: Complete, verified ML system
  Each module: ~50-100 lines
  Each built with tight context
  Each verified before next
  Total: ~350 lines of production code
```

**Teaches:**

- Modular decomposition
- Tight context per module
- Interface definition
- Dependency management
- Integration testing
- Documentation generation

### Demo 16: Multi-Agent Orchestration

**Directive:** `.ai/directives/rye/demo_multi_agent.md`

**Example:** Parallel problem-solving teams

```
Problem: Solve a complex optimization problem

Team:
  Agent A: Mathematician
    Task: Develop theoretical framework
    Tools: Knowledge search, proof verification
    Output: Mathematical formulation

  Agent B: Engineer
    Task: Design algorithm based on math
    Tools: Code generation, testing
    Inputs: Math formulation from A
    Output: Algorithm implementation

  Agent C: Researcher
    Task: Find relevant papers/solutions
    Tools: Knowledge search, analysis
    Output: Related work summary

  Agent D: Optimizer
    Task: Optimize for performance
    Tools: Profiling, testing
    Inputs: Algorithm from B
    Output: Optimized version

Orchestration:
  1. Spawn all 4 agents simultaneously
  2. Agent C works immediately
  3. Agents A starts theoretical work
  4. A completes → feeds to B
  5. B creates algorithm → feeds to D
  6. D optimizes while C is still searching
  7. C completes → aggregate with B's work
  8. D completes → ready to use

  Timeline: Parallel execution, coordinated handoffs
  Result: Multi-perspective solution

Messages between agents:
  A → B: "Use this mathematical framework"
  C → (all): "Found these related papers"
  B → D: "Here's algorithm to optimize"
  D → (all): "Optimized version ready"
```

**Teaches:**

- Multiple concurrent agents
- Role assignment
- Message passing
- Coordinated execution
- Result aggregation
- Conflict resolution

### Demo 17: State-Based Version Control

**Directive:** `.ai/directives/rye/demo_version_control.md`

**Example:** Exploring solution space

```
Checkpoint A (Base attempt)
  state.attempt_id = "base"
  state.score = 45%
  state.approach = "brute_force"
  state.timestamp = 2026-01-28T10:00:00Z

Branch 1: Optimize with caching
  checkpoint: "base"
  state.attempt_id = "cache_opt"
  state.score = 52%
  state.approach = "brute_force + caching"
  state.parent = "base"

Branch 2: Change algorithm family
  checkpoint: "base"
  state.attempt_id = "dynamic_prog"
  state.score = 49%
  state.approach = "dynamic_programming"
  state.parent = "base"

Branch 3: Hybrid from best
  checkpoint: "cache_opt"
  state.attempt_id = "hybrid"
  state.score = 58%
  state.approach = "caching + heuristic"
  state.parent = "cache_opt"

Checkpoint B (Converge to best)
  state.attempt_id = "v2"
  state.score = 58%
  state.best_parent = "hybrid"
  state.merge_from = ["cache_opt", "dynamic_prog", "hybrid"]
  state.timestamp = 2026-01-28T10:30:00Z

Exploration tree:
  Base (45%) ──→ Cache (52%) ──→ Hybrid (58%) ──→ Checkpoint B
            └──→ DynProg (49%)

Capabilities:
  - Checkpoint at any point
  - Branch for exploration
  - Roll back to known state
  - Merge best approaches
  - Reproducible from any checkpoint
  - Version history with lineage
```

**Teaches:**

- Checkpointing state
- Branching for exploration
- Merging best solutions
- Rollback capability
- Reproducibility
- Version tree navigation

---

## Implementation Checklist

### Phase 1: Meta Tools (Initial 0.1.0)

- [ ] Demo 1 directive: search_directives
- [ ] Demo 2 directive: load_directives
- [ ] Demo 3 directive: create_directives
- [ ] Demo 4 directive: execute_sign
- [ ] Guide users through Phase 1
- [ ] Verify each demo works end-to-end

### Phase 2: Core Harness (0.2.0)

- [ ] Demo 5 directive: permissions_cost
- [ ] Demo 6 directive: state_files
- [ ] Demo 7 directive: knowledge_evolution
- [ ] Demo 8 directive: hooks_plugins
- [ ] Implement permission system
- [ ] Implement state file management
- [ ] Document harness features

### Phase 3: Advanced Orchestration (0.3.0)

- [ ] Demo 9 directive: deep_recursion
- [ ] Demo 10 directive: parallel_orchestration
- [ ] Demo 11 directive: tight_context
- [ ] Demo 12 directive: self_evolving_systems
- [ ] Implement recursion safety
- [ ] Implement parallel execution
- [ ] Document patterns

### Phase 4: Advanced Showcase (0.4.0)

- [ ] Demo 13 directive: genome_evolution
- [ ] Demo 14 directive: proofs
- [ ] Demo 15 directive: software_building
- [ ] Demo 16 directive: multi_agent
- [ ] Demo 17 directive: version_control
- [ ] Create example code for each
- [ ] Comprehensive guides

### Polish (1.0.0)

- [ ] All demos complete
- [ ] Tutorial guides for each phase
- [ ] Video walkthroughs (optional)
- [ ] Integration tests
- [ ] Performance optimization
- [ ] Production readiness

---

## Demo Metadata Standard

Every demo directive includes:

```xml
<metadata>
  <description>One-line description</description>
  <category>core/demo or rye/demo</category>
  <phase>1-4</phase>
  <duration_minutes>5-30</duration_minutes>
  <prerequisites>["demo_X", "demo_Y"]</prerequisites>
  <learning_objectives>
    - Objective 1
    - Objective 2
    - Objective 3
  </learning_objectives>
  <difficulty>beginner|intermediate|advanced</difficulty>
  <estimated_output_lines>50-500</estimated_output_lines>
</metadata>
```

---

## Key Principles

1. **Each demo is self-contained** but builds on previous
2. **Each teaches one concept** clearly
3. **Each is runnable** from start to finish
4. **Each generates artifacts** (files, state, knowledge)
5. **Progressive complexity** from simple to advanced
6. **Clear success criteria** for each demo
7. **Real examples** not toy examples
8. **Hands-on practice** not just reading

---

_Document Status: Design for Implementation_  
_Last Updated: 2026-01-28_  
_Next: Implement Phase 1 demos_
