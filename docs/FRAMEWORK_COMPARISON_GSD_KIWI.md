# Framework Comparison: Get Shit Done (GSD) vs Kiwi MCP

**Purpose:** Deep analysis of both AI context engineering frameworks to identify patterns, features, and concepts from GSD that could enhance Kiwi MCP's directives, scripts, and knowledge base.

---

## Executive Summary

| Aspect                 | GSD                                     | Kiwi MCP                                      |
| ---------------------- | --------------------------------------- | --------------------------------------------- |
| **Primary Focus**      | Spec-driven development workflow        | Unified directive/script/knowledge management |
| **Architecture**       | Command + Agent + Workflow + Template   | MCP Server + Handler + Registry               |
| **Context Management** | File-based artifacts (.planning/)       | .ai/ folder structure                         |
| **Orchestration**      | Multi-agent with wave-based parallelism | Single unified MCP with 4 tools               |
| **State Persistence**  | STATE.md + SUMMARY.md + config.json     | Knowledge entries + directive state           |
| **Target Use Case**    | Building software projects from scratch | Managing reusable AI workflows                |

---

## Architecture Comparison

### GSD Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Claude Code Interface                       │
├─────────────────────────────────────────────────────────────────┤
│  Slash Commands (commands/gsd/*.md)                              │
│  ├── new-project, plan-phase, execute-phase, verify-work, etc.  │
│  └── Thin wrappers → delegate to workflows                      │
├─────────────────────────────────────────────────────────────────┤
│  Workflows (get-shit-done/workflows/*.md)                        │
│  ├── execute-phase.md, verify-phase.md, discover-phase.md       │
│  └── Process definitions with @-references                      │
├─────────────────────────────────────────────────────────────────┤
│  Agents (agents/*.md)                                            │
│  ├── gsd-executor, gsd-planner, gsd-verifier, gsd-debugger      │
│  └── Specialized roles with tool permissions                    │
├─────────────────────────────────────────────────────────────────┤
│  Templates (templates/*.md)                                      │
│  ├── summary.md, state.md, project.md, roadmap.md               │
│  └── Structured output formats                                  │
├─────────────────────────────────────────────────────────────────┤
│  References (references/*.md)                                    │
│  ├── checkpoints.md, verification-patterns.md, tdd.md           │
│  └── Deep-dive documentation                                    │
└─────────────────────────────────────────────────────────────────┘
```

### Kiwi MCP Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       MCP Server                                 │
├──────────────┬──────────────┬──────────────┬────────────────────┤
│   search     │     load     │   execute    │        help        │
└──────┬───────┴──────┬───────┴──────┬───────┴────────┬───────────┘
       │              │              │                │
       └──────────────┴──────────────┴────────────────┘
              TypeHandlerRegistry
       ┌──────────┬──────────┬──────────┐
       │          │          │          │
   Directive   Script    Knowledge    (Future)
   Handler     Handler    Handler
       │          │          │
       ├──────────┼──────────┤
       │  Local + Registry Storage    │
       └──────────────────────────────┘
```

---

## Key GSD Concepts to Port to Kiwi MCP

### 1. Progressive Disclosure Hierarchy

**GSD Pattern:**

```
Command → Workflow → Template → Reference
   ↓          ↓          ↓           ↓
"Should I   "What      "What does  "Why this
 use this?" happens?"  output      design?"
                       look like?"
```

**Current Kiwi MCP:**

- Directives are flat (everything in one file)
- No layered information architecture
- No clear separation between "what" and "how"

**Proposed Enhancement:**

Create a **directive layering system**:

```markdown
# Directive Layers

## Layer 1: Directive Summary (metadata)

- Name, description, category, inputs/outputs
- Quick "should I use this?" answer

## Layer 2: Process Steps (directive body)

- Step-by-step workflow
- @-references to deeper content

## Layer 3: Templates (linked resources)

- Output format specifications
- Structured file templates

## Layer 4: Knowledge Entries (context)

- Deep-dive explanations
- Domain knowledge
- Best practices
```

**Implementation:**

Add to directive XML schema:

```xml
<directive name="example" version="1.0.0">
  <metadata>
    <!-- Layer 1: Quick context -->
    <description>Brief description</description>
    <when_to_use>Decision criteria for agent</when_to_use>
    <estimated_time>5-10 minutes</estimated_time>
  </metadata>

  <references>
    <!-- Layer 2: External resources -->
    <template ref="templates/output_format.md" />
    <knowledge ref="knowledge/domain_context.md" />
  </references>

  <process>
    <!-- Layer 3: Execution steps -->
  </process>
</directive>
```

---

### 2. Structured Task Format with Verification

**GSD Pattern:**

```xml
<task type="auto">
  <name>Create login endpoint</name>
  <files>src/app/api/auth/login/route.ts</files>
  <action>
    Use jose for JWT (not jsonwebtoken - CommonJS issues).
    Validate credentials against users table.
    Return httpOnly cookie on success.
  </action>
  <verify>curl -X POST localhost:3000/api/auth/login returns 200 + Set-Cookie</verify>
  <done>Valid credentials return cookie, invalid return 401</done>
</task>
```

**Current Kiwi MCP:**

```xml
<step name="create_endpoint">
  <description>Create the login endpoint</description>
  <action>Create a POST endpoint for login...</action>
</step>
```

**Proposed Enhancement:**

Adopt GSD's task structure for directive steps:

```xml
<step name="create_login_endpoint" type="auto">
  <description>Create login endpoint with JWT</description>
  <files>src/app/api/auth/login/route.ts</files>
  <action>
    <![CDATA[
    Use jose for JWT (Edge-compatible).
    Validate credentials against users table.
    Return httpOnly cookie on success.
    ]]>
  </action>
  <verify>
    <command>curl -X POST localhost:3000/api/auth/login -d '{"email":"test@test.com","password":"test"}'</command>
    <expect>200 status with Set-Cookie header</expect>
  </verify>
  <done>Valid credentials return cookie, invalid return 401</done>
</step>
```

**Benefits:**

- Clear success criteria per step
- Automated verification possible
- Better tracking of completion

---

### 3. Checkpoint System

**GSD Pattern:**

Three checkpoint types with clear usage guidelines:

| Type                      | Usage                           | Frequency |
| ------------------------- | ------------------------------- | --------- |
| `checkpoint:human-verify` | Visual/functional verification  | 90%       |
| `checkpoint:decision`     | Architecture/technology choices | 9%        |
| `checkpoint:human-action` | Truly unavoidable manual steps  | 1%        |

**Current Kiwi MCP:**

- No formal checkpoint system
- No standardized human interaction points

**Proposed Enhancement:**

Add `<checkpoint>` element to directive schema:

```xml
<process>
  <step name="deploy_to_vercel" type="auto">
    <action>Run vercel --yes to deploy</action>
    <verify>vercel ls shows deployment</verify>
  </step>

  <checkpoint type="human-verify" gate="blocking">
    <what_built>Deployed to https://myapp.vercel.app</what_built>
    <how_to_verify>
      1. Visit the URL
      2. Check homepage loads
      3. Verify no console errors
    </how_to_verify>
    <resume_signal>Type "approved" or describe issues</resume_signal>
  </checkpoint>

  <step name="configure_dns" type="auto">
    <!-- continues after checkpoint approval -->
  </step>
</process>
```

**Knowledge Entry:**

Create `knowledge/checkpoint_patterns.md` with:

- When to use each checkpoint type
- Anti-patterns (asking humans to automate)
- Examples for each type

---

### 4. Wave-Based Parallel Execution

**GSD Pattern:**

```
Wave 1: [plan-01, plan-02] → parallel
Wave 2: [plan-03] → depends on Wave 1
Wave 3: [plan-04, plan-05] → depends on Wave 2
```

- Plans within same wave execute in parallel
- Waves execute sequentially
- Dependencies are computed ahead of time

**Current Kiwi MCP:**

- Directives execute sequentially
- No dependency tracking between steps
- No parallelism support

**Proposed Enhancement:**

Add wave support to directive metadata:

```xml
<directive name="full_stack_setup" version="1.0.0">
  <metadata>
    <parallel_capable>true</parallel_capable>
    <subagent_strategy>orchestrate_parallel</subagent_strategy>
  </metadata>

  <process>
    <wave number="1">
      <step name="setup_frontend" parallel="true">...</step>
      <step name="setup_backend" parallel="true">...</step>
    </wave>

    <wave number="2" depends_on="1">
      <step name="integrate_api">...</step>
    </wave>

    <wave number="3" depends_on="2">
      <step name="deploy" parallel="true">...</step>
      <step name="configure_monitoring" parallel="true">...</step>
    </wave>
  </process>
</directive>
```

**Handler Updates:**

Add to `DirectiveHandler`:

- Wave computation from step dependencies
- Parallel execution within waves
- Dependency tracking

---

### 5. State Management (STATE.md Pattern)

**GSD Pattern:**

```markdown
# Project State

## Current Position

Phase: 2 of 5 (Authentication)
Plan: 1 of 3 in current phase
Status: In progress
Last activity: 2025-01-18 — Completed 01-02-PLAN.md

Progress: [████░░░░░░] 40%

## Accumulated Context

### Decisions

- [Phase 1]: Used jose instead of jsonwebtoken (ESM-native)
- [Phase 2]: 15-min access tokens with 7-day refresh tokens

### Blockers/Concerns

None yet.

## Session Continuity

Last session: 2025-01-18 14:30
Stopped at: Completed task 3 of login endpoint
Resume file: .planning/phases/02-auth/.continue-here.md
```

**Current Kiwi MCP:**

- No centralized state tracking
- Knowledge entries are decoupled from workflow state
- No session continuity

**Proposed Enhancement:**

Create a **workflow state directive** that maintains:

```yaml
# .ai/state/current_workflow.yaml

workflow:
  directive: create_api_service
  started: 2025-01-18T10:00:00Z
  last_activity: 2025-01-18T14:30:00Z

position:
  current_step: 4
  total_steps: 8
  status: in_progress
  progress: 50%

context:
  decisions:
    - step: 2
      decision: "Used FastAPI instead of Flask"
      rationale: "Better async support"

  inputs_used:
    service_name: user-api
    database: postgresql

  outputs_created:
    - src/app/main.py
    - src/app/routes/users.py

session:
  last_checkpoint: step_3_complete
  resume_from: step_4
```

**New Knowledge Entry:**

```markdown
# State Management Pattern

## When to Use

- Long-running directives (>30 minutes)
- Multi-session workflows
- Complex orchestration

## How to Implement

1. Create state file at directive start
2. Update after each step completion
3. Check for resume on directive start
4. Archive on completion
```

---

### 6. Deviation Rules (Auto-Fix Patterns)

**GSD Pattern:**

```markdown
## RULE 1: Auto-fix bugs

**Trigger:** Code doesn't work as intended
**Action:** Fix immediately, track for Summary

## RULE 2: Auto-add missing critical functionality

**Trigger:** Missing essential features for correctness/security
**Action:** Add immediately, track for Summary

## RULE 3: Auto-fix blocking issues

**Trigger:** Something prevents completing current task
**Action:** Fix immediately to unblock

## RULE 4: Ask about architectural changes

**Trigger:** Fix requires significant structural modification
**Action:** STOP, present to user, wait for decision
```

**Current Kiwi MCP:**

- No standardized deviation handling
- No clear escalation rules

**Proposed Enhancement:**

Create `directives/patterns/deviation_handling.md`:

```xml
<directive name="deviation_handling" version="1.0.0">
  <metadata>
    <description>Standard patterns for handling unexpected issues during directive execution</description>
    <category>patterns</category>
  </metadata>

  <rules>
    <rule name="auto_fix_bugs" severity="critical">
      <trigger>Code doesn't work as intended</trigger>
      <action>Fix immediately without asking</action>
      <track>Log in execution summary</track>
    </rule>

    <rule name="auto_fix_blocking" severity="high">
      <trigger>Cannot proceed with current step</trigger>
      <action>Resolve blocker, continue execution</action>
      <track>Log in execution summary</track>
    </rule>

    <rule name="ask_architectural" severity="medium">
      <trigger>Fix requires significant structural change</trigger>
      <action>Pause, present options, wait for user decision</action>
      <checkpoint>true</checkpoint>
    </rule>

    <rule name="ask_scope_expansion" severity="low">
      <trigger>Nice-to-have discovered during execution</trigger>
      <action>Note for future, continue with plan</action>
      <track>Log as suggestion</track>
    </rule>
  </rules>
</directive>
```

**Knowledge Entry:**

```markdown
# Deviation Handling Best Practices

## Auto-Fix Categories

1. **Bugs** - Fix immediately (broken code must work)
2. **Security** - Fix immediately (never ship vulnerable)
3. **Blocking** - Fix to continue (missing deps, wrong paths)

## Ask First Categories

1. **Architecture** - New tables, services, patterns
2. **Scope** - Features not in original plan
3. **Cost** - Paid services, API limits
```

---

### 7. Summary Documentation Pattern

**GSD Pattern:**

```markdown
---
phase: 01-foundation
plan: 02
subsystem: auth
tags: [jwt, jose, prisma]

requires:
  - phase: 01-foundation
    provides: [User model, Session model]
provides:
  - JWT authentication with refresh tokens
  - Protected route middleware
affects: [02-features, 03-api]

tech-stack:
  added: [jose, bcrypt]
  patterns: [JWT refresh rotation, httpOnly cookies]

key-files:
  created: [src/lib/auth.ts, src/middleware.ts]
  modified: [prisma/schema.prisma]

duration: 28min
completed: 2025-01-18
---

# Phase 1: Foundation Summary

**JWT auth with refresh rotation using jose library**

## Accomplishments

- User model with email/password auth
- Login/logout endpoints with httpOnly JWT cookies
- Protected route middleware

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added password hashing**

- Found during: Task 2
- Fix: Added bcrypt hashing
```

**Current Kiwi MCP:**

- No execution summaries
- No tracking of what was accomplished
- No dependency graph between directives

**Proposed Enhancement:**

Create automatic summary generation:

```xml
<directive name="execution_summary" version="1.0.0">
  <metadata>
    <description>Generate execution summary after directive completion</description>
    <trigger>directive_complete</trigger>
  </metadata>

  <process>
    <step name="collect_metrics">
      <action>
        Gather:
        - Start/end timestamps
        - Steps completed
        - Files created/modified
        - Deviations encountered
      </action>
    </step>

    <step name="generate_summary">
      <action>
        Create summary in .ai/outputs/summaries/{directive}_{timestamp}.md
      </action>
      <template>templates/execution_summary.md</template>
    </step>

    <step name="update_knowledge">
      <action>
        If learnings discovered, create knowledge entry
      </action>
    </step>
  </process>
</directive>
```

**Template:**

```markdown
---
directive: { directive_name }
executed: { timestamp }
duration: { duration }

provides:
  - { output_1 }
  - { output_2 }

tech_used: [{ tech_1 }, { tech_2 }]

files:
  created: [{ file_1 }]
  modified: [{ file_2 }]
---

# {directive_name} Execution Summary

**{one_liner_outcome}**

## Accomplishments

{accomplishments_list}

## Deviations

{deviations_or_none}

## Learnings

{learnings_for_knowledge_base}
```

---

### 8. Verification Patterns

**GSD Pattern:**

```markdown
## Verification Levels

1. **Exists** - File is present at expected path
2. **Substantive** - Content is real implementation, not placeholder
3. **Wired** - Connected to the rest of the system
4. **Functional** - Actually works when invoked

## Stub Detection

- TODO/FIXME/PLACEHOLDER comments
- return null/undefined/{}
- Empty handlers: onClick={() => {}}
- Hardcoded values where dynamic expected
```

**Current Kiwi MCP:**

- No verification patterns
- No stub detection
- No automated validation

**Proposed Enhancement:**

Create verification knowledge and directives:

**Knowledge Entry: `knowledge/verification_patterns.md`**

````markdown
# Verification Patterns

## Core Principle

**Existence ≠ Implementation**

A file existing does not mean the feature works.

## Verification Levels

| Level       | Check                | Automation     |
| ----------- | -------------------- | -------------- |
| Exists      | File at path         | ✓ Automated    |
| Substantive | Real code, not stubs | ✓ Automated    |
| Wired       | Connected to system  | ✓ Automated    |
| Functional  | Actually works       | Human required |

## Stub Detection Patterns

### Universal Stubs

```bash
grep -E "(TODO|FIXME|PLACEHOLDER)" "$file"
grep -E "return null|return undefined|return {}" "$file"
grep -E "console.log.*only" "$file"
```
````

### React Stubs

```javascript
// RED FLAGS:
return <div>Placeholder</div>
onClick={() => {}}
onChange={() => console.log('clicked')}
```

### API Stubs

```typescript
// RED FLAGS:
return Response.json({ message: "Not implemented" });
return Response.json([]); // Empty array with no DB query
```

````

**Verification Directive:**

```xml
<directive name="verify_implementation" version="1.0.0">
  <metadata>
    <description>Verify code implementation is real, not stubs</description>
  </metadata>

  <inputs>
    <input name="files" type="array" required="true">
      Files to verify
    </input>
  </inputs>

  <process>
    <step name="check_existence">
      <action>Verify all files exist at expected paths</action>
    </step>

    <step name="detect_stubs">
      <action>
        Run stub detection patterns:
        - TODO/FIXME comments
        - Placeholder returns
        - Empty handlers
      </action>
    </step>

    <step name="check_wiring">
      <action>
        Verify connections:
        - Component → API calls
        - API → Database queries
        - Form → Handlers
      </action>
    </step>

    <step name="report">
      <action>Generate verification report</action>
      <output>
        - Verified: {count}
        - Stubs found: {count}
        - Human verification needed: {list}
      </output>
    </step>
  </process>
</directive>
````

---

### 9. Context Engineering (Quality Degradation Curve)

**GSD Pattern:**

```markdown
## Quality Degradation Curve

| Context Usage | Quality   | Claude's State          |
| ------------- | --------- | ----------------------- |
| 0-30%         | PEAK      | Thorough, comprehensive |
| 30-50%        | GOOD      | Confident, solid work   |
| 50-70%        | DEGRADING | Efficiency mode begins  |
| 70%+          | POOR      | Rushed, minimal         |

## Solution

- 2-3 tasks per plan maximum
- Fresh context per plan execution
- Orchestrator stays lean, delegates heavy work
```

**Current Kiwi MCP:**

- No context budget awareness
- No guidance on step sizing
- No subagent spawning for heavy work

**Proposed Enhancement:**

**Knowledge Entry: `knowledge/context_engineering.md`**

```markdown
# Context Engineering for Directives

## The Problem: Context Rot

As context window fills, AI quality degrades:

- 0-30%: Peak performance
- 30-50%: Good quality
- 50-70%: Degrading
- 70%+: Poor, rushed output

## Solutions

### 1. Keep Directives Atomic

- 2-5 steps per directive
- Each step ~15-60 minutes of work
- Split large workflows into linked directives

### 2. Use Subagents for Heavy Work

- Orchestrator directive stays lean
- Spawn subagents for execution
- Fresh context per subagent

### 3. Progressive Context Loading

- Load only what's needed for current step
- Use @-references for lazy loading
- Archive completed context

## Step Sizing Guide

| Duration  | Action                           |
| --------- | -------------------------------- |
| < 15 min  | Too small — combine with related |
| 15-60 min | Right size — single focused unit |
| > 60 min  | Too large — split into smaller   |
```

**Directive Metadata Enhancement:**

```xml
<metadata>
  <context_budget>
    <estimated_usage>30%</estimated_usage>
    <subagent_recommended>false</subagent_recommended>
    <lazy_load_refs>true</lazy_load_refs>
  </context_budget>
</metadata>
```

---

### 10. Atomic Commit Pattern

**GSD Pattern:**

```bash
# Each task gets its own commit
git add src/auth.ts
git commit -m "feat(02-01): add JWT authentication"

git add src/middleware.ts
git commit -m "feat(02-01): add protected route middleware"

# Benefits:
# - Git bisect finds exact failing task
# - Each task independently revertable
# - Clear history for future context
```

**Current Kiwi MCP:**

- No commit guidance
- No tracking of changes per step

**Proposed Enhancement:**

Add to directive execution:

```xml
<step name="create_auth" commit="true">
  <action>Create authentication module</action>
  <commit_message>feat({directive}): add JWT authentication</commit_message>
  <files_to_stage>
    <file>src/auth.ts</file>
    <file>src/types/auth.ts</file>
  </files_to_stage>
</step>
```

**Knowledge Entry: `knowledge/git_patterns.md`**

```markdown
# Git Integration Patterns

## Atomic Commits

Each directive step should commit atomically:

- Stage only step-related files
- Never use `git add .`
- Capture commit hash for summary

## Commit Format
```

{type}({directive}-{step}): {description}

- {change 1}
- {change 2}

```

## Types
| Type | Use |
|------|-----|
| feat | New feature |
| fix | Bug fix |
| docs | Documentation |
| refactor | Code cleanup |
| test | Tests only |
```

---

## Feature Comparison Matrix

| Feature                   | GSD     | Kiwi MCP             | Port Priority |
| ------------------------- | ------- | -------------------- | ------------- |
| Progressive disclosure    | ✅ Full | ❌ None              | 🔴 High       |
| Structured task format    | ✅ Full | ⚠️ Basic             | 🔴 High       |
| Checkpoint system         | ✅ Full | ❌ None              | 🔴 High       |
| Wave parallelism          | ✅ Full | ⚠️ Metadata only     | 🟡 Medium     |
| State management          | ✅ Full | ❌ None              | 🔴 High       |
| Deviation rules           | ✅ Full | ❌ None              | 🟡 Medium     |
| Execution summaries       | ✅ Full | ❌ None              | 🔴 High       |
| Verification patterns     | ✅ Full | ❌ None              | 🟡 Medium     |
| Context engineering       | ✅ Full | ⚠️ model_class       | 🟡 Medium     |
| Atomic commits            | ✅ Full | ❌ None              | 🟢 Low        |
| Multi-agent orchestration | ✅ Full | ⚠️ Subagent metadata | 🟡 Medium     |
| Template system           | ✅ Full | ❌ None              | 🔴 High       |
| Reference docs            | ✅ Full | ⚠️ Knowledge entries | 🟢 Low        |
| UI/UX patterns            | ✅ Full | ❌ None              | 🟢 Low        |
| Brownfield detection      | ✅ Full | ❌ None              | 🟢 Low        |
| TDD workflow              | ✅ Full | ❌ None              | 🟢 Low        |

---

## Implementation Roadmap

### Phase 1: High Priority (Foundation)

1. **Enhanced Step Format**

   - Add `<files>`, `<verify>`, `<done>` to step schema
   - Update directive parser
   - Add validation

2. **Checkpoint System**

   - Add `<checkpoint>` element to schema
   - Implement checkpoint handlers
   - Create checkpoint knowledge entries

3. **State Management**

   - Create workflow state directive
   - Add state persistence to execution
   - Implement resume from state

4. **Execution Summaries**

   - Create summary template
   - Add auto-generation on directive complete
   - Link summaries to knowledge base

5. **Template System**
   - Create templates directory
   - Add template reference to directives
   - Implement template loading

### Phase 2: Medium Priority (Enhancement)

6. **Wave Parallelism**

   - Enhance wave metadata
   - Implement wave execution in handler
   - Add dependency tracking

7. **Deviation Rules**

   - Create deviation handling directive
   - Add deviation tracking to execution
   - Create escalation patterns

8. **Verification Patterns**

   - Create verification knowledge entries
   - Build verification directives
   - Add stub detection

9. **Context Engineering**

   - Add context budget metadata
   - Implement subagent spawning
   - Add lazy loading support

10. **Multi-Agent Orchestration**
    - Enhance subagent_strategy
    - Implement agent spawning
    - Add result aggregation

### Phase 3: Low Priority (Polish)

11. **Atomic Commits**

    - Add commit support to steps
    - Implement commit tracking
    - Add to summaries

12. **UI Patterns**

    - Create output formatting knowledge
    - Add progress indicators
    - Standardize user prompts

13. **Brownfield Detection**

    - Add codebase mapping directive
    - Create stack detection
    - Integrate with init

14. **TDD Workflow**
    - Create TDD directive pattern
    - Add red/green/refactor tracking
    - Link to testing knowledge

---

## Code Examples for Implementation

### Example 1: Enhanced Directive with GSD Patterns

```xml
<directive name="create_api_endpoint" version="2.0.0">
  <metadata>
    <description>Create a REST API endpoint with full CRUD operations</description>
    <category>development</category>
    <author>kiwi-mcp</author>
    <model_class tier="balanced" fallback="reasoning" parallel="false">
      Standard development task with verification
    </model_class>
    <permissions>
      <read resource="filesystem" path="src/**/*" />
      <write resource="filesystem" path="src/**/*" />
      <execute resource="shell" command="npm" />
    </permissions>
    <context_budget>
      <estimated_usage>40%</estimated_usage>
      <step_count>5</step_count>
    </context_budget>
  </metadata>

  <references>
    <template ref="templates/api_route.md" />
    <knowledge ref="knowledge/rest_patterns.md" />
    <knowledge ref="knowledge/verification_patterns.md" />
  </references>

  <inputs>
    <input name="resource_name" type="string" required="true">
      Name of the resource (e.g., "users", "products")
    </input>
    <input name="fields" type="array" required="true">
      List of fields for the resource
    </input>
  </inputs>

  <process>
    <wave number="1">
      <step name="create_schema" type="auto">
        <description>Create database schema for resource</description>
        <files>prisma/schema.prisma</files>
        <action>
          <![CDATA[
          Add {resource_name} model to Prisma schema with fields:
          - id (UUID, default)
          - createdAt, updatedAt (DateTime)
          - {fields} with appropriate types
          Run: npx prisma db push
          ]]>
        </action>
        <verify>
          <command>npx prisma db push --dry-run</command>
          <expect>No errors, schema valid</expect>
        </verify>
        <done>Model exists in schema, migrations applied</done>
      </step>
    </wave>

    <wave number="2" depends_on="1">
      <step name="create_routes" type="auto" parallel="true">
        <description>Create API route handlers</description>
        <files>src/app/api/{resource_name}/route.ts</files>
        <action>
          <![CDATA[
          Create route.ts with:
          - GET: List all with pagination
          - POST: Create with validation
          Include error handling and proper status codes.
          ]]>
        </action>
        <verify>
          <command>npx tsc --noEmit</command>
          <expect>No TypeScript errors</expect>
        </verify>
        <done>Route handlers compile without errors</done>
      </step>

      <step name="create_route_by_id" type="auto" parallel="true">
        <description>Create single resource route handlers</description>
        <files>src/app/api/{resource_name}/[id]/route.ts</files>
        <action>
          <![CDATA[
          Create [id]/route.ts with:
          - GET: Fetch single by ID
          - PUT: Update with validation
          - DELETE: Soft delete
          ]]>
        </action>
        <verify>
          <command>npx tsc --noEmit</command>
          <expect>No TypeScript errors</expect>
        </verify>
        <done>Route handlers compile without errors</done>
      </step>
    </wave>

    <wave number="3" depends_on="2">
      <checkpoint type="human-verify" gate="blocking">
        <what_built>REST API for {resource_name} at /api/{resource_name}</what_built>
        <how_to_verify>
          <![CDATA[
          1. Run: npm run dev
          2. Test GET /api/{resource_name} - returns empty array
          3. Test POST /api/{resource_name} with valid data - returns 201
          4. Test GET /api/{resource_name}/{id} - returns created resource
          5. Test PUT /api/{resource_name}/{id} - updates resource
          6. Test DELETE /api/{resource_name}/{id} - returns 204
          ]]>
        </how_to_verify>
        <resume_signal>Type "approved" or describe issues</resume_signal>
      </checkpoint>
    </wave>
  </process>

  <deviation_rules>
    <auto_fix>bugs, blocking, security</auto_fix>
    <ask_first>architecture, scope_expansion</ask_first>
  </deviation_rules>

  <outputs>
    <success>
      <![CDATA[
      API endpoint created:
      - Schema: prisma/schema.prisma (model added)
      - Routes: src/app/api/{resource_name}/route.ts
      - Single: src/app/api/{resource_name}/[id]/route.ts

      Next steps:
      1. Add authentication middleware
      2. Add input validation schemas
      3. Add integration tests
      ]]>
    </success>
    <failure>
      <![CDATA[
      Common issues:
      - Database connection failed: Check DATABASE_URL in .env
      - TypeScript errors: Run npx tsc --noEmit for details
      - Prisma errors: Run npx prisma generate
      ]]>
    </failure>
  </outputs>
</directive>
```

### Example 2: Workflow State Template

```yaml
# .ai/state/workflow_state.yaml

workflow:
  directive: create_api_endpoint
  version: "2.0.0"
  started: 2025-01-18T10:00:00Z
  last_activity: 2025-01-18T10:45:00Z

position:
  current_wave: 2
  total_waves: 3
  current_step: create_routes
  completed_steps:
    - create_schema
  pending_steps:
    - create_route_by_id
    - human_verify
  status: in_progress
  progress: 40%

inputs:
  resource_name: products
  fields:
    - name: name
      type: String
    - name: price
      type: Decimal
    - name: description
      type: String

context:
  decisions:
    - step: create_schema
      decision: "Used Decimal for price instead of Float"
      rationale: "Better precision for currency"

  deviations:
    - rule: blocking
      description: "Added @id @default(uuid()) annotation"
      step: create_schema

outputs:
  files_created:
    - prisma/schema.prisma
  files_modified: []
  commits:
    - hash: abc123
      message: "feat(create_api_endpoint): add products schema"

checkpoints:
  pending:
    - type: human-verify
      step: wave_3
      description: "Verify API endpoints work correctly"

session:
  can_resume: true
  resume_from: create_route_by_id
  context_snapshot: .ai/state/snapshots/create_api_endpoint_wave2.json
```

---

## Knowledge Base Entries to Create

Based on GSD patterns, create these knowledge entries:

| Entry ID                     | Title                        | Content Source               |
| ---------------------------- | ---------------------------- | ---------------------------- |
| `001-checkpoint-patterns`    | Checkpoint Types and Usage   | GSD checkpoints.md           |
| `002-verification-levels`    | Verification Patterns        | GSD verification-patterns.md |
| `003-context-engineering`    | Context Budget Management    | GSD philosophy sections      |
| `004-deviation-handling`     | Auto-Fix vs Ask First Rules  | GSD executor deviation_rules |
| `005-task-sizing`            | Step Sizing Guidelines       | GSD planner task_breakdown   |
| `006-stub-detection`         | Identifying Placeholder Code | GSD verification-patterns.md |
| `007-git-integration`        | Atomic Commit Patterns       | GSD git-integration.md       |
| `008-progressive-disclosure` | Information Layering         | GSD-STYLE.md                 |
| `009-wave-execution`         | Parallel Execution Patterns  | GSD execute-phase.md         |
| `010-state-management`       | Workflow State Persistence   | GSD state.md template        |

---

## Conclusion

GSD provides a comprehensive framework for AI-assisted development that Kiwi MCP can learn from significantly. The key innovations to port:

1. **Structured execution** - Tasks with files, actions, verification, done criteria
2. **Human interaction** - Checkpoint system for verification and decisions
3. **State persistence** - Workflow state that survives context limits
4. **Quality control** - Deviation rules, verification patterns, stub detection
5. **Parallel execution** - Wave-based orchestration
6. **Documentation** - Automatic summaries with dependency tracking

By incorporating these patterns, Kiwi MCP's directives become more robust, resumable, verifiable, and maintainable - moving from simple instruction sequences to full workflow orchestration.
