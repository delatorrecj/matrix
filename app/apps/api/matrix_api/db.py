"""Persistence layer — Postgres+PostGIS with a graceful in-memory fallback (SDD §3).

The demo must run with **zero infra**: if `DATABASE_URL` is unreachable (short ~2 s
connect timeout) or the psycopg driver is absent, every operation transparently uses an
in-process store with the exact same read shapes. The active backend is logged once at
startup and never crashes the API.

Glass box (PRD-F14): `save_dimension_results` persists the *full* provenance of every
`matrix_kernel.results.DimensionResult` (equation_id, input_dataset_ids, range, computed
confidence, references, assumptions), and `get_run` returns it intact — a reloaded run is
as inspectable as a live one. Objects are read duck-typed (`getattr`) so this module never
imports the kernel and stays importable in bare environments, and so Scenario v2 fields
(`intervention_type`, `location`, `geometry`, `parameters`) persist as soon as the
orchestrator emits them while v1 scenarios keep working.

Schema: packages/data/schema.sql (applied idempotently at init; also via load_postgis.py).

Public API (the WS handler wires these post-merge — see the seam note in main.py):
    init_db(force_backend=None) -> str          # "postgres" | "memory"; idempotent
    save_scenario(scenario, raw_input, input_type) -> scenario_id
    get_scenario(scenario_id) -> dict | None
    save_run(scenario_id, run_id=None, status=..., duration_ms=..., timings=...,
             agent_count=...) -> run_id         # upsert; later calls update status/timings
    get_run(run_id) -> dict | None              # includes "results": full provenance list
    save_dimension_results(run_id, results) -> int
    save_audit_entry(entry, run_id=None) -> entry_id
    get_audit(run_id) -> list[dict]
"""
from __future__ import annotations

import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("matrix_api.db")

CONNECT_TIMEOUT_S = 2  # fail fast so the in-memory fallback is near-instant

# Default matches app/docker-compose.yml (postgis/postgis:16-3.4, matrix/matrix@:5432).
# MATRIX_PG_DSN is honored as a fallback for consistency with matrix_kernel.bias_auditor.
_DEFAULT_DSN = "postgresql://matrix:matrix@localhost:5432/matrix"

_VALID_RUN_STATUSES = {"queued", "running", "streaming", "done", "failed"}

# ─── backend state (chosen once, flipped to memory only on connection loss) ─────────────

_lock = threading.RLock()
_backend: str | None = None  # None = not initialized; "postgres" | "memory"

# In-memory store: same read shapes as the Postgres path so endpoints are backend-agnostic.
_mem_scenarios: dict[str, dict[str, Any]] = {}
_mem_runs: dict[str, dict[str, Any]] = {}
_mem_results: dict[str, list[dict[str, Any]]] = {}
_mem_audit: dict[str, list[dict[str, Any]]] = {}


def _dsn() -> str:
    return os.environ.get("DATABASE_URL") or os.environ.get("MATRIX_PG_DSN") or _DEFAULT_DSN


def _city_slug() -> str:
    return os.environ.get("MATRIX_CITY_SLUG", "iloilo")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso(value: Any) -> Any:
    """Timestamps go out as ISO strings on both backends (JSON-serializable)."""
    return value.isoformat() if isinstance(value, datetime) else value


def _schema_path() -> Path:
    override = os.environ.get("MATRIX_SCHEMA_PATH")
    if override:
        return Path(override)
    # matrix_api/db.py -> [0] matrix_api [1] api [2] apps [3] app
    return Path(__file__).resolve().parents[3] / "packages" / "data" / "schema.sql"


def _connect():
    """Open a psycopg3 connection with a short timeout. Raises on any failure."""
    import psycopg  # lazy: the fallback path must work without the driver installed

    return psycopg.connect(_dsn(), connect_timeout=CONNECT_TIMEOUT_S)


