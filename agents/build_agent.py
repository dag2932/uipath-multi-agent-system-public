import json
import os
import re
import uuid
from datetime import datetime

from state import AgentState
from utils import extract_json_object, load_system_prompt, build_reasoning_context, invoke_llm_json
from config import get_model, get_api_key, is_llm_first, is_llm_required

llm = None

STOP_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "by",
    "check",
    "create",
    "daily",
    "execute",
    "for",
    "from",
    "generate",
    "get",
    "in",
    "into",
    "of",
    "on",
    "or",
    "process",
    "run",
    "send",
    "sync",
    "the",
    "to",
    "update",
    "with",
}

ENTITY_HINTS = [
    ("invoice", "Invoice"),
    ("contract", "Contract"),
    ("employee", "Employee"),
    ("payment", "Payment"),
    ("order", "Order"),
    ("ticket", "Ticket"),
    ("request", "Request"),
    ("case", "Case"),
    ("lead", "Lead"),
    ("customer", "Customer"),
    ("record", "Record"),
    ("report", "Report"),
    ("document", "Document"),
    ("transaction", "Transaction"),
]

ACTION_WORKFLOW_HINTS = [
    (("email", "mail", "notify", "notification", "remind", "message"), "SendNotifications", "Execute the outbound communication step defined in the solution design."),
    (("update", "writeback", "sync", "post", "push"), "UpdateTargetSystem", "Write processed results back into the target system."),
    (("approve", "approval", "submit"), "SubmitApprovals", "Submit the processed items for downstream approval or handoff."),
    (("export", "report", "file", "download", "upload"), "PublishOutputArtifacts", "Publish the generated output artifacts to the defined destination."),
    (("create", "open", "book", "register"), "CreateTargetRecords", "Create or register target records based on the processed data."),
]


def _get_llm():
    global llm
    if llm is not None:
        return llm

    api_key = get_api_key()
    if api_key:
        try:
            from langchain_openai import ChatOpenAI

            model = get_model()
            llm = ChatOpenAI(model=model, api_key=api_key, temperature=0.7)
        except Exception as exc:
            print(f"Warning: Could not initialize LLM: {exc}")
    return llm



def _make_project_name(process_overview: str) -> str:
    base = "GeneratedAutomation"
    if not process_overview:
        return base

    parts = [part.capitalize() for part in re.findall(r"[A-Za-z0-9]+", process_overview)[:4]]
    return "".join(parts) or base



def _sanitize_identifier(value: str, default: str) -> str:
    parts = [
        segment[:1].upper() + segment[1:]
        for part in re.findall(r"[A-Za-z0-9]+", value)
        for segment in re.findall(r"[A-Z]+(?![a-z])|[A-Z]?[a-z0-9]+", part)
    ]
    return "".join(parts) or default



def _escape_for_vb_string(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )



def _collect_requirement_text(reqs: dict) -> str:
    text_parts = [reqs.get("process_overview", "")]
    for key in ("business_rules", "exceptions", "assumptions", "open_questions", "systems"):
        value = reqs.get(key, [])
        if isinstance(value, list):
            text_parts.extend(str(item) for item in value)
        elif value:
            text_parts.append(str(value))

    inputs_outputs = reqs.get("inputs_outputs", {})
    if isinstance(inputs_outputs, dict):
        for items in inputs_outputs.values():
            if isinstance(items, list):
                text_parts.extend(str(item) for item in items)

    return " ".join(part for part in text_parts if part)



def _infer_primary_entity(reqs: dict) -> str:
    combined_text = _collect_requirement_text(reqs).lower()
    for needle, label in ENTITY_HINTS:
        if needle in combined_text:
            return label

    tokens = re.findall(r"[A-Za-z][A-Za-z0-9]+", combined_text)
    for token in tokens:
        if token.lower() not in STOP_WORDS and len(token) > 4:
            return token.capitalize()
    return "BusinessRecord"



def _infer_action_workflow(process_text: str) -> tuple[str, str]:
    lowered = process_text.lower()
    for keywords, workflow_name, purpose in ACTION_WORKFLOW_HINTS:
        if any(keyword in lowered for keyword in keywords):
            return workflow_name, purpose
    return "ExecuteBusinessAction", "Execute the final business action after validation and decisioning."



