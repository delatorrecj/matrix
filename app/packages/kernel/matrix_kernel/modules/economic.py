"""Economic impact module (stub). Confidence: Medium.

Equations (docs/methods-matrix.md §3.4):
  ECON-1  Land-value Δ (≤1 km)  -- BIR-ZV (✅ manual XLS), CCHAIN RWI
                                   carry confidence M.
  ECON-2  Footfall Δ per zone   -- persona pool, OVERTURE places
  ECON-3  Employment Δ          -- PSA-ASPBI/OpenStat, ADB/NEDA multiplier

Returns one DimensionResult per equation. Phase 3 (Gate 3).
"""
from __future__ import annotations

from matrix_kernel.results import DimensionResult


def score(trajectory, datasets) -> list[DimensionResult]:
    raise NotImplementedError("ECON-1..3 -- Phase 3 (Gate 3); methods-matrix §3.4")
