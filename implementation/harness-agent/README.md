# Harness Agent Implementation Spec

**Status:** Ready to Implement  
**Depends On:** Safety Harness (completed), Parser Updates (completed)

---

## Overview

Implement a data-driven agent loop that:
1. Spawns an LLM conversation with tool access
2. Wraps execution in SafetyHarness for cost/limit enforcement
3. Uses directive metadata for permissions, limits, model selection
4. Evaluates hooks at checkpoints (before/after tool calls, on errors)

---

## Philosophy Alignment

### Data-Driven Principles

| Principle | Implementation |
|-----------|----------------|
| **Tools are data** | Tool definitions come from `.ai/tools/` YAML files, not hardcoded |
| **Permissions are data** | Agent only exposes tools that directive has permission for |
| **Limits are data** | From `<limits>` tag in directive metadata |
| **Models are data** | From `<model>` tag - tier, model_id, fallback_id |
| **Hooks are data** | Expression-based from `<hooks>` in metadata |

### Kernel vs Tool Separation

- **Kernel** (`kiwi_mcp/`): Primitives only - subprocess, http_client
- **Harness Agent** (`.ai/tools/threads/`): User-space tool, NOT a kernel primitive
- **Tool Registry**: Agent discovers available tools from `.ai/tools/`

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Directive Metadata                            │
│  <model tier="reasoning" model_id="claude-sonnet-4" />          │
│  <limits><turns>10</turns><tokens>5000</tokens></limits>        │
│  <permissions>                                                   │
│    <execute resource="tool" action="read_file" />               │
│    <execute resource="tool" action="write_file" />              │
│    <write resource="filesystem" path=".ai/tmp/*" />             │
│  </permissions>                                                  │
│  <hooks>                                                         │
│    <hook>                                                        │
│      <when>event.code == "permission_denied"</when>             │
│      <directive>request_elevated_permissions</directive>        │
│    </hook>                                                       │
│  </hooks>                                                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     HarnessAgent                                 │
│                                                                  │
│  1. Load directive metadata                                      │
│  2. Filter available tools by permissions                        │
│  3. Build LLM tool definitions from filtered tools               │
│  4. Create SafetyHarness with limits/hooks                       │
│  5. Run agent loop:                                              │
│     a. checkpoint_before_step()                                  │
│     b. Call LLM with conversation + tools                        │
│     c. harness.update_cost_after_turn(response)                  │
│     d. If tool_use: check permission → execute → loop            │
│     e. If text: checkpoint_after_step() → done or continue       │
│     f. On error: checkpoint_on_error() → handle hook or fail     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Tool Execution Layer                           │
│                                                                  │
│  Tools discovered from:                                          │
│  - .ai/tools/**/*.yaml (project tools)                          │
│  - ~/.ai/tools/**/*.yaml (user tools)                           │
│  - Built-in filesystem tools (read_file, write_file, list_files)│
│                                                                  │
│  Each tool call:                                                 │
│  1. Check permission against directive's <permissions>           │
│  2. If denied → emit permission_denied event → evaluate hooks    │
│  3. If granted → execute via primitive executor                  │
│  4. Return result to LLM                                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Permission Model Integration

### Current Permission Format

From directive `<permissions>` tag (parsed as list):

```python
[
    {"tag": "read", "attrs": {"resource": "filesystem", "path": ".ai/*"}},
    {"tag": "write", "attrs": {"resource": "filesystem", "path": ".ai/tmp/*"}},
    {"tag": "execute", "attrs": {"resource": "tool", "action": "read_file"}},
    {"tag": "execute", "attrs": {"resource": "shell", "action": "*"}}
]
```

### Permission Checking Logic

```python
def check_permission(permissions: List[Dict], resource: str, action: str, path: str = None) -> bool:
    """
    Check if an action is permitted.
    
    Args:
        permissions: List from directive metadata
        resource: "filesystem", "tool", "shell", "kiwi-mcp"
        action: "read", "write", "execute", tool name, etc.
        path: Optional path for filesystem operations
    
    Returns:
        True if permitted, False otherwise
    """
    for perm in permissions:
        tag = perm["tag"]  # read, write, execute
        attrs = perm["attrs"]
        
        if attrs.get("resource") != resource:
            continue
        
        # Check action match
        perm_action = attrs.get("action", attrs.get("path", "*"))
        if perm_action == "*" or perm_action == action:
            # For filesystem, also check path pattern
            if resource == "filesystem" and path:
                if _path_matches(path, attrs.get("path", "*")):
                    return True
            else:
                return True
    
    return False
```

---

## Tool Discovery

### Built-in Tools (Always Available, Subject to Permissions)

