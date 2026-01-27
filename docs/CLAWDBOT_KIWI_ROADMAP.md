# Clawdbot Kiwi MCP Implementation Roadmap

## Overview

This roadmap outlines how to build a clawdbot-like personal AI assistant using Kiwi MCP's directive-driven, tool-based, and knowledge-centric architecture.

## Core Value Proposition

**Clawdbot**: Monolithic gateway with hardcoded integrations
**Kiwi MCP Approach**: Composable system where channels, tools, and workflows are discoverable, reusable components

## Architecture Principles

### 1. Directive-Driven Workflows
- **What**: XML directives define HOW to accomplish tasks
- **Why**: Reusable, versioned, shareable workflows
- **Example**: `handle_inbound_message.xml` orchestrates message processing

### 2. Tool-Based Execution
- **What**: Python scripts/APIs that DO the actual work
- **Why**: Independent, testable, composable execution units
- **Example**: `channel_telegram.py` handles Telegram integration

### 3. Knowledge-Centric Patterns
- **What**: Markdown entries storing domain knowledge, patterns, configs
- **Why**: Searchable, versioned, shareable documentation
- **Example**: `agent_personality.md` defines assistant behavior

### 4. MCP-Native Protocol
- **What**: Built on MCP protocol for universal compatibility
- **Why**: Works with any MCP-compatible client
- **Example**: Expose all functionality via `mcp_kiwi_mcp_*` tools

## Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Goal**: Basic MCP server with one channel (Telegram) and message handling

**Deliverables**:
1. ✅ MCP server exposing Kiwi MCP tools
2. ✅ Telegram channel tool (`channel_telegram.py`)
3. ✅ Message handler directive (`handle_inbound_message.xml`)
4. ✅ Session manager tool (`session_manager.py`)
5. ✅ LLM chat tool (`llm_chat.py`)
6. ✅ Basic knowledge entries (agent personality, setup guides)

**Success Criteria**:
- Can receive Telegram message
- Process with LLM
- Send response back
- Maintain session state

**Files to Create**:
```
.ai/
├── tools/
│   ├── channel_telegram.py
│   ├── session_manager.py
│   └── llm_chat.py
├── directives/
│   └── handle_inbound_message.xml
└── knowledge/
    ├── agent_personality.md
    └── telegram_setup.md
```

### Phase 2: Multi-Channel Support (Week 3-4)

**Goal**: Add WhatsApp, Slack, Discord channels

**Deliverables**:
1. ✅ WhatsApp channel tool (via Baileys)
2. ✅ Slack channel tool (via Bolt)
3. ✅ Discord channel tool (via discord.js wrapper)
4. ✅ Channel router directive (`channel_router.xml`)
5. ✅ Channel-specific knowledge entries

**Success Criteria**:
- All channels can send/receive messages
- Routing works correctly
- Session isolation per channel

**Files to Create**:
```
.ai/tools/
├── channel_whatsapp.py
├── channel_slack.py
└── channel_discord.py

.ai/directives/
└── channel_router.xml

.ai/knowledge/
├── whatsapp_setup.md
├── slack_setup.md
└── discord_setup.md
```

### Phase 3: Advanced Features (Week 5-6)

**Goal**: Browser, canvas, nodes, cron, skills platform

**Deliverables**:
1. ✅ Browser control tool
2. ✅ Canvas rendering tool
3. ✅ Node tools (camera, screen, location)
4. ✅ Cron scheduler tool
5. ✅ Skills discovery and installation
6. ✅ Pairing/security system

**Success Criteria**:
- Browser automation works
- Canvas can be rendered
- Nodes can execute device commands
- Cron jobs can be scheduled
- Skills can be discovered and installed

**Files to Create**:
```
.ai/tools/
├── browser_control.py
├── canvas_render.py
├── node_camera.py
├── node_screen.py
├── node_location.py
└── cron_scheduler.py

.ai/directives/
├── browser_automation.xml
├── canvas_workflow.xml
└── skill_installer.xml

.ai/knowledge/
├── browser_automation_patterns.md
├── canvas_usage.md
└── skills_platform.md
```

### Phase 4: Companion Apps (Week 7-8)

**Goal**: macOS/iOS/Android node support

**Deliverables**:
1. ✅ Node protocol tool
2. ✅ Device pairing directive
3. ✅ Node command execution
4. ✅ Voice wake support (macOS)
5. ✅ Talk mode support

**Success Criteria**:
- Devices can pair as nodes
- Node commands execute correctly
- Voice wake works on macOS
- Talk mode provides continuous conversation

