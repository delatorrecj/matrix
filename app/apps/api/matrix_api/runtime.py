"""Runtime hardening for the WS simulation pipeline (RFC matrix-rfc-001 §3, §6).

Everything heavier than a send_json lives here so main.py stays thin:

  StageTimer     -- per-stage wall-clock timings for the DONE event. The shape
                    {sumo_ms, modules_ms, gemini_ms, total_ms} is a frontend
                    contract -- do not rename keys.
  run_stage      -- asyncio.wait_for wrapper that converts a timeout into a typed
                    StageTimeout carrying the stage name (mapped to an ERROR event).
  SimGate / GATE -- loop-agnostic concurrency gate (default 2 concurrent sims).
                    Excess connections are QUEUED (FIFO) rather than rejected: the
                    client keeps its socket and receives {type:"QUEUED", position}.
  health checks  -- per-dependency status for GET /health; every check is bounded
                    by a short timeout so /health never blocks > ~2 s total.
  db seam        -- defensive wiring for matrix_api.db (feat/api-persistence):
                    persistence is best-effort and never raises into the WS
                    pipeline, regardless of merge order.

Env knobs (read at call time, so tests/ops can change them without a restart):

  MATRIX_STAGE_TIMEOUT_SUMO_S      default 120  -- trajectory acquisition (SUMO/Redis)
  MATRIX_STAGE_TIMEOUT_MODULES_S   default 60   -- five impact modules
  MATRIX_STAGE_TIMEOUT_GEMINI_S    default 30   -- Gemini synthesis narrative
  MATRIX_QUEUE_TIMEOUT_S           default 120  -- max wait for a sim slot (0 disables)
  MATRIX_MAX_CONCURRENT_SIMS       default 2    -- sim slots (MAX_CONCURRENT_SIMS also honored)

A timeout value of 0 (or negative) disables that timeout.
"""
from __future__ import annotations

import asyncio
import inspect
import os
import socket
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, suppress
from typing import Any, Awaitable, Iterator, TypeVar

from fastapi import WebSocket, WebSocketDisconnect

# --- guarded cross-PR imports -------------------------------------------------
# feat/llm-resilience introduces matrix_kernel.llm.LLMUnavailable. Until it merges,
# a placeholder keeps `except runtime.LLMUnavailable` valid; the WS handler also
# catches plain Exception for the synthesis stage, so nothing depends on the real
# class being present.
try:
    from matrix_kernel.llm import LLMUnavailable
except ImportError:  # pragma: no cover - depends on merge order

    class LLMUnavailable(Exception):
        """Placeholder until matrix_kernel.llm lands (feat/llm-resilience)."""


# feat/api-persistence introduces matrix_api.db (fallback-safe, never-raising).
# Wire it defensively so the two PRs compose regardless of merge order.
try:
    from . import db as _db  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - depends on merge order
    _db = None

T = TypeVar("T")

# --- stage timings (DONE event) -----------------------------------------------


class StageTimer:
    """Collects per-stage wall-clock timings (ms) for the DONE event.

    Stage names map to timing keys as f"{name}_ms"; timings() adds total_ms
    measured from construction. The DONE shape {sumo_ms, modules_ms, gemini_ms,
    total_ms} is consumed by the frontend -- keep the keys exact.
    """

    def __init__(self) -> None:
        self._t0 = time.perf_counter()
        self._stages: dict[str, int] = {}

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        t = time.perf_counter()
        try:
            yield
        finally:
            self._stages[f"{name}_ms"] = round((time.perf_counter() - t) * 1000)

    def timings(self) -> dict[str, int]:
        out = dict(self._stages)
        out["total_ms"] = round((time.perf_counter() - self._t0) * 1000)
        return out


# --- per-stage timeouts ---------------------------------------------------------

_TIMEOUT_DEFAULTS_S: dict[str, float] = {"sumo": 120.0, "modules": 60.0, "gemini": 30.0}
_QUEUE_TIMEOUT_DEFAULT_S = 120.0