def _build_workflow_plan(reqs: dict, design: dict) -> list[dict]:
    process_text = _collect_requirement_text(reqs)
    primary_entity = _infer_primary_entity(reqs)
    systems = reqs.get("systems", []) or []
    systems_text = ", ".join(str(system) for system in systems) if systems else "source systems"
    use_reframework = "RECOMMENDED" in design.get("reframework_decision", "")
    use_dispatcher = "RECOMMENDED" in design.get("dispatcher_performer", "")

    acquisition_name = f"Collect{primary_entity}Data"
    validation_name = f"ValidateAndPrepare{primary_entity}"
    action_name, action_purpose = _infer_action_workflow(process_text)

    workflow_plan = [
        {
            "name": _sanitize_identifier(acquisition_name, "CollectInputData"),
            "purpose": f"Retrieve {primary_entity.lower()} data from {systems_text} and normalize it for downstream processing.",
            "implementation_notes": [
                f"Use the integrations named in the design: {systems_text}.",
                "Return data in a structure that the downstream workflow can iterate deterministically.",
            ],
        },
        {
            "name": _sanitize_identifier(validation_name, "ValidateAndPrepareData"),
            "purpose": f"Apply business rules, validations, and transformations for each {primary_entity.lower()} before execution.",
            "implementation_notes": [
                "Map the business rules from the requirements into explicit validation and routing steps.",
                "Keep data enrichment and decisioning isolated from system-specific I/O.",
            ],
        },
        {
            "name": _sanitize_identifier(action_name, "ExecuteBusinessAction"),
            "purpose": action_purpose,
            "implementation_notes": [
                "Implement the final action in the target system or delivery channel.",
                "Add retries, logging, and idempotency safeguards according to the solution design.",
            ],
        },
    ]

    if use_dispatcher:
        workflow_plan.insert(
            1,
            {
                "name": f"Queue{primary_entity}Transactions",
                "purpose": f"Create transaction payloads for queued processing of {primary_entity.lower()} items.",
                "implementation_notes": [
                    "Create a queue item schema that matches the solution design.",
                    "Separate data collection from transaction processing for scale and recoverability.",
                ],
            },
        )

    if use_reframework:
        workflow_plan.insert(
            0,
            {
                "name": "InitializeApplications",
                "purpose": "Initialize configuration, credentials, and application sessions required by the automation.",
                "implementation_notes": [
                    "Load assets, config values, and environment-specific settings before transaction handling.",
                    "Centralize session setup to support retry and recovery behavior.",
                ],
            },
        )

    for workflow in workflow_plan:
        workflow["name"] = _sanitize_identifier(workflow["name"], "GeneratedWorkflow")
        workflow["file_name"] = f"{workflow['name']}.xaml"
        workflow["display_name"] = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", workflow["name"])

    return workflow_plan



def _generate_main_xaml(project_name: str, workflow_plan: list[dict], process_label: str) -> str:
    invoke_steps = []
    for workflow in workflow_plan:
        invoke_steps.append(
            "    <WriteLine DisplayName=\"Log {display_name}\" Text=\"[&quot;Starting {display_name}&quot;]\" />\n"
            "    <InvokeWorkflow DisplayName=\"Invoke {display_name}\" WorkflowFileName=\"{file_name}\" />\n"
            "    <WriteLine DisplayName=\"Log {display_name} Complete\" Text=\"[&quot;Finished {display_name}&quot;]\" />".format(
                display_name=_escape_for_vb_string(workflow["display_name"]),
                file_name=workflow["file_name"],
            )
        )

    invoke_block = "\n".join(invoke_steps)
    process_label = _escape_for_vb_string(process_label)
    return f"""<Activity mc:Ignorable=\"sap sap2010 sads\" x:Class=\"{project_name}.Main\" xmlns=\"http://schemas.microsoft.com/netfx/2009/xaml/activities\" xmlns:mc=\"http://schemas.openxmlformats.org/markup-compatibility/2006\" xmlns:sap=\"http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation\" xmlns:sap2010=\"http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation\" xmlns:sads=\"http://schemas.microsoft.com/netfx/2010/xaml/activities/debugger\" xmlns:x=\"http://schemas.microsoft.com/winfx/2006/xaml\">
  <x:Members />
  <Sequence DisplayName=\"Main Orchestration\">
    <WriteLine DisplayName=\"Log Start\" Text=\"[&quot;Starting automation: {process_label}&quot;]\" />
{invoke_block}
    <WriteLine DisplayName=\"Log End\" Text=\"[&quot;Automation completed&quot;]\" />
  </Sequence>
</Activity>"""



