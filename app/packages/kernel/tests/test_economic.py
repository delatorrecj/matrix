"""Tests for Economic module.

ECON-2 and ECON-3 consult loaders backed by `data/raw/`, which data/.gitignore excludes
wholesale -- so on a fresh clone (and in CI) they return None and the equations degrade to
confidence L with the substitution disclosed. That degradation is correct behaviour
(PRD-F14), but it means asserting a bare "confidence == M" only passes on a machine that
happens to have run the manual PSA download and the OSM fetch.

So both branches are pinned explicitly below rather than left to whatever is on disk.
ECON-1 reads BIR zonal values from `data/processed/` (git-tracked), so it must stay M
either way -- that asymmetry is the point of the second test.
"""
import pytest

pytest.importorskip("sumo", reason="eclipse-sumo not installed; run `uv sync` in app/packages/kernel")

import matrix_kernel.datasets as datasets  # noqa: E402  (import after the SUMO guard)
from matrix_kernel.modules.economic import score  # noqa: E402
from matrix_kernel.trajectory import Trajectory  # noqa: E402


@pytest.fixture
def raw_datasets(monkeypatch):
    """Pin the two data/raw-backed loaders ECON-2/ECON-3 consult.

    score() imports them INSIDE the function body (`from matrix_kernel.datasets import ...`),
    so the patch target is the datasets module -- patching matrix_kernel.modules.economic
    would bind nothing. Both loaders are @lru_cache'd; replacing the attribute bypasses the
    cache, so no cache clearing is needed.
    """
    def _apply(*, present: bool):
        # places_factor = clamp(n_places / 10_000, 0.5, 2.0) -> 12_000 lands mid-range at 1.2
        places = (12_000, "OSM amenity nodes (test fixture)") if present else None
        aspbi = (250_000.0, "PSA ASPBI 2022 Western Visayas (test fixture)") if present else None
        monkeypatch.setattr(datasets, "overture_place_count_proxy", lambda: places)
        monkeypatch.setattr(datasets, "western_visayas_aspbi_employment", lambda: aspbi)

    return _apply


def _trajectory() -> Trajectory:
    return Trajectory(
        edge_counts={"C0": 20, "C1": 40, "OTHER": 210},
        frames=[],
        meta={"closed_edges": ["C0", "C1"], "lanes_closed": 1},
    )


_BASELINE = {"C0": 100, "C1": 50, "OTHER": 200}


def test_economic_results(raw_datasets):
    raw_datasets(present=True)
    results = score(_trajectory(), baseline=_BASELINE)

    assert {r.equation_id for r in results} == {"ECON-1", "ECON-2", "ECON-3"}
    by_id = {r.equation_id: r for r in results}
    assert by_id["ECON-1"].confidence == "M"
    assert by_id["ECON-2"].confidence == "M"
    assert by_id["ECON-3"].confidence == "M"
    assert any("ASPBI" in a or "employment" in a.lower() for a in by_id["ECON-3"].assumptions)
    assert any("places" in a.lower() or "footfall" in a.lower() for a in by_id["ECON-2"].assumptions)
    for r in results:
        assert r.range[0] <= r.value <= r.range[1]


def test_economic_degrades_honestly_without_raw_datasets(raw_datasets):
    """Missing data/raw must cap ECON-2/ECON-3 at L and SAY SO under Inspect (PRD-F14) --
    never silently keep the M-confidence label with a scalar stand-in behind it."""
    raw_datasets(present=False)
    results = score(_trajectory(), baseline=_BASELINE)
    by_id = {r.equation_id: r for r in results}

    # BIR zonal values live in data/processed/ (tracked), so ECON-1 must NOT degrade.
    assert by_id["ECON-1"].confidence == "M"

    for eq in ("ECON-2", "ECON-3"):
        assert by_id[eq].confidence == "L", eq
        assumptions = by_id[eq].assumptions
        assert any("missing" in a for a in assumptions), eq
        assert any("capped at L" in a for a in assumptions), eq
        assert by_id[eq].range[0] <= by_id[eq].value <= by_id[eq].range[1], eq
