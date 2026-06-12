"""Persistence tests — REST surface + matrix_api.db on both backends.

Bare mode (no Postgres, no SUMO, no Redis): the in-memory fallback is exercised
end-to-end through FastAPI TestClient — create scenario -> read back, runs lifecycle
with full glass-box provenance, audit log, and /validation fallbacks. The Postgres
round-trip tests skip cleanly when DATABASE_URL is unreachable (they run post-merge
against docker compose).
"""
from __future__ import annotations

import json
import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import matrix_api.db as db
import matrix_api.main as main

# Pure kernel modules (no SUMO/Redis): the real glass-box contract + audit entry shape.
from matrix_kernel.results import DimensionResult
from matrix_kernel.bias_auditor import audit_personas


def _fake_scenario(scenario_id: str):
    """A Scenario v1 double with v2 fields riding along (PR #2 forward-compat)."""
    return SimpleNamespace(
        scenario_id=scenario_id,
        description="close one lane on Diversion Rd",
        corridor="Diversion",
        lanes_closed=1,
        intervention_type="lane_closure",  # v2
        location="Diversion Rd",           # v2
        geometry={"type": "Point", "coordinates": [122.5621, 10.7202]},  # v2 GeoJSON
        parameters={"lanes_closed": 1},    # v2
    )


def _results(n: int = 2) -> list[DimensionResult]:
    """Real DimensionResults so persistence is tested against the kernel contract."""
    base = [
        DimensionResult(
            dimension="behavioral",
            metric="delta trips/day on corridor",
            equation_id="BEH-1",
            value=-1240.0,
            range=(-1600.0, -900.0),
            unit="trips/day",
            confidence="M",
            input_dataset_ids=["OSM-ILO", "SUMO-NET"],
            references=["Calderon 2014"],
            assumptions=["uncalibrated random demand"],
        ),
        DimensionResult(
            dimension="ecological",
            metric="delta CO2 (corridor)",
            equation_id="ECO-2",
            value=4.2,
            range=(2.0, 6.5),
            unit="t/day",
            confidence="L",
            input_dataset_ids=["HBEFA"],
        ),
    ]
    return base[:n]


@pytest.fixture
def client(monkeypatch):
    """TestClient pinned to the in-memory backend (even if a local Postgres is up)."""
    db._reset_for_tests()
    db.init_db(force_backend="memory")
    monkeypatch.delenv("MATRIX_VALIDATION_REPORT", raising=False)
    with TestClient(main.app) as c:
        yield c
    db._reset_for_tests()


# ─── backend selection ───────────────────────────────────────────────────────────────────


def test_falls_back_to_memory_when_db_unreachable(monkeypatch):
    db._reset_for_tests()
    # Port 9 (discard) refuses immediately; the ~2 s connect timeout bounds the worst case.
    monkeypatch.setenv("DATABASE_URL", "postgresql://nobody:nope@127.0.0.1:9/matrix")
    monkeypatch.delenv("MATRIX_DB_BACKEND", raising=False)
    assert db.init_db() == "memory"
    assert db.active_backend() == "memory"
    db._reset_for_tests()


def test_init_is_idempotent():
    db._reset_for_tests()
    assert db.init_db(force_backend="memory") == "memory"
    assert db.init_db() == "memory"  # second call keeps the choice
    db._reset_for_tests()


# ─── scenario round-trip (POST /scenario -> db) ─────────────────────────────────────────