def _generate_subworkflow_xaml(project_name: str, workflow: dict, architecture: str) -> str:
    purpose = _escape_for_vb_string(workflow["purpose"])
    implementation_hint = _escape_for_vb_string(" ".join(workflow.get("implementation_notes", [])))
    architecture = _escape_for_vb_string(architecture)
    return f"""<Activity mc:Ignorable=\"sap sap2010 sads\" x:Class=\"{project_name}.{workflow['name']}\" xmlns=\"http://schemas.microsoft.com/netfx/2009/xaml/activities\" xmlns:mc=\"http://schemas.openxmlformats.org/markup-compatibility/2006\" xmlns:sap=\"http://schemas.microsoft.com/netfx/2009/xaml/activities/presentation\" xmlns:sap2010=\"http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation\" xmlns:sads=\"http://schemas.microsoft.com/netfx/2010/xaml/activities/debugger\" xmlns:x=\"http://schemas.microsoft.com/winfx/2006/xaml\">
  <x:Members />
  <Sequence DisplayName=\"{workflow['display_name']}\">
    <WriteLine DisplayName=\"Workflow Purpose\" Text=\"[&quot;{purpose}&quot;]\" />
    <WriteLine DisplayName=\"Implementation Hint\" Text=\"[&quot;{implementation_hint}&quot;]\" />
    <WriteLine DisplayName=\"Architecture Context\" Text=\"[&quot;Architecture: {architecture}&quot;]\" />
  </Sequence>
</Activity>"""



def _generate_workflow_architecture(reqs: dict, design: dict, workflow_plan: list[dict]) -> str:
    workflow_rows = "\n".join(
        f"| {workflow['file_name']} | Sub-workflow | {workflow['purpose']} | Template scaffold |"
        for workflow in workflow_plan
    )
    implementation_sections = "\n\n".join(
        "### {name}\n- Purpose: {purpose}\n- Implementation focus:\n{notes}".format(
            name=workflow["file_name"],
            purpose=workflow["purpose"],
            notes="\n".join(f"  - {note}" for note in workflow.get("implementation_notes", [])),
        )
        for workflow in workflow_plan
    )

    systems = reqs.get("systems", []) or []
    systems_text = ", ".join(str(system) for system in systems) if systems else "No explicit systems listed"

    return f"""# Workflow Architecture

## Overview
- Process: {reqs.get('process_overview', 'Generated automation workflow')}
- Architecture: {design.get('architecture', 'RPA Workflow - Simple Sequential Processing')}
- Complexity: {design.get('complexity_score', 'n/a')}/5
- Systems: {systems_text}

## Generated Workflow Set

| Workflow | Type | Purpose | Status |
|----------|------|---------|--------|
| Main.xaml | Orchestrator | Execute the design-driven workflow sequence | Generated |
{workflow_rows}

## Generation Rules Applied
- Workflow names were derived from the process overview, listed systems, and design decisions.
- The generated XAML files are scaffolds for the approved solution design, not sample business cases.
- Sub-workflows isolate acquisition, business-rule handling, and final action execution so each stage can be implemented and tested independently.

## Implementation Guidance
{implementation_sections}

## Next Steps
1. Open Main.xaml and confirm the orchestration order matches the approved design.
2. Implement the real activities inside each generated sub-workflow.
3. Externalize credentials, endpoints, and thresholds into configuration or Orchestrator assets.
4. Test each sub-workflow independently before running the full orchestration.

## Validation Checklist
- [ ] Workflow names match the intended business steps.
- [ ] Source integrations align with the systems named in the requirements.
- [ ] Business rules are implemented in the validation workflow.
- [ ] Target actions are implemented in the execution workflow.
- [ ] Logging and exception handling match the chosen architecture.

Last Updated: {datetime.now().isoformat(timespec='seconds')}
"""