```yaml
# Hardcoded tool definitions for filesystem operations
builtin_tools:
  read_file:
    resource: filesystem
    action: read
    description: "Read contents of a file"
    input_schema:
      path: {type: string, required: true}
  
  write_file:
    resource: filesystem
    action: write
    description: "Write content to a file"
    input_schema:
      path: {type: string, required: true}
      content: {type: string, required: true}
  
  list_files:
    resource: filesystem
    action: read
    description: "List files in a directory"
    input_schema:
      path: {type: string, default: "."}
  
  run_command:
    resource: shell
    action: execute
    description: "Run a shell command"
    input_schema:
      command: {type: string, required: true}
```

### Project Tools (Discovered from .ai/tools/)

```python
def discover_tools(project_path: Path) -> List[Dict]:
    """
    Discover tools from project and user space.
    
    Returns list of tool definitions with:
    - name: tool identifier
    - description: for LLM
    - input_schema: JSON schema for inputs
    - executor: how to run (python_runtime, subprocess, http, etc.)
    - requires: list of capabilities needed
    """
    tools = []
    
    # Project tools
    for yaml_file in (project_path / ".ai" / "tools").rglob("*.yaml"):
        tool = load_tool_yaml(yaml_file)
        tools.append(tool)
    
    # User tools
    for yaml_file in (Path.home() / ".ai" / "tools").rglob("*.yaml"):
        tool = load_tool_yaml(yaml_file)
        tools.append(tool)
    
    return tools
```

### Filter Tools by Permissions

```python
def filter_tools_by_permissions(tools: List[Dict], permissions: List[Dict]) -> List[Dict]:
    """
    Filter tools to only those the directive has permission to use.
    """
    allowed = []
    for tool in tools:
        # Check if directive has execute permission for this tool
        required_caps = tool.get("requires", [])
        
        # If tool has no requirements, check execute.tool permission
        if not required_caps:
            if check_permission(permissions, "tool", tool["name"]):
                allowed.append(tool)
            continue
        
        # Check all required capabilities
        all_granted = True
        for cap in required_caps:
            resource, action = cap.split(".", 1) if "." in cap else ("tool", cap)
            if not check_permission(permissions, resource, action):
                all_granted = False
                break
        
        if all_granted:
            allowed.append(tool)
    
    return allowed
```

---

## Agent Loop Implementation

### File: `.ai/tools/threads/harness_agent.py`

```python
async def run_agent(
    directive: Dict,
    inputs: Dict,
    project_path: Path,
) -> Dict:
    """
    Run agent loop with harness enforcement.
    """
    # 1. Create harness
    harness = SafetyHarness(
        project_path=project_path,
        limits=directive.get("limits", {}),
        hooks=directive.get("hooks", []),
        directive_name=directive["name"],
        directive_inputs=inputs
    )
    
    # 2. Get permitted tools
    all_tools = discover_tools(project_path) + BUILTIN_TOOLS
    permissions = directive.get("permissions", [])
    allowed_tools = filter_tools_by_permissions(all_tools, permissions)
    
    # 3. Build LLM tool definitions
    llm_tools = [to_anthropic_tool(t) for t in allowed_tools]
    
    # 4. Initialize conversation
    model_id = directive.get("model", {}).get("model_id", "claude-sonnet-4-20250514")
    system_prompt = build_system_prompt(directive, inputs)
    messages = [{"role": "user", "content": "Execute the directive now."}]
    
    # 5. Agent loop
    while True:
        # Check limits before LLM call
        checkpoint = harness.checkpoint_before_step("llm_call")
        if checkpoint.context and "hook_directive" in checkpoint.context:
            return await handle_hook(checkpoint, harness)
        
        # Call LLM
        response = await call_llm(model_id, system_prompt, messages, llm_tools)
        
        # Update cost
        harness.update_cost_after_turn(response.usage, model_id)
        
        # Process response
        for block in response.content:
            if block.type == "tool_use":
                # Check permission for this specific call
                tool_name = block.name
                tool_input = block.input
                
                if not is_tool_call_permitted(tool_name, tool_input, permissions):
                    # Emit permission denied event
                    result = harness.checkpoint_on_error(
                        "permission_denied",
                        {"tool": tool_name, "input": tool_input}
                    )
                    if result.context and "hook_directive" in result.context:
                        return await handle_hook(result, harness)
                    return {"status": "failed", "error": "Permission denied"}
                
                # Execute tool
                tool_result = await execute_tool(tool_name, tool_input, project_path)
                
                # Add to conversation
                messages.append({"role": "assistant", "content": response.content})
                messages.append({
                    "role": "user",
                    "content": [{"type": "tool_result", "tool_use_id": block.id, "content": tool_result}]
                })
                
            elif block.type == "text":
                # Check if done
                if is_complete(block.text):
                    return {
                        "status": "success",
                        "output": block.text,
                        "cost": harness.cost.to_dict()
                    }
        
        # Continue loop for next turn
```

