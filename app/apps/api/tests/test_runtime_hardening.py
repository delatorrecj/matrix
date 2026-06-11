"""WS pipeline hardening tests (feat/api-hardening). Every kernel seam
(_get_trajectory, module scorers, synthesize) is mocked, so no Redis server or
Gemini key is needed -- but importing matrix_api.main pulls the kernel's import
chain, which requires the eclipse-sumo wheel, so a bare env skips this module
(pure runtime.py units run bare in tests/test_runtime_unit.py). Covers: DONE
timings, per-stage timeouts -> typed ERROR, the FIFO concurrency gate (QUEUED),
slot cleanup on disconnect/failure, the dependency-aware /health, and the
merge-order-safe matrix_api.db seam."""
from __future__ import annotations

import threading
import time

import pytest

# matrix_api.main imports the kernel modules, whose import chain requires the
# eclipse-sumo wheel (matrix_kernel.sumo_env wires SUMO_HOME at import). Same
# guard convention as the kernel's SUMO-dependent test modules: skip cleanly
# in a bare env instead of erroring at collection.
pytest.importorskip("sumo", reason="eclipse-sumo not installed (bare env)")

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from matrix_api import main, runtime
from matrix_kernel.results import DimensionResult
from matrix_kernel.trajectory import Frame, Trajectory

FAKE_TRAJ = Trajectory(
    edge_counts={"edge-1": 10},
    frames=[Frame(tick=0.0, agents=[{"id": "a1", "lon": 122.56, "lat": 10.72, "mode": "jeepney"}])],
    meta={"kind": "scenario"},
)


def _fake_result(dimension: str, equation_id: str) -> DimensionResult:
    return DimensionResult(
        dimension=dimension,
        metric=f"fake {equation_id}",
        equation_id=equation_id,
        value=1.0,
        range=(0.5, 1.5),
        unit="x",
        confidence="M",
        input_dataset_ids=["TEST-DS"],
    )


def _drain(ws) -> list[dict]:
    """Collect events until a terminal DONE or ERROR."""
    events = []
    while True:
        data = ws.receive_json()
        events.append(data)
        if data["type"] in ("DONE", "ERROR"):
            return events


