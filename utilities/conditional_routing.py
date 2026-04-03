"""
Conditional routing logic for the LangGraph orchestrator.

Routes execution based on quality checks, blockers, and approval status.
Enables early stopping and intelligent flow optimization.
"""

from core.state import AgentState


def route_after_requirements_quality(state: AgentState) -> str:
    """
    Route after requirements quality check.
    
    Options:
    - "requirements_approval" if blockers and approval required
    - "design_briefing" if no blockers or no approval required
    """
    quality = state.stage_quality_checks.get("requirements", {})
    blockers = quality.get("blockers", [])
    require_approval = state.context_overrides.get("require_approval", False)
    
    if blockers and require_approval:
        return "requirements_approval"
    
    return "design_briefing"


def route_after_requirements_approval(state: AgentState) -> str:
    """
    Route after requirements approval gate.
    
    Options:
    - "requirements_approved" (END) if rejected
    - "design_briefing" if approved
    """
    approved = state.human_gates.get("requirements_approved", True)
    
    if not approved and state.human_gates.get("requirements_blocked"):
        return "requirements_approved"  # END (rejected)
    
    if not approved and state.human_gates.get("requirements_feedback"):
        return "requirements_approved"  # END with feedback (user to iterate)
    
    return "design_briefing"


def route_after_design_quality(state: AgentState) -> str:
    """
    Route after design quality check.
    
    Options:
    - "design_approval" if blockers and approval required
    - "build_briefing" if no blockers or no approval required
    """
    quality = state.stage_quality_checks.get("design", {})
    blockers = quality.get("blockers", [])
    require_approval = state.context_overrides.get("require_approval", False)
    
    if blockers and require_approval:
        return "design_approval"
    
    return "build_briefing"


def route_after_design_approval(state: AgentState) -> str:
    """
    Route after design approval gate.
    
    Options:
    - "design_approved" (END) if rejected
    - "build_briefing" if approved
    """
    approved = state.human_gates.get("design_approved", True)
    
    if not approved and state.human_gates.get("design_blocked"):
        return "design_approved"  # END (rejected)
    
    if not approved and state.human_gates.get("design_feedback"):
        return "design_approved"  # END with feedback
    
    return "build_briefing"


def route_after_build_quality(state: AgentState) -> str:
    """
    Route after build quality check.
    
    Options:
    - "build_approval" if blockers and approval required
    - "documentation_briefing" if no blockers or no approval required
    - "build_failed" (END) if critical build failures
    """
    quality = state.stage_quality_checks.get("build", {})
    blockers = quality.get("blockers", [])
    
    # Critical build failures should halt immediately
    critical_blockers = [b for b in blockers if b.startswith("CRITICAL")]
    if critical_blockers:
        return "build_failed"  # END
    
    require_approval = state.context_overrides.get("require_approval", False)
    
    if blockers and require_approval:
        return "build_approval"
    
    return "documentation_briefing"


def route_after_build_approval(state: AgentState) -> str:
    """
    Route after build approval gate.
    
    Options:
    - "build_approved" (END) if rejected
    - "documentation_briefing" if approved
    """
    approved = state.human_gates.get("build_approved", True)
    
    if not approved and state.human_gates.get("build_blocked"):
        return "build_approved"  # END (rejected)
    
    if not approved and state.human_gates.get("build_feedback"):
        return "build_approved"  # END with feedback
    
    return "documentation_briefing"


def route_after_documentation_quality(state: AgentState) -> str:
    """
    Route after documentation quality check.
    
    Options:
    - "quality" for final assessment
    - "documentation_failed" (END) if critical doc failures
    """
    quality = state.stage_quality_checks.get("documentation", {})
    blockers = quality.get("blockers", [])
    
    critical_blockers = [b for b in blockers if b.startswith("CRITICAL")]
    if critical_blockers:
        return "documentation_failed"  # END
    
    return "quality"


def route_after_quality_assessment(state: AgentState) -> str:
    """
    Route after final quality assessment.
    
    Options:
    - "final_approval" if approval required
    - "delivery" (END) if approved
    - "quality_failed" (END) if blockers and no approval
    """
    quality = state.stage_quality_checks.get("quality", {})
    blockers = quality.get("blockers", [])
    readiness = quality.get("readiness", "UNKNOWN")
    
    require_approval = state.context_overrides.get("require_approval", False)
    
    if require_approval:
        return "final_approval"
    
    if blockers or readiness == "BLOCKED":
        return "quality_failed"  # END (blocked)
    
    return "delivery"


def route_after_final_approval(state: AgentState) -> str:
    """
    Route after final approval gate.
    
    Options:
    - "delivery" (END) if approved
    - "quality_failed" (END) if rejected
    """
    approved = state.human_gates.get("final_approved", False)
    
    return "delivery" if approved else "quality_failed"