class StageTimeout(Exception):
    """A pipeline stage exceeded its budget. Maps to ERROR {stage, recoverable:true}."""

    def __init__(self, stage: str, timeout_s: float) -> None:
        self.stage = stage
        self.timeout_s = timeout_s
        super().__init__(f"stage {stage!r} exceeded its {timeout_s}s budget")


def stage_timeout_s(stage: str) -> float:
    """Budget for `stage` in seconds; env-overridable (MATRIX_STAGE_TIMEOUT_<STAGE>_S)."""
    default = _TIMEOUT_DEFAULTS_S[stage]
    raw = os.environ.get(f"MATRIX_STAGE_TIMEOUT_{stage.upper()}_S")
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def queue_timeout_s() -> float:
    raw = os.environ.get("MATRIX_QUEUE_TIMEOUT_S")
    if raw is None:
        return _QUEUE_TIMEOUT_DEFAULT_S
    try:
        return float(raw)
    except ValueError:
        return _QUEUE_TIMEOUT_DEFAULT_S


async def run_stage(awaitable: Awaitable[T], *, stage: str, timeout_s: float) -> T:
    """Await a stage with a budget; on timeout raise a typed StageTimeout.

    asyncio.wait_for cancels the wrapped task on timeout. Work already running in
    a thread (asyncio.to_thread) cannot be killed, but the pipeline stops awaiting
    it, the slot is released by the handler's finally, and the client gets a typed
    ERROR instead of a silent hang. timeout_s <= 0 disables the budget.
    """
    if timeout_s <= 0:
        return await awaitable
    try:
        return await asyncio.wait_for(awaitable, timeout=timeout_s)
    except TimeoutError as exc:  # asyncio.TimeoutError is TimeoutError on 3.12
        raise StageTimeout(stage, timeout_s) from exc


# --- concurrency gate -----------------------------------------------------------


