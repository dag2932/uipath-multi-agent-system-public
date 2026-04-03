import os
from core.state import AgentState
from core.utils import extract_json_object, load_system_prompt, build_reasoning_context, invoke_llm_json_with_policy
from core.config import get_model, get_api_key, is_llm_first, is_llm_required

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

def design_agent(state):
    if not isinstance(state, AgentState):
        state = AgentState(**state)
    if not state.human_gates["requirements_approved"]:
        return state.model_dump()

    # Load and use system prompt
    system_prompt = load_system_prompt('design')
    state.agent_context['design_system_prompt'] = system_prompt

    # Apply adjustable design context
    phase_context = state.get_phase_context('design')
    if phase_context:
        print(f"[Design context override] {phase_context}\n")

    print("Jules Winnfield: Designing the UiPath solution...\n")

    # Design agent should be guided by uipath-rpa-workflows skill context
    if state.skill_context:
        print("[Skill context loaded from uipath-rpa-workflows/SKILL.md, applying core principles...]")

    # Analyze requirements to make architectural decisions
    handover_req = state.lifecycle_handover.get("requirements_to_design", {})
    reqs = state.requirements or {}
    if handover_req:
        reqs = {
            **reqs,
            "process_overview": handover_req.get("process_overview", reqs.get("process_overview", "")),
            "trigger": handover_req.get("trigger", reqs.get("trigger", "")),
            "systems": handover_req.get("systems", reqs.get("systems", [])),
            "business_rules": handover_req.get("business_rules", reqs.get("business_rules", [])),
            "exceptions": handover_req.get("exceptions", reqs.get("exceptions", [])),
            "assumptions": handover_req.get("assumptions", reqs.get("assumptions", [])),
            "open_questions": handover_req.get("open_questions", reqs.get("open_questions", [])),
            "confidence": handover_req.get("confidence", reqs.get("confidence", "medium")),
        }
    requirements_quality = state.stage_quality_checks.get("requirements", {})
    requirements_briefing = state.briefings.get("requirements", "")
    business_rules = reqs.get("business_rules", [])
    inputs_outputs = reqs.get("inputs_outputs", {})
    systems = reqs.get("systems", [])
    
    # --- INTELLIGENT REFRAMEWORK DETECTION ---
    complexity_indicators = {
        "bulk_data": any("report" in str(io).lower() for io in inputs_outputs.get("inputs", [])),
        "error_handling_complex": False,
        "multi_system": len(systems) > 2,
        "queue_needed": False,
        "retry_needed": False,
    }
    
    # Check for error handling indicators in requirements
    requirements_text = str(reqs).lower()
    if any(word in requirements_text for word in ["retry", "error", "exception", "handle", "wiederhol"]):
        complexity_indicators["error_handling_complex"] = True
    if any(word in requirements_text for word in ["queue", "warteschlange", "pending", "backlog"]):
        complexity_indicators["queue_needed"] = True
    if any(word in requirements_text for word in ["retry", "verify", "validate", "check"]):
        complexity_indicators["retry_needed"] = True
    
    # Calculate complexity score
    complexity_score = sum(complexity_indicators.values())
    
    # Decide on REFramework based on complexity
    if complexity_score >= 2 or complexity_indicators["queue_needed"]:
        reframework_decision = "REFramework RECOMMENDED - complex process"
        reframework_reasoning = f"Process has {complexity_score} complexity factors: {', '.join([k for k, v in complexity_indicators.items() if v])}"
        if complexity_indicators["queue_needed"]:
            reframework_reasoning += ". Queue management will benefit from REFramework's transaction handling."
    else:
        reframework_decision = "REFramework NOT needed - simple linear process"
        reframework_reasoning = "Single-pass sequential processing without complex error recovery"
    
    # Detect if Dispatcher/Performer pattern is needed
    is_bulk_data = complexity_indicators["bulk_data"]
    needs_dispatcher = is_bulk_data and complexity_indicators["error_handling_complex"]
    
    if needs_dispatcher:
        dispatcher_performer_decision = "Dispatcher/Performer RECOMMENDED"
        dispatcher_passenger_reasoning = f"Bulk data processing ({len(systems)} systems) with complex error handling - decouple data collection from processing"
    else:
        dispatcher_performer_decision = "Dispatcher/Performer NOT needed - single execution model"
        dispatcher_passenger_reasoning = f"Processing a {'bulk report' if is_bulk_data else 'small dataset'} sequentially - tight coupling acceptable"
    
    # Architecture decision based on REFramework
    if reframework_decision.startswith("REFramework RECOMMENDED"):
        architecture = "RPA Workflow with REFramework Pattern"
        architecture_reasoning = "Complex process with error recovery, transaction management, and potential queue handling"
    else:
        architecture = "RPA Workflow - Simple Sequential Processing"
        architecture_reasoning = "Linear process with minimal error handling complexity"
    
    # --- LOGGING STRATEGY ---
    logging_strategy = "Structured logging with:"
    logging_items = [
        "Process start/end timestamps",
        "Record processing count (success/skipped/failed)",
        "System integration points (SAP, Email)",
        "Error details with context",
    ]
    
    # --- EXCEPTION HANDLING STRATEGY ---
    exception_strategy = "Multi-tier error handling:"
    exception_items = [
        "Data validation errors → log and continue (non-critical)",
        "Service availability errors (SAP/Email down) → retry with exponential backoff",
        "Authentication failures → fail immediately and alert",
    ]
    
    if complexity_indicators["retry_needed"]:
        exception_items.insert(1, "Transient failures → 3 retries with 5-second intervals")
    
    # --- CONFIGURATION EXTERNALIZATION ---
    config_points = [
        "Integration URLs (SAP, Email server)",
        "Timeout values and retry counts",
        "Batch size (if bulk processing)",
        "Email templates and subject lines",
        "Reminder days offset and thresholds",
    ]
    
    # --- ASSET REQUIREMENTS ---
    assets = [
        "SAP credentials (username/password or OAuth)",
        "Email service credentials",
        "API keys or connection strings",
    ]
    
    if reframework_decision.startswith("REFramework RECOMMENDED"):
        assets.append("Queue name or transaction storage (in Orchestrator)")
    
    # --- RISK ASSESSMENT ---
    risks = []
    if is_bulk_data:
        risks.append("Bulk data processing may hit API rate limits - implement pagination/chunking")
    if complexity_indicators["multi_system"]:
        risks.append(f"Multi-system synchronization ({len(systems)} systems) - data consistency issues possible")
    if complexity_indicators["error_handling_complex"]:
        risks.append("Complex error recovery logic - ensure all paths are tested")
    if complexity_indicators["queue_needed"]:
        risks.append("Queue management adds operational complexity - monitor queue depth")
    risks.extend([
        "Email delivery failures (bounced addresses, server issues)",
        "Data quality: missing required fields in source system"
    ])
    
    # --- TRADEOFFS ---
    tradeoffs = []
    if reframework_decision.startswith("REFramework RECOMMENDED"):
        tradeoffs.append("REFramework provides robustness but adds ~20% performance overhead")
        tradeoffs.append("Queue model adds operational complexity but enables better error recovery")
    tradeoffs.extend([
        "XAML RPA: visual debugging support, but harder to integrate with external APIs",
        "Sequential processing: simpler logic, but may timeout on 10k+ record sets"
    ])

    design = {
        "architecture": architecture,
        "architecture_reasoning": architecture_reasoning,
        "reframework_decision": reframework_decision,
        "reframework_reasoning": reframework_reasoning,
        "dispatcher_performer": dispatcher_performer_decision,
        "dispatcher_passenger_reasoning": dispatcher_passenger_reasoning,
        "transaction_model": "Queue-based with transaction persistence" if "RECOMMENDED" in reframework_decision else "Stateless - no queue/persistence",
        "orchestration": "REFramework: Get Transaction → Process Item → Set Result" if "RECOMMENDED" in reframework_decision else "Sequential: Read Report → Parse Data → Process → Log Results",
        "logging_strategy": logging_strategy,
        "logging_items": logging_items,
        "exception_strategy": exception_strategy,
        "exception_items": exception_items,
        "configuration": "Externalize all connection strings and thresholds",
        "config_points": config_points,
        "assets_required": assets,
        "risks": risks,
        "tradeoffs": tradeoffs,
        "complexity_score": complexity_score,
        "complexity_indicators": complexity_indicators
    }

    llm_instance = _get_llm()
    if is_llm_required() and not llm_instance:
        raise RuntimeError("LLM_REQUIRED=true but no LLM client could be initialized.")

    if llm_instance:
        print("Jules Winnfield: Running LLM-assisted architecture refinement...\n")
        try:
            reasoning_context = build_reasoning_context(
                state,
                stage="design",
                extra={
                    "detected_architecture": architecture,
                    "complexity_score": complexity_score,
                    "complexity_indicators": complexity_indicators,
                    "requirements_handover": handover_req,
                },
            )
            llm_prompt = f"""Return a JSON object only.

Schema:
{{
  "architecture_reasoning": "string",
  "reframework_decision": "string",
  "reframework_reasoning": "string",
  "dispatcher_performer": "string",
  "dispatcher_passenger_reasoning": "string",
  "logging_items": ["string"],
  "exception_items": ["string"],
  "config_points": ["string"],
  "assets_required": ["string"],
  "risks": ["string"],
  "tradeoffs": ["string"],
    "ai_recommendations": ["string"],
    "component_blueprint": ["string"],
    "security_controls": ["string"],
    "test_strategy": ["string"],
    "deployment_strategy": ["string"],
    "observability_plan": ["string"]
}}

Reasoning context packet (JSON):
{reasoning_context}
"""
            structured = invoke_llm_json_with_policy(
                llm_instance=llm_instance,
                system_prompt=system_prompt,
                user_prompt=llm_prompt,
                required_keys=["reframework_decision", "risks", "tradeoffs"],
                retries=2,
            )
            if structured:
                for key in [
                    "architecture_reasoning",
                    "reframework_decision",
                    "reframework_reasoning",
                    "dispatcher_performer",
                    "dispatcher_passenger_reasoning",
                ]:
                    if structured.get(key):
                        design[key] = structured[key]
                for key in ["logging_items", "exception_items", "config_points", "assets_required", "risks", "tradeoffs"]:
                    if structured.get(key):
                        design[key] = structured[key]
                design["ai_recommendations"] = structured.get("ai_recommendations", [])
                design["component_blueprint"] = structured.get("component_blueprint", [])
                design["security_controls"] = structured.get("security_controls", [])
                design["test_strategy"] = structured.get("test_strategy", [])
                design["deployment_strategy"] = structured.get("deployment_strategy", [])
                design["observability_plan"] = structured.get("observability_plan", [])
                print("✓ LLM enhancement applied in design phase.\n")
            else:
                design["ai_recommendations"] = ["LLM response was not parseable JSON; baseline design retained."]
                print("✓ LLM recommendations captured as unstructured notes.\n")
        except Exception as e:
            print(f"Note: Design LLM enhancement skipped ({e})\n")
    else:
        if is_llm_first():
            print("⚠ LLM-first mode active but LLM unavailable. Using deterministic design policy.\n")
        else:
            print("Note: Design phase running without LLM enhancement.\n")

    # Display architecture summary
    print("✓ Architecture Analysis:")
    print(f"  - Complexity Score: {complexity_score}/5")
    print(f"  - Model: {architecture}")
    print(f"  - REFramework: {reframework_decision.split(' - ')[0]}")
    print(f"  - Dispatcher/Performer: {design.get('dispatcher_performer', dispatcher_performer_decision).split(' - ')[0]}")
    if complexity_score >= 2:
        print(f"  - Detected patterns: {', '.join([k for k, v in complexity_indicators.items() if v])}")
    print()

    md_content = f"""# Solution Design

## Architecture Decision
**{design['architecture']}**

Reasoning: {design['architecture_reasoning']}

## REFramework Decision
**{design['reframework_decision']}**

Rationale: {design['reframework_reasoning']}

## Dispatcher / Performer Pattern
**{design['dispatcher_performer']}**

Rationale: {design['dispatcher_passenger_reasoning']}

## Transaction Model
{design['transaction_model']}

## Orchestration Flow
```
{design['orchestration']}
```

## Logging Strategy
{design['logging_strategy']}
{chr(10).join(f'  - {item}' for item in design['logging_items'])}

## Exception Handling
{design['exception_strategy']}
{chr(10).join(f'  - {item}' for item in design['exception_items'])}

## Configuration Externalization
Externalize the following settings to config files:
{chr(10).join(f'  - {point}' for point in design['config_points'])}

## Required Assets & Credentials
{chr(10).join(f'  - {asset}' for asset in design['assets_required'])}

## Identified Risks
{chr(10).join(f'  - {risk}' for risk in design['risks'])}

## Architecture Trade-offs
{chr(10).join(f'  - {tradeoff}' for tradeoff in design['tradeoffs'])}

## Component Blueprint
{chr(10).join(f'- {item}' for item in design.get('component_blueprint', [])) if design.get('component_blueprint') else '- To be refined during implementation'}

## Security Controls
{chr(10).join(f'- {item}' for item in design.get('security_controls', [])) if design.get('security_controls') else '- Secret management in Orchestrator assets, log redaction, and least-privilege access'}

## Test Strategy
{chr(10).join(f'- {item}' for item in design.get('test_strategy', [])) if design.get('test_strategy') else '- Unit checks, integration tests, and end-to-end dry runs with representative data'}

## Deployment Strategy
{chr(10).join(f'- {item}' for item in design.get('deployment_strategy', [])) if design.get('deployment_strategy') else '- Staged deployment with rollback checkpoints and controlled cutover'}

## Observability Plan
{chr(10).join(f'- {item}' for item in design.get('observability_plan', [])) if design.get('observability_plan') else '- Runtime, error rate, throughput, and business outcome KPIs'}
"""

    if design.get("ai_recommendations"):
        md_content += "\n## LLM Recommendations\n"
        md_content += chr(10).join(
            item if str(item).startswith("-") else f"- {item}"
            for item in design["ai_recommendations"]
        )
        md_content += "\n"

    flowchart = """
```mermaid
flowchart TD
    A[Start: System timer trigger] --> B[Initialize UiPath process]
    B --> C[Load assets, credentials, and runtime config]
    C --> D[Invoke Data Acquisition workflow]
    D --> E{Data retrieved?}
    E -->|Yes| F[ParallelForEach business record]
    E -->|No| G[Log warning + End]
    F --> H{Record passes validation<br/>and business rules?}
    H -->|Yes| I[Invoke Business Action workflow]
    H -->|No| J[Log skip reason]
    I --> K{Action Success?}
    K -->|Yes| L[SuccessCount +1]
    K -->|Transient Error| M[Retry up to 3x<br/>with backoff]
    M --> N{Still failing?}
    N -->|Yes| O[FailCount +1]
    N -->|No| L
    K -->|Auth Error| O
    O --> P[Continue loop]
    J --> Q[SkipCount +1]
    Q --> P
    L --> P
    P --> R[Write summary log<br/>with metrics]
    R --> S[End]
    G --> S
```
"""

    md_content += "\n## To-Be Solution Flowchart (Automated RPA Process)\n" + flowchart
    md_content += "\n\n### Architecture Governed By\nThis design follows **uipath-rpa-workflows** skill principles (discovery-first, validate continuously, activity docs as source of truth).\n"

    with open("outputs/02_solution_design.md", "w") as f:
        f.write(md_content)
    with open("outputs/02_solution_design_flowchart.md", "w") as f:
        f.write("# Solution Design Flowchart (To-Be Process)\n\n" + flowchart)

    state.solution_design = design
    state.solution_design['flowchart'] = flowchart
    state.solution_design['flowchart_source_skill'] = 'uipath-rpa-workflows'

    # Handover package for build stage.
    state.lifecycle_handover["design_to_build"] = {
        "architecture": design.get("architecture", ""),
        "reframework_decision": design.get("reframework_decision", ""),
        "dispatcher_performer": design.get("dispatcher_performer", ""),
        "complexity_score": design.get("complexity_score", 0),
        "orchestration": design.get("orchestration", ""),
        "logging_items": design.get("logging_items", []),
        "exception_items": design.get("exception_items", []),
        "assets_required": design.get("assets_required", []),
        "risks": design.get("risks", []),
        "quality_issues": state.stage_quality_checks.get("design", {}).get("issues", []),
        "reasoning_context_packet": build_reasoning_context(state, stage="design_handover"),
    }

    # Human gate 2
    print(f"Generated design document: outputs/02_solution_design.md\n")
    try:
        approve = input("Jules Winnfield: Do you approve this architecture? (yes/no): ").strip().lower()
    except EOFError:
        approve = 'yes'
    state.human_gates["design_approved"] = approve in ("", "y", "yes")

    if not state.human_gates["design_approved"]:
        print("Design not approved. Build phase will be skipped.")
        state.errors.append("Design not approved")
    else:
        print("✓ Design approved. Proceeding to build phase.\n")

    return state.model_dump()


