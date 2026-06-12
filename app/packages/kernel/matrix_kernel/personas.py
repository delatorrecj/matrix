"""Commuter persona pool + the Iloilo mode-share anchor (PRD-F6; methods §3.1, §4).

Milestone A seeds the pool from a *static* Iloilo mode-share anchor (literature-calibrated
from Calderon 2014 + LPTRP context -> Medium confidence; the documented "soft spot" in
READINESS.md — not a 2026 travel survey). The Gemini 3.1 Flash-Lite generator (RFC
matrix-rfc-001) is a Milestone-B upgrade. The pool is cached in Redis
(`personas:{slug}:v1` — `personas:iloilo:v1` by default, see config.py) and
*reweighted, not regenerated* per scenario.

The bias auditor ([bias_auditor.py]) enforces this anchor to +/-3% on every batch.
"""
from __future__ import annotations

import json
import logging
import os
import random
from dataclasses import asdict, dataclass

from matrix_kernel.config import get_city_config

logger = logging.getLogger(__name__)

_CITY = get_city_config()

# Mode-share ANCHOR — the ground truth the bias auditor enforces to +/-3%. The
# canonical per-city values (and the Iloilo source note: Calderon 2014 BRT study +
# Enhanced LPTRP jeepney-dominant context -> confidence M) now live in
# matrix_kernel/config.py. The ILOILO_MODE_SHARE name is kept importable for
# back-compat (runner.py, demand_delta.py, modules/behavioral.py, tests) but holds
# the *active* city's anchor — Iloilo by default, with the exact historical values.
ILOILO_MODE_SHARE: dict[str, float] = dict(_CITY.mode_share)

PERSONA_POOL_KEY = _CITY.persona_pool_key
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
    """Sample `n` personas via Gemini 3.1 Flash-Lite, following the Iloilo anchor."""
    anchor = anchor or ILOILO_MODE_SHARE
    from google.genai import types
    from pydantic import BaseModel

    from matrix_kernel.llm import LLMUnavailable, generate_content, make_client

    class PersonaList(BaseModel):
        personas: list[dict]

    try:
        client = make_client()
        model_name = os.environ.get("GEMINI_MODEL_FLASH_LITE", "gemini-3.1-flash-lite")

        prompt = (
            f"Generate {n} diverse commuter personas for Iloilo City. "
            f"The overall mode share MUST roughly match this distribution: {anchor}. "
            "Each persona should have:\n"
            "- id: string (e.g. 'p0001')\n"
            "- mode: string (one of the keys in the mode share anchor)\n"
            "- income_decile: integer (1 to 10)\n"
            "- trip_purpose: string ('work', 'school', 'shop', 'other')\n"
            "Return the result as a JSON object with a 'personas' list."
        )

        response = generate_content(
            client,
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=PersonaList,
                temperature=0.7,
            ),
        )
    except LLMUnavailable as e:
        logger.warning(
            "personas: Gemini unavailable after %d attempt(s) — falling back to "
            "the static seeded pool. (%s)", e.attempts, e)
        return _static_seeded_pool(n, anchor, seed)

    try:
        data = response.parsed.personas if hasattr(response.parsed, 'personas') else json.loads(response.text).get('personas', [])

        pool = []
        for d in data:
            pool.append(Persona(
                id=d.get("id", f"p{len(pool):04d}"),
                mode=d.get("mode", "jeepney"),
                income_decile=int(d.get("income_decile", 5)),
                trip_purpose=d.get("trip_purpose", "work")
            ))

        # Ensure we have exactly n
        while len(pool) < n:
            pool.append(pool[-1])
        return pool[:n]
    except Exception as e:
        logger.warning(
            "personas: unusable Gemini response (%s) — falling back to the "
            "static seeded pool.", e)
        return _static_seeded_pool(n, anchor, seed)


def _static_seeded_pool(n: int, anchor: dict[str, float], seed: int) -> list[Persona]:
    """The static literature-anchored fallback pool (the Milestone-A seeding) —
    runs when Gemini is unavailable or returns an unusable payload."""
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
