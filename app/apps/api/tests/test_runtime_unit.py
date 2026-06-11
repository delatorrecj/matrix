"""Pure runtime.py unit tests -- run BARE (no SUMO/Redis/Gemini, no app import).

matrix_api.runtime is stdlib-only (its kernel/db imports are guarded), so these
run in any environment -- unlike tests/test_runtime_hardening.py, whose WS
pipeline tests import matrix_api.main and therefore need the eclipse-sumo wheel.
Covers: the FIFO concurrency gate, stage timers, the typed StageTimeout path,
env knobs, the exact ERROR event shape, and the cheap health checkers.
"""
from __future__ import annotations

import asyncio

import pytest

from matrix_api import runtime


# --- concurrency gate ---------------------------------------------------------------


def test_sim_gate_fifo_abandon_release(monkeypatch):
    monkeypatch.setenv("MATRIX_MAX_CONCURRENT_SIMS", "1")
    gate = runtime.SimGate()

    ok, ticket, pos = gate.admit()
    assert (ok, ticket, pos) == (True, -1, 0)

    ok2, t2, p2 = gate.admit()
    ok3, t3, p3 = gate.admit()
    assert not ok2 and p2 == 1
    assert not ok3 and p3 == 2

    assert not gate.poll(t2)  # no free slot yet
    gate.release()
    assert not gate.poll(t3)  # FIFO: t2 is ahead
    assert gate.poll(t2)

    gate.abandon(t3)
    gate.abandon(t3)  # idempotent
    gate.release()
    assert gate.snapshot() == {"active": 0, "queued": 0, "limit": 1}

    gate.release()  # over-release never goes negative
    assert gate.snapshot()["active"] == 0


def test_sim_gate_limit_env(monkeypatch):
    monkeypatch.delenv("MATRIX_MAX_CONCURRENT_SIMS", raising=False)
    monkeypatch.delenv("MAX_CONCURRENT_SIMS", raising=False)
    assert runtime.SimGate.limit() == 2  # documented default
    monkeypatch.setenv("MAX_CONCURRENT_SIMS", "5")
    assert runtime.SimGate.limit() == 5
    monkeypatch.setenv("MATRIX_MAX_CONCURRENT_SIMS", "3")  # prefixed name wins
    assert runtime.SimGate.limit() == 3
    monkeypatch.setenv("MATRIX_MAX_CONCURRENT_SIMS", "0")  # floor of 1
    assert runtime.SimGate.limit() == 1
    monkeypatch.setenv("MATRIX_MAX_CONCURRENT_SIMS", "junk")
    assert runtime.SimGate.limit() == 2


def test_wait_for_slot_times_out_as_queue_stage(monkeypatch):
    monkeypatch.setenv("MATRIX_MAX_CONCURRENT_SIMS", "1")
    gate = runtime.SimGate()
    assert gate.admit()[0]
    ok, ticket, _ = gate.admit()
    assert not ok

    async def go():
        with pytest.raises(runtime.StageTimeout) as ei:
            await runtime.wait_for_slot(gate, ticket, timeout_s=0.1, poll_s=0.01)
        assert ei.value.stage == "queue"

    asyncio.run(go())
    gate.abandon(ticket)
    gate.release()
    assert gate.snapshot() == {"active": 0, "queued": 0, "limit": 1}


# --- stage timeouts -------------------------------------------------------------------


def test_stage_timeout_env_overrides(monkeypatch):
    assert runtime.stage_timeout_s("sumo") == 120.0
    assert runtime.stage_timeout_s("modules") == 60.0
    assert runtime.stage_timeout_s("gemini") == 30.0
    monkeypatch.setenv("MATRIX_STAGE_TIMEOUT_GEMINI_S", "5.5")
    assert runtime.stage_timeout_s("gemini") == 5.5
    monkeypatch.setenv("MATRIX_STAGE_TIMEOUT_GEMINI_S", "not-a-number")
    assert runtime.stage_timeout_s("gemini") == 30.0
    monkeypatch.setenv("MATRIX_QUEUE_TIMEOUT_S", "1")
    assert runtime.queue_timeout_s() == 1.0


def test_run_stage_timeout_raises_typed_stage_timeout():
    async def go():
        with pytest.raises(runtime.StageTimeout) as ei:
            await runtime.run_stage(asyncio.sleep(5), stage="sumo", timeout_s=0.05)
        assert ei.value.stage == "sumo"
        assert "sumo" in str(ei.value)

    asyncio.run(go())


def test_run_stage_zero_disables_timeout():
    async def go():
        return await runtime.run_stage(
            asyncio.sleep(0, result=42), stage="gemini", timeout_s=0
        )

    assert asyncio.run(go()) == 42


# --- typed events + timings ------------------------------------------------------------


def test_error_event_shape_is_exact():
    ev = runtime.error_event("s1", "sumo", "boom", True)
    assert ev == {
        "type": "ERROR",
        "scenario_id": "s1",
        "stage": "sumo",
        "message": "boom",
        "recoverable": True,
    }


def test_stage_timer_keys():
    timer = runtime.StageTimer()
    with timer.stage("sumo"):
        pass
    with timer.stage("modules"):
        pass
    with timer.stage("gemini"):
        pass
    t = timer.timings()
    assert set(t) == {"sumo_ms", "modules_ms", "gemini_ms", "total_ms"}
    assert all(isinstance(v, int) for v in t.values())


# --- health checkers ---------------------------------------------------------------------


def test_check_gemini_key_presence(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    assert runtime.check_gemini()["status"] == "missing"
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    assert runtime.check_gemini()["status"] == "ok"


def test_check_database_unconfigured_vs_down(monkeypatch):
    for var in ("MATRIX_DATABASE_URL", "DATABASE_URL", "SUPABASE_DB_URL"):
        monkeypatch.delenv(var, raising=False)
    assert runtime.check_database()["status"] == "unconfigured"
    # Port 9 (discard) on localhost: nothing listens -> connect fails fast.
    monkeypatch.setenv("MATRIX_DATABASE_URL", "postgresql://u:p@127.0.0.1:9/matrix")
    assert runtime.check_database(timeout_s=0.2)["status"] == "down"


def test_health_report_degradation_rules(monkeypatch):
    monkeypatch.setattr(
        runtime, "check_redis", lambda url, timeout_s=0.5: {"status": "ok", "detail": None}
    )
    monkeypatch.setattr(runtime, "check_gemini", lambda: {"status": "ok", "detail": None})
    # An unconfigured DB must NOT degrade: persistence is optional + fallback-safe.
    monkeypatch.setattr(
        runtime, "check_database", lambda timeout_s=0.5: {"status": "unconfigured", "detail": "x"}
    )
    assert runtime.health_report("redis://x")["status"] == "ok"
    monkeypatch.setattr(
        runtime, "check_database", lambda timeout_s=0.5: {"status": "down", "detail": "x"}
    )
    assert runtime.health_report("redis://x")["status"] == "degraded"


# --- db persistence seam (feat/api-persistence, merge-order safe) ----------------------------


def test_db_seam_absent_module_is_noop():
    # On this branch matrix_api.db does not exist; the helpers must be safe no-ops.
    assert runtime.persist_run_started("x") is None or runtime._db is not None
    runtime.persist_dimension_results("run-x", [])
    runtime.persist_run_done("x", "run-x", {"total_ms": 1})
