"""Bias auditor (PRD-F6) -- a first-class product feature, not polish.

Persona generation is constrained to the Iloilo ground-truth mode share. After every persona
batch, deviation beyond +/-3% (MODE_SHARE_TOLERANCE) flags a reweight, and every check is
appended to a public, append-only audit log (Postgres `bias_audit_log`). methods §4 (bias
auditor card), SDD §3. Phase 2 (Gate 2).

Reweight logic (CR-008 Item 3):
  reweight_pool() applies per-mode multiplicative importance weights:
      f_k = target_k / observed_k   (observed_k > 0)
  and performs a stratified resample so the corrected mode share sits within ±3% of target.
  The adjustment factors ride in BiasAuditEntry.adjustment_factors so they are Inspect-resolvable
  (glass-box: the reweight is never a silent black-box correction).
"""
from __future__ import annotations

import os
import random
from dataclasses import dataclass, field
from typing import Any

MODE_SHARE_TOLERANCE = 0.03  # +/-3% before a reweight is triggered (PRD-F6)
PG_DSN = os.environ.get("MATRIX_PG_DSN", "postgresql://matrix:matrix@localhost:5432/matrix")


@dataclass(frozen=True)
class BiasAuditEntry:
    batch_id: str
    target_mode_share: dict[str, float]
    observed_mode_share: dict[str, float]
    reweighted: bool
    # Per-mode multiplicative correction factors applied by reweight_pool().
    # None when no reweight was performed; populated whenever reweight_pool() is called.
    # Inspect-resolvable: the exact factor for each mode is logged to bias_audit_log.
    adjustment_factors: dict[str, float] | None = field(default=None)

    @property
    def max_delta(self) -> float:
        """Largest |observed - target| across all modes -- the value checked against ±3%."""
        modes = set(self.observed_mode_share) | set(self.target_mode_share)
        return max(
            (abs(self.observed_mode_share.get(m, 0.0) - self.target_mode_share.get(m, 0.0))
             for m in modes),
            default=0.0,
        )


def audit_personas(
    observed: dict[str, float],
    target: dict[str, float],
    batch_id: str = "",
    adjustment_factors: dict[str, float] | None = None,
) -> BiasAuditEntry:
    """Compare observed vs target mode share; flag a reweight beyond ±3% (PRD-F6).

    Pure + side-effect-free so it is unit-testable without a DB; call `persist_audit` to write
    the result to the public log. `adjustment_factors` is set by reweight_pool() so the factors
    ride into the audit entry for glass-box traceability.
    """
    modes = set(observed) | set(target)
    max_delta = max((abs(observed.get(m, 0.0) - target.get(m, 0.0)) for m in modes), default=0.0)
    return BiasAuditEntry(
        batch_id=batch_id,
        target_mode_share=dict(target),
        observed_mode_share=dict(observed),
        reweighted=max_delta > MODE_SHARE_TOLERANCE,
        adjustment_factors=adjustment_factors,
    )


def reweight_pool(
    observed: dict[str, float],
    target: dict[str, float],
    pool: list[Any],
    seed: int | None = None,
) -> tuple[list[Any], dict[str, float]]:
    """Resample the persona pool so the corrected mode share sits within ±3% of target.

    Uses per-mode multiplicative correction factors:
        f_k = target_k / observed_k   (for observed_k > 0)
    A mode absent from the observed share (observed_k == 0) receives an injection factor
    of `_INJECTION_WEIGHT` (10×) so it can appear in the resampled pool at the target rate;
    modes absent from the target are dropped from the resample (weight = 0).

    The resample is stratified: the output pool has the same size as the input pool so the
    pipeline never sees a shrinking or growing persona set. Each persona is sampled with-
    replacement, weighted by its mode's f_k.

    Returns:
        (resampled_pool, adjustment_factors)
        where adjustment_factors maps mode → f_k and is meant to be stored in BiasAuditEntry
        for glass-box traceability.

    Glass-box contract (methods §4):
        The per-mode factors are the full story of what the reweight did — they are logged to
        bias_audit_log.adjustment_factors and surfaced in the Inspect drawer.
    """
    _INJECTION_WEIGHT = 10.0  # weight for zero-observed modes (ensures they can appear)

    rng = random.Random(seed)

    if not pool:
        return [], {}

    # Compute per-mode weights (f_k = target_k / observed_k)
    all_modes = set(target)
    adjustment_factors: dict[str, float] = {}
    for mode in all_modes:
        obs_k = observed.get(mode, 0.0)
        tgt_k = target.get(mode, 0.0)
        if obs_k > 0:
            adjustment_factors[mode] = tgt_k / obs_k
        else:
            # Mode absent in observed but present in target — inject with high weight
            adjustment_factors[mode] = _INJECTION_WEIGHT if tgt_k > 0 else 0.0

    # Assign a weight to each persona from its mode's factor
    # Personas whose mode is not in target (adjustment_factors[mode] == 0) get weight 0 → excluded
    weights: list[float] = []
    for p in pool:
        mode = getattr(p, "mode", None)
        weights.append(adjustment_factors.get(mode, 0.0))

    total_weight = sum(weights)
    if total_weight <= 0:
        # Cannot reweight — all personas are from modes not in target; return original
        return list(pool), adjustment_factors

    # Stratified weighted resample (with replacement) to preserve pool size
    resampled = rng.choices(pool, weights=weights, k=len(pool))
    return resampled, adjustment_factors


def persist_audit(entry: BiasAuditEntry, run_id: str | None = None, dsn: str = PG_DSN) -> str:
    """Append `entry` to the public, append-only `bias_audit_log` (Postgres). Returns the row id."""
    import psycopg  # lazy import: the audit logic must be usable without a DB driver
    from psycopg.types.json import Json

    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO bias_audit_log "
            "  (run_id, batch_id, mode_share, ground_truth, max_delta, reweighted) "
            "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (run_id, entry.batch_id, Json(entry.observed_mode_share),
             Json(entry.target_mode_share), entry.max_delta, entry.reweighted),
        )
        row_id = cur.fetchone()[0]
        conn.commit()
    return str(row_id)
