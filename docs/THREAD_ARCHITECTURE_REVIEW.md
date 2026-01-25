# THREAD_AND_STREAMING_ARCHITECTURE.md - Review Report

**Date:** 2026-01-25  
**Reviewer:** AI Assistant  
**Document Version:** Draft (6053 lines)

---

## Executive Summary

This review evaluates THREAD_AND_STREAMING_ARCHITECTURE.md against core architectural principles and cross-references with PERMISSION_MODEL.md. Overall, the document is **architecturally sound** and demonstrates strong adherence to the "kernel stays dumb" principle. However, there are several **critical terminology inconsistencies**, **missing clarifications**, and **minor technical issues** that need addressing for production readiness.

**Key Findings:**
- ✅ Core principle "kernel stays dumb" is consistently maintained
- ✅ Data-driven architecture is well-explained and consistent
- ✅ Three-layer thread spawning model is clear
- ⚠️ Critical terminology confusion between tools and directives
- ⚠️ Incomplete explanation of harness instantiation flow
- ⚠️ Thread registry permission model needs stronger emphasis
- ⚠️ Some code examples contain minor inconsistencies

---

## Critical Issues (Must Fix)

### 1. **Terminology Confusion: `run_directive` vs `thread_directive`**

**Lines: 1352-1360, 4321**

The document uses `run_directive` in two conflicting ways:

**Current text (Line 1354):**
> **Terminology Note:** `run_directive` and `thread_directive` are distinct in Kiwi:
> 1. **run_directive directive** - `.ai/directives/run_directive.md` - Workflow instructions
> 2. **thread_directive tool** - `.ai/tools/orchestration/thread_directive.yaml` - Executable tool

**Problem:** This creates confusion because:
- Line 1352 section header says "The run_directive Directive"
- Line 4321 mentions "run_directive directive" again
- But the actual tool that LLMs call is `thread_directive` (Layer 3 in Appendix A.1)
- The document sometimes implies LLMs call `run_directive`, other times `thread_directive`

**Evidence from document:**
- Line 1357: "run_directive directive" - workflow instructions (OK)
- Line 1358: "thread_directive tool" - executable tool (OK)
- Line 1438: Example shows calling `thread_directive` tool (Correct)
- Line 4321: "run_directive directive (workflow instructions)" (OK)
- BUT: No clear statement that LLMs should NOT call a tool named `run_directive`

**Impact:** Medium-High. Implementers might create the wrong tool names.

**Recommendation:**
Add explicit clarification in Line 1360 section:
```xml
**Critical distinction:**
- `run_directive` is a DIRECTIVE (.ai/directives/run_directive.md) that provides guidance
- `thread_directive` is the TOOL (.ai/tools/orchestration/thread_directive.yaml) that LLMs actually call
- There is NO tool named `run_directive` - this would cause confusion
- LLMs reference the directive for guidance, but call the thread_directive tool for execution
```

---

### 2. **Harness Instantiation Flow Incomplete**

**Lines: 4380-4432, 1626-1680**

The document explains that `spawn_thread` instantiates the harness, but the **actual flow** is confusing across multiple sections.

**Problem:** Three different explanations of who instantiates `KiwiHarnessRunner`:

**Version 1 (Line 1709-1714):**
```
kiwi_harness.spawn.spawn_directive_thread():
  1. Generate thread_id
  2. Load directive, mint capability token
  3. Spawn background thread with KiwiHarnessRunner
```

**Version 2 (Line 4218-4244 - Appendix A.1):**
```python
# kiwi_harness tool instantiates KiwiHarnessRunner
async def spawn_with_kiwi_harness(...):
    runner = KiwiHarnessRunner(...)
    return await execute_tool("spawn_thread", {
        "runner_instance": runner,  # Pass instantiated runner
    })
```

**Version 3 (Line 4401-4410 - Appendix A.2):**
```
4. spawn_thread tool (Layer 1 - Python runtime tool):
   ├── Imports kiwi_harness package
   ├── Creates KiwiHarnessRunner instance
```

**Contradiction:** Version 2 says `kiwi_harness` tool instantiates the runner and passes it to `spawn_thread`. Version 3 says `spawn_thread` imports and instantiates it. These are incompatible.

