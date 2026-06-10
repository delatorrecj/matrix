"""MATRIX API gateway. FastAPI + WebSocket. SDD §2, RFC §3.

`/simulate/{id}` streams the real progressive pipeline:
  ACCEPTED -> PLAYBACK_FRAME* -> DIMENSION_RESULT (per module, provenance intact)
  -> SYNTHESIS (templated; Gemini 3.1 Pro synthesis is Phase 4) -> DONE
For Milestone A it serves the cached demo scenario for a snappy stream, else runs the kernel
live. Numbers come from the kernel + equations, NEVER the LLM (glass box, PRD-F14); the
synthesis narrative cites equation_id + dataset_ids (citation guard, methods §4).

Run locally:  uvicorn matrix_api.main:app
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from pydantic import BaseModel

from matrix_api import db

# Kernel imports are guarded so the REST persistence surface (/scenario, /runs/{id},
# /audit/{id}, /validation) stays importable without eclipse-sumo/redis (bare test env,
# QAD). The WS pipeline still requires the kernel at runtime — unchanged when installed.
try:
    from matrix_kernel.modules import behavioral, ecological, social, economic, societal
    from matrix_kernel.runner import Scenario, simulate
    from matrix_kernel.trajectory import Trajectory
    from matrix_kernel.orchestrator import parse_scenario
    from matrix_kernel.synthesis import synthesize

    _KERNEL_IMPORT_ERROR: str | None = None
except ImportError as _exc:  # pragma: no cover - only without the kernel env
    behavioral = ecological = social = economic = societal = None  # type: ignore[assignment]
    Scenario = simulate = Trajectory = synthesize = None  # type: ignore[assignment]
    parse_scenario = None  # type: ignore[assignment]
    _KERNEL_IMPORT_ERROR = str(_exc)
    logging.getLogger("matrix_api").warning(
        "matrix_kernel unavailable (%s) — REST persistence endpoints only", _exc
    )

app = FastAPI(title="MATRIX API", version="0.1.0")

# app/ repo root (main.py -> matrix_api -> api -> apps -> app) for the validation report.
_APP_ROOT = Path(__file__).resolve().parents[3]


@app.on_event("startup")
def _init_persistence() -> None:
    """Choose + announce the persistence backend once (Postgres, else in-memory fallback)."""
    db.init_db()

# The event types streamed over the WS (RFC §3) -- frozen so the frontend (Track B) can mock them.
EVENT_TYPES = ("ACCEPTED", "PLAYBACK_FRAME", "DIMENSION_RESULT", "SYNTHESIS", "DONE")
REDIS_URL = os.environ.get("MATRIX_REDIS_URL", "redis://localhost:6379/0")
MAX_STREAM_FRAMES = 20


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "matrix-api", "version": "0.1.0"}

class ScenarioInput(BaseModel):
    query: str
    input_type: str = "nl"

@app.post("/scenario")
def create_scenario(input_data: ScenarioInput) -> dict:
    """Parse NL/map query into a structured Scenario via Gemini 3.1 Pro (Phase 4),
    persist it (Postgres, or the in-memory fallback), and return the parsed params."""
    if parse_scenario is None:  # kernel not installed (bare env) — REST surface stays up
        return JSONResponse(
            status_code=503,
            content={"error": f"scenario parser unavailable: {_KERNEL_IMPORT_ERROR}"},
        )
    try:
        scenario = parse_scenario(input_data.query)
    except ValueError as e:
        # LLM flagged as ambiguous
        return JSONResponse(status_code=400, content={"error": str(e), "is_ambiguous": True})
    db.save_scenario(scenario, raw_input=input_data.query, input_type=input_data.input_type)
    # v1 fields stay top-level for the existing frontend; Scenario-v2 fields are read
    # defensively (they appear once the orchestrator upgrade lands) and ride along.
    return {
        "scenario_id": scenario.scenario_id,
        "description": scenario.description,
        "corridor": getattr(scenario, "corridor", None),
        "lanes_closed": getattr(scenario, "lanes_closed", None),
        "intervention_type": getattr(scenario, "intervention_type", None),
        "location": getattr(scenario, "location", None),
    }

@app.get("/runs/{run_id}")
def get_run(run_id: str) -> dict:
    """A stored run: status/timings + every DimensionResult with full glass-box
    provenance (PRD-F14) — a reloaded run is as inspectable as a live one."""
    run = db.get_run(run_id)
    if run is None:
        return JSONResponse(status_code=404, content={"error": "run not found", "run_id": run_id})
    return run

@app.get("/audit/{run_id}")
def get_audit(run_id: str) -> dict:
    """Public bias-audit log for a run (PRD-F6), from Postgres `bias_audit_log` or the
    in-memory fallback. The latest entry is flattened top-level (the BiasAuditLog panel's
    shape); `entries` carries the full append-only history. Never fabricates an entry."""
    entries = db.get_audit(run_id)
    latest = entries[-1] if entries else {}
    payload = {
        "run_id": run_id,
        "batch_id": latest.get("batch_id", ""),
        "target_mode_share": latest.get("target_mode_share", {}),
        "observed_mode_share": latest.get("observed_mode_share", {}),
        "max_delta": latest.get("max_delta"),
        "reweighted": latest.get("reweighted", False),
        "timestamp": latest.get("timestamp"),
        "entries": entries,
    }
    if not entries:
        payload["note"] = "no audit entries recorded for this run"
    return payload

@app.get("/validation")
def get_validation() -> dict:
    """Validation gates (PRD-F18, QAD VAL-01/02). Order of truth: the generated
    validation_report.json if present, else the kernel's validation module, else an
    honest empty list — a gate is never fabricated."""
    override = os.environ.get("MATRIX_VALIDATION_REPORT")
    candidates = [Path(override)] if override else [
        _APP_ROOT / "validation_report.json",
        _APP_ROOT / "packages" / "kernel" / "validation_report.json",
    ]
    for path in candidates:
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                logging.getLogger("matrix_api").warning(
                    "unreadable validation report %s (%s); falling back", path, exc
                )
    try:
        from matrix_kernel.validation import get_all_validations
    except ImportError:
        return {"gates": [], "note": "validation module not available"}
    return {
        "gates": get_all_validations(),
        "source": "matrix_kernel.validation",
        "note": "live module results (no validation_report.json found)",
    }

@app.post("/report/{run_id}")
def generate_report(run_id: str) -> dict:
    return {"run_id": run_id, "status": "stub"}


# ─── persistence seam for the WS pipeline (wired post-merge by the WS-handler owner) ────
# Inside simulate_ws, persistence is three calls (all fallback-safe, never raise):
#   run_id = db.save_run(scenario_id, status="running")              # after ACCEPTED
#   db.save_dimension_results(run_id, results)                       # after modules score
#   db.save_run(scenario_id, run_id=run_id, status="done",           # alongside DONE
#               duration_ms=round((time.perf_counter() - t0) * 1000))
# Bias-audit entries from persona generation go through db.save_audit_entry(entry, run_id).
# GET /runs/{run_id} and GET /audit/{run_id} then serve the stored run on both backends.


def _result_payload(r) -> dict:
    """Serialize a DimensionResult to the DIMENSION_RESULT event (full provenance, RFC §3)."""
    return {
        "type": "DIMENSION_RESULT",
        "dimension": r.dimension,
        "metric": r.metric,
        "equation_id": r.equation_id,
        "value": r.value,
        "range": list(r.range),
        "unit": r.unit,
        "confidence": r.confidence,
        "directional": r.directional,
        "input_dataset_ids": r.input_dataset_ids,
        "references": r.references,
        "assumptions": r.assumptions,
    }


def _get_trajectory(scenario_id: str) -> Trajectory:
    """Milestone A: serve the cached demo scenario for a snappy stream; else run the kernel live."""
    import redis

    r = redis.from_url(REDIS_URL)
    raw = r.get(f"scenario:{scenario_id}:latest") or r.get("scenario:demo:latest")
    if raw is not None:
        return Trajectory.from_json(raw)
    return simulate(Scenario(scenario_id, "live scenario", corridor=""))


@app.websocket("/simulate/{scenario_id}")
async def simulate_ws(ws: WebSocket, scenario_id: str) -> None:
    await ws.accept()
    t0 = time.perf_counter()
    try:
        await ws.send_json({"type": "ACCEPTED", "scenario_id": scenario_id})

        # Kernel work is blocking -> off the event loop.
        traj = await asyncio.to_thread(_get_trajectory, scenario_id)

        for fr in traj.frames[:MAX_STREAM_FRAMES]:
            await ws.send_json({"type": "PLAYBACK_FRAME", "tick": fr.tick, "agents": fr.agents})

        # Score modules in parallel for the first four, then run societal which needs ecological output.
        # This matches the implementation plan.
        coros = [
            asyncio.to_thread(behavioral.score, traj),
            asyncio.to_thread(ecological.score, traj),
            asyncio.to_thread(social.score, traj),
            asyncio.to_thread(economic.score, traj),
        ]
        results_lists = await asyncio.gather(*coros)
        
        # Flatten the results from the first four modules
        results = [r for lst in results_lists for r in lst]
        
        # Find ECO-2 result to pass to societal module
        eco2_res = next((r for r in results if r.equation_id == "ECO-2"), None)
        eco2_val = eco2_res.value if eco2_res else 0.0
        
        # Run societal module
        societal_results = await asyncio.to_thread(societal.score, traj, eco2_val=eco2_val)
        results.extend(societal_results)

        for r in results:
            await ws.send_json(_result_payload(r))

        # Gemini 3.1 Pro synthesis narrative (Phase 4.3). Must cite equation_id + dataset_ids.
        narrative, citations = await asyncio.to_thread(synthesize, results)
        
        await ws.send_json({"type": "SYNTHESIS", "narrative": narrative, "citations": citations})

        await ws.send_json({
            "type": "DONE",
            "scenario_id": scenario_id,
            "duration_ms": round((time.perf_counter() - t0) * 1000),
        })
    except WebSocketDisconnect:
        return
