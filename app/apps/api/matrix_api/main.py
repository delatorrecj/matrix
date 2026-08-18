"""MATRIX API gateway. FastAPI + WebSocket. SDD §2, RFC §3.

`/simulate/{id}` streams the real progressive pipeline:
  ACCEPTED -> [QUEUED] -> PLAYBACK_FRAME* -> EDGE_COUNTS -> DIMENSION_RESULT (per module, provenance intact)
  -> SYNTHESIS (templated; Azure OpenAI synthesis is Phase 4) -> DONE
Any stage failure emits a typed ERROR event before closing -- never a silent drop.
DONE carries per-stage timings {sumo_ms, modules_ms, llm_ms, total_ms} (RFC-001
latency budget visibility). Stage budgets, the concurrency gate, and the dependency
health checks live in matrix_api.runtime so the handler stays thin.

For Milestone A it serves the cached demo scenario for a snappy stream, else runs the kernel
live. Numbers come from the kernel + equations, NEVER the LLM (glass box, PRD-F14); the
synthesis narrative cites equation_id + dataset_ids (citation guard, methods §4).

Run locally:  uvicorn matrix_api.main:app
"""
from __future__ import annotations

# ── Load .env BEFORE any import reads os.environ (Azure OpenAI key, DB URL, etc.) ─────
# Searches upward from CWD so `app/.env` is found whether you start from
# `app/apps/api/` or `app/`. The local `apps/api/.env` loads as an override.
from dotenv import find_dotenv, load_dotenv as _load_dotenv

_load_dotenv(find_dotenv(usecwd=True))   # app/.env  (or wherever the first hit is)
_load_dotenv()                            # apps/api/.env (override — closer wins)

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
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

from matrix_api.auth import allowed_origins, authorize_websocket, require_api_key

