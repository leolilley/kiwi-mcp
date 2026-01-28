# Building Clawdbot with Kiwi MCP: Complete Guide

## Introduction

This document provides a comprehensive guide for implementing a clawdbot-like personal AI assistant using Kiwi MCP's directive-driven, tool-based, and knowledge-centric architecture. Instead of building a monolithic gateway, we leverage Kiwi MCP's unified MCP protocol to create a distributed, composable assistant system.

## Core Philosophy

### Clawdbot's Approach

- **Gateway-centric**: Single WebSocket control plane managing all channels, sessions, and tools
- **Channel-first**: Direct integrations with messaging platforms (WhatsApp, Telegram, Slack, etc.)
- **Tool execution**: Built-in tools for browser, canvas, nodes, cron, etc.
- **Session management**: Per-channel/per-group session isolation
- **Skills platform**: Extensible skill system with registry

### Kiwi MCP's Approach

- **Directive-driven**: Workflows defined as reusable directives (HOW to do things)
- **Tool-based execution**: Tools are executable scripts/APIs (WHAT actually does the work)
- **Knowledge-centric**: Domain knowledge stored as searchable knowledge entries
- **MCP-native**: Built on MCP protocol for universal compatibility
- **Composable**: Items (directives/tools/knowledge) can be discovered, loaded, and executed dynamically

## Architecture Overview

### System Components

```
┌─────────────────────────────────────┐
│     MCP Server (Control Plane)      │
│  - Exposes Kiwi MCP tools          │
│  - Manages connections              │
│  - Routes to directives/tools       │
└──────────────┬──────────────────────┘
               │
       ┌───────┴────────┐
       │               │
┌──────▼──────┐  ┌─────▼──────┐
│ Directives  │  │   Tools    │
│ (Workflows) │  │ (Execution)│
└─────────────┘  └────────────┘
       │               │
       └───────┬───────┘
               │
       ┌───────▼───────┐
       │   Knowledge   │
       │  (Patterns)   │
       └───────────────┘
```

### Component Mapping

| Clawdbot Component | Kiwi MCP Implementation |
| ----------------- | ----------------------- |
| **Control Plane** | WebSocket Gateway      | MCP Server              |
| **Channels**      | Native integrations    | Tools + Directives     |
| **Agent Logic**   | Hardcoded prompts      | Directives             |
| **Tools**         | Built-in handlers      | Kiwi MCP Tools         |
| **Sessions**      | Session model          | Tools + Directives     |
| **Skills**        | Skill registry         | Registry + Directives/Tools/Knowledge |
| **Configuration** | JSON config            | Knowledge entries      |
| **Extensibility** | Code changes           | Add directives/tools/knowledge |
| **Discovery**     | Manual                 | `mcp_kiwi_mcp_search`  |
| **Sharing**       | Git repo               | Registry               |
| **Versioning**    | Git tags               | Built-in versioning    |
| **Integrity**     | N/A                    | Hash validation        |

## Key Advantages

### 1. Composability

- Channels, tools, and workflows are separate, reusable components
- Mix and match directives/tools/knowledge across projects
- No monolithic codebase

### 2. Discoverability

- Search for directives/tools/knowledge via `mcp_kiwi_mcp_search`
- Registry enables sharing across projects/users
- Self-documenting via knowledge entries

### 3. Extensibility

- Add new channels by creating a tool + knowledge entry
- Add new workflows by creating a directive
- No code changes needed for new features

### 4. Testability

- Each tool is independently testable
- Directives can be tested in isolation
- Knowledge entries provide test scenarios

### 5. Versioning & Integrity

- All items have integrity hashes
- Version management built-in
- Registry supports versioned items

## Implementation Structure

### Example Project Structure

```
.ai/
├── tools/
│   ├── channel_telegram.py      # WhatsApp integration tool
│   ├── channel_whatsapp.py      # Telegram integration tool
│   ├── channel_slack.py         # Slack integration tool
│   ├── channel_discord.py       # Discord integration tool
│   ├── session_manager.py       # Session management
│   ├── llm_chat.py              # LLM integration
│   ├── browser_control.py      # Browser automation
│   ├── canvas_render.py         # Canvas operations
│   └── node_commands.py         # Device node commands
├── directives/
│   ├── handle_inbound_message.xml    # Route incoming messages
│   ├── setup_channel.xml             # Configure new channel
│   ├── channel_routing.xml           # Multi-channel routing logic
│   ├── session_manager.xml           # Session lifecycle
│   └── multi_agent_router.xml        # Multi-agent routing
└── knowledge/
    ├── agent_personality.md           # Agent behavior guidelines
    ├── telegram_setup.md             # Telegram setup guide
    ├── whatsapp_setup.md             # WhatsApp setup guide
    ├── session_patterns.md           # Session management patterns
    ├── channel_security.md           # Security guidelines
    └── config_patterns.md            # Configuration patterns
```

## Message Flow Example

### Clawdbot Flow

```
WhatsApp Message → Gateway → Agent Runtime → Tool Execution → Response → WhatsApp
```

### Kiwi MCP Flow

```
WhatsApp Message
  → Tool: channel_whatsapp (receives message)
  → Directive: handle_inbound_message (orchestrates)
    → Directive: session_manager (gets/creates session)
    → Tool: llm_chat (processes with AI)
    → Tool: channel_whatsapp (sends response)
```

**Implementation Components**:

1. **Tool**: `channel_whatsapp.py` - Handles WhatsApp connection, send/receive
2. **Directive**: `handle_inbound_message.xml` - Orchestrates message handling
3. **Tool**: `session_manager.py` - Manages session state
4. **Tool**: `llm_chat.py` - Interfaces with LLM API
5. **Knowledge**: `message_handling_patterns.md` - Best practices

