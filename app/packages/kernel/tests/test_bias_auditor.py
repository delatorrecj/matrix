"""Tests for the bias auditor + persona pool (U5; PRD-F6, methods §4).

Pure mode-share logic always runs; the Redis-cache + Postgres-log integration is skipped
unless both services are up (so `python -m pytest` stays green standalone, per CLAUDE.md).
"""
import pytest

from matrix_kernel import personas
from matrix_kernel.bias_auditor import (
    MODE_SHARE_TOLERANCE,
    PG_DSN,
    audit_personas,
    persist_audit,
    reweight_pool,
)
from matrix_kernel.personas import (
    ILOILO_MODE_SHARE,
    generate_persona_pool,
    observed_mode_share,
)


def test_skewed_batch_is_caught_and_reweighted():
    observed = {"jeepney": 1.0, "private_car": 0.0, "motorcycle": 0.0, "walk": 0.0, "bicycle": 0.0}
    entry = audit_personas(observed, ILOILO_MODE_SHARE, batch_id="skew-test")
    assert entry.reweighted is True
    assert entry.max_delta > MODE_SHARE_TOLERANCE


def test_anchored_pool_passes_audit():
    # A pool sampled from the anchor should sit within ±3% (n large enough that noise < 3%).
    pool = generate_persona_pool(n=2000, seed=42)
    entry = audit_personas(observed_mode_share(pool), ILOILO_MODE_SHARE, batch_id="anchored")
    assert entry.reweighted is False
    assert entry.max_delta <= MODE_SHARE_TOLERANCE


def test_max_delta_is_largest_mode_gap():
    e = audit_personas({"a": 0.5, "b": 0.5}, {"a": 0.6, "b": 0.4})
    assert e.max_delta == pytest.approx(0.1)
    assert e.reweighted is True


def test_pool_size_and_modes():
    pool = generate_persona_pool(n=100, seed=1)
    assert len(pool) == 100
    assert all(p.mode in ILOILO_MODE_SHARE for p in pool)


def test_cache_roundtrip_and_audit_log_write():
    """Integration: skips (not fails) when Redis/Postgres aren't reachable, so the core
    suite still runs standalone (CLAUDE.md). Checked at runtime, not collection time."""
    redis = pytest.importorskip("redis")
    psycopg = pytest.importorskip("psycopg")
    try:
        redis.from_url(personas.REDIS_URL).ping()
        psycopg.connect(PG_DSN).close()
    except Exception as e:  # services down -> skip
        pytest.skip(f"Redis/Postgres not reachable: {e}")

    pool = generate_persona_pool(n=500, seed=42)
    assert personas.cache_pool(pool) == 500
    assert len(personas.load_pool()) == 500
    # A deliberately skewed batch must be caught, reweighted, and appended to the public log.
    entry = audit_personas({"jeepney": 1.0}, ILOILO_MODE_SHARE, batch_id="integration-test")
    assert persist_audit(entry)


def test_reweight_pool_brings_skew_within_tolerance():
    # A pool heavy on private_car
    class MockPersona:
        def __init__(self, mode):
            self.mode = mode

    # We must have at least one of every target mode so they can be sampled!
    # Target: jeepney 0.50, tricycle 0.05, private_car 0.15, motorcycle 0.15, walk 0.1, bicycle 0.05
    # Pool size = 1000
    pool = (
        [MockPersona("private_car") for _ in range(450)] +
        [MockPersona("jeepney") for _ in range(250)] +
        [MockPersona("motorcycle") for _ in range(125)] +
        [MockPersona("walk") for _ in range(75)] +
        [MockPersona("bicycle") for _ in range(50)] +
        [MockPersona("tricycle") for _ in range(50)]
    )
    observed = observed_mode_share(pool)
    assert observed["private_car"] == 0.45

    resampled, factors = reweight_pool(observed, ILOILO_MODE_SHARE, pool, seed=42)
    assert len(resampled) == 1000  # preserves size

    new_observed = observed_mode_share(resampled)
    # The new share should be close to ILOILO_MODE_SHARE within the 3% tolerance
    entry = audit_personas(new_observed, ILOILO_MODE_SHARE)
    assert entry.reweighted is False  # it passes the audit now
    assert entry.max_delta <= MODE_SHARE_TOLERANCE
    assert factors["private_car"] < 1.0  # private_car was down-weighted
    assert factors["jeepney"] > 1.0      # jeepney was up-weighted


def test_reweight_pool_already_within_tolerance_is_noop():
    # If the pool matches the target perfectly, factors should be 1.0 and shares unchanged
    class MockPersona:
        def __init__(self, mode):
            self.mode = mode
    
    # 70 private_car, 30 jeepney target for simplicity
    target = {"private_car": 0.70, "jeepney": 0.30}
    pool = [MockPersona("private_car") for _ in range(70)] + [MockPersona("jeepney") for _ in range(30)]
    observed = observed_mode_share(pool)

    resampled, factors = reweight_pool(observed, target, pool, seed=42)
    assert factors["private_car"] == 1.0
    assert factors["jeepney"] == 1.0
    
    new_observed = observed_mode_share(resampled)
    # Sampling with replacement has binomial variance; check it's approximately the same
    assert new_observed["private_car"] == pytest.approx(0.70, abs=0.08)
    assert new_observed["jeepney"] == pytest.approx(0.30, abs=0.08)


def test_reweight_pool_factors_in_audit_entry():
    # Ensures the factors ride into the entry
    factors = {"jeepney": 1.2, "private_car": 0.5}
    entry = audit_personas({"jeepney": 0.5}, {"jeepney": 0.6}, batch_id="test", adjustment_factors=factors)
    assert entry.reweighted is True
    assert entry.adjustment_factors == factors