**From PERMISSION_MODEL.md (lines 109-116):**
The permission document shows harness loads directive AFTER spawning:
```python
# Inside spawned thread, KiwiHarnessRunner loads directive
directive_data = await mcp.execute(...)
```

**Impact:** High. This is a critical implementation detail that must be correct.

**Correct Flow (based on Layer 2 definition in A.1):**
1. LLM calls `thread_directive` tool (Layer 3 validation/orchestration)
2. `thread_directive` calls `kiwi_harness` tool (Layer 2 Kiwi implementation)
3. `kiwi_harness` instantiates `KiwiHarnessRunner` object
4. `kiwi_harness` calls `spawn_thread` with `runner_instance` parameter
5. `spawn_thread` spawns OS thread/process with the runner
6. Inside spawned thread: `runner.run()` loads directive, mints token, starts loop

**Recommendation:**
- Fix Line 4401-4410 (Version 3) to match Version 2
- Change Line 4401 from "spawn_thread tool imports and creates" to "spawn_thread tool receives pre-instantiated runner from kiwi_harness"
- Add sequence diagram in Appendix A.1 showing the complete flow with all 3 layers

---

### 3. **Token Minting Location Ambiguity**

**Lines: 4650-4662, 1709-1714**

**Problem:** Multiple contradictory statements about when/where tokens are minted:

**Statement 1 (Line 1712):**
```
kiwi_harness.spawn.spawn_directive_thread():
  2. Load directive, mint capability token  ← Before spawning
  3. Spawn background thread with KiwiHarnessRunner
```

**Statement 2 (Line 4650-4662):**
```
- thread_directive tool (Layer 3) does NOT mint tokens
- kiwi_harness tool (Layer 2) does NOT mint tokens
- spawn_thread tool (Layer 1) instantiates KiwiHarnessRunner class
- KiwiHarnessRunner.run_directive() method is what actually:
  1. Loads the directive via MCP
  2. Extracts <permissions>
  3. Mints the capability token  ← INSIDE spawned thread
  4. Stores it in ThreadContext
```

**From PERMISSION_MODEL.md (lines 128-150):**
Confirms Statement 2 is correct - token minted INSIDE spawned thread after directive is loaded.

**Impact:** High. This affects implementation order and permission flow understanding.

**Recommendation:**
- Fix Line 1712 to remove "mint capability token" from pre-spawn phase
- Update to: "2. Auto-generate thread_id, prepare spawn parameters"
- Ensure all references consistently show token minting happens INSIDE spawned thread

---

### 4. **Thread Registry Permission Model Insufficient**

**Lines: 4529-4571, 22**

**Problem:** Document states thread_registry is "privileged internal tool" but permission model contradicts this.

**Line 22 (Executive Summary):**
```
5. Thread Registry - Privileged internal tool used by harness, 
   not subject to directive permissions
```

**Lines 4529-4571 (Appendix A.2):**
```yaml
# thread_registry Tool (Regular MCP Tool)
requires:
  - registry.write  # For register, update_status
  - registry.read   # For get_status, query
```

```python
# thread_registry tool implementation
async def register_thread(params: dict) -> dict:
    token = params.get("__auth")
    if not validate_token(token, required_caps=["registry.write"]):
        return {"error": "Missing required capability: registry.write"}
```

**Contradiction:** 
- Executive summary says "not subject to directive permissions"
- Implementation shows it REQUIRES permissions and validates tokens
- This is actually correct behavior (matches PERMISSION_MODEL.md), but executive summary is wrong

**From PERMISSION_MODEL.md (lines 4434-4448):**
Confirms thread_registry is a regular tool requiring system capabilities, NOT a special bypassed tool.

**Impact:** Medium. Could lead to incorrect assumptions about security model.

**Recommendation:**
- Fix Executive Summary Line 22-23
- Change to: "Thread Registry - Regular MCP tool requiring system capabilities (registry.write/read), only accessible to core directives"
- Remove "not subject to directive permissions" claim
- Add emphasis that thread_registry is NOT special - it's the core directives that call it that are special (they have the required capabilities)

---

## Minor Inconsistencies (Should Fix)

### 5. **Sink Instantiation Timing**

