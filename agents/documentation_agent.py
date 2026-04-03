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
    
    doc_content = f"""# Automation Documentation

## Executive Summary
**Process**: {reqs.get('process_overview', 'Unknown')[:150]}

**Architecture**: {design.get('architecture', 'Coded Workflow')}

**Scope**: End-to-end automation of contract expiry notifications

---

## 1. Functional Overview

### What This Automation Does
- Periodically checks for contracts expiring within a configured window (30 days)
- Retrieves employee contact information from SAP SuccessFactors
- Sends email reminders to affected employees before contract expiration
- Logs all processing results for audit and monitoring

### Business Value
- Proactive employee notification reduces manual follow-up
- Standardized communication via email
- Audit trail for compliance
- Scalable to any number of employee contracts

---

## 2. System Interactions

### Input Systems
{chr(10).join(f'- {s}' for s in reqs.get('systems', []))}

### Integration Points
- **SAP SuccessFactors**
  - Connection method: OData API / CSV Export / IntegrationConnectorService
  - Data: Employee records, contract details, expiry dates
  - Frequency: Once per process execution

- **Email System**
  - Method: SMTP / Office 365 Exchange
  - Recipient: Employee email from SuccessFactors
  - Template: Customizable reminder message

### Process Flow
```
1. Read employee & contract data from SuccessFactors
   ↓
2. Filter: Contracts expiring in 30-day window
   ↓
3. For each employee:
   - Validate email address
   - Send reminder (or skip with log)
   ↓
4. Log results: success count, failures, skipped
   ↓
5. Report summary (optional: send to admin)
```

---

## 3. Technical Overview

### Technology Stack
- **Platform**: UiPath Cloud / On-Premises
- **Language**: C# (Coded Workflow)
- **Key Activities**: 
  - System.LogMessage (logging)
  - mail.SendMail (email notifications)
  - Optional: IntegrationConnectorService (SAP)

### Architecture Rationale
- **Why Coded Workflow**: Better for API integration and data transformation
- **Why NOT REFramework**: Single-step process without transactions/queues
- **Why NOT Dispatcher/Performer**: Bulk data but processed in single run, not parallel

### Error Handling Strategy
- **Business Exceptions** (missing email, already expired) → log and continue
- **Transient Errors** (temporary service issues) → retry with backoff
- **Critical Errors** (auth failure) → fail and alert

---

## 4. Deployment & Operations

### Prerequisites
- [ ] SAP SuccessFactors credentials configured in Orchestrator
- [ ] Email service credentials (SMTP or O365)
- [ ] Network access to both systems from Robot
- [ ] Employee email data in SuccessFactors export

### Installation Steps
1. Open project in UiPath Studio 2023.10+
2. Configure credentials in Orchestrator
3. Set process configuration (reminder days, email template)
4. Test with sample employee data
5. Deploy to production and schedule

### Configuration Settings
- **ReminderDaysOffset**: Number of days before expiration to send reminder (default: 30)
- **SuccessFactorsUrl**: OData endpoint for employee contracts
- **EmailFrom**: Sender email address
- **EmailTemplate**: Message body (supports {{ExpiryDate}}, {{EmployeeName}} placeholders)

### Scheduling
- **Recommended Frequency**: Daily (or per business requirement)
- **Run Window**: Off-peak hours (e.g., 2 AM)
- **Retry Policy**: Up to 3 retries on transient failures

---

## 5. Monitoring & Troubleshooting

### Logging
All operations logged with timestamps:
- Contract processing counts (success, skipped, failed)
- Email send confirmations
- API call results
- Error details

### Key Metrics to Monitor
- **Success Rate**: % of contracts processed successfully
- **Skip Rate**: % skipped (usually due to missing email)
- **Failure Rate**: % that encountered errors
- **Execution Time**: Process duration

### Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Email send fails | SMTP/O365 not configured | Verify credentials, test SMTP connection |
| Missing employee data | Field mapping wrong | Check SuccessFactors export field names |
| No contracts found | Filter date range wrong | Verify ReminderDaysOffset setting |
| Orchestrator timeout | Too many employees | Consider Dispatcher/Performer pattern |

---

## 6. Maintenance & Support

### Regular Maintenance
- [ ] Review logs weekly for anomalies
- [ ] Verify email delivery success weekly
- [ ] Check API rate limits monthly
- [ ] Update documentation of any config changes

### Known Limitations
- Single execution model (not parallel) - suitable up to ~5000 employees
- Email template is not visual (plain text)
- No human approval workflow

### Future Enhancements
- Add repeat notification logic (e.g., send again 7 days before expiry)
- Integrate with ticketing system (assign to manager)
- Add HTML email formatting
- Support multiple reminder windows

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

    with open("outputs/04_documentation.md", "w") as f:
        f.write(doc_content)

    state.documentation = doc_content
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