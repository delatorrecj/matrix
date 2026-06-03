"""Bias auditor (stub) -- PRD-F6. A first-class product feature, not polish.

Persona generation is constrained to Iloilo ground-truth mode share. After every
persona batch, deviation beyond +/-3% triggers a reweight, and every check appends
to a public, append-only audit log (Supabase: bias_audit). Phase 2 (Gate 2).
"""
from __future__ import annotations

from dataclasses import dataclass

MODE_SHARE_TOLERANCE = 0.03  # +/-3% before a reweight is triggered (PRD-F6)


@dataclass(frozen=True)
class BiasAuditEntry:
    batch_id: str
    target_mode_share: dict[str, float]
    observed_mode_share: dict[str, float]
    reweighted: bool


def audit_personas(
    observed: dict[str, float],
    target: dict[str, float],
) -> BiasAuditEntry:
    """Compare observed vs target mode share; flag/reweight beyond tolerance."""
    raise NotImplementedError("mode-share +/-3% audit + public log -- Phase 2 (Gate 2)")
