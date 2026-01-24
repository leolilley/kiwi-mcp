thread id: T-019bac50-3127-719a-b66c-69fe1c70fdda

# Directive-Driven MCP Development

**Date:** 2026-01-11  
**Author:** Leo + Agent  
**Purpose:** How to use the Kiwi directive system to build the unified MCP

---

## Philosophy: Why Directive-Driven Development?

The goal is to create a **reproducible, self-improving build process** where:

1. Every step is a directive that can be re-executed
2. Failed executions improve the directive (annealing)
3. Successful patterns get captured as knowledge
4. At the end, you have a directive collection that can recreate the entire MCP

> "Solve once, solve everywhere."

### The Meta-Irony

We're using the Kiwi system (directives + scripts + knowledge) to build the unified Kiwi MCP. The directives we create become part of the system they're building.

---

## Table of Contents

1. [Directive Hierarchy](#1-directive-hierarchy)
2. [Master Orchestrator](#2-master-orchestrator)
3. [Phase Directives](#3-phase-directives)
4. [Component Directives](#4-component-directives)
5. [Annealing Strategy](#5-annealing-strategy)
6. [Knowledge Capture](#6-knowledge-capture)
7. [Complete Directive Collection](#7-complete-directive-collection)
8. [Execution Playbook](#8-execution-playbook)

---

## 1. Directive Hierarchy

```
┌─────────────────────────────────────────────────────────────────────┐
│                    build_kiwi_mcp (Master Orchestrator)             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Phase 1: Scaffold          Phase 2: Core           Phase 3: Types  │
│  ┌─────────────────┐       ┌─────────────────┐     ┌──────────────┐ │
│  │ init_mcp_project│       │ create_tool     │     │ create_type_ │ │
│  │                 │       │ (×4)            │     │ handler      │ │
│  │ - pyproject     │       │                 │     │ (×3 types)   │ │
│  │ - server.py     │       │ - search        │     │              │ │
│  │ - structure     │       │ - load          │     │ - directive  │ │
│  └─────────────────┘       │ - execute       │     │ - script     │ │
│                            │ - help          │     │ - knowledge  │ │
│                            └─────────────────┘     └──────────────┘ │
│                                                                     │
│  Phase 4: API              Phase 5: Integration   Phase 6: Polish   │
│  ┌─────────────────┐       ┌─────────────────┐     ┌──────────────┐ │
│  │ port_api_client │       │ wire_handlers   │     │ add_tests    │ │
│  │ (×3)            │       │                 │     │              │ │
│  │                 │       │ integration_    │     │ generate_    │ │
│  │ - directive_reg │       │ test            │     │ docs         │ │
│  │ - script_reg    │       │                 │     │              │ │
│  │ - knowledge_reg │       │ e2e_validation  │     │ final_review │ │
│  └─────────────────┘       └─────────────────┘     └──────────────┘ │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Master Orchestrator

The master orchestrator directive coordinates the entire build.

### Directive: `build_kiwi_mcp`

```xml
<directive name="build_kiwi_mcp" version="1.0.0">
  <metadata>
    <description>Master orchestrator for building the unified Kiwi MCP</description>
    <category>orchestration</category>
    <author>code-kiwi</author>
    <complexity>high</complexity>
    <estimated_time>4-6 hours</estimated_time>
  </metadata>

  <context>
    <prerequisites>
      - context-kiwi, script-kiwi, knowledge-kiwi repos accessible
      - Supabase project configured
      - Python environment ready
    </prerequisites>
  </context>

  <inputs>
    <input name="project_path" type="string" required="true">
      Absolute path to kiwi-mcp project root
    </input>
    <input name="source_repos" type="object" required="true">
      Paths to source MCPs: {context_kiwi, script_kiwi, knowledge_kiwi}
    </input>
    <input name="skip_phases" type="array" required="false">
      Phases to skip if already completed
    </input>
  </inputs>

  <process>
    <phase name="1_scaffold" directive="init_mcp_project">
      <description>Create project structure and base files</description>
      <inputs>
        <map from="project_path" to="project_path"/>
      </inputs>
      <success_criteria>
        - pyproject.toml exists and is valid
        - server.py runs without import errors
        - Directory structure matches IMPLEMENTATION.md
      </success_criteria>
      <on_failure>
        Store error in knowledge, update directive, retry
      </on_failure>
    </phase>

    <phase name="2_tools" parallel="false">
      <description>Create the 4 unified tools</description>
      <steps>
        <step directive="create_tool" inputs="{tool_name: 'search'}"/>
        <step directive="create_tool" inputs="{tool_name: 'load'}"/>
        <step directive="create_tool" inputs="{tool_name: 'execute'}"/>
        <step directive="create_tool" inputs="{tool_name: 'help'}"/>
      </steps>
      <success_criteria>
        - All 4 tools importable
        - Tools have correct schema
        - Server lists all 4 tools
      </success_criteria>
    </phase>

    <phase name="3_handlers" parallel="true">
      <description>Create type-specific handlers</description>
      <steps>
        <step directive="create_type_handler" inputs="{type_name: 'directive'}"/>
        <step directive="create_type_handler" inputs="{type_name: 'script'}"/>
        <step directive="create_type_handler" inputs="{type_name: 'knowledge'}"/>
      </steps>
      <note>
        These can run in parallel as they're independent.
        Each creates: search.py, load.py, execute.py for its type.
      </note>
    </phase>

    <phase name="4_api" parallel="true">
      <description>Port API clients from source MCPs</description>
      <steps>
        <step directive="port_api_client" inputs="{
          source_mcp: 'context_kiwi',
          source_file: 'db/directives.py',
          target_name: 'directive_registry'
        }"/>
        <step directive="port_api_client" inputs="{
          source_mcp: 'script_kiwi',
          source_file: 'api/script_registry.py',
          target_name: 'script_registry'
        }"/>
        <step directive="port_api_client" inputs="{
          source_mcp: 'knowledge_kiwi',
          source_file: 'api/knowledge_registry.py',
          target_name: 'knowledge_registry'
        }"/>
      </steps>
    </phase>

    <phase name="5_integration">
      <description>Wire everything together and test</description>
      <steps>
        <step directive="wire_handler_registry"/>
        <step directive="integration_test"/>
        <step directive="e2e_validation"/>
      </steps>
      <success_criteria>
        - TypeHandlerRegistry routes correctly
        - All operations work for all types
        - No import errors
      </success_criteria>
    </phase>

    <phase name="6_polish">
      <description>Tests, docs, final review</description>
      <steps>
        <step directive="add_tests"/>
        <step directive="generate_docs"/>
        <step directive="final_review"/>
      </steps>
    </phase>
  </process>

  <outputs>
    <output name="project_status" type="object">
      {phases_completed, tests_passed, coverage, issues}
    </output>
    <output name="learnings" type="array">
      Knowledge entries to capture from the build
    </output>
  </outputs>

  <annealing>
    <on_phase_failure>
      1. Capture error details
      2. Create knowledge entry: kb-build-error-{phase}-{timestamp}
      3. Analyze root cause
      4. Update the failing directive
      5. Retry phase
    </on_phase_failure>
    <on_success>
      1. Record execution time per phase
      2. Note any manual interventions
      3. Update directives with improvements
      4. Publish updated directives to registry
    </on_success>
  </annealing>
</directive>
```

---

## 3. Phase Directives

### Phase 1: `init_mcp_project`

```xml
<directive name="init_mcp_project" version="1.0.0">
  <metadata>
    <description>Initialize a new MCP project with correct structure</description>
    <category>scaffolding</category>
    <complexity>low</complexity>
  </metadata>

  <inputs>
    <input name="project_path" type="string" required="true"/>
    <input name="project_name" type="string" default="kiwi-mcp"/>
    <input name="package_name" type="string" default="kiwi_mcp"/>
  </inputs>

  <process>
    <step name="create_structure">
      <action>Create directory structure</action>
      <code language="bash">
mkdir -p {project_path}/{package_name}/{tools,handlers/{directive,script,knowledge},api,config,utils}
mkdir -p {project_path}/tests/{unit,integration}
      </code>
    </step>

    <step name="create_pyproject">
      <action>Generate pyproject.toml</action>
      <template>IMPLEMENTATION.md#pyproject.toml</template>
      <substitutions>
        - {project_name} → project_name input
        - {package_name} → package_name input
      </substitutions>
    </step>

    <step name="create_init_files">
      <action>Create __init__.py files</action>
      <files>
        - {package_name}/__init__.py: __version__ = "0.1.0"
        - {package_name}/tools/__init__.py: empty
        - {package_name}/handlers/__init__.py: empty
        - {package_name}/api/__init__.py: empty
        - tests/__init__.py: empty
      </files>
    </step>

    <step name="create_server">
      <action>Create server.py</action>
      <template>IMPLEMENTATION.md#server.py</template>
      <note>
        Initially create with placeholder tool imports.
        Will be updated as tools are created.
      </note>
    </step>

    <step name="create_config">
      <action>Create configuration files</action>
      <files>
        - pytest.ini
        - .env.example
        - .gitignore
        - Makefile
      </files>
    </step>

    <step name="validate">
      <action>Validate project structure</action>
      <validation>
        - Run: python -c "import {package_name}"
        - Check all directories exist
        - Verify pyproject.toml is valid TOML
      </validation>
    </step>
  </process>

  <outputs>
    <output name="project_ready" type="boolean"/>
    <output name="structure_report" type="object"/>
  </outputs>

  <knowledge_hooks>
    <on_success>
      Create: kb-pattern-mcp-project-structure
      Content: Validated directory structure for MCP projects
    </on_success>
  </knowledge_hooks>
</directive>
```

### Phase 2: `create_tool`

````xml
<directive name="create_tool" version="1.0.0">
  <metadata>
    <description>Create a unified MCP tool</description>
    <category>implementation</category>
    <complexity>medium</complexity>
  </metadata>

  <inputs>
    <input name="tool_name" type="string" required="true">
      One of: search, load, execute, help
    </input>
    <input name="project_path" type="string" required="true"/>
  </inputs>

  <context>
    <reference>IMPLEMENTATION.md - Tool Specifications section</reference>
  </context>

  <process>
    <step name="load_spec">
      <action>Load tool specification from IMPLEMENTATION.md</action>
      <knowledge_search>
        Query: "kiwi mcp {tool_name} tool specification"
        Fallback: Read IMPLEMENTATION.md section 5.{tool_index}
      </knowledge_search>
    </step>

    <step name="create_tool_file">
      <action>Create {tool_name}.py</action>
      <template>
```python
# kiwi_mcp/tools/{tool_name}.py
"""
{Tool_Name} Tool

{description from spec}
"""

import json
from typing import Any
from mcp.types import Tool

from kiwi_mcp.handlers.registry import TypeHandlerRegistry


class {Tool_Name}Tool:
    """{description}"""

    @property
    def schema(self) -> Tool:
        return Tool(
            name="{tool_name}",
            description="""{full_description}""",
            inputSchema={schema_from_spec}
        )

    async def execute(self, arguments: dict) -> str:
        """Execute {tool_name} operation."""
        # Validation
        {validation_logic}

        # Dispatch to handler
        try:
            result = await TypeHandlerRegistry.dispatch_async(
                item_type, "{operation}",
                **validated_args
            )
            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})
````

      </template>
    </step>

    <step name="update_tools_init">
      <action>Add export to tools/__init__.py</action>
      <code>

from .{tool_name} import {Tool_Name}Tool
</code>
</step>

    <step name="update_server">
      <action>Register tool in server.py</action>
      <modification>
        Add to self.tools dict in KiwiMCP.__init__
      </modification>
    </step>

    <step name="validate">
      <action>Validate tool works</action>
      <tests>
        - Import succeeds
        - Schema is valid
        - execute() returns JSON
      </tests>
    </step>

  </process>
  
  <annealing>
    <failure_patterns>
      <pattern name="import_error">
        <symptom>ModuleNotFoundError</symptom>
        <fix>Check TypeHandlerRegistry import path</fix>
      </pattern>
      <pattern name="schema_invalid">
        <symptom>MCP schema validation fails</symptom>
        <fix>Ensure inputSchema matches MCP spec</fix>
      </pattern>
    </failure_patterns>
  </annealing>
</directive>
```

### Phase 3: `create_type_handler`

```xml
<directive name="create_type_handler" version="1.0.0">
  <metadata>
    <description>Create handlers for a specific type (directive/script/knowledge)</description>
    <category>implementation</category>
    <complexity>high</complexity>
  </metadata>

  <inputs>
    <input name="type_name" type="string" required="true">
      One of: directive, script, knowledge
    </input>
    <input name="project_path" type="string" required="true"/>
    <input name="source_mcp_path" type="string" required="true">
      Path to source MCP to port from
    </input>
  </inputs>

  <process>
    <step name="analyze_source">
      <action>Analyze source MCP structure</action>
      <analysis>
        Read source tools/ directory structure.
        Identify:
        - Search implementation
        - Load/Get implementation
        - Run/Execute implementation
        - Publish implementation
        - Delete implementation
      </analysis>
    </step>

    <step name="create_search_handler">
      <action>Create handlers/{type_name}/search.py</action>
      <porting_guide>
        Source: {source_mcp}/tools/search.py
        Adapt:
        - Change function signature to async def search_{type_name}s(...)
        - Return List[Dict] instead of tool result
        - Keep multi-term search logic
        - Keep relevance scoring
      </porting_guide>
    </step>

    <step name="create_load_handler">
      <action>Create handlers/{type_name}/load.py</action>
      <porting_guide>
        Source: {source_mcp}/tools/get.py or load.py
        Adapt:
        - async def load_{type_name}(item_id, source, destination, ...)
        - Combine registry fetch + local write
        - Return Dict with status, path
      </porting_guide>
    </step>

    <step name="create_execute_handler">
      <action>Create handlers/{type_name}/execute.py</action>
      <porting_guide>
        Source: {source_mcp}/tools/run.py, publish.py, delete.py
        Combine into single execute function:
        - async def execute_{type_name}(action, item_id, parameters, ...)
        - Switch on action: run, publish, delete, create, update
        - For knowledge: also handle "link" action
      </porting_guide>
      <action_mapping>
        | action  | source function                    |
        |---------|-----------------------------------|
        | run     | run.py: execute()                 |
        | publish | publish.py: execute()             |
        | delete  | delete.py: execute()              |
        | create  | (new) or manage.py: create        |
        | update  | (new) or manage.py: update        |
        | link    | (knowledge only) link.py          |
      </action_mapping>
    </step>

    <step name="create_resolver">
      <action>Create handlers/{type_name}/resolver.py (if needed)</action>
      <note>
        Port local file resolution logic:
        - For directive: from loader.py
        - For script: from script_resolver.py
        - For knowledge: from knowledge_resolver.py

        Rename to just "resolver" for consistency.
      </note>
    </step>

    <step name="create_init">
      <action>Create handlers/{type_name}/__init__.py</action>
      <exports>
        from .search import search_{type_name}s
        from .load import load_{type_name}
        from .execute import execute_{type_name}
      </exports>
    </step>

    <step name="register_handlers">
      <action>Add to TypeHandlerRegistry</action>
      <code>
TypeHandlerRegistry.register("{type_name}", "search", search_{type_name}s)
TypeHandlerRegistry.register("{type_name}", "load", load_{type_name})
TypeHandlerRegistry.register("{type_name}", "execute", execute_{type_name})
      </code>
    </step>

    <step name="validate">
      <action>Test handler operations</action>
      <tests>
        - search_{type_name}s("test", source="local")
        - load_{type_name}("test_id", destination="user")
        - execute_{type_name}("run", "test_id", {})
      </tests>
    </step>
  </process>

  <type_specific_notes>
    <directive>
      - loader.py contains DirectiveLoader class - port as resolver.py
      - XML parsing logic for directive content
      - Tech stack extraction from parsed XML
    </directive>
    <script>
      - Python execution via importlib
      - Environment variable handling
      - Dependency checking
      - Cost estimation
    </script>
    <knowledge>
      - YAML frontmatter parsing
      - Zettel ID format validation
      - Link/relationship handling
      - Collection support
    </knowledge>
  </type_specific_notes>

  <annealing>
    <common_errors>
      <error name="circular_import">
        <fix>Use lazy imports inside functions</fix>
      </error>
      <error name="async_sync_mismatch">
        <fix>Ensure registry client methods are async</fix>
      </error>
      <error name="path_resolution">
        <fix>Use utils/paths.py consistently</fix>
      </error>
    </common_errors>
  </annealing>
</directive>
```

### Phase 4: `port_api_client`

```xml
<directive name="port_api_client" version="1.0.0">
  <metadata>
    <description>Port a Supabase registry client from source MCP</description>
    <category>porting</category>
    <complexity>medium</complexity>
  </metadata>

  <inputs>
    <input name="source_mcp" type="string" required="true">
      Source MCP name: context_kiwi, script_kiwi, knowledge_kiwi
    </input>
    <input name="source_file" type="string" required="true">
      Relative path to source file within MCP
    </input>
    <input name="target_name" type="string" required="true">
      Target registry name: directive_registry, script_registry, knowledge_registry
    </input>
    <input name="project_path" type="string" required="true"/>
  </inputs>

  <process>
    <step name="read_source">
      <action>Read source registry implementation</action>
      <path>{source_mcp_path}/{source_mcp}/{source_file}</path>
    </step>

    <step name="create_base_registry">
      <action>Ensure api/base.py exists</action>
      <check>If not exists, create BaseRegistry class</check>
      <template>IMPLEMENTATION.md#api/base.py</template>
    </step>

    <step name="adapt_class">
      <action>Create api/{target_name}.py</action>
      <adaptations>
        1. Inherit from BaseRegistry
        2. Remove duplicate Supabase client init (use base)
        3. Keep search logic with multi-term matching
        4. Keep relevance scoring (or use base._calculate_relevance_score)
        5. Make all methods async
        6. Standardize return types
      </adaptations>
      <method_mapping>
        | Source Method        | Target Method          |
        |---------------------|------------------------|
        | search_*            | async search()         |
        | get_*               | async get()            |
        | publish_*           | async publish()        |
        | delete_*            | async delete()         |
        | (knowledge) link    | async create_relationship() |
      </method_mapping>
    </step>

    <step name="standardize_returns">
      <action>Ensure consistent return types</action>
      <returns>
        - search: List[Dict[str, Any]]
        - get: Optional[Dict[str, Any]]
        - publish: Dict[str, Any] with status/error
        - delete: Dict[str, Any] with status/error
      </returns>
    </step>

    <step name="update_init">
      <action>Export from api/__init__.py</action>
      <code>
from .{target_name} import {ClassName}
      </code>
    </step>

    <step name="validate">
      <action>Test registry client</action>
      <tests>
        - Client initializes (may be None without env vars)
        - is_configured property works
        - Methods don't crash with mock data
      </tests>
    </step>
  </process>

  <porting_checklist>
    <item>Remove hardcoded paths</item>
    <item>Use BaseRegistry for common logic</item>
    <item>Ensure error messages are helpful</item>
    <item>Handle missing Supabase gracefully</item>
    <item>Add type hints</item>
  </porting_checklist>
</directive>
```

### Phase 5: `wire_handler_registry`

```xml
<directive name="wire_handler_registry" version="1.0.0">
  <metadata>
    <description>Wire up TypeHandlerRegistry with all handlers</description>
    <category>integration</category>
    <complexity>low</complexity>
  </metadata>

  <process>
    <step name="create_registry">
      <action>Create handlers/registry.py</action>
      <template>IMPLEMENTATION.md#handlers/registry.py</template>
    </step>

    <step name="register_all">
      <action>Register all handlers in _register_handlers()</action>
      <code>
def _register_handlers():
    # Directive
    from kiwi_mcp.handlers.directive import search_directives, load_directive, execute_directive
    TypeHandlerRegistry.register("directive", "search", search_directives)
    TypeHandlerRegistry.register("directive", "load", load_directive)
    TypeHandlerRegistry.register("directive", "execute", execute_directive)

    # Script
    from kiwi_mcp.handlers.script import search_scripts, load_script, execute_script
    TypeHandlerRegistry.register("script", "search", search_scripts)
    TypeHandlerRegistry.register("script", "load", load_script)
    TypeHandlerRegistry.register("script", "execute", execute_script)

    # Knowledge
    from kiwi_mcp.handlers.knowledge import search_knowledge, load_knowledge, execute_knowledge
    TypeHandlerRegistry.register("knowledge", "search", search_knowledge)
    TypeHandlerRegistry.register("knowledge", "load", load_knowledge)
    TypeHandlerRegistry.register("knowledge", "execute", execute_knowledge)

_register_handlers()
      </code>
    </step>

    <step name="validate">
      <action>Test dispatch works</action>
      <tests>
        - TypeHandlerRegistry.get_handler("directive", "search") is not None
        - TypeHandlerRegistry.get_handler("script", "load") is not None
        - TypeHandlerRegistry.get_handler("knowledge", "execute") is not None
      </tests>
    </step>
  </process>
</directive>
```

---

## 4. Component Directives

### Utility Directives

```xml
<directive name="create_utils" version="1.0.0">
  <metadata>
    <description>Create shared utility modules</description>
    <category>implementation</category>
  </metadata>

  <process>
    <step name="create_paths">
      <action>Create utils/paths.py</action>
      <functions>
        - get_user_home() → Path
        - get_project_path(project_path) → Path
        - get_type_directory(base, type) → Path
        - resolve_item_path(id, type, source, project_path) → Optional[Path]
      </functions>
    </step>

    <step name="create_files">
      <action>Create utils/files.py</action>
      <functions>
        - read_markdown_file(path) → Dict
        - write_markdown_file(path, content, frontmatter) → None
        - write_python_file(path, content) → None
      </functions>
    </step>

    <step name="create_search">
      <action>Create utils/search.py</action>
      <functions>
        - parse_search_query(query) → List[str]
        - calculate_relevance_score(terms, name, desc) → float
        - matches_all_terms(text, terms) → bool
      </functions>
      <note>
        Extract common search logic here.
        All handlers and registries can use these.
      </note>
    </step>

    <step name="create_logger">
      <action>Create utils/logger.py</action>
      <implementation>Simple logging wrapper</implementation>
    </step>
  </process>
</directive>
```

### Test Directives

```xml
<directive name="add_tests" version="1.0.0">
  <metadata>
    <description>Add comprehensive test suite</description>
    <category>testing</category>
  </metadata>

  <process>
    <step name="create_conftest">
      <action>Create tests/conftest.py</action>
      <fixtures>
        - temp_project: Temporary project directory
        - sample_directive: Sample .md file
        - sample_script: Sample .py file
        - sample_knowledge: Sample knowledge entry
        - mock_registry: Mocked Supabase client
      </fixtures>
    </step>

    <step name="create_unit_tests">
      <action>Create unit tests</action>
      <files>
        - tests/unit/test_tools.py
        - tests/unit/test_handlers.py
        - tests/unit/test_api.py
        - tests/unit/test_utils.py
      </files>
      <coverage_targets>
        - Tool validation logic
        - Handler dispatch
        - Path resolution
        - Search scoring
      </coverage_targets>
    </step>

    <step name="create_integration_tests">
      <action>Create integration tests</action>
      <files>
        - tests/integration/test_directive_flow.py
        - tests/integration/test_script_flow.py
        - tests/integration/test_knowledge_flow.py
      </files>
      <flows>
        - search → load → execute(run)
        - create → execute(publish)
        - search → execute(delete)
      </flows>
    </step>

    <step name="run_tests">
      <action>Run full test suite</action>
      <command>pytest tests/ -v --tb=short</command>
      <success_criteria>All tests pass</success_criteria>
    </step>
  </process>
</directive>
```

---

## 5. Annealing Strategy

### What is Annealing?

Directives improve through execution. When a directive fails or requires manual intervention, we:

1. **Capture the failure** → Create knowledge entry
2. **Analyze root cause** → Identify what was missing
3. **Update the directive** → Add the fix
4. **Retry** → Verify the fix works
5. **Publish** → Share improved directive

### Annealing Directive

```xml
<directive name="anneal_directive" version="1.0.0">
  <metadata>
    <description>Improve a directive based on execution feedback</description>
    <category>meta</category>
    <author>code-kiwi</author>
  </metadata>

  <inputs>
    <input name="directive_name" type="string" required="true"/>
    <input name="execution_log" type="object" required="true">
      {
        success: boolean,
        error: string | null,
        manual_interventions: string[],
        duration_seconds: number,
        steps_completed: string[],
        steps_failed: string[]
      }
    </input>
    <input name="project_path" type="string" required="true"/>
  </inputs>

  <process>
    <step name="analyze_execution">
      <action>Analyze what happened</action>
      <analysis>
        If error:
          - Parse error message
          - Identify which step failed
          - Determine root cause category:
            - missing_dependency
            - incorrect_path
            - api_change
            - edge_case
            - unclear_instruction

        If manual_interventions:
          - These are gaps in the directive
          - Each intervention should become a step

        If slow (duration > expected):
          - Identify bottleneck steps
          - Consider parallelization
      </analysis>
    </step>

    <step name="create_knowledge_entry">
      <action>Store learning</action>
      <knowledge>
        zettel_id: kb-directive-{directive_name}-{timestamp}
        title: "Execution feedback for {directive_name}"
        entry_type: learning
        content: |
          ## Execution Summary
          - Success: {success}
          - Duration: {duration}s

          ## Issues Found
          {list of issues}

          ## Fixes Applied
          {list of fixes}

          ## Recommendations
          {future improvements}
      </knowledge>
    </step>

    <step name="update_directive" condition="has_improvements">
      <action>Modify directive with fixes</action>
      <modifications>
        - Add missing steps
        - Clarify unclear instructions
        - Add error handling for edge cases
        - Add failure_patterns to annealing section
        - Update success_criteria
        - Increment version
      </modifications>
    </step>

    <step name="test_updated_directive">
      <action>Re-run directive to verify fix</action>
      <command>
        execute(action="run", id="{directive_name}", type="directive")
      </command>
    </step>

    <step name="publish_if_stable" condition="test_passed AND improvements_significant">
      <action>Publish updated directive</action>
      <command>
        execute(action="publish", id="{directive_name}", type="directive",
                parameters={version: "{new_version}"})
      </command>
    </step>
  </process>

  <outputs>
    <output name="annealing_report" type="object">
      {
        issues_found: number,
        fixes_applied: number,
        new_version: string | null,
        published: boolean,
        knowledge_entry: string
      }
    </output>
  </outputs>
</directive>
```

### Annealing Patterns

```yaml
# Common failure patterns and their fixes

patterns:
  - name: import_error
    symptoms:
      - ModuleNotFoundError
      - ImportError
    diagnosis: |
      Check:
      1. Module path is correct
      2. __init__.py exports the symbol
      3. Circular import
    fix_template: |
      Add step: "Validate imports"
      Add to prerequisites: "Ensure {module} is installed"

  - name: path_not_found
    symptoms:
      - FileNotFoundError
      - No such file or directory
    diagnosis: |
      Check:
      1. project_path is absolute
      2. Directory was created
      3. File extension is correct
    fix_template: |
      Add step: "Create parent directories"
      Add validation: "Path exists check"

  - name: supabase_auth
    symptoms:
      - 401 Unauthorized
      - Invalid API key
    diagnosis: |
      Check:
      1. SUPABASE_URL set
      2. SUPABASE_SECRET_KEY set (not anon key)
      3. Key has correct permissions
    fix_template: |
      Add prerequisite: "Supabase configured with service_role key"
      Add step: "Validate Supabase connection"

  - name: async_sync_mismatch
    symptoms:
      - coroutine was never awaited
      - object NoneType can't be used in 'await'
    diagnosis: |
      Check:
      1. Method is defined as async
      2. Caller uses await
      3. Registry client methods are async
    fix_template: |
      Update function signature to async
      Add await to all calls

  - name: type_mismatch
    symptoms:
      - TypeError
      - 'str' object has no attribute 'get'
    diagnosis: |
      Check:
      1. Return type matches expected
      2. JSON parsing happened
      3. Optional values handled
    fix_template: |
      Add type validation step
      Add null checks
```

---

## 6. Knowledge Capture

### Knowledge Schema for Build Learnings

```yaml
# kb-mcp-build-{component}-{date}.md

---
zettel_id: kb-mcp-build-handlers-20260111
title: "Building Type Handlers for Unified MCP"
entry_type: learning
category: mcp-development
tags:
  - kiwi-mcp
  - handlers
  - porting
source_type: experiment
---

## Context
Building type handlers by porting from source MCPs.

## Key Learnings

### What Worked
- Using BaseRegistry for common Supabase logic
- Async all the way down
- Lazy imports to avoid circular dependencies

### What Didn't Work
- Trying to share too much code initially
- Sync methods in registry clients
- Hardcoded paths

### Recommendations
1. Start with handlers working independently
2. Extract common code after it works
3. Test each handler in isolation before wiring
```

### Knowledge Entries to Create

| ID                         | Title                               | Trigger                    |
| -------------------------- | ----------------------------------- | -------------------------- |
| `kb-mcp-project-structure` | MCP Project Structure Pattern       | After init_mcp_project     |
| `kb-mcp-tool-pattern`      | Unified Tool Implementation Pattern | After all tools created    |
| `kb-mcp-handler-pattern`   | Type Handler Pattern                | After all handlers created |
| `kb-mcp-registry-pattern`  | Registry Client Porting             | After all APIs ported      |
| `kb-mcp-testing-strategy`  | MCP Testing Approach                | After tests added          |
| `kb-mcp-build-timeline`    | Full Build Timeline & Issues        | After completion           |

---

## 7. Complete Directive Collection

### Directory Structure

```
.ai/directives/
├── orchestration/
│   └── build_kiwi_mcp.md           # Master orchestrator
│
├── scaffolding/
│   └── init_mcp_project.md         # Phase 1
│
├── implementation/
│   ├── create_tool.md              # Phase 2
│   ├── create_type_handler.md      # Phase 3
│   └── create_utils.md             # Utilities
│
├── porting/
│   └── port_api_client.md          # Phase 4
│
├── integration/
│   ├── wire_handler_registry.md    # Phase 5a
│   ├── integration_test.md         # Phase 5b
│   └── e2e_validation.md           # Phase 5c
│
├── testing/
│   └── add_tests.md                # Phase 6a
│
├── documentation/
│   ├── generate_docs.md            # Phase 6b
│   └── final_review.md             # Phase 6c
│
└── meta/
    └── anneal_directive.md         # Annealing process
```

### Directive Dependency Graph

```
build_kiwi_mcp
├── init_mcp_project
│   └── (no dependencies)
├── create_tool (×4)
│   └── depends: init_mcp_project
├── create_type_handler (×3)
│   ├── depends: init_mcp_project
│   └── uses: port_api_client
├── port_api_client (×3)
│   └── depends: init_mcp_project
├── wire_handler_registry
│   └── depends: create_type_handler (all 3)
├── integration_test
│   └── depends: wire_handler_registry
├── e2e_validation
│   └── depends: integration_test
├── add_tests
│   └── depends: e2e_validation
├── generate_docs
│   └── depends: add_tests
└── final_review
    └── depends: generate_docs
```

---

## 8. Execution Playbook

### How to Execute the Build

```markdown
## Step-by-Step Execution

### Prerequisites

1. Clone/access all 3 source MCPs:

   - /home/leo/projects/context-kiwi
   - /home/leo/projects/script-kiwi
   - /home/leo/projects/knowledge-kiwi

2. Set up kiwi-mcp project:

   - /home/leo/projects/kiwi-mcp

3. Ensure Supabase is configured (for testing)

### Execution Commands

# Option A: Run master orchestrator (recommended)

run("build_kiwi_mcp", {
project_path: "/home/leo/projects/kiwi-mcp",
source_repos: {
context_kiwi: "/home/leo/projects/context-kiwi",
script_kiwi: "/home/leo/projects/script-kiwi",
knowledge_kiwi: "/home/leo/projects/knowledge-kiwi"
}
})

# Option B: Run phases individually

run("init_mcp_project", {project_path: "/home/leo/projects/kiwi-mcp"})
run("create_tool", {tool_name: "search", project_path: "..."})
run("create_tool", {tool_name: "load", project_path: "..."})

# ... etc

### After Each Phase

1. Check success criteria
2. If failed:
   - Run anneal_directive with execution log
   - Retry phase
3. If succeeded:
   - Store learnings as knowledge entry
   - Proceed to next phase

### Verification

After all phases:

1. Run: pytest tests/ -v
2. Run: python -c "from kiwi_mcp import server; print('OK')"
3. Test MCP connection: Configure in IDE and call help()
```

### Annealing Loop

```
┌────────────────────────────────────────────────────────────┐
│                      EXECUTION LOOP                        │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌───────────┐    ┌───────────┐    ┌───────────────────┐   │
│  │  Execute  │───▶│  Check    │───▶│  Success?         │   │
│  │ Directive │    │  Result   │    │                   │   │
│  └───────────┘    └───────────┘    └─────────┬─────────┘   │
│                                              │             │
│       │                   ┌──────────────────┴──────┐      │
│       │                   │                         │      │
│       │                   ▼                         ▼      │
│       │            ┌─────────────┐              ┌────────┐ │
│       │            │   YES       │              │   NO   │ │
│       │            └──────┬──────┘              └────┬───┘ │
│       │                   │                          │     │
│       │                   ▼                          ▼     │
│       │            ┌─────────────┐         ┌─────────────┐ │
│       │            │ Store       │         │ Capture     │ │
│       │            │ Learning    │         │ Error       │ │
│       │            └──────┬──────┘         └──────┬──────┘ │
│       │                   │                       │        │
│       │                   ▼                       ▼        │
│       │            ┌─────────────┐         ┌─────────────┐ │
│       │            │ Next Phase  │         │ Anneal      │ │
│       │            │             │         │ Directive   │ │
│       │            └─────────────┘         └──────┬──────┘ │
│       │                                           │        │
│       │                                           ▼        │
│       │                                    ┌─────────────┐ │
│       │                                    │ Update      │ │
│       │                                    │ Directive   │ │
│       │                                    └──────┬──────┘ │
│       │                                           │        │
│       │                                           ▼        │
│       │                                    ┌─────────────┐ │
│       └────────────────────────────────────│ Retry       │ │
│                                            │             │ │
│                                            └─────────────┘ │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## Summary

This document provides a complete directive-driven approach to building the unified Kiwi MCP:

1. **Master Orchestrator** (`build_kiwi_mcp`) - Coordinates 6 phases
2. **Phase Directives** - One directive per major phase
3. **Component Directives** - Granular directives for specific tasks
4. **Annealing Strategy** - How directives improve from failures
5. **Knowledge Capture** - What to record and when
6. **Complete Collection** - All 14 directives organized
7. **Execution Playbook** - Step-by-step guide

**The End Result:**

After execution, you'll have:

- A working unified Kiwi MCP
- 14 battle-tested directives that can recreate it
- Knowledge entries capturing all learnings
- A template for building future MCPs

> "Solve once, solve everywhere."

---

_Generated: 2026-01-11_
