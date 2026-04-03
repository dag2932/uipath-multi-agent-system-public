import os
import json
import pathlib
import re
from typing import Any, Dict, Optional

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


def compact_text(value: Any, max_chars: int = 400) -> str:
    """Return a compact single-line representation to keep prompts bounded."""
    if value is None:
        return ""
    text = str(value).replace("\n", " ").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "..."


def build_reasoning_context(state: Any, stage: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build a normalized context packet consumed by LLM prompts across agents."""
    requirements = getattr(state, "requirements", {}) or {}
    design = getattr(state, "solution_design", {}) or {}
    build = getattr(state, "build_artifacts", {}) or {}
    stage_quality = getattr(state, "stage_quality_checks", {}) or {}
    handovers = getattr(state, "lifecycle_handover", {}) or {}
    briefings = getattr(state, "briefings", {}) or {}

    packet = {
        "stage": stage,
        "process_overview": compact_text(requirements.get("process_overview") or getattr(state, "process_description", ""), 600),
        "systems": requirements.get("systems", []),
        "business_rules": requirements.get("business_rules", [])[:12],
        "exceptions": requirements.get("exceptions", [])[:12],
        "open_questions": requirements.get("open_questions", [])[:10],
        "upstream_quality": stage_quality,
        "handover_packets": handovers,
        "briefings": {k: compact_text(v, 450) for k, v in briefings.items()},
        "design_summary": {
            "architecture": design.get("architecture"),
            "reframework_decision": design.get("reframework_decision"),
            "dispatcher_performer": design.get("dispatcher_performer"),
        },
        "build_summary": {
            "project_dir": build.get("project_dir"),
            "workflow_files": build.get("workflow_files", []),
            "workflow_type": build.get("workflow_type"),
        },
    }

    if extra:
        packet["extra"] = extra
    return packet


def invoke_llm_json(llm_instance: Any, system_prompt: str, user_prompt: str) -> Optional[Dict[str, Any]]:
    """Invoke chat model and extract JSON output from response content."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    response = llm_instance.invoke(messages)
    return extract_json_object(getattr(response, "content", ""))
