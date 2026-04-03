"""
Approval gate nodes for human-in-the-loop decision making.

Each approval gate allows stakeholders to review stage outputs and approve,
request changes, or escalate before proceeding.
"""

from typing import Dict, Any
from core.state import AgentState


async def approval_gate_requirements(state: AgentState) -> Dict[str, Any]:
    """
    Approval gate for requirements stage.
    
    Reviews extracted requirements and quality assessment before proceeding to design.
    Can auto-approve (no gate) or require manual approval.
    """
    requirements = state.requirements or {}
    quality = state.stage_quality_checks.get("requirements", {})
    blockers = quality.get("blockers", [])
    
    # Check if approval required
    require_approval = state.context_overrides.get("require_approval", False)
    
    if require_approval and blockers:
        # Requires approval due to blockers
        print("\n" + "="*60)
        print("APPROVAL GATE: Requirements Stage")
        print("="*60)
        print(f"\nExtracted Entity: {requirements.get('entities', {}).get('primary', 'Unknown')}")
        print(f"Systems: {requirements.get('systems', [])}")
        print(f"Confidence: {requirements.get('confidence', {})}")
        print(f"\n⚠️  Blockers found:")
        for blocker in blockers:
            print(f"  - {blocker}")
        
        decision = input("\nApprove? (yes/no/changes): ").strip().lower()
        
        if decision == "no":
            return {
                "human_gates": {
                    **state.human_gates,
                    "requirements_approved": False,
                    "requirements_blocked": True
                },
                "current_phase": "requirements_approval_rejected"
            }
        elif decision == "changes":
            feedback = input("Provide feedback for requirements revision: ").strip()
            return {
                "human_gates": {
                    **state.human_gates,
                    "requirements_approved": False,
                    "requirements_feedback": feedback
                },
                "current_phase": "requirements_feedback_pending"
            }
    
    # Auto-approve or approval passed
    return {
        "human_gates": {
            **state.human_gates,
            "requirements_approved": True
        }
    }


async def approval_gate_design(state: AgentState) -> Dict[str, Any]:
    """
    Approval gate for design stage.
    
    Reviews architecture decisions, exception handling, and complexity assessment.
    """
    design = state.design or {}
    quality = state.stage_quality_checks.get("design", {})
    blockers = quality.get("blockers", [])
    
    require_approval = state.context_overrides.get("require_approval", False)
    
    if require_approval and blockers:
        print("\n" + "="*60)
        print("APPROVAL GATE: Design Stage")
        print("="*60)
        print(f"\nArchitecture: {design.get('architecture', 'Unknown')}")
        print(f"Complexity Score: {design.get('complexity_score', 0)}/5")
        print(f"REFramework: {design.get('reframework_decision', False)}")
        
        print(f"\n⚠️  Blockers found:")
        for blocker in blockers:
            print(f"  - {blocker}")
        
        decision = input("\nApprove design? (yes/no/changes): ").strip().lower()
        
        if decision == "no":
            return {
                "human_gates": {
                    **state.human_gates,
                    "design_approved": False,
                    "design_blocked": True
                },
                "current_phase": "design_approval_rejected"
            }
        elif decision == "changes":
            feedback = input("Provide feedback for design revision: ").strip()
            return {
                "human_gates": {
                    **state.human_gates,
                    "design_approved": False,
                    "design_feedback": feedback
                },
                "current_phase": "design_feedback_pending"
            }
    
    return {
        "human_gates": {
            **state.human_gates,
            "design_approved": True
        }
    }


async def approval_gate_build(state: AgentState) -> Dict[str, Any]:
    """
    Approval gate for build stage.
    
    Reviews generated workflows and project structure.
    """
    build = state.build or {}
    quality = state.stage_quality_checks.get("build", {})
    blockers = quality.get("blockers", [])
    
    require_approval = state.context_overrides.get("require_approval", False)
    
    if require_approval and blockers:
        print("\n" + "="*60)
        print("APPROVAL GATE: Build Stage")
        print("="*60)
        print(f"\nProject: {build.get('project_name', 'Unknown')}")
        workflows = build.get("generated_workflows", [])
        print(f"Workflows Generated: {len(workflows)}")
        for wf in workflows[:5]:
            print(f"  - {wf.get('name', 'Unknown')}")
        if len(workflows) > 5:
            print(f"  ... and {len(workflows) - 5} more")
        
        print(f"\n⚠️  Blockers found:")
        for blocker in blockers:
            print(f"  - {blocker}")
        
        decision = input("\nApprove build? (yes/no/changes): ").strip().lower()
        
        if decision == "no":
            return {
                "human_gates": {
                    **state.human_gates,
                    "build_approved": False,
                    "build_blocked": True
                },
                "current_phase": "build_approval_rejected"
            }
        elif decision == "changes":
            feedback = input("Provide feedback for build revision: ").strip()
            return {
                "human_gates": {
                    **state.human_gates,
                    "build_approved": False,
                    "build_feedback": feedback
                },
                "current_phase": "build_feedback_pending"
            }
    
    return {
        "human_gates": {
            **state.human_gates,
            "build_approved": True
        }
    }


async def approval_gate_final(state: AgentState) -> Dict[str, Any]:
    """
    Final approval gate before delivery.
    
    Reviews entire lifecycle and readiness assessment.
    """
    quality = state.stage_quality_checks.get("quality", {})
    blockers = quality.get("blockers", [])
    readiness = quality.get("readiness", "UNKNOWN")
    
    require_approval = state.context_overrides.get("require_approval", False)
    
    print("\n" + "="*60)
    print("FINAL APPROVAL GATE")
    print("="*60)
    print(f"\nReadiness: {readiness}")
    print(f"Blockers: {len(blockers)}")
    if blockers:
        for blocker in blockers[:5]:
            print(f"  - {blocker}")
        if len(blockers) > 5:
            print(f"  ... and {len(blockers) - 5} more")
    
    decision = input("\nApprove for handoff? (yes/no): ").strip().lower()
    
    approval_status = "approved" if decision == "yes" else "rejected"
    
    return {
        "human_gates": {
            **state.human_gates,
            "final_approved": decision == "yes"
        },
        "current_phase": f"final_approval_{approval_status}"
    }
