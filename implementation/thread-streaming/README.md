# Thread and Streaming Implementation Plan

**Source Document:** `docs/THREAD_AND_STREAMING_ARCHITECTURE.md`  
**Status:** Planning Phase  
**Total Estimated Time:** ~21-26 days

## Overview

This folder contains the complete implementation plan for Thread and Streaming Architecture (Phase 8). The implementation is broken down into **13 phases**, each containing **atomic tasks** that can be completed independently.

## Philosophy

- **Atomic Tasks**: Each task is a single, focused change (~50-200 lines, 1-4 hours)
- **Self-Contained**: Each task file has enough context to implement without reading the entire doc
- **Copy-Paste Ready**: Exact code snippets from the architecture doc included
- **Progressive Complexity**: Start simple (dataclasses), build to complex (integrations)
- **Verification at Every Level**: Task → Phase → Layer

## Dependency Graph

```
8.1 (http streaming) ──┐
                       ├──> 8.2 (LLM endpoints)
8.3 (JSON-RPC) ────────┘
                       ├──> 8.4 (MCP base tools)
                       │
8.1 ───────────────────> 8.5 (thread registry)
                       │
8.5 ───────────────────> 8.7 (intervention) [8.6 skipped]
                       │
8.4, 8.10 ────────────> 8.13 (MCP connector)
```

**Parallelization Opportunities:**

- Phases 8.1-8.2 (streaming) and 8.3-8.4 (MCP primitives) can run in parallel
- Phase 8.5-8.7 (intervention) requires streaming complete (8.6 skipped)

**Critical Path to Annealing:** 8.1 → 8.5 → 8.7 (8.6 skipped)

## Phase Summary

| Phase | Focus                         | Days | Dependencies | Status     |
| ----- | ----------------------------- | ---- | ------------ | ---------- |
| 8.1   | http_client streaming + sinks | 3-4  | None         | 📋         |
| 8.2   | LLM endpoint tools            | 1-2  | 8.1          | 📋         |
| 8.3   | JSON-RPC protocol handling    | 2    | None         | 📋         |
| 8.4   | MCP base tools (stdio + http) | 2    | 8.3          | 📋         |
| 8.5   | Thread registry (SQLite)      | 2-3  | 8.1          | ✅         |
| 8.6   | Help tool extensions          | 2    | 8.5          | ⏭️ Skipped |
| 8.7   | Thread intervention tools     | 3    | 8.5          | 📋         |
| 8.8   | Cleanup: remove kiwi_mcp/mcp/ | 1    | 8.4          | ✅         |
| 8.9   | Thread ID sanitization        | 0.5  | 8.5          | ✅         |
| 8.10  | Capability token system       | 1-2  | 8.5          | ✅         |
| 8.11  | Tool chain error handling     | 1    | 8.1          | ✅         |
| 8.12  | Cost tracking validation      | 1    | None         | 📋         |
| 8.13  | MCP connector pattern         | 1-2  | 8.4, 8.10    | 📋         |

## Execution Strategy

1. **Sequential Phases**: Follow the dependency graph
2. **Parallel Tasks**: Within a phase, tasks without dependencies can run in parallel
3. **Incremental Verification**: Test after each task, not just at phase end
4. **Rollback Points**: After each phase, create a git tag for easy rollback

## Folder Structure

```
implementation/thread-streaming/
├── README.md                    # This file
├── phases/                      # One folder per phase
│   ├── 8.1-http-streaming/
│   │   ├── README.md            # Phase overview
│   │   ├── tasks/               # Atomic implementation tasks
│   │   │   ├── 01-add-stream-config-dataclass.md
│   │   │   ├── 02-add-stream-destination-dataclass.md
│   │   │   └── ...
│   │   └── verification.md      # Phase completion checklist
│   ├── 8.2-llm-endpoints/
│   └── ...
├── shared/                      # Cross-cutting reference docs
│   ├── permission-patterns.md
│   ├── error-handling-patterns.md
│   └── testing-patterns.md
└── appendices/                  # Detailed implementation specs
    ├── A.1-thread-id-handling/
    ├── A.2-permissions/
    └── ...
```

## Key Architectural Principles

1. **Kernel Stays Dumb**: MCP kernel has NO thread logic - it only loads and returns data
2. **Data-Driven Tools**: Everything is a tool with config (except primitives)
3. **Harness IN Thread**: The harness is instantiated BY spawn_thread, lives in the thread
4. **Guidance in AGENTS.md**: Spawning patterns documented in system prompt, not kernel
5. **Permissions via Tokens**: Capability tokens minted by harness, validated by tools

## Naming Conventions

- **safety_harness**: The Safety harness implementation (replaces kiwi_harness naming)
- **base_harness**: Generic base harness (philosophy-agnostic)
- **thread_directive**: Tool for spawning directives on managed threads
- **run_directive**: Directive that provides guidance on directive execution

## Tool Patterns

**Runtime Tools (Python-only):**

- No YAML sidecars
- Metadata at top: `__tool_type__`, `__version__`, `__executor_id__`, `__category__`
- Dependencies: `DEPENDENCIES = [...]` if needed
- Examples: `file_sink.py`, `null_sink.py`, `websocket_sink.py`

**HTTP Tools (YAML configs):**

- Pure YAML configuration files
- Chain to `http_client` primitive
- Examples: `anthropic_messages.yaml`, `anthropic_thread.yaml`

**Tool Discovery:** Runtime tools are discovered via AST parsing of Python files. HTTP tools are discovered via YAML parsing.

## Getting Started

1. Start with Phase 8.1 (no dependencies)
2. Read the phase README.md for context
3. Work through tasks in order (01-, 02-, etc.)
4. Verify each task before moving to the next
5. Complete phase verification before starting next phase

## Recent Completions

### ✅ Phase 8.10: Capability Token System (COMPLETED 2026-01-28)
- CapabilityToken dataclass with Ed25519 signing
- Permission-to-capability conversion system
- Token attenuation for parent-child threads
- Tool YAML `requires` field validation
- 7 capability modules (fs, net, db, git, process, mcp)
- Complete test coverage (28/28 tests passing)
- Integration with thread registry and spawning

**Key Achievement:** Security foundation for thread permissions is now complete and operational.

### ✅ Phase 8.11: Tool Chain Error Handling (COMPLETED 2026-01-28)
- ToolChainError with full execution context
- ValidationError and FailedToolContext for precise diagnostics
- Error wrapping at every execution layer
- LLM-actionable error responses with JSON serialization
- Complete test coverage (19/19 tests passing)
- Integration with executor and config validation

**Key Achievement:** Comprehensive error handling provides clear diagnostics and LLM-actionable responses for any tool chain failures.

## Related Documents

- `docs/THREAD_AND_STREAMING_ARCHITECTURE.md` - Full architecture specification
- `docs/PERMISSION_MODEL.md` - Permission enforcement details
- `docs/SAFETY_HARNESS_ROADMAP.md` - Harness implementation details
- `MCP_DISCOVERY_FLOW.md` - How MCP discovery and integration works