**Lines: 324-376, 451-495**

**Problem:** Document says sinks are instantiated at "chain resolution time" but doesn't clarify if this is before or during http_client execution.

**Line 328 comment:**
```python
"""Execute streaming HTTP request with destination fan-out.

Sinks are pre-instantiated by the tool executor at chain resolution time.
See tool chain resolution section above for sink instantiation logic.
"""
```

**Line 453 (Sink Architecture):**
```
Where Sinks Are Instantiated:

Sink instantiation happens at **tool chain resolution time** 
in the tool executor, NOT in http_client.
```

**Ambiguity:** "Chain resolution time" could mean:
- Before http_client is called (sinks passed as parameter) ✓ Correct
- During http_client execution (http_client loads sinks) ✗ Wrong

**Evidence it's pre-instantiation:**
Line 333 shows `sinks = params.pop("__sinks", [])` - sinks come FROM params, not loaded by http_client.

**Impact:** Low. Implementation is clear in code examples, but terminology could be clearer.

**Recommendation:**
Change Line 453 to: "Sink instantiation happens **before http_client execution** by the tool executor during chain resolution. Sinks are passed to http_client via `__sinks` parameter."

---

### 6. **Code Example Inconsistency: Thread ID Generation**

**Lines: 1712, 4213-4216**

**Problem:** Two different patterns for thread ID generation shown:

**Version 1 (Line 1712):**
```
"deploy_staging_20260125_103045"
```

**Version 2 (Line 4216):**
```python
def generate_thread_id(directive_name: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{directive_name}_{timestamp}"
    # Example: "deploy_staging_20260125_103045"
```

**Consistency check:** Both produce the same format. ✅ No issue here, actually.

**However:** Line 760 shows same pattern again, and all three locations should be kept in sync if format ever changes.

**Impact:** Very Low. Just a maintenance consideration.

**Recommendation:**
Add a note in one location (suggest Line 4216) stating: "This format is used consistently throughout documentation examples. Any format changes should update all references."

---

### 7. **Missing Cross-Reference to Permission Model**

**Lines: 2817-2893, 4366-4869**

**Problem:** Permission sections provide **good summaries** but lack consistent cross-references to PERMISSION_MODEL.md for details.

**Current cross-references:**
- Line 153: ✅ Links to PERMISSION_MODEL.md in principles
- Line 2819: ✅ Links with list of topics
- Line 4436: ✅ Links with list of topics
- Line 4606: ✅ Links with complete details list
- Line 4672: ✅ Links for capability system

**Missing cross-references:**
- Line 2815-2893 (Layer 6 section): Explains tokens but no link
- Line 4788-4817 (Token Structure): Detailed example but no link

**Impact:** Very Low. Document already has good cross-references overall.

**Recommendation:**
Add one-liner at start of Line 2815 section: "See [PERMISSION_MODEL.md](./PERMISSION_MODEL.md) for complete token lifecycle and enforcement details."

---

## Suggestions for Clarity

### 8. **"Kernel Stays Dumb" - Definition Could Be Earlier**

**Lines: 149, 1246-1254**

**Current structure:**
- Line 149: Listed as principle #1
- Line 1246: First detailed explanation in Layer 4.5

**Suggestion:**
Add expanded definition in "Key Architectural Principles" section (around Line 149):

```markdown
1. **Kernel Stays Dumb**: 
   - MCP kernel has NO thread logic - it only loads and returns data
   - Thread spawning is a tool call, not kernel behavior
   - Kernel forwards capability tokens opaquely, never interprets them
   - All decision-making happens in harness or tools, not kernel
   - Example: execute(directive, run, X) always returns directive data; LLM decides whether to spawn thread
```

**Impact:** Low. Would improve comprehension on first read.

---

### 9. **Async Spawn Pattern Inconsistently Emphasized**

**Lines: 23, 1677-1679, 3244-3585**

**Problem:** Async spawn behavior is mentioned in multiple places but not consistently emphasized as a critical behavior.

**Line 23 (Executive Summary):** ✅ "Spawn Returns Immediately"
**Line 1677:** ✅ "Both spawn_thread and kiwi_harness are async spawn operations"
**Line 3244:** ✅ Full section on "Thread Monitoring & Async Spawn Pattern"

