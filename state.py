from typing import Optional, Dict, Any, List
from pydantic import BaseModel

class AgentState(BaseModel):
    process_description: Optional[str] = None
    skill_context: Optional[str] = None
    requirements: Optional[Dict[str, Any]] = None
    solution_design: Optional[Dict[str, Any]] = None
    design: Optional[Dict[str, Any]] = None
    build_artifacts: Optional[Dict[str, Any]] = None
    build: Optional[Dict[str, Any]] = None
    documentation: Optional[str] = None
    documentation_briefing: Optional[Dict[str, Any]] = None
    code_quality_review: Optional[Dict[str, Any]] = None
    briefings: Dict[str, str] = {}
    stage_quality_checks: Dict[str, Dict[str, Any]] = {}
    agent_context: Dict[str, Any] = {}
    context_overrides: Dict[str, Any] = {}
    human_gates: Dict[str, bool] = {"requirements_approved": False, "design_approved": False}
    current_phase: str = "start"
    errors: List[str] = []
    project_dir: Optional[str] = None

    def get_phase_context(self, phase: str) -> Optional[str]:
        if phase in self.context_overrides and self.context_overrides[phase]:
            return self.context_overrides[phase]
        if phase in self.agent_context and self.agent_context[phase]:
            return self.agent_context[phase]
        return None