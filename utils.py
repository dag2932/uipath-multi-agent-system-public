import os
import pathlib

def load_system_prompt(agent_name: str) -> str:
    """
    Load system prompt for an agent from prompts/ directory.
    
    Args:
        agent_name: Agent identifier (e.g., 'requirements', 'design', 'build', 'documentation', 'quality')
    
    Returns:
        System prompt content as string, or empty string if file not found.
    """
    prompt_path = pathlib.Path(__file__).parent / 'prompts' / f'{agent_name}_system.md'
    
    if prompt_path.exists():
        return prompt_path.read_text(encoding='utf-8')
    else:
        return f"[System prompt not found: {prompt_path}]"

def display_system_prompt(prompt_text: str, agent_persona: str):
    """
    Display system prompt to user with formatting.
    
    Args:
        prompt_text: Full system prompt content
        agent_persona: Display name of agent (e.g., 'Vincent Vega')
    """
    print(f"\n[System Prompt - {agent_persona}]")
    print("=" * 60)
    print(prompt_text)
    print("=" * 60)
    print()