@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Startup/shutdown (modern replacement for @app.on_event). Choose the persistence
    backend, then warm the kernel caches off the event loop so a slow model load / ingest
    never stalls startup. Both steps are best-effort and never fatal."""
    db.init_db()
    await asyncio.to_thread(_warm_kernel_caches)
    yield


# Auth + rate limiting are env-gated and OFF by default (see matrix_api/auth.py);
# /health, /validation, /credibility, and the docs stay open even when enabled.
app = FastAPI(
    title="MATRIX API", version="0.1.0",
    dependencies=[Depends(require_api_key)], lifespan=_lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),  # MATRIX_ALLOWED_ORIGINS; defaults to localhost:3000
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

# app/ repo root (main.py -> matrix_api -> api -> apps -> app) for the validation report.
_APP_ROOT = Path(__file__).resolve().parents[3]


def _warm_kernel_caches() -> None:
    """Best-effort warm-up of the two caches the live pipeline reads but nothing populated:

      • persona pool + bias audit (PRD-F6) — runs the full generate→audit→reweight loop once
        and caches it, so every run can log a real bias-audit entry (the auditor previously
        existed only in tests). Static literature-anchored pool by default; MATRIX_PERSONA_LLM=1
        exercises the Azure OpenAI generator whose drift the reweighter corrects.
      • GraphRAG/Chroma collection — ingests the corpus so orchestrator `retrieve()` returns
        sourced chunks instead of [] (the collection was never built outside tests).
      • Validation + credibility reports (CR-012 T1.4 / Credibility Phase 1) — when a Redis
        baseline exists, regenerate validation_report.json so GET /validation serves a live
        NRMSE (PASS or honest FAIL). Always attempt credibility_report.json (fixture-backed
        spot-checks work without Redis).

    Both are wrapped so a missing kernel / Redis / Chroma never blocks API startup. Disable
    with MATRIX_SKIP_WARMUP=1 (e.g. bare test envs)."""
    if os.environ.get("MATRIX_SKIP_WARMUP", "0") == "1" or _KERNEL_IMPORT_ERROR:
        return
    log = logging.getLogger("matrix_api")
    try:
        from matrix_kernel.personas import warm_persona_pool

        _pool, entry = warm_persona_pool()
        log.info("persona pool warmed: %d personas, reweighted=%s", len(_pool), entry.reweighted)
    except Exception as exc:  # pragma: no cover - depends on Redis/LLM availability
        log.warning("persona pool warm-up skipped (%s)", exc)
    try:
        from matrix_kernel.build_graphrag import ingest_corpus

        ingest_corpus()
        log.info("GraphRAG corpus ingested")
    except Exception as exc:  # pragma: no cover - depends on Chroma availability
        log.warning("GraphRAG ingest skipped (%s)", exc)
    try:
        from matrix_kernel.build_validation_report import generate, write_markdown_artifact
        from matrix_kernel.validation import write_validation_report

        report = generate()
        path = write_validation_report(report, _APP_ROOT / "validation_report.json")
        write_markdown_artifact(report, path.with_suffix(".md"))
        statuses = ", ".join(f"{g['gate_id']}={g['status']}" for g in report["gates"])
        log.info("validation report written (%s): %s", path, statuses)
    except Exception as exc:  # pragma: no cover - net/baseline soft path
        log.warning("validation report generation skipped (%s)", exc)
    try:
        from matrix_kernel.credibility import write_credibility_report

        cpath = write_credibility_report(path=_APP_ROOT / "credibility_report.json")
        log.info("credibility report written: %s", cpath)
    except Exception as exc:  # pragma: no cover
        log.warning("credibility report generation skipped (%s)", exc)

# The event types streamed over the WS (RFC §3) -- frozen so the frontend (Track B) can mock them.
# QUEUED and ERROR extend the original sequence (additive only -- never reordered).
EVENT_TYPES = ("ACCEPTED", "QUEUED", "PLAYBACK_FRAME", "EDGE_COUNTS", "DIMENSION_RESULT", "SYNTHESIS", "DONE", "ERROR")
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
    # Optional map-drop geometry: a GeoJSON *geometry* dict (Point/Polygon), supplied
    # structurally by the builder/map UI. The LLM never originates it (PRD-F14); it rides
    # straight through to Scenario.geometry so the kernel resolves edges from what was drawn.
    geometry: dict | None = None

@app.post("/scenario")
def create_scenario(input_data: ScenarioInput) -> dict:
    """Parse NL/map query into a structured Scenario via Azure OpenAI (Phase 4),
    persist it (Postgres, or the in-memory fallback), and return the parsed params."""
    if parse_scenario is None:  # kernel not installed (bare env) — REST surface stays up
        return JSONResponse(
            status_code=503,
            content={"error": f"scenario parser unavailable: {_KERNEL_IMPORT_ERROR}"},
        )
    try:
        scenario = parse_scenario(input_data.query, geometry=input_data.geometry)
    except ValueError as e:
        # LLM flagged as ambiguous
        return JSONResponse(status_code=400, content={"error": str(e), "is_ambiguous": True})
    except Exception as e:
        # Orchestrator failure (LLMUnavailable, Chroma/RAG, structured-parse) — surface the
        # real cause with a logged traceback instead of an opaque 500 (mirrors the WS ERROR
        # contract). The kernel never originates a number, so there is nothing to fabricate.
        logging.getLogger("matrix_api").exception("scenario parse failed for query=%r", input_data.query)
        return JSONResponse(
            status_code=502,
            content={"error": f"scenario parse failed: {type(e).__name__}: {e}"},
        )
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
        "geometry": getattr(scenario, "geometry", None),
        "raw_input": input_data.query,
        "parameters": getattr(scenario, "parameters", None) or {},
    }

def _geometry_lnglat(geometry: dict | None) -> list[float] | None:
    """Map-drop GeoJSON → [lon, lat]. Point as-is; Polygon = mean of the outer ring."""
    if not geometry:
        return None
    coords = geometry.get("coordinates")
    gtype = geometry.get("type")
    if gtype == "Point" and isinstance(coords, (list, tuple)) and len(coords) >= 2:
        return [float(coords[0]), float(coords[1])]
    if gtype == "Polygon" and isinstance(coords, list) and coords:
        ring = coords[0]
        if not isinstance(ring, list) or not ring:
            return None
        vertices = ring[:-1] if len(ring) > 1 else ring
        n = len(vertices)
        if n == 0:
            return None
        return [sum(v[0] for v in vertices) / n, sum(v[1] for v in vertices) / n]
    return None


def _camera_location_of_interest(location: object, geometry: dict | None) -> list[float] | None:
    """Camera-only [lon, lat]: map-drop centroid, else gazetteer coords for `location`."""
    pt = _geometry_lnglat(geometry)
    if pt:
        return pt
    if not location or not str(location).strip():
        return None
    try:
        from matrix_kernel.gazetteer import location_coordinates
    except ImportError:  # pragma: no cover - bare env without kernel package
        return None
    return location_coordinates(str(location))


@app.get("/scenario/{scenario_id}")
def get_scenario(scenario_id: str) -> dict:
    """A saved scenario's parsed fields, notably `location`/`geometry` -- the results view
    (CR-013) fetches this once on load to pan/zoom the map to the scenario's location of
    interest. `geometry` comes back from Postgres as a `ST_AsGeoJSON` *string*; the
    in-memory fallback stores it as a dict already -- normalize both to a dict|None here.
    `location_of_interest` is camera-only (not Scenario.geometry): map-drop centroid, else
    gazetteer coordinates for the stored location name. `raw_input` is the planner's
    original query so the results dock can restate it."""
    record = db.get_scenario(scenario_id)
    if record is None:
        return JSONResponse(status_code=404, content={"error": "scenario not found", "scenario_id": scenario_id})
    geometry = record.get("geometry")
    if isinstance(geometry, str):
        geometry = json.loads(geometry)
    geom = geometry if isinstance(geometry, dict) else None
    parsed = record.get("parsed_params")
    parameters = parsed.get("parameters") if isinstance(parsed, dict) else None
    return {
        "scenario_id": record.get("scenario_id", scenario_id),
        "raw_input": record.get("raw_input") or "",
        "description": record.get("description", ""),
        "intervention_type": record.get("intervention_type"),
        "location": record.get("location"),
        "parameters": parameters if isinstance(parameters, dict) else {},
        "geometry": geom,
        "location_of_interest": _camera_location_of_interest(record.get("location"), geom),
    }


_CORRIDOR_TIMING_KEYS = ("affected_edges", "edge_resolution")


def _run_public_view(run: dict) -> dict:
    """Lift the corridor fields stuffed into timings JSONB into their own top-level
    keys. Every other timings entry passes through untouched -- this must not
    silently drop provenance (PRD-F14) for keys outside the standard stage set."""
    out = dict(run)
    timings = out.get("timings")
    if isinstance(timings, dict):
        out["affected_edges"] = timings.get("affected_edges")
        out["edge_resolution"] = timings.get("edge_resolution")
        out["timings"] = {k: v for k, v in timings.items() if k not in _CORRIDOR_TIMING_KEYS}
    else:
        out.setdefault("affected_edges", None)
        out.setdefault("edge_resolution", None)
    return out


@app.get("/scenarios/{scenario_id}/latest-run")
def get_latest_run(scenario_id: str) -> dict:
    """Most recent completed run for a scenario (glass-box results intact).

    The results URL is `/scenario/{scenario_id}` — the internal UUID run_id never
    reaches the client — so reload/share hydrates via this lookup instead of
    re-opening WS /simulate.
    """
    run = db.get_latest_run_for_scenario(scenario_id)
    if run is None:
        return JSONResponse(
            status_code=404,
            content={"error": "no completed run", "scenario_id": scenario_id},
        )
    return _run_public_view(run)


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> dict:
    """A stored run: status/timings + every DimensionResult with full glass-box
    provenance (PRD-F14) — a reloaded run is as inspectable as a live one."""
    run = db.get_run(run_id)
    if run is None:
        return JSONResponse(status_code=404, content={"error": "run not found", "run_id": run_id})
    return _run_public_view(run)

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
        "adjustment_factors": latest.get("adjustment_factors"),
        "timestamp": latest.get("timestamp"),
        "entries": entries,
    }
    if not entries:
        payload["note"] = "no audit entries recorded for this run"
    return payload


class FeedbackInput(BaseModel):
    run_id: str
    equation_id: str
    verdict: str
    note: str = ""
    observed_value: float | None = None

@app.post("/feedback")
def submit_feedback(feedback: FeedbackInput) -> dict:
    """Submit feedback for a specific dimension result (PRD-F20)."""
    if feedback.verdict not in ("plausible", "implausible"):
        return JSONResponse(status_code=400, content={"error": "verdict must be plausible or implausible"})
    feedback_id = db.save_planner_feedback(feedback.run_id, feedback.model_dump())
    return {"status": "success", "feedback_id": feedback_id}

@app.get("/feedback")
def get_feedback(run_id: str) -> dict:
    """Retrieve all feedback for a run."""
    entries = db.get_planner_feedback(run_id)
    return {"run_id": run_id, "entries": entries}

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


@app.get("/credibility")
def get_credibility() -> dict:
    """Credibility Phase 1 report: equation conformance, VAL gates, third-party spot-checks.

    Prefers credibility_report.json written at startup; otherwise builds live (fixture-backed
    OpenAQ / WHO-EMEP checks work offline). Never invents a PASS for missing data."""
    override = os.environ.get("MATRIX_CREDIBILITY_REPORT")
    candidates = [Path(override)] if override else [
        _APP_ROOT / "credibility_report.json",
        _APP_ROOT / "packages" / "kernel" / "credibility_report.json",
    ]
    for path in candidates:
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                logging.getLogger("matrix_api").warning(
                    "unreadable credibility report %s (%s); rebuilding", path, exc
                )
    try:
        from matrix_kernel.credibility import build_credibility_report
    except ImportError:
        return {"error": "credibility module not available", "llm_invents_numbers": False}
    return build_credibility_report()


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
        "focus_geometry": getattr(r, "focus_geometry", None),
    }


def _scenario_from_record(record: dict) -> "Scenario":
    """Rebuild a kernel Scenario from a persisted scenario record (db.get_scenario).

    This is what makes a live run simulate the user's ACTUAL parsed intervention —
    its type, location, parameters, and map-drop geometry — rather than a blank
    stand-in. The SUMO-free Scenario is imported directly (not via the runner) so the
    rebuild is unit-testable on a bare venv. v1-only records (no intervention_type)
    rebuild as a plain lane_closure, exactly as before."""
    from matrix_kernel.scenario import Scenario as _Scenario  # SUMO-free; safe on a bare venv

    params = record.get("parsed_params") or {}
    geometry = record.get("geometry")
    return _Scenario(
        scenario_id=str(record.get("scenario_id") or ""),
        description=record.get("description") or params.get("description") or "",
        corridor=params.get("corridor") or "",
        lanes_closed=int(params.get("lanes_closed") or 1),
        intervention_type=record.get("intervention_type") or params.get("intervention_type") or "lane_closure",
        location=record.get("location") or params.get("location") or "",
        geometry=geometry if isinstance(geometry, dict) else None,
        parameters=params.get("parameters") or {},
    )


# The one id whose run falls back to the pre-warmed demo trajectory (Milestone A snappy
# stream). Every other id resolves to its own persisted scenario — so a real run reflects
# the user's query instead of being shadowed by the cached demo.
_DEMO_SCENARIO_ID = os.environ.get("MATRIX_DEMO_SCENARIO_ID", "demo")


def _get_trajectory(scenario_id: str) -> Trajectory:
    """Resolve the Trajectory for a run, in priority order:
      1. an id-specific pre-warmed trajectory cached in Redis (scenario:<id>:latest);
      2. for the demo id only, the pre-warmed demo trajectory (snappy stream);
      3. the PERSISTED scenario (POST /scenario) simulated live via the kernel;
      4. a blank live scenario, only when nothing was ever persisted for this id.
    After a live sim (3 or 4), the result is written back to Redis (TTL=MATRIX_TRAJ_CACHE_TTL_S,
    default 2h) so repeated runs of the same id skip SUMO entirely (path 1).
    """
    import redis

    from matrix_kernel.scenario import Scenario as _Scenario  # SUMO-free; safe on a bare venv

    r = redis.from_url(REDIS_URL)
    raw = r.get(f"scenario:{scenario_id}:latest")
    if raw is None and scenario_id == _DEMO_SCENARIO_ID:
        raw = r.get("scenario:demo:latest")
    if raw is not None:
        return Trajectory.from_json(raw)

    record = db.get_scenario(scenario_id)
    scenario = (
        _scenario_from_record(record)
        if record
        else _Scenario(scenario_id, "live scenario", corridor="")
    )
    traj = simulate(scenario)
    # Write back to Redis so repeated runs of the same scenario_id skip SUMO entirely.
    # Best-effort — a Redis failure must never abort a run that just completed.
    try:
        _ttl = int(os.environ.get("MATRIX_TRAJ_CACHE_TTL_S", "7200"))
        r.set(f"scenario:{scenario_id}:latest", traj.to_json(), ex=_ttl)
    except Exception:
        pass
    return traj


def _persist_bias_audit(scenario_id: str, traj: "Trajectory") -> None:
    """Log a public bias-audit entry (PRD-F6) for this run so GET /audit/{scenario_id} and the
    BiasAuditLog panel show real data (previously always empty — the auditor ran only in tests).

    Keyed by scenario_id, not the internal UUID run_id: the WS path, the DONE event, and the
    frontend (BiasAuditLog runId={scenarioId}) all identify a run by its scenario_id — the UUID
    run_id never reaches the client. Prefers the warmed persona-pool audit (carries any reweight
    adjustment_factors); falls back to the run's realized mode share so an entry is ALWAYS
    recorded. Best-effort: a failure here never aborts a run that already produced its results
    (glass box stays honest — no fabricated entry, just a logged warning)."""
    if _KERNEL_IMPORT_ERROR:
        return
    try:
        from matrix_kernel import personas
        from matrix_kernel.bias_auditor import audit_personas

        entry = personas.load_pool_audit()
        if not entry:
            observed = traj.observed_mode_share()
            entry = audit_personas(observed, personas.ILOILO_MODE_SHARE, batch_id="run").as_dict()
        db.save_audit_entry(entry, scenario_id)
    except Exception:  # pragma: no cover - depends on Redis/DB availability
        logging.getLogger("matrix_api").warning("bias audit logging skipped", exc_info=True)


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
    # Env-gated auth/rate guard (no-op by default); rejects the pending handshake
    # with 1008/1013 before any kernel work can be triggered.
    if not await authorize_websocket(ws):
        return
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

        # Per-edge aggregate vehicle counts for the congestion choropleth (drives the map's
        # congestion layer; join key = SUMO edge id, matching public/layers/edges.geojson).
        # One message; an absent edge id means zero recorded vehicles, never a guess (PRD-F14).
        # location_of_interest/edge_resolution (CR-013) ride along here too: they're the
        # ground truth of WHERE the scenario actually ran (computed in runner.simulate from
        # the edges actually resolved), not a pre-simulation guess -- the results view uses
        # this, not GET /scenario/{id}, to pan/mark the map for NL-only (non-map-drop) queries.
        await ws.send_json({
            "type": "EDGE_COUNTS",
            "edge_counts": traj.edge_counts,
            "location_of_interest": traj.meta.get("location_of_interest"),
            "edge_resolution": traj.meta.get("edge_resolution"),
            "affected_edges": traj.meta.get("affected_edges") or [],
        })

        # Public bias audit (PRD-F6): log this run's persona mode share vs the ground-truth
        # anchor so GET /audit/{scenario_id} returns real data. Off the critical path, never fatal.
        await asyncio.to_thread(_persist_bias_audit, scenario_id, traj)

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

        # Azure OpenAI synthesis narrative (Phase 4.3). Must cite equation_id + dataset_ids.
        stage = "synthesis"
        with timer.stage("gemini"):  # stage label 'gemini' -> timing key 'llm_ms' (StageTimer alias)
            narrative, citations = await runtime.run_stage(
                asyncio.to_thread(synthesize, results),
                stage="synthesis",
                timeout_s=runtime.stage_timeout_s("gemini"),
            )

        await ws.send_json({"type": "SYNTHESIS", "narrative": narrative, "citations": citations})

        timings = timer.timings()
        persist_timings = {
            **timings,
            "affected_edges": traj.meta.get("affected_edges") or [],
            "edge_resolution": traj.meta.get("edge_resolution"),
        }
        runtime.persist_run_done(scenario_id, run_id, persist_timings)
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
        # feat/llm-resilience: LLM transiently down -- the run can be retried.
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
