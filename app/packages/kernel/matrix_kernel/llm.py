"""Resilient wrapper for the kernel's Azure OpenAI calls (RFC matrix-rfc-001; 90s budget).

Every `openai` API call in the kernel goes through here so a
timeout or 429 can never hang a simulation or fail silently:

- **Bounded retries** with exponential backoff + full jitter, ONLY on retryable
  failures: HTTP 429, 5xx, and transport-level timeouts/connection drops.
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
"""
from __future__ import annotations

import logging
import os
import random
import time
from typing import Any, Callable

import openai

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_S = 20.0
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_BACKOFF_BASE_S = 0.5
DEFAULT_BACKOFF_CAP_S = 8.0

class LLMUnavailable(RuntimeError):
    """Azure OpenAI could not produce a response — retries exhausted, a non-retryable
    error, or the client could not even be constructed (e.g. missing API key).
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
    """True only for failures that can plausibly heal on retry: 429, 5xx, and timeouts."""
    if isinstance(exc, (openai.RateLimitError, openai.InternalServerError, openai.APITimeoutError, openai.APIConnectionError)):
        return True
    return False

def _backoff_delay(attempt: int, base_s: float, cap_s: float,
                   rng: random.Random) -> float:
    """Full-jitter exponential backoff: uniform(0, min(cap, base * 2**(attempt-1)))."""
    return max(0.0, rng.uniform(0.0, min(cap_s, base_s * (2 ** (attempt - 1)))))

def make_client(timeout_s: float | None = None) -> openai.OpenAI:
    """Construct the OpenAI client for the Azure AI Foundry OpenAI-COMPATIBLE v1 endpoint,
    converting construction failure into the typed `LLMUnavailable` so fallbacks engage.

    Foundry exposes `https://<resource>.services.ai.azure.com/openai/v1`, which is driven by
    the *standard* `openai.OpenAI(base_url=…, api_key=…)` client (the `model` arg is the
    deployment name) — NOT `openai.AzureOpenAI`, whose classic
    `/openai/deployments/{name}/…?api-version=…` routing 404s against this surface.
    """
    if timeout_s is None:
        timeout_s = _env_float("MATRIX_LLM_TIMEOUT_S", DEFAULT_TIMEOUT_S)
    try:
        api_key = os.environ.get("AZURE_OPENAI_API_KEY")
        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")

        if not api_key or not endpoint:
            raise ValueError("AZURE_OPENAI_API_KEY or AZURE_OPENAI_ENDPOINT missing")

        # Accept either the bare resource URL or the full v1 URL and normalize to the
        # OpenAI-compatible base: https://<resource>.services.ai.azure.com/openai/v1
        base = endpoint.rstrip("/")
        if base.endswith("/openai/v1"):
            base_url = base
        elif base.endswith("/openai"):
            base_url = base + "/v1"
        else:
            base_url = base + "/openai/v1"

        return openai.OpenAI(base_url=base_url, api_key=api_key, timeout=timeout_s)
    except Exception as exc:
        raise LLMUnavailable(
            f"could not construct Azure OpenAI (v1) client: {exc}",
            attempts=0, last_error=exc,
        ) from exc

def generate_chat_completion(
    client: openai.OpenAI,
    *,
    model: str,
    messages: list[dict[str, Any]],
    response_format: Any | None = None,
    temperature: float | None = None,
    max_attempts: int | None = None,
    sleep: Callable[[float], None] = time.sleep,
    rng: random.Random | None = None,
) -> Any:
    """`client.chat.completions.create` with bounded retries.
    """
    if max_attempts is None:
        max_attempts = _env_int("MATRIX_LLM_MAX_ATTEMPTS", DEFAULT_MAX_ATTEMPTS)
    max_attempts = max(1, max_attempts)
    base_s = _env_float("MATRIX_LLM_BACKOFF_BASE_S", DEFAULT_BACKOFF_BASE_S)
    cap_s = _env_float("MATRIX_LLM_BACKOFF_CAP_S", DEFAULT_BACKOFF_CAP_S)
    if rng is None:
        rng = random.Random()

    last_error: BaseException | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            kwargs = {
                "model": model,
                "messages": messages,
            }
            if temperature is not None:
                kwargs["temperature"] = temperature

            if response_format is not None:
                if isinstance(response_format, type):
                    kwargs["response_format"] = response_format
                    return client.beta.chat.completions.parse(**kwargs)
                else:
                    kwargs["response_format"] = response_format
            return client.chat.completions.create(**kwargs)
        except Exception as exc:
            last_error = exc
            if not is_retryable(exc):
                raise LLMUnavailable(
                    f"non-retryable error from Azure OpenAI ({model}): {exc}",
                    attempts=attempt, last_error=exc,
                ) from exc
            if attempt == max_attempts:
                break
            delay = _backoff_delay(attempt, base_s, cap_s, rng)
            logger.warning(
                "llm: retryable failure from Azure OpenAI (%s), attempt %d/%d: %s — "
                "retrying in %.2fs", model, attempt, max_attempts, exc, delay)
            sleep(delay)

    raise LLMUnavailable(
        f"Azure OpenAI ({model}) unavailable after {max_attempts} attempt(s): {last_error}",
        attempts=max_attempts, last_error=last_error,
    ) from last_error