def init_db(force_backend: str | None = None) -> str:
    """Choose the persistence backend once and announce it. Never raises.

    Order: explicit `force_backend` arg > env MATRIX_DB_BACKEND > probe Postgres (~2 s
    timeout) > in-memory. Re-calling without `force_backend` is a no-op after the first
    choice (the startup hook and lazy per-op init can both call it safely).
    """
    global _backend
    with _lock:
        choice = force_backend or (None if _backend else os.environ.get("MATRIX_DB_BACKEND"))
        if choice in ("memory", "postgres"):
            _backend = choice
            if choice == "postgres":
                _apply_schema_best_effort()
            logger.info("persistence backend: %s (explicit)", _backend)
            return _backend
        if _backend is not None:
            return _backend
        try:
            with _connect():
                pass
            _backend = "postgres"
            _apply_schema_best_effort()
            logger.info("persistence backend: postgres (%s)", _redacted_dsn())
        except Exception as exc:  # driver missing, refused, auth, timeout, ...
            _backend = "memory"
            logger.warning(
                "persistence backend: in-memory (Postgres unavailable: %s). "
                "Results survive only this process; start docker compose for durability.",
                exc,
            )
        return _backend


def active_backend() -> str | None:
    return _backend


def _redacted_dsn() -> str:
    dsn = _dsn()
    if "@" in dsn and "://" in dsn:  # strip credentials for logs
        scheme, rest = dsn.split("://", 1)
        return f"{scheme}://***@{rest.rsplit('@', 1)[-1]}"
    return dsn


def _apply_schema_best_effort() -> None:
    """Apply packages/data/schema.sql (idempotent). A failure here is logged, not fatal —
    the schema may already be in place via load_postgis.py."""
    path = _schema_path()
    if not path.is_file():
        logger.warning("schema.sql not found at %s; assuming schema already applied", path)
        return
    try:
        # No bind params -> psycopg3 uses the simple query protocol, which accepts the
        # whole multi-statement file in one execute().
        with _connect() as conn:
            conn.execute(path.read_text(encoding="utf-8"))
            conn.commit()
    except Exception as exc:
        logger.warning("could not apply schema.sql (%s); continuing", exc)


def _ensure_init() -> str:
    return _backend or init_db()


def _flip_to_memory(exc: Exception) -> None:
    """Postgres died mid-session: degrade to in-memory rather than crash (the demo must
    keep running). Earlier rows stay in Postgres; the flip is logged loudly."""
    global _backend
    with _lock:
        if _backend != "memory":
            _backend = "memory"
            logger.error(
                "Postgres operation failed (%s) — falling back to in-memory persistence "
                "for the rest of this process", exc,
            )


# ─── scenarios ───────────────────────────────────────────────────────────────────────────


def _scenario_params(scenario: Any) -> dict[str, Any]:
    """Duck-typed snapshot of a kernel Scenario. v1 fields (corridor/lanes_closed) and
    Scenario-v2 fields (intervention_type/location/geometry/parameters) are both read
    defensively so this works before and after the orchestrator upgrade."""
    return {
        "description": getattr(scenario, "description", "") or "",
        "corridor": getattr(scenario, "corridor", None),
        "lanes_closed": getattr(scenario, "lanes_closed", None),
        "intervention_type": getattr(scenario, "intervention_type", None),
        "location": getattr(scenario, "location", None),
        "parameters": getattr(scenario, "parameters", None),
    }


def save_scenario(scenario: Any, raw_input: str = "", input_type: str = "nl") -> str:
    """Persist a parsed Scenario (upsert by scenario_id). Returns the scenario id."""
    _ensure_init()
    scenario_id = str(getattr(scenario, "scenario_id", "") or uuid.uuid4())
    params = _scenario_params(scenario)
    geometry = getattr(scenario, "geometry", None)  # GeoJSON dict | None (Scenario v2)
    record = {
        "scenario_id": scenario_id,
        "city_slug": _city_slug(),
        "input_type": input_type if input_type in ("nl", "map") else "nl",
        "raw_input": raw_input or "",
        "description": params["description"],
        "intervention_type": params["intervention_type"],
        "location": params["location"],
        "parsed_params": params,
        "geometry": geometry if isinstance(geometry, dict) else None,
        "created_at": _now_iso(),
    }
    if _backend == "postgres":
        try:
            _pg_save_scenario(record)
            return scenario_id
        except Exception as exc:
            _flip_to_memory(exc)
    with _lock:
        _mem_scenarios[scenario_id] = record
    return scenario_id


