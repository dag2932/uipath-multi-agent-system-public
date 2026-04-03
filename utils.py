import os
import json
import pathlib
import re

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


def extract_json_object(text: str):
    """Extract a JSON object from plain text or fenced markdown."""
    if not text:
        return None

    candidate = text.strip()
    fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", candidate, re.DOTALL)
    if fenced_match:
        candidate = fenced_match.group(1).strip()
    else:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = candidate[start:end + 1]

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None
