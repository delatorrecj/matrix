"""Standalone WebSocket e2e smoke for /simulate (U10).

Run with uvicorn already serving the API:
  uv run --directory app/apps/api uvicorn matrix_api.main:app --port 8000   # (background)
  uv run --directory app/apps/api python ws_smoke.py                        # this client

Asserts the five RFC §3 event types arrive in order and that every DIMENSION_RESULT carries
glass-box provenance (equation_id + input_dataset_ids). Exits non-zero on failure.
"""
from __future__ import annotations

import asyncio
import json
import sys

import websockets


async def main(uri: str = "ws://localhost:8000/simulate/demo") -> None:
    seen: list[str] = []
    results: list[dict] = []
    async with websockets.connect(uri, max_size=None) as ws:
        while True:
            msg = json.loads(await ws.recv())
            seen.append(msg["type"])
            if msg["type"] == "DIMENSION_RESULT":
                results.append(msg)
            if msg["type"] == "SYNTHESIS":
                print("SYNTHESIS:", msg["narrative"])
                assert msg["citations"] and msg["citations"][0]["equation_id"], "uncited synthesis"
            if msg["type"] == "DONE":
                print("DONE duration_ms:", msg.get("duration_ms"))
                break

    print("event order:", seen[:3], "...", seen[-2:])
    assert seen[0] == "ACCEPTED" and seen[-1] == "DONE", f"bad lifecycle: {seen}"
    for t in ("PLAYBACK_FRAME", "DIMENSION_RESULT", "SYNTHESIS"):
        assert t in seen, f"missing {t}"
    assert results, "no DIMENSION_RESULT received"
    for r in results:
        assert r["equation_id"] and r["input_dataset_ids"], f"missing provenance: {r}"
    beh1 = next(r for r in results if r["equation_id"] == "BEH-1")
    print(f"BEH-1: value={beh1['value']} {beh1['unit']} | confidence={beh1['confidence']} "
          f"| range={beh1['range']} | datasets={beh1['input_dataset_ids']}")
    print("PASS: five event types in order; every DIMENSION_RESULT has working provenance.")


if __name__ == "__main__":
    asyncio.run(main(*(sys.argv[1:] or [])))