**Missing:** No async warning in the three-layer tool definitions (Appendix A.1, Lines 4108-4323)

**Recommendation:**
Add async behavior note to each layer definition in A.1:
```yaml
# Layer 1: spawn_thread
config:
  background: true  # CRITICAL: Returns immediately, thread runs async
```

**Impact:** Low. Already well-documented, just could use one more reminder.

---

### 10. **Context vs Cost Budget Separation**

**Lines: 23, 826-890, 5212-5404**

**Current explanation:** Line 23 executive summary mentions "Context vs Cost - Separate concerns" but doesn't explain the difference.

**Detailed explanation:** Lines 826-890 (ContextBudget class) and Section A.4 (Line 5212) explain thoroughly.

**Gap:** No quick summary of the difference for readers who just skim the executive summary.

**Suggestion:**
Add to Line 23 (or new Line 24):
```
8. Context vs Cost - Separate concerns:
   • Context = current input tokens per call (model limit, e.g., 200k tokens)
   • Cost = cumulative usage across thread lifetime (budget limit, e.g., $10 total)
   • Both tracked independently, either can trigger termination
```

**Impact:** Very Low. Would improve skim-reading comprehension.

---

## Missing Pieces

### 11. **No Diagram for Three-Layer Spawning**

**Lines: 4104-4323**

**Gap:** Appendix A.1 explains three-layer thread spawning in detail, but lacks a visual diagram showing the complete flow.

**Current text-based diagram (Line 4325-4348):** Shows static layer structure but not execution flow.

**Recommendation:**
Add sequence diagram after Line 4348:

```
THREAD SPAWNING SEQUENCE (Three Layers)

LLM (in current thread)
  │
  │ execute(tool, run, thread_directive, {directive_name: "deploy"})
  ▼
Layer 3: thread_directive tool
  │ ├── Load directive metadata
  │ ├── Validate <cost>, <permissions>, <model>, version
  │ └── Call kiwi_harness
  ▼
Layer 2: kiwi_harness tool
  │ ├── Generate thread_id = "deploy_20260125_103045"
  │ ├── Instantiate: runner = KiwiHarnessRunner(...)
  │ └── Call spawn_thread with runner_instance
  ▼
Layer 1: spawn_thread tool
  │ ├── Validate thread_id uniqueness
  │ ├── Spawn OS thread: threading.Thread(target=runner.run, ...)
  │ └── Return {"thread_id": "...", "status": "spawned"}
  │
  │ [Async boundary - caller returns immediately]
  │
  ▼
INSIDE SPAWNED THREAD: runner.run()
  │ ├── Load directive via MCP
  │ ├── Extract <permissions> from directive
  │ ├── Mint capability token
  │ ├── Build system prompt from AGENTS.md
  │ └── Start agent loop (call LLM → execute tools → repeat)
```

**Impact:** Low. Would significantly improve understanding of the most complex part.

---

### 12. **Error Handling Examples Missing**

**Lines: 4350-4363, 5987-6036**

**Current coverage:**
- Line 4350: Error response format (basic)
- Line 5991: Error wrapping pattern (general)
- Line 6011: Example error response (validation)

**Gap:** No error handling examples for:
- Thread ID collision (spawn_thread returns existing thread error)
- Permission denied during tool execution (token validation fails)
- Cost budget exceeded mid-execution (harness terminates)
- Stream interruption recovery (reconnection logic)

**Recommendation:**
Add subsection in Layer 8.5 (Thread Monitoring) showing error handling:

```markdown
### Common Error Scenarios

#### Thread ID Collision
If spawn_thread is called with duplicate thread_id:
- Base layer (spawn_thread): Returns collision error
- kiwi_harness layer: Regenerates thread_id with microseconds
- thread_directive layer: Retries with new ID (max 3 attempts)

#### Permission Denied
If tool requires capability not in token:
- Tool validates token, returns structured error
- Harness formats for LLM: "Cannot execute write_file: missing fs.write capability"
- LLM can search for alternative approach or report to user

#### Cost Budget Exceeded
When max_turns, max_tokens, or max_usd exceeded:
- Cost tracker detects violation after LLM response
- Harness terminates loop immediately
- Final message injected: "Budget exceeded: X of Y used"
- Thread status set to "completed" with budget_exceeded flag
```

