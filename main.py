import asyncio
import pathlib
from graph.orchestrator import create_graph
from core.state import AgentState
from core.config import is_llm_first, is_llm_required
from core.runtime import init_run_state, load_latest_checkpoint, save_run_telemetry


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

    resume_state = None
    if sys.stdin.isatty():
        latest = load_latest_checkpoint()
        if latest:
            run_id, raw_state, node_name = latest
            resume_choice = _prompt_user(
                f"Found checkpoint from run {run_id} (last node: {node_name}). Resume? (y/n) [y]: "
            )
            if resume_choice is None:
                return
            if resume_choice.lower() != "n":
                resume_state = AgentState(**raw_state)
                print(f"✓ Resuming run {run_id}\n")

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
    
    if resume_state is None:
        # Step 3: Use-Case Project Directory
        print("Step 3: Use-Case Project Directory")
        print("-" * 40)
        default_project_dir = "outputs/uipath_project"

        if sys.stdin.isatty():
            project_dir = _prompt_user(
                f"Enter project directory for generated use-case files [default: {default_project_dir}]: "
            )
            if project_dir is None:
                return
            project_dir = project_dir or default_project_dir
        else:
            project_dir = os.getenv("USE_CASE_PROJECT_DIR", default_project_dir)

        project_dir = str(pathlib.Path(project_dir).expanduser())
        pathlib.Path(project_dir).mkdir(parents=True, exist_ok=True)
        print(f"✓ Use-case project directory: {project_dir}\n")

        # Step 4: Process Description
        print("Step 4: Process Description")
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
        skill_md_path = pathlib.Path(__file__).resolve().parents[1] / 'skills' / 'uipath-rpa-workflows' / 'SKILL.md'
        skill_text = ''
        if skill_md_path.exists():
            skill_text = skill_md_path.read_text(encoding='utf-8')

        initial_state = AgentState(
            process_description=process_description,
            skill_context=skill_text,
            project_dir=project_dir,
            agent_context={
                'requirements': 'Follow requirement discovery from uipath-rpa-workflows with explicit trigger, error handling, no duplicate notifications.',
                'design': 'Use design principles from the rpa workflow architect skill (discovery-first, validate after each change).',
                'build': 'Generate only minimal XAML with iterative validation and ensure package docs are used.',
                'documentation': 'Include all sections as per uipath-rpa-workflows: functional overview, integration, monitoring.'
            },
            context_overrides={}
        )
    else:
        initial_state = resume_state

    initial_state = init_run_state(initial_state)
    print(f"Run ID: {initial_state.run_id}\n")

    graph = create_graph()
    final_state_dict = await graph.ainvoke(initial_state.model_dump())
    final_state = AgentState(**final_state_dict)
    telemetry_path = save_run_telemetry(final_state)
    memory_path = pathlib.Path("artifacts") / "memory" / f"{final_state.run_id}.ndjson"

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
    print(f"Telemetry: {telemetry_path}")
    print(f"Checkpoint memory: {memory_path}")
    print("Next steps: Review artifacts and deploy as needed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCancelled by user. Exiting.")