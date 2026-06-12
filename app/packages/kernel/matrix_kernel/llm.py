"""Resilient wrapper for the kernel's Gemini calls (RFC matrix-rfc-001; 90s budget).

Every `google-genai` `generate_content` call in the kernel goes through here so a
Gemini timeout or 429 can never hang a simulation or fail silently:

- **Hard per-call timeout** via `types.HttpOptions(timeout=<ms>)` (the SDK's
  per-request knob — milliseconds), injected into the request config.
- **Bounded retries** with exponential backoff + full jitter, ONLY on retryable
  failures: HTTP 429, 5xx (`google.genai.errors.ServerError` / `ClientError.code`),
  and transport-level timeouts/connection drops (httpx ships with google-genai).
- **Typed failure** — `LLMUnavailable` — so callers' fallbacks (synthesis
  placeholder, static persona pool) are explicit, logged code paths instead of
  bare `except Exception`.

Glass box (PRD-F14) is untouched: this module changes *availability* handling
only. The LLM still narrates and cites — it never originates a number.

Env knobs (read per call so ops/tests can override without re-import):
  MATRIX_LLM_TIMEOUT_S        hard per-call timeout, seconds        (default 20)
  MATRIX_LLM_MAX_ATTEMPTS     total attempts incl. the first        (default 3)
  MATRIX_LLM_BACKOFF_BASE_S   backoff base, seconds                 (default 0.5)
  MATRIX_LLM_BACKOFF_CAP_S    backoff ceiling per wait, seconds     (default 8.0)

Worst case is bounded at max_attempts * timeout + sum(backoff) — tune the knobs
per call site (synthesis sits on the 90s hot path; the persona pool is pre-warmed
nightly, so it can afford a longer timeout).
"""
from __future__ import annotations

import logging
import os
import random
import time
from typing import Any, Callable

import httpx  # transport used by google-genai; needed only to classify errors
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_S = 20.0
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_BACKOFF_BASE_S = 0.5
DEFAULT_BACKOFF_CAP_S = 8.0

# Transport-level failures that are transient by nature (connection drops,
# read/connect timeouts). Deliberately NOT all of httpx.RequestError — a bad URL
# or unsupported protocol will never heal on retry.
_RETRYABLE_TRANSPORT_ERRORS = (
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.ReadError,
    httpx.WriteError,
    httpx.RemoteProtocolError,
    ConnectionError,   # stdlib socket-level
    TimeoutError,      # stdlib
)


class LLMUnavailable(RuntimeError):
    """Gemini could not produce a response — retries exhausted, a non-retryable
    error, or the client could not even be constructed (e.g. missing API key).

    Callers catch THIS (never bare Exception) and run their documented fallback.
    """

    def __init__(self, message: str, *, attempts: int = 1,
                 last_error: BaseException | None = None) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.last_error = last_error


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("llm: ignoring invalid %s=%r — using default %s", name, raw, default)
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("llm: ignoring invalid %s=%r — using default %s", name, raw, default)
        return default


def is_retryable(exc: BaseException) -> bool:
    """True only for failures that can plausibly heal on retry: 429, 5xx, and
    transport timeouts/drops. Auth/4xx/schema errors fail fast instead."""
    if isinstance(exc, genai_errors.APIError):
        code = exc.code
        return code == 429 or (isinstance(code, int) and 500 <= code <= 599)
    return isinstance(exc, _RETRYABLE_TRANSPORT_ERRORS)


def _backoff_delay(attempt: int, base_s: float, cap_s: float,
                   rng: random.Random) -> float:
    """Full-jitter exponential backoff: uniform(0, min(cap, base * 2**(attempt-1))).
    Clamped to >= 0 so a misconfigured (negative) knob can never feed
    time.sleep() a negative value and crash the retry loop untyped."""
    return max(0.0, rng.uniform(0.0, min(cap_s, base_s * (2 ** (attempt - 1)))))


def _with_timeout(config: types.GenerateContentConfig | None,
                  timeout_s: float) -> types.GenerateContentConfig:
    """Return a copy of `config` with the hard per-request timeout injected
    (HttpOptions.timeout is in MILLISECONDS). Never mutates the caller's config."""
    timeout_ms = max(1, int(timeout_s * 1000))
    if config is None:
        return types.GenerateContentConfig(
            http_options=types.HttpOptions(timeout=timeout_ms))
    if config.http_options is not None:
        http_options = config.http_options.model_copy(update={"timeout": timeout_ms})
    else:
        http_options = types.HttpOptions(timeout=timeout_ms)
    return config.model_copy(update={"http_options": http_options})


def make_client() -> genai.Client:
    """Construct a `genai.Client`, converting construction failure (most commonly
    a missing API key) into the typed `LLMUnavailable` so fallbacks engage."""
    try:
        return genai.Client()
    except Exception as exc:
        raise LLMUnavailable(
            f"could not construct Gemini client: {exc}",
            attempts=0, last_error=exc,
        ) from exc


def generate_content(
    client: genai.Client,
    *,
    model: str,
    contents: Any,
    config: types.GenerateContentConfig | None = None,
    timeout_s: float | None = None,
    max_attempts: int | None = None,
    sleep: Callable[[float], None] = time.sleep,
    rng: random.Random | None = None,
) -> types.GenerateContentResponse:
    """`client.models.generate_content` with a hard timeout and bounded retries.

    Raises `LLMUnavailable` (and only that) on failure: immediately for
    non-retryable errors, after `max_attempts` for retryable ones. `sleep`/`rng`
    are injectable for tests — production callers leave the defaults.
    """
    if timeout_s is None:
        timeout_s = _env_float("MATRIX_LLM_TIMEOUT_S", DEFAULT_TIMEOUT_S)
    if max_attempts is None:
        max_attempts = _env_int("MATRIX_LLM_MAX_ATTEMPTS", DEFAULT_MAX_ATTEMPTS)
    max_attempts = max(1, max_attempts)
    base_s = _env_float("MATRIX_LLM_BACKOFF_BASE_S", DEFAULT_BACKOFF_BASE_S)
    cap_s = _env_float("MATRIX_LLM_BACKOFF_CAP_S", DEFAULT_BACKOFF_CAP_S)
    if rng is None:
        rng = random.Random()
    config = _with_timeout(config, timeout_s)

    last_error: BaseException | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return client.models.generate_content(
                model=model, contents=contents, config=config)
        except Exception as exc:
            last_error = exc
            if not is_retryable(exc):
                raise LLMUnavailable(
                    f"non-retryable error from Gemini ({model}): {exc}",
                    attempts=attempt, last_error=exc,
                ) from exc
            if attempt == max_attempts:
                break
            delay = _backoff_delay(attempt, base_s, cap_s, rng)
            logger.warning(
                "llm: retryable failure from Gemini (%s), attempt %d/%d: %s — "
                "retrying in %.2fs", model, attempt, max_attempts, exc, delay)
            sleep(delay)

    raise LLMUnavailable(
        f"Gemini ({model}) unavailable after {max_attempts} attempt(s): {last_error}",
        attempts=max_attempts, last_error=last_error,
    ) from last_error
