import os
import re
from typing import List, Optional
from state import AgentState
from utils import extract_json_object, load_system_prompt
from config import get_model, get_api_key

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

def _extract_entities(description: str) -> dict:
    """Extract key entities and patterns from process description."""
    entities = {
        "mentions_contracts": bool(re.search(r"verträge|contract", description, re.IGNORECASE)),
        "mentions_expiry": bool(re.search(r"läuft aus|ablauf|expir|expires", description, re.IGNORECASE)),
        "mentions_email": bool(re.search(r"mail|email|e-mail|benachricht", description, re.IGNORECASE)),
        "mentions_report": bool(re.search(r"report|export|document|datei", description, re.IGNORECASE)),
        "mentions_employees": bool(re.search(r"mitarbeiter|employee|person|staff", description, re.IGNORECASE)),
        "time_patterns": re.findall(r"(\d+)\s*(tag|day|woche|week|monat|month)", description, re.IGNORECASE),
        "system_names": re.findall(r"(Success Factor|SuccessFactors|SAP|Orchestrator|Outlook|Exchange|Salesforce|Jira|Tableau|PowerBI|Dynamics|Oracle)", description, re.IGNORECASE),
        # Frequency patterns
        "frequency_daily": bool(re.search(r"täglich|daily|every\s+day", description, re.IGNORECASE)),
        "frequency_weekly": bool(re.search(r"wöchentlich|weekly|every\s+week", description, re.IGNORECASE)),
        "frequency_monthly": bool(re.search(r"monatlich|monthly|every\s+month", description, re.IGNORECASE)),
        "frequency_on_demand": bool(re.search(r"auf anforderung|on\s+demand|manuel|manual", description, re.IGNORECASE)),
        # Error handling indicators
        "mentions_error_handling": bool(re.search(r"fehler|error|exception|handling|retry|wiederhol", description, re.IGNORECASE)),
        "mentions_validation": bool(re.search(r"validierung|validation|prüfung|check|verify", description, re.IGNORECASE)),
        "mentions_logging": bool(re.search(r"protokoll|log|audit|tracking", description, re.IGNORECASE)),
        # Multi-system coordination
        "mentions_multiple_systems": len(set(re.findall(r"(Success Factor|SuccessFactors|SAP|Orchestrator|Outlook|Exchange|Salesforce|Jira|Tableau|PowerBI|Dynamics|Oracle)", description, re.IGNORECASE))) > 1,
        "mentions_sync": bool(re.search(r"synchron|sync|abstimm(?:ung)?|coord", description, re.IGNORECASE)),
        "mentions_queue": bool(re.search(r"queue|warteschlange|backlog", description, re.IGNORECASE)),
        # Complexity indicators
        "mentions_bulk_data": bool(re.search(r"bulk|masse|viele|many|tausende|thousands", description, re.IGNORECASE)),
        "mentions_conditions": bool(re.search(r"wenn|if|falls|condition|bedingung", description, re.IGNORECASE))
    }
    return entities


def _format_frequency(entities: dict) -> str:
    if entities["frequency_daily"]:
        return "Scheduled daily"
    if entities["frequency_weekly"]:
        return "Scheduled weekly"
    if entities["frequency_monthly"]:
        return "Scheduled monthly"
    if entities["frequency_on_demand"]:
        return "Manual or on demand"
    return "To be confirmed"


