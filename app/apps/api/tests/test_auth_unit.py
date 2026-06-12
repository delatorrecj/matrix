"""Pure matrix_api/auth.py unit tests -- run BARE (no SUMO/Redis/Gemini, no app import).

auth.py only needs fastapi + starlette, so these run in any environment -- unlike
tests/test_auth.py, whose end-to-end checks import matrix_api.main and therefore
need the eclipse-sumo wheel. Covers: env flag/key/origin parsing, bearer-token
extraction, fail-closed key validation, and the sliding-window rate limiter
(per-key isolation, Retry-After, window expiry, <=0 disables).
"""
from __future__ import annotations

import time

import pytest

from matrix_api import auth

ENV_VARS = (
    "MATRIX_AUTH_ENABLED",
    "MATRIX_API_KEYS",
    "MATRIX_RATE_LIMIT_ENABLED",
    "MATRIX_RATE_LIMIT_PER_MIN",
    "MATRIX_ALLOWED_ORIGINS",
)


@pytest.fixture(autouse=True)
def clean_auth_env(monkeypatch):
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)


# ------------------------------------------------------------------ env parsing

def test_auth_disabled_by_default():
    assert auth.auth_enabled() is False


@pytest.mark.parametrize("raw", ["1", "true", "TRUE", " yes ", "On"])
def test_auth_enabled_truthy_values(monkeypatch, raw):
    monkeypatch.setenv("MATRIX_AUTH_ENABLED", raw)
    assert auth.auth_enabled() is True


@pytest.mark.parametrize("raw", ["0", "false", "no", "off", ""])
def test_auth_enabled_falsy_values(monkeypatch, raw):
    monkeypatch.setenv("MATRIX_AUTH_ENABLED", raw)
    assert auth.auth_enabled() is False


def test_api_keys_parse_and_strip(monkeypatch):
    assert auth.api_keys() == ()
    monkeypatch.setenv("MATRIX_API_KEYS", " key-a , key-b ,, ")
    assert auth.api_keys() == ("key-a", "key-b")


def test_rate_limit_enabled_follows_auth_by_default(monkeypatch):
    assert auth.rate_limit_enabled() is False
    monkeypatch.setenv("MATRIX_AUTH_ENABLED", "true")
    assert auth.rate_limit_enabled() is True
    monkeypatch.setenv("MATRIX_RATE_LIMIT_ENABLED", "false")  # explicit override wins
    assert auth.rate_limit_enabled() is False


def test_rate_limit_per_min_default_and_invalid(monkeypatch):
    assert auth.rate_limit_per_min() == auth.DEFAULT_RATE_LIMIT_PER_MIN
    monkeypatch.setenv("MATRIX_RATE_LIMIT_PER_MIN", "10")
    assert auth.rate_limit_per_min() == 10
    monkeypatch.setenv("MATRIX_RATE_LIMIT_PER_MIN", "not-a-number")
    assert auth.rate_limit_per_min() == auth.DEFAULT_RATE_LIMIT_PER_MIN


def test_allowed_origins_default_and_parsing(monkeypatch):
    assert auth.allowed_origins() == list(auth.DEFAULT_ALLOWED_ORIGINS)
    monkeypatch.setenv(
        "MATRIX_ALLOWED_ORIGINS", " https://matrix.iloilo.gov.ph , http://localhost:3000 ,"
    )
    assert auth.allowed_origins() == ["https://matrix.iloilo.gov.ph", "http://localhost:3000"]


# ------------------------------------------------------------------ bearer + keys

@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (None, None),
        ("", None),
        ("Bearer", None),
        ("Bearer ", None),
        ("Basic abc123", None),
        ("Bearer my-key", "my-key"),
        ("bearer my-key", "my-key"),  # scheme is case-insensitive (RFC 9110 §11.1)
        ("Bearer  my-key ", "my-key"),
    ],
)
def test_bearer_key_extraction(header, expected):
    assert auth._bearer_key(header) == expected


def test_key_validation_fails_closed_without_keys(monkeypatch):
    assert auth._key_is_valid("anything") is False
    monkeypatch.setenv("MATRIX_API_KEYS", "key-a,key-b")
    assert auth._key_is_valid("key-b") is True
    assert auth._key_is_valid("key-c") is False


def test_key_validation_non_ascii_candidate_is_rejected_not_crash(monkeypatch):
    # compare_digest raises TypeError on non-ASCII str; the candidate is
    # attacker-controlled, so this must be a clean False (-> 401), never a 500.
    monkeypatch.setenv("MATRIX_API_KEYS", "key-a")
    assert auth._key_is_valid("café") is False
    monkeypatch.setenv("MATRIX_API_KEYS", "café")
    assert auth._key_is_valid("café") is True


# ------------------------------------------------------------------ rate limiter

def test_limiter_allows_under_limit_then_429s():
    limiter = auth.SlidingWindowLimiter()
    for _ in range(3):
        assert limiter.hit("k", 3) is None
    retry_after = limiter.hit("k", 3)
    assert retry_after is not None
    assert retry_after >= 1


def test_limiter_buckets_are_per_key():
    limiter = auth.SlidingWindowLimiter()
    assert limiter.hit("k1", 1) is None
    assert limiter.hit("k1", 1) is not None
    assert limiter.hit("k2", 1) is None  # other key unaffected


def test_limiter_window_expires():
    limiter = auth.SlidingWindowLimiter(window_seconds=0.05)
    assert limiter.hit("k", 1) is None
    assert limiter.hit("k", 1) is not None
    time.sleep(0.06)
    assert limiter.hit("k", 1) is None


def test_limiter_nonpositive_limit_disables():
    limiter = auth.SlidingWindowLimiter()
    for _ in range(10):
        assert limiter.hit("k", 0) is None
        assert limiter.hit("k", -1) is None


def test_limiter_bucket_count_is_hard_capped():
    limiter = auth.SlidingWindowLimiter(max_buckets=2)
    for i in range(5):  # distinct fresh keys: nothing is stale, FIFO eviction kicks in
        assert limiter.hit(f"k{i}", 10) is None
    assert len(limiter._hits) <= 2


def test_limiter_reset():
    limiter = auth.SlidingWindowLimiter()
    assert limiter.hit("k", 1) is None
    assert limiter.hit("k", 1) is not None
    limiter.reset()
    assert limiter.hit("k", 1) is None
