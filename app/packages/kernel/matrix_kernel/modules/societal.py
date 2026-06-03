"""Societal impact module (stub). Confidence: typically Medium.

Equations (docs/methods-matrix.md §3.5):
  SOCI-1  Societal composite      -- weighted sum of the subscores below
  SOCI-2  Heritage proximity      -- NHCP, OSM heritage (117 sites)
  SOCI-3  Health-exposure proxy   -- ECO-2 × WorldPop population density
  SOCI-4  Walkability Δ           -- OSM-ILO, TSSP-2019 bike (Macalalag factors)

Returns one DimensionResult per equation. Phase 3 (Gate 3).
"""
from __future__ import annotations

from matrix_kernel.results import DimensionResult


def score(trajectory, datasets) -> list[DimensionResult]:
    raise NotImplementedError("SOCI-1..4 -- Phase 3 (Gate 3); methods-matrix §3.5")