def _build_extracted_entities(entities: dict, time_period: Optional[str]) -> List[str]:
    extracted = []

    if entities["mentions_contracts"]:
        extracted.append("- **Primary Object**: Contracts or contract-related records")
    elif entities["mentions_report"]:
        extracted.append("- **Primary Object**: Report or exported business data")
    else:
        extracted.append("- **Primary Object**: Business records to be processed")

    extracted.append(f"- **Execution Pattern**: {_format_frequency(entities)}")

    if time_period:
        extracted.append(f"- **Relevant Time Window**: {time_period}")

    if entities["mentions_email"]:
        extracted.append("- **Communication Channel**: Email notifications")
    if entities["mentions_validation"]:
        extracted.append("- **Control Requirement**: Data validation or verification is expected")
    if entities["mentions_error_handling"]:
        extracted.append("- **Operational Concern**: Explicit error handling is required")
    if entities["mentions_multiple_systems"]:
        extracted.append("- **Integration Scope**: Multiple systems need coordination")
    if entities["mentions_bulk_data"]:
        extracted.append("- **Volume Indicator**: Bulk or high-volume processing is implied")

    return extracted


def _build_as_is_flowchart(entities: dict) -> str:
    trigger_label = _format_frequency(entities)
    source_label = "Open source system or input data"
    if entities["system_names"]:
        source_label = f"Open {entities['system_names'][0]} and collect input data"

    review_label = "Review business records manually"
    if entities["mentions_contracts"]:
        review_label = "Review contract-related records manually"
    elif entities["mentions_report"]:
        review_label = "Review exported report manually"

    decision_label = "Relevant items found?"
    if entities["mentions_expiry"]:
        decision_label = "Relevant expiring items found?"

    action_label = "Perform manual follow-up actions"
    if entities["mentions_email"]:
        action_label = "Prepare and send manual email notifications"

    log_label = "Record outcome manually"
    if entities["mentions_logging"]:
        log_label = "Update manual log or audit trail"

    return f"""
```mermaid
flowchart TD
    A[Start: {trigger_label}] --> B[{source_label}]
    B --> C[{review_label}]
    C --> D{{{decision_label}}}
    D -->|Yes| E[{action_label}]
    D -->|No| F[End: No action required]
    E --> G[{log_label}]
    G --> H[End]
    F --> H
```
"""

