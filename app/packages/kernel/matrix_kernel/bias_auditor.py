"""Bias auditor (PRD-F6) -- a first-class product feature, not polish.

Persona generation is constrained to the Iloilo ground-truth mode share. After every persona
batch, deviation beyond +/-3% (MODE_SHARE_TOLERANCE) flags a reweight, and every check is
appended to a public, append-only audit log (Postgres `bias_audit_log`). methods §4 (bias
auditor card), SDD §3. Phase 2 (Gate 2).
"""
from __future__ import annotations

import os
from dataclasses import dataclass

MODE_SHARE_TOLERANCE = 0.03  # +/-3% before a reweight is triggered (PRD-F6)
PG_DSN = os.environ.get("MATRIX_PG_DSN", "postgresql://matrix:matrix@localhost:5432/matrix")


@dataclass(frozen=True)
class BiasAuditEntry:
    batch_id: str
    target_mode_share: dict[str, float]
    observed_mode_share: dict[str, float]
    reweighted: bool

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
) -> BiasAuditEntry:
    """Compare observed vs target mode share; flag a reweight beyond ±3% (PRD-F6).

    Pure + side-effect-free so it is unit-testable without a DB; call `persist_audit` to write
    the result to the public log.
    """
    modes = set(observed) | set(target)
    max_delta = max((abs(observed.get(m, 0.0) - target.get(m, 0.0)) for m in modes), default=0.0)
    return BiasAuditEntry(
        batch_id=batch_id,
        target_mode_share=dict(target),
        observed_mode_share=dict(observed),
        reweighted=max_delta > MODE_SHARE_TOLERANCE,
    )


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
