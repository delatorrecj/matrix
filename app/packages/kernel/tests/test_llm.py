"""Tests for the resilient Gemini wrapper (matrix_kernel.llm) and its call sites.

All bare-mode: fake/stub clients only, no network, no API key. Covers retry
classification (429/5xx/transport vs. 4xx), exponential backoff + jitter, the
hard per-call timeout injection (HttpOptions.timeout, milliseconds), the typed
LLMUnavailable, and that synthesis + personas fall back EXPLICITLY on it.
"""
import logging
from types import SimpleNamespace

import httpx
import pytest
from google.genai import errors as genai_errors
from google.genai import types

from matrix_kernel import llm
from matrix_kernel import personas
from matrix_kernel.llm import LLMUnavailable, generate_content, is_retryable
from matrix_kernel.personas import ILOILO_MODE_SHARE, generate_persona_pool
from matrix_kernel.results import DimensionResult
from matrix_kernel.synthesis import synthesize

_KNOBS = ("MATRIX_LLM_TIMEOUT_S", "MATRIX_LLM_MAX_ATTEMPTS",
          "MATRIX_LLM_BACKOFF_BASE_S", "MATRIX_LLM_BACKOFF_CAP_S")


@pytest.fixture(autouse=True)
def _clean_llm_env(monkeypatch):
    """Hermetic defaults — a developer's shell env must not skew these tests."""
    for knob in _KNOBS:
        monkeypatch.delenv(knob, raising=False)


# --- fakes (no network) -------------------------------------------------------