def requirements_agent(state):
    if not isinstance(state, AgentState):
        state = AgentState(**state)
    
    # Load and use system prompt
    system_prompt = load_system_prompt('requirements')
    state.agent_context['requirements_system_prompt'] = system_prompt
    
    print("Vincent Vega: Analyzing the process description...\n")

    previous_requirements = state.requirements or {}
    briefing_structured = previous_requirements.get("briefing_structured", {})

    # Extract entities
    entities = _extract_entities(state.process_description)
    
    # Build systems list
    systems = list(set(entities["system_names"])) if entities["system_names"] else ["Primary business system"]
    if briefing_structured.get("systems"):
        systems = list(dict.fromkeys([*systems, *briefing_structured.get("systems", [])]))
    
    # Build inputs/outputs based on entities
    inputs = []
    outputs = []
    if entities["mentions_report"]:
        inputs.append("Exported employee and contract report from HR system")
    if entities["mentions_expiry"]:
        inputs.append("Contract expiry date for each employee")
    if entities["mentions_email"]:
        outputs.append("Email notifications to employees")
    if not inputs:
        inputs.append("Business records or source data required for the process")
    if not outputs:
        outputs.append("Processed records, status updates, or business outputs")
    
    # Extract time period
    time_period = None
    if entities["time_patterns"]:
        time_period = f"{entities['time_patterns'][0][0]} {entities['time_patterns'][0][1].lower()}"
    
    # Build business rules
    business_rules = []
    if time_period:
        business_rules.append(f"Send reminder {time_period} before contract expiration")
    if entities["mentions_contracts"] and entities["mentions_employees"]:
        business_rules.append("One reminder per employee with expiring contract")
    if entities["mentions_email"]:
        business_rules.append("Notifications must be delivered via email")
    if entities["mentions_validation"]:
        business_rules.append("Input data must pass validation before processing")
    if entities["mentions_multiple_systems"]:
        business_rules.append("Cross-system data must stay consistent throughout the process")
    if briefing_structured.get("objectives"):
        business_rules.extend(str(item) for item in briefing_structured.get("objectives", []) if str(item).strip())
    if not business_rules:
        business_rules.append("Processing steps and completion criteria need confirmation")
    
    # Build exceptions
    exceptions = ["Source data is missing, incomplete, or unavailable"]
    if entities["mentions_email"]:
        exceptions.append("Notification recipient or email address is missing")
    if entities["mentions_contracts"] or entities["mentions_expiry"]:
        exceptions.append("Relevant records are already expired or no longer actionable")
    if entities["mentions_validation"]:
        exceptions.append("Validation rules fail for one or more records")
    if entities["mentions_multiple_systems"]:
        exceptions.append("System data conflicts or synchronization issues occur")
    if entities["mentions_error_handling"]:
        exceptions.append("A recoverable operation fails and requires retry handling")
    if briefing_structured.get("constraints"):
        exceptions.extend(str(item) for item in briefing_structured.get("constraints", []) if str(item).strip())
    
    # Build targeted questions based on extracted patterns
    open_questions = []
    
    # Frequency-related questions
    if not any([entities["frequency_daily"], entities["frequency_weekly"], 
                entities["frequency_monthly"], entities["frequency_on_demand"]]):
        open_questions.append("What is the execution frequency (daily, weekly, monthly, on-demand)?")
    
    # Multi-system questions
    if entities["mentions_multiple_systems"]:
        open_questions.append(f"How should the process handle synchronization between {len(set([s for s in entities['system_names']]))} systems?")
        open_questions.append("What is the priority if data conflicts occur between systems?")
    
    # Error handling questions
    if entities["mentions_error_handling"]:
        open_questions.append("What is the retry strategy for failed operations (max retries, backoff)?")
        open_questions.append("Should critical errors pause the process or skip to next record?")
    
    # Validation questions
    if entities["mentions_validation"]:
        open_questions.append("What validation rules should be applied (format, mandatory fields, range checks)?")
    
    # Bulk data questions
    if entities["mentions_bulk_data"]:
        open_questions.append("For bulk processing, is batch size a concern? Should we process in chunks?")
    
    # Standard questions
    if not open_questions:  # Fallback to generic questions
        open_questions = [
            "What is the execution frequency (daily, weekly, monthly, on-demand)?",
            "What exact records or transactions should be processed?",
            "Are there templates, decision rules, or dynamic content requirements?",
            "Should duplicate processing be detected and prevented?"
        ]
    else:
        # Add generic questions if not already covered
        if not any("frequency" in q.lower() for q in open_questions):
            open_questions.append("What is the execution frequency (daily, weekly, monthly, on-demand)?")
        open_questions.append("Should the process log all operations for audit trailing?")
        open_questions.append("Who should be notified of critical errors or failures?")
    
    assumptions = [
        "Required source data is accessible at runtime",
        "The target systems allow the necessary read and write operations",
        "Business ownership for exceptions and escalations exists"
    ]
    if entities["mentions_email"]:
        assumptions.append("Email infrastructure is configured and accessible")
    if time_period:
        assumptions.append(f"The relevant time window is {time_period}")
    if entities["mentions_validation"]:
        assumptions.append("Validation rules are stable enough to codify in automation")
    
    requirements = {
        "process_overview": state.process_description,
        "trigger": _format_frequency(entities),
        "systems": systems,
        "inputs_outputs": {"inputs": inputs, "outputs": outputs},
        "business_rules": business_rules,
        "exceptions": exceptions,
        "assumptions": assumptions,
        "open_questions": open_questions,
        "extracted_timeframe": time_period,
        "source_briefing": {
            "process_summary": briefing_structured.get("process_summary", ""),
            "objectives": briefing_structured.get("objectives", []),
            "constraints": briefing_structured.get("constraints", []),
        }
    }

    # Enhance with LLM if available
    llm_instance = _get_llm()
    if llm_instance:
        print("Vincent Vega: Analyzing the process description with OpenAI...\n")
        try:
            requirements_quality = state.stage_quality_checks.get("requirements", {})
            enhanced_prompt = f"""Based on this process description and the preliminary extraction, return a JSON object only.

Required JSON schema:
{{
  "trigger": "string",
  "systems": ["string"],
  "inputs": ["string"],
  "outputs": ["string"],
  "business_rules": ["string"],
  "exceptions": ["string"],
  "assumptions": ["string"],
  "open_questions": ["string"],
    "ai_insights": ["string"],
    "confidence": "low|medium|high"
}}

Process: {state.process_description}
Preliminary systems: {', '.join(systems)}
Preliminary business rules: {chr(10).join(business_rules)}
Preliminary exceptions: {chr(10).join(exceptions)}
Previous requirements quality issues: {requirements_quality.get('issues', [])}
Briefing objectives: {briefing_structured.get('objectives', [])}
Briefing constraints: {briefing_structured.get('constraints', [])}
"""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": enhanced_prompt}
            ]
            response = llm_instance.invoke(messages)
            structured = extract_json_object(response.content)
            if structured:
                requirements["trigger"] = structured.get("trigger") or requirements["trigger"]
                requirements["systems"] = structured.get("systems") or requirements["systems"]
                requirements["inputs_outputs"]["inputs"] = structured.get("inputs") or requirements["inputs_outputs"]["inputs"]
                requirements["inputs_outputs"]["outputs"] = structured.get("outputs") or requirements["inputs_outputs"]["outputs"]
                requirements["business_rules"] = structured.get("business_rules") or requirements["business_rules"]
                requirements["exceptions"] = structured.get("exceptions") or requirements["exceptions"]
                requirements["assumptions"] = structured.get("assumptions") or requirements["assumptions"]
                requirements["open_questions"] = structured.get("open_questions") or requirements["open_questions"]
                requirements["ai_insights"] = structured.get("ai_insights", [])
                requirements["confidence"] = structured.get("confidence", "medium")
                print("✓ OpenAI-enhanced requirements merged into working state.\n")
            else:
                requirements["ai_insights"] = [response.content]
                requirements["confidence"] = "low"
                print("✓ OpenAI insights captured as unstructured notes.\n")
        except Exception as e:
            print(f"Note: LLM enhancement skipped ({e})\n")
    else:
        print("Vincent Vega: Analyzing the process description...\n")
        print("✓ Requirements analysis complete.\n")

    extracted_entities = _build_extracted_entities(entities, time_period)

    print("Vincent Vega: Finalizing requirements summary...\n")
    print("✓ Requirements analysis complete.")

    md_content = f"""# Requirements Analysis

## Process Overview
{requirements['process_overview']}

## Extracted Entities
{chr(10).join(extracted_entities)}

## Trigger & Frequency
{requirements['trigger']}

## Systems Involved
{chr(10).join(f'- {s}' for s in requirements['systems'])}

## Inputs
{chr(10).join(f'- {i}' for i in requirements['inputs_outputs']['inputs'])}

## Outputs
{chr(10).join(f'- {o}' for o in requirements['inputs_outputs']['outputs'])}

## Business Rules
{chr(10).join(f'- {rule}' for rule in requirements['business_rules'])}

## Identified Exceptions & Edge Cases
{chr(10).join(f'- {exc}' for exc in requirements['exceptions'])}

## Assumptions
{chr(10).join(f'- {ass}' for ass in requirements['assumptions'])}

## Open Questions for Clarification
{chr(10).join(f'{i+1}. {q}' for i, q in enumerate(requirements['open_questions']))}
"""

    if requirements.get("ai_insights"):
        md_content += "\n## LLM Insights\n"
        md_content += chr(10).join(
            insight if str(insight).startswith("-") else f"- {insight}"
            for insight in requirements["ai_insights"]
        )
        md_content += "\n"

    with open("outputs/01_requirements.md", "w") as f:
        f.write(md_content)

    # Generate AS-IS process flowchart from requirements
    as_is_flowchart = _build_as_is_flowchart(entities)

    with open("outputs/00_as_is_process_flowchart.md", "w") as f:
        f.write("# Current As-Is Process Flowchart\n\n" + as_is_flowchart)

    state.requirements = requirements
    state.requirements['as_is_flowchart'] = as_is_flowchart

    # Handover package for design stage.
    state.lifecycle_handover["requirements_to_design"] = {
        "process_overview": requirements.get("process_overview", ""),
        "trigger": requirements.get("trigger", ""),
        "systems": requirements.get("systems", []),
        "business_rules": requirements.get("business_rules", []),
        "exceptions": requirements.get("exceptions", []),
        "assumptions": requirements.get("assumptions", []),
        "open_questions": requirements.get("open_questions", []),
        "confidence": requirements.get("confidence", "medium"),
        "quality_issues": state.stage_quality_checks.get("requirements", {}).get("issues", []),
    }

    # Ask for targeted clarifications - ALL open questions
    print("Vincent Vega: I have several questions to refine the requirements:\n")
    for i, q in enumerate(requirements['open_questions'], 1):
        print(f"{i}. {q}")
    
    # Add business case question
    print(f"\n{len(requirements['open_questions']) + 1}. How long does the process take manually (in hours, per execution)?")
    
    try:
        answers = input("\nProvide answers (or press Enter to accept as-is): ").strip()
    except EOFError:
        answers = ''
    
    manual_duration_hours = 0
    if answers:
        # Try to extract manual duration from answers
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*(hour|h|hr|stunde)', answers, re.IGNORECASE)
        if match:
            manual_duration_hours = float(match.group(1).replace(',', '.'))
            print(f"✓ Clarifications noted. Manual duration: {manual_duration_hours} hours/execution")
        else:
            print("✓ Clarifications noted.")
    
    # Store business case data
    state.requirements['manual_duration_hours'] = manual_duration_hours
    state.requirements['clarifications'] = answers
    print()

    # Human gate 1
    print(f"Generated documentation: outputs/01_requirements.md\n")
    try:
        approve = input("Vincent Vega: Do you approve these requirements? (yes/no): ").strip().lower()
    except EOFError:
        approve = 'yes'
    state.human_gates["requirements_approved"] = approve in ("", "y", "yes")

    if not state.human_gates["requirements_approved"]:
        print("Requirements not approved. Stopping.")
        state.errors.append("Requirements not approved")
    else:
        print("✓ Requirements approved.\n")

    return state.model_dump()


