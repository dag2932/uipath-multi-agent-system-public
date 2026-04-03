import asyncio
from graph.orchestrator import create_graph
from state import AgentState

async def main():
    import sys

    print("Vincent Vega: Please describe the business process you want to automate")
    if sys.stdin.isatty():
        process_description = input("> ").strip()
    else:
        process_description = sys.stdin.read().strip()

    if not process_description:
        print("No description provided. Exiting.")
        return

    # Load uipath-rpa-workflows skill content as design reference context
    import pathlib
    skill_md_path = pathlib.Path(__file__).resolve().parents[1] / 'skills' / 'uipath-rpa-workflows' / 'SKILL.md'
    skill_text = ''
    if skill_md_path.exists():
        skill_text = skill_md_path.read_text(encoding='utf-8')

    initial_state = AgentState(
        process_description=process_description,
        skill_context=skill_text,
        agent_context={
            'requirements': 'Follow requirement discovery from uipath-rpa-workflows with explicit trigger, error handling, no duplicate notifications.',
            'design': 'Use design principles from the rpa workflow architect skill (discovery-first, validate after each change).',
            'build': 'Generate only minimal XAML with iterative validation and ensure package docs are used.',
            'documentation': 'Include all sections as per uipath-rpa-workflows: functional overview, integration, monitoring.'
        },
        context_overrides={}
    )

    graph = create_graph()
    final_state_dict = await graph.ainvoke(initial_state.model_dump())
    final_state = AgentState(**final_state_dict)

    print("\nFinal Consolidation (Professor X):")
    print("Completed artifacts:")
    print("- 01_requirements.md")
    print("- 02_solution_design.md")
    print("- 03_build_notes.md")
    print("- 04_documentation.md")
    print("- 05_code_quality_review.md")
    print("- UiPath project artifacts in outputs/")
    if final_state.errors:
        print("Errors encountered:", final_state.errors)
    print("Next steps: Review artifacts and deploy as needed.")

if __name__ == "__main__":
    asyncio.run(main())