"""Tests for processed-dataset loaders (Credibility Phase 3)."""
from __future__ import annotations

import pytest

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


def test_isochrone_rwi_join():
    """Reads data/processed/cchain_iloilo/ (git-tracked), so this always runs."""
    from matrix_kernel.datasets import brgy_rwi_and_hospital_access

    joined = brgy_rwi_and_hospital_access(15)
    assert joined is not None and len(joined[0]) > 50


def test_aspbi_and_historic_loaders_when_raw_is_present():
    """ASPBI + OSM historic parse out of `data/raw/`, which data/.gitignore excludes -- so
    they are absent in CI and on a fresh clone. Skip rather than fail (the precedent is
    tests/test_geometry_sumolib.py, which skips on the gitignored net): this keeps parser
    coverage on a machine that has the data, while the MODULES' behaviour when it is
    missing is covered by the degradation tests in test_economic.py / test_societal.py.
    """
    from matrix_kernel.datasets import osm_historic_points, western_visayas_aspbi_employment

    emp = western_visayas_aspbi_employment()
    hist = osm_historic_points()
    if emp is None or hist is None:
        pytest.skip("data/raw not materialized (gitignored) -- see data/fetch/ and data/INVENTORY.md")

    assert emp[0] > 1000
    assert hist[1] >= 40  # nodes with lon/lat; ways without center skipped
