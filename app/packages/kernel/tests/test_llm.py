"""Tests for the resilient Azure OpenAI wrapper (matrix_kernel.llm) and its call sites.

All bare-mode: fake/stub clients only, no network, no API key. Covers retry
classification (429/5xx/transport vs. 4xx), exponential backoff + jitter, the
hard per-call timeout injection (HttpOptions.timeout, milliseconds), the typed
LLMUnavailable, and that synthesis + personas fall back EXPLICITLY on it.
"""
import logging
from types import SimpleNamespace

import httpx
import pytest
import openai

from matrix_kernel import llm
from matrix_kernel import personas
from matrix_kernel.llm import LLMUnavailable, generate_chat_completion, is_retryable
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

class _FakeMessage:
    def __init__(self, content="", parsed=None):
        self.content = content
        self.parsed = parsed

class _FakeChoice:
    def __init__(self, content="", parsed=None):
        self.message = _FakeMessage(content, parsed)

class _FakeResponse:
    def __init__(self, content="", parsed=None):
        self.choices = [_FakeChoice(content, parsed)]

class _FakeCompletions:
    def __init__(self, outcomes, calls):
        self._outcomes = outcomes
        self.calls = calls

    def create(self, **kwargs):
        self.calls.append(kwargs)
        outcome = (self._outcomes.pop(0) if len(self._outcomes) > 1 else self._outcomes[0])
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome
        
    def parse(self, **kwargs):
        return self.create(**kwargs)

class _FakeChat:
    def __init__(self, outcomes, calls):
        self.completions = _FakeCompletions(outcomes, calls)

class _FakeBeta:
    def __init__(self, outcomes, calls):
        self.chat = _FakeChat(outcomes, calls)

class FakeClient:
    def __init__(self, *outcomes):
        self.calls = []
        self._outcomes = list(outcomes)
        self.chat = _FakeChat(self._outcomes, self.calls)
        self.beta = _FakeBeta(self._outcomes, self.calls)


class RecordingSleep:
    def __init__(self):
        self.delays = []

    def __call__(self, seconds):
        self.delays.append(seconds)


class UpperBoundRng:
    """uniform(lo, hi) -> hi, so full-jitter delays become deterministic."""

    def uniform(self, lo, hi):
        return hi


def _mock_response(code):
    req = httpx.Request("POST", "http://test")
    return httpx.Response(code, request=req)

def _client_error(code, message="bad request"):
    resp = _mock_response(code)
    if code == 429:
        return openai.RateLimitError(message, response=resp, body={})
    elif code == 404:
        return openai.NotFoundError(message, response=resp, body={})
    elif code == 401:
        return openai.AuthenticationError(message, response=resp, body={})
    return openai.BadRequestError(message, response=resp, body={})

def _server_error(code=503, message="backend overloaded"):
    if code == 503:
        return openai.APIConnectionError(request=httpx.Request("POST", "http://test"))
    return openai.InternalServerError(message, response=_mock_response(code), body={})


# --- retry / backoff / typed failure ------------------------------------------

def test_success_first_try_no_backoff():
    response = _FakeResponse("ok")
    client = FakeClient(response)
    sleep = RecordingSleep()
    out = generate_chat_completion(client, model="gpt-5.4", messages=[{"role": "user", "content": "hi"}], sleep=sleep)
    assert out is response
    assert len(client.calls) == 1
    assert sleep.delays == []


def test_transient_failure_then_success_backs_off_once():
    response = _FakeResponse("recovered")
    client = FakeClient(_server_error(503), response)
    sleep = RecordingSleep()
    out = generate_chat_completion(client, model="gpt-5.4", messages=[{"role": "user", "content": "hi"}],
                                   sleep=sleep, rng=UpperBoundRng())
    assert out is response
    assert len(client.calls) == 2
    assert len(sleep.delays) == 1
    assert 0.0 < sleep.delays[0] <= llm.DEFAULT_BACKOFF_CAP_S


def test_retries_exhausted_raises_typed_exception():
    client = FakeClient(_client_error(429, message="rate limited"))
    sleep = RecordingSleep()
    with pytest.raises(LLMUnavailable) as excinfo:
        generate_chat_completion(client, model="gpt-5.4", messages=[{"role": "user", "content": "hi"}],
                                 max_attempts=3, sleep=sleep)
    assert excinfo.value.attempts == 3
    assert isinstance(excinfo.value.last_error, openai.RateLimitError)
    assert len(client.calls) == 3
    assert len(sleep.delays) == 2  # no sleep after the final attempt


def test_non_retryable_error_fails_immediately():
    client = FakeClient(_client_error(400))
    sleep = RecordingSleep()
    with pytest.raises(LLMUnavailable) as excinfo:
        generate_chat_completion(client, model="gpt-5.4", messages=[{"role": "user", "content": "hi"}],
                                 max_attempts=5, sleep=sleep)
    assert excinfo.value.attempts == 1
    assert len(client.calls) == 1  # never retried
    assert sleep.delays == []
    assert isinstance(excinfo.value.__cause__, openai.BadRequestError)


