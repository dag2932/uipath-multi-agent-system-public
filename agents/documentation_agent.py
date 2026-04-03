import os
from state import AgentState
from utils import extract_json_object, load_system_prompt, build_reasoning_context, invoke_llm_json
from config import get_model, get_api_key, is_llm_first, is_llm_required

# LLM will be initialized on-demand when needed
llm = None

def _get_llm():
    """Lazy initialization of LLM with current config"""
    global llm
    if llm is not None:
        return llm
    
    api_key = get_api_key()
    if api_key:
        try:
            from langchain_openai import ChatOpenAI
            model = get_model()
            llm = ChatOpenAI(model=model, api_key=api_key, temperature=0.7)
        except Exception as e:
            print(f"Warning: Could not initialize LLM: {e}")
    return llm


def _infer_scope(reqs: dict) -> str:
    systems = reqs.get('systems', [])
    if systems:
        return f"Automation across {', '.join(systems)}"
    return "Automation of the described business process"


def _build_functional_overview(reqs: dict) -> list[str]:
    overview = ["- Reads the required source data for the process"]

    if reqs.get('business_rules'):
        overview.append("- Applies the identified business rules to each relevant record")
    if reqs.get('inputs_outputs', {}).get('outputs'):
        overview.append("- Produces the expected business outputs or status updates")
    if reqs.get('exceptions'):
        overview.append("- Handles known exception scenarios without stopping the entire run")
    if reqs.get('assumptions'):
        overview.append("- Relies on the documented assumptions and integration prerequisites")

    return overview


def _build_integration_points(reqs: dict) -> list[str]:
    systems = reqs.get('systems', [])
    if not systems:
        return ["- Primary business system or data source", "- Downstream target system or communication channel"]
    return [f"- **{system}**" for system in systems]


def _build_metrics(reqs: dict) -> list[str]:
    metrics = ["- Execution success rate", "- Exception count", "- End-to-end runtime"]
    outputs = reqs.get('inputs_outputs', {}).get('outputs', [])
    if outputs:
        metrics.append(f"- Output completion: {outputs[0]}")
    return metrics