def _extract_requirement_chunks(description: str) -> dict:
    """Extract structured requirement chunks and entities (enhanced version)."""
    # Use the existing comprehensive entity extraction
    entities = _extract_entities(description)
    
    # Build advanced chunks with entities
    chunks = {
        'process_summary': description.split('\n')[0].strip() if description else '',
        'frequency': 'täglich' if entities['frequency_daily'] else ('wöchentlich' if entities['frequency_weekly'] else 'unspecified'),
        'systems': list(set(entities['system_names'])) if entities['system_names'] else [],
        'mentions_contracts': entities['mentions_contracts'],
        'mentions_expiry': entities['mentions_expiry'],
        'mentions_email': entities['mentions_email'],
        'mentions_error_handling': entities['mentions_error_handling'],
        'mentions_multiple_systems': entities['mentions_multiple_systems'],
        'mentions_bulk_data': entities['mentions_bulk_data'],
        'entities': entities,  # Pass full entity dict
        'objectives': [],
        'constraints': []
    }
    
    # Parse structured requirements if present
    if '\nAnforderungen:' in description:
        block = description.split('\nAnforderungen:')[1].split('\nSysteme:')[0] if '\nSysteme:' in description else description.split('\nAnforderungen:')[1]
        for line in block.splitlines():
            line = line.strip().lstrip('- ').strip()
            if line:
                if 'retry' in line.lower() or 'timeout' in line.lower() or 'duplik' in line.lower() or 'fehler' in line.lower():
                    chunks['constraints'].append(line)
                else:
                    chunks['objectives'].append(line)
    
    return chunks


