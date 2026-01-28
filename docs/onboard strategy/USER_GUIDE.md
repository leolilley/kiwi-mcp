# RYE User Guide: From Installation to Advanced Systems

**Date:** 2026-01-28  
**Version:** 0.1.0  
**Audience:** New and experienced users

---

## Quick Start (5 minutes)

### 1. Install

```bash
pipx install rye
```

That's it. You now have:
- ✓ Lilux kernel
- ✓ RYE core content
- ✓ MCP server ready
- ✓ All CLI tools

### 2. Configure Agent

Add to your Claude/Cursor/LLM config:

```json
{
  "mcpServers": {
    "lilux": {
      "command": "lilux",
      "args": ["serve"],
      "env": {
        "USER_SPACE": "/Users/yourname/.local/share/lilux"
      }
    }
  }
}
```

### 3. First Directive

Tell your agent:

```
execute action run directive core init
```

This:
- Creates user space: `~/.local/share/lilux/`
- Sets up directories
- Generates config
- Optional: Sets up vector search
- Ready to go!

### 4. Learn via Demos

```
execute action run directive core demo search directives
```

Then work through Phase 1 demos (search, load, create, sign).

---

## Understanding the System

### The 4 Core Tools

You have 4 MCP tools available to your agent:

#### 1. **Search** - Find things

```
execute action search directive keyword
execute action search tool "database"
execute action search knowledge "algorithms"
execute action search directive category:core/demo
```

**Returns:** Matching items with metadata

#### 2. **Load** - Read full content

```
execute action load directive core init
execute action load tool core validate
execute action load knowledge proof_by_induction
```

**Returns:** Complete item (metadata + content)

#### 3. **Execute** - Run things

```
execute action run directive core init
execute action run tool core validate /path/to/file
execute action run directive rye demo permissions cost
```

**Returns:** Execution result

#### 4. **Help** - Get guidance

```
execute action get help
execute action get help search
execute action get help directives
```

**Returns:** Usage guidance

---

## User Space Structure

When you run `init`, this is created:

```
~/.local/share/lilux/
├── user/
│   ├── directives/        ← Your custom directives
│   ├── tools/             ← Your custom tools/scripts
│   ├── knowledge/         ← Your custom knowledge
│   └── state/             ← Execution state (saved here)
├── cache/
│   ├── embeddings/        ← Vector search cache
│   └── indices/           ← Search indices
├── config.yaml            ← Your configuration
└── logs/                  ← Execution logs
```

### Key Paths

```bash
# Find your user space
echo $USER_SPACE
# Output: /Users/yourname/.local/share/lilux

# View your custom directives
ls ~/.local/share/lilux/user/directives/

# Check config
cat ~/.local/share/lilux/config.yaml

# See state files
ls ~/.local/share/lilux/user/state/
```

---

## Creating Your First Directive

### Option 1: Via Demo

```
execute action run directive core demo create directives
```

Interactive walkthrough. Creates a directive step-by-step.

### Option 2: Manual

Create file: `~/.local/share/lilux/user/directives/hello.md`

```xml
<directive name="hello" version="0.1.0">
  <metadata>
    <description>Simple hello world directive</description>
    <category>user/examples</category>
  </metadata>

  <process>
    <step name="greet">
      <instruction>
        Print a greeting message.
      </instruction>
      <tool>core/echo</tool>
      <parameters>
        <message>Hello from my first directive!</message>
      </parameters>
    </step>
  </process>
</directive>
```

Then run:

```
execute action run directive user/examples/hello
```

---

## State Files: Your Persistent Memory

State files let you remember things between runs.

### Basic Usage

#### Read State

```
execute action run directive user/examples/check state
```

Directive:
```xml
<step name="check_state">
  <instruction>
    Load state from ${USER_SPACE}/user/state/my_state.yaml
    Print what we remember
  </instruction>
  <tool>core/read_state</tool>
  <parameters>
    <state_file>my_state.yaml</state_file>
    <output>stdout</output>
  </parameters>
</step>
```

#### Write State

```xml
<step name="save_progress">
  <instruction>
    Save current progress to state file
  </instruction>
  <tool>core/write_state</tool>
  <parameters>
    <state_file>my_state.yaml</state_file>
    <data>
      attempt: 5
      best_score: 0.85
      last_updated: ${TIMESTAMP}
    </data>
  </parameters>
</step>
```

### Example: Tracking Progress

File: `~/.local/share/lilux/user/state/math_exploration.yaml`

```yaml
# Math problem solving session
problem: "Prove property X implies Y in graphs"
iterations: 5

attempts:
  - iteration: 1
    method: "direct_proof"
    time: 120
    status: "dead_end"
    learning: "Direct approach insufficient"
  
  - iteration: 2
    method: "contradiction"
    time: 180
    status: "partial_progress"
    learning: "Contradiction method helpful"
  
  - iteration: 3
    method: "induction"
    time: 90
    status: "success"
    learning: "Induction very effective"

best_attempt: 3
best_method: "induction"
```