def test_scenario_roundtrip(client, monkeypatch):
    monkeypatch.setattr(main, "parse_scenario", lambda q: _fake_scenario("scn-test-1"))
    resp = client.post("/scenario", json={"query": "close a lane on Diversion Rd"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["scenario_id"] == "scn-test-1"
    assert body["corridor"] == "Diversion"
    assert body["intervention_type"] == "lane_closure"  # v2 rides along

    stored = db.get_scenario("scn-test-1")
    assert stored is not None
    assert stored["raw_input"] == "close a lane on Diversion Rd"
    assert stored["input_type"] == "nl"
    assert stored["city_slug"]  # from MATRIX_CITY_SLUG (default iloilo), never hardcoded
    assert stored["parsed_params"]["corridor"] == "Diversion"
    assert stored["parsed_params"]["lanes_closed"] == 1
    assert stored["geometry"]["type"] == "Point"


def test_scenario_v1_only_fields(client, monkeypatch):
    """Persistence works for a plain v1 Scenario (no v2 attributes at all)."""
    v1 = SimpleNamespace(scenario_id="scn-v1", description="v1", corridor="Molo", lanes_closed=2)
    monkeypatch.setattr(main, "parse_scenario", lambda q: v1)
    assert client.post("/scenario", json={"query": "q"}).status_code == 200
    stored = db.get_scenario("scn-v1")
    assert stored["parsed_params"]["intervention_type"] is None
    assert stored["geometry"] is None


def test_scenario_ambiguous_returns_400(client, monkeypatch):
    def boom(q):
        raise ValueError("which corridor?")
    monkeypatch.setattr(main, "parse_scenario", boom)
    resp = client.post("/scenario", json={"query": "build something somewhere"})
    assert resp.status_code == 400
    assert resp.json()["is_ambiguous"] is True


# ─── runs lifecycle (save_run -> save_dimension_results -> GET /runs/{id}) ──────────────


def test_runs_lifecycle_full_provenance(client):
    scenario_id = db.save_scenario(_fake_scenario("scn-run"), raw_input="q")
    run_id = db.save_run(scenario_id, status="running")

    resp = client.get(f"/runs/{run_id}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"
    assert resp.json()["results"] == []

    assert db.save_dimension_results(run_id, _results()) == 2
    db.save_run(scenario_id, run_id=run_id, status="done", duration_ms=8421,
                timings={"kernel_s": 6.1, "modules_s": 1.9})

    body = client.get(f"/runs/{run_id}").json()
    assert body["status"] == "done"
    assert body["duration_ms"] == 8421
    assert body["timings"]["kernel_s"] == 6.1
    assert body["completed_at"] is not None

    # Glass box (PRD-F14): a stored run is as inspectable as a live one — every field
    # of the WS DIMENSION_RESULT payload survives the round-trip.
    results = body["results"]
    assert {r["equation_id"] for r in results} == {"BEH-1", "ECO-2"}
    beh = next(r for r in results if r["equation_id"] == "BEH-1")
    assert beh["dimension"] == "behavioral"
    assert beh["metric"] == "delta trips/day on corridor"
    assert beh["value"] == -1240.0
    assert beh["range"] == [-1600.0, -900.0]
    assert beh["unit"] == "trips/day"
    assert beh["confidence"] == "M"
    assert beh["directional"] is False
    assert beh["input_dataset_ids"] == ["OSM-ILO", "SUMO-NET"]
    assert beh["references"] == ["Calderon 2014"]
    assert beh["assumptions"] == ["uncalibrated random demand"]
    eco = next(r for r in results if r["equation_id"] == "ECO-2")
    assert eco["confidence"] == "L" and eco["directional"] is True  # PRD-F5


def test_unknown_run_is_404(client):
    resp = client.get("/runs/never-ran")
    assert resp.status_code == 404
    assert resp.json()["error"] == "run not found"


# ─── audit log (PRD-F6) ─────────────────────────────────────────────────────────────────


def test_audit_roundtrip(client):
    entry = audit_personas(
        observed={"jeepney": 0.50, "private": 0.30, "walk": 0.20},
        target={"jeepney": 0.55, "private": 0.25, "walk": 0.20},
        batch_id="b-1",
    )
    assert entry.reweighted is True  # 5% > 3% tolerance
    db.save_audit_entry(entry, run_id="run-a")

    body = client.get("/audit/run-a").json()
    assert body["run_id"] == "run-a"
    assert body["batch_id"] == "b-1"
    assert body["reweighted"] is True
    assert body["target_mode_share"]["jeepney"] == 0.55
    assert body["observed_mode_share"]["jeepney"] == 0.50
    assert body["max_delta"] == pytest.approx(0.05)
    assert len(body["entries"]) == 1


def test_audit_dict_entry_computes_max_delta(client):
    """A dict entry without max_delta gets it computed, never a fabricated 0.0."""
    db.save_audit_entry(
        {"batch_id": "b-2", "mode_share": {"jeepney": 0.50}, "ground_truth": {"jeepney": 0.55}},
        run_id="run-b",
    )
    body = client.get("/audit/run-b").json()
    assert body["max_delta"] == pytest.approx(0.05)
    assert body["observed_mode_share"] == {"jeepney": 0.50}


def test_audit_never_fabricated(client):
    """No entries -> empty shapes + a note; never the old mock numbers."""
    body = client.get("/audit/run-without-audit").json()
    assert body["entries"] == []
    assert body["target_mode_share"] == {}
    assert body["reweighted"] is False
    assert "note" in body


# ─── GET /validation ────────────────────────────────────────────────────────────────────


def test_validation_serves_report_file(client, tmp_path, monkeypatch):
    report = {"schema_version": 1, "generated_at": "2026-06-11T00:00:00Z",
              "kernel": "0.1.0", "gates": [{"gate": "VAL-01", "status": "NOT_RUN"}]}
    path = tmp_path / "validation_report.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    monkeypatch.setenv("MATRIX_VALIDATION_REPORT", str(path))
    assert client.get("/validation").json() == report  # served verbatim


def test_validation_falls_back_to_kernel_module(client, tmp_path, monkeypatch):
    # Point at a non-existent report so the module path is exercised even after a
    # real validation_report.json lands in the repo (PR #5).
    monkeypatch.setenv("MATRIX_VALIDATION_REPORT", str(tmp_path / "missing.json"))
    body = client.get("/validation").json()
    assert body["source"] == "matrix_kernel.validation"
    assert isinstance(body["gates"], list) and body["gates"]


def test_validation_honest_when_module_missing(client, tmp_path, monkeypatch):
    import sys
    monkeypatch.setenv("MATRIX_VALIDATION_REPORT", str(tmp_path / "missing.json"))
    monkeypatch.setitem(sys.modules, "matrix_kernel.validation", None)  # forces ImportError
    body = client.get("/validation").json()
    assert body == {"gates": [], "note": "validation module not available"}


# ─── Postgres round-trip (skips cleanly without a reachable DATABASE_URL) ───────────────


def _postgres_available() -> bool:
    try:
        import psycopg

        with psycopg.connect(db._dsn(), connect_timeout=2):
            return True
    except Exception:
        return False


requires_postgres = pytest.mark.skipif(
    not _postgres_available(), reason="Postgres unreachable at DATABASE_URL (docker compose down)"
)


@requires_postgres
def test_postgres_full_roundtrip():
    db._reset_for_tests()
    assert db.init_db(force_backend="postgres") == "postgres"
    sid = f"scn-pg-{uuid.uuid4().hex[:8]}"
    try:
        db.save_scenario(_fake_scenario(sid), raw_input="pg round-trip", input_type="nl")
        stored = db.get_scenario(sid)
        assert stored["raw_input"] == "pg round-trip"
        assert stored["geometry"]["type"] == "Point"
        assert stored["parsed_params"]["corridor"] == "Diversion"

        run_id = db.save_run(sid, status="running")
        assert db.save_dimension_results(run_id, _results()) == 2
        db.save_run(sid, run_id=run_id, status="done", duration_ms=1234, timings={"t": 1})

        run = db.get_run(run_id)
        assert db.active_backend() == "postgres"  # no silent fallback mid-test
        assert run["status"] == "done" and run["duration_ms"] == 1234
        assert {r["equation_id"] for r in run["results"]} == {"BEH-1", "ECO-2"}
        beh = next(r for r in run["results"] if r["equation_id"] == "BEH-1")
        assert beh["range"] == [-1600.0, -900.0]
        assert beh["input_dataset_ids"] == ["OSM-ILO", "SUMO-NET"]
        assert beh["assumptions"] == ["uncalibrated random demand"]

        entry = audit_personas(observed={"jeepney": 0.54}, target={"jeepney": 0.55}, batch_id="b-pg")
        db.save_audit_entry(entry, run_id=run_id)
        audit = db.get_audit(run_id)
        assert len(audit) == 1 and audit[0]["reweighted"] is False
        assert audit[0]["target_mode_share"] == {"jeepney": 0.55}
    finally:
        # Clean up (CASCADE removes the run + results; audit rows go explicitly).
        import psycopg

        with psycopg.connect(db._dsn(), connect_timeout=2) as conn:
            conn.execute("DELETE FROM bias_audit_log WHERE batch_id = 'b-pg'")
            conn.execute("DELETE FROM scenarios WHERE id = %s", (sid,))
            conn.commit()
        db._reset_for_tests()
