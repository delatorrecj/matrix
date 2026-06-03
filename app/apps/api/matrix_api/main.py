"""MATRIX API gateway (skeleton). FastAPI + WebSocket. SDD §2, RFC §3.

Phase 0: a health check + a WS /simulate/{id} that streams the placeholder
lifecycle events, so the frontend (Track B) can build against the real event
*shapes* before the kernel is live. Real orchestration + synthesis is Phase 4.

Verify the google-genai SDK call shape + Gemini 3.1 model IDs against live docs
before wiring the orchestrator (docs/build-matrix.md §3). Never Gemini 1.5/2.0.

Run locally:  uvicorn matrix_api.main:app --reload
"""
from __future__ import annotations

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI(title="MATRIX API", version="0.1.0")

# The event types the gateway streams over the WS (RFC §3). Frozen here so Track B
# can mock them before the kernel exists.
EVENT_TYPES = ("ACCEPTED", "PLAYBACK_FRAME", "DIMENSION_RESULT", "SYNTHESIS", "DONE")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "matrix-api", "version": "0.1.0"}


@app.websocket("/simulate/{scenario_id}")
async def simulate(ws: WebSocket, scenario_id: str) -> None:
    await ws.accept()
    try:
        # Phase 0 placeholder handshake -- the real pipeline lands in Phase 4 (Gate 4).
        await ws.send_json({"type": "ACCEPTED", "scenario_id": scenario_id})
        await ws.send_json(
            {
                "type": "DONE",
                "scenario_id": scenario_id,
                "note": "skeleton -- kernel not wired until Phase 2/4",
            }
        )
    except WebSocketDisconnect:
        return
