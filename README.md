# UiPath Multi-Agent Automation Builder

Public technical overview for a staged agent system that turns one process description into delivery-ready RPA artifacts.

## 1. Agent System Components

| Component | Purpose | Technical Contract |
|---|---|---|
| Orchestrator | Executes stage graph | Ordered + conditional transitions across stages |
| Shared State | Single source of truth | Typed state object passed through all nodes |
| Runtime | Reliability and traceability | Checkpoint, resume, telemetry, memory snapshot persistence |
| Stage Agents | Domain transformation | Deterministic baseline + optional LLM enrichment |
| Governance | Risk control | Approval gates and terminal outcomes |
| Routing Policy | Flow control | Branching from quality/blocker/approval signals |
| Prompt Layer | LLM behavior control | Prompt loading + schema-constrained response handling |

## 2. Delivery Pipeline

1. Requirements
2. Design
3. Build
4. Documentation
5. Quality

Each stage produces artifacts and quality signals consumed by the next stage.

## 3. Reliability Model

- Node-level checkpointing
- Resume from latest successful checkpoint
- Event telemetry with node timing and status
- Checkpoint-derived memory timeline for replay/audit

## 4. Artifact Model

Functional artifacts:
- outputs/01_requirements.md
- outputs/02_solution_design.md
- outputs/03_build_notes.md
- outputs/04_documentation.md
- outputs/05_code_quality_review.md
- outputs/uipath_project or custom USE_CASE_PROJECT_DIR

Runtime artifacts:
- artifacts/checkpoints/<run_id>/<node>.json
- artifacts/memory/<run_id>.ndjson
- artifacts/telemetry/<run_id>.json

## 5. Configuration

- OPENAI_API_KEY: enable model calls
- LLM_MODEL: model selection
- LLM_FIRST: model-first with deterministic fallback
- LLM_REQUIRED: fail if model unavailable
- USE_CASE_PROJECT_DIR: output scaffold path override

## 6. Operating KPIs

- Delivery readiness rate
- Approval escalation rate
- Mean stage duration
- Critical failure concentration
- Resume/rework rate
- LLM fallback rate

## 7. Public Scope

This public repository exposes documentation only.
Implementation code is maintained in the private repository.
