"""Tests for processed-dataset loaders (Credibility Phase 3)."""
from __future__ import annotations

from matrix_kernel.datasets import (
    bir_median_commercial_php_sqm,
    flood_exposed_population_100yr,
    inverse_rwi_equity_weight,
    latest_worldpop_total,
    mean_market_convenience_pois,
)


def test_worldpop_latest_loads():
    loaded = latest_worldpop_total()
    assert loaded is not None
    pop, year = loaded
    assert pop > 100_000
    assert year == "2020"


def test_bir_median_commercial():
    loaded = bir_median_commercial_php_sqm()
    assert loaded is not None
    median, n = loaded
    assert n > 100
    assert 1_000 < median < 100_000


def test_rwi_and_amenity_and_flood():
    assert inverse_rwi_equity_weight() is not None
    assert mean_market_convenience_pois() is not None
    exposed = flood_exposed_population_100yr()
    assert exposed is not None
    persons, _year = exposed
    assert persons > 0


def test_aspbi_historic_isochrone_loaders():
    from matrix_kernel.datasets import (
        brgy_rwi_and_hospital_access,
        osm_historic_points,
        western_visayas_aspbi_employment,
    )

    emp = western_visayas_aspbi_employment()
    assert emp is not None and emp[0] > 1000
    hist = osm_historic_points()
    assert hist is not None and hist[1] >= 40  # nodes with lon/lat; ways without center skipped
    joined = brgy_rwi_and_hospital_access(15)
    assert joined is not None and len(joined[0]) > 50
