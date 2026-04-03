import asyncio
from graph.orchestrator import create_graph
from state import AgentState
from config import is_llm_first, is_llm_required


def _prompt_user(prompt: str):
    """Read interactive user input and handle cancellation cleanly."""
    try:
        return input(prompt).strip()
    except EOFError:
        return ""
    except KeyboardInterrupt:
        print("\nCancelled by user. Exiting.")
        return None

async def main():
    import sys
    import os

    print("\n" + "="*60)
    print("UiPath Multi-Agent Automation Builder")
    print("="*60 + "\n")

    # Step 1: API Key Configuration
    print("Step 1: OpenAI API Key Configuration (LLM-first)")
    print("-" * 40)
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    
    if sys.stdin.isatty():
        if api_key:
            use_existing = _prompt_user("Use existing API key? (y/n) [y]: ")
            if use_existing is None:
                return
            use_existing = use_existing.lower()
            if use_existing != 'n':
                print(f"✓ Using existing API key")
            else:
                api_key = _prompt_user("Enter OpenAI API Key (or press Enter to skip): ")
                if api_key is None:
                    return
        else:
            api_key = _prompt_user("Enter OpenAI API Key (or press Enter to skip): ")
            if api_key is None:
                return
        
        if api_key:
            os.environ["OPENAI_API_KEY"] = api_key
            print("✓ API Key configured\n")
        else:
            print("⚠ No API Key provided. LLM-first features will degrade to deterministic fallbacks.\n")
    
    # Step 2: Model Selection
    print("Step 2: Model Selection")
    print("-" * 40)
    available_models = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4"
    ]
    
    current_model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    
    if sys.stdin.isatty():
        print(f"Available models:")
        for i, model in enumerate(available_models, 1):
            marker = " (current)" if model == current_model else ""
            print(f"  {i}. {model}{marker}")
        
        choice = _prompt_user(f"\nSelect model (1-{len(available_models)}) or press Enter for {current_model}: ")
        if choice is None:
            return
        
        if choice and choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(available_models):
                current_model = available_models[idx]
        
        os.environ["LLM_MODEL"] = current_model
        print(f"✓ Using model: {current_model}\n")

    # LLM-first runtime defaults (can be overridden via environment).
    os.environ.setdefault("LLM_FIRST", "true")
    os.environ.setdefault("LLM_REQUIRED", "false")
    print(f"LLM-first mode: {'enabled' if is_llm_first() else 'disabled'}")
    print(f"LLM required mode: {'enabled' if is_llm_required() else 'disabled'}\n")
    
    # Step 3: Process Description
    print("Step 3: Process Description")
    print("-" * 40)
    print("Describe the business process you want to automate:")
    
    if sys.stdin.isatty():
        process_description = _prompt_user("> ")
        if process_description is None:
            return
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
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCancelled by user. Exiting.")