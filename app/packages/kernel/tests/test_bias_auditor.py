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


def test_entry_as_dict_carries_factors_and_computed_delta():
    """as_dict() is the shape the public log / WS / Redis cache consume — it must carry the
    factors and a *computed* max_delta (never a stored 0.0)."""
    factors = {"jeepney": 1.2, "private_car": 0.5}
    d = audit_personas({"jeepney": 0.5}, {"jeepney": 0.6}, batch_id="t", adjustment_factors=factors).as_dict()
    assert d["adjustment_factors"] == factors
    assert d["max_delta"] == pytest.approx(0.1)
    assert d["reweighted"] is True
    assert set(d) == {"batch_id", "target_mode_share", "observed_mode_share",
                      "reweighted", "adjustment_factors", "max_delta"}


def test_warm_persona_pool_runs_the_full_loop():
    """warm_persona_pool wires generate→audit→reweight onto a live path (was test-only).
    The static literature-anchored default is deterministic and Redis-free (caching is
    best-effort), so this runs in a bare env."""
    pool, entry = personas.warm_persona_pool(n=400, use_llm=False, seed=11)
    assert len(pool) == 400
    assert entry.target_mode_share == ILOILO_MODE_SHARE
    # The entry is self-consistent: reweighted iff the realized share drifted past tolerance.
    assert entry.reweighted == (entry.max_delta > MODE_SHARE_TOLERANCE)
    assert entry.as_dict()["observed_mode_share"]  # non-empty realized share


def test_methods_4_1_worked_example_matches_doc():
    """Executable mirror of methods-matrix §4.1 (CR-012 WS-4) — the judges-facing bias
    worked example. A persona-LLM batch that over-generates private cars is flagged,
    reweighted, and passes re-audit; the per-mode factors match the documented table.
    Pins the doc's numbers to reality so they can never silently drift."""
    class MockPersona:
        def __init__(self, mode):
            self.mode = mode

    # §4.1 "Observed" column (the over-indexed LLM batch) as integer counts over n=2000:
    # shares 0.40 / 0.30 / 0.15 / 0.08 / 0.04 / 0.03 (sum 1.0).
    observed_counts = {
        "jeepney": 800, "private_car": 600, "motorcycle": 300,
        "walk": 160, "bicycle": 80, "tricycle": 60,
    }
    pool = [MockPersona(m) for m, c in observed_counts.items() for _ in range(c)]
    observed = observed_mode_share(pool)
    assert observed["private_car"] == pytest.approx(0.30)

    # Audit flags it: private_car +0.15 over anchor, far beyond ±3%.
    flagged = audit_personas(observed, ILOILO_MODE_SHARE, batch_id="methods-4.1")
    assert flagged.reweighted is True
    assert flagged.max_delta == pytest.approx(0.15)

    # Reweight → the per-mode factors match the §4.1 table (f_k = target / observed).
    resampled, factors = reweight_pool(observed, ILOILO_MODE_SHARE, pool, seed=42)
    assert factors["jeepney"] == pytest.approx(1.25)
    assert factors["private_car"] == pytest.approx(0.50)
    assert factors["motorcycle"] == pytest.approx(1.00)
    assert factors["walk"] == pytest.approx(1.25)
    assert factors["bicycle"] == pytest.approx(1.25)
    assert factors["tricycle"] == pytest.approx(5 / 3, abs=0.01)  # 0.05/0.03 ≈ 1.67

    # Re-audit the corrected pool: now within ±3% (the §4.1 "Result" row).
    corrected = audit_personas(observed_mode_share(resampled), ILOILO_MODE_SHARE)
    assert corrected.reweighted is False
    assert corrected.max_delta <= MODE_SHARE_TOLERANCE


def test_deployed_static_pool_is_on_anchor_by_construction():
    """WS-4 / T4.2: the DEPLOYED default pool is sampled straight from the anchor, so it is
    on-target by construction → the audit passes with no reweight. The reweight is the safety
    net for the opt-in LLM-persona path (where model bias can appear), not a prod correction."""
    pool = generate_persona_pool(n=2000, seed=7)  # the deployed-style static pool
    entry = audit_personas(observed_mode_share(pool), ILOILO_MODE_SHARE, batch_id="deployed-default")
    assert entry.reweighted is False
    assert entry.adjustment_factors is None  # no correction was needed