class SimGate:
    """Loop-agnostic concurrency gate for /simulate (RFC §6: multi-user -> queue).

    Built on threading.Lock + a FIFO ticket queue instead of asyncio.Semaphore so
    it works across event loops (uvicorn's single loop in prod, one loop per
    TestClient portal in tests) and so an abandoned waiter can never leak a slot:
    queued waiters poll for the head ticket and a cancelled waiter just abandons
    its ticket without ever holding a slot.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active = 0
        self._queue: list[int] = []
        self._next_ticket = 0

    @staticmethod
    def limit() -> int:
        """Slots, read from env each call (MATRIX_MAX_CONCURRENT_SIMS, default 2)."""
        raw = os.environ.get("MATRIX_MAX_CONCURRENT_SIMS") or os.environ.get(
            "MAX_CONCURRENT_SIMS"
        )
        if raw is None:
            return 2
        try:
            return max(1, int(raw))
        except ValueError:
            return 2

    def admit(self) -> tuple[bool, int, int]:
        """Try to take a slot now. Returns (admitted, ticket, queue_position).

        Admitted callers hold a slot (ticket -1, position 0) and must release().
        Queued callers must wait_for_slot() with their ticket, or abandon() it.
        """
        with self._lock:
            if self._active < self.limit() and not self._queue:
                self._active += 1
                return True, -1, 0
            ticket = self._next_ticket
            self._next_ticket += 1
            self._queue.append(ticket)
            return False, ticket, len(self._queue)

    def poll(self, ticket: int) -> bool:
        """Take a slot iff `ticket` is at the head of the queue and a slot is free."""
        with self._lock:
            if self._queue and self._queue[0] == ticket and self._active < self.limit():
                self._queue.pop(0)
                self._active += 1
                return True
            return False

    def abandon(self, ticket: int) -> None:
        """Drop a waiter that gave up (disconnect / queue timeout). Idempotent."""
        with self._lock:
            with suppress(ValueError):
                self._queue.remove(ticket)

    def release(self) -> None:
        """Give back a held slot. Idempotence guard: never goes below zero."""
        with self._lock:
            self._active = max(0, self._active - 1)

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return {"active": self._active, "queued": len(self._queue), "limit": self.limit()}


GATE = SimGate()


async def wait_for_slot(
    gate: SimGate, ticket: int, *, timeout_s: float, poll_s: float = 0.05
) -> None:
    """Wait (FIFO) until `ticket` gets a slot. Cancellable without leaking a slot:
    cancellation is only ever delivered at the `sleep` (before another poll), so a
    cancelled waiter never incremented `active`, and the caller abandons its ticket
    in its finally block. timeout_s <= 0 waits indefinitely."""
    deadline = None if timeout_s <= 0 else time.monotonic() + timeout_s
    while not gate.poll(ticket):
        if deadline is not None and time.monotonic() >= deadline:
            raise StageTimeout("queue", timeout_s)
        await asyncio.sleep(poll_s)


async def wait_for_slot_or_disconnect(
    ws: WebSocket, gate: SimGate, ticket: int, *, timeout_s: float
) -> None:
    """wait_for_slot, but watching the socket: a client that disconnects while
    QUEUED must abandon immediately -- not silently win a slot later and burn a
    whole SUMO stage against a dead socket, delaying everyone behind it.

    Returns when the slot is HELD (caller must release). Raises WebSocketDisconnect
    if the client went away, StageTimeout("queue") on queue timeout. On every
    exception path the slot is provably not held: if the slot race was won in the
    same tick the disconnect arrived, it is released here before raising.
    """
    slot = asyncio.ensure_future(wait_for_slot(gate, ticket, timeout_s=timeout_s))
    watch = asyncio.ensure_future(ws.receive())
    try:
        await asyncio.wait({slot, watch}, return_when=asyncio.FIRST_COMPLETED)
        if watch.done() and not watch.cancelled():
            msg = watch.result()
            if isinstance(msg, dict) and msg.get("type") == "websocket.disconnect":
                raise WebSocketDisconnect(int(msg.get("code") or 1000))
            # This protocol has no client->server frames; ignore an unexpected
            # frame and keep waiting (disconnect detection ends here -- rare).
        await slot  # slot held on return; StageTimeout("queue") on timeout
    except BaseException:
        # The slot task can have won concurrently (e.g. disconnect + slot in the
        # same event-loop tick). The caller only releases on a normal return, so
        # give a won slot back before raising -- never leak.
        if slot.done() and not slot.cancelled() and slot.exception() is None:
            gate.release()
        raise
    finally:
        for task in (slot, watch):
            if not task.done():
                task.cancel()
        for task in (slot, watch):  # reap quietly; outcomes were already handled
            with suppress(BaseException):
                await task


# --- typed WS events ------------------------------------------------------------


def error_event(scenario_id: str, stage: str, message: str, recoverable: bool) -> dict:
    """The typed ERROR event (RFC §3). The shape is a frontend contract -- keep exact."""
    return {
        "type": "ERROR",
        "scenario_id": scenario_id,
        "stage": stage,
        "message": message,
        "recoverable": recoverable,
    }


# --- dependency-aware health (GET /health) ---------------------------------------


def check_redis(url: str, timeout_s: float = 0.5) -> dict[str, Any]:
    """Ping Redis with a short socket timeout. Never raises, never blocks > ~1 s."""
    try:
        import redis  # lazy: optional in bare/test environments
    except ImportError:
        return {"status": "down", "detail": "redis client not installed"}
    kwargs: dict[str, Any] = {
        "socket_connect_timeout": timeout_s,
        "socket_timeout": timeout_s,
    }
    # redis-py >= 6 retries failed connections 3x with backoff by default, which
    # multiplies the budget (~1.8 s observed with the server down). One attempt
    # is the right semantic for a health probe.
    try:
        from redis.backoff import NoBackoff
        from redis.retry import Retry

        kwargs["retry"] = Retry(NoBackoff(), 0)
    except Exception:  # pragma: no cover - older redis-py without the retry API
        pass
    client = None
    try:
        client = redis.from_url(url, **kwargs)
        ok = bool(client.ping())
        return {"status": "ok" if ok else "down", "detail": None if ok else "ping failed"}
    except Exception as exc:
        return {"status": "down", "detail": str(exc)[:200]}
    finally:
        if client is not None:
            with suppress(Exception):
                client.close()


def check_database(timeout_s: float = 0.5) -> dict[str, Any]:
    """Cheap reachability: TCP connect to the configured DB host (no driver needed).

    "unconfigured" is not a failure -- persistence (matrix_api.db) is fallback-safe
    and optional, so only a configured-but-unreachable DB degrades /health.
    """
    url = (
        os.environ.get("MATRIX_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or os.environ.get("SUPABASE_DB_URL")
    )
    if not url:
        return {"status": "unconfigured", "detail": "no MATRIX_DATABASE_URL / DATABASE_URL set"}
    try:
        parsed = urllib.parse.urlsplit(url)
        host, port = parsed.hostname, parsed.port or 5432
    except ValueError as exc:
        return {"status": "down", "detail": f"unparseable database URL: {exc}"}
    if not host:
        return {"status": "down", "detail": "database URL has no host"}
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return {"status": "ok", "detail": None}
    except OSError as exc:
        return {"status": "down", "detail": str(exc)[:200]}


def check_gemini() -> dict[str, Any]:
    """Key presence only (no live call -- /health must stay fast and budget-free).
    google-genai reads GEMINI_API_KEY / GOOGLE_API_KEY."""
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return {"status": "ok", "detail": None}
    return {"status": "missing", "detail": "GEMINI_API_KEY / GOOGLE_API_KEY not set"}


def health_report(redis_url: str) -> dict[str, Any]:
    """Per-dependency status + overall ok|degraded. Bounded < ~2 s total.

    The two network probes run in parallel so the bound is max(check budgets),
    not their sum (redis worst case is ~2x timeout_s: localhost resolves to
    ::1 then 127.0.0.1).
    """
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_redis = pool.submit(check_redis, redis_url)
        f_db = pool.submit(check_database)
        deps = {
            "redis": f_redis.result(),
            "database": f_db.result(),
            "gemini": check_gemini(),
        }
    degraded = (
        deps["redis"]["status"] != "ok"
        or deps["gemini"]["status"] != "ok"
        or deps["database"]["status"] == "down"
    )
    return {"status": "degraded" if degraded else "ok", "dependencies": deps}


# --- db persistence seam (feat/api-persistence) -----------------------------------
# matrix_api.db's functions are documented fallback-safe/never-raising, but the WS
# pipeline must survive any merge-order or signature skew, so every call here is
# additionally guarded. All helpers are no-ops when the module isn't present.


def persist_run_started(scenario_id: str) -> Any:
    if _db is None:
        return None
    try:
        return _db.save_run(scenario_id, status="running")
    except Exception:
        return None


def persist_dimension_results(run_id: Any, results: list) -> None:
    if _db is None:
        return
    with suppress(Exception):
        _db.save_dimension_results(run_id, results)


def persist_run_done(scenario_id: str, run_id: Any, timings: dict[str, int]) -> None:
    if _db is None:
        return
    kwargs: dict[str, Any] = {
        "run_id": run_id,
        "status": "done",
        "duration_ms": timings.get("total_ms"),
    }
    # Pass timings only if the (possibly newer) signature accepts it.
    with suppress(TypeError, ValueError):
        params = inspect.signature(_db.save_run).parameters
        if "timings" in params or any(
            p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values()
        ):
            kwargs["timings"] = timings
    try:
        _db.save_run(scenario_id, **kwargs)
    except TypeError:
        kwargs.pop("timings", None)
        with suppress(Exception):
            _db.save_run(scenario_id, **kwargs)
    except Exception:
        pass