**Impact:** Low. Would help implementers handle edge cases correctly.

---

## Strengths

### What Works Well

1. **✅ Consistent "Kernel Stays Dumb" Application**
   - Every layer correctly shows kernel as data router
   - No special cases or kernel thread logic anywhere
   - Clear separation between kernel and harness responsibilities

2. **✅ Three-Layer Spawning Model**
   - Clear separation of concerns across layers
   - Base layer is harness-agnostic (excellent design)
   - Kiwi-specific layer adds opinionated defaults
   - High-level layer adds validation

3. **✅ Data-Driven Architecture**
   - Sinks, capabilities, extractors all follow same pattern
   - Tools are configuration, primitives are code (well-explained)
   - No hardcoded special cases

4. **✅ Permission Model Integration**
   - Capability tokens explained correctly
   - Tool-layer enforcement clearly described
   - Hierarchical permissions (core vs user) well-articulated
   - Path-based scoping integrated properly

5. **✅ Comprehensive Examples**
   - Code examples are detailed and mostly consistent
   - YAML tool definitions are production-ready
   - Python implementations show actual code patterns

6. **✅ Clear Cross-References**
   - Good use of "See Appendix X" links
   - References to PERMISSION_MODEL.md where appropriate
   - Internal section references for complex topics

7. **✅ Implementation Phases**
   - Realistic time estimates
   - Clear dependencies between phases
   - Concrete file paths and deliverables

---

## Architectural Alignment

### ✅ "Kernel Stays Dumb" Verification

**Checked all mentions of kernel behavior:**

- ✅ Line 14: "The MCP stays dumb. Threads are just tools."
- ✅ Line 1248: "The kernel has **no knowledge of threads**"
- ✅ Line 1263-1266: "Kernel: Parse, validate, return directive data (No thread logic...)"
- ✅ Line 2811: "Kernel stays dumb: Forwards opaque capability tokens"
- ✅ Line 4370: "MCP kernel does NOT: Know about 'threads'"
- ✅ Line 4642: "Kernel forwards opaquely (no validation)"

**Verdict:** ✅ Consistently maintained. No violations found.

---

### ✅ Data-Driven Pattern Verification

**Checked for hardcoded logic violations:**

- ✅ Sinks: All except `return` are data-driven tools (Lines 377-450)
- ✅ Capabilities: Data-driven tools in `.ai/tools/capabilities/` (Lines 4670-4710)
- ✅ Extractors: Referenced as parallel pattern to sinks (Lines 422-495)
- ✅ MCPs: Registry-based, not hardcoded (Lines 2966-3127)
- ✅ Thread spawning: Three-layer tool system, not kernel logic (Lines 4104-4323)

**Verdict:** ✅ Consistently applied. All extensibility points are data-driven.

---

### ✅ Permission Model Alignment

**Cross-checked with PERMISSION_MODEL.md:**

| Concept | THREAD doc | PERMISSION doc | Aligned? |
|---------|------------|----------------|----------|
| Token minting location | Inside spawned thread (Line 4656) | Inside spawned thread (Line 109) | ✅ Yes |
| Thread-scoped tokens | One per thread (Line 4617) | One per thread (Line 200) | ✅ Yes |
| Nested execution | Same thread, same token (Line 4838) | Same thread, same token (Line 226) | ✅ Yes |
| Hierarchical permissions | Core vs user (Line 4432) | Core vs user (Line 346) | ✅ Yes |
| Path scoping | Required for fs.* (Line 4751) | Required for fs.* (Line 593) | ✅ Yes |
| Project sandboxing | Default (Line 4522) | Default (Line 876) | ✅ Yes |
| System capabilities | SYSTEM_ONLY (Line 4459) | SYSTEM_ONLY (Line 646) | ✅ Yes |
| Tool enforcement | All tools validate (Line 4564) | All tools validate (Line 1117) | ✅ Yes |

**Verdict:** ✅ Fully aligned with PERMISSION_MODEL.md

---

## Summary Checklist

