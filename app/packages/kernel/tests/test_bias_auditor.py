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
