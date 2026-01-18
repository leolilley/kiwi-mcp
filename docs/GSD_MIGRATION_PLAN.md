# Kiwi MCP Enhancement Plan: Advanced Workflow Patterns

**Purpose:** Enhancement plan to implement advanced workflow patterns in Kiwi MCP using directive-based prompting and subagent orchestration.

**Approach:** All features will be implemented as directives, scripts, and knowledge entries - using the Kiwi MCP tool ecosystem exclusively.

**Philosophy:** Kiwi uses a **universal agent model** - any agent can run any directive. What other frameworks call specialized "agents" (executor, planner, verifier) are simply directives that define workflows.

---

## Table of Contents

1. [Enhancement Philosophy](#enhancement-philosophy)
2. [Harness Compatibility](#harness-compatibility)
3. [Implementation Architecture](#implementation-architecture)
4. [Phase 1: Core Infrastructure](#phase-1-core-infrastructure)
5. [Phase 2: Workflow System](#phase-2-workflow-system)
6. [Phase 3: Verification & Quality](#phase-3-verification--quality)
7. [Phase 4: Context Engineering](#phase-4-context-engineering)
8. [Full Directive Catalog](#full-directive-catalog)
9. [Knowledge Entries to Create](#knowledge-entries-to-create)
10. [Directive Metadata Updates](#directive-metadata-updates)
11. [Implementation Order](#implementation-order)

---

## Enhancement Philosophy

### Core Principles

1. **Directive-First:** Every workflow pattern becomes a directive
2. **Universal Agent:** No specialized agents - any agent runs any directive via model routing
3. **Subagent Orchestration:** Complex workflows use parallel subagents
4. **Knowledge-Informed:** Domain knowledge captured in knowledge entries
5. **Script-Backed:** Heavy computation delegated to Python scripts
6. **Harness-Agnostic:** Works across Claude Code, Amp, and OpenCode

### Universal Agent Model

Kiwi's key design principle: **There are no specialized agents.** Instead:

- Every directive can be run by any agent
- `model_class` metadata determines which LLM tier handles the directive
- Complex behavior emerges from directive composition, not agent specialization

| Traditional Approach | Kiwi MCP Approach                       |
| -------------------- | --------------------------------------- |
| Executor Agent       | `execution/execute_plan.md` directive   |
| Planner Agent        | `workflows/plan_phase.md` directive     |
| Verifier Agent       | `verification/verify_work.md` directive |
| Researcher Agent     | `workflows/research_topic.md` directive |
| Debugger Agent       | `workflows/debug_issue.md` directive    |

The universal agent:

1. Receives a task
2. Searches for relevant directives
3. Loads and executes directives
4. Uses model routing via `model_class` to select appropriate LLM tier

### Mapping Concepts → Kiwi MCP

| Concept           | Kiwi MCP Implementation               |
| ----------------- | ------------------------------------- |
| Slash Command     | Directive (via agent dispatch table)  |
| Workflow          | Orchestrator directive with subagents |
| Specialized Agent | Directive with specific `model_class` |
| Template          | Knowledge entry (templates/)          |
| Reference         | Knowledge entry (patterns/)           |
| .planning/        | .ai/state/ + .ai/plans/               |
| PLAN.md           | Directive + progress doc              |
| SUMMARY.md        | Execution summary knowledge entry     |
| STATE.md          | .ai/state/workflow_state.yaml         |

---

## Harness Compatibility

### The Three Harnesses

| Harness         | Subagent Mechanism       | Parallel Support | Notes                                         |
| --------------- | ------------------------ | ---------------- | --------------------------------------------- |
| **Amp**         | `Task()` tool            | Full parallel    | Native subagent spawning, wait for completion |
| **Claude Code** | Slash commands + context | Limited          | Manual handoff, checkpoint files              |
| **OpenCode**    | Thread-based             | Experimental     | Agent pools, async execution                  |

### Subagent Invocation Pattern

The key insight from our existing patterns: **Directives are the instruction manual. Subagents read the manual.**

```xml
<step name="execute_with_subagents" parallel="true">
  <action>
    Spawn subagents, each executing one directive:

    Task("Execute directive: {directive_name} with inputs: {inputs}")
  </action>
</step>
```

### Harness Detection

Directives can detect which harness is running:

```xml
<step name="detect_harness">
  <action><![CDATA[
Check for harness indicators:
- Task tool available → Amp
- claude command context → Claude Code
- opencode context → OpenCode

Set: harness_type = detected harness
Adjust subagent strategy accordingly.
  ]]></action>
</step>
```

---

## Implementation Architecture

### Folder Structure

Integration into existing Kiwi structure (no new top-level categories):

```
.ai/
├── directives/
│   ├── core/                    # Existing core directives
│   ├── meta/                    # Existing orchestration directives
│   │   ├── orchestrate_general.md
│   │   ├── resume_orchestration_directive.md
│   │   └── orchestrate_phase.md        # NEW: Phase orchestration
│   │
│   ├── workflows/               # Enhanced workflows
│   │   ├── plan_implementation.md      # Existing
│   │   ├── plan_phase.md               # NEW: Phase planning
│   │   ├── execute_plan.md             # NEW: Plan execution
│   │   ├── verify_work.md              # NEW: Work verification
│   │   ├── research_topic.md           # NEW: Research workflow
│   │   ├── debug_issue.md              # NEW: Debugging workflow
│   │   └── new_project.md              # NEW: Project initialization
│   │
│   ├── state/                   # NEW: State management
│   │   ├── init_state.md
│   │   ├── update_state.md
│   │   ├── checkpoint.md
│   │   ├── resume_state.md
│   │   └── resolve_checkpoint.md
│   │
│   └── verification/            # NEW: Verification directives
│       ├── verify_exists.md
│       ├── verify_substantive.md
│       ├── verify_wired.md
│       └── verify_functional.md
│
├── knowledge/
│   ├── patterns/
│   │   ├── orchestration/       # Existing + enhanced
│   │   │   ├── 004-parallel-execution-pattern.md
│   │   │   └── wave-execution.md           # NEW
│   │   │
│   │   ├── checkpoints/         # NEW: Checkpoint patterns
│   │   │   ├── human-verify.md
│   │   │   ├── decision-checkpoint.md
│   │   │   └── human-action.md
│   │   │
│   │   ├── deviation-handling/  # NEW: Deviation patterns
│   │   │   ├── auto-fix-rules.md
│   │   │   └── escalation-patterns.md
│   │   │
│   │   ├── verification/        # Enhanced verification
│   │   │   ├── verification-levels.md      # NEW
│   │   │   └── stub-detection.md           # NEW
│   │   │
│   │   └── context-engineering/ # NEW: Context patterns
│   │       ├── quality-curve.md
│   │       ├── task-sizing.md
│   │       └── progressive-disclosure.md
│   │
│   └── templates/               # Enhanced templates
│       ├── project.md
│       ├── requirements.md
│       ├── roadmap.md
│       ├── state.md
│       ├── summary.md
│       ├── plan.md
│       └── verification.md
│
├── state/                       # NEW: Workflow state
│   ├── current_workflow.yaml
│   ├── checkpoints/
│   └── snapshots/
│
├── plans/                       # Existing + enhanced
│   └── {project}_plan.md
│
└── progress/                    # Existing + enhanced
    └── {workflow}_progress.md
```

---

## Phase 1: Core Infrastructure

### 1.1 State Management System

**Directive: `state/init_state.md`**

```xml
<directive name="init_state" version="1.0.0">
  <metadata>
    <description>Initialize workflow state tracking for a project</description>
    <category>state</category>
    <model_class tier="fast" fallback="balanced" parallel="false">
      State file creation and initialization
    </model_class>
    <permissions>
      <write resource="filesystem" path=".ai/state/**/*" />
    </permissions>
  </metadata>

  <inputs>
    <input name="project_name" type="string" required="true">
      Name of the project
    </input>
    <input name="plan_doc" type="string" required="false">
      Path to plan document if exists
    </input>
  </inputs>

  <process>
    <step name="create_state_dir">
      <action>Create .ai/state/ directory if not exists</action>
    </step>

    <step name="create_state_file">
      <action><![CDATA[
Create .ai/state/current_workflow.yaml:

workflow:
  project: {project_name}
  created: {ISO timestamp}
  status: initialized

position:
  current_phase: 0
  total_phases: 0
  current_step: null
  progress: 0%

context:
  decisions: []
  deviations: []

session:
  last_activity: {timestamp}
  can_resume: true
      ]]></action>
    </step>
  </process>
</directive>
```

**Directive: `state/update_state.md`**

```xml
<directive name="update_state" version="1.0.0">
  <metadata>
    <description>Update workflow state after step completion</description>
    <category>state</category>
    <model_class tier="fast" fallback="balanced" parallel="false">
      Simple file update operation
    </model_class>
    <permissions>
      <read resource="filesystem" path=".ai/state/**/*" />
      <write resource="filesystem" path=".ai/state/**/*" />
    </permissions>
  </metadata>

  <inputs>
    <input name="step_completed" type="string" required="true">Step name</input>
    <input name="status" type="string" required="false">New status</input>
    <input name="decision" type="object" required="false">Decision made</input>
    <input name="deviation" type="object" required="false">Deviation recorded</input>
  </inputs>

  <process>
    <step name="read_state">
      <action>Read .ai/state/current_workflow.yaml</action>
    </step>

    <step name="update_fields">
      <action><![CDATA[
Update relevant fields:
- position.current_step = {step_completed}
- session.last_activity = {now}
- If decision: append to context.decisions
- If deviation: append to context.deviations
- Recalculate progress percentage
      ]]></action>
    </step>

    <step name="write_state">
      <action>Write updated state back to file</action>
    </step>
  </process>
</directive>
```

### 1.2 Checkpoint System

**Directive: `state/checkpoint.md`**

```xml
<directive name="checkpoint" version="1.0.0">
  <metadata>
    <description>Create a checkpoint for human interaction</description>
    <category>state</category>
    <model_class tier="fast" fallback="balanced" parallel="false">
      Create checkpoint and await resolution
    </model_class>
    <permissions>
      <write resource="filesystem" path=".ai/state/**/*" />
    </permissions>
  </metadata>

  <inputs>
    <input name="checkpoint_type" type="string" required="true">
      Type: human-verify | decision | human-action
    </input>
    <input name="description" type="string" required="true">
      What needs to be verified/decided/done
    </input>
    <input name="context" type="string" required="false">
      Additional context for the human
    </input>
    <input name="options" type="array" required="false">
      For decision type: list of options
    </input>
  </inputs>

  <process>
    <step name="determine_checkpoint_type">
      <action><![CDATA[
Checkpoint types (in order of frequency):

1. human-verify (90% of checkpoints):
   - Verify visual/functional behavior
   - "Does the login form look correct?"
   - Gate: blocking (must pass to continue)

2. decision (9% of checkpoints):
   - Architecture or technology choices
   - "Should we use Redis or Memcached for caching?"
   - Gate: blocking (need human decision)

3. human-action (1% of checkpoints):
   - Truly unavoidable manual steps
   - "Please add your API key to .env"
   - Gate: blocking (need external action)
      ]]></action>
    </step>

    <step name="create_checkpoint_file">
      <action><![CDATA[
Create .ai/state/checkpoints/{timestamp}_{type}.yaml:

checkpoint:
  id: {uuid}
  type: {checkpoint_type}
  created: {timestamp}
  status: pending

request:
  description: {description}
  context: {context}
  options: {options if decision type}

verification:
  how_to_verify: {steps for human}
  expected_result: {what success looks like}

resolution:
  resolved_at: null
  resolution: null
  notes: null
      ]]></action>
    </step>

    <step name="present_to_human">
      <action><![CDATA[
Present checkpoint clearly:

---
## ⏸️ Checkpoint: {checkpoint_type}

{description}

{if human-verify}
### How to Verify
{verification steps}

Reply with:
- "approved" - to continue
- "issue: {description}" - if something's wrong
{/if}

{if decision}
### Options
{numbered list of options}

Reply with the number or describe your choice.
{/if}

{if human-action}
### Action Required
{what they need to do}

Reply "done" when complete.
{/if}
---
      ]]></action>
    </step>
  </process>
</directive>
```

**Directive: `state/resolve_checkpoint.md`**

```xml
<directive name="resolve_checkpoint" version="1.0.0">
  <metadata>
    <description>Resolve a pending checkpoint and continue workflow</description>
    <category>state</category>
    <model_class tier="fast" fallback="balanced" parallel="false">
      Parse resolution and update state
    </model_class>
    <permissions>
      <read resource="filesystem" path=".ai/state/**/*" />
      <write resource="filesystem" path=".ai/state/**/*" />
    </permissions>
  </metadata>

  <inputs>
    <input name="checkpoint_id" type="string" required="false">
      ID of checkpoint to resolve (uses most recent if not specified)
    </input>
    <input name="resolution" type="string" required="true">
      Human's response: approved, issue, decision, done
    </input>
    <input name="notes" type="string" required="false">
      Additional notes from human
    </input>
  </inputs>

  <process>
    <step name="load_checkpoint">
      <action>Load checkpoint file from .ai/state/checkpoints/</action>
    </step>

    <step name="parse_resolution">
      <action><![CDATA[
Parse human response:

- "approved" / "yes" / "looks good" → passed
- "issue: ..." / "problem: ..." → issue_found
- "1" / "2" / option text → decision_made
- "done" / "completed" → action_completed

Record:
- resolution_type
- resolution_details
- timestamp
      ]]></action>
    </step>

    <step name="update_checkpoint">
      <action><![CDATA[
Update checkpoint file:
- resolution.resolved_at = {now}
- resolution.resolution = {parsed resolution}
- resolution.notes = {notes}
- status = resolved

Move to .ai/state/checkpoints/resolved/
      ]]></action>
    </step>

    <step name="route_by_resolution">
      <action><![CDATA[
Based on resolution:

- passed → Continue with next step
- issue_found →
  1. Record issue details
  2. Determine if auto-fixable
  3. Either fix and re-verify, or ask for guidance
- decision_made →
  1. Record decision in state
  2. Continue with chosen path
- action_completed →
  1. Verify action if possible
  2. Continue workflow
      ]]></action>
    </step>
  </process>
</directive>
```

### 1.3 Resume Capability

**Directive: `state/resume_state.md`**

```xml
<directive name="resume_state" version="1.0.0">
  <metadata>
    <description>Resume workflow from saved state</description>
    <category>state</category>
    <model_class tier="balanced" fallback="reasoning" parallel="false">
      Analyze state and determine resume point
    </model_class>
    <permissions>
      <read resource="filesystem" path=".ai/state/**/*" />
      <read resource="filesystem" path=".ai/plans/**/*" />
    </permissions>
  </metadata>

  <inputs>
    <input name="project_name" type="string" required="false">
      Project to resume (auto-detects if one active)
    </input>
  </inputs>

  <process>
    <step name="load_state">
      <action><![CDATA[
Load .ai/state/current_workflow.yaml

Check:
- session.can_resume == true
- Last activity timestamp
- Current position
      ]]></action>
    </step>

    <step name="check_pending_checkpoints">
      <action><![CDATA[
Check .ai/state/checkpoints/ for pending items.

If pending checkpoint exists:
  1. Load checkpoint details
  2. Present to user for resolution
  3. Wait for resolution before continuing
      ]]></action>
    </step>

    <step name="reconstruct_context">
      <action><![CDATA[
Build minimal context for continuation:

1. Load current phase plan from .ai/plans/
2. Load decisions made (from state)
3. Load deviations recorded
4. Identify next step

Present:
## 📍 Resuming Workflow

**Project:** {project_name}
**Phase:** {current_phase} of {total_phases}
**Progress:** {progress}%
**Last Step:** {last_completed_step}

### Decisions Made
{list of decisions}

### Next Up
{next_step.description}

Ready to continue?
      ]]></action>
    </step>

    <step name="continue_workflow">
      <action><![CDATA[
On user confirmation:
1. Update session.last_activity
2. Load next step details
3. Execute from current position
      ]]></action>
    </step>
  </process>
</directive>
```

---

## Phase 2: Workflow System

### 2.1 Planning Workflow

**Directive: `workflows/plan_phase.md`**

```xml
<directive name="plan_phase" version="1.0.0">
  <metadata>
    <description>Create detailed implementation plan for a project phase</description>
    <category>workflows</category>
    <model_class tier="reasoning" fallback="expert" parallel="false">
      Complex planning requires deep reasoning
    </model_class>
    <permissions>
      <read resource="filesystem" path="**/*" />
      <write resource="filesystem" path=".ai/plans/**/*" />
    </permissions>
  </metadata>

  <inputs>
    <input name="phase_num" type="integer" required="true">
      Phase number to plan
    </input>
    <input name="roadmap_path" type="string" required="false">
      Path to roadmap document
    </input>
  </inputs>

  <process>
    <step name="load_phase_goal">
      <action><![CDATA[
Load roadmap and extract phase goal:
- Phase name and objective
- Must-have deliverables
- Nice-to-have features
- Dependencies on previous phases
      ]]></action>
    </step>

    <step name="analyze_codebase">
      <action><![CDATA[
Understand current state:
- Existing files and structure
- Patterns already in use
- Technologies and frameworks
- Relevant code to modify
      ]]></action>
    </step>

    <step name="create_task_breakdown">
      <action><![CDATA[
Break phase into plans following the 2-3 task rule:

Load knowledge: patterns/context-engineering/task-sizing.md

Each plan should:
- Accomplish ONE cohesive goal
- Have 2-3 tasks maximum
- Be completable by a subagent
- Have clear verification criteria

Create dependency graph between plans.
      ]]></action>
    </step>

    <step name="assign_wave_numbers">
      <action><![CDATA[
Group plans into waves based on dependencies:

Wave 1: Plans with no dependencies (run in parallel)
Wave 2: Plans depending only on Wave 1
Wave 3: Plans depending on Wave 1 or 2
...

Plans in the same wave can run in parallel.
      ]]></action>
    </step>

    <step name="generate_plan_docs">
      <action><![CDATA[
For each plan, create .ai/plans/phase_{N}/plan_{name}.md:

---
plan: {name}
phase: {phase_num}
wave: {wave_num}
depends_on: [{dependencies}]
must_haves:
  - {observable truth 1}
  - {observable truth 2}
---

# Plan: {name}

## Goal
{one sentence}

## Tasks

### Task 1: {name}
**Files:** {file paths}
**Action:** {what to do}
**Verify:** {how to verify}
**Done:** {success criteria}

### Task 2: {name}
...

## Verification
{how to verify entire plan is complete}
      ]]></action>
    </step>

    <step name="verify_plan_quality">
      <action><![CDATA[
Verify each plan:
1. Has exactly 2-3 tasks
2. Each task has files, action, verify, done
3. Must-haves are observable truths
4. Dependencies form valid DAG
      ]]></action>
    </step>
  </process>
</directive>
```

### 2.2 Execution Workflow

**Directive: `workflows/execute_plan.md`**

```xml
<directive name="execute_plan" version="1.0.0">
  <metadata>
    <description>Execute a single plan with task completion and deviation handling</description>
    <category>workflows</category>
    <model_class tier="balanced" fallback="reasoning" parallel="false">
      Standard execution with deviation handling
    </model_class>
    <permissions>
      <read resource="filesystem" path="**/*" />
      <write resource="filesystem" path="**/*" />
      <execute resource="shell" command="*" />
    </permissions>
  </metadata>

  <inputs>
    <input name="plan_path" type="string" required="true">
      Path to plan document
    </input>
  </inputs>

  <process>
    <step name="load_plan">
      <action>Load plan from {plan_path} and parse frontmatter + tasks</action>
    </step>

    <step name="execute_tasks">
      <action><![CDATA[
For each task in plan:

1. Read task details (files, action, verify, done)
2. Execute the action
3. Run verification command/check
4. If verification passes: mark done, continue
5. If verification fails:
   - Analyze failure
   - Apply deviation handling rules
   - Either fix and retry, or escalate
      ]]></action>
    </step>

    <step name="handle_deviations">
      <action><![CDATA[
Load knowledge: patterns/deviation-handling/auto-fix-rules.md

Deviation categories:

AUTO-FIX (proceed without asking):
- bug: Code doesn't work as intended
- missing_critical: Essential for correctness/security
- blocking: Prevents completing current task

ASK-FIRST (pause and ask):
- architectural: Significant structural modification
- scope_expansion: Nice-to-have not in original plan

Record all deviations in state for summary.
      ]]></action>
    </step>

    <step name="verify_must_haves">
      <action><![CDATA[
After all tasks complete, verify must_haves from frontmatter:

For each must_have:
1. Check if it's an observable truth
2. Verify through code inspection or test
3. Record result

All must_haves should be true for plan completion.
      ]]></action>
    </step>

    <step name="create_summary">
      <action><![CDATA[
Create execution summary:

---
plan: {name}
completed: {timestamp}
duration: {time taken}
tasks_completed: {count}
deviations: {count}
---

## Summary
{what was accomplished}

## Files Changed
{list of files with brief description}

## Deviations
{list of deviations with rationale}

## Verification
{must_have check results}
      ]]></action>
    </step>
  </process>
</directive>
```

### 2.3 Phase Orchestration

**Directive: `meta/orchestrate_phase.md`**

```xml
<directive name="orchestrate_phase" version="1.0.0">
  <metadata>
    <description>Orchestrate execution of all plans in a phase using wave-based parallelism</description>
    <category>meta</category>
    <model_class tier="reasoning" fallback="expert" parallel="true">
      Multi-wave parallel orchestration
    </model_class>
    <parallel_capable>true</parallel_capable>
    <subagent_strategy>per-task</subagent_strategy>
    <preferred_subagent>subagent</preferred_subagent>
    <permissions>
      <read resource="filesystem" path=".ai/**/*" />
      <write resource="filesystem" path=".ai/**/*" />
      <execute resource="kiwi-mcp" action="*" />
    </permissions>
  </metadata>

  <inputs>
    <input name="phase_num" type="integer" required="true">
      Phase number to execute
    </input>
  </inputs>

  <process>
    <step name="load_phase_plans">
      <action><![CDATA[
Load all plans from .ai/plans/phase_{phase_num}/

Group by wave number:
- Wave 1: [{plan_a, plan_b, ...}]
- Wave 2: [{plan_c, plan_d, ...}]
- ...

Verify dependency graph is valid.
      ]]></action>
    </step>

    <step name="execute_waves" parallel="true">
      <action><![CDATA[
For each wave (sequential):
  For each plan in wave (parallel):

    Spawn subagent:
    Task("Execute directive: execute_plan with plan_path={plan_path}")

  Wait for all subagents in wave to complete.
  Check all plans passed before next wave.

Wave execution is sequential.
Plan execution within wave is parallel.
      ]]></action>
    </step>

    <step name="aggregate_results">
      <action><![CDATA[
After all waves complete:

## Phase {phase_num} Execution Complete

**Waves executed:** {count}
**Plans completed:** {completed}/{total}

### Plan Details
{for each plan: one-liner from summary}

### Issues Encountered
{aggregated from summaries or "None"}
      ]]></action>
    </step>

    <step name="verify_phase_goal">
      <action><![CDATA[
Execute: verify_work directive with phase: {phase_num}

Verifier checks must_haves against actual codebase.
Creates .ai/progress/phase_{phase_num}_verification.md

Route by result:
- passed → update roadmap, offer next phase
- human_needed → present verification checklist
- gaps_found → offer plan_phase with gaps=true
      ]]></action>
    </step>

    <step name="update_state">
      <action><![CDATA[
Update .ai/state/current_workflow.yaml:
- position.current_phase += 1
- progress recalculated
- session.last_activity = now

Mark phase complete in roadmap if verified.
      ]]></action>
    </step>
  </process>
</directive>
```

---

## Phase 3: Verification & Quality

### 3.1 Verification System

**Directive: `verification/verify_work.md`**

```xml
<directive name="verify_work" version="1.0.0">
  <metadata>
    <description>Verify phase/plan completion through code inspection and testing</description>
    <category>verification</category>
    <model_class tier="reasoning" fallback="expert" parallel="false">
      Deep code analysis to verify implementation completeness
    </model_class>
    <permissions>
      <read resource="filesystem" path="**/*" />
      <write resource="filesystem" path=".ai/progress/**/*" />
      <execute resource="shell" command="*" />
    </permissions>
  </metadata>

  <inputs>
    <input name="phase_num" type="integer" required="false">
      Phase to verify (verifies current if not specified)
    </input>
    <input name="plan_path" type="string" required="false">
      Specific plan to verify (verifies all if not specified)
    </input>
  </inputs>

  <process>
    <step name="load_must_haves">
      <action><![CDATA[
Load all plans for phase (or specific plan).
Collect all must_haves from frontmatter.
Group by category (observable truths, artifacts, wiring).
      ]]></action>
    </step>

    <step name="verify_existence">
      <action><![CDATA[
Load knowledge: patterns/verification/verification-levels.md

Level 1: EXISTENCE
For each artifact must_have:
- Check file exists at expected path
- Record: EXISTS or MISSING
      ]]></action>
    </step>

    <step name="verify_substantive">
      <action><![CDATA[
Level 2: SUBSTANTIVE
For each existing file:

Load knowledge: patterns/verification/stub-detection.md

Run stub detection:
- grep for TODO, FIXME, PLACEHOLDER
- Check for empty returns (null, undefined, {})
- Check for log-only functions
- Check for hardcoded values

Record: SUBSTANTIVE or STUB
      ]]></action>
    </step>

    <step name="verify_wiring">
      <action><![CDATA[
Level 3: WIRING
For each wiring must_have:

Check connections:
- Component → API: fetch/axios calls exist
- API → Database: query exists, result returned
- Form → Handler: onSubmit has real implementation
- State → Render: state variables in JSX

Record: WIRED or NOT_WIRED
      ]]></action>
    </step>

    <step name="verify_functional">
      <action><![CDATA[
Level 4: FUNCTIONAL
Run automated tests if available:
- Unit tests pass
- Integration tests pass
- E2E tests pass (if applicable)

Some items require human verification:
- Visual appearance
- User flow completion
- Real-time behavior
- External service integration

List items requiring human verification.
      ]]></action>
    </step>

    <step name="generate_report">
      <action><![CDATA[
Create .ai/progress/phase_{phase}_verification.md:

# Phase {phase} Verification

## Status: {passed|gaps_found|human_needed}

## Automated Checks

| Must-Have | Level | Status | Notes |
|-----------|-------|--------|-------|
{for each must_have}

## Gaps Found
{list of failed checks with details}

## Human Verification Required
{list of items needing human testing}

## Summary
- Passed: {count}
- Failed: {count}
- Human needed: {count}
      ]]></action>
    </step>
  </process>
</directive>
```

### 3.2 Deviation Handling

**Directive: `workflows/handle_deviation.md`**

```xml
<directive name="handle_deviation" version="1.0.0">
  <metadata>
    <description>Handle deviations during plan execution according to severity rules</description>
    <category>workflows</category>
    <model_class tier="balanced" fallback="reasoning" parallel="false">
      Rule-based deviation handling with escalation
    </model_class>
    <permissions>
      <read resource="filesystem" path=".ai/knowledge/**/*" />
      <write resource="filesystem" path=".ai/state/**/*" />
    </permissions>
  </metadata>

  <inputs>
    <input name="deviation_type" type="string" required="true">
      Type: bug, missing_critical, blocking, architectural, scope_expansion
    </input>
    <input name="description" type="string" required="true">
      What was found
    </input>
    <input name="proposed_fix" type="string" required="false">
      Proposed solution if applicable
    </input>
  </inputs>

  <process>
    <step name="classify_deviation">
      <action><![CDATA[
Load knowledge: patterns/deviation-handling/auto-fix-rules.md

Classify deviation:

AUTO-FIX (no permission needed):
- bug: Code doesn't work as intended
- missing_critical: Essential for correctness/security/performance
- blocking: Prevents completing current task

ASK-FIRST (user decision needed):
- architectural: Significant structural modification
- scope_expansion: Nice-to-have not in original plan
      ]]></action>
    </step>

    <step name="handle_auto_fix">
      <action><![CDATA[
If auto-fix category:

1. Apply the fix
2. Add/update tests if applicable
3. Verify fix works
4. Record deviation:
   {
     rule: "Rule {N} - {category}",
     description: "{description}",
     fix: "{what was done}",
     files: ["{affected files}"],
     step: "{current step}"
   }
5. Continue task
      ]]></action>
    </step>

    <step name="handle_ask_first">
      <action><![CDATA[
If ask-first category:

1. STOP current task
2. Execute checkpoint directive:
   type: decision
   description: "{deviation description}"
   context: "{why this matters}"
   options:
     - Apply fix: {proposed fix with tradeoffs}
     - Skip: Continue without this change
     - Redesign: Modify the plan
3. Wait for resolution
4. Continue based on decision
      ]]></action>
    </step>

    <step name="record_deviation">
      <action><![CDATA[
Update state with deviation record:
- Type and classification
- Description
- Resolution (fix applied or decision made)
- Impact on plan

This feeds into execution summary.
      ]]></action>
    </step>
  </process>
</directive>
```

---

## Phase 4: Context Engineering

### 4.1 Context Budget Management

**Knowledge Entry: `patterns/context-engineering/quality-curve.md`**

````markdown
---
zettel_id: quality-curve
title: Context Window Quality Degradation Curve
entry_type: pattern
category: patterns/context-engineering
tags:
  - context-window
  - quality
  - planning
---

# Context Window Quality Degradation Curve

## The Problem

AI quality degrades predictably as context fills:

| Context Usage | Quality Level | Recommendation       |
| ------------- | ------------- | -------------------- |
| 0-25%         | Excellent     | Complex reasoning OK |
| 25-50%        | Good          | Standard tasks OK    |
| 50-75%        | Degrading     | Simple tasks only    |
| 75-100%       | Poor          | Handoff to subagent  |

## Implications for Directive Design

### Task Sizing

Each plan should contain 2-3 tasks maximum:

- More tasks = more context consumed
- Quality degrades mid-plan
- Verification becomes unreliable

### Subagent Strategy

Spawn subagents for:

- Each plan execution (fresh context)
- Research tasks (token-intensive)
- Debugging (iteration-heavy)

### Progressive Disclosure

Load context lazily:

1. Start with plan summary only
2. Load task details when executing that task
3. Load knowledge entries on-demand
4. Unload completed task context

## Directive Metadata

```xml
<metadata>
  <context_budget>
    <estimated_usage>40%</estimated_usage>
    <step_count>5</step_count>
    <spawn_threshold>60%</spawn_threshold>
  </context_budget>
</metadata>
```
````

This tells the agent:

- This directive uses ~40% of context
- Has 5 steps
- Should spawn subagent if context > 60%

````

### 4.2 Task Sizing Guidelines

**Knowledge Entry: `patterns/context-engineering/task-sizing.md`**

```markdown
---
zettel_id: task-sizing
title: Task Sizing Guidelines for AI Execution
entry_type: pattern
category: patterns/context-engineering
tags:
- task-sizing
- planning
- context-window
---

# Task Sizing Guidelines

## The 2-3 Task Rule

Each plan should have exactly 2-3 tasks:
- **1 task**: Too simple, doesn't justify a plan
- **2-3 tasks**: Optimal for subagent execution
- **4+ tasks**: Too complex, split into multiple plans

## What Makes a Good Task

### Structure

```markdown
### Task: {name}
**Files:** {specific file paths}
**Action:** {concrete steps}
**Verify:** {how to check it works}
**Done:** {observable success criteria}
````

### Characteristics

Good tasks are:

- **Atomic**: Complete one coherent change
- **Verifiable**: Can check success programmatically
- **Scoped**: Touch 1-3 files maximum
- **Independent**: Don't require mid-task decisions

### Anti-patterns

Bad tasks:

- "Implement authentication" (too broad)
- "Fix bugs" (not specific)
- "Add tests" (missing what/where)
- "Refactor code" (no clear end state)

## Task Dependencies

Within a plan:

- Tasks execute sequentially
- Later tasks can depend on earlier ones
- Cross-plan dependencies use wave numbers

Between plans:

- Wave 1 plans: no dependencies
- Wave 2 plans: depend on Wave 1
- Wave N plans: depend on Wave < N

## Verification Criteria

Every task needs:

1. **Verify command**: What to run

   ```
   Verify: npm run test -- --grep "auth"
   ```

2. **Done criteria**: Observable truth
   ```
   Done: Test passes, 200 response for valid creds
   ```

Avoid vague criteria:

- ❌ "Works correctly"
- ❌ "Looks good"
- ✅ "Returns 200 with valid token"
- ✅ "Creates file at path/to/file.ts"

````

---

## Full Directive Catalog

### State Management (state/)

| Directive | Description |
| ------------------- | ---------------------------------------------- |
| `init_state` | Initialize workflow state tracking |
| `update_state` | Update state after step completion |
| `checkpoint` | Create checkpoint for human interaction |
| `resolve_checkpoint`| Resolve pending checkpoint |
| `resume_state` | Resume workflow from saved state |

### Workflows (workflows/)

| Directive | Description |
| ------------------- | ---------------------------------------------- |
| `new_project` | Initialize new project with requirements |
| `plan_phase` | Create detailed phase implementation plan |
| `execute_plan` | Execute single plan with deviation handling |
| `verify_work` | Verify phase/plan completion |
| `research_topic` | Research and produce findings |
| `debug_issue` | Debug with structured approach |
| `handle_deviation` | Handle deviations during execution |
| `create_summary` | Create execution summary |

### Orchestration (meta/)

| Directive | Description |
| --------------------- | ---------------------------------------- |
| `orchestrate_phase` | Execute all plans in phase with waves |
| `orchestrate_general` | (existing) Create orchestrator pairs |

### Verification (verification/)

| Directive | Description |
| -------------------- | ---------------------------------- |
| `verify_exists` | Check file/artifact existence |
| `verify_substantive` | Check for stub/placeholder code |
| `verify_wired` | Check component connections |
| `verify_functional` | Run tests and functional checks |

---

## Knowledge Entries to Create

### Templates (templates/)

| Entry | Description |
| ----------------- | ------------------------ |
| `project.md` | PROJECT.md template |
| `requirements.md` | REQUIREMENTS.md template |
| `roadmap.md` | ROADMAP.md template |
| `state.md` | STATE.yaml template |
| `summary.md` | SUMMARY.md template |
| `plan.md` | PLAN.md template |
| `verification.md` | VERIFICATION.md template |

### Patterns (patterns/)

| Path | Entry | Description |
| ----------------------------- | ----------------------------- | ----------------------------------------- |
| `checkpoints/` | `human-verify.md` | Human verification checkpoint pattern |
| `checkpoints/` | `decision-checkpoint.md` | Decision checkpoint pattern |
| `checkpoints/` | `human-action.md` | Human action checkpoint pattern |
| `deviation-handling/` | `auto-fix-rules.md` | When to auto-fix vs ask |
| `deviation-handling/` | `escalation-patterns.md` | How to escalate issues |
| `verification/` | `verification-levels.md` | Exists → Substantive → Wired → Functional |
| `verification/` | `stub-detection.md` | Identifying placeholder code |
| `verification/` | `tdd-detection.md` | TDD plan heuristic |
| `context-engineering/` | `quality-curve.md` | Context degradation patterns |
| `context-engineering/` | `task-sizing.md` | 2-3 task rule |
| `context-engineering/` | `progressive-disclosure.md` | Information layering |
| `context-engineering/` | `depth-settings.md` | Quick/Standard/Comprehensive modes |
| `orchestration/` | `wave-execution.md` | Parallel wave patterns |
| `orchestration/` | `ux-patterns.md` | Output formatting for orchestrators |
| `style/` | `language-guidelines.md` | Imperative voice, no filler |
| `style/` | `anti-patterns.md` | Enterprise patterns, vague tasks |
| `git/` | `atomic-commits.md` | Commit conventions |

---

## Directive Metadata Updates

### New Metadata Elements

Add these to the directive schema:

```xml
<metadata>
  <!-- Existing -->
  <description>...</description>
  <category>...</category>
  <model_class tier="..." fallback="..." parallel="...">...</model_class>
  <parallel_capable>true|false</parallel_capable>
  <subagent_strategy>per-file|per-category|per-task</subagent_strategy>
  <preferred_subagent>subagent</preferred_subagent>
  <permissions>...</permissions>

  <!-- NEW: Progressive disclosure - when to use this directive -->
  <when_to_use>Decision criteria for agent selection</when_to_use>

  <!-- NEW: Context budget hints -->
  <context_budget>
    <estimated_usage>40%</estimated_usage>
    <step_count>5</step_count>
    <spawn_threshold>60%</spawn_threshold>
  </context_budget>

  <!-- NEW: Deviation rules for this directive -->
  <deviation_rules>
    <auto_fix>bugs, blocking, security</auto_fix>
    <ask_first>architecture, scope_expansion</ask_first>
  </deviation_rules>
</metadata>
```

### Enhanced Step Structure

Steps can now include verification and commit signals:

```xml
<step name="create_endpoint" type="auto">
  <description>Create the API endpoint</description>
  <files>src/api/route.ts</files>
  <action><![CDATA[
    Create POST endpoint with validation...
  ]]></action>
  <verify>
    <command>npm run typecheck</command>
    <expect>No errors</expect>
  </verify>
  <done>Endpoint compiles, handles requests</done>
  <commit>feat(auth): add login endpoint</commit>
</step>
```

The `<commit>` element signals that an atomic commit should be made after verification passes. Format follows conventional commits: `{type}({scope}): {description}`

### Checkpoint Elements

New checkpoint element for process sections:

```xml
<process>
  <step name="deploy">...</step>

  <checkpoint type="human-verify" gate="blocking">
    <what_built>Deployed to staging</what_built>
    <how_to_verify>
      1. Visit https://staging.example.com
      2. Test login flow
    </how_to_verify>
    <resume_signal>Type "approved" or describe issues</resume_signal>
  </checkpoint>

  <step name="promote_to_prod">...</step>
</process>
```

---

## Implementation Order

### Wave 1: Foundation (No Dependencies)

Run in parallel:

```
Task("Execute: create directive state/init_state")
Task("Execute: create directive state/update_state")
Task("Execute: create directive state/checkpoint")
Task("Execute: create knowledge templates/project")
Task("Execute: create knowledge templates/summary")
Task("Execute: create knowledge patterns/deviation-handling/auto-fix-rules")
Task("Execute: create knowledge patterns/checkpoints/human-verify")
```

### Wave 2: State Management (Depends on Wave 1)

```
Task("Execute: create directive state/resume_state")
Task("Execute: create directive state/resolve_checkpoint")
Task("Execute: create knowledge templates/state")
Task("Execute: create knowledge patterns/context-engineering/task-sizing")
```

### Wave 3: Core Workflows (Depends on Wave 2)

```
Task("Execute: create directive workflows/plan_phase")
Task("Execute: create directive workflows/execute_plan")
Task("Execute: create directive workflows/handle_deviation")
Task("Execute: create knowledge patterns/verification/verification-levels")
```

### Wave 4: Verification (Depends on Wave 3)

```
Task("Execute: create directive verification/verify_work")
Task("Execute: create directive workflows/create_summary")
Task("Execute: create knowledge templates/plan")
Task("Execute: create knowledge templates/verification")
```

### Wave 5: Orchestration (Depends on Wave 4)

```
Task("Execute: create directive meta/orchestrate_phase")
Task("Execute: create knowledge patterns/orchestration/wave-execution")
```

### Wave 6: Project Initialization (Depends on Wave 5)

```
Task("Execute: create directive workflows/new_project")
Task("Execute: create directive workflows/research_topic")
Task("Execute: create directive workflows/debug_issue")
Task("Execute: create knowledge templates/requirements")
Task("Execute: create knowledge templates/roadmap")
```

### Wave 7: Polish (Depends on Wave 6)

```
Task("Execute: create knowledge patterns/context-engineering/quality-curve")
Task("Execute: create knowledge patterns/context-engineering/progressive-disclosure")
Task("Execute: create knowledge patterns/checkpoints/decision-checkpoint")
Task("Execute: create knowledge patterns/checkpoints/human-action")
```

### Wave 8: Style & Quality (No Dependencies - Can Run Parallel with Others)

```
Task("Execute: create knowledge patterns/style/language-guidelines")
Task("Execute: create knowledge patterns/style/anti-patterns")
Task("Execute: create knowledge patterns/context-engineering/depth-settings")
Task("Execute: create knowledge patterns/verification/tdd-detection")
Task("Execute: create knowledge patterns/git/atomic-commits")
Task("Execute: create knowledge patterns/orchestration/ux-patterns")
```

---

## Master Orchestrator Directive

**Directive: `meta/orchestrate_workflow_enhancement.md`**

```xml
<directive name="orchestrate_workflow_enhancement" version="1.0.0">
  <metadata>
    <description>Orchestrate the full workflow enhancement implementation</description>
    <category>meta</category>
    <model_class tier="reasoning" fallback="expert" parallel="true">
      Multi-wave parallel orchestration
    </model_class>
    <parallel_capable>true</parallel_capable>
    <subagent_strategy>per-task</subagent_strategy>
    <permissions>
      <read resource="filesystem" path=".ai/**/*" />
      <write resource="filesystem" path=".ai/**/*" />
      <execute resource="kiwi-mcp" action="*" />
    </permissions>
  </metadata>

  <process>
    <step name="create_progress_doc">
      <action>Create progress tracking for enhancement</action>
    </step>

    <step name="wave_1" parallel="true">
      <description>Foundation - No dependencies</description>
      <action><![CDATA[
Spawn parallel subagents for Wave 1 items:
{list of Wave 1 tasks}

Wait for all to complete before Wave 2.
      ]]></action>
    </step>

    <!-- Continue for Waves 2-7 -->

    <step name="verify">
      <action><![CDATA[
Verify all items created:
- Count directives in state/, workflows/, verification/
- Count knowledge entries in patterns/
- Count templates in templates/
- Test key workflows
      ]]></action>
    </step>

    <step name="update_agent_dispatch">
      <action><![CDATA[
Update agent.md command dispatch table with new commands:

| User Says | Run Directive | With Inputs |
|-----------|---------------|-------------|
| new project | new_project | project_path |
| plan phase X | plan_phase | phase_num=X |
| execute phase X | orchestrate_phase | phase_num=X |
| verify work X | verify_work | phase_num=X |
| resume | resume_state | none |
      ]]></action>
    </step>

    <step name="report">
      <action><![CDATA[
## Workflow Enhancement Complete

Created:
- Directives: {count}
- Knowledge entries: {count}
- Templates: {count}

Commands available:
- new project
- plan phase X
- execute phase X
- verify work X
- resume

Run: new project
      ]]></action>
    </step>
  </process>
</directive>
```

---

## Phase 5: Style & Quality Patterns

### 5.1 Language & Tone Guidelines

**Knowledge Entry: `patterns/style/language-guidelines.md`**

```markdown
---
zettel_id: language-guidelines
title: Language and Tone Guidelines for Directives
entry_type: pattern
category: patterns/style
tags:
- style
- language
- tone
- quality
---

# Language and Tone Guidelines

## Imperative Voice

**DO:** "Execute tasks", "Create file", "Read state"

**DON'T:** "Execution is performed", "The file should be created"

## No Filler

Absent: "Let me", "Just", "Simply", "Basically", "I'd be happy to"

Present: Direct instructions, technical precision

## No Sycophancy

Absent: "Great!", "Awesome!", "Excellent!", "I'd love to help"

Present: Factual statements, verification results, direct answers

## Brevity with Substance

**Good one-liner:** "JWT auth with refresh rotation using jose library"

**Bad one-liner:** "Phase complete" or "Authentication implemented"

## Directive Step Actions

Each action should be:
- Concrete and specific
- Include what to avoid and WHY
- Reference specific files
- Include verification command
```

### 5.2 Anti-Patterns

**Knowledge Entry: `patterns/style/anti-patterns.md`**

```markdown
---
zettel_id: anti-patterns
title: Anti-Patterns to Avoid in Directives
entry_type: pattern
category: patterns/style
tags:
- anti-patterns
- quality
- banned
---

# Anti-Patterns to Avoid

## Enterprise Patterns (Banned)

Never include:
- Story points, sprint ceremonies, RACI matrices
- Human dev time estimates (days/weeks)
- Team coordination, knowledge transfer docs
- Change management processes

We optimize for solo developer + AI workflow.

## Temporal Language (Banned in Directives)

**DON'T:** "We changed X to Y", "Previously", "No longer", "Instead of"

**DO:** Describe current state only

**Exception:** CHANGELOG.md, progress docs, git commits

## Generic XML (Banned)

**DON'T:** `<section>`, `<item>`, `<content>`

**DO:** Semantic purpose tags: `<objective>`, `<verification>`, `<action>`

## Vague Tasks (Banned)

```xml
<!-- BAD -->
<step name="add_auth">
  <action>Implement auth</action>
</step>

<!-- GOOD -->
<step name="create_login_endpoint">
  <files>src/api/auth/login.ts</files>
  <action>
    POST endpoint accepting {email, password}.
    Query User by email, compare with bcrypt.
    On match, create JWT with jose, set httpOnly cookie.
    Return 200. On mismatch, return 401.
  </action>
  <verify>curl -X POST localhost:3000/api/auth/login returns 200 with Set-Cookie</verify>
  <done>Valid credentials → 200 + cookie. Invalid → 401.</done>
</step>
```
```

### 5.3 Depth & Compression Settings

**Knowledge Entry: `patterns/context-engineering/depth-settings.md`**

```markdown
---
zettel_id: depth-settings
title: Depth and Compression Settings for Planning
entry_type: pattern
category: patterns/context-engineering
tags:
- depth
- compression
- planning
---

# Depth & Compression Settings

Depth setting controls compression tolerance when creating plans.

## Settings

| Setting | Compression | Plans/Phase | Use When |
| ------------- | ----------- | ----------- | -------------------------------- |
| Quick | Aggressive | 1-3 | Fast iteration, prototyping |
| Standard | Balanced | 3-5 | Normal development |
| Comprehensive | Resist | 5-10 | Complex systems, learning |

## Key Principle

**Depth controls compression, not inflation.**

- Never pad to hit a target number
- Derive plans from actual work required
- Split when complexity demands it, not arbitrarily

## Compression Triggers (Split Required)

- More than 3 tasks in a plan
- Multiple independent subsystems
- More than 5 files per task
- Different concerns (frontend/backend/database)

## Input Format

Directives that create plans can accept depth:

```xml
<input name="depth" type="string" required="false" default="standard">
  Compression tolerance: quick | standard | comprehensive
</input>
```
```

### 5.4 TDD Plan Detection

**Knowledge Entry: `patterns/verification/tdd-detection.md`**

```markdown
---
zettel_id: tdd-detection
title: TDD Plan Detection Heuristic
entry_type: pattern
category: patterns/verification
tags:
- tdd
- testing
- planning
---

# TDD Plan Detection Heuristic

## The Question

> Can you write `expect(fn(input)).toBe(output)` before writing `fn`?

- **Yes** → TDD plan (one feature per plan)
- **No** → Standard plan

## When TDD Applies

- Pure functions with clear inputs/outputs
- API endpoints with defined contracts
- Data transformations
- Validation logic
- Business rules

## When TDD Doesn't Apply

- UI components (visual verification)
- Integration with external services
- Exploratory development
- Configuration/setup tasks

## TDD Plan Structure

```yaml
---
plan: feature_name
type: tdd
---
```

```xml
<objective>
Implement [feature] using TDD (RED → GREEN → REFACTOR)
</objective>

<behavior>
Expected behavior specification:
- Input: {description}
- Output: {description}
- Edge cases: {list}
</behavior>

<implementation>
How to make tests pass:
- Key algorithm/approach
- Libraries to use
- Files to create
</implementation>
```

## TDD Commits

Each cycle produces three commits:

1. **RED:** `test(plan): add failing test for [feature]`
2. **GREEN:** `feat(plan): implement [feature]`
3. **REFACTOR:** `refactor(plan): clean up [feature]`

## TDD Gets Dedicated Plans

The RED→GREEN→REFACTOR cycle is too heavy to embed within larger plans.
Each TDD feature should be its own plan with 2-3 tasks (write test, implement, refactor).
```

### 5.5 Atomic Commit Conventions

**Knowledge Entry: `patterns/git/atomic-commits.md`**

```markdown
---
zettel_id: atomic-commits
title: Atomic Commit Conventions
entry_type: pattern
category: patterns/git
tags:
- git
- commits
- conventions
---

# Atomic Commit Conventions

## Format

```
{type}({scope}): {description}
```

## Types

| Type | Use |
| ---------- | --------------------------- |
| `feat` | New feature |
| `fix` | Bug fix |
| `test` | Tests only (TDD RED) |
| `refactor` | Code cleanup (TDD REFACTOR) |
| `docs` | Documentation/metadata |
| `chore` | Config/dependencies |

## Scope

Use plan identifier or component name:
- `feat(auth): add login endpoint`
- `fix(phase-1-plan-2): handle null user`
- `test(payment): add failing test for refund`

## Rules

1. **One commit per task** during execution
2. **Stage files individually** (never `git add .`)
3. **Capture hash** for execution summary
4. **Include verification** before commit

## Integration with Directives

```xml
<step name="implement_feature">
  <action>...</action>
  <verify>npm run test</verify>
  <commit>feat(auth): add JWT validation</commit>
</step>
```

The `<commit>` element signals that a commit should be made after verification passes.
```

### 5.6 UX Patterns for Orchestrators

**Knowledge Entry: `patterns/orchestration/ux-patterns.md`**

```markdown
---
zettel_id: ux-patterns
title: UX Patterns for Orchestrator Output
entry_type: pattern
category: patterns/orchestration
tags:
- ux
- output
- orchestration
---

# UX Patterns for Orchestrator Output

## "Next Up" Format

After completing a phase or plan, present next steps clearly:

```markdown
───────────────────────────────────────────────────────────────

## ▶ Next Up

**Phase 2: Authentication** — JWT login with refresh tokens

`run directive orchestrate_phase with phase_num=2`

───────────────────────────────────────────────────────────────

**Also available:**
- `verify work 1` — Re-verify Phase 1
- `resume` — Resume from last checkpoint

───────────────────────────────────────────────────────────────
```

## Decision Gates

When asking user to make a decision:

1. Always provide concrete options
2. Include an escape hatch
3. Explain tradeoffs briefly

```markdown
## 🔀 Decision Required

**Which caching strategy?**

1. **Redis** — Fast, requires separate server
2. **In-memory** — Simple, lost on restart
3. **SQLite** — Persistent, slower than Redis
4. **Something else** — Describe your preference

Reply with number or description.
```

## Status Symbols

| Symbol | Meaning |
| ------ | --------------- |
| ✅ | Complete |
| ⏳ | In progress |
| ⏸️ | Paused/Checkpoint |
| ❌ | Failed |
| 🔀 | Decision needed |
| ▶ | Next action |

## Progress Display

```markdown
## Phase 2 Progress

[████████░░░░░░░░] 50% (3/6 plans)

| Plan | Status | Duration |
| ---- | ------ | -------- |
| 2.1 Auth Schema | ✅ | 2m |
| 2.2 Login API | ✅ | 4m |
| 2.3 Session Mgmt | ⏳ | - |
| 2.4 Refresh Token | ⏸️ | - |
```
```

### 5.7 Progressive Disclosure

**Knowledge Entry: `patterns/context-engineering/progressive-disclosure.md`**

```markdown
---
zettel_id: progressive-disclosure
title: Progressive Disclosure in Directive Design
entry_type: pattern
category: patterns/context-engineering
tags:
- progressive-disclosure
- context
- design
---

# Progressive Disclosure

Information flows through layers, each answering different questions.

## The Hierarchy

```
Directive Metadata → Process Steps → Knowledge Refs → Templates
       ↓                  ↓               ↓              ↓
  "Should I use     "What           "Why this      "What does
   this?"           happens?"        design?"       output look like?"
```

## Layer 1: Directive Metadata

Quick context for selection:
- Name and description
- Category and tags
- Model class (complexity indicator)
- Inputs summary

**Question answered:** "Should I use this directive?"

## Layer 2: Process Steps

Execution flow:
- Step sequence
- Actions to perform
- Verification commands

**Question answered:** "What happens when I run this?"

## Layer 3: Knowledge References

Deep context (loaded on demand):
- Best practices
- Design rationale
- Domain knowledge

**Question answered:** "Why is it designed this way?"

## Layer 4: Templates

Concrete output formats:
- File templates
- Structure specifications
- Example outputs

**Question answered:** "What does the output look like?"

## Implementation in Directives

```xml
<directive name="example" version="1.0.0">
  <metadata>
    <!-- Layer 1: Quick selection context -->
    <description>Brief what/why</description>
    <when_to_use>Decision criteria</when_to_use>
  </metadata>

  <references>
    <!-- Layer 3 & 4: Loaded on demand -->
    <knowledge ref="patterns/rationale.md" />
    <template ref="templates/output.md" />
  </references>

  <process>
    <!-- Layer 2: Execution steps -->
    <step name="do_thing">
      <action>Concrete action</action>
    </step>
  </process>
</directive>
```

## Lazy Loading

References are **signals**, not pre-loaded content.
Load knowledge/templates only when that step executes.
This preserves context window for actual work.
```

---

## Core Meta-Patterns Summary

The 15 core principles guiding this enhancement:

1. **XML for semantic structure, Markdown for content** — Tags have meaning
2. **References are lazy loading signals** — Load on demand, not upfront
3. **Directives delegate to knowledge** — Keep directives focused
4. **Progressive disclosure hierarchy** — Layer information appropriately
5. **Imperative, brief, technical** — No filler, no sycophancy
6. **Solo developer + AI workflow** — No enterprise patterns
7. **Context size as quality constraint** — Split aggressively
8. **Temporal language banned** — Current state only in directives
9. **Plans ARE prompts** — Executable, not documentation
10. **Atomic commits per task** — Git history as context source
11. **Decision gates with options** — Always provide choices
12. **Checkpoints post-automation** — Automate first, verify after
13. **Deviation rules are automatic** — No permission for bugs/critical
14. **Depth controls compression** — Derive from actual work
15. **TDD gets dedicated plans** — Cycle too heavy to embed

---

## Summary

This enhancement plan:

1. **Implements advanced workflow patterns as Kiwi directives**

   - No specialized agents - universal agent runs all directives
   - Model routing via `model_class` metadata
   - Integration into existing folder structure

2. **Uses directive-based prompting throughout**

   - Subagents execute directives, not embedded instructions
   - Knowledge entries inform execution
   - State persists across sessions

3. **Enables wave-based parallel execution**

   - Independent work runs in parallel
   - Dependencies respected via wave ordering
   - Orchestrators coordinate subagents

4. **Adds new capabilities**

   - Checkpoint system for human interaction
   - State management with resume capability
   - Deviation handling rules
   - Verification levels
   - Context engineering patterns

5. **Extends directive metadata**

   - `context_budget` for context management
   - `deviation_rules` for auto-fix behavior
   - Enhanced step structure with verify/done
   - Checkpoint elements in process

6. **Supports all three harnesses**
   - Amp: Full parallel via Task()
   - Claude Code: Checkpoint-based handoff
   - OpenCode: Thread-based (experimental)

To begin enhancement:

```
run directive orchestrate_workflow_enhancement
```
````