### Consistency
- ⚠️ **Terminology** - `run_directive` vs `thread_directive` needs clarification (Issue #1)
- ⚠️ **Harness instantiation** - Conflicting explanations need resolution (Issue #2)
- ⚠️ **Token minting** - Ambiguous timing needs fixing (Issue #3)
- ✅ Code examples are mostly consistent (minor issue #6)
- ✅ Diagrams match text descriptions

### Technical Correctness
- ✅ Data flows are logical and correct
- ✅ No circular dependencies found
- ✅ Three-layer spawning aligns with code examples
- ✅ Permission examples are accurate
- ⚠️ **Thread registry** - Permission model needs clarification (Issue #4)
- ✅ Cost/context budget systems clearly separated
- ✅ Streaming architecture is sound

### Clarity & Completeness
- ✅ Complex concepts well-explained
- ✅ No major missing pieces
- ✅ Code examples are complete
- ⚠️ `thread_directive` tool vs directive distinction could be clearer (Issue #1)
- ✅ Thread registry "optional" claim needs fixing (Issue #4)
- ✅ Direct vs managed execution clearly differentiated
- ⚠️ Missing visual diagram for three-layer spawning (Issue #11)

### Architectural Alignment
- ✅ "Kernel stays dumb" consistently maintained
- ✅ No special kernel logic violations
- ✅ Data-driven pattern applied throughout
- ✅ Permission enforcement at tool level (not kernel)
- ✅ Infrastructure tools treated as regular tools

### Specific Focus Areas
- ✅ Layer 4.5 (Execute Directive): Verified no thread logic in kernel
- ⚠️ Thread spawning flow: Clear in concept, conflicting in details (Issue #2)
- ⚠️ Harness architecture: Instantiation flow needs clarification (Issue #2)
- ⚠️ Sink architecture: Timing could be clearer (Issue #5)
- ✅ Permission examples show scopes and project sandboxing correctly
- ⚠️ Thread registry: "Privileged" claim incorrect (Issue #4)
- ✅ Package structure clear
- ✅ Streaming vs sync modes well-explained

---

## Priority Fixes

### 🔴 Must Fix Before Implementation

1. **Issue #2** - Harness Instantiation Flow (Lines 4380-4432)
   - Critical for correct implementation
   - Fix conflicting explanations of who instantiates KiwiHarnessRunner
   - Add sequence diagram

2. **Issue #3** - Token Minting Location (Lines 1709-1714, 4650-4662)
   - Critical for security architecture understanding
   - Ensure all references show minting INSIDE spawned thread

3. **Issue #1** - Terminology Clarification (Lines 1352-1360)
   - High priority to prevent implementation errors
   - Make tool vs directive distinction crystal clear

### 🟡 Should Fix Before Release

4. **Issue #4** - Thread Registry Permission Model (Line 22, 4529-4571)
   - Important for security understanding
   - Fix executive summary claim about "not subject to permissions"

5. **Issue #11** - Add Three-Layer Spawning Diagram (After Line 4348)
   - Would significantly improve comprehension
   - Most complex part of the architecture

### 🟢 Nice to Have

6. **Issue #8** - Earlier "Kernel Stays Dumb" Definition (Around Line 149)
7. **Issue #10** - Context vs Cost Quick Summary (Line 23-24)
8. **Issue #12** - Error Handling Examples (New subsection in Layer 8.5)

---

## Conclusion

The THREAD_AND_STREAMING_ARCHITECTURE.md document presents a **sound and well-designed architecture** that successfully maintains the "kernel stays dumb" principle while enabling sophisticated thread management, streaming, and permission enforcement.

**Strengths:**
- Architecturally correct and principled
- Comprehensive coverage of all layers
- Good integration with permission model
- Realistic implementation plan

**Weaknesses:**
- Several critical terminology inconsistencies (#1, #2, #3, #4)
- Some ambiguous explanations that could confuse implementers
- Missing visual diagrams for most complex parts

**Recommendation:** 
✅ **Approve architecture with required fixes**. Address Issues #1-4 before implementation begins. Issues #5-12 can be addressed during implementation or before final release.

**Estimated fix time:** 2-4 hours for critical issues, 4-6 hours for all issues.
