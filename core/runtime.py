import json
import pathlib
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from core.state import AgentState


BASE_DIR = pathlib.Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = BASE_DIR / "artifacts"
CHECKPOINTS_DIR = ARTIFACTS_DIR / "checkpoints"
TELEMETRY_DIR = ARTIFACTS_DIR / "telemetry"
MEMORY_DIR = ARTIFACTS_DIR / "memory"


def _ensure_runtime_dirs() -> None:
    CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)
    TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def _utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _to_jsonable(value: Any, seen: Optional[set] = None) -> Any:
    if seen is None:
        seen = set()

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    obj_id = id(value)
    if obj_id in seen:
        return "<circular_reference>"

    if isinstance(value, dict):
        seen.add(obj_id)
        out = {str(k): _to_jsonable(v, seen) for k, v in value.items()}
        seen.remove(obj_id)
        return out

    if isinstance(value, (list, tuple, set)):
        seen.add(obj_id)
        out = [_to_jsonable(v, seen) for v in value]
        seen.remove(obj_id)
        return out

    return str(value)


def init_run_state(state: AgentState) -> AgentState:
    _ensure_runtime_dirs()
    if not state.run_id:
        state.run_id = f"run_{uuid.uuid4().hex[:12]}"

    state.run_meta.setdefault("started_at", _utc_now())
    state.run_meta.setdefault("completed_nodes", [])
    state.run_meta.setdefault("resume_enabled", True)
    state.run_meta.setdefault("llm_policy", {})

    return state


def should_skip_completed_node(state: AgentState, node_name: str) -> bool:
    completed = state.run_meta.get("completed_nodes", [])
    return node_name in completed


def mark_node_completed(state: AgentState, node_name: str) -> None:
    completed = state.run_meta.setdefault("completed_nodes", [])
    if node_name not in completed:
        completed.append(node_name)


def start_stage_timer() -> float:
    return time.perf_counter()


def append_telemetry(
    state: AgentState,
    node_name: str,
    status: str,
    duration_ms: Optional[int] = None,
    error: Optional[str] = None,
    skipped: bool = False,
) -> None:
    state.telemetry.append(
        {
            "ts": _utc_now(),
            "run_id": state.run_id,
            "node": node_name,
            "status": status,
            "duration_ms": duration_ms,
            "error": error,
            "skipped": skipped,
        }
    )


def _build_memory_snapshot(state: AgentState, node_name: str, failed: bool) -> Dict[str, Any]:
    """Create a compact memory snapshot describing the checkpoint context."""
    requirements = state.requirements or {}
    design = state.solution_design or state.design or {}
    build = state.build_artifacts or state.build or {}
    quality = state.code_quality_review or {}

    return {
        "ts": _utc_now(),
        "run_id": state.run_id,
        "checkpoint_node": node_name,
        "failed": failed,
        "phase": state.current_phase,
        "project_dir": state.project_dir,
        "summary": {
            "systems": requirements.get("systems", []),
            "open_questions": len(requirements.get("open_questions", [])),
            "architecture": design.get("architecture"),
            "workflow_count": len(build.get("workflow_files", [])),
            "quality_score": quality.get("overall_score"),
            "errors": len(state.errors),
        },
    }


def _persist_memory_snapshot(run_id: str, snapshot: Dict[str, Any]) -> pathlib.Path:
    """Append memory snapshots to an ndjson stream for each run."""
    _ensure_runtime_dirs()
    target = MEMORY_DIR / f"{run_id}.ndjson"
    with target.open("a", encoding="utf-8") as f:
        f.write(json.dumps(_to_jsonable(snapshot), ensure_ascii=True) + "\n")
    return target


def save_checkpoint(state: AgentState, node_name: str, failed: bool = False) -> pathlib.Path:
    _ensure_runtime_dirs()
    run_id = state.run_id or "run_unknown"
    run_dir = CHECKPOINTS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    snapshot = _build_memory_snapshot(state, node_name=node_name, failed=failed)
    state.agent_memory.append(snapshot)
    _persist_memory_snapshot(run_id, snapshot)

    checkpoint_name = f"{node_name}{'_failed' if failed else ''}.json"
    target = run_dir / checkpoint_name
    safe_payload = _to_jsonable(state.model_dump())
    target.write_text(json.dumps(safe_payload, indent=2), encoding="utf-8")
    return target


def save_run_telemetry(state: AgentState) -> pathlib.Path:
    _ensure_runtime_dirs()
    run_id = state.run_id or "run_unknown"
    target = TELEMETRY_DIR / f"{run_id}.json"
    payload = {
        "run_id": run_id,
        "started_at": state.run_meta.get("started_at"),
        "finished_at": _utc_now(),
        "completed_nodes": state.run_meta.get("completed_nodes", []),
        "errors": _to_jsonable(state.errors),
        "agent_memory": _to_jsonable(state.agent_memory),
        "events": _to_jsonable(state.telemetry),
    }
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target


def load_latest_checkpoint() -> Optional[Tuple[str, Dict[str, Any], str]]:
    _ensure_runtime_dirs()
    run_dirs = [d for d in CHECKPOINTS_DIR.iterdir() if d.is_dir()]
    if not run_dirs:
        return None

    latest_run_dir = max(run_dirs, key=lambda d: d.stat().st_mtime)
    checkpoint_files = sorted(latest_run_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
    if not checkpoint_files:
        return None

    latest_checkpoint = checkpoint_files[-1]
    raw = json.loads(latest_checkpoint.read_text(encoding="utf-8"))
    node_name = latest_checkpoint.stem.replace("_failed", "")
    return latest_run_dir.name, raw, node_name
