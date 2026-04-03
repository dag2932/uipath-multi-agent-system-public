from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from agents.requirements_agent import requirements_agent, requirements_briefing_agent, requirements_quality_agent
from agents.design_agent import design_agent, design_briefing_agent, design_quality_agent
from agents.build_agent import build_agent, build_briefing_agent, build_quality_agent
from agents.documentation_agent import documentation_agent, documentation_briefing_agent, documentation_quality_agent
from agents.quality_agent import quality_agent
from state import AgentState

def create_graph():
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("requirements_briefing", requirements_briefing_agent)
    workflow.add_node("requirements", requirements_agent)
    workflow.add_node("requirements_quality", requirements_quality_agent)
    workflow.add_node("design_briefing", design_briefing_agent)
    workflow.add_node("design", design_agent)
    workflow.add_node("design_quality", design_quality_agent)
    workflow.add_node("build_briefing", build_briefing_agent)
    workflow.add_node("build", build_agent)
    workflow.add_node("build_quality", build_quality_agent)
    workflow.add_node("documentation_briefing", documentation_briefing_agent)
    workflow.add_node("documentation", documentation_agent)
    workflow.add_node("documentation_quality", documentation_quality_agent)
    workflow.add_node("quality", quality_agent)

    # Define edges
    workflow.add_edge(START, "requirements_briefing")
    workflow.add_edge("requirements_briefing", "requirements")
    workflow.add_edge("requirements", "requirements_quality")
    workflow.add_edge("requirements_quality", "design_briefing")

    workflow.add_edge("design_briefing", "design")
    workflow.add_edge("design", "design_quality")
    workflow.add_edge("design_quality", "build_briefing")

    workflow.add_edge("build_briefing", "build")
    workflow.add_edge("build", "build_quality")
    workflow.add_edge("build_quality", "documentation_briefing")

    workflow.add_edge("documentation_briefing", "documentation")
    workflow.add_edge("documentation", "documentation_quality")
    workflow.add_edge("documentation_quality", "quality")
    workflow.add_edge("quality", END)


    # For parallel: build and documentation in parallel
    # But LangGraph sequential by default, for parallel need conditional or separate branches
    # For simplicity, since it's async, but to make parallel, use add_edge with conditions or separate paths
    # For now, sequential, but can run build and doc in parallel if needed

    return workflow.compile()

# For human gates, we can add conditional edges
# But for simplicity, assume approvals are handled inside agents with input()