Each run can read this, see previous attempts, and improve.

---

## Knowledge: Your Learning System

Knowledge entries are how your system learns.

### Create Knowledge

Directive:
```xml
<step name="save_learning">
  <instruction>
    Save what we learned to knowledge base
  </instruction>
  <tool>core/create_knowledge</tool>
  <parameters>
    <zettel_id>proof_induction_strategy</zettel_id>
    <title>Induction Method for Graph Proofs</title>
    <content>
      # Proof by Induction for Graph Properties
      
      Works well for: Properties on graph size
      
      Structure:
      1. Base case: Prove for n=1
      2. Inductive step: Assume true for n, prove for n+1
      
      Example: Proving edge properties
      - Base: n=1 (trivial)
      - Inductive: If true for n vertices, true for n+1
      
      Effectiveness: 9/10 for property proofs
    </content>
    <metadata>
      type: technique
      effectiveness: 9
      difficulty: medium
      related_problems: ["graph_theorem_1", "graph_theorem_2"]
    </metadata>
  </parameters>
</step>
```

### Update Knowledge

```xml
<step name="update_with_new_learning">
  <instruction>
    Update knowledge entry with new discovery
  </instruction>
  <tool>core/update_knowledge</tool>
  <parameters>
    <zettel_id>proof_induction_strategy</zettel_id>
    <add_learning>
      "Combining induction with caching made it 3x faster"
    </add_learning>
    <update_field>
      <effectiveness>9.5</effectiveness>
    </update_field>
  </parameters>
</step>
```

---

## Demos: Learn by Doing

### Phase 1: Meta Tools (Basic)

**Duration:** ~30 minutes total

1. **Search Directives** (5 min)
   ```
   execute action run directive core demo search directives
   ```
   Learn to find things.

2. **Load Directives** (5 min)
   ```
   execute action run directive core demo load directives
   ```
   Learn to read content.

3. **Create Directives** (10 min)
   ```
   execute action run directive core demo create directives
   ```
   Create your first directive.

4. **Execute & Sign** (10 min)
   ```
   execute action run directive core demo execute sign
   ```
   Run and verify directives.

### Phase 2: Core Harness (Intermediate)

**Duration:** ~60 minutes total

1. **Permissions & Cost** (15 min)
   ```
   execute action run directive rye demo permissions cost
   ```

2. **State Files** (15 min)
   ```
   execute action run directive rye demo state files
   ```

3. **Knowledge Evolution** (15 min)
   ```
   execute action run directive rye demo knowledge evolution
   ```

4. **Hooks & Plugins** (15 min)
   ```
   execute action run directive rye demo hooks plugins
   ```

### Phase 3: Advanced Orchestration (Advanced)

**Duration:** ~90 minutes total

1. **Deep Recursion** (20 min)
   ```
   execute action run directive rye demo deep recursion
   ```

2. **Parallel Orchestration** (20 min)
   ```
   execute action run directive rye demo parallel
   ```

3. **Tight Context** (20 min)
   ```
   execute action run directive rye demo tight context
   ```

4. **Self-Evolving** (30 min)
   ```
   execute action run directive rye demo self evolving
   ```

### Phase 4: Advanced Showcase (Expert)

**Duration:** Variable, 30-60 min each

1. **Genome Evolution**
   ```
   execute action run directive rye demo genome evolution
   ```

2. **Math Proofs**
   ```
   execute action run directive rye demo math proofs
   ```

3. **Software Building**
   ```
   execute action run directive rye demo software building
   ```

4. **Multi-Agent**
   ```
   execute action run directive rye demo multi agent
   ```

5. **Version Control**
   ```
   execute action run directive rye demo version control
   ```

---

## Common Workflows

### Workflow 1: Iterative Problem Solving

```
# Initialize with empty state
state.iteration = 0
state.attempts = []
state.best_score = 0
state.learnings = []

# Loop until solved
while not solved:
  iteration++
  
  # Run attempt (using previous learnings)
  result = execute_attempt_with_learnings()
  
  # Record attempt
  attempts.append(result)
  best_score = max(best_score, result.score)
  
  # Extract learnings
  learnings = extract_learnings(result)
  
  # Save state
  save_state()
  
  # Update knowledge
  if result.score >= threshold:
    create_knowledge_entry(learnings)
```

### Workflow 2: Building Multi-Component System

```
# Phase 1: Build Component A
directive_a = execute("build component_a")
save_artifact(directive_a.output, "component_a.py")

# Phase 2: Build Component B (depends on A)
directive_b = execute("build component_b", 
                      inputs=["component_a.py"])
save_artifact(directive_b.output, "component_b.py")

# Phase 3: Integration
directive_integrate = execute("integrate components",
                              inputs=["component_a.py", "component_b.py"])

# Phase 4: Testing
directive_test = execute("test system",
                         inputs=["component_a.py", "component_b.py", ...])

# Phase 5: Documentation
directive_docs = execute("generate docs",
                         inputs=[all_components])
```