def _generate_build_notes(project_dir: str, workflow_plan: list[dict], design: dict, llm_build_focus: dict) -> str:
    workflow_list = "\n".join(f"- {workflow['file_name']}: {workflow['purpose']}" for workflow in workflow_plan)
    notes = f"""# Build Notes

## Generated Artifacts
- {project_dir}/project.json
- {project_dir}/Main.xaml
- {project_dir}/WORKFLOW_ARCHITECTURE.md
{workflow_list}

## Build Summary
- Workflow type: RPA (XAML)
- Architecture: {design.get('architecture', 'RPA Workflow - Simple Sequential Processing')}
- REFramework: {design.get('reframework_decision', 'Not specified')}
- Dispatcher/Performer: {design.get('dispatcher_performer', 'Not specified')}

## What Was Generated
- Main.xaml orchestrates the generated workflow sequence from the approved design.
- Each sub-workflow contains a focused implementation placeholder tied to a specific business step.
- Workflow names were generated from the process and design context instead of hardcoded sample names.

## Next Implementation Steps
1. Implement the real system activities inside each generated sub-workflow.
2. Add explicit input and output arguments where data must cross workflow boundaries.
3. Externalize environment-specific settings and credentials.
4. Validate the final orchestration in UiPath Studio with representative test data.
"""

    if llm_build_focus.get("immediate_priorities"):
        notes += "\n\n## LLM Immediate Priorities\n"
        notes += "\n".join(f"- {item}" for item in llm_build_focus["immediate_priorities"])
    if llm_build_focus.get("testing_focus"):
        notes += "\n\n## LLM Testing Focus\n"
        notes += "\n".join(f"- {item}" for item in llm_build_focus["testing_focus"])
    if llm_build_focus.get("implementation_risks"):
        notes += "\n\n## LLM Implementation Risks\n"
        notes += "\n".join(f"- {item}" for item in llm_build_focus["implementation_risks"])
    if llm_build_focus.get("build_notes"):
        notes += "\n\n## LLM Build Notes\n"
        notes += "\n".join(f"- {item}" for item in llm_build_focus["build_notes"])

    return notes + "\n"



