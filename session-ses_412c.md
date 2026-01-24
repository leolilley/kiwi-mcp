# Kiwi-MCP: execute action create_directive on create_directive

**Session ID:** ses_412cb1b45ffesAsjzcpSjQABbB
**Created:** 1/24/2026, 12:33:45 PM
**Updated:** 1/24/2026, 12:34:23 PM

---

## User

kiwi-mcp run execute action create on create_directive

---

## Assistant (Kiwi-Free-Grokfast · grok-code · 19.3s)

_Thinking:_

The user said: "kiwi-mcp run execute action create on create_directive"


## Parsing user command  
- The user provided: "kiwi-mcp run execute action create on create_directive."  
- This suggests mapping natural language to a directive execution based on a command dispatch table.  
- The pattern "run directive X" appears relevant for interpreting the command.

## Interpreting user intent  
- The user's command, "kiwi-mcp run execute action create on create_directive," seems to involve using the kiwi-mcp_execute tool.  
- It likely means creating a directive named "create_directive" with action="create" and item_type="directive."  
- The command appears mangled, possibly intending to run or create a directive called "create_directive.

```
Tool: kiwi-mcp_search

**Input:**
```json
{
  "item_type": "directive",
  "query": "create directive",
  "source": "all",
  "project_path": "/home/leo/projects/kiwi-mcp"
}
```
**Output:**
```
{
  "query": "create directive",
  "source": "all",
  "results": [
    {
      "name": "create_directive",
      "description": "Create new directives with proper XML structure and validation.",
      "version": "4.0.0",
      "score": 100.0,
      "source": "project",
      "path": "/home/leo/projects/kiwi-mcp/.ai/directives/core/create_directive.md"
    },
    {
      "name": "bootstrap",
      "description": "Bootstrap a project from a plan document - initializes .ai/ structure and creates all directives needed to complete the project via MCP tool calls",
      "version": "1.9.0",
      "score": 100.0,
      "source": "project",
      "path": "/home/leo/projects/kiwi-mcp/.ai/directives/core/bootstrap.md"
    },
    {
      "name": "create_context_loader",
      "description": "Create directives that load knowledge entries into agent context via the unified MCP.",
      "version": "1.2.0",
      "score": 100.0,
      "source": "project",
      "path": "/home/leo/projects/kiwi-mcp/.ai/directives/core/create_context_loader.md"
    },
    {
      "name": "create_init",
      "description": "Create specialized init directives for specific tech stacks.",
      "version": "1.3.2",
      "score": 100.0,
      "source": "project",
      "path": "/home/leo/projects/kiwi-mcp/.ai/directives/core/create_init.md"
    },
    {
      "name": "orchestrate_general",
      "description": "Create orchestrator directive for parallel execution of a specific directive across multiple targets (does NOT execute them)",
      "version": "1.4.0",
      "score": 100.0,
      "source": "project",
      "path": "/home/leo/projects/kiwi-mcp/.ai/directives/meta/orchestrate_general.md"
    },
    {
      "name": "fix_nested_cdata_in_directive",
      "description": "Fix nested CDATA errors in directives that fail kiwi-mcp execute create validation",
      "version": "1.0.0",
      "score": 100.0,
      "source": "project",
      "path": "/home/leo/projects/kiwi-mcp/.ai/directives/meta/fix_nested_cdata_in_directive.md"
    },
    {
      "name": "orchestrate_general",
      "description": "Create orchestrator and sub-directive pairs for parallel execution (does NOT execute them)",
      "version": "1.3.0",
      "score": 100.0,
      "source": "user",
      "path": "/home/leo/.ai/directives/custom/orchestrate_general.md"
    },
    {
      "name": "create_directive",
      "description": "Create new directives with proper XML structure and validation.",
      "version": "4.0.0",
      "score": 100.0,
      "source": "user",
      "path": "/home/leo/.ai/directives/core/create_directive.md"
    },
    {
      "name": "bootstrap",
      "description": "Bootstrap a project from a plan document - initializes .ai/ structure and creates all directives needed to complete the project via MCP tool calls",
      "version": "1.9.0",
      "score": 100.0,
      "source": "user",
      "path": "/home/leo/.ai/directives/core/bootstrap.md"
    },
    {
      "name": "create_context_loader",
      "description": "Create directives that load knowledge entries into agent context via the unified MCP.",
      "version": "1.2.0",
      "score": 100.0,
      "source": "user",
      "path": "/home/leo/.ai/directives/core/create_context_loader.md"
    }
  ],
  "total": 10,
  "search_type": "keyword"
}
```
```

---

## Assistant (Kiwi-Free-Grokfast · grok-code · 4.5s)

_Thinking:_

The search found "create_directive" directive with high score.


## Investigating search results  
- The search identified the "create_directive" directive with a high relevance score.  
- It's available in both project and user spaces, with version 4.0.0.

