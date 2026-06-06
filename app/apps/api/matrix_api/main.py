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

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from matrix_kernel.modules import behavioral, ecological, social, economic, societal
from matrix_kernel.runner import Scenario, simulate
from matrix_kernel.trajectory import Trajectory

app = FastAPI(title="MATRIX API", version="0.1.0")

# The event types streamed over the WS (RFC §3) -- frozen so the frontend (Track B) can mock them.
EVENT_TYPES = ("ACCEPTED", "PLAYBACK_FRAME", "DIMENSION_RESULT", "SYNTHESIS", "DONE")
REDIS_URL = os.environ.get("MATRIX_REDIS_URL", "redis://localhost:6379/0")
MAX_STREAM_FRAMES = 20


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "matrix-api", "version": "0.1.0"}


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

        # Templated synthesis (real Gemini 3.1 Pro synthesis is Phase 4). It MUST cite the
        # equation_id + dataset_ids for any number it asserts (citation guard).
        beh1 = next((r for r in results if r.equation_id == "BEH-1"), None)
        if beh1 is not None:
            narrative = (
                f"On the affected corridor the scenario shifts {beh1.value:+.0f} {beh1.unit} "
                f"(range {beh1.range[0]:.0f}..{beh1.range[1]:.0f}, confidence {beh1.confidence})."
            )
            citations = [{
                "claim": narrative,
                "equation_id": beh1.equation_id,
                "dataset_ids": beh1.input_dataset_ids,
            }]
        else:
            narrative, citations = "No behavioral result produced.", []
        await ws.send_json({"type": "SYNTHESIS", "narrative": narrative, "citations": citations})

        await ws.send_json({
            "type": "DONE",
            "scenario_id": scenario_id,
            "duration_ms": round((time.perf_counter() - t0) * 1000),
        })
    except WebSocketDisconnect:
        return
