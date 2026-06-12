"""MATRIX API gateway. FastAPI + WebSocket. SDD §2, RFC §3.

`/simulate/{id}` streams the real progressive pipeline:
  ACCEPTED -> [QUEUED] -> PLAYBACK_FRAME* -> DIMENSION_RESULT (per module, provenance intact)
  -> SYNTHESIS (templated; Gemini 3.1 Pro synthesis is Phase 4) -> DONE
Any stage failure emits a typed ERROR event before closing -- never a silent drop.
DONE carries per-stage timings {sumo_ms, modules_ms, gemini_ms, total_ms} (RFC-001
latency budget visibility). Stage budgets, the concurrency gate, and the dependency
health checks live in matrix_api.runtime so the handler stays thin.

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
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from pydantic import BaseModel

from matrix_api import db, runtime

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
# QUEUED and ERROR extend the original sequence (additive only -- never reordered).
EVENT_TYPES = ("ACCEPTED", "QUEUED", "PLAYBACK_FRAME", "DIMENSION_RESULT", "SYNTHESIS", "DONE", "ERROR")
REDIS_URL = os.environ.get("MATRIX_REDIS_URL", "redis://localhost:6379/0")
MAX_STREAM_FRAMES = 20


@app.get("/health")
def health() -> dict:
    """Dependency-aware health: per-dependency status + overall ok|degraded.

    Sync def -> FastAPI threadpool; every check is timeout-bounded in runtime.py,
    so the endpoint never blocks > ~2 s even with all dependencies down.
    """
    report = runtime.health_report(REDIS_URL)
    return {
        "status": report["status"],
        "service": "matrix-api",
        "version": "0.1.0",
        "dependencies": report["dependencies"],
    }

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


async def _score_all_modules(traj: Trajectory) -> list:
    """Score modules in parallel for the first four, then societal which needs
    ecological output. This matches the implementation plan."""
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
    results.extend(await asyncio.to_thread(societal.score, traj, eco2_val=eco2_val))
    return results


async def _send_error(
    ws: WebSocket, scenario_id: str, stage: str, message: str, recoverable: bool
) -> None:
    """ERROR before close -- never a silent drop. Best-effort: the socket may be gone."""
    try:
        await ws.send_json(runtime.error_event(scenario_id, stage, message, recoverable))
        await ws.close(code=1011)
    except Exception:
        pass


@app.websocket("/simulate/{scenario_id}")
async def simulate_ws(ws: WebSocket, scenario_id: str) -> None:
    await ws.accept()
    timer = runtime.StageTimer()
    stage = "accept"  # tracks where a generic failure happened, for the ERROR event
    admitted, ticket, position = runtime.GATE.admit()
    holds_slot = admitted
    run_id = None
    try:
        await ws.send_json({"type": "ACCEPTED", "scenario_id": scenario_id})

        if not admitted:
            # At capacity (MATRIX_MAX_CONCURRENT_SIMS): queue FIFO instead of rejecting,
            # so the client keeps its socket and can render a waiting state. The wait
            # watches the socket: a disconnect while queued abandons the ticket
            # immediately instead of later burning a slot against a dead client.
            stage = "queue"
            await ws.send_json(
                {"type": "QUEUED", "scenario_id": scenario_id, "position": position}
            )
            await runtime.wait_for_slot_or_disconnect(
                ws, runtime.GATE, ticket, timeout_s=runtime.queue_timeout_s()
            )
            holds_slot = True

        # Persistence seam (matrix_api.db, feat/api-persistence) -- best-effort, never raises.
        run_id = runtime.persist_run_started(scenario_id)

        # Kernel work is blocking -> off the event loop; budgeted so a hung SUMO/Redis
        # read can't wedge the socket (RFC-001: SUMO sits in the 15-60 s band).
        stage = "sumo"
        with timer.stage("sumo"):
            traj = await runtime.run_stage(
                asyncio.to_thread(_get_trajectory, scenario_id),
                stage="sumo",
                timeout_s=runtime.stage_timeout_s("sumo"),
            )

        for fr in traj.frames[:MAX_STREAM_FRAMES]:
            await ws.send_json({"type": "PLAYBACK_FRAME", "tick": fr.tick, "agents": fr.agents})

        stage = "modules"
        with timer.stage("modules"):
            results = await runtime.run_stage(
                _score_all_modules(traj),
                stage="modules",
                timeout_s=runtime.stage_timeout_s("modules"),
            )

        for r in results:
            await ws.send_json(_result_payload(r))

        runtime.persist_dimension_results(run_id, results)

        # Gemini 3.1 Pro synthesis narrative (Phase 4.3). Must cite equation_id + dataset_ids.
        stage = "synthesis"
        with timer.stage("gemini"):
            narrative, citations = await runtime.run_stage(
                asyncio.to_thread(synthesize, results),
                stage="synthesis",
                timeout_s=runtime.stage_timeout_s("gemini"),
            )

        await ws.send_json({"type": "SYNTHESIS", "narrative": narrative, "citations": citations})

        timings = timer.timings()
        runtime.persist_run_done(scenario_id, run_id, timings)
        await ws.send_json({
            "type": "DONE",
            "scenario_id": scenario_id,
            "duration_ms": timings["total_ms"],
            "timings": timings,
        })
    except WebSocketDisconnect:
        return
    except runtime.StageTimeout as e:
        await _send_error(ws, scenario_id, e.stage, str(e), recoverable=True)
    except runtime.LLMUnavailable as e:
        # feat/llm-resilience: Gemini transiently down -- the run can be retried.
        await _send_error(ws, scenario_id, "synthesis", str(e), recoverable=True)
    except Exception as e:
        # Synthesis failures are recoverable (the narrative can be re-run); a failure
        # in any earlier stage means the run itself failed.
        await _send_error(
            ws,
            scenario_id,
            stage,
            f"{type(e).__name__}: {e}",
            recoverable=(stage == "synthesis"),
        )
    finally:
        # Critical: never leak a slot -- disconnects, timeouts, and crashes all land here.
        if holds_slot:
            runtime.GATE.release()
        else:
            runtime.GATE.abandon(ticket)
