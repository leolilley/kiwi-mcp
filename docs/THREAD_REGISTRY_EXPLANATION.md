## Thread Registry: Complete Explanation

Let me break this down clearly:

### What is Thread Registry?

**Thread Registry** is a **monitoring and coordination database** (SQLite) that tracks:
- **Thread metadata** (thread_id, directive_name, status, timestamps)
- **Runtime state** (running, completed, error, paused, terminating)
- **Usage stats** (turn_count, token usage, cost)
- **Events** (tool calls, errors, warnings, interventions)

Think of it like a **process table** (like `ps` or `top` in Linux) but for LLM agent threads.

### What is it for?

**Primary use cases:**

1. **Monitoring active threads** - See what's running, how far along it is
2. **Intervention** - Pause, resume, or terminate threads
3. **Debugging** - Query events, see what tool calls happened
4. **Analytics** - Track historical thread performance, costs
5. **Coordination** - Check if a thread_id already exists before spawning

**Example queries:**
```python
# What's the status of my deployment thread?
status = await thread_registry.get_status("deploy_staging_20260125_103045")
# → {"status": "running", "turn_count": 12, "usage": {...}}

# Show me all failed threads today
failed = await thread_registry.query({
    "status": "error", 
    "created_after": "2026-01-25T00:00:00Z"
})

# Pause a runaway thread
await thread_registry.update_status(thread_id, "paused")
```

### Why is it OPTIONAL?

**It's optional because:**

1. **Not all directives need it** - Simple tasks don't need monitoring infrastructure
2. **Alternative monitoring exists** - Transcript files (`.ai/threads/{thread_id}/transcript.jsonl`) provide full execution logs
3. **Permission model** - Only directives with `registry.write` capability can use it
4. **Separation of concerns** - Thread execution is independent from thread monitoring

**Example scenarios:**

**Scenario A: Core directive spawning threads (needs registry)**
```xml
<!-- thread_directive (core) -->
<permissions>
  <execute resource="registry" action="write"/>  ← Has access
  <execute resource="registry" action="read"/>
</permissions>
```
- Can register threads, update status, query state ✅
- Useful for orchestration, monitoring multiple threads

**Scenario B: Simple user directive (no registry)**
```xml
<!-- deploy_staging (user) -->
<permissions>
  <read resource="filesystem" path="src/**"/>
  <execute resource="tool" id="bash"/>
  <!-- NO registry permissions -->
</permissions>
```
- Cannot call `thread_registry` ❌
- Still runs fine on its thread
- Monitoring via transcript file or external tools

### How do permissions work?

**Thread Registry is a regular MCP tool** with capability requirements:

```yaml
# .ai/tools/threads/thread_registry.yaml
tool_id: thread_registry
requires:
  - registry.write  # For register, update_status
  - registry.read   # For get_status, query
```

**Permission flow:**

```
1. thread_directive (core) declares:
   <execute resource="registry" action="write"/>

2. Harness mints token:
   caps: [{cap: "registry.write", scope: {}}, ...]

3. thread_directive can call thread_registry:
   execute(tool, run, thread_registry, {action: "register"})
   → Tool validates token has registry.write ✅

4. Child directive (deploy_staging) gets NEW token:
   caps: [{cap: "fs.read", scope: {path: "src/**"}}, ...]
   → NO registry.write!

5. If deploy_staging tries to call thread_registry:
   execute(tool, run, thread_registry, {action: "get_status"})
   → Tool validates token: MISSING registry.write ❌ DENIED
```

### Why the comment says "OPTIONAL"?

Looking at lines 988-990:
```python
# Note: Thread registry registration is OPTIONAL
# If directive has registry.write capability, it can register itself
# Otherwise, external monitoring tools can query thread state via other means
```

This means:

1. **Harness doesn't force registration** - No automatic calls to `thread_registry.register()` on thread start
2. **Directive decides** - If it has `registry.write`, it can opt-in to registry
3. **Alternative: Transcript files** - Always written to `.ai/threads/{thread_id}/transcript.jsonl`
4. **External monitoring** - Other tools can watch filesystem, logs, etc.

**In practice:**
- `thread_directive` (core) **uses registry** because it needs to coordinate/monitor threads
- `deploy_staging` (user) **doesn't use registry** because it doesn't need that capability
- Both work fine - registry is infrastructure, not a requirement for execution

Does this clarify the design? Thread registry is a **monitoring tool**, not execution infrastructure. Threads run independently whether or not they're registered.