# Clawdbot Implementation Using Kiwi MCP

## Executive Summary

This document outlines how to implement a clawdbot-like personal AI assistant system using Kiwi MCP's directive-driven, tool-based, and knowledge-centric architecture. Rather than building a monolithic gateway, we leverage Kiwi MCP's unified MCP protocol to create a distributed, composable assistant system.

## Core Philosophy Alignment

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

## Architecture Mapping

### 1. Gateway → MCP Server + Directive Orchestration

**Clawdbot**: Single WebSocket gateway (`ws://127.0.0.1:18789`) managing all connections

**Kiwi MCP Implementation**:

- **MCP Server** as the control plane (replaces WebSocket gateway)
- **Directives** orchestrate multi-step workflows (replaces hardcoded agent logic)
- **Tools** execute actual operations (replaces built-in tool handlers)
- **Knowledge** stores channel configs, session patterns, best practices

**Implementation Strategy**:

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
```

### 2. Channels → Tools + Directives

**Clawdbot**: Native channel integrations (WhatsApp via Baileys, Telegram via grammY, etc.)

**Kiwi MCP Implementation**:

- Each channel becomes a **Tool** (executable script/API wrapper)
- Channel routing logic becomes a **Directive** (workflow for message handling)
- Channel configurations stored as **Knowledge** entries

**Example Structure**:

```
.ai/
├── tools/
│   ├── channel_whatsapp.py      # WhatsApp integration tool
│   ├── channel_telegram.py      # Telegram integration tool
│   ├── channel_slack.py         # Slack integration tool
│   └── channel_discord.py        # Discord integration tool
├── directives/
│   ├── handle_inbound_message.xml    # Route incoming messages
│   ├── setup_channel.xml             # Configure new channel
│   └── channel_routing.xml           # Multi-channel routing logic
└── knowledge/
    ├── whatsapp_setup.md             # WhatsApp setup guide
    ├── telegram_best_practices.md    # Telegram patterns
    └── channel_security.md           # Security guidelines
```

### 3. Agent Runtime → Directive Execution

**Clawdbot**: Pi agent runtime in RPC mode with tool streaming

**Kiwi MCP Implementation**:

- **Directives** define agent behavior (replaces hardcoded agent prompts)
- **Tool execution** via Kiwi MCP's execute tool
- **Streaming** handled by MCP's native streaming capabilities
- **Context management** via Knowledge entries and directive state

**Agent Directive Example**:

```xml
<directive name="personal_assistant" version="1.0.0">
  <metadata>
    <description>Personal AI assistant that handles messages across channels</description>
    <category>agent</category>
  </metadata>

  <process>
    <step name="receive_message">
      <description>Receive message from any channel</description>
      <action>
        Use tool: channel_receive to get incoming message
        Store in session context
      </action>
    </step>

    <step name="route_to_session">
      <description>Route to appropriate session</description>
      <action>
        Use directive: session_router with message context
        Determine session_id based on channel/peer/group
      </action>
    </step>

    <step name="process_with_agent">
      <description>Process message with AI agent</description>
      <action>
        Use tool: llm_chat with session context
        Stream response back to channel
      </action>
    </step>
  </process>
</directive>
```

### 4. Session Management → Knowledge + Directives

**Clawdbot**: Session model with `main` for direct chats, group isolation, activation modes

**Kiwi MCP Implementation**:

- **Knowledge entries** store session patterns and configurations
- **Directives** handle session lifecycle (create, update, prune)
- **Tools** manage session state (read/write session data)

**Session Directive**:

```xml
<directive name="session_manager" version="1.0.0">
  <process>
    <step name="get_or_create_session">
      <action>
        Use tool: session_get with session_id
        If not found, use tool: session_create
        Load session context from knowledge: session_patterns
      </action>
    </step>

    <step name="update_session">
      <action>
        Use tool: session_update with new messages
        Apply compaction if needed (directive: session_compact)
      </action>
    </step>
  </process>
