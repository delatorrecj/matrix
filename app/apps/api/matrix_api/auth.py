"""API-key auth + per-key rate limiting + CORS allowlist for the MATRIX gateway.

Defensive hardening: once deployed, an open gateway means anyone can trigger
unlimited Gemini-billed simulations. Everything here is env-gated and OFF by
default so local dev and the hackathon demo keep working with zero config.

Env vars (all optional):
  MATRIX_AUTH_ENABLED        "true" to require `Authorization: Bearer <key>`
                             on every HTTP route except EXEMPT_PATHS, and a key
                             on the /simulate WebSocket. Default: false.
  MATRIX_API_KEYS            comma-separated list of accepted keys.
  MATRIX_RATE_LIMIT_ENABLED  "true"/"false". Default: follows MATRIX_AUTH_ENABLED
                             (auth on -> limiting on, keyed by API key; auth off
                             but limiting on -> keyed by client IP).
  MATRIX_RATE_LIMIT_PER_MIN  requests per rolling 60s window per key/IP.
                             Default: 60. Values <= 0 disable limiting.
  MATRIX_ALLOWED_ORIGINS     comma-separated CORS origins.
                             Default: http://localhost:3000, http://127.0.0.1:3000.

Env is read per-request (cheap string ops) so tests and ops can flip flags
without rebuilding the app; only the CORS allowlist is bound at startup, because
Starlette's CORSMiddleware takes a static list.

WS rejection follows Starlette 1.x semantics: `close()` before `accept()` sends
`websocket.close` while the handshake is still pending, which the server turns
into a denial (uvicorn: HTTP 403; TestClient: WebSocketDisconnect with the code).
Code 1008 = policy violation (bad/missing key), 1013 = try again later (rate limit).
"""
from __future__ import annotations

import math
import os
import secrets
import threading
import time
from collections import deque

from fastapi import HTTPException, status
from starlette.requests import HTTPConnection
from starlette.websockets import WebSocket

# Routes that stay open even with auth enabled: the ops probe (/health), the
# public-trust validation page (/validation), and the interactive docs.
EXEMPT_PATHS = frozenset(
    {"/health", "/validation", "/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"}
)

DEFAULT_ALLOWED_ORIGINS = ("http://localhost:3000", "http://127.0.0.1:3000")
DEFAULT_RATE_LIMIT_PER_MIN = 60
RATE_WINDOW_SECONDS = 60.0

_TRUTHY = {"1", "true", "yes", "on"}


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUTHY


def auth_enabled() -> bool:
    return _env_flag("MATRIX_AUTH_ENABLED", default=False)


def api_keys() -> tuple[str, ...]:
    raw = os.environ.get("MATRIX_API_KEYS", "")
    return tuple(k.strip() for k in raw.split(",") if k.strip())


def rate_limit_enabled() -> bool:
    raw = os.environ.get("MATRIX_RATE_LIMIT_ENABLED")
    if raw is None:
        return auth_enabled()  # locking the door turns the meter on by default
    return raw.strip().lower() in _TRUTHY


def rate_limit_per_min() -> int:
    raw = os.environ.get("MATRIX_RATE_LIMIT_PER_MIN")
    if raw is None:
        return DEFAULT_RATE_LIMIT_PER_MIN
    try:
        return int(raw.strip())
    except ValueError:
        return DEFAULT_RATE_LIMIT_PER_MIN


def allowed_origins() -> list[str]:
    raw = os.environ.get("MATRIX_ALLOWED_ORIGINS")
    if raw is None:
        return list(DEFAULT_ALLOWED_ORIGINS)
    return [o.strip() for o in raw.split(",") if o.strip()]


def _bearer_key(header_value: str | None) -> str | None:
    """Extract the key from an `Authorization: Bearer <key>` header, else None."""
    if not header_value:
        return None
    scheme, _, token = header_value.partition(" ")
    if scheme.lower() != "bearer":
        return None
    token = token.strip()
    return token or None