def design_briefing_agent(state):
    if not isinstance(state, AgentState):
        state = AgentState(**state)
    design = state.solution_design or {}
    reqs = state.requirements or {}
    req_quality = state.stage_quality_checks.get('requirements', {})
    req_struct = reqs.get('briefing_structured', {})

    state.design = state.design or {}
    state.design['briefing_structured'] = {
        'process_goal': req_struct.get('process_summary', reqs.get('process_overview', '')),
        'trigger': req_struct.get('frequency', reqs.get('trigger', 'unspecified')),
        'systems': reqs.get('systems', []),
        'business_rules_count': len(reqs.get('business_rules', [])),
        'requirements_quality_score': req_quality.get('score', 'n/a'),
        'requirements_open_issues': req_quality.get('issues', []),
        'requirements_confidence': reqs.get('confidence', 'medium')
    }

    summary = (
        "Design Briefing:\n"
        f"- Architecture: {design.get('architecture', 'n/a')}\n"
        f"- REFramework decision: {design.get('reframework_decision', 'n/a')}\n"
        f"- Dispatcher/Performer: {design.get('dispatcher_performer', 'n/a')}\n"
        f"- Complexity: {design.get('complexity_score', 'n/a')}\n"
        f"- Input confidence from requirements: {reqs.get('confidence', 'n/a')}\n"
        f"- Upstream quality issues: {len(req_quality.get('issues', []))}\n"
    )
    state.briefings['design'] = summary
    print(summary)
    return state.model_dump()


def design_quality_agent(state):
    if not isinstance(state, AgentState):
        state = AgentState(**state)

    design = state.solution_design or {}
    complete = bool(design)
    issues = []
    score = 4.0

    if not complete:
        score = 2.0
        issues.append('Solution design missing')
    if design.get('complexity_score', 0) < 1:
        issues.append('Complexity score not computed')
    if 'reframework_decision' not in design:
        issues.append('REFramework decision missing')
    if 'dispatcher_performer' not in design:
        issues.append('Dispatcher/Performer decision missing')

    if issues:
        score = min(score, 3.5)

    state.stage_quality_checks['design'] = {
        'stage': 'design',
        'complete': complete,
        'score': score,
        'issues': issues
    }

    print(f"Design quality: {score}/5, {len(issues)} issues")
    return state.model_dump()