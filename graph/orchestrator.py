import inspect
from typing import Any, Callable

from langgraph.graph import StateGraph, START, END
from agents.requirements_agent import requirements_agent, requirements_briefing_agent, requirements_quality_agent
from agents.design_agent import design_agent, design_briefing_agent, design_quality_agent
from agents.build_agent import build_agent, build_briefing_agent, build_quality_agent
from agents.documentation_agent import documentation_agent, documentation_briefing_agent, documentation_quality_agent
from agents.quality_agent import quality_agent
from agents.approval_gates import (
    approval_gate_requirements, approval_gate_design, 
    approval_gate_build, approval_gate_final
)
from agents.end_nodes import (
    delivery_complete, build_failed, documentation_failed, quality_failed,
    requirements_approved, design_approved, build_approved
)
from utilities.conditional_routing import (
    route_after_requirements_quality, route_after_requirements_approval,
    route_after_design_quality, route_after_design_approval,
    route_after_build_quality, route_after_build_approval,
    route_after_documentation_quality, route_after_quality_assessment,
    route_after_final_approval
)
from core.state import AgentState
from core.runtime import (
    init_run_state,
    should_skip_completed_node,
    mark_node_completed,
    start_stage_timer,
    append_telemetry,
    save_checkpoint,
)


def _to_state(raw_state: Any) -> AgentState:
    if isinstance(raw_state, AgentState):
        return raw_state
    return AgentState(**raw_state)


def _instrument_node(node_name: str, node_fn: Callable[[dict], dict]) -> Callable[[dict], dict]:
    async def _wrapped(raw_state: dict) -> dict:
        state = init_run_state(_to_state(raw_state))

        if should_skip_completed_node(state, node_name):
            append_telemetry(state, node_name, status="skipped", skipped=True)
            return state.model_dump()

        started = start_stage_timer()
        try:
            node_out = node_fn(state)
            if inspect.isawaitable(node_out):
                node_out = await node_out
            if isinstance(node_out, AgentState):
                next_state = node_out
            elif isinstance(node_out, dict):
                merged = state.model_dump()
                merged.update(node_out)
                next_state = AgentState(**merged)
            else:
                raise TypeError(f"Node '{node_name}' returned unsupported type: {type(node_out).__name__}")

            # Preserve runtime metadata if a node drops unknown fields.
            if not next_state.run_id:
                next_state.run_id = state.run_id
            if not next_state.run_meta:
                next_state.run_meta = dict(state.run_meta)
            if not next_state.telemetry:
                next_state.telemetry = list(state.telemetry)
            if not next_state.errors and state.errors:
                next_state.errors = list(state.errors)

            duration_ms = int((start_stage_timer() - started) * 1000)
            mark_node_completed(next_state, node_name)
            append_telemetry(next_state, node_name, status="ok", duration_ms=duration_ms)
            save_checkpoint(next_state, node_name=node_name, failed=False)
            return next_state.model_dump()
        except Exception as exc:
            duration_ms = int((start_stage_timer() - started) * 1000)
            state.errors.append(f"{node_name}: {exc}")
            append_telemetry(state, node_name, status="error", duration_ms=duration_ms, error=str(exc))
            save_checkpoint(state, node_name=node_name, failed=True)
            raise

    return _wrapped


