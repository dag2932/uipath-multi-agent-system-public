import os
import json
import pathlib
import re
import time
from typing import Any, Dict, Optional

def load_system_prompt(agent_name: str) -> str:
    """
    Load system prompt for an agent from prompts/ directory.
    
    Args:
        agent_name: Agent identifier (e.g., 'requirements', 'design', 'build', 'documentation', 'quality')
    
    Returns:
        System prompt content as string, or empty string if file not found.
    """
    root = pathlib.Path(__file__).resolve().parents[1]
    prompt_path = root / 'prompts' / f'{agent_name}_system.md'
    
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
    return invoke_llm_json_with_policy(
        llm_instance=llm_instance,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        required_keys=None,
        retries=2,
    )


def validate_required_keys(payload: Optional[Dict[str, Any]], required_keys: Optional[list]) -> bool:
    if not payload:
        return False
    if not required_keys:
        return True
    return all(key in payload for key in required_keys)


def invoke_llm_json_with_policy(
    llm_instance: Any,
    system_prompt: str,
    user_prompt: str,
    required_keys: Optional[list] = None,
    retries: int = 2,
    backoff_seconds: float = 0.75,
) -> Optional[Dict[str, Any]]:
    """LLM invocation with retries and minimum schema enforcement.

    Retry matrix:
    - invocation error: retry
    - parse failure: retry
    - required key missing: retry
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    last_payload: Optional[Dict[str, Any]] = None
    for attempt in range(retries + 1):
        try:
            response = llm_instance.invoke(messages)
            payload = extract_json_object(getattr(response, "content", ""))
            last_payload = payload
            if validate_required_keys(payload, required_keys):
                return payload
        except Exception:
            pass

        if attempt < retries:
            time.sleep(backoff_seconds * (2 ** attempt))

    return last_payload