---

## LLM Provider Abstraction

### Data-Driven Provider Selection

```yaml
# .ai/config/llm_providers.yaml
providers:
  anthropic:
    executor_id: anthropic_messages
    env_var: ANTHROPIC_API_KEY
    models:
      - claude-sonnet-4-20250514
      - claude-3-5-sonnet-20241022
      - claude-3-haiku-20240307
  
  openai:
    executor_id: openai_chat
    env_var: OPENAI_API_KEY
    models:
      - gpt-4o
      - gpt-4o-mini

# Model tier mapping (user-defined)
tiers:
  fast:
    preferred: claude-3-haiku-20240307
    fallback: gpt-4o-mini
  reasoning:
    preferred: claude-sonnet-4-20250514
    fallback: gpt-4o
```

### Provider Resolution

```python
def resolve_model(model_config: Dict, providers_config: Dict) -> Tuple[str, str]:
    """
    Resolve model tier/id to concrete model and provider.
    
    Args:
        model_config: From directive <model> tag
        providers_config: From .ai/config/llm_providers.yaml
    
    Returns:
        (model_id, provider_name)
    """
    # If explicit model_id, use it
    if model_config.get("model_id"):
        model_id = model_config["model_id"]
        provider = find_provider_for_model(model_id, providers_config)
        return model_id, provider
    
    # Resolve from tier
    tier = model_config.get("tier", "reasoning")
    tier_config = providers_config["tiers"].get(tier, {})
    
    preferred = tier_config.get("preferred")
    fallback = model_config.get("fallback_id") or tier_config.get("fallback")
    
    # Check which provider is available
    if is_provider_available(preferred, providers_config):
        return preferred, find_provider_for_model(preferred, providers_config)
    elif fallback and is_provider_available(fallback, providers_config):
        return fallback, find_provider_for_model(fallback, providers_config)
    else:
        raise RuntimeError(f"No available model for tier {tier}")
```

---

## File Structure

```
.ai/tools/threads/
├── harness_agent.py          # NEW: Agent loop implementation
├── harness_agent.yaml        # NEW: Tool sidecar
├── permission_checker.py     # NEW: Permission checking logic
├── tool_discovery.py         # NEW: Tool discovery from .ai/tools/
├── llm_providers.py          # NEW: Provider abstraction
├── safety_harness.py         # EXISTING: Cost/limit enforcement
├── expression_evaluator.py   # EXISTING: Hook expression eval
├── thread_directive.py       # UPDATE: Wire to harness_agent
└── ...

.ai/config/
├── llm_providers.yaml        # NEW: Provider/model configuration
└── ...
```

---

## Tasks

### Phase 1: Permission Checker
- [ ] Implement `permission_checker.py`
- [ ] Handle filesystem path patterns (glob matching)
- [ ] Handle tool execution permissions
- [ ] Handle shell command permissions
- [ ] Add tests

### Phase 2: Tool Discovery
- [ ] Implement `tool_discovery.py`
- [ ] Load tool definitions from YAML files
- [ ] Filter by permissions
- [ ] Convert to LLM-compatible format (Anthropic/OpenAI)
- [ ] Add tests

### Phase 3: LLM Provider Abstraction
- [ ] Create `.ai/config/llm_providers.yaml`
- [ ] Implement `llm_providers.py`
- [ ] Support Anthropic Messages API
- [ ] Support OpenAI Chat API
- [ ] Tier-based model selection
- [ ] Add tests

### Phase 4: Agent Loop
- [ ] Implement `harness_agent.py`
- [ ] Integrate SafetyHarness checkpoints
- [ ] Tool execution with permission checks
- [ ] Hook handling for errors/limits
- [ ] Conversation management
- [ ] Add tests

### Phase 5: Integration
- [ ] Update `thread_directive.py` to use harness_agent
- [ ] End-to-end test with real LLM
- [ ] Test permission denied → hook flow
- [ ] Test limit exceeded → hook flow

---

## Success Criteria

- [ ] Agent can execute directives with file read/write
- [ ] Permissions are enforced (denied tools trigger hooks)
- [ ] Limits are enforced (turns/tokens/spend tracked)
- [ ] Hooks fire correctly on events
- [ ] Multiple LLM providers work via config
- [ ] All tools are data-driven (no hardcoded tool lists)
