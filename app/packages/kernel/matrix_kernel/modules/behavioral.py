"""Behavioral impact module (stub). Confidence: typically High.

Equations (docs/methods-matrix.md §3.1):
  BEH-1  Δ trips/day per corridor    -- datasets: OSM-ILO, OVERTURE, persona pool
  BEH-2  Mode-share shift (+/-3% anchor) -- persona pool, Calderon2014, CCHAIN
  BEH-3  Peak saturation (V/C)       -- SUMO net, OSM-ILO

Returns one DimensionResult per equation. Phase 3 (Gate 3).
"""
from __future__ import annotations

from matrix_kernel.results import DimensionResult


def score(trajectory, datasets) -> list[DimensionResult]:
    raise NotImplementedError("BEH-1/2/3 -- Phase 3 (Gate 3); methods-matrix §3.1")