</directive>
```

### 5. Tools → Kiwi MCP Tools

**Clawdbot**: Built-in tools (browser, canvas, nodes, cron, sessions, Discord/Slack actions)

**Kiwi MCP Implementation**:

- Each clawdbot tool becomes a **Kiwi MCP Tool** (Python script or API wrapper)
- Tool discovery via `mcp_kiwi_mcp_search` (search for tools)
- Tool execution via `mcp_kiwi_mcp_execute` (run tool with parameters)

**Tool Examples**:

```
.ai/tools/
├── browser_control.py        # Browser automation
├── canvas_render.py          # Canvas operations
├── node_camera.py            # Camera access
├── node_screen.py            # Screen recording
├── cron_scheduler.py         # Cron job management
└── discord_actions.py        # Discord API wrapper
```

### 6. Skills Platform → Knowledge Registry + Directives

**Clawdbot**: Skills with install gating + UI (bundled, managed, workspace skills)

**Kiwi MCP Implementation**:

- **Skills** are **Directives** (workflows) + **Tools** (execution) + **Knowledge** (documentation)
- **Registry** is the Kiwi MCP registry (Supabase or local)
- **Discovery** via `mcp_kiwi_mcp_search` with `source=registry`
- **Installation** via `mcp_kiwi_mcp_execute` with `action=load` from registry

**Skill Structure**:

```
Skill: "email_summarizer"
├── .ai/directives/email_summarizer.xml    # Workflow
├── .ai/tools/email_parser.py              # Email parsing tool
└── .ai/knowledge/email_summarizer.md      # Documentation
```

### 7. Multi-Agent Routing → Directive Orchestration

**Clawdbot**: Route inbound channels/accounts/peers to isolated agents (workspaces + per-agent sessions)

**Kiwi MCP Implementation**:

- **Routing logic** becomes a **Directive** (multi-step routing workflow)
- **Agent definitions** stored as **Knowledge** entries
- **Workspace isolation** via project_path in tool execution

**Routing Directive**:

```xml
<directive name="multi_agent_router" version="1.0.0">
  <process>
    <step name="identify_agent">
      <action>
        Load knowledge: agent_routing_rules
        Match channel/peer/account to agent workspace
        Return agent_id and workspace_path
      </action>
    </step>

    <step name="route_to_agent">
      <action>
        Execute directive: personal_assistant
        With project_path = agent workspace
        Pass message context
      </action>
    </step>
  </process>