**Files to Create**:
```
.ai/tools/
├── node_connector.py
└── node_commands.py

.ai/directives/
├── device_pairing.xml
└── node_command_handler.xml

.ai/knowledge/
├── node_protocol.md
└── device_pairing_guide.md
```

## Component Mapping

| Clawdbot Component | Kiwi MCP Implementation |
|-------------------|------------------------|
| Gateway WebSocket | MCP Server |
| Channel Integrations | Tools (`channel_*.py`) |
| Agent Runtime | Directives (`*_handler.xml`) |
| Session Model | Tool (`session_manager.py`) + Knowledge |
| Built-in Tools | Tools (`*.py`) |
| Skills Platform | Registry + Directives/Tools/Knowledge |
| Configuration | Knowledge entries |
| Multi-agent Routing | Directive (`channel_router.xml`) |

## Key Advantages

### 1. Composability
- Mix and match components
- Reuse across projects
- No monolithic dependencies

### 2. Discoverability
- Search via `mcp_kiwi_mcp_search`
- Load dynamically
- Self-documenting

### 3. Extensibility
- Add channels by creating tool + knowledge
- Add workflows by creating directive
- No code changes needed

### 4. Shareability
- Publish to registry
- Version control built-in
- Community contributions

### 5. Testability
- Each component independently testable
- Mock-friendly interfaces
- Clear input/output contracts

## Migration Strategy

### From Clawdbot to Kiwi MCP

1. **Extract Channel Logic**
   - Convert each channel to a tool
   - Document as knowledge entry

2. **Extract Agent Logic**
   - Convert prompts to directives
   - Store personality in knowledge

3. **Extract Tool Logic**
   - Convert built-in tools to Kiwi tools
   - Document usage in knowledge

4. **Extract Session Logic**
   - Create session management tools
   - Create session lifecycle directives

5. **Extract Skills**
   - Convert to directive + tool + knowledge bundles
   - Publish to registry

## Example Workflow

### Message Flow

```
1. Telegram message arrives
   ↓
2. Tool: channel_telegram receives message
   ↓
3. Directive: handle_inbound_message orchestrates
   ↓
4. Tool: session_manager gets/creates session
   ↓
5. Tool: llm_chat processes with AI
   ↓
6. Tool: channel_telegram sends response
   ↓
7. Tool: session_manager updates session
```

### Skill Installation Flow

```
1. User: "install email summarizer skill"
   ↓
2. Directive: skill_installer orchestrates
   ↓
3. Tool: registry_search finds skill
   ↓
4. Tool: registry_load downloads skill
   ↓
5. Tool: skill_validator validates
   ↓
6. Knowledge: skill_documentation stored
   ↓
7. Tool: skill_activator enables skill
```

## Next Steps

1. **Review**: Read `CLAWDBOT_KIWI_IMPLEMENTATION.md` for architecture details
2. **Examples**: Review `CLAWDBOT_KIWI_EXAMPLES.md` for code examples
3. **Prototype**: Start with Phase 1 (basic Telegram channel)
4. **Iterate**: Add channels and features incrementally
5. **Share**: Publish components to registry for community use

## Resources

- **Architecture**: `docs/CLAWDBOT_KIWI_IMPLEMENTATION.md`
- **Examples**: `docs/CLAWDBOT_KIWI_EXAMPLES.md`
- **Kiwi MCP Docs**: `docs/ARCHITECTURE.md`
- **Directive Guide**: `docs/DIRECTIVE_AUTHORING.md`
- **Tool Guide**: `docs/TOOL_IMPLEMENTATION_STATUS.md`

## Questions to Consider

1. **Event System**: How to handle real-time events (message arrival)?
   - Option A: MCP server with event streaming
   - Option B: Separate event bus + MCP integration
   - Option C: Polling-based approach

2. **State Management**: How to maintain state across tool calls?
   - Option A: Session files (current approach)
   - Option B: In-memory state with persistence
   - Option C: External state store (Redis, etc.)

3. **Streaming**: How to stream LLM responses?
   - Option A: MCP native streaming
   - Option B: WebSocket for streaming
   - Option C: Server-sent events

4. **Multi-tenancy**: How to support multiple users/workspaces?
   - Option A: Separate project_path per user
   - Option B: Workspace isolation in single project
   - Option C: Multi-project MCP server

## Conclusion

Kiwi MCP provides a superior foundation for building a clawdbot-like system through:

- **Better architecture**: Composable, extensible, maintainable
- **Better developer experience**: Search, load, execute dynamically
- **Better sharing**: Registry enables community contributions
- **Better testing**: Independent, mockable components

The directive-driven approach means agent behavior is declarative rather than hardcoded, making it easier to customize, version, and share.
