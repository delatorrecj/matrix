"""Confidence rubric + earned-confidence ensemble (methods-matrix §2, §5; PRD-F5, F15).

confidence_rubric()          -- maps the datasets a result consumed to H/M/L by the
                                "worst factor caps the tier" rule (methods §2). Confidence
                                is *computed* from data provenance, never guessed.
earned_confidence_interval() -- Monte-Carlo over uncertain assumptions -> a (lo, hi) range
                                (10th-90th percentile, methods §5), so the range is earned,
                                not a flat +/-% (PRD-F15).
"""
from __future__ import annotations

from typing import Callable, Sequence

import numpy as np

from matrix_kernel.results import Confidence

# Per-dataset confidence tiers. Sourced from data/INVENTORY.md (Conf column) and the
# methods-matrix §3 per-equation "Conf basis" -- e.g. Calderon2014 caps a mode-share result
# at M as a 2014 literature calibration, even though as a source document it is high quality.
# The unified kernel stamps each result's input_dataset_ids; this maps them to a tier.
# Later this can read the SDD `datasets` table; for now it is the curated, citable ledger.
DATASET_TIERS: dict[str, Confidence] = {
    # Engine / base geometry -- full Iloilo coverage, established physics (H)
    "OSM-ILO": "H",
    "OVERTURE": "H",
    "SUMO-NET": "H",        # derived from OSM-ILO via netconvert (network physics)
    "CCHAIN": "H",
    "WorldPop": "H",
    "WORLDCOVER": "H",
    "WHO-EMEP": "H",        # established emission factors
    # Bias-audited synthetic persona pool -- validated to the ground-truth anchor (H)
    "PERSONA-POOL": "H",
    # Live ground monitoring / open-gov registries -- current, full Iloilo coverage (H).
    # Tiers taken from data/INVENTORY.md's Conf column (the dataset-quality ledger); a
    # weaker *method* on top of these still caps a result via the worst-factor rule.
    "EMB": "H",             # DENR-EMB ground air-quality stations (INVENTORY OPENAQ/EMB row: H)
    "LIPAD": "H",           # PhilLiDAR/LiPAD Iloilo flood + DTM (INVENTORY LIPAD: H)
    "DEM": "H",             # Copernicus GLO-30 DEM (INVENTORY DEM-GLO30: H)
    "NHFR": "H",            # DOH National Health Facility Registry, live open-gov (INVENTORY NHFR: H)
    # Satellite proxy -- live but a regional proxy for ground concentrations (M)
    "S5P-NO2": "M",         # Sentinel-5P NO2 (INVENTORY S5P-NO2: M)
    # Literature-calibration anchors / proxies -- literature-calibrated or ~>10yr (M)
    "Calderon2014": "M",
    "TSSP-2019": "M",
    "BIR-ZV": "M",
    "PSA-ASPBI": "M",
    "PSA-OpenStat": "M",
    "NHCP": "M",
}

_RANK: dict[Confidence, int] = {"L": 1, "M": 2, "H": 3}
_BY_RANK: dict[int, Confidence] = {1: "L", 2: "M", 3: "H"}


def confidence_rubric(input_dataset_ids: Sequence[str]) -> Confidence:
    """Compute the H/M/L tier from the consumed datasets (methods-matrix §2).

    "Worst factor caps the tier": a result is only as trustworthy as its weakest input.
    Unknown / unprovenanced dataset IDs are treated as Low -- we cannot earn confidence from
    data we cannot trace, the honest conservative default for a glass box.
    """
    if not input_dataset_ids:
        raise ValueError("confidence_rubric: no datasets to assess (glass-box, PRD-F14)")
    worst = min(_RANK[DATASET_TIERS.get(ds, "L")] for ds in input_dataset_ids)
    return _BY_RANK[worst]


def method_capped_confidence(
    input_dataset_ids: Sequence[str], method_maturity: Confidence
) -> Confidence:
    """Worst of the data-tier rubric AND the equation's method maturity (methods §2).

    `confidence = f(data vintage, coverage, method maturity, validation)` — worst factor
    caps the tier. `confidence_rubric` covers the *data* factors; some equations sit on a
    *method* that is weaker than their inputs (e.g. ECO-4's flood-exposure redistribution or
    SOC-1's equity-weighted access are literature-calibrated → M even though the flood-hazard
    and registry inputs are H). Pass that ceiling here so the demotion is computed and
    declared, never silently inherited or guessed. Mirrors `demand_delta._computed_confidence`.
    """
    data_tier = confidence_rubric(input_dataset_ids)
    return _BY_RANK[min(_RANK[data_tier], _RANK[method_maturity])]


def earned_confidence_interval(
    point: float,
    sample: Callable[[], float],
    n: int = 1000,
) -> tuple[float, float]:
    """Sample uncertain assumptions -> (lo, hi) = 10th-90th percentile (methods §5, PRD-F15).

    Guaranteed to bracket `point` (lo <= point <= hi) so the central estimate always sits
    inside its earned range (DimensionResult requires lo <= hi).
    """
    n = max(1, n)
    draws = np.fromiter((sample() for _ in range(n)), dtype=float, count=n)
    lo = float(min(np.percentile(draws, 10), point))
    hi = float(max(np.percentile(draws, 90), point))
    return (lo, hi)