def _key_is_valid(candidate: str) -> bool:
    # compare_digest against every configured key (no early exit) to avoid
    # leaking which key matched through timing. Compare as UTF-8 bytes:
    # compare_digest raises TypeError on non-ASCII *str* input, and the
    # candidate is attacker-controlled (header/query param) -- a stray "é"
    # must be a clean 401/1008, never a 500.
    encoded = candidate.encode("utf-8")
    matched = False
    for key in api_keys():
        matched |= secrets.compare_digest(encoded, key.encode("utf-8"))
    return matched


class SlidingWindowLimiter:
    """In-memory per-key sliding window. No external deps, process-local by design
    (one uvicorn process for the pilot; swap for Redis if the API ever scales out)."""

    def __init__(self, window_seconds: float = RATE_WINDOW_SECONDS, max_buckets: int = 4096) -> None:
        self._window = window_seconds
        self._max_buckets = max_buckets
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int) -> int | None:
        """Record one hit. Returns None if allowed, else whole seconds to wait (Retry-After)."""
        if limit <= 0:
            return None
        now = time.monotonic()
        with self._lock:
            bucket = self._hits.setdefault(key, deque())
            while bucket and now - bucket[0] >= self._window:
                bucket.popleft()
            if len(bucket) >= limit:
                return max(1, math.ceil(self._window - (now - bucket[0])))
            bucket.append(now)
            if len(self._hits) > self._max_buckets:
                self._sweep(now)
            return None

    def _sweep(self, now: float) -> None:
        stale = [k for k, b in self._hits.items() if not b or now - b[-1] >= self._window]
        for k in stale:
            del self._hits[k]
        # Hard memory bound: under a flood of *distinct fresh* keys (only possible
        # keyed-by-IP) nothing is stale, so evict oldest-inserted FIFO. Forgetting a
        # bucket can only under-throttle that one key; unbounded growth is worse.
        while len(self._hits) > self._max_buckets:
            del self._hits[next(iter(self._hits))]

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


_limiter = SlidingWindowLimiter()


def reset_rate_limiter() -> None:
    """Test hook: clear all rate-limit buckets."""
    _limiter.reset()


def _client_ip(conn: HTTPConnection) -> str:
    return conn.client.host if conn.client else "unknown"


def require_api_key(conn: HTTPConnection) -> None:
    """Global FastAPI dependency: bearer auth + rate limit for every HTTP route.

    Registered app-wide via `FastAPI(dependencies=[...])`, so it also gets attached
    to WebSocket routes -- those no-op here and are guarded by `authorize_websocket`
    at the top of the WS endpoint instead (an HTTPException is meaningless mid-handshake).
    """
    if conn.scope["type"] != "http":
        return
    if conn.scope["path"] in EXEMPT_PATHS:
        return

    caller: str | None = None
    if auth_enabled():
        key = _bearer_key(conn.headers.get("Authorization"))
        if key is None or not _key_is_valid(key):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="missing or invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        caller = key

    if rate_limit_enabled():
        ident = caller if caller is not None else _client_ip(conn)
        retry_after = _limiter.hit(ident, rate_limit_per_min())
        if retry_after is not None:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="rate limit exceeded",
                headers={"Retry-After": str(retry_after)},
            )


async def authorize_websocket(ws: WebSocket) -> bool:
    """Guard for the top of a WS endpoint, before `accept()`.

    Accepts the key as `?api_key=<key>` (browser WebSocket() can't set headers)
    or `Authorization: Bearer <key>`. Returns True to proceed; on failure closes
    the pending handshake (1008 bad key, 1013 rate-limited) and returns False.
    """
    caller: str
    if auth_enabled():
        key = ws.query_params.get("api_key") or _bearer_key(ws.headers.get("Authorization"))
        if key is None or not _key_is_valid(key):
            await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="missing or invalid API key")
            return False
        caller = key
    else:
        caller = _client_ip(ws)

    if rate_limit_enabled():
        retry_after = _limiter.hit(caller, rate_limit_per_min())
        if retry_after is not None:
            await ws.close(code=status.WS_1013_TRY_AGAIN_LATER, reason="rate limit exceeded")
            return False
    return True