```
Tool: kiwi-mcp_load

**Input:**
```json
{
  "item_type": "directive",
  "item_id": "create_directive",
  "source": "project",
  "project_path": "/home/leo/projects/kiwi-mcp"
}
```
**Output:**
```
{
  "name": "create_directive",
  "version": "4.0.0",
  "description": "Create new directives with proper XML structure and validation.",
  "content": "<!-- kiwi-mcp:validated:2026-01-22T21:33:03Z:242a33ed9dd8 -->\n# Create Directive\n\nCreate new directives with proper structure, validate, and generate signature.\n\n```xml\n<directive name=\"create_directive\" version=\"4.0.0\">\n  <metadata>\n    <description>Create new directives with proper XML structure and validation.</description>\n    <category>core</category>\n    <author>kiwi-mcp</author>\n    <model tier=\"general\" fallback=\"reasoning\" parallel=\"false\">\n      Multi-step directive creation with XML generation and validation.\n    </model>\n    <context_budget>\n      <estimated_usage>15%</estimated_usage>\n      <step_count>4</step_count>\n      <spawn_threshold>50%</spawn_threshold>\n    </context_budget>\n    <deviation_rules>\n      <auto_fix>XML syntax errors, missing required fields, formatting</auto_fix>\n      <ask_first>category changes, structural modifications</ask_first>\n      <escalate>conflicting directive names, breaking changes</escalate>\n    </deviation_rules>\n    <permissions>\n      <read resource=\"filesystem\" path=\"**/*\"/>\n      <write resource=\"filesystem\" path=\".ai/directives/**/*.md\"/>\n      <execute resource=\"kiwi-mcp\" action=\"execute\"/>\n      <execute resource=\"kiwi-mcp\" action=\"search\"/>\n    </permissions>\n    <relationships>\n      <requires>directive-creation-pattern</requires>\n      <suggests>edit_directive</suggests>\n      <suggests>sync_directives</suggests>\n      <suggests>anneal_directive</suggests>\n    </relationships>\n  </metadata>\n  <context>\n    <tech_stack>any</tech_stack>\n  </context>\n  <inputs>\n    <input name=\"name\" type=\"string\" required=\"true\">\n      Directive name in snake_case (e.g., \"deploy_app\", \"create_component\")\n    </input>\n    <input name=\"description\" type=\"string\" required=\"true\">\n      What does this directive do? Be specific.\n    </input>\n    <input name=\"category\" type=\"string\" required=\"true\">\n      Category name (e.g., \"core\", \"patterns\", \"workflows\", \"meta\", \"state\").\n      Determines folder: .ai/directives/{category}/\n    </input>\n    <input name=\"subcategory\" type=\"string\" required=\"false\">\n      Optional nested category (e.g., \"api-endpoints\", \"testing\").\n      Creates nested folder: .ai/directives/{category}/{subcategory}/\n    </input>\n    <input name=\"complexity\" type=\"enum\" values=\"simple,moderate,complex,orchestrator\" default=\"moderate\">\n      Complexity determines model tier:\n      - simple: fast tier - file ops, templates, formatting\n      - moderate: balanced tier - standard workflows (default)\n      - complex: reasoning tier - architecture decisions, analysis\n      - orchestrator: reasoning tier with parallel=true, context_budget, deviation_rules\n    </input>\n    <input name=\"enable_orchestration\" type=\"boolean\" default=\"false\">\n      Load orchestration_pattern knowledge entry to provide orchestration patterns and templates.\n      When enabled, creates directives with parallel execution, context budgeting, and deviation handling.\n    </input>\n  </inputs>\n   <process>\n     <step name=\"load_creation_pattern\">\n       <description>Load and follow the directive creation pattern</description>\n       <action><![CDATA[\nCRITICAL: This directive (create_directive) is the ONLY approved way to create directives.\n\nLoad the directive-creation-pattern knowledge entry to understand why:\n\nmcp__kiwi_mcp__load(\n  item_type=\"knowledge\",\n  item_id=\"directive-creation-pattern\",\n  source=\"local\",\n  project_path=\"{project_path}\"\n)\n\nKey rules:\n- NEVER use create_file to manually create directive files\n- ALWAYS use this directive (create_directive)\n- Directives without valid signatures cannot run or publish\n- The handler enforces validation, signing, and registration\n\nIf you are about to use create_file for a .ai/directives/ path, STOP.\n       ]]></action>\n     </step>\n\n     <step name=\"gather_requirements\">\n       <description>Understand what the directive needs</description>\n       <checklist>\n         <item>What problem does it solve?</item>\n         <item>What inputs are required?</item>\n         <item>What are the concrete steps?</item>\n         <item>What does success look like?</item>\n         <item>What complexity level? (simple/moderate/complex/orchestrator)</item>\n         <item>Does it depend on other directives? (relationships.requires)</item>\n         <item>Does it suggest other directives? (relationships.suggests)</item>\n         <item>Does it extend another directive? (relationships.extends)</item>\n         <item>What verification criteria ensure proper completion?</item>\n         <item>What success criteria define measurable outcomes?</item>\n       </checklist>\n     </step>\n\n     <step name=\"load_orchestration_template\">\n       <description>Load orchestration patterns from knowledge if requested</description>\n        <action><![CDATA[\nIf enable_orchestration is true:\n\n1. Load orchestration_pattern knowledge entry:\n\nmcp__kiwi_mcp__load(\n  item_type=\"knowledge\",\n  item_id=\"orchestration_pattern\",\n  source=\"local\",\n  project_path=\"{project_path}\"\n)\n\n2. Extract and apply orchestration patterns:\n   - Parallel execution capabilities (parallel=\"true\")\n   - Context budget management (<context_budget>)\n   - Deviation handling rules (<deviation_rules>)\n   - Subagent spawning patterns\n   - Wave-based execution structure\n   - Checkpoint integration\n\n3. Enhance directive template with orchestration framework:\n   - Add <parallel_capable>true</parallel_capable>\n   - Include <subagent_strategy> and <preferred_subagent>\n   - Add orchestration process steps (parallel tasks, deviation handling, result aggregation)\n\nThis transforms the directive into a full orchestration framework for complex multi-step workflows.\n       ]]></action>\n       <verification>\n         <check>If orchestration enabled: orchestration_pattern knowledge loaded successfully</check>\n         <check>Orchestration patterns applied to template</check>\n       </verification>\n     </step>\n\n\n\n     <step name=\"plan_verification\">\n       <description>Plan verification and success criteria</description>\n       <action><![CDATA[\nPlan verification levels for the directive:\n\nEXISTENCE: Check that required files/artifacts are created\n- Files exist at expected paths\n- Required outputs are present\n\nSUBSTANTIVE: Verify content quality, not just presence\n- No placeholder/stub content (TODO, FIXME, empty functions)\n- Real implementation with business logic\n- Proper error handling and edge cases\n\nWIRING: Check connections between components\n- API calls reach correct endpoints\n- State updates trigger proper re-renders\n- Database queries return expected data\n- External service integrations work\n\nFUNCTIONAL: End-to-end behavior verification\n- Automated tests pass (unit, integration, e2e)\n- Manual verification checklists for complex behaviors\n- Performance meets requirements\n- Security checks pass\n\nInclude <verification> tags in process steps for pre-completion checks.\nInclude <success_criteria> section for overall directive completion.\n       ]]></action>\n     </step>\n\n\n     <step name=\"create_content\">\n       <description>Generate and save the directive file</description>\n       <action><![CDATA[\nIf orchestration mode: Skip this step (handled by orchestration_general)\n\nIf standard mode: Create the directive file at:\n  .ai/directives/{category}/{name}.md\n  (or .ai/directives/{category}/{subcategory}/{name}.md if subcategory provided)\nCreate directories as needed (lazy creation).\n       ]]></action>\n       <template>\n# [NAME]\n[DESCRIPTION]\n```xml\n<directive name=\"[NAME]\" version=\"1.0.0\">\n  <metadata>\n    <description>[DESCRIPTION]</description>\n    <category>[CATEGORY]</category>\n    <author>kiwi-mcp</author>\n    <model tier=\"[TIER]\" fallback=\"[FALLBACK]\" parallel=\"[OPTIONAL_PARALLEL]\" id=\"[OPTIONAL_ID]\">\n      [TIER_EXPLANATION]\n    </model>\n    <!-- ORCHESTRATION ENABLED: Include orchestration framework -->\n    [IF_ORCHESTRATION_ENABLED]\n    <parallel_capable>true</parallel_capable>\n    <subagent_strategy>per-task</subagent_strategy>\n    <preferred_subagent>subagent</preferred_subagent>\n    <context_budget>\n      <estimated_usage>25%</estimated_usage>\n      <step_count>[STEP_COUNT]</step_count>\n      <spawn_threshold>60%</spawn_threshold>\n    </context_budget>\n    <deviation_rules>\n      <auto_fix>XML syntax errors, missing required fields</auto_fix>\n      <ask_first>architectural changes, scope expansion</ask_first>\n      <escalate>breaking changes, security issues</escalate>\n    </deviation_rules>\n    [/IF_ORCHESTRATION_ENABLED]\n    <!-- MANUAL ORCHESTRATOR: Uncomment for complex multi-step workflows -->\n    <!--\n    <context_budget>\n      <estimated_usage>20%</estimated_usage>\n      <step_count>N</step_count>\n      <spawn_threshold>50%</spawn_threshold>\n    </context_budget>\n    <deviation_rules>\n      <auto_fix>what to fix automatically</auto_fix>\n      <ask_first>what needs confirmation</ask_first>\n      <escalate>what to escalate to user</escalate>\n    </deviation_rules>\n    -->\n    <permissions>\n      <read resource=\"filesystem\" path=\"**/*\" />\n      <write resource=\"filesystem\" path=\"**/*\" />\n    </permissions>\n    <relationships>\n      <!-- <requires>directive_name</requires> -->\n      <!-- <suggests>directive_name</suggests> -->\n      <!-- <extends>directive_name</extends> -->\n    </relationships>\n  </metadata>\n  <context>\n    <tech_stack>[TECH_STACK or \"any\"]</tech_stack>\n  </context>\n  <inputs>\n    <input name=\"example\" type=\"string\" required=\"true\">\n      Description of this input\n    </input>\n  </inputs>\n  <process>\n    [IF_ORCHESTRATION_ENABLED]\n    <step name=\"setup_orchestration\">\n      <description>Initialize orchestration framework</description>\n      <action><![CDATA[\nInitialize parallel execution environment:\n1. Load required subagents\n2. Set up context budget monitoring\n3. Configure deviation handling rules\n4. Prepare checkpoint system\n      ]]></action>\n    </step>\n\n    <step name=\"execute_parallel_tasks\" parallel=\"true\">\n      <description>Execute tasks in parallel waves</description>\n      <action><![CDATA[\nSpawn subagents for parallel execution:\nTask(\"Execute: [subtask_directive] with inputs: {inputs}\")\n\nWait for wave completion before proceeding to next wave.\n      ]]></action>\n    </step>\n\n    <step name=\"handle_deviations\">\n      <description>Process any deviations encountered</description>\n      <action><![CDATA[\nCheck for deviations during execution:\n- Auto-fix: Apply automatic corrections\n- Ask-first: Create checkpoints for user decisions\n- Escalate: Handle critical issues\n      ]]></action>\n    </step>\n\n    <step name=\"aggregate_results\">\n      <description>Collect and summarize results</description>\n      <action>Aggregate results from all parallel executions</action>\n    </step>\n    [/IF_ORCHESTRATION_ENABLED]\n\n    <!-- STANDARD PROCESS: Uncomment for regular directives -->\n    <!--\n    <step name=\"step_1\">\n      <description>First step</description>\n      <action>What to do</action>\n      <verification>\n        <check>Verification condition</check>\n        <command>Optional: command to run</command>\n      </verification>\n    </step>\n    -->\n  </process>\n  <success_criteria>\n    <criterion>Measurable success condition</criterion>\n    <criterion>Another completion requirement</criterion>\n  </success_criteria>\n  <outputs>\n    <success>What to report on success</success>\n  </outputs>\n</directive>\n```\n      </template>\n      <tier_guide>\n        MODEL TIERS:\n        - fast: Simple file ops, templates, formatting\n        - balanced: Standard code gen, multi-step workflows (most directives)\n        - reasoning: Complex analysis, architecture decisions\n        - expert: Novel problems, research-level tasks\n        FALLBACK: Higher tier to retry on failure (fast -&gt; balanced -&gt; reasoning -&gt; expert)\n        PARALLEL: Optional - true for orchestrators spawning subagents, false otherwise. Omit if not needed.\n        ID: Optional agent identifier to specify a specific agent for execution\n      </tier_guide>\n       <cdata_note>\n         XML SPECIAL CHARACTERS: Wrap content with special chars in CDATA blocks.\n         Example: action element with CDATA wrapper for shell commands.\n       </cdata_note>\n       <verification_guide>\n         VERIFICATION TAGS: Add &lt;verification&gt; elements to process steps for pre-completion validation.\n\n         Structure:\n         &lt;verification&gt;\n           &lt;check&gt;Human-readable verification condition&lt;/check&gt;\n           &lt;command&gt;Optional: CLI command to run for automated verification&lt;/command&gt;\n           &lt;expect&gt;Optional: Expected result from command&lt;/expect&gt;\n         &lt;/verification&gt;\n\n         Verification levels:\n         - EXISTENCE: Files/artifacts exist\n         - SUBSTANTIVE: Real implementation, not stubs\n         - WIRING: Component connections work\n         - FUNCTIONAL: End-to-end behavior correct\n       </verification_guide>\n       <success_criteria_guide>\n         SUCCESS CRITERIA: Add &lt;success_criteria&gt; section for measurable completion requirements.\n\n         Structure:\n         &lt;success_criteria&gt;\n           &lt;criterion&gt;Specific, measurable success condition&lt;/criterion&gt;\n           &lt;criterion&gt;Another completion requirement&lt;/criterion&gt;\n         &lt;/success_criteria&gt;\n\n         Criteria should be:\n         - Observable: Can be verified through code inspection or testing\n         - Specific: Clear pass/fail conditions\n         - Comprehensive: Cover all aspects of successful completion\n       </success_criteria_guide>\n       <orchestration_guide>\n         ORCHESTRATION: Enable orchestration to create directives with advanced workflow patterns.\n\n         When enable_orchestration=true:\n         - Loads orchestration_pattern knowledge entry\n         - Adds parallel execution capabilities\n         - Includes context budget management\n         - Provides deviation handling framework\n         - Enables subagent orchestration\n         - Supports checkpoint-based human interaction\n\n         Orchestration features:\n         - parallel=\"true\" for concurrent task execution\n         - context_budget for memory management\n         - deviation_rules for error handling\n         - subagent spawning for complex workflows\n         - checkpoint integration for user interaction\n\n         Use for complex multi-step workflows that benefit from parallel execution and sophisticated error handling.\n       </orchestration_guide>\n    </step>\n     <step name=\"validate_and_sign\">\n       <description>Validate XML and generate signature hash</description>\n       <action><![CDATA[\nIf orchestration mode: Skip this step (handled by orchestration_general)\n\nIf standard mode: CRITICAL: After saving the file, run the create action to validate and sign:\nmcp__kiwi_mcp__execute(\n  item_type=\"directive\",\n  action=\"create\",\n  item_id=\"{name}\",\n  parameters={\n    \"category\": \"{category}\",\n    \"location\": \"project\"\n  },\n  project_path=\"{project_path}\"\n)\nThis validates:\n1. XML parses without errors\n2. Required metadata fields present\n3. Generates validation signature hash\n4. Updates file with signature comment\nIf validation fails, fix errors and re-run create action.\n       ]]></action>\n      <verify>\n        <check>File has signature comment at top</check>\n        <check>No XML parse errors</check>\n        <on_failure>Fix XML syntax and re-run create action</on_failure>\n      </verify>\n    </step>\n    <step name=\"confirm_discoverable\">\n      <description>Confirm directive is searchable</description>\n      <action>\nVerify the directive is now discoverable:\nmcp__kiwi_mcp__search(\n  item_type=\"directive\",\n  query=\"{name}\",\n  source=\"local\",\n  project_path=\"{project_path}\"\n)\nShould return the new directive with correct version.\n      </action>\n    </step>\n  </process>\n   <outputs>\n     <success><![CDATA[\n\u2713 Created directive: {name}\nLocation: .ai/directives/{category}/{name}.md\nVersion: 1.0.0\nMode: {orchestration ? \"orchestration\" : \"standard\"}\n\nNext steps:\n- Test: run directive {name}\n- Edit: edit directive {name}\n- Sync: sync directives\n{if orchestration}\n- Orchestration used: orchestration_general directive handled complex patterns\n{/if}\n     ]]></success>\n    <failure>\n\u2717 Failed to create directive: {name}\nError: {error}\nCommon fixes:\n- Escape XML special characters with CDATA\n- Check for mismatched tags\n- Verify required fields are present\n    </failure>\n  </outputs>\n</directive>\n```\n",
  "parsed": {
    "_attrs": {
      "name": "create_directive",
      "version": "4.0.0"
    },
    "metadata": {
      "description": "Create new directives with proper XML structure and validation.",
      "category": "core",
      "author": "kiwi-mcp",
      "model": {
        "_text": "Multi-step directive creation with XML generation and validation.",
        "_attrs": {
          "tier": "general",
          "fallback": "reasoning",
          "parallel": "false"
        }
      },
      "context_budget": {
        "estimated_usage": "15%",
        "step_count": "4",
        "spawn_threshold": "50%"
      },
      "deviation_rules": {
        "auto_fix": "XML syntax errors, missing required fields, formatting",
        "ask_first": "category changes, structural modifications",
        "escalate": "conflicting directive names, breaking changes"
      },
      "permissions": {
        "read": {
          "_attrs": {
            "resource": "filesystem",
            "path": "**/*"
          }
        },
        "write": {
          "_attrs": {
            "resource": "filesystem",
            "path": ".ai/directives/**/*.md"
          }
        },
        "execute": [
          {
            "_attrs": {
              "resource": "kiwi-mcp",
              "action": "execute"
            }
          },
          {
            "_attrs": {
              "resource": "kiwi-mcp",
              "action": "search"
            }
          }
        ]
      },
      "relationships": {
        "requires": "directive-creation-pattern",
        "suggests": [
          "edit_directive",
          "sync_directives",
          "anneal_directive"
        ]
      }
    },
    "context": {
      "tech_stack": "any"
    },
    "inputs": {
      "input": [
        {
          "_text": "Directive name in snake_case (e.g., \"deploy_app\", \"create_component\")",
          "_attrs": {
            "name": "name",
            "type": "string",
            "required": "true"
          }
        },
        {
          "_text": "What does this directive do? Be specific.",
          "_attrs": {
            "name": "description",
            "type": "string",
            "required": "true"
          }
        },
        {
          "_text": "Category name (e.g., \"core\", \"patterns\", \"workflows\", \"meta\", \"state\").\n      Determines folder: .ai/directives/{category}/",
          "_attrs": {
            "name": "category",
            "type": "string",
            "required": "true"
          }
        },
        {
          "_text": "Optional nested category (e.g., \"api-endpoints\", \"testing\").\n      Creates nested folder: .ai/directives/{category}/{subcategory}/",
          "_attrs": {
            "name": "subcategory",
            "type": "string",
            "required": "false"
          }
        },
        {
          "_text": "Complexity determines model tier:\n      - simple: fast tier - file ops, templates, formatting\n      - moderate: balanced tier - standard workflows (default)\n      - complex: reasoning tier - architecture decisions, analysis\n      - orchestrator: reasoning tier with parallel=true, context_budget, deviation_rules",
          "_attrs": {
            "name": "complexity",
            "type": "enum",
            "values": "simple,moderate,complex,orchestrator",
            "default": "moderate"
          }
        },
        {
          "_text": "Load orchestration_pattern knowledge entry to provide orchestration patterns and templates.\n      When enabled, creates directives with parallel execution, context budgeting, and deviation handling.",
          "_attrs": {
            "name": "enable_orchestration",
            "type": "boolean",
            "default": "false"
          }
        }
      ]
    },
    "process": {
      "step": [
        {
          "_attrs": {
            "name": "load_creation_pattern"
          },
          "description": "Load and follow the directive creation pattern",
          "action": "CRITICAL: This directive (create_directive) is the ONLY approved way to create directives.\n\nLoad the directive-creation-pattern knowledge entry to understand why:\n\nmcp__kiwi_mcp__load(\n  item_type=\"knowledge\",\n  item_id=\"directive-creation-pattern\",\n  source=\"local\",\n  project_path=\"{project_path}\"\n)\n\nKey rules:\n- NEVER use create_file to manually create directive files\n- ALWAYS use this directive (create_directive)\n- Directives without valid signatures cannot run or publish\n- The handler enforces validation, signing, and registration\n\nIf you are about to use create_file for a .ai/directives/ path, STOP."
        },
        {
          "_attrs": {
            "name": "gather_requirements"
          },
          "description": "Understand what the directive needs",
          "checklist": {
            "item": [
              "What problem does it solve?",
              "What inputs are required?",
              "What are the concrete steps?",
              "What does success look like?",
              "What complexity level? (simple/moderate/complex/orchestrator)",
              "Does it depend on other directives? (relationships.requires)",
              "Does it suggest other directives? (relationships.suggests)",
              "Does it extend another directive? (relationships.extends)",
              "What verification criteria ensure proper completion?",
              "What success criteria define measurable outcomes?"
            ]
          }
        },
        {
          "_attrs": {
            "name": "load_orchestration_template"
          },
          "description": "Load orchestration patterns from knowledge if requested",
          "action": "If enable_orchestration is true:\n\n1. Load orchestration_pattern knowledge entry:\n\nmcp__kiwi_mcp__load(\n  item_type=\"knowledge\",\n  item_id=\"orchestration_pattern\",\n  source=\"local\",\n  project_path=\"{project_path}\"\n)\n\n2. Extract and apply orchestration patterns:\n   - Parallel execution capabilities (parallel=\"true\")\n   - Context budget management (<context_budget>)\n   - Deviation handling rules (<deviation_rules>)\n   - Subagent spawning patterns\n   - Wave-based execution structure\n   - Checkpoint integration\n\n3. Enhance directive template with orchestration framework:\n   - Add <parallel_capable>true</parallel_capable>\n   - Include <subagent_strategy> and <preferred_subagent>\n   - Add orchestration process steps (parallel tasks, deviation handling, result aggregation)\n\nThis transforms the directive into a full orchestration framework for complex multi-step workflows.",
          "verification": {
            "check": [
              "If orchestration enabled: orchestration_pattern knowledge loaded successfully",
              "Orchestration patterns applied to template"
            ]
          }
        },
        {
          "_attrs": {
            "name": "plan_verification"
          },
          "description": "Plan verification and success criteria",
          "action": "Plan verification levels for the directive:\n\nEXISTENCE: Check that required files/artifacts are created\n- Files exist at expected paths\n- Required outputs are present\n\nSUBSTANTIVE: Verify content quality, not just presence\n- No placeholder/stub content (TODO, FIXME, empty functions)\n- Real implementation with business logic\n- Proper error handling and edge cases\n\nWIRING: Check connections between components\n- API calls reach correct endpoints\n- State updates trigger proper re-renders\n- Database queries return expected data\n- External service integrations work\n\nFUNCTIONAL: End-to-end behavior verification\n- Automated tests pass (unit, integration, e2e)\n- Manual verification checklists for complex behaviors\n- Performance meets requirements\n- Security checks pass\n\nInclude <verification> tags in process steps for pre-completion checks.\nInclude <success_criteria> section for overall directive completion."
        },
        {
          "_attrs": {
            "name": "create_content"
          },
          "description": "Generate and save the directive file",
          "action": "If orchestration mode: Skip this step (handled by orchestration_general)\n\nIf standard mode: Create the directive file at:\n  .ai/directives/{category}/{name}.md\n  (or .ai/directives/{category}/{subcategory}/{name}.md if subcategory provided)\nCreate directories as needed (lazy creation).",
          "template": {
            "_text": "# [NAME]\n[DESCRIPTION]\n```xml",
            "directive": {
              "_attrs": {
                "name": "[NAME]",
                "version": "1.0.0"
              },
              "metadata": {
                "description": "[DESCRIPTION]",
                "category": "[CATEGORY]",
                "author": "kiwi-mcp",
                "model": {
                  "_text": "[TIER_EXPLANATION]",
                  "_attrs": {
                    "tier": "[TIER]",
                    "fallback": "[FALLBACK]",
                    "parallel": "[OPTIONAL_PARALLEL]",
                    "id": "[OPTIONAL_ID]"
                  }
                },
                "parallel_capable": "true",
                "subagent_strategy": "per-task",
                "preferred_subagent": "subagent",
                "context_budget": {
                  "estimated_usage": "25%",
                  "step_count": "[STEP_COUNT]",
                  "spawn_threshold": "60%"
                },
                "deviation_rules": {
                  "auto_fix": "XML syntax errors, missing required fields",
                  "ask_first": "architectural changes, scope expansion",
                  "escalate": "breaking changes, security issues"
                },
                "permissions": {
                  "read": {
                    "_attrs": {
                      "resource": "filesystem",
                      "path": "**/*"
                    }
                  },
                  "write": {
                    "_attrs": {
                      "resource": "filesystem",
                      "path": "**/*"
                    }
                  }
                },
                "relationships": {}
              },
              "context": {
                "tech_stack": "[TECH_STACK or \"any\"]"
              },
              "inputs": {
                "input": {
                  "_text": "Description of this input",
                  "_attrs": {
                    "name": "example",
                    "type": "string",
                    "required": "true"
                  }
                }
              },
              "process": {
                "_text": "[IF_ORCHESTRATION_ENABLED]",
                "step": [
                  {
                    "_attrs": {
                      "name": "setup_orchestration"
                    },
                    "description": "Initialize orchestration framework",
                    "action": "Initialize parallel execution environment:\n1. Load required subagents\n2. Set up context budget monitoring\n3. Configure deviation handling rules\n4. Prepare checkpoint system"
                  },
                  {
                    "_attrs": {
                      "name": "execute_parallel_tasks",
                      "parallel": "true"
                    },
                    "description": "Execute tasks in parallel waves",
                    "action": "Spawn subagents for parallel execution:\nTask(\"Execute: [subtask_directive] with inputs: {inputs}\")\n\nWait for wave completion before proceeding to next wave."
                  },
                  {
                    "_attrs": {
                      "name": "handle_deviations"
                    },
                    "description": "Process any deviations encountered",
                    "action": "Check for deviations during execution:\n- Auto-fix: Apply automatic corrections\n- Ask-first: Create checkpoints for user decisions\n- Escalate: Handle critical issues"
                  },
                  {
                    "_attrs": {
                      "name": "aggregate_results"
                    },
                    "description": "Collect and summarize results",
                    "action": "Aggregate results from all parallel executions"
                  }
                ]
              },
              "success_criteria": {
                "criterion": [
                  "Measurable success condition",
                  "Another completion requirement"
                ]
              },
              "outputs": {
                "success": "What to report on success"
              }
            }
          },
          "tier_guide": "MODEL TIERS:\n        - fast: Simple file ops, templates, formatting\n        - balanced: Standard code gen, multi-step workflows (most directives)\n        - reasoning: Complex analysis, architecture decisions\n        - expert: Novel problems, research-level tasks\n        FALLBACK: Higher tier to retry on failure (fast -> balanced -> reasoning -> expert)\n        PARALLEL: Optional - true for orchestrators spawning subagents, false otherwise. Omit if not needed.\n        ID: Optional agent identifier to specify a specific agent for execution",
          "cdata_note": "XML SPECIAL CHARACTERS: Wrap content with special chars in CDATA blocks.\n         Example: action element with CDATA wrapper for shell commands.",
          "verification_guide": "VERIFICATION TAGS: Add <verification> elements to process steps for pre-completion validation.\n\n         Structure:\n         <verification>\n           <check>Human-readable verification condition</check>\n           <command>Optional: CLI command to run for automated verification</command>\n           <expect>Optional: Expected result from command</expect>\n         </verification>\n\n         Verification levels:\n         - EXISTENCE: Files/artifacts exist\n         - SUBSTANTIVE: Real implementation, not stubs\n         - WIRING: Component connections work\n         - FUNCTIONAL: End-to-end behavior correct",
          "success_criteria_guide": "SUCCESS CRITERIA: Add <success_criteria> section for measurable completion requirements.\n\n         Structure:\n         <success_criteria>\n           <criterion>Specific, measurable success condition</criterion>\n           <criterion>Another completion requirement</criterion>\n         </success_criteria>\n\n         Criteria should be:\n         - Observable: Can be verified through code inspection or testing\n         - Specific: Clear pass/fail conditions\n         - Comprehensive: Cover all aspects of successful completion",
          "orchestration_guide": "ORCHESTRATION: Enable orchestration to create directives with advanced workflow patterns.\n\n         When enable_orchestration=true:\n         - Loads orchestration_pattern knowledge entry\n         - Adds parallel execution capabilities\n         - Includes context budget management\n         - Provides deviation handling framework\n         - Enables subagent orchestration\n         - Supports checkpoint-based human interaction\n\n         Orchestration features:\n         - parallel=\"true\" for concurrent task execution\n         - context_budget for memory management\n         - deviation_rules for error handling\n         - subagent spawning for complex workflows\n         - checkpoint integration for user interaction\n\n         Use for complex multi-step workflows that benefit from parallel execution and sophisticated error handling."
        },
        {
          "_attrs": {
            "name": "validate_and_sign"
          },
          "description": "Validate XML and generate signature hash",
          "action": "If orchestration mode: Skip this step (handled by orchestration_general)\n\nIf standard mode: CRITICAL: After saving the file, run the create action to validate and sign:\nmcp__kiwi_mcp__execute(\n  item_type=\"directive\",\n  action=\"create\",\n  item_id=\"{name}\",\n  parameters={\n    \"category\": \"{category}\",\n    \"location\": \"project\"\n  },\n  project_path=\"{project_path}\"\n)\nThis validates:\n1. XML parses without errors\n2. Required metadata fields present\n3. Generates validation signature hash\n4. Updates file with signature comment\nIf validation fails, fix errors and re-run create action.",
          "verify": {
            "check": [
              "File has signature comment at top",
              "No XML parse errors"
            ],
            "on_failure": "Fix XML syntax and re-run create action"
          }
        },
        {
          "_attrs": {
            "name": "confirm_discoverable"
          },
          "description": "Confirm directive is searchable",
          "action": "Verify the directive is now discoverable:\nmcp__kiwi_mcp__search(\n  item_type=\"directive\",\n  query=\"{name}\",\n  source=\"local\",\n  project_path=\"{project_path}\"\n)\nShould return the new directive with correct version."
        }
      ]
    },
    "outputs": {
      "success": "\u2713 Created directive: {name}\nLocation: .ai/directives/{category}/{name}.md\nVersion: 1.0.0\nMode: {orchestration ? \"orchestration\" : \"standard\"}\n\nNext steps:\n- Test: run directive {name}\n- Edit: edit directive {name}\n- Sync: sync directives\n{if orchestration}\n- Orchestration used: orchestration_general directive handled complex patterns\n{/if}",
      "failure": "\u2717 Failed to create directive: {name}\nError: {error}\nCommon fixes:\n- Escape XML special characters with CDATA\n- Check for mismatched tags\n- Verify required fields are present"
    }
  },
  "permissions": [
    {
      "tag": "read",
      "attrs": {
        "resource": "filesystem",
        "path": "**/*"
      }
    },
    {
      "tag": "write",
      "attrs": {
        "resource": "filesystem",
        "path": ".ai/directives/**/*.md"
      }
    },
    {
      "tag": "execute",
      "attrs": {
        "resource": "kiwi-mcp",
        "action": "execute"
      }
    },
    {
      "tag": "execute",
      "attrs": {
        "resource": "kiwi-mcp",
        "action": "search"
      }
    }
  ],
  "model": {
    "tier": "general",
    "fallback": "reasoning",
    "parallel": "false",
    "id": null,
    "reasoning": "Multi-step directive creation with XML generation and validation."
  },
  "relationships": {
    "requires": [
      "directive-creation-pattern"
    ],
    "suggests": [
      "edit_directive",
      "sync_directives",
      "anneal_directive"
    ]
  },
  "category": "core",
  "source": "project",
  "path": "/home/leo/projects/kiwi-mcp/.ai/directives/core/create_directive.md",
  "mode": "read_only"
}
```
```

