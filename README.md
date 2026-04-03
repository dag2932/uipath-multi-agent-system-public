# UiPath Multi-Agent Automation Builder

Technical agent system for transforming one process description into five delivery artifacts and a UiPath scaffold.

## System Components

| Component | Responsibility | Primary Modules |
|---|---|---|
| Orchestrator | Compiles and executes the state graph | graph/orchestrator.py |
| Shared State | Typed cross-node contract | core/state.py |
| Runtime | Checkpoints, resume, telemetry, memory snapshots | core/runtime.py |
| Stage Agents | Requirements, design, build, documentation, quality generation | agents/*.py |
| Governance | Approval gates and terminal outcomes | agents/approval_gates.py, agents/end_nodes.py |
| Routing | Conditional edges based on quality and approvals | utilities/conditional_routing.py |
| Prompt Layer | Stage-specific system prompts | prompts/*.md |

## Execution Model

Graph path:
1. requirements_briefing
2. requirements
3. requirements_quality
4. design_briefing
5. design
6. design_quality
7. build_briefing
8. build
9. build_quality
10. documentation_briefing
11. documentation
12. documentation_quality
13. quality
14. delivery or failure end node

Each node is instrumented for checkpointing and telemetry.

## Runtime Contracts

### Agent State

AgentState includes:
- process inputs and phase artifacts
- quality checks and handover packets
- governance state (human_gates)
- runtime state (run_id, run_meta, telemetry, agent_memory)

### LLM Policy

- LLM_FIRST=true uses model-first generation with deterministic fallback
- LLM_REQUIRED=true fails run if model is unavailable
- JSON schema validation with retries is enforced in LLM-enhanced stages

## Checkpoint and Memory

At every node completion or failure:
1. Full state is saved in a checkpoint file.
2. A compact memory snapshot is appended to run memory stream.
3. Telemetry event is appended with node status and duration.

This creates both full recovery state and a lightweight replayable memory timeline.

## Run

### Interactive

```bash
python main.py
```

### Non-interactive

```bash
export USE_CASE_PROJECT_DIR="outputs/custom_use_case_project"
export LLM_MODEL="gpt-4o-mini"
export LLM_FIRST="true"
export LLM_REQUIRED="false"
echo "Automate monthly contract reminders" | python main.py
```

## Artifacts

### Functional outputs

- outputs/01_requirements.md
- outputs/02_solution_design.md
- outputs/03_build_notes.md
- outputs/04_documentation.md
- outputs/05_code_quality_review.md
- outputs/uipath_project/ (default) or custom USE_CASE_PROJECT_DIR

### Runtime outputs

- artifacts/checkpoints/<run_id>/*.json
- artifacts/memory/<run_id>.ndjson
- artifacts/telemetry/<run_id>.json

## Repository Layout

- agents/
- core/
- graph/
- prompts/
- utilities/
- docs/
- tests/
- outputs/
- artifacts/

## Requirements

- Python 3.9+
- Optional: OPENAI_API_KEY for LLM-first mode
- Optional: UiPath Studio to execute generated workflows