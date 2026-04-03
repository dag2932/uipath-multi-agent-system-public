"""
End nodes for various completion/termination states.

These nodes represent different outcomes of the pipeline execution.
"""

from typing import Dict, Any
from core.state import AgentState


async def delivery_complete(state: AgentState) -> Dict[str, Any]:
    """
    Successful delivery completion.
    
    All stages passed, approvals obtained, ready for handoff.
    """
    return {
        "current_phase": "delivery_complete",
        "human_gates": {
            **state.human_gates,
            "delivery_ready": True
        }
    }


async def build_failed(state: AgentState) -> Dict[str, Any]:
    """
    Build stage failed with critical errors.
    
    Workflow generation or project structure incorrect; cannot proceed.
    """
    quality = state.stage_quality_checks.get("build", {})
    errors = quality.get("blockers", [])
    
    return {
        "current_phase": "build_failed",
        "errors": state.errors + errors
    }


async def documentation_failed(state: AgentState) -> Dict[str, Any]:
    """
    Documentation stage failed with critical errors.
    
    Cannot generate proper documentation; review artifacts.
    """
    quality = state.stage_quality_checks.get("documentation", {})
    errors = quality.get("blockers", [])
    
    return {
        "current_phase": "documentation_failed",
        "errors": state.errors + errors
    }


async def quality_failed(state: AgentState) -> Dict[str, Any]:
    """
    Final quality assessment determined system is not ready.
    
    Blockers identified in final review; requires significant changes.
    """
    quality = state.stage_quality_checks.get("quality", {})
    blockers = quality.get("blockers", [])
    
    return {
        "current_phase": "quality_failed",
        "errors": state.errors + blockers
    }


async def requirements_approved(state: AgentState) -> Dict[str, Any]:
    """
    Requirements stage approval completed (approved or rejected).
    
    If approved, system continues. If rejected, terminates here.
    """
    approved = state.human_gates.get("requirements_approved", False)
    feedback = state.human_gates.get("requirements_feedback", "")
    
    phase = "blocked" if not approved else "approved"
    
    return {
        "current_phase": f"requirements_{phase}",
        "errors": state.errors + ([feedback] if feedback and not approved else [])
    }


async def design_approved(state: AgentState) -> Dict[str, Any]:
    """
    Design stage approval completed (approved or rejected).
    """
    approved = state.human_gates.get("design_approved", False)
    feedback = state.human_gates.get("design_feedback", "")
    
    phase = "blocked" if not approved else "approved"
    
    return {
        "current_phase": f"design_{phase}",
        "errors": state.errors + ([feedback] if feedback and not approved else [])
    }


async def build_approved(state: AgentState) -> Dict[str, Any]:
    """
    Build stage approval completed (approved or rejected).
    """
    approved = state.human_gates.get("build_approved", False)
    feedback = state.human_gates.get("build_feedback", "")
    
    phase = "blocked" if not approved else "approved"
    
    return {
        "current_phase": f"build_{phase}",
        "errors": state.errors + ([feedback] if feedback and not approved else [])
    }