class _FakeModels:
    """Scripted generate_content: each outcome is returned, or raised if it's an
    exception. The last outcome repeats forever (so 'always failing' is easy)."""

    def __init__(self, outcomes):
        self._outcomes = list(outcomes)
        self.calls = []

    def generate_content(self, *, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        outcome = (self._outcomes.pop(0) if len(self._outcomes) > 1
                   else self._outcomes[0])
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class FakeClient:
    def __init__(self, *outcomes):
        self.models = _FakeModels(outcomes)


class RecordingSleep:
    def __init__(self):
        self.delays = []

    def __call__(self, seconds):
        self.delays.append(seconds)


class UpperBoundRng:
    """uniform(lo, hi) -> hi, so full-jitter delays become deterministic."""

    def uniform(self, lo, hi):
        return hi


def _client_error(code, status="INVALID_ARGUMENT", message="bad request"):
    return genai_errors.ClientError(code, {"error": {"code": code, "message": message, "status": status}})


def _server_error(code=503, status="UNAVAILABLE", message="backend overloaded"):
    return genai_errors.ServerError(code, {"error": {"code": code, "message": message, "status": status}})


# --- retry / backoff / typed failure ------------------------------------------

def test_success_first_try_no_backoff():
    response = SimpleNamespace(text="ok")
    client = FakeClient(response)
    sleep = RecordingSleep()
    out = generate_content(client, model="gemini-3.1-pro", contents="hi", sleep=sleep)
    assert out is response
    assert len(client.models.calls) == 1
    assert sleep.delays == []


def test_transient_failure_then_success_backs_off_once():
    response = SimpleNamespace(text="recovered")
    client = FakeClient(_server_error(503), response)
    sleep = RecordingSleep()
    out = generate_content(client, model="gemini-3.1-pro", contents="hi",
                           sleep=sleep, rng=UpperBoundRng())
    assert out is response
    assert len(client.models.calls) == 2
    assert len(sleep.delays) == 1
    assert 0.0 < sleep.delays[0] <= llm.DEFAULT_BACKOFF_CAP_S


def test_retries_exhausted_raises_typed_exception():
    client = FakeClient(_client_error(429, status="RESOURCE_EXHAUSTED", message="rate limited"))
    sleep = RecordingSleep()
    with pytest.raises(LLMUnavailable) as excinfo:
        generate_content(client, model="gemini-3.1-flash-lite", contents="hi",
                         max_attempts=3, sleep=sleep)
    assert excinfo.value.attempts == 3
    assert isinstance(excinfo.value.last_error, genai_errors.ClientError)
    assert len(client.models.calls) == 3
    assert len(sleep.delays) == 2  # no sleep after the final attempt


def test_non_retryable_error_fails_immediately():
    client = FakeClient(_client_error(400))
    sleep = RecordingSleep()
    with pytest.raises(LLMUnavailable) as excinfo:
        generate_content(client, model="gemini-3.1-pro", contents="hi",
                         max_attempts=5, sleep=sleep)
    assert excinfo.value.attempts == 1
    assert len(client.models.calls) == 1  # never retried
    assert sleep.delays == []
    assert isinstance(excinfo.value.__cause__, genai_errors.ClientError)


def test_backoff_grows_exponentially_and_caps(monkeypatch):
    monkeypatch.setenv("MATRIX_LLM_BACKOFF_BASE_S", "1.0")
    monkeypatch.setenv("MATRIX_LLM_BACKOFF_CAP_S", "3.0")
    client = FakeClient(_server_error(500))
    sleep = RecordingSleep()
    with pytest.raises(LLMUnavailable):
        generate_content(client, model="m", contents="hi", max_attempts=4,
                         sleep=sleep, rng=UpperBoundRng())
    # full jitter upper bounds: min(cap, 1*2^(k-1)) -> 1, 2, then capped at 3
    assert sleep.delays == [1.0, 2.0, 3.0]


def test_negative_backoff_knob_never_sleeps_negative(monkeypatch):
    monkeypatch.setenv("MATRIX_LLM_BACKOFF_BASE_S", "-1.0")
    client = FakeClient(_server_error(503))
    sleep = RecordingSleep()
    with pytest.raises(LLMUnavailable):  # typed — not time.sleep's ValueError
        generate_content(client, model="m", contents="hi", max_attempts=3,
                         sleep=sleep)
    assert all(d >= 0.0 for d in sleep.delays)


def test_retry_classification():
    assert is_retryable(_client_error(429, status="RESOURCE_EXHAUSTED"))
    assert is_retryable(_server_error(500))
    assert is_retryable(_server_error(503))
    assert is_retryable(httpx.ConnectError("connection refused"))
    assert is_retryable(httpx.ReadTimeout("read timed out"))
    assert is_retryable(TimeoutError("socket timeout"))
    assert not is_retryable(_client_error(400))
    assert not is_retryable(_client_error(401, status="UNAUTHENTICATED"))
    assert not is_retryable(_client_error(404, status="NOT_FOUND"))
    assert not is_retryable(ValueError("schema mismatch"))


# --- hard per-call timeout ------------------------------------------------------

def test_timeout_injected_into_request_config():
    client = FakeClient(SimpleNamespace(text="ok"))
    generate_content(client, model="m", contents="hi", timeout_s=2.5)
    config = client.models.calls[0]["config"]
    assert config.http_options.timeout == 2500  # HttpOptions.timeout is in ms


def test_timeout_env_knob_and_default(monkeypatch):
    client = FakeClient(SimpleNamespace(text="ok"))
    generate_content(client, model="m", contents="hi")
    assert (client.models.calls[0]["config"].http_options.timeout
            == int(llm.DEFAULT_TIMEOUT_S * 1000))

    monkeypatch.setenv("MATRIX_LLM_TIMEOUT_S", "7")
    generate_content(client, model="m", contents="hi")
    assert client.models.calls[1]["config"].http_options.timeout == 7000


def test_timeout_preserves_caller_config_without_mutating_it():
    caller_config = types.GenerateContentConfig(temperature=0.2)
    client = FakeClient(SimpleNamespace(text="ok"))
    generate_content(client, model="m", contents="hi", config=caller_config,
                     timeout_s=1.0)
    sent = client.models.calls[0]["config"]
    assert sent.temperature == 0.2
    assert sent.http_options.timeout == 1000
    assert caller_config.http_options is None  # caller's object untouched


def test_max_attempts_env_knob(monkeypatch):
    monkeypatch.setenv("MATRIX_LLM_MAX_ATTEMPTS", "2")
    client = FakeClient(_server_error(503))
    sleep = RecordingSleep()
    with pytest.raises(LLMUnavailable) as excinfo:
        generate_content(client, model="m", contents="hi", sleep=sleep)
    assert excinfo.value.attempts == 2
    assert len(client.models.calls) == 2


def test_make_client_failure_is_typed(monkeypatch):
    def _boom():
        raise ValueError("Missing key inputs argument!")
    monkeypatch.setattr(llm.genai, "Client", _boom)
    with pytest.raises(LLMUnavailable):
        llm.make_client()


# --- call sites: fallbacks are explicit, logged paths ---------------------------

def _result():
    return DimensionResult(
        dimension="behavioral", metric="Δ trips/day", equation_id="BEH-1",
        value=450.0, range=(400.0, 500.0), unit="trips/day", confidence="M",
        input_dataset_ids=["OSM-ILO"],
    )


def test_synthesis_falls_back_on_llm_unavailable(monkeypatch, caplog):
    def _unavailable(*args, **kwargs):
        raise LLMUnavailable("Gemini (gemini-3.1-pro) unavailable after 3 attempt(s)",
                             attempts=3)
    monkeypatch.setattr("matrix_kernel.synthesis.generate_content", _unavailable)
    with caplog.at_level(logging.WARNING, logger="matrix_kernel.synthesis"):
        narrative, citations = synthesize([_result()], client=object())
    assert narrative == "Synthesis narrative generation failed. Please see the raw data."
    assert citations == []
    assert "placeholder narrative" in caplog.text


def test_synthesis_success_path_keeps_cited_numbers(monkeypatch):
    response = SimpleNamespace(text="Trips increased by 450.00 [BEH-1].")
    monkeypatch.setattr("matrix_kernel.synthesis.generate_content",
                        lambda *a, **k: response)
    narrative, citations = synthesize([_result()], client=object())
    assert "[BEH-1]" in narrative
    assert citations and citations[0]["equation_id"] == "BEH-1"


def test_synthesis_empty_response_text_is_blocked_not_crashed(monkeypatch):
    response = SimpleNamespace(text=None)
    monkeypatch.setattr("matrix_kernel.synthesis.generate_content",
                        lambda *a, **k: response)
    narrative, citations = synthesize([_result()], client=object())
    assert narrative  # the blocked-narrative message, never a crash on None
    assert citations == []


def test_personas_fall_back_to_static_pool_on_llm_unavailable(monkeypatch, caplog):
    def _no_client():
        raise LLMUnavailable("could not construct Gemini client", attempts=0)
    monkeypatch.setattr(llm, "make_client", _no_client)
    with caplog.at_level(logging.WARNING, logger="matrix_kernel.personas"):
        pool = generate_persona_pool(n=50, seed=7)
    assert "static seeded pool" in caplog.text
    assert len(pool) == 50
    assert all(p.mode in ILOILO_MODE_SHARE for p in pool)
    # deterministic: identical to the static seeded pool with the same seed
    assert pool == personas._static_seeded_pool(50, ILOILO_MODE_SHARE, 7)


def test_personas_use_gemini_payload_when_available(monkeypatch):
    parsed = SimpleNamespace(personas=[
        {"id": "p0000", "mode": "jeepney", "income_decile": 3, "trip_purpose": "work"},
        {"id": "p0001", "mode": "walk", "income_decile": 8, "trip_purpose": "school"},
    ])
    monkeypatch.setattr(llm, "make_client", lambda: object())
    monkeypatch.setattr(llm, "generate_content",
                        lambda *a, **k: SimpleNamespace(parsed=parsed, text=None))
    pool = generate_persona_pool(n=2, seed=1)
    assert [p.mode for p in pool] == ["jeepney", "walk"]
    assert pool[1].income_decile == 8


def test_personas_fall_back_on_unusable_response(monkeypatch, caplog):
    monkeypatch.setattr(llm, "make_client", lambda: object())
    monkeypatch.setattr(llm, "generate_content",
                        lambda *a, **k: SimpleNamespace(parsed=None, text="not json"))
    with caplog.at_level(logging.WARNING, logger="matrix_kernel.personas"):
        pool = generate_persona_pool(n=10, seed=3)
    assert "unusable Gemini response" in caplog.text
    assert pool == personas._static_seeded_pool(10, ILOILO_MODE_SHARE, 3)
