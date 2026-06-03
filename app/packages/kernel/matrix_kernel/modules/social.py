"""Social impact module (stub). Confidence: typically Medium.

Equations (docs/methods-matrix.md §3.3):
  SOC-1  Equity-weighted access  -- CCHAIN RWI + health isochrones, NHFR
  SOC-2  Displacement risk count -- CCHAIN osm_poi_*, OSM-ILO
  SOC-3  Distributional split    -- CCHAIN RWI, WorldPop  (PRD-F17)

Returns one DimensionResult per equation. Phase 3 (Gate 3).
"""
from __future__ import annotations

from matrix_kernel.results import DimensionResult


def score(trajectory, datasets) -> list[DimensionResult]:
    raise NotImplementedError("SOC-1..3 -- Phase 3 (Gate 3); methods-matrix §3.3")
