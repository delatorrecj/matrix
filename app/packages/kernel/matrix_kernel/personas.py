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
    from pydantic import BaseModel
    from matrix_kernel.llm import LLMUnavailable, generate_chat_completion, make_client

    class PersonaList(BaseModel):
        personas: list[dict]

    try:
        client = make_client()
        model_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5.4")

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

        messages = [{"role": "user", "content": prompt}]
        response = generate_chat_completion(
            client,
            model=model_name,
            messages=messages,
            response_format=PersonaList,
            temperature=0.7,
        )
    except LLMUnavailable as e:
        logger.warning(
            "personas: Gemini unavailable after %d attempt(s) — falling back to "
            "the static seeded pool. (%s)", e.attempts, e)
        return _static_seeded_pool(n, anchor, seed)

    try:
        data = response.choices[0].message.parsed.personas if hasattr(response.choices[0].message, 'parsed') else json.loads(response.choices[0].message.content).get('personas', [])

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


def warm_persona_pool(
    n: int = 500,
    anchor: dict[str, float] | None = None,
    seed: int = 42,
    use_llm: bool | None = None,
):
    """The full bias-auditor loop in one place (PRD-F6): generate → audit → reweight-if-drift
    → cache. This is what wires the auditor + reweighter onto a live code path (run at API
    startup); previously both existed only in tests.

    Returns ``(pool, BiasAuditEntry)``. The realized mode share is checked against the anchor;
    if it drifts beyond ±3% the pool is reweighted (matrix_kernel.bias_auditor.reweight_pool)
    and the per-mode factors are recorded on the entry so the correction is glass-box
    (Inspect-resolvable, never silent). The deployed default uses the static literature-anchored
    pool (deterministic, on-anchor by construction → no correction needed); set
    ``MATRIX_PERSONA_LLM=1`` to exercise the Gemini 3.1 Flash-Lite generator, whose drift is
    what the reweighter corrects. Best-effort caching: a Redis failure never aborts warming.
    """
    from matrix_kernel.bias_auditor import audit_personas, reweight_pool

    anchor = anchor or ILOILO_MODE_SHARE
    if use_llm is None:
        use_llm = os.environ.get("MATRIX_PERSONA_LLM", "0") == "1"

    pool = generate_persona_pool(n, anchor, seed) if use_llm else _static_seeded_pool(n, anchor, seed)
    observed = observed_mode_share(pool)
    entry = audit_personas(observed, anchor, batch_id=PERSONA_POOL_KEY)

    if entry.reweighted:
        pool, factors = reweight_pool(observed, anchor, pool, seed=seed)
        observed = observed_mode_share(pool)
        # Re-audit the corrected pool and carry the factors so the public log shows the math.
        entry = audit_personas(observed, anchor, batch_id=PERSONA_POOL_KEY, adjustment_factors=factors)

    try:
        cache_pool(pool)
        cache_pool_audit(entry)
    except Exception as exc:  # Redis down — warming is best-effort, the run path falls back.
        logger.warning("warm_persona_pool: cache skipped (%s)", exc)

    return pool, entry


def cache_pool(pool: list[Persona], key: str = PERSONA_POOL_KEY,
               url: str = REDIS_URL) -> int:
    """Persist the pool to Redis so scenario runs reuse it (RFC matrix-rfc-001). Returns size."""
    import redis  # lazy — importing this module shouldn't require a live Redis

    r = redis.from_url(url)
    r.set(key, json.dumps([asdict(p) for p in pool]))
    return len(pool)


_POOL_AUDIT_KEY = PERSONA_POOL_KEY + ":audit"


def cache_pool_audit(entry, key: str = _POOL_AUDIT_KEY, url: str = REDIS_URL) -> None:
    """Cache the warmed pool's BiasAuditEntry (incl. any reweight factors) so each run can
    log it against its run_id without regenerating the pool (PRD-F6, 90 s budget)."""
    import redis

    redis.from_url(url).set(key, json.dumps(entry.as_dict()))


def load_pool_audit(key: str = _POOL_AUDIT_KEY, url: str = REDIS_URL) -> dict | None:
    """Load the cached warmed-pool audit entry (dict), or None when none has been warmed."""
    import redis

    raw = redis.from_url(url).get(key)
    return json.loads(raw) if raw is not None else None


def load_pool(key: str = PERSONA_POOL_KEY, url: str = REDIS_URL) -> list[Persona]:
    """Load the cached pool from Redis."""
    import redis

    raw = redis.from_url(url).get(key)
    if raw is None:
        raise KeyError(f"persona pool {key!r} not in Redis — run generate + cache_pool first")
    return [Persona(**d) for d in json.loads(raw)]