def documentation_agent(state):
    if not isinstance(state, AgentState):
        state = AgentState(**state)

    # Load and use system prompt
    system_prompt = load_system_prompt('documentation')
    state.agent_context['documentation_system_prompt'] = system_prompt

    phase_context = state.get_phase_context('documentation')
    if phase_context:
        print(f"[Documentation context override] {phase_context}\n")

    print("Mia Wallace: Generating comprehensive documentation...\n")

    # Apply skill context to documentation task
    if state.skill_context:
        print("[Skill context loaded from uipath-rpa-workflows/SKILL.md used to establish structure and principles.]")

    reqs = state.requirements or {}
    design = state.solution_design or {}
    build_artifacts = state.build_artifacts or {}
    handover_build = state.lifecycle_handover.get("build_to_documentation", {})
    if handover_build:
        build_artifacts = {
            **build_artifacts,
            "project_dir": handover_build.get("project_dir", build_artifacts.get("project_dir", "outputs/uipath_project")),
            "files": handover_build.get("files", build_artifacts.get("files", [])),
            "generated_workflows": handover_build.get("generated_workflows", build_artifacts.get("generated_workflows", [])),
            "workflow_type": handover_build.get("workflow_type", build_artifacts.get("workflow_type", "RPA (XAML)")),
        }
    build_quality = state.stage_quality_checks.get('build', {})
    design_quality = state.stage_quality_checks.get('design', {})
    generated_workflows = build_artifacts.get('generated_workflows', [])
    generated_workflow_lines = [
        f"- {workflow.get('file_name', 'unknown')}: {workflow.get('purpose', 'Generated step')}"
        for workflow in generated_workflows
    ]
    process_overview = reqs.get('process_overview', 'Unknown')
    functional_overview = _build_functional_overview(reqs)
    integration_points = _build_integration_points(reqs)
    metrics = _build_metrics(reqs)
    llm_doc_notes = ""

    llm_instance = _get_llm()
    if is_llm_required() and not llm_instance:
        raise RuntimeError("LLM_REQUIRED=true but no LLM client could be initialized.")

    if llm_instance:
        print("Mia Wallace: Running LLM-assisted documentation enhancement...\n")
        try:
            reasoning_context = build_reasoning_context(
                state,
                stage="documentation",
                extra={
                    "generated_workflows": generated_workflow_lines,
                    "build_handover": handover_build,
                    "build_quality": build_quality,
                    "design_quality": design_quality,
                },
            )
            llm_prompt = f"""Return a JSON object only.

Schema:
{{
  "functional_overview": ["string"],
  "business_value": ["string"],
  "integration_points": ["string"],
  "prerequisites": ["string"],
  "configuration_settings": ["string"],
  "metrics": ["string"],
  "common_issues": [{{"issue":"string","cause":"string","solution":"string"}}],
  "future_enhancements": ["string"],
  "llm_doc_notes": ["string"]
}}

Reasoning context packet (JSON):
{reasoning_context}
"""
            structured = invoke_llm_json(llm_instance, system_prompt, llm_prompt)
            if structured:
                functional_overview = structured.get("functional_overview") or functional_overview
                business_value = structured.get("business_value") or [
                    "Reduces manual effort for the described process",
                    "Improves consistency and traceability",
                    "Creates a repeatable operational flow",
                    "Provides a basis for monitoring and optimization",
                ]
                integration_points = structured.get("integration_points") or integration_points
                prerequisites = structured.get("prerequisites") or [
                    "Source system credentials configured in Orchestrator",
                    "Target system or communication credentials configured in Orchestrator",
                    "Network access from the robot to all required endpoints",
                    "Test data available for validation",
                ]
                configuration_settings = structured.get("configuration_settings") or [
                    "InputSource: Main data source or endpoint",
                    "OutputTarget: Destination system, mailbox, or storage target",
                    "BusinessRuleParameters: Thresholds, filters, or configurable limits",
                    "ExecutionMode: Scheduled or on-demand",
                ]
                metrics = structured.get("metrics") or metrics
                common_issues = structured.get("common_issues") or []
                future_enhancements = structured.get("future_enhancements") or [
                    "Add richer retry and recovery behavior",
                    "Add downstream integration or ticketing hooks",
                    "Add configurable templates for user-facing outputs",
                    "Add analytics or dashboard reporting",
                ]
                llm_doc_notes = structured.get("llm_doc_notes", [])
                print("✓ LLM enhancement applied in documentation phase.\n")
            else:
                common_issues = []
                business_value = [
                    "Reduces manual effort for the described process",
                    "Improves consistency and traceability",
                    "Creates a repeatable operational flow",
                    "Provides a basis for monitoring and optimization",
                ]
                prerequisites = [
                    "Source system credentials configured in Orchestrator",
                    "Target system or communication credentials configured in Orchestrator",
                    "Network access from the robot to all required endpoints",
                    "Test data available for validation",
                ]
                configuration_settings = [
                    "InputSource: Main data source or endpoint",
                    "OutputTarget: Destination system, mailbox, or storage target",
                    "BusinessRuleParameters: Thresholds, filters, or configurable limits",
                    "ExecutionMode: Scheduled or on-demand",
                ]
                future_enhancements = ["LLM response was not parseable JSON; default documentation strategy retained."]
                llm_doc_notes = ["LLM response was not parseable JSON; fallback content used."]
                print("✓ LLM notes captured in documentation phase.\n")
        except Exception as e:
            print(f"Note: Documentation LLM enhancement skipped ({e})\n")
    else:
        if is_llm_first():
            print("⚠ LLM-first mode active but LLM unavailable. Using deterministic documentation templates.\n")
        else:
            print("Note: Documentation phase running without LLM enhancement.\n")

    if 'business_value' not in locals():
        business_value = [
            "Reduces manual effort for the described process",
            "Improves consistency and traceability",
            "Creates a repeatable operational flow",
            "Provides a basis for monitoring and optimization",
        ]
    if 'prerequisites' not in locals():
        prerequisites = [
            "Source system credentials configured in Orchestrator",
            "Target system or communication credentials configured in Orchestrator",
            "Network access from the robot to all required endpoints",
            "Test data available for validation",
        ]
    if 'configuration_settings' not in locals():
        configuration_settings = [
            "InputSource: Main data source or endpoint",
            "OutputTarget: Destination system, mailbox, or storage target",
            "BusinessRuleParameters: Thresholds, filters, or configurable limits",
            "ExecutionMode: Scheduled or on-demand",
        ]
    if 'common_issues' not in locals():
        common_issues = []
    if 'future_enhancements' not in locals():
        future_enhancements = [
            "Add richer retry and recovery behavior",
            "Add downstream integration or ticketing hooks",
            "Add configurable templates for user-facing outputs",
            "Add analytics or dashboard reporting",
        ]

    if common_issues:
        common_issues_table = chr(10).join(
            f"| {item['issue']} | {item['cause']} | {item['solution']} |"
            for item in common_issues
        )
    else:
        common_issues_table = "\n".join([
            "| Integration call fails | Credentials, network, or endpoint issue | Verify configuration and connectivity |",
            "| Missing business data | Field mapping or source extract is incomplete | Validate the source schema and mappings |",
            "| No records selected | Filters or business rules are too restrictive | Review configuration and filter criteria |",
            "| Execution timeout | Volume is too high for the current design | Optimize processing or split the workload |",
        ])
    
    doc_content = f"""# Automation Documentation

## Executive Summary
**Process**: {process_overview[:150]}

**Architecture**: {design.get('architecture', 'Coded Workflow')}

**Scope**: {_infer_scope(reqs)}

---

## 1. Functional Overview

### What This Automation Does
{chr(10).join(functional_overview)}

### Business Value
{chr(10).join(f'- {item}' for item in business_value)}

---

## 2. System Interactions

### Input Systems
{chr(10).join(f'- {s}' for s in reqs.get('systems', []))}

### Integration Points
{chr(10).join(integration_points)}

### Process Flow
```
1. Read source data from the input system
   ↓
2. Apply the required business rules and validations
   ↓
3. Process each relevant record
    - Validate required fields
    - Execute the business action or skip with logging
   ↓
4. Log results: success count, failures, skipped
   ↓
5. Publish or store outputs as required
```

### Generated Workflow Set
{chr(10).join(generated_workflow_lines) if generated_workflow_lines else '- No workflow metadata available in state'}

---

## 3. Technical Overview

### Technology Stack
- **Platform**: UiPath Cloud / On-Premises
- **Language**: C# (Coded Workflow)
- **Key Activities**: 
  - System.LogMessage (logging)
    - Integration activities for source and target systems
    - Data transformation and validation activities

### Architecture Rationale
- **Why Coded Workflow**: Suitable for structured orchestration, integration, and maintainable custom logic
- **Why NOT REFramework**: Only use it if the final process needs transaction state management or queue orchestration
- **Why NOT Dispatcher/Performer**: Only use it if throughput or queue-based scaling becomes necessary

### Error Handling Strategy
- **Business Exceptions** → log the item and continue when safe
- **Transient Errors** → retry according to the agreed policy
- **Critical Errors** → stop the run and alert the support owner

---

## 4. Deployment & Operations

### Prerequisites
{chr(10).join(f'- [ ] {item}' for item in prerequisites)}

### Installation Steps
1. Open project in UiPath Studio 2023.10+
2. Configure credentials in Orchestrator
3. Set process-specific configuration values
4. Test with representative business data
5. Deploy to production and schedule

### Configuration Settings
{chr(10).join(f'- {item}' for item in configuration_settings)}

### Scheduling
- **Recommended Frequency**: {reqs.get('trigger', 'Per business requirement')}
- **Run Window**: Off-peak hours where possible
- **Retry Policy**: Up to 3 retries on transient failures

---

## 5. Monitoring & Troubleshooting

### Logging
All operations logged with timestamps:
- Processing counts (success, skipped, failed)
- Integration call results
- Business action confirmations
- Error details

### Key Metrics to Monitor
{chr(10).join(metrics)}

### Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
{common_issues_table}

---

## 6. Maintenance & Support

### Regular Maintenance
- [ ] Review logs weekly for anomalies
- [ ] Verify source and target integrations weekly
- [ ] Check service or API limits monthly
- [ ] Update documentation of any config changes

### Known Limitations
- Single execution model unless parallelization is explicitly designed
- Final output depends on the quality of source data and integration contracts
- No human approval workflow

### Future Enhancements
{chr(10).join(f'- {item}' for item in future_enhancements)}

---

## 7. Support & Escalation

**Support Contact**: automation-team@company.com
**On-Call**: See escalation policy
**Documentation**: This file + CONFIG_GUIDE.md in project folder

### Raising Issues
- Include logs from Orchestrator
- Note exact error message
- Provide data sample (anonymized)
- Expected vs actual behavior
"""

    if llm_doc_notes:
        doc_content += "\n## LLM Documentation Improvements\n"
        doc_content += chr(10).join(
            item if str(item).startswith("-") else f"- {item}"
            for item in llm_doc_notes
        )
        doc_content += "\n"

    with open("outputs/04_documentation.md", "w") as f:
        f.write(doc_content)

    state.documentation = doc_content
    state.documentation_briefing = {
        'workflow_count': len(generated_workflows),
        'upstream_build_issues': build_quality.get('issues', []),
        'upstream_design_issues': design_quality.get('issues', []),
    }

    # Handover package for final quality stage.
    state.lifecycle_handover["documentation_to_quality"] = {
        'documentation_length': len(doc_content),
        'generated_workflows': generated_workflows,
        'upstream_build_issues': build_quality.get('issues', []),
        'upstream_design_issues': design_quality.get('issues', []),
        'quality_focus': [
            'architecture consistency',
            'generated workflow completeness',
            'operational readiness',
            'testing and monitoring coverage'
        ],
        'reasoning_context_packet': build_reasoning_context(state, stage='documentation_handover')
    }
    print("✓ Generated: 04_documentation.md (with process flow, troubleshooting, and maintenance guide)")
    print()

    return state.model_dump()