### Workflow 3: Exploratory Research

```
# Problem: Find optimal algorithm for X

# Explore multiple approaches in parallel
results = parallel_execute([
  "try_approach_1",
  "try_approach_2",
  "try_approach_3",
  "try_approach_4",
])

# Pick best
best = max(results, key=lambda r: r.score)

# Deep dive on best
execute("deep_optimization", approach=best.approach)

# Record findings
create_knowledge_entry(findings)
```

---

## Debugging

### Check Logs

```bash
# See recent logs
tail -f ~/.local/share/lilux/logs/lilux.log

# Filter by level
grep ERROR ~/.local/share/lilux/logs/lilux.log
grep "core/init" ~/.local/share/lilux/logs/lilux.log
```

### Debug State

```bash
# See current state file
cat ~/.local/share/lilux/user/state/my_state.yaml

# Edit state (carefully!)
nano ~/.local/share/lilux/user/state/my_state.yaml
```

### Test Directive

```
execute action load directive my/test directive
```

This shows you the full directive structure. Check:
- Metadata valid?
- Steps defined correctly?
- Tool names correct?
- Parameters valid?

### Dry Run

```
execute action run directive my/test dry_run=true
```

Shows what would run without executing.

---

## Troubleshooting

### "Permission denied" on User Space

```bash
# Fix permissions
chmod -R u+rwx ~/.local/share/lilux/
```

### "Directive not found"

Make sure you're in the right namespace:
- Core directives: `core/name`
- RYE directives: `rye/name`
- Your directives: `user/name` (if in user space)

### "Tool execution failed"

Check:
1. Tool exists: `execute action search tool tool_name`
2. Tool has required parameters
3. Input files/paths exist
4. Permissions granted

### Vector search not working

Reinstall with vector support:

```bash
pipx upgrade rye --extra vector
rye-init --setup-vector
```

---

## Best Practices

### 1. Version Your Directives

Include version in metadata:
```xml
<metadata>
  <version>0.1.0</version>
</metadata>
```

Increment when you change them.

### 2. Record State Frequently

Save state after important steps:
```xml
<step name="save_checkpoint">
  <tool>core/write_state</tool>
  <parameters>
    <state_file>my_progress.yaml</state_file>
    <data>${CURRENT_STATE}</data>
  </parameters>
</step>
```

### 3. Document Your Directives

Add detailed descriptions:
```xml
<metadata>
  <description>Clear, one-line description</description>
</metadata>

<instructions>
  # What this does
  More detailed explanation of purpose and usage.
  
  Prerequisites:
  - State file exists
  - Component X loaded
  
  Output:
  - Saves result to state
  - Creates artifact.txt
</instructions>
```

### 4. Use Categories

Organize directives:
```
user/experiments/problem_1/
user/experiments/problem_2/
user/workflows/data_processing/
user/demos/tutorial_1/
```

### 5. Test Before Sharing

Run it once:
```
execute action run directive user/my_directive
```

Verify output before sharing or using in production.

---

## Advanced Topics

### Parallel Execution

```xml
<step name="parallel_searches">
  <instruction>
    Run multiple searches in parallel.
    Wait for all to complete.
    Merge results.
  </instruction>
  <orchestration>
    <type>parallel</type>
    <directives>
      - search_kb_1
      - search_kb_2
      - search_kb_3
    </directives>
    <wait_strategy>all_complete</wait_strategy>
    <merge_strategy>deduplicate_by_score</merge_strategy>
  </orchestration>
</step>
```

### Recursive Directives

```xml
<step name="recursive_solve">
  <instruction>
    Solve problem recursively.
    
    Base case: If problem size < threshold, solve directly
    Recursive: Break into smaller problems, solve each
  </instruction>
  <constraints>
    <max_depth>50</max_depth>
    <timeout_seconds>300</timeout_seconds>
  </constraints>
</step>
```

### Cost Control

```xml
<step name="expensive_operation">
  <instruction>
    This operation costs credits.
  </instruction>
  <cost>
    <estimate>5.0</estimate>
    <currency>credits</currency>
  </cost>
  <require_approval>true</require_approval>
</step>
```

---

## Getting Help

### In Agent

```
execute action get help directives
execute action get help tools
execute action get help demo
```

### Online

- Repository: https://github.com/leolilley/lilux-rye
- Issues: https://github.com/leolilley/lilux-rye/issues
- Discussions: https://github.com/leolilley/lilux-rye/discussions

### Community

Check knowledge entries:
```
execute action search knowledge "common patterns"
execute action search knowledge "troubleshooting"
```

---

## What's Next?

After quick start:

1. **Phase 1:** Work through 4 meta tool demos (30 min)
2. **Phase 2:** Learn harness features (1 hour)
3. **Create:** Build your own directive
4. **Explore:** Phase 3-4 demos as interested
5. **Build:** Create your own systems

---

_User Guide: Your journey from install to expertise_  
_Last Updated: 2026-01-28_  
_Questions? See troubleshooting or open an issue_