def _pg_save_scenario(record: dict[str, Any]) -> None:
    from psycopg.types.json import Json

    with _connect() as conn:
        conn.execute(
            "INSERT INTO scenarios (id, city_slug, input_type, raw_input, description,"
            "  intervention_type, location, parsed_params, geometry)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s,"
            "   CASE WHEN %s::text IS NULL THEN NULL"
            "        ELSE ST_SetSRID(ST_GeomFromGeoJSON(%s::text), 4326) END)"
            " ON CONFLICT (id) DO UPDATE SET"
            "  input_type = EXCLUDED.input_type, raw_input = EXCLUDED.raw_input,"
            "  description = EXCLUDED.description,"
            "  intervention_type = EXCLUDED.intervention_type, location = EXCLUDED.location,"
            "  parsed_params = EXCLUDED.parsed_params, geometry = EXCLUDED.geometry",
            (
                record["scenario_id"], record["city_slug"], record["input_type"],
                record["raw_input"], record["description"], record["intervention_type"],
                record["location"], Json(record["parsed_params"]),
                json.dumps(record["geometry"]) if record["geometry"] else None,
                json.dumps(record["geometry"]) if record["geometry"] else None,
            ),
        )
        conn.commit()


def get_scenario(scenario_id: str) -> dict[str, Any] | None:
    _ensure_init()
    if _backend == "postgres":
        try:
            return _pg_get_scenario(scenario_id)
        except Exception as exc:
            _flip_to_memory(exc)
    with _lock:
        record = _mem_scenarios.get(scenario_id)
        return dict(record) if record else None


def _pg_get_scenario(scenario_id: str) -> dict[str, Any] | None:
    from psycopg.rows import dict_row

    with _connect() as conn:
        row = conn.cursor(row_factory=dict_row).execute(
            "SELECT id AS scenario_id, city_slug, input_type, raw_input, description,"
            "  intervention_type, location, parsed_params,"
            "  ST_AsGeoJSON(geometry)::text AS geometry, created_at"
            " FROM scenarios WHERE id = %s",
            (scenario_id,),
        ).fetchone()
    if row is None:
        return None
    row["geometry"] = json.loads(row["geometry"]) if row["geometry"] else None
    row["created_at"] = _iso(row["created_at"])
    return row


# ─── runs ────────────────────────────────────────────────────────────────────────────────


def save_run(
    scenario_id: str,
    run_id: str | None = None,
    status: str = "queued",
    duration_ms: int | None = None,
    timings: dict[str, Any] | None = None,
    agent_count: int | None = None,
) -> str:
    """Create or update a run (upsert by run_id). Call once at WS ACCEPTED with
    status="running", again at DONE with status="done" + duration_ms. Returns run_id.

    A stub scenario row is ensured first so the runs.scenario_id FK always resolves
    (e.g. the cached "demo" scenario that never went through POST /scenario)."""
    _ensure_init()
    run_id = run_id or str(uuid.uuid4())
    if status not in _VALID_RUN_STATUSES:
        status = "failed"
    now = _now_iso()
    if _backend == "postgres":
        try:
            _pg_save_run(run_id, scenario_id, status, duration_ms, timings, agent_count)
            return run_id
        except Exception as exc:
            _flip_to_memory(exc)
    with _lock:
        existing = _mem_runs.get(run_id, {})
        _mem_runs[run_id] = {
            "run_id": run_id,
            "scenario_id": scenario_id,
            "baseline_id": existing.get("baseline_id"),  # shape parity with the pg reader
            "status": status,
            "duration_ms": duration_ms if duration_ms is not None else existing.get("duration_ms"),
            "agent_count": agent_count if agent_count is not None else existing.get("agent_count"),
            "timings": timings if timings is not None else existing.get("timings"),
            "created_at": existing.get("created_at", now),
            "completed_at": now if status in ("done", "failed") else existing.get("completed_at"),
        }
    return run_id


def _pg_save_run(
    run_id: str,
    scenario_id: str,
    status: str,
    duration_ms: int | None,
    timings: dict[str, Any] | None,
    agent_count: int | None,
) -> None:
    from psycopg.types.json import Json

    with _connect() as conn:
        conn.execute(  # FK target may not exist for cached/demo scenarios
            "INSERT INTO scenarios (id, city_slug, raw_input) VALUES (%s, %s, '')"
            " ON CONFLICT (id) DO NOTHING",
            (scenario_id, _city_slug()),
        )
        conn.execute(
            "INSERT INTO runs (run_id, scenario_id, status, duration_ms, timings, agent_count,"
            "  completed_at)"
            " VALUES (%s, %s, %s, %s, %s, %s,"
            "   CASE WHEN %s IN ('done','failed') THEN now() END)"
            " ON CONFLICT (run_id) DO UPDATE SET"
            "  status = EXCLUDED.status,"
            "  duration_ms = COALESCE(EXCLUDED.duration_ms, runs.duration_ms),"
            "  timings = COALESCE(EXCLUDED.timings, runs.timings),"
            "  agent_count = COALESCE(EXCLUDED.agent_count, runs.agent_count),"
            "  completed_at = COALESCE(EXCLUDED.completed_at, runs.completed_at)",
            (run_id, scenario_id, status, duration_ms,
             Json(timings) if timings is not None else None, agent_count, status),
        )
        conn.commit()