def documentation_briefing_agent(state):
    if not isinstance(state, AgentState):
        state = AgentState(**state)

    content = state.documentation or ''
    design_struct = state.solution_design or {}

    structured = {
        'architecture': design_struct.get('architecture', 'unknown'),
        'process_summary': state.requirements.get('briefing_structured', {}).get('process_summary', '') if state.requirements else '',
        'systems': state.requirements.get('briefing_structured', {}).get('systems', []) if state.requirements else [],
        'key_points': [
            'Process flow',
            'Error handling strategy',
            'Scheduling',
            'Monitoring and troubleshooting'
        ],
    }
    state.documentation = state.documentation or ''
    state.documentation_briefing = structured

    summary = (
        "Documentation Briefing:\n"
        f"- Docs length: {len(content)} chars\n"
        f"- Includes sections: yes\n"
        f"- Architecture: {structured['architecture']}\n"
        f"- Systems: {', '.join(structured['systems']) if structured['systems'] else 'none'}\n"
    )
    state.briefings['documentation'] = summary
    print(summary)
    return state.model_dump()


def documentation_quality_agent(state):
    if not isinstance(state, AgentState):
        state = AgentState(**state)

    content = state.documentation or ''
    score = 5.0 if len(content) > 2000 else 3.0
    issues = []
    if not content:
        score = 1.0
        issues.append('Documentation content missing')
    if 'Error Handling' not in content:
        issues.append('Missing error handling section')
    if 'Monitoring & Troubleshooting' not in content:
        issues.append('Missing monitoring/troubleshooting section')

    state.stage_quality_checks['documentation'] = {
        'stage': 'documentation',
        'complete': bool(content),
        'score': score,
        'issues': issues
    }

    print(f"Documentation quality: {score}/5, issues: {len(issues)}")
    return state.model_dump()