def test_backoff_grows_exponentially_and_caps(monkeypatch):
    monkeypatch.setenv("MATRIX_LLM_BACKOFF_BASE_S", "1.0")
    monkeypatch.setenv("MATRIX_LLM_BACKOFF_CAP_S", "3.0")
    client = FakeClient(_server_error(500))
    sleep = RecordingSleep()
    with pytest.raises(LLMUnavailable):
        generate_chat_completion(client, model="m", messages=[{"role": "user", "content": "hi"}], max_attempts=4,
                                 sleep=sleep, rng=UpperBoundRng())
    # full jitter upper bounds: min(cap, 1*2^(k-1)) -> 1, 2, then capped at 3
    assert sleep.delays == [1.0, 2.0, 3.0]


def test_negative_backoff_knob_never_sleeps_negative(monkeypatch):
    monkeypatch.setenv("MATRIX_LLM_BACKOFF_BASE_S", "-1.0")
    client = FakeClient(_server_error(503))
    sleep = RecordingSleep()
    with pytest.raises(LLMUnavailable):  # typed — not time.sleep's ValueError
        generate_chat_completion(client, model="m", messages=[{"role": "user", "content": "hi"}], max_attempts=3,
                                 sleep=sleep)
    assert all(d >= 0.0 for d in sleep.delays)

def test_retry_classification():
    assert is_retryable(_client_error(429))
    assert is_retryable(_server_error(500))
    assert is_retryable(_server_error(503))
    assert is_retryable(openai.APIConnectionError(request=None))
    assert is_retryable(openai.APITimeoutError(request=None))
    assert not is_retryable(_client_error(400))
    assert not is_retryable(_client_error(401))
    assert not is_retryable(_client_error(404))
    assert not is_retryable(ValueError("schema mismatch"))


# --- hard per-call timeout ------------------------------------------------------

def test_max_attempts_env_knob(monkeypatch):
    monkeypatch.setenv("MATRIX_LLM_MAX_ATTEMPTS", "2")
    client = FakeClient(_server_error(503))
    sleep = RecordingSleep()
    with pytest.raises(LLMUnavailable) as excinfo:
        generate_chat_completion(client, model="m", messages=[{"role": "user", "content": "hi"}], sleep=sleep)
    assert excinfo.value.attempts == 2
    assert len(client.calls) == 2


def test_make_client_failure_is_typed(monkeypatch):
    def _boom():
        raise ValueError("Missing key inputs argument!")
    monkeypatch.setattr(openai, "AzureOpenAI", _boom)
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
        raise LLMUnavailable("Azure OpenAI (gpt-5.4) unavailable after 3 attempt(s)",
                             attempts=3)
    monkeypatch.setattr("matrix_kernel.synthesis.generate_chat_completion", _unavailable)
    with caplog.at_level(logging.WARNING, logger="matrix_kernel.synthesis"):
        narrative, citations = synthesize([_result()], client=object())
    assert narrative == "Synthesis narrative generation failed. Please see the raw data."
    assert citations == []
    assert "placeholder narrative" in caplog.text


def test_synthesis_success_path_keeps_cited_numbers(monkeypatch):
    response = _FakeResponse("Trips increased by 450.00 [BEH-1].")
    monkeypatch.setattr("matrix_kernel.synthesis.generate_chat_completion",
                        lambda *a, **k: response)
    narrative, citations = synthesize([_result()], client=object())
    assert "[BEH-1]" in narrative
    assert citations and citations[0]["equation_id"] == "BEH-1"


def test_synthesis_empty_response_text_is_blocked_not_crashed(monkeypatch):
    response = _FakeResponse(None)
    monkeypatch.setattr("matrix_kernel.synthesis.generate_chat_completion",
                        lambda *a, **k: response)
    narrative, citations = synthesize([_result()], client=object())
    assert narrative  # the blocked-narrative message, never a crash on None
    assert citations == []


def test_personas_fall_back_to_static_pool_on_llm_unavailable(monkeypatch, caplog):
    def _no_client():
        raise LLMUnavailable("could not construct Azure OpenAI client", attempts=0)
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
    monkeypatch.setattr(llm, "generate_chat_completion",
                        lambda *a, **k: _FakeResponse("", parsed=parsed))
    pool = generate_persona_pool(n=2, seed=1)
    assert [p.mode for p in pool] == ["jeepney", "walk"]
    assert pool[1].income_decile == 8


def test_personas_fall_back_on_unusable_response(monkeypatch, caplog):
    monkeypatch.setattr(llm, "make_client", lambda: object())
    monkeypatch.setattr(llm, "generate_chat_completion",
                        lambda *a, **k: _FakeResponse("not json", parsed=None))
    with caplog.at_level(logging.WARNING, logger="matrix_kernel.personas"):
        pool = generate_persona_pool(n=10, seed=3)
    assert "unusable Azure OpenAI response" in caplog.text
    assert pool == personas._static_seeded_pool(10, ILOILO_MODE_SHARE, 3)
