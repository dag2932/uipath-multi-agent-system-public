import os
from state import AgentState
from utils import load_system_prompt
from config import DEFAULT_MODEL, OPENAI_API_KEY

# Initialize LLM if API key is available
llm = None
if OPENAI_API_KEY:
    try:
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(model=DEFAULT_MODEL, api_key=OPENAI_API_KEY, temperature=0.7)
    except Exception as e:
        print(f"Warning: Could not initialize LLM: {e}")

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
    reqs = state.requirements or {}
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

    # Display architecture summary
    print("✓ Architecture Analysis:")
    print(f"  - Complexity Score: {complexity_score}/5")
    print(f"  - Model: {architecture}")
    print(f"  - REFramework: {reframework_decision.split(' - ')[0]}")
    print(f"  - Dispatcher/Performer: {dispatcher_performer_decision.split(' - ')[0]}")
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
"""

    flowchart = """
```mermaid
flowchart TD
    A[Start: System timer trigger] --> B[Initialize UiPath process]
    B --> C[Load asset credentials:<br/>SAP OAuth + SMTP config]
    C --> D[Invoke GetEmployeeContracts]
    D --> E{Data retrieved?}
    E -->|Yes| F[ParallelForEach contract]
    E -->|No| G[Log warning + End]
    F --> H{Valid email &&<br/>Expiry in window?}
    H -->|Yes| I[Invoke SendReminders]
    H -->|No| J[Log skip reason]
    I --> K{Send Success?}
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

    # Human gate 2
    print(f"Generated design document: outputs/02_solution_design.md\n")
    try:
        approve = input("Jules Winnfield: Do you approve this architecture? (yes/no): ").strip().lower()
    except EOFError:
        approve = 'yes'
    state.human_gates["design_approved"] = approve == "yes"


def design_briefing_agent(state):
    if not isinstance(state, AgentState):
        state = AgentState(**state)

    reqs_struct = state.requirements.get('briefing_structured', {}) if state.requirements else {}
    design_input = {
        'process_goal': reqs_struct.get('process_summary', ''),
        'trigger': reqs_struct.get('frequency', 'unspecified'),
        'systems': reqs_struct.get('systems', []),
        'business_rules': reqs_struct.get('objectives', []),
        'error_handling': reqs_struct.get('constraints', []),
    }

    state.design = state.design or {}
    state.design['briefing_structured'] = design_input

    summary = (
        "Design Briefing:\n"
        f"- Process goal: {design_input['process_goal']}\n"
        f"- Trigger: {design_input['trigger']}\n"
        f"- Systems: {', '.join(design_input['systems']) if design_input['systems'] else 'none'}\n"
        f"- Business rules: {len(design_input['business_rules'])} items\n"
        f"- Error handling: {len(design_input['error_handling'])} items\n"
    )

    state.briefings['design'] = summary
    print(summary)
    return state.model_dump()

    if not state.human_gates["design_approved"]:
        print("Design not approved. Stopping.")
        state.errors.append("Design not approved")
    else:
        print("✓ Design approved.\n")

    return state.model_dump()


def design_briefing_agent(state):
    if not isinstance(state, AgentState):
        state = AgentState(**state)

    design = state.solution_design or {}
    summary = (
        "Design Briefing:\n"
        f"- Architecture: {design.get('architecture', 'n/a')}\n"
        f"- REFramework decision: {design.get('reframework_decision', 'n/a')}\n"
        f"- Dispatcher/Performer: {design.get('dispatcher_performer', 'n/a')}\n"
        f"- Complexity: {design.get('complexity_score', 'n/a')}\n"
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