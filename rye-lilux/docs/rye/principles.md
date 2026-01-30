**Source:** RYE principles from kiwi-mcp data-driven architecture

# RYE Operating System Principles

## What is RYE?

RYE is an **operating system layer** that runs on top of the Lilux microkernel. It provides intelligent tool execution and content understanding.

## Microkernel + OS Relationship

| Aspect              | Lilux (Microkernel)          | RYE (OS)                                |
| ------------------- | ---------------------------- | --------------------------------------- |
| **What**            | Generic execution primitives | Universal executor + data-driven tools  |
| **Analogy**         | Hardware microkernel         | Operating system                        |
| **Intelligence**    | Dumb - just executes         | Smart - understands content shapes      |
| **Package**         | `lilux`                      | `rye-lilux`                             |
| **Entry Point**     | Not used (dependency)        | `python -m rye.server`                  |
| **Tool Categories** | 5 hardcoded tools            | All tools in .ai/tools/\* (by category) |

## Key Principles

### 1. Data-Driven Architecture

- All tools defined as data in `.ai/tools/`
- No hardcoded tool lists
- Auto-discovery from filesystem

### 2. Category Organization

- Tools organized by category: `rye`, `python`, `utility`, etc.
- Each category is a category
- Everything is a tool (primitives, runtimes, capabilities, etc.)

### 3. Schema/Code Separation

- **Schemas** in `.ai/tools/rye/primitives/` (metadata only)
- **Code** in `lilux/primitives/` (implementation)
- Clear separation of concerns

### 4. Universal Execution

- Single universal executor routes all tools
- Routes based on `__tool_type__` and `__executor_id__`
- Supports primitives → runtimes → tools chain

## Bottom Line

- User installs RYE → gets OS + microkernel
- LLM talks to RYE → RYE universal executor routes to Lilux
- RYE scans .ai/tools/ → builds dynamic tool registry
- All intelligence is data-defined in .ai/ (not hardcoded)