def build_agent(state):
    if not isinstance(state, AgentState):
        state = AgentState(**state)
    if not state.human_gates["design_approved"]:
        print("Butch Coolidge: Skipping build because the design gate was not approved.\n")
        state.errors.append("Build skipped because design was not approved")
        return state.model_dump()

    system_prompt = load_system_prompt("build")
    state.agent_context["build_system_prompt"] = system_prompt

    phase_context = state.get_phase_context("build")
    if phase_context:
        print(f"[Build context override] {phase_context}\n")

    print("Butch Coolidge: Building UiPath RPA artifacts from the approved solution design...\n")

    project_dir = "outputs/uipath_project"
    os.makedirs(project_dir, exist_ok=True)
    state.project_dir = project_dir

    reqs = state.requirements or {}
    design = state.solution_design or {}
    handover_req = state.lifecycle_handover.get("requirements_to_design", {})
    handover_design = state.lifecycle_handover.get("design_to_build", {})
    if handover_req:
        reqs = {**reqs, **{k: v for k, v in handover_req.items() if k in reqs or k in ["process_overview", "trigger", "systems", "business_rules", "exceptions", "assumptions", "open_questions", "confidence"]}}
    if handover_design:
        design = {**design, **handover_design}
    requirements_quality = state.stage_quality_checks.get("requirements", {})
    design_quality = state.stage_quality_checks.get("design", {})
    design_briefing = state.briefings.get("design", "")
    project_name = _make_project_name(reqs.get("process_overview", ""))
    project_description = reqs.get("process_overview", "Generated automation workflow")[:100]
    use_reframework = "RECOMMENDED" in design.get("reframework_decision", "")

    workflow_plan = _build_workflow_plan(reqs, design)
    workflow_files = [workflow["file_name"] for workflow in workflow_plan]

    project_json = {
        "name": project_name,
        "projectId": str(uuid.uuid4()),
        "description": project_description,
        "main": "Main.xaml",
        "dependencies": {
            "UiPath.System.Activities": "[25.12.2]",
            "UiPath.Mail.Activities": "[2.8.0]",
            "UiPath.Excel.Activities": "[3.5.0]",
            "UiPath.Web.Activities": "[25.12.0]",
        },
        "webServices": [],
        "entitiesStores": [],
        "schemaVersion": "4.0",
        "studioVersion": "2024.10.0",
        "projectVersion": "1.0.0",
        "runtimeOptions": {
            "autoDispose": False,
            "netFrameworkLazyLoading": False,
            "isPausable": True,
            "isAttended": False,
            "requiresUserInteraction": False,
            "supportsPersistence": use_reframework,
            "workflowSerialization": "NewtonsoftJson",
            "excludedLoggedData": ["Private:*", "*password*"],
            "executionType": "Workflow",
            "readyForPiP": False,
            "startsInPiP": False,
            "mustRestoreAllDependencies": True,
            "pipType": "ChildSession",
        },
        "designOptions": {
            "projectProfile": "Development",
            "outputType": "Process",
            "libraryOptions": {"privateWorkflows": []},
            "processOptions": {"ignoredFiles": []},
            "fileInfoCollection": [],
            "saveToCloud": False,
        },
        "expressionLanguage": "CSharp",
        "entryPoints": [
            {
                "filePath": "Main.xaml",
                "uniqueId": str(uuid.uuid4()),
                "input": [],
                "output": [],
            }
        ],
        "isTemplate": False,
        "templateProjectData": {},
        "publishData": {},
        "targetFramework": "Windows",
    }

    with open(f"{project_dir}/project.json", "w") as file_handle:
        json.dump(project_json, file_handle, indent=2)

    main_xaml = _generate_main_xaml(
        project_name=project_name,
        workflow_plan=workflow_plan,
        process_label=reqs.get("process_overview", "Generated automation workflow"),
    )
    with open(f"{project_dir}/Main.xaml", "w") as file_handle:
        file_handle.write(main_xaml)

    for workflow in workflow_plan:
        workflow_xaml = _generate_subworkflow_xaml(
            project_name=project_name,
            workflow=workflow,
            architecture=design.get("architecture", "RPA Workflow - Simple Sequential Processing"),
        )
        with open(f"{project_dir}/{workflow['file_name']}", "w") as file_handle:
            file_handle.write(workflow_xaml)

    workflow_architecture = _generate_workflow_architecture(reqs, design, workflow_plan)
    with open(f"{project_dir}/WORKFLOW_ARCHITECTURE.md", "w") as file_handle:
        file_handle.write(workflow_architecture)

    llm_build_focus = {}
    llm_instance = _get_llm()
    if is_llm_required() and not llm_instance:
        raise RuntimeError("LLM_REQUIRED=true but no LLM client could be initialized.")

    if llm_instance:
        print("Butch Coolidge: Running LLM-assisted build review...\n")
        try:
            reasoning_context = build_reasoning_context(
                state,
                stage="build",
                extra={
                    "workflow_files": ["Main.xaml", *workflow_files],
                    "architecture": design.get("architecture", "unknown"),
                    "design_handover": handover_design,
                },
            )
            llm_prompt = f"""Return a JSON object only.

Schema:
{{
  "immediate_priorities": ["string"],
  "testing_focus": ["string"],
  "implementation_risks": ["string"],
  "build_notes": ["string"]
}}

Reasoning context packet (JSON):
{reasoning_context}
"""
            structured = invoke_llm_json(llm_instance, system_prompt, llm_prompt)
            if structured:
                llm_build_focus = structured
                print("✓ LLM enhancement applied in build phase.\n")
            else:
                llm_build_focus = {"build_notes": ["LLM response was not parseable JSON; baseline build guidance retained."]}
                print("✓ LLM notes captured in build phase.\n")
        except Exception as exc:
            print(f"Note: Build LLM enhancement skipped ({exc})\n")
    else:
        if is_llm_first():
            print("⚠ LLM-first mode active but LLM unavailable. Using deterministic build guidance.\n")
        else:
            print("Note: Build phase running without LLM enhancement.\n")

    build_notes = _generate_build_notes(project_dir, workflow_plan, design, llm_build_focus)
    with open("outputs/03_build_notes.md", "w") as file_handle:
        file_handle.write(build_notes)

    print("✓ UiPath project scaffold created:")
    print("  - project.json")
    print("  - Main.xaml")
    for workflow_file in workflow_files:
        print(f"  - {workflow_file}")
    print("  - WORKFLOW_ARCHITECTURE.md")
    print("  - 03_build_notes.md")
    print()

    state.build_artifacts = {
        "project_dir": project_dir,
        "files": ["project.json", "Main.xaml", *workflow_files, "WORKFLOW_ARCHITECTURE.md"],
        "workflow_files": workflow_files,
        "generated_workflows": workflow_plan,
        "project_name": project_name,
        "workflow_type": "RPA (XAML)",
        "completeness": "60%",
        "next_steps": "Implement the generated sub-workflows, wire arguments, and test the orchestration in UiPath Studio.",
        "llm_used": bool(llm_build_focus),
        "llm_guidance": llm_build_focus,
        "upstream_context": {
            "requirements_quality": requirements_quality,
            "design_quality": design_quality,
            "design_briefing": design_briefing,
        },
    }

    # Handover package for documentation stage.
    state.lifecycle_handover["build_to_documentation"] = {
        "project_dir": project_dir,
        "project_name": project_name,
        "workflow_type": "RPA (XAML)",
        "files": ["project.json", "Main.xaml", *workflow_files, "WORKFLOW_ARCHITECTURE.md"],
        "generated_workflows": workflow_plan,
        "llm_guidance": llm_build_focus,
        "quality_issues": state.stage_quality_checks.get("build", {}).get("issues", []),
        "reasoning_context_packet": build_reasoning_context(state, stage="build_handover"),
    }

    return state.model_dump()