def requirements_briefing_agent(state):
    if not isinstance(state, AgentState):
        state = AgentState(**state)

    # Enhanced extraction with full entity analysis
    extracted = _extract_requirement_chunks(state.process_description or '')

    # store extracted structured payload for requirements agent
    state.requirements = state.requirements or {}
    state.requirements['briefing_structured'] = extracted
    
    # Extract and highlight key entities for briefing
    entities = extracted.get('entities', {})
    key_finds = []
    if entities.get('mentions_contracts'):
        key_finds.append('Contract tracking')
    if entities.get('mentions_expiry'):
        key_finds.append('Expiry detection')
    if entities.get('mentions_email'):
        key_finds.append('Email notifications')
    if entities.get('mentions_error_handling'):
        key_finds.append('Error handling')
    if entities.get('mentions_multiple_systems'):
        key_finds.append('Multi-system sync')
    if entities.get('mentions_bulk_data'):
        key_finds.append('Bulk processing')

    context_snippet = (state.skill_context or '')[:120].replace('\n', ' ')

    summary = (
        "Requirements Briefing:\n"
        f"- Process summary: {extracted['process_summary']}\n"
        f"- Key findings: {', '.join(key_finds) if key_finds else 'standard workflow'}\n"
        f"- Frequency: {extracted['frequency']}\n"
        f"- Systems: {', '.join(extracted['systems']) if extracted['systems'] else 'not yet identified'}\n"
        f"- Objectives: {len(extracted['objectives'])} items\n"
        f"- Constraints: {len(extracted['constraints'])} items\n"
        f"- Skill context snippet: {context_snippet}...\n"
    )

    state.requirements['phase_context'] = state.get_phase_context('requirements')
    state.requirements['key_entities_found'] = key_finds
    state.briefings['requirements'] = summary
    print(summary)
    return state.model_dump()