</directive>
```

## Implementation Phases

### Phase 1: Core MCP Server + Basic Channel

**Goal**: Replace gateway with MCP server, implement one channel (e.g., Telegram)

**Components**:

1. **MCP Server** exposing Kiwi MCP tools
2. **Telegram Tool** (`channel_telegram.py`)
3. **Message Handler Directive** (`handle_message.xml`)
4. **Session Tool** (`session_manager.py`)
5. **LLM Chat Tool** (`llm_chat.py`)

**Knowledge Entries**:

- `telegram_setup.md` - Setup instructions
- `session_patterns.md` - Session management patterns
- `agent_personality.md` - Agent behavior guidelines

### Phase 2: Multi-Channel Support

**Goal**: Add WhatsApp, Slack, Discord channels

**Components**:

1. **Channel Tools** for each platform
2. **Channel Router Directive** (`channel_routing.xml`)
3. **Channel Config Knowledge** entries

### Phase 3: Advanced Features

**Goal**: Browser, canvas, nodes, cron, skills

**Components**:

1. **Browser Tool** (`browser_control.py`)
2. **Canvas Tool** (`canvas_render.py`)
3. **Node Tools** (camera, screen, location)
4. **Cron Tool** (`cron_scheduler.py`)
5. **Skills Platform** (directives + tools + knowledge)

### Phase 4: Companion Apps

**Goal**: macOS/iOS/Android nodes

**Components**:

1. **Node Protocol Tool** (`node_connector.py`)
2. **Device Pairing Directive** (`device_pairing.xml`)
3. **Node Command Tools** (camera, screen, notifications)

## Key Advantages of Kiwi MCP Approach

### 1. **Composability**

- Channels, tools, and workflows are separate, reusable components
- Mix and match directives/tools/knowledge across projects
- No monolithic codebase

### 2. **Discoverability**

- Search for directives/tools/knowledge via `mcp_kiwi_mcp_search`
- Registry enables sharing across projects/users
- Self-documenting via knowledge entries

### 3. **Extensibility**

- Add new channels by creating a tool + knowledge entry
- Add new workflows by creating a directive
- No code changes needed for new features

### 4. **Testability**

- Each tool is independently testable
- Directives can be tested in isolation
- Knowledge entries provide test scenarios

### 5. **Versioning & Integrity**

- All items have integrity hashes
- Version management built-in
- Registry supports versioned items

## Migration Path from Clawdbot

### Step 1: Extract Channel Logic

- Convert each channel integration to a Kiwi MCP Tool
- Document channel setup as Knowledge entries

### Step 2: Extract Agent Logic

- Convert agent prompts/behavior to Directives
- Store agent personality in Knowledge entries

### Step 3: Extract Tool Logic

- Convert built-in tools to Kiwi MCP Tools
- Document tool usage in Knowledge entries

### Step 4: Extract Session Logic

- Create session management Tools
- Create session lifecycle Directives
- Document session patterns in Knowledge

### Step 5: Extract Skills

- Convert skills to Directive + Tool + Knowledge bundles
- Publish to registry for sharing

## Example: Complete Message Flow

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

**Implementation**:

1. **Tool**: `channel_whatsapp.py` - Handles WhatsApp connection, send/receive
2. **Directive**: `handle_inbound_message.xml` - Orchestrates message handling
3. **Tool**: `session_manager.py` - Manages session state
4. **Tool**: `llm_chat.py` - Interfaces with LLM API
5. **Knowledge**: `message_handling_patterns.md` - Best practices

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

## Skills Platform

### Clawdbot Skills

- Bundled skills (in repo)
- Managed skills (from registry)
- Workspace skills (user-created)

### Kiwi MCP Skills

- **Directive** = Skill workflow
- **Tool** = Skill execution
- **Knowledge** = Skill documentation
- **Registry** = Skill sharing

**Skill Discovery**:

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

## Comparison Table

| Feature           | Clawdbot            | Kiwi MCP Implementation               |
| ----------------- | ------------------- | ------------------------------------- |
| **Control Plane** | WebSocket Gateway   | MCP Server                            |
| **Channels**      | Native integrations | Tools + Directives                    |
| **Agent Logic**   | Hardcoded prompts   | Directives                            |
| **Tools**         | Built-in handlers   | Kiwi MCP Tools                        |
| **Sessions**      | Session model       | Tools + Directives                    |
| **Skills**        | Skill registry      | Registry + Directives/Tools/Knowledge |
| **Configuration** | JSON config         | Knowledge entries                     |
| **Extensibility** | Code changes        | Add directives/tools/knowledge        |
| **Discovery**     | Manual              | `mcp_kiwi_mcp_search`                 |
| **Sharing**       | Git repo            | Registry                              |
| **Versioning**    | Git tags            | Built-in versioning                   |
| **Integrity**     | N/A                 | Hash validation                       |

## Next Steps

1. **Prototype**: Build Phase 1 (MCP server + Telegram channel)
2. **Validate**: Test directive-driven message handling
3. **Expand**: Add more channels (Phase 2)
4. **Enhance**: Add advanced features (Phase 3)
5. **Distribute**: Build companion apps (Phase 4)

## Conclusion

Kiwi MCP provides a more composable, extensible, and maintainable foundation for building a clawdbot-like system. By leveraging directives for workflows, tools for execution, and knowledge for patterns, we create a system that is:

- **More flexible**: Easy to add new channels, tools, workflows
- **More maintainable**: Clear separation of concerns
- **More shareable**: Registry enables community contributions
- **More testable**: Each component is independently testable
- **More discoverable**: Search and load items dynamically

The directive-driven approach means the "agent" behavior is defined declaratively rather than hardcoded, making it easier to customize, version, and share agent personalities and workflows.