def get_run(run_id: str) -> dict[str, Any] | None:
    """The stored run + its dimension results with full glass-box provenance (PRD-F14)."""
    _ensure_init()
    if _backend == "postgres":
        try:
            return _pg_get_run(run_id)
        except Exception as exc:
            _flip_to_memory(exc)
    with _lock:
        run = _mem_runs.get(run_id)
        if run is None:
            return None
        return {**run, "results": [dict(r) for r in _mem_results.get(run_id, [])]}


def _pg_get_run(run_id: str) -> dict[str, Any] | None:
    from psycopg.rows import dict_row

    with _connect() as conn:
        cur = conn.cursor(row_factory=dict_row)
        run = cur.execute(
            "SELECT run_id, scenario_id, baseline_id, status, duration_ms, agent_count,"
            "  timings, created_at, completed_at FROM runs WHERE run_id = %s",
            (run_id,),
        ).fetchone()
        if run is None:
            return None
        rows = cur.execute(
            'SELECT dimension, metric, equation_id, value, range_low, range_high, unit,'
            '  confidence, directional_only, input_dataset_ids, "references", assumptions'
            " FROM dimension_results WHERE run_id = %s ORDER BY created_at, equation_id",
            (run_id,),
        ).fetchall()
    run["created_at"] = _iso(run["created_at"])
    run["completed_at"] = _iso(run["completed_at"])
    run["results"] = [
        {
            "dimension": r["dimension"],
            "metric": r["metric"],
            "equation_id": r["equation_id"],
            "value": r["value"],
            "range": [r["range_low"], r["range_high"]],
            "unit": r["unit"],
            "confidence": r["confidence"],
            "directional": r["directional_only"],
            "input_dataset_ids": list(r["input_dataset_ids"] or []),
            "references": list(r["references"] or []),
            "assumptions": r["assumptions"] or [],
        }
        for r in rows
    ]
    return run


# ─── dimension results (glass box, PRD-F14) ─────────────────────────────────────────────


def _result_record(r: Any) -> dict[str, Any]:
    """Serialize a DimensionResult duck-typed; same keys as the WS DIMENSION_RESULT event
    so a reloaded run feeds the Inspect drawer unchanged."""
    lo, hi = tuple(getattr(r, "range", (0.0, 0.0)))
    return {
        "dimension": getattr(r, "dimension"),
        "metric": getattr(r, "metric"),
        "equation_id": getattr(r, "equation_id"),
        "value": getattr(r, "value"),
        "range": [lo, hi],
        "unit": getattr(r, "unit"),
        "confidence": getattr(r, "confidence"),
        "directional": bool(getattr(r, "directional", getattr(r, "confidence", "") == "L")),
        "input_dataset_ids": list(getattr(r, "input_dataset_ids")),
        "references": list(getattr(r, "references", []) or []),
        "assumptions": list(getattr(r, "assumptions", []) or []),
    }


def save_dimension_results(run_id: str, results: list[Any]) -> int:
    """Persist module outputs for a run, full provenance intact. Returns the row count."""
    _ensure_init()
    records = [_result_record(r) for r in results]
    if _backend == "postgres":
        try:
            _pg_save_dimension_results(run_id, records)
            return len(records)
        except Exception as exc:
            _flip_to_memory(exc)
    with _lock:
        _mem_results.setdefault(run_id, []).extend(records)
    return len(records)


def _pg_save_dimension_results(run_id: str, records: list[dict[str, Any]]) -> None:
    from psycopg.types.json import Json

    with _connect() as conn:
        cur = conn.cursor()
        cur.executemany(
            "INSERT INTO dimension_results (run_id, dimension, metric, equation_id, value,"
            '  range_low, range_high, unit, confidence, directional_only, input_dataset_ids,'
            '  "references", assumptions)'
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            [
                (run_id, rec["dimension"], rec["metric"], rec["equation_id"], rec["value"],
                 rec["range"][0], rec["range"][1], rec["unit"], rec["confidence"],
                 rec["directional"], rec["input_dataset_ids"], rec["references"],
                 Json(rec["assumptions"]))
                for rec in records
            ],
        )
        conn.commit()