---

## Assistant (Kiwi-Free-Grokfast · grok-code · 14.8s)

_Thinking:_

The directive is loaded. It's the create_directive directive itself.


## Interpreting user request  
- The user mentioned "kiwi-mcp run execute action create on create_directive," indicating a specific command.  
- This suggests they want to execute an action related to creating a directive using the kiwi-mcp system.  
- The phrasing aligns with running a tool, likely kiwi-mcp_execute, to process the create_directive action.

## Interpreting user request  
- The user's command includes "run execute action create on create_directive," suggesting they want to use kiwi-mcp_execute with action="create" and item_id="create_directive."  
- This implies creating a directive named "create_directive," though it seems to already exist, possibly for testing or recreation.  
- The phrasing "run execute" may be a misphrased attempt to run the create_directive directive, but no additional inputs like name, description, or category were provided.

```
Tool: kiwi-mcp_search

**Input:**
```json
{
  "item_type": "directive",
  "query": "execute action create",
  "source": "all",
  "project_path": "/home/leo/projects/kiwi-mcp"
}
```
**Output:**
```
{
  "query": "execute action create",
  "source": "all",
  "results": [
    {
      "name": "demo_complex_orchestration",
      "description": "Demonstrates complex orchestration of Kiwi MCP tools working together: search \u2192 load \u2192 execute \u2192 create \u2192 publish \u2192 knowledge capture",
      "version": "1.0.0",
      "score": 33.33333333333333,
      "source": "project",
      "path": "/home/leo/projects/kiwi-mcp/.ai/directives/demos/demo_complex_orchestration.md"
    },
    {
      "name": "checkpoint",
      "description": "Create a checkpoint for human interaction",
      "version": "1.0.0",
      "score": 33.33333333333333,
      "source": "project",
      "path": "/home/leo/projects/kiwi-mcp/.ai/directives/state/checkpoint.md"
    },
    {
      "name": "orchestrate_harness_phase_1",
      "description": "Execute Phase 1: Tool Foundation - rename scripts to tools, add executor abstraction",
      "version": "1.0.1",
      "score": 33.33333333333333,
      "source": "project",
      "path": "/home/leo/projects/kiwi-mcp/.ai/directives/harness/orchestrate_harness_phase_1.md"
    },
    {
      "name": "orchestrate_general",
      "description": "Create orchestrator directive for parallel execution of a specific directive across multiple targets (does NOT execute them)",
      "version": "1.4.0",
      "score": 33.33333333333333,
      "source": "project",
      "path": "/home/leo/projects/kiwi-mcp/.ai/directives/meta/orchestrate_general.md"
    },
    {
      "name": "fix_nested_cdata_in_directive",
      "description": "Fix nested CDATA errors in directives that fail kiwi-mcp execute create validation",
      "version": "1.0.0",
      "score": 33.33333333333333,
      "source": "project",
      "path": "/home/leo/projects/kiwi-mcp/.ai/directives/meta/fix_nested_cdata_in_directive.md"
    },
    {
      "name": "orchestrate_general",
      "description": "Create orchestrator and sub-directive pairs for parallel execution (does NOT execute them)",
      "version": "1.3.0",
      "score": 33.33333333333333,
      "source": "user",
      "path": "/home/leo/.ai/directives/custom/orchestrate_general.md"
    },
    {
      "name": "checkpoint",
      "description": "Create a checkpoint for human interaction",
      "version": "1.0.0",
      "score": 33.33333333333333,
      "source": "user",
      "path": "/home/leo/.ai/directives/state/checkpoint.md"
    },
    {
      "name": "orchestrate_general",
      "description": "Create orchestrator and sub-directive pairs for parallel execution (does NOT execute them)",
      "version": "1.3.0",
      "score": 33.33333333333333,
      "source": "user",
      "path": "/home/leo/.ai/directives/meta/orchestrate_general.md"
    },
    {
      "name": "create_tool_registry_tests",
      "description": "Create comprehensive test suite for ToolRegistry covering search, get, publish, delete, and chain resolution",
      "version": "1.0.0",
      "score": 16.666666666666664,
      "source": "project",
      "path": "/home/leo/projects/kiwi-mcp/.ai/directives/implementation/create_tool_registry_tests.md"
    },
    {
      "name": "create_git_checkpoint",
      "description": "Create git checkpoints (commits) after state-mutating tool executions for easy rollback",
      "version": "1.0.0",
      "score": 16.666666666666664,
      "source": "project",
      "path": "/home/leo/projects/kiwi-mcp/.ai/directives/implementation/create_git_checkpoint.md"
    }
  ],
  "total": 10,
  "search_type": "keyword"
}
```
```

---

## Assistant (Kiwi-Free-Grokfast · grok-code · 6.9s)

---

