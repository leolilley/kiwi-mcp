# Load vs Run: Response Design

The `load` and `run` actions serve different purposes and return different response structures optimized for their use cases.

## Load: Full Inspection

Use `load` when you need to understand an item's complete structure before deciding what to do.

**Use cases:**
- Inspecting a directive before running it
- Reviewing a script's parameters and dependencies
- Copying items between locations (project ↔ user ↔ registry)
- Debugging or understanding how something works

**Returns:** Full metadata, raw content, parsed structure, permissions, paths, etc.

### Directive Load Response
```json
{
  "name": "directive_name",
  "version": "1.0.0",
  "description": "...",
  "content": "# Full markdown content...",
  "parsed": { /* complete XML structure */ },
  "permissions": [{"tag": "execute", "attrs": {...}}],
  "source": "project",
  "path": "/path/to/file.md",
  "mode": "read_only"
}
```

### Knowledge Load Response
```json
{
  "zettel_id": "001-topic",
  "title": "Topic Title",
  "content": "Full markdown content...",
  "entry_type": "learning",
  "category": "patterns",
  "tags": ["tag1", "tag2"],
  "source": "project",
  "path": "/path/to/file.md",
  "mode": "read_only"
}
```

## Run: Execution Context

Use `run` when you're ready to execute and need just the actionable information.

**Use cases:**
- Executing a directive (following its process steps)
- Using knowledge to inform decisions
- Running a script with parameters

**Returns:** Only what's needed for execution, with structure optimized for immediate use.

### Directive Run Response
```json
{
  "status": "ready",
  "name": "directive_name",
  "description": "Brief description",
  "inputs": [
    {"name": "param1", "type": "string", "required": true, "description": "..."}
  ],
  "process": [
    {"name": "step_1", "description": "...", "action": "What to do"}
  ],
  "provided_inputs": {"param1": "value"},
  "instructions": "Follow each process step in order..."
}
```

### Knowledge Run Response
```json
{
  "status": "ready",
  "title": "Topic Title",
  "content": "The knowledge content...",
  "instructions": "Use this knowledge to inform your decisions."
}
```

## Summary

| Aspect | Load | Run |
|--------|------|-----|
| Purpose | Inspection / Copy | Execution |
| Response size | Full | Minimal |
| Includes metadata | Yes | No |
| Includes paths | Yes | No |
| Includes raw content | Yes | No (directives) |
| Process steps | In parsed structure | Extracted array |

## When to Use Each

```
"What does this directive do?" → load
"Run the build workflow" → run

"Show me the knowledge entry" → load
"Use this knowledge for the task" → run

"Copy directive to user space" → load with destination
"Inspect before running" → load
```
