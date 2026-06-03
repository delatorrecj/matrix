"""Ecological impact module (stub). Confidence: typically High (Medium for air).

Equations (docs/methods-matrix.md §3.2):
  ECO-1  Transport CO2e Δ      -- SUMO VKT per mode, WHO/EMEP emission factors
  ECO-2  Air-quality delta     -- EMB/OPENAQ, S5P-NO2  (Medium)
  ECO-3  Green-cover loss      -- CCHAIN esa_worldcover, WORLDCOVER, Sentinel-2
  ECO-4  Flood-exposure Δ      -- CCHAIN project_noah_hazards, LIPAD, DEM

Returns one DimensionResult per equation. Phase 3 (Gate 3).
"""
from __future__ import annotations

from matrix_kernel.results import DimensionResult


def score(trajectory, datasets) -> list[DimensionResult]:
    raise NotImplementedError("ECO-1..4 -- Phase 3 (Gate 3); methods-matrix §3.2")