## Skills Platform

### Skill Structure

Skills are composed of three components:

```
Skill: "email_summarizer"
├── .ai/directives/email_summarizer.xml    # Workflow
├── .ai/tools/email_parser.py              # Email parsing tool
└── .ai/knowledge/email_summarizer.md      # Documentation
```

### Skill Discovery

```python
# Search for skills
results = mcp_kiwi_mcp_search(
    item_type="directive",
    query="email summarization",
    source="registry"
)

# Load skill
skill = mcp_kiwi_mcp_load(
    item_type="directive",
    item_id="email_summarizer",
    source="registry"
)

# Install to project
mcp_kiwi_mcp_execute(
    item_type="directive",
    action="load",
    item_id="email_summarizer",
    source="registry",
    destination="project",
    project_path="/path/to/project"
)
```

## Security Model

### Clawdbot Security

- DM pairing for unknown senders
- Sandbox mode for non-main sessions
- Tool allowlists/denylists

### Kiwi MCP Security

- **Integrity verification** via hash validation
- **Permission model** in directives (permissions metadata)
- **Sandboxing** via tool execution isolation
- **Knowledge-based** security patterns stored as entries

**Security Directive Example**:

```xml
<directive name="secure_message_handler">
  <metadata>
    <permissions>
      <read resource="session" path="**/*" />
      <execute resource="channel" action="send" />
      <deny resource="system" action="*" />
    </permissions>
  </metadata>
  ...
</directive>
```

## Configuration Management

### Clawdbot

- JSON config file (`~/.clawdbot/clawdbot.json`)
- Environment variables
- Channel-specific configs

### Kiwi MCP

- **Knowledge entries** for configuration patterns
- **Directives** for config validation/setup
- **Tools** for config management
- **Environment resolution** via runtime/env_resolver

**Config Knowledge Entry**:

```markdown
---
zettel_id: config_patterns
title: Configuration Patterns
entry_type: pattern
---

# Channel Configuration

## Telegram
- botToken: Required
- allowFrom: Array of user IDs
- groups: Group allowlist

## WhatsApp
- credentials: Path to credentials file
- allowFrom: Array of phone numbers
```

## Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Goal**: Basic MCP server with one channel (Telegram) and message handling

**Deliverables**:
1. MCP server exposing Kiwi MCP tools
2. Telegram channel tool (`channel_telegram.py`)
3. Message handler directive (`handle_inbound_message.xml`)
4. Session manager tool (`session_manager.py`)
5. LLM chat tool (`llm_chat.py`)
6. Basic knowledge entries (agent personality, setup guides)

**Success Criteria**:
- Can receive Telegram message
- Process with LLM
- Send response back
- Maintain session state

### Phase 2: Multi-Channel Support (Week 3-4)

**Goal**: Add WhatsApp, Slack, Discord channels

**Deliverables**:
1. WhatsApp channel tool (via Baileys)
2. Slack channel tool (via Bolt)
3. Discord channel tool (via discord.js wrapper)
4. Channel router directive (`channel_router.xml`)
5. Channel-specific knowledge entries

**Success Criteria**:
- All channels can send/receive messages
- Routing works correctly
- Session isolation per channel

### Phase 3: Advanced Features (Week 5-6)

**Goal**: Browser, canvas, nodes, cron, skills platform

**Deliverables**:
1. Browser control tool
2. Canvas rendering tool
3. Node tools (camera, screen, location)
4. Cron scheduler tool
5. Skills discovery and installation
6. Pairing/security system

**Success Criteria**:
- Browser automation works
- Canvas can be rendered
- Nodes can execute device commands
- Cron jobs can be scheduled
- Skills can be discovered and installed

### Phase 4: Companion Apps (Week 7-8)

**Goal**: macOS/iOS/Android node support

**Deliverables**:
1. Node protocol tool
2. Device pairing directive
3. Node command execution
4. Voice wake support (macOS)
5. Talk mode support

**Success Criteria**:
- Devices can pair as nodes
- Node commands execute correctly
- Voice wake works on macOS
- Talk mode provides continuous conversation

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

## Key Questions to Consider

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

## Resources

- **Architecture Details**: `docs/CLAWDBOT_KIWI_IMPLEMENTATION.md`
- **Code Examples**: `docs/CLAWDBOT_KIWI_EXAMPLES.md`
- **Implementation Roadmap**: `docs/CLAWDBOT_KIWI_ROADMAP.md`
- **Kiwi MCP Docs**: `docs/ARCHITECTURE.md`
- **Directive Guide**: `docs/DIRECTIVE_AUTHORING.md`
- **Tool Guide**: `docs/TOOL_IMPLEMENTATION_STATUS.md`

## Conclusion

Kiwi MCP provides a superior foundation for building a clawdbot-like system through:

- **Better architecture**: Composable, extensible, maintainable
- **Better developer experience**: Search, load, execute dynamically
- **Better sharing**: Registry enables community contributions
- **Better testing**: Independent, mockable components

The directive-driven approach means agent behavior is declarative rather than hardcoded, making it easier to customize, version, and share. Instead of building a monolithic gateway, you create a distributed system of composable components that can be discovered, loaded, and executed dynamically.

## Next Steps

1. **Review**: Read the detailed implementation documents
2. **Prototype**: Start with Phase 1 (basic Telegram channel)
3. **Iterate**: Add channels and features incrementally
4. **Share**: Publish components to registry for community use