def create_graph():
    """
    Create LangGraph orchestrator with conditional edges and approval gates.
    
    Architecture:
    - Linear core execution: briefing → agent → quality → next stage
    - Conditional routing: Quality checks trigger approval gates
    - Early stopping: Critical failures or rejections halt pipeline
    - Caching: Briefing data reused across stages
    """
    workflow = StateGraph(AgentState)

    # ===== CORE AGENT NODES =====
    workflow.add_node("requirements_briefing", _instrument_node("requirements_briefing", requirements_briefing_agent))
    workflow.add_node("requirements", _instrument_node("requirements", requirements_agent))
    workflow.add_node("requirements_quality", _instrument_node("requirements_quality", requirements_quality_agent))
    
    workflow.add_node("design_briefing", _instrument_node("design_briefing", design_briefing_agent))
    workflow.add_node("design", _instrument_node("design", design_agent))
    workflow.add_node("design_quality", _instrument_node("design_quality", design_quality_agent))
    
    workflow.add_node("build_briefing", _instrument_node("build_briefing", build_briefing_agent))
    workflow.add_node("build", _instrument_node("build", build_agent))
    workflow.add_node("build_quality", _instrument_node("build_quality", build_quality_agent))
    
    workflow.add_node("documentation_briefing", _instrument_node("documentation_briefing", documentation_briefing_agent))
    workflow.add_node("documentation", _instrument_node("documentation", documentation_agent))
    workflow.add_node("documentation_quality", _instrument_node("documentation_quality", documentation_quality_agent))
    
    workflow.add_node("quality", _instrument_node("quality", quality_agent))

    # ===== APPROVAL GATE NODES =====
    workflow.add_node("requirements_approval", _instrument_node("requirements_approval", approval_gate_requirements))
    workflow.add_node("design_approval", _instrument_node("design_approval", approval_gate_design))
    workflow.add_node("build_approval", _instrument_node("build_approval", approval_gate_build))
    workflow.add_node("final_approval", _instrument_node("final_approval", approval_gate_final))

    # ===== END STATE NODES =====
    workflow.add_node("delivery", _instrument_node("delivery", delivery_complete))
    workflow.add_node("build_failed", _instrument_node("build_failed", build_failed))
    workflow.add_node("documentation_failed", _instrument_node("documentation_failed", documentation_failed))
    workflow.add_node("quality_failed", _instrument_node("quality_failed", quality_failed))
    workflow.add_node("requirements_approved", _instrument_node("requirements_approved", requirements_approved))
    workflow.add_node("design_approved", _instrument_node("design_approved", design_approved))
    workflow.add_node("build_approved", _instrument_node("build_approved", build_approved))

    # ===== CORE EDGES (Linear flow) =====
    workflow.add_edge(START, "requirements_briefing")
    workflow.add_edge("requirements_briefing", "requirements")
    workflow.add_edge("requirements", "requirements_quality")
    
    workflow.add_edge("design_briefing", "design")
    workflow.add_edge("design", "design_quality")
    
    workflow.add_edge("build_briefing", "build")
    workflow.add_edge("build", "build_quality")
    
    workflow.add_edge("documentation_briefing", "documentation")
    workflow.add_edge("documentation", "documentation_quality")

    # ===== CONDITIONAL EDGES (Quality-driven routing) =====
    # After requirements quality check: route to approval gate or proceed
    workflow.add_conditional_edges(
        "requirements_quality",
        route_after_requirements_quality,
        {
            "requirements_approval": "requirements_approval",
            "design_briefing": "design_briefing"
        }
    )
    
    # After requirements approval: proceed or end
    workflow.add_conditional_edges(
        "requirements_approval",
        route_after_requirements_approval,
        {
            "requirements_approved": "requirements_approved",
            "design_briefing": "design_briefing"
        }
    )
    
    # After design quality check: route to approval gate or proceed
    workflow.add_conditional_edges(
        "design_quality",
        route_after_design_quality,
        {
            "design_approval": "design_approval",
            "build_briefing": "build_briefing"
        }
    )
    
    # After design approval: proceed or end
    workflow.add_conditional_edges(
        "design_approval",
        route_after_design_approval,
        {
            "design_approved": "design_approved",
            "build_briefing": "build_briefing"
        }
    )
    
    # After build quality check: route to approval, documentation, or fail
    workflow.add_conditional_edges(
        "build_quality",
        route_after_build_quality,
        {
            "build_approval": "build_approval",
            "build_failed": "build_failed",
            "documentation_briefing": "documentation_briefing"
        }
    )
    
    # After build approval: proceed or end
    workflow.add_conditional_edges(
        "build_approval",
        route_after_build_approval,
        {
            "build_approved": "build_approved",
            "documentation_briefing": "documentation_briefing"
        }
    )
    
    # After documentation quality check: proceed to quality or fail
    workflow.add_conditional_edges(
        "documentation_quality",
        route_after_documentation_quality,
        {
            "documentation_failed": "documentation_failed",
            "quality": "quality"
        }
    )
    
    # After final quality assessment: route to approval, delivery, or fail
    workflow.add_conditional_edges(
        "quality",
        route_after_quality_assessment,
        {
            "final_approval": "final_approval",
            "delivery": "delivery",
            "quality_failed": "quality_failed"
        }
    )
    
    # After final approval: delivery or fail
    workflow.add_conditional_edges(
        "final_approval",
        route_after_final_approval,
        {
            "delivery": "delivery",
            "quality_failed": "quality_failed"
        }
    )

    # ===== FINAL EDGES (All paths lead to END) =====
    workflow.add_edge("delivery", END)
    workflow.add_edge("requirements_approved", END)
    workflow.add_edge("design_approved", END)
    workflow.add_edge("build_approved", END)
    workflow.add_edge("build_failed", END)
    workflow.add_edge("documentation_failed", END)
    workflow.add_edge("quality_failed", END)

    return workflow.compile()