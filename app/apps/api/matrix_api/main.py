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
import os
import time

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

from matrix_kernel.modules import behavioral, ecological, social, economic, societal
from matrix_kernel.runner import Scenario, simulate
from matrix_kernel.trajectory import Trajectory
from matrix_kernel.orchestrator import parse_scenario
from matrix_kernel.synthesis import synthesize

from matrix_api.auth import allowed_origins, authorize_websocket, require_api_key

# Auth + rate limiting are env-gated and OFF by default (see matrix_api/auth.py);
# /health, /validation, and the docs stay open even when enabled.
app = FastAPI(title="MATRIX API", version="0.1.0", dependencies=[Depends(require_api_key)])
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),  # MATRIX_ALLOWED_ORIGINS; defaults to localhost:3000
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

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


@app.websocket("/simulate/{scenario_id}")
async def simulate_ws(ws: WebSocket, scenario_id: str) -> None:
    # Env-gated auth/rate guard (no-op by default); rejects the pending handshake
    # with 1008/1013 before any kernel work can be triggered.
    if not await authorize_websocket(ws):
        return
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
