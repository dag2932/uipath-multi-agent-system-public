# Agent Configuration File

## System Prompts Directory
All agent system prompts are stored in `prompts/` with the naming convention:
- `{agent_name}_system.md`

Agents:
- `requirements_system.md` — Vincent Vega, Requirements Discovery Agent
- `design_system.md` — Jules Winnfield, Solution Design Architect
- `build_system.md` — Butch Coolidge, RPA Implementation Engineer
- `documentation_system.md` — Mia Wallace, Technical Documentation Specialist
- `quality_system.md` — Marsellus Wallace, Quality Reviewer

## Usage

### Loading Prompts at Runtime
Agents automatically load their system prompts on initialization:

```python
from utils import load_system_prompt

system_prompt = load_system_prompt('requirements')
state.agent_context['requirements_system_prompt'] = system_prompt
```

### Customizing System Prompts
1. Edit the desired `prompts/{agent_name}_system.md` file
2. Changes take effect immediately on next agent run (no code recompile)
3. Prompts are cached in `state.agent_context` for the session

### Overriding Context at Runtime
Pass context overrides via `state.context_overrides`:

```python
state.context_overrides['requirements'] = "Use GDPR compliance rules..."
state.context_overrides['design'] = "Prefer microservice architecture..."
```

Both override and default context are available to agents via:
```python
phase_context = state.get_phase_context('requirements')
```

## Prompt Structure

Each system prompt follows this pattern:

```markdown
# {Agent Name} System Prompt

You are **{Character Name}**, the {Role}.

## Role
[What the agent does]

## Principles
1. [Principle 1]
2. [Principle 2]
...

## Output
[What the agent produces]

## Context
[Relevant skill/pattern context]
```

## Extending with New Agents

To add a new agent:

1. Create `prompts/{new_agent_name}_system.md` with system prompt
2. Import `load_system_prompt` in agent code
3. Call `load_system_prompt('{new_agent_name}')` in agent initialization
4. Store in `state.agent_context['{new_agent_name}_system_prompt']`

Done! No additional configuration files needed.

---

**Last Updated:** 2026-04-03