def build_briefing_agent(state):
    if not isinstance(state, AgentState):
        state = AgentState(**state)

    artifacts = state.build_artifacts or {}
    design_struct = state.solution_design or {}
    generated_workflows = artifacts.get("generated_workflows", [])
    design_quality = state.stage_quality_checks.get("design", {})

    state.build = state.build or {}
    state.build["briefing_structured"] = {
        "project_dir": artifacts.get("project_dir", "n/a"),
        "files": artifacts.get("files", []),
        "workflow_type": artifacts.get("workflow_type", "n/a"),
        "architecture": design_struct.get("architecture", "unknown"),
        "core_features": [workflow.get("purpose", "Generated workflow step") for workflow in generated_workflows],
        "upstream_design_issues": design_quality.get("issues", []),
    }

    summary = (
        "Build Briefing:\n"
        f"- Project directory: {artifacts.get('project_dir', 'n/a')}\n"
        f"- Files generated: {', '.join(artifacts.get('files', []))}\n"
        f"- Workflow type: {artifacts.get('workflow_type', 'n/a')}\n"
        f"- Architecture: {design_struct.get('architecture', 'unknown')}\n"
        f"- Completeness: {artifacts.get('completeness', 'n/a')}\n"
        f"- Upstream design issues: {len(design_quality.get('issues', []))}\n"
    )
    state.briefings["build"] = summary
    print(summary)
    return state.model_dump()



def build_quality_agent(state):
    if not isinstance(state, AgentState):
        state = AgentState(**state)

    artifacts = state.build_artifacts or {}
    files = artifacts.get("files", [])
    workflow_files = artifacts.get("workflow_files", [])
    complete = bool(files)
    issues = []
    score = 4.0

    if not complete:
        score = 2.0
        issues.append("Build artifacts missing")
    if "project.json" not in files:
        issues.append("project.json not generated")
    if "Main.xaml" not in files:
        issues.append("Main.xaml not generated")
    if "WORKFLOW_ARCHITECTURE.md" not in files:
        issues.append("WORKFLOW_ARCHITECTURE.md not generated")
    if len(workflow_files) < 2:
        issues.append("Expected at least two generated sub-workflows")
    for workflow_file in workflow_files:
        if workflow_file not in files:
            issues.append(f"{workflow_file} not registered in build artifacts")

    if issues:
        score = min(score, 3.0)

    state.stage_quality_checks["build"] = {
        "stage": "build",
        "complete": complete,
        "score": score,
        "issues": issues,
    }

    print(f"Build quality: {score}/5, issues: {len(issues)}")
    return state.model_dump()
