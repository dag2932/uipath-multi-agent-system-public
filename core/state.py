from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

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
    briefings: Dict[str, str] = Field(default_factory=dict)
    stage_quality_checks: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    agent_context: Dict[str, Any] = Field(default_factory=dict)
    context_overrides: Dict[str, Any] = Field(default_factory=dict)
    lifecycle_handover: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    human_gates: Dict[str, bool] = Field(default_factory=lambda: {"requirements_approved": False, "design_approved": False})
    current_phase: str = "start"
    errors: List[str] = Field(default_factory=list)
    project_dir: Optional[str] = None
    run_id: Optional[str] = None
    run_meta: Dict[str, Any] = Field(default_factory=dict)
    telemetry: List[Dict[str, Any]] = Field(default_factory=list)
    agent_memory: List[Dict[str, Any]] = Field(default_factory=list)

    def get_phase_context(self, phase: str) -> Optional[str]:
        if phase in self.context_overrides and self.context_overrides[phase]:
            return self.context_overrides[phase]
        if phase in self.agent_context and self.agent_context[phase]:
            return self.agent_context[phase]
        return None