# ─── bias audit log (public, append-only — PRD-F6) ──────────────────────────────────────


def save_audit_entry(entry: Any, run_id: str | None = None) -> str:
    """Append a bias-audit entry (BiasAuditEntry duck-type or dict). Returns the entry id.

    The kernel's matrix_kernel.bias_auditor.persist_audit() writes the same table directly
    when it has a DB; this function is the API-side path that also covers the fallback."""
    _ensure_init()
    if isinstance(entry, dict):
        observed = entry.get("observed_mode_share") or entry.get("mode_share") or {}
        target = entry.get("target_mode_share") or entry.get("ground_truth") or {}
        max_delta = entry.get("max_delta")
        if max_delta is None:  # never store a fabricated 0.0 (glass box) — compute it
            modes = set(observed) | set(target)
            max_delta = max(
                (abs(observed.get(m, 0.0) - target.get(m, 0.0)) for m in modes), default=0.0
            )
        record = {
            "batch_id": entry.get("batch_id", ""),
            "observed_mode_share": observed,
            "target_mode_share": target,
            "max_delta": float(max_delta),
            "reweighted": bool(entry.get("reweighted", False)),
        }
    else:
        record = {
            "batch_id": getattr(entry, "batch_id", ""),
            "observed_mode_share": dict(getattr(entry, "observed_mode_share", {}) or {}),
            "target_mode_share": dict(getattr(entry, "target_mode_share", {}) or {}),
            "max_delta": float(getattr(entry, "max_delta", 0.0)),
            "reweighted": bool(getattr(entry, "reweighted", False)),
        }
    record["run_id"] = run_id
    record["timestamp"] = _now_iso()
    if _backend == "postgres":
        try:
            return _pg_save_audit_entry(record)
        except Exception as exc:
            _flip_to_memory(exc)
    entry_id = str(uuid.uuid4())
    with _lock:
        _mem_audit.setdefault(run_id or "", []).append({"id": entry_id, **record})
    return entry_id


def _pg_save_audit_entry(record: dict[str, Any]) -> str:
    from psycopg.types.json import Json

    with _connect() as conn:
        row = conn.execute(
            "INSERT INTO bias_audit_log (run_id, batch_id, mode_share, ground_truth,"
            "  max_delta, reweighted) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (record["run_id"], record["batch_id"], Json(record["observed_mode_share"]),
             Json(record["target_mode_share"]), record["max_delta"], record["reweighted"]),
        ).fetchone()
        conn.commit()
    return str(row[0])


def get_audit(run_id: str) -> list[dict[str, Any]]:
    """All audit entries for a run, oldest first. Empty list when none (never fabricated)."""
    _ensure_init()
    if _backend == "postgres":
        try:
            return _pg_get_audit(run_id)
        except Exception as exc:
            _flip_to_memory(exc)
    with _lock:
        return [dict(e) for e in _mem_audit.get(run_id, [])]


def _pg_get_audit(run_id: str) -> list[dict[str, Any]]:
    from psycopg.rows import dict_row

    with _connect() as conn:
        rows = conn.cursor(row_factory=dict_row).execute(
            "SELECT id, run_id, batch_id, mode_share, ground_truth, max_delta, reweighted,"
            "  created_at FROM bias_audit_log WHERE run_id = %s ORDER BY created_at, id",
            (run_id,),
        ).fetchall()
    return [
        {
            "id": str(r["id"]),
            "run_id": r["run_id"],
            "batch_id": r["batch_id"],
            "observed_mode_share": r["mode_share"],
            "target_mode_share": r["ground_truth"],
            "max_delta": float(r["max_delta"]),
            "reweighted": r["reweighted"],
            "timestamp": _iso(r["created_at"]),
        }
        for r in rows
    ]


# ─── test seam ───────────────────────────────────────────────────────────────────────────


def _reset_for_tests() -> None:
    """Clear the chosen backend + the in-memory store (test isolation only)."""
    global _backend
    with _lock:
        _backend = None
        _mem_scenarios.clear()
        _mem_runs.clear()
        _mem_results.clear()
        _mem_audit.clear()
