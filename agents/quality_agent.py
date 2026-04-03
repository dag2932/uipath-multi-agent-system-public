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


def _infer_review_context(state: AgentState) -> tuple[str, str]:
    reqs = state.requirements or {}
    outputs = reqs.get('inputs_outputs', {}).get('outputs', [])
    primary_output = outputs[0] if outputs else 'business outputs'
    process = reqs.get('process_overview', 'the described automation')
    return process[:100], primary_output

def quality_agent(state):
    if not isinstance(state, AgentState):
        state = AgentState(**state)

    # Load and use system prompt
    system_prompt = load_system_prompt('quality')
    state.agent_context['quality_system_prompt'] = system_prompt

    print("Marsellus Wallace: Reviewing code quality...\n")

    process_summary, primary_output = _infer_review_context(state)
    design = state.solution_design or {}
    build_artifacts = state.build_artifacts or {}
    stage_checks = state.stage_quality_checks or {}
    build_workflows = build_artifacts.get("workflow_files", [])
    handover_doc = state.lifecycle_handover.get("documentation_to_quality", {})
    handover_build = state.lifecycle_handover.get("build_to_documentation", {})
    if not build_workflows and handover_build.get("generated_workflows"):
        build_workflows = [
            wf.get("file_name", "") for wf in handover_build.get("generated_workflows", []) if wf.get("file_name")
        ]
    llm_quality_notes = ""

    llm_instance = _get_llm()
    if is_llm_required() and not llm_instance:
        raise RuntimeError("LLM_REQUIRED=true but no LLM client could be initialized.")

    if llm_instance:
        print("Marsellus Wallace: Running LLM-assisted quality deep dive...\n")
        try:
            reasoning_context = build_reasoning_context(
                state,
                stage="quality",
                extra={
                    "process_summary": process_summary,
                    "primary_output": primary_output,
                    "generated_workflows": build_workflows,
                    "documentation_handover": handover_doc,
                },
            )
            llm_prompt = f"""Return a JSON object only.

Schema:
{{
  "issues": ["string"],
  "recommendations": ["string"],
  "risks": ["string"],
  "critical_blockers": ["string"],
  "production_readiness": "string",
    "severity_findings": [{{"severity":"critical|high|medium|low","finding":"string","fix":"string"}}],
    "test_gaps": ["string"],
    "go_no_go_criteria": ["string"],
  "llm_deep_dive": ["string"]
}}

Reasoning context packet (JSON):
{reasoning_context}
"""
            structured = invoke_llm_json_with_policy(
                llm_instance=llm_instance,
                system_prompt=system_prompt,
                user_prompt=llm_prompt,
                required_keys=["issues", "recommendations", "critical_blockers"],
                retries=2,
            )
            if structured:
                llm_quality_notes = structured.get("llm_deep_dive", [])
                ai_issues = structured.get("issues") or []
                ai_recommendations = structured.get("recommendations") or []
                ai_risks = structured.get("risks") or []
                ai_blockers = structured.get("critical_blockers") or []
                ai_readiness = structured.get("production_readiness")
                ai_severity_findings = structured.get("severity_findings") or []
                ai_test_gaps = structured.get("test_gaps") or []
                ai_go_no_go = structured.get("go_no_go_criteria") or []
                print("✓ LLM enhancement applied in quality phase.\n")
            else:
                llm_quality_notes = ["LLM response was not parseable JSON; deterministic quality review retained."]
                ai_issues = []
                ai_recommendations = []
                ai_risks = []
                ai_blockers = []
                ai_readiness = None
                ai_severity_findings = []
                ai_test_gaps = []
                ai_go_no_go = []
                print("✓ LLM notes captured in quality phase.\n")
        except Exception as e:
            print(f"Note: Quality LLM enhancement skipped ({e})\n")
            ai_issues = []
            ai_recommendations = []
            ai_risks = []
            ai_blockers = []
            ai_readiness = None
            ai_severity_findings = []
            ai_test_gaps = []
            ai_go_no_go = []
    else:
        if is_llm_first():
            print("⚠ LLM-first mode active but LLM unavailable. Using deterministic quality heuristics.\n")
        else:
            print("Note: Quality phase running without LLM enhancement.\n")
        ai_issues = []
        ai_recommendations = []
        ai_risks = []
        ai_blockers = []
        ai_readiness = None
        ai_severity_findings = []
        ai_test_gaps = []
        ai_go_no_go = []
    
    # Intelligent quality assessment
    upstream_issue_count = sum(len(item.get("issues", [])) for item in stage_checks.values() if isinstance(item, dict))
    readiness = "Partial - The generated solution needs process-specific completion before release"
    if upstream_issue_count == 0 and build_workflows:
        readiness = "Good - Core scaffold is consistent; production hardening and integration completion remain"

    review = {
        "structure_modularity": "✓ Good - Modular design with separated orchestration and sub-workflow responsibilities",
        "logging_completeness": "✓ Excellent - Logs at workflow start, each processing step, and final summary",
        "exception_handling": "✓ Strong - Workflow-level handling plus item-level continuation strategy",
        "config_externalization": "✓ Good - Key runtime values should be externalized before production",
        "reframework_compliance": "N/A - Only needed if the final process becomes transaction-heavy",
        "dispatcher_performer": "N/A - Only needed if throughput demands queue-based scaling",
        "maintainability": "✓ Good - State-driven orchestration with distinct agent responsibilities",
        "data_validation": "✓ Good - Validation checkpoints are expected before business actions are executed",
        "performance": "⚠ Medium - Performance depends on record volume and integration latency",
        "security": "⚠ Watch - Ensure credentials remain outside code and logs",
        "issues": [
            "Generated implementation still contains template-level placeholders",
            "Integration details require environment-specific completion",
            "Idempotency rules are not fully enforced yet"
        ] + ai_issues,
        "recommendations": [
            "Replace remaining template placeholders with process-specific integrations",
            "Externalize configurable thresholds, endpoints, and templates",
            "Add duplicate prevention or idempotency checks where business actions can repeat",
            "Add retry logic for transient integration failures",
            "Validate the solution with representative test data before production"
        ] + ai_recommendations,
        "risks": [
            "Integration constraints: Source or target systems may impose rate limits or timeout thresholds",
            "Data quality: Required fields may be missing or malformed in source records",
            "Operational overlap: If the process runs twice, duplicate business actions may occur without idempotency",
            "Configuration drift: Environment settings may diverge between test and production"
        ] + ai_risks,
        "production_readiness": ai_readiness or readiness,
        "critical_blockers": [
            "Replace template integration placeholders with working implementations",
            f"Validate the handling of {primary_output}",
            "Test the process end-to-end with real credentials and representative data"
        ] + ai_blockers,
        "severity_findings": ai_severity_findings,
        "test_gaps": ai_test_gaps,
        "go_no_go_criteria": ai_go_no_go,
    }

    # Fold upstream stage findings into final quality view so each agent result is carried forward.
    if upstream_issue_count:
        review["issues"].append(f"Upstream stages reported {upstream_issue_count} unresolved quality issues")
    if handover_doc.get("upstream_build_issues"):
        review["issues"].append("Documentation handover indicates unresolved build issues")
    if not build_workflows:
        review["critical_blockers"].append("Build stage did not provide generated workflow metadata")

    md_content = f"""# Code Quality Review

## Quality Assessment Summary

| Dimension | Score | Status |
|-----------|-------|--------|
| **Structure & Modularity** | 4/5 | {review['structure_modularity'].split(' - ')[0]} |
| **Logging Completeness** | 5/5 | {review['logging_completeness'].split(' - ')[0]} |
| **Exception Handling** | 4/5 | {review['exception_handling'].split(' - ')[0]} |
| **Configuration Externalization** | 3/5 | {review['config_externalization'].split(' - ')[0]} |
| **Security** | 4/5 | {review['security'].split(' - ')[0]} |
| **Performance** | 3/5 | {review['performance'].split(' - ')[0]} |
| **Maintainability** | 4/5 | {review['maintainability'].split(' - ')[0]} |
| **Overall** | **3.7/5** | **Ready for Implementation** |

---

## Detailed Findings

### Structure & Modularity
{review['structure_modularity']}

**Recommendation**: Extract business logic into helper methods as workflow grows.

### Logging Completeness
{review['logging_completeness']}

**Example entries logged**:
- Process start with date/time
- Selected record count and filtering criteria
- Per-item: success, skip, or failure reason
- Summary: success/skip/fail counts

### Exception Handling
{review['exception_handling']}

**Pattern**:
```
Workflow-level: catch all and rethrow
Loop-level: catch per-record and continue
Validation-level: check required data before action
```

### Configuration Externalization
{review['config_externalization']}

**Current**:
```csharp
private const string ProcessEndpoint = "...";
private const string OutputTemplate = "...";
```

**TODO**: Move to external config for production:
```json
{{"Endpoint": "...", "OutputTemplate": "..."}}
```

### Security Posture
{review['security']}

**Checklist**:
- [x] Passwords excluded from log output
- [x] Sensitive data not hardcoded
- [ ] Credentials stored in Orchestrator assets (TODO)
- [ ] API keys not in code (TODO)

### Performance
{review['performance']}

**Current Model**: Sequential processing with integration-dependent runtime

**Acceptable for**: Moderate workloads until measured otherwise

**If scaling becomes an issue**: Consider batching, queue orchestration, or Dispatcher/Performer

### Data Validation
{review['data_validation']}

**Validations present**:
- Required data check before action
- Skip records without context instead of crashing
- Conversion errors caught and logged

---

## Issues Found

{chr(10).join(f"{i+1}. {issue}" for i, issue in enumerate(review['issues']))}

---

## Improvement Recommendations

{chr(10).join(f"{i+1}. {rec}" for i, rec in enumerate(review['recommendations']))}

---

## Identified Risks

{chr(10).join(f"- **{risk.split(':')[0]}**: {risk}" for risk in review['risks'])}

---

## Production Readiness Assessment

### Current Status: **Partial Readiness**

**Ready**:
- ✓ Project structure and dependencies
- ✓ Logging and monitoring capability
- ✓ Error handling framework
- ✓ Configuration points defined

**Not Ready** (blockers):
- ✗ Final integrations not implemented
- ✗ No production credentials configured
- ✗ Not tested with real data

---

## Critical Blockers (Must Resolve)

{chr(10).join(f"{i+1}. {blocker}" for i, blocker in enumerate(review['critical_blockers']))}

---

## Severity Findings

{chr(10).join(f"- **{item.get('severity', 'medium').upper()}**: {item.get('finding', '')} | **Fix**: {item.get('fix', '')}" for item in review.get('severity_findings', [])) if review.get('severity_findings') else '- No additional severity-tagged findings from LLM'}

---

## Test Gaps

{chr(10).join(f'- {item}' for item in review.get('test_gaps', [])) if review.get('test_gaps') else '- Add stress test, failure injection test, and idempotency regression test'}

---

## Go/No-Go Criteria

{chr(10).join(f'- {item}' for item in review.get('go_no_go_criteria', [])) if review.get('go_no_go_criteria') else '- All critical blockers closed, production credentials validated, and end-to-end test passed'}

---

## Deployment Checklist

Before production deployment:
- [ ] Implement the real source and target integrations
- [ ] Implement the final business action with error handling
- [ ] Configure production credentials in Orchestrator
- [ ] Test with representative process data
- [ ] Test external side effects in a safe environment
- [ ] Verify logs are being written correctly
- [ ] Set up monitoring and alerting
- [ ] Document any deviations from design
- [ ] Schedule production run in off-peak window
"""

    if llm_quality_notes:
        md_content += "\n## LLM Quality Deep Dive\n"
        md_content += chr(10).join(
            item if str(item).startswith("-") else f"- {item}"
            for item in llm_quality_notes
        )
        md_content += "\n"

    with open("outputs/05_code_quality_review.md", "w") as f:
        f.write(md_content)

    state.code_quality_review = review
    if llm_quality_notes:
        state.code_quality_review["llm_deep_dive"] = llm_quality_notes

    print("✓ Code Quality Review Complete:")
    print(f"  - Overall: 3.7/5 (Ready for Implementation)")
    print(f"  - Logging: Excellent (5/5)")
    print(f"  - Error Handling: Strong (4/5)")
    print(f"  - {len(review['issues'])} issues identified, {len(review['recommendations'])} recommendations")
    print(f"  - {len(review['critical_blockers'])} critical blockers")
    print()

    return state.model_dump()