def _wait_until(cond, timeout_s: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if cond():
            return True
        time.sleep(0.02)
    return cond()


@pytest.fixture(autouse=True)
def fresh_gate(monkeypatch):
    """Isolate the concurrency gate per test (main reads runtime.GATE at call time)."""
    monkeypatch.setattr(runtime, "GATE", runtime.SimGate())


@pytest.fixture
def client():
    return TestClient(main.app)


@pytest.fixture
def fast_pipeline(monkeypatch):
    """Mock every kernel seam so the WS pipeline runs bare (no Redis/SUMO/Gemini)."""
    monkeypatch.setattr(main, "_get_trajectory", lambda scenario_id: FAKE_TRAJ)
    monkeypatch.setattr(main.behavioral, "score", lambda traj: [_fake_result("behavioral", "BEH-1")])
    monkeypatch.setattr(main.ecological, "score", lambda traj: [_fake_result("ecological", "ECO-2")])
    monkeypatch.setattr(main.social, "score", lambda traj: [_fake_result("social", "SOC-1")])
    monkeypatch.setattr(main.economic, "score", lambda traj: [_fake_result("economic", "ECON-1")])
    monkeypatch.setattr(
        main.societal, "score", lambda traj, eco2_val=0.0: [_fake_result("societal", "SOCI-1")]
    )
    monkeypatch.setattr(
        main,
        "synthesize",
        lambda results: (
            "Narrative [BEH-1].",
            [{"claim": "x", "equation_id": "BEH-1", "dataset_ids": ["TEST-DS"]}],
        ),
    )


# --- DONE timings -----------------------------------------------------------------


def test_done_carries_timings_and_event_order(fast_pipeline, client):
    with client.websocket_connect("/simulate/s1") as ws:
        events = _drain(ws)

    types = [e["type"] for e in events]
    assert types[0] == "ACCEPTED"
    assert types[-2] == "SYNTHESIS"
    assert types[-1] == "DONE"
    assert types.count("PLAYBACK_FRAME") == 1
    assert types.count("DIMENSION_RESULT") == 5
    assert "QUEUED" not in types  # under capacity -> no queueing

    done = events[-1]
    assert done["scenario_id"] == "s1"
    assert "duration_ms" in done  # pre-existing key, kept for back-compat
    timings = done["timings"]
    # Exact frontend contract -- do not change these keys.
    assert set(timings) == {"sumo_ms", "modules_ms", "gemini_ms", "total_ms"}
    assert all(isinstance(v, int) and v >= 0 for v in timings.values())
    assert timings["total_ms"] >= max(
        timings["sumo_ms"], timings["modules_ms"], timings["gemini_ms"]
    )
    assert done["duration_ms"] == timings["total_ms"]


# --- stage timeouts -> typed ERROR --------------------------------------------------


def test_stage_timeout_emits_error_with_stage(fast_pipeline, client, monkeypatch):
    monkeypatch.setenv("MATRIX_STAGE_TIMEOUT_SUMO_S", "0.2")
    release = threading.Event()

    def slow_traj(scenario_id):
        release.wait(5)
        return FAKE_TRAJ

    monkeypatch.setattr(main, "_get_trajectory", slow_traj)
    try:
        with client.websocket_connect("/simulate/slow") as ws:
            assert ws.receive_json()["type"] == "ACCEPTED"
            err = ws.receive_json()
        assert err["type"] == "ERROR"
        assert err["scenario_id"] == "slow"
        assert err["stage"] == "sumo"
        assert err["recoverable"] is True
        assert set(err) == {"type", "scenario_id", "stage", "message", "recoverable"}
    finally:
        release.set()  # unblock the abandoned worker thread

    # The timed-out run must not leak its slot.
    assert _wait_until(lambda: runtime.GATE.snapshot()["active"] == 0)


def test_synthesis_failure_is_recoverable_error(fast_pipeline, client, monkeypatch):
    def boom(results):
        raise RuntimeError("Gemini exploded")

    monkeypatch.setattr(main, "synthesize", boom)
    with client.websocket_connect("/simulate/synthfail") as ws:
        events = _drain(ws)

    err = events[-1]
    assert err["type"] == "ERROR"
    assert err["stage"] == "synthesis"
    assert err["recoverable"] is True
    assert "Gemini exploded" in err["message"]
    # The glass-box numbers still streamed before the narrative failed.
    assert sum(1 for e in events if e["type"] == "DIMENSION_RESULT") == 5
    assert _wait_until(lambda: runtime.GATE.snapshot()["active"] == 0)


def test_early_stage_failure_is_unrecoverable_error(fast_pipeline, client, monkeypatch):
    def broken_traj(scenario_id):
        raise ValueError("no such scenario")

    monkeypatch.setattr(main, "_get_trajectory", broken_traj)
    with client.websocket_connect("/simulate/broken") as ws:
        assert ws.receive_json()["type"] == "ACCEPTED"
        err = ws.receive_json()

    assert err["type"] == "ERROR"
    assert err["stage"] == "sumo"
    assert err["recoverable"] is False
    assert "no such scenario" in err["message"]
    assert _wait_until(lambda: runtime.GATE.snapshot()["active"] == 0)


# --- concurrency gate ----------------------------------------------------------------


def test_third_concurrent_sim_is_queued_then_runs(fast_pipeline, client, monkeypatch):
    hold = threading.Event()

    def blocking_traj(scenario_id):
        hold.wait(10)
        return FAKE_TRAJ

    monkeypatch.setattr(main, "_get_trajectory", blocking_traj)
    try:
        with client.websocket_connect("/simulate/a") as wsa, client.websocket_connect(
            "/simulate/b"
        ) as wsb:
            assert wsa.receive_json()["type"] == "ACCEPTED"
            assert wsb.receive_json()["type"] == "ACCEPTED"
            with client.websocket_connect("/simulate/c") as wsc:
                assert wsc.receive_json()["type"] == "ACCEPTED"
                queued = wsc.receive_json()
                assert queued == {"type": "QUEUED", "scenario_id": "c", "position": 1}
                assert runtime.GATE.snapshot() == {"active": 2, "queued": 1, "limit": 2}

                hold.set()
                assert _drain(wsa)[-1]["type"] == "DONE"
                assert _drain(wsb)[-1]["type"] == "DONE"
                # The queued run is admitted FIFO once a slot frees, then completes.
                assert _drain(wsc)[-1]["type"] == "DONE"
    finally:
        hold.set()

    assert _wait_until(
        lambda: runtime.GATE.snapshot() == {"active": 0, "queued": 0, "limit": 2}
    )


def test_queued_client_times_out_with_error(fast_pipeline, client, monkeypatch):
    monkeypatch.setenv("MATRIX_QUEUE_TIMEOUT_S", "0.2")
    monkeypatch.setenv("MATRIX_MAX_CONCURRENT_SIMS", "1")
    hold = threading.Event()

    def blocking_traj(scenario_id):
        hold.wait(10)
        return FAKE_TRAJ

    monkeypatch.setattr(main, "_get_trajectory", blocking_traj)
    try:
        with client.websocket_connect("/simulate/holder") as ws1:
            assert ws1.receive_json()["type"] == "ACCEPTED"
            with client.websocket_connect("/simulate/waiter") as ws2:
                assert ws2.receive_json()["type"] == "ACCEPTED"
                assert ws2.receive_json()["type"] == "QUEUED"
                err = ws2.receive_json()
                assert err["type"] == "ERROR"
                assert err["stage"] == "queue"
                assert err["recoverable"] is True
            # The abandoned waiter must leave the queue empty.
            assert _wait_until(lambda: runtime.GATE.snapshot()["queued"] == 0)
            hold.set()
            assert _drain(ws1)[-1]["type"] == "DONE"
    finally:
        hold.set()

    assert _wait_until(lambda: runtime.GATE.snapshot()["active"] == 0)


def test_disconnect_while_queued_abandons_ticket(fast_pipeline, client, monkeypatch):
    """A client that walks away while QUEUED must leave the queue immediately --
    not later win a slot and run the pipeline against a dead socket."""
    monkeypatch.setenv("MATRIX_MAX_CONCURRENT_SIMS", "1")
    hold = threading.Event()

    def blocking_traj(scenario_id):
        hold.wait(10)
        return FAKE_TRAJ

    monkeypatch.setattr(main, "_get_trajectory", blocking_traj)
    try:
        with client.websocket_connect("/simulate/holder") as ws1:
            assert ws1.receive_json()["type"] == "ACCEPTED"
            with client.websocket_connect("/simulate/walker") as ws2:
                assert ws2.receive_json()["type"] == "ACCEPTED"
                assert ws2.receive_json()["type"] == "QUEUED"
            # ws2 closed while queued: ticket abandoned, slot count untouched.
            assert _wait_until(lambda: runtime.GATE.snapshot()["queued"] == 0)
            assert runtime.GATE.snapshot()["active"] == 1
            hold.set()
            assert _drain(ws1)[-1]["type"] == "DONE"
    finally:
        hold.set()

    assert _wait_until(lambda: runtime.GATE.snapshot() == {"active": 0, "queued": 0, "limit": 1})


def test_disconnect_mid_run_releases_slot(fast_pipeline, client, monkeypatch):
    """A WebSocketDisconnect surfacing mid-pipeline (the way Starlette reports a
    client that walked away) must release the gate slot -- no leak."""

    def dying_traj(scenario_id):
        raise WebSocketDisconnect(1001)

    monkeypatch.setattr(main, "_get_trajectory", dying_traj)
    with client.websocket_connect("/simulate/gone") as ws:
        assert ws.receive_json()["type"] == "ACCEPTED"

    assert _wait_until(
        lambda: runtime.GATE.snapshot() == {"active": 0, "queued": 0, "limit": 2}
    )


# --- dependency-aware /health -------------------------------------------------------------


def test_health_degraded_when_redis_down(client, monkeypatch):
    # Port 9 (discard) on localhost: nothing listens -> connect fails fast.
    monkeypatch.setattr(main, "REDIS_URL", "redis://127.0.0.1:9/0")
    t0 = time.monotonic()
    resp = client.get("/health")
    elapsed = time.monotonic() - t0

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["service"] == "matrix-api"
    assert body["dependencies"]["redis"]["status"] == "down"
    assert set(body["dependencies"]) == {"redis", "database", "gemini"}
    assert elapsed < 2.5  # never blocks > ~2 s, even with deps down


def test_health_ok_when_dependencies_up(client, monkeypatch):
    monkeypatch.setattr(
        runtime, "check_redis", lambda url, timeout_s=0.5: {"status": "ok", "detail": None}
    )
    monkeypatch.setattr(runtime, "check_gemini", lambda: {"status": "ok", "detail": None})
    # An unconfigured DB must NOT degrade: persistence is optional + fallback-safe.
    monkeypatch.setattr(
        runtime, "check_database", lambda timeout_s=0.5: {"status": "unconfigured", "detail": "x"}
    )
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["dependencies"]["database"]["status"] == "unconfigured"


def test_health_degraded_when_db_configured_but_down(client, monkeypatch):
    monkeypatch.setattr(
        runtime, "check_redis", lambda url, timeout_s=0.5: {"status": "ok", "detail": None}
    )
    monkeypatch.setattr(runtime, "check_gemini", lambda: {"status": "ok", "detail": None})
    monkeypatch.setenv("MATRIX_DATABASE_URL", "postgresql://user:pw@127.0.0.1:9/matrix")
    body = client.get("/health").json()
    assert body["status"] == "degraded"
    assert body["dependencies"]["database"]["status"] == "down"


# --- db persistence seam (feat/api-persistence, merge-order safe) ----------------------------


class _StubDB:
    """Stands in for matrix_api.db with a timings-aware save_run."""

    def __init__(self):
        self.calls = []

    def save_run(self, scenario_id, run_id=None, status=None, duration_ms=None, timings=None):
        self.calls.append(("save_run", scenario_id, run_id, status, duration_ms, timings))
        return "run-1"

    def save_dimension_results(self, run_id, results):
        self.calls.append(("save_dimension_results", run_id, len(results)))


class _LegacyDB(_StubDB):
    """A db whose save_run predates the timings kwarg -- must still be called."""

    def save_run(self, scenario_id, run_id=None, status=None, duration_ms=None):
        self.calls.append(("save_run", scenario_id, run_id, status, duration_ms, None))
        return "run-1"


def test_db_seam_persists_run_and_results(fast_pipeline, client, monkeypatch):
    stub = _StubDB()
    monkeypatch.setattr(runtime, "_db", stub)
    with client.websocket_connect("/simulate/persisted") as ws:
        assert _drain(ws)[-1]["type"] == "DONE"

    names = [c[0] for c in stub.calls]
    assert names == ["save_run", "save_dimension_results", "save_run"]
    start, dims, done = stub.calls
    assert start[1:4] == ("persisted", None, "running")
    assert dims[1:] == ("run-1", 5)
    assert done[1:4] == ("persisted", "run-1", "done")
    assert isinstance(done[4], int)  # duration_ms
    assert set(done[5]) == {"sumo_ms", "modules_ms", "gemini_ms", "total_ms"}  # timings


def test_db_seam_tolerates_legacy_signature(fast_pipeline, client, monkeypatch):
    stub = _LegacyDB()
    monkeypatch.setattr(runtime, "_db", stub)
    with client.websocket_connect("/simulate/legacy") as ws:
        assert _drain(ws)[-1]["type"] == "DONE"

    done = stub.calls[-1]
    assert done[0] == "save_run" and done[3] == "done" and done[5] is None


def test_db_seam_never_raises_into_pipeline(fast_pipeline, client, monkeypatch):
    class ExplodingDB:
        def save_run(self, *a, **k):
            raise RuntimeError("db down")

        def save_dimension_results(self, *a, **k):
            raise RuntimeError("db down")

    monkeypatch.setattr(runtime, "_db", ExplodingDB())
    with client.websocket_connect("/simulate/dbdown") as ws:
        assert _drain(ws)[-1]["type"] == "DONE"  # pipeline unaffected
