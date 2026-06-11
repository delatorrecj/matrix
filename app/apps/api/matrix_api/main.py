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
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from pydantic import BaseModel

from matrix_api import runtime
from matrix_kernel.modules import behavioral, ecological, social, economic, societal
from matrix_kernel.runner import Scenario, simulate
from matrix_kernel.trajectory import Trajectory
from matrix_kernel.orchestrator import parse_scenario
from matrix_kernel.synthesis import synthesize

app = FastAPI(title="MATRIX API", version="0.1.0")

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
    """Parse NL/map query into a structured Scenario via Gemini 3.1 Pro (Phase 4)."""
    try:
        scenario = parse_scenario(input_data.query)
        # Milestone A/B: we return the parsed params immediately.
        # DB persistence (Supabase) happens here in full production.
        return {
            "scenario_id": scenario.scenario_id,
            "description": scenario.description,
            "corridor": scenario.corridor,
            "lanes_closed": scenario.lanes_closed
        }
    except ValueError as e:
        # LLM flagged as ambiguous
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=400, content={"error": str(e), "is_ambiguous": True})

@app.get("/runs/{run_id}")
def get_run(run_id: str) -> dict:
    return {"run_id": run_id, "status": "stub"}

@app.get("/audit/{run_id}")
def get_audit(run_id: str) -> dict:
    # In a full implementation, this reads from Postgres `bias_audit_log`.
    # Returning a mock entry for Phase 6 frontend integration.
    return {
        "run_id": run_id,
        "batch_id": "b-12345",
        "target_mode_share": {"jeepney": 0.55, "private": 0.25, "walk": 0.20},
        "observed_mode_share": {"jeepney": 0.54, "private": 0.27, "walk": 0.19},
        "reweighted": False,
        "timestamp": "2026-06-09T12:00:00Z"
    }

@app.post("/report/{run_id}")
def generate_report(run_id: str) -> dict:
    return {"run_id": run_id, "status": "stub"}


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
