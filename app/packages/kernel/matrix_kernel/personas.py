"""Commuter persona pool + the Iloilo mode-share anchor (PRD-F6; methods §3.1, §4).

Milestone A seeds the pool from a *static* Iloilo mode-share anchor (literature-calibrated
from Calderon 2014 + LPTRP context -> Medium confidence; the documented "soft spot" in
READINESS.md — not a 2026 travel survey). The Gemini 3.1 Flash-Lite generator (RFC
matrix-rfc-001) is a Milestone-B upgrade. The pool is cached in Redis (personas:iloilo:v1)
and *reweighted, not regenerated* per scenario.

The bias auditor ([bias_auditor.py]) enforces this anchor to +/-3% on every batch.
"""
from __future__ import annotations

import json
import os
import random
from dataclasses import asdict, dataclass

# Iloilo mode-share ANCHOR — the ground truth the bias auditor enforces to +/-3%.
# Literature-derived (Calderon 2014 BRT study + Enhanced LPTRP jeepney-dominant context);
# best-available estimate, NOT a live survey -> Behavioral *behavior* confidence = M.
ILOILO_MODE_SHARE: dict[str, float] = {
    "jeepney": 0.55,
    "private_car": 0.15,
    "motorcycle": 0.15,
    "walk": 0.10,
    "bicycle": 0.05,
}

PERSONA_POOL_KEY = "personas:iloilo:v1"
REDIS_URL = os.environ.get("MATRIX_REDIS_URL", "redis://localhost:6379/0")
_PURPOSES = ("work", "school", "shop", "other")


@dataclass(frozen=True)
class Persona:
    """One synthetic commuter. No PII — fully synthetic (SDD §5)."""

    id: str
    mode: str
    income_decile: int   # 1 (lowest) .. 10 (highest)
    trip_purpose: str


def generate_persona_pool(n: int = 500, anchor: dict[str, float] | None = None,
                          seed: int = 42) -> list[Persona]:
    """Sample `n` personas whose mode mix follows the Iloilo anchor (reproducible by seed)."""
    anchor = anchor or ILOILO_MODE_SHARE
    rng = random.Random(seed)
    modes, weights = list(anchor), list(anchor.values())
    return [
        Persona(
            id=f"p{i:04d}",
            mode=rng.choices(modes, weights=weights)[0],
            income_decile=rng.randint(1, 10),
            trip_purpose=rng.choice(_PURPOSES),
        )
        for i in range(n)
    ]


def observed_mode_share(pool: list[Persona]) -> dict[str, float]:
    """The realized mode share of a pool (what the bias auditor compares to the anchor)."""
    n = len(pool) or 1
    counts: dict[str, int] = {}
    for p in pool:
        counts[p.mode] = counts.get(p.mode, 0) + 1
    keys = set(counts) | set(ILOILO_MODE_SHARE)
    return {m: counts.get(m, 0) / n for m in keys}


def cache_pool(pool: list[Persona], key: str = PERSONA_POOL_KEY,
               url: str = REDIS_URL) -> int:
    """Persist the pool to Redis so scenario runs reuse it (RFC matrix-rfc-001). Returns size."""
    import redis  # lazy — importing this module shouldn't require a live Redis

    r = redis.from_url(url)
    r.set(key, json.dumps([asdict(p) for p in pool]))
    return len(pool)


def load_pool(key: str = PERSONA_POOL_KEY, url: str = REDIS_URL) -> list[Persona]:
    """Load the cached pool from Redis."""
    import redis

    raw = redis.from_url(url).get(key)
    if raw is None:
        raise KeyError(f"persona pool {key!r} not in Redis — run generate + cache_pool first")
    return [Persona(**d) for d in json.loads(raw)]