def requirements_quality_agent(state):
    if not isinstance(state, AgentState):
        state = AgentState(**state)

    exists = bool(state.requirements)
    business_rules = state.requirements.get('business_rules', []) if exists else []
    open_questions = state.requirements.get('open_questions', []) if exists else []
    manual_duration = state.requirements.get('manual_duration_hours', 0) if exists else 0
    key_entities = state.requirements.get('key_entities_found', []) if exists else []
    
    quality = {
        'stage': 'requirements',
        'complete': exists,
        'score': 4.0 if exists and len(business_rules) >= 2 else 2.5,
        'issues': [],
        'business_case_data_available': manual_duration > 0
    }

    if not exists:
        quality['issues'].append('Requirements object missing')
    else:
        if len(state.requirements.get('systems', [])) == 0:
            quality['issues'].append('No systems identified')
        if len(business_rules) < 2:
            quality['issues'].append('Few business rules in requirement set')
        if len(open_questions) == 0:
            quality['issues'].append('No follow-up questions generated')
        if manual_duration <= 0:
            quality['issues'].append('Missing business case data: manual process duration not captured')
        if len(key_entities) < 3:
            quality['issues'].append(f'Limited entity extraction: only {len(key_entities)} key entities found (target: 3+)')
        
        # Boost score if all data is present
        if manual_duration > 0 and len(key_entities) >= 3 and len(business_rules) >= 2:
            quality['score'] = 5.0

    state.stage_quality_checks['requirements'] = quality
    print(f"Requirements quality: {quality['score']}/5, issues: {len(quality['issues'])}, business case: {'✓' if manual_duration > 0 else '✗'}")
    return state.model_dump()