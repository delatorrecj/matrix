"""Tests for Societal module.

SOCI-2 (heritage) and SOCI-4 (walkability) both read the Iloilo OSM extract under
`data/raw/`, which data/.gitignore excludes -- absent on a fresh clone and in CI, where
they degrade to confidence L with the substitution disclosed. Both branches are pinned
explicitly below so the result does not depend on whether this machine ran the OSM fetch.
"""
import pytest

# modules.societal -> baseline -> sumo_env needs the eclipse-sumo wheel at import;
# skip cleanly on a bare venv instead of erroring at collection (`uv sync` runs it).
pytest.importorskip("sumo", reason="eclipse-sumo not installed; run `uv sync` in app/packages/kernel")

import matrix_kernel.modules.societal as societal  # noqa: E402  (import after the SUMO guard)
from matrix_kernel.modules.societal import _GENERIC_POP_DENSITY, score  # noqa: E402
from matrix_kernel.trajectory import Trajectory  # noqa: E402


@pytest.fixture
def raw_datasets(monkeypatch):
    """Pin the two data/raw-backed loaders SOCI-2/SOCI-4 consult.

    societal.py imports these at MODULE level, so the patch target is
    matrix_kernel.modules.societal -- patching matrix_kernel.datasets would not rebind the
    names score() actually calls. (economic.py imports its loaders inside the function, so
    its fixture patches the other namespace; the asymmetry is deliberate, not an oversight.)

    tssp2019_walk_factors() is left alone: it reads matrix_kernel/data/, which ships in the
    package and is git-tracked.
    """
    def _apply(*, present: bool):
        # (lat, lon) -- that ORDER is what osm_historic_points returns and what the
        # distance decay unpacks. Points sit near the module's city centroid so the
        # exp(-d/2km) decay is meaningful rather than ~0.
        points = [(10.7202, 122.5621), (10.7050, 122.5700)]
        historic = (points, len(points)) if present else None
        density = (0.35, 1_200) if present else None      # (fraction of ways, n_ways)
        monkeypatch.setattr(societal, "osm_historic_points", lambda: historic)
        monkeypatch.setattr(societal, "osm_walk_bike_tag_density", lambda: density)

    return _apply


def _trajectory() -> Trajectory:
    return Trajectory(
        edge_counts={"C0": 20, "C1": 40, "OTHER": 210},
        frames=[],
        meta={"closed_edges": ["C0", "C1"], "lanes_closed": 1, "val01_status": "PASS"},
    )


_BASELINE = {"C0": 100, "C1": 50, "OTHER": 200}


def test_societal_results(raw_datasets):
    raw_datasets(present=True)
    # Passed eco2_val = 10.0 as a mock
    results = score(_trajectory(), baseline=_BASELINE, eco2_val=10.0)

    assert {r.equation_id for r in results} == {"SOCI-1", "SOCI-2", "SOCI-3", "SOCI-4"}
    for r in results:
        assert r.dimension == "societal"
        assert r.equation_id and r.input_dataset_ids
        assert r.range[0] <= r.value <= r.range[1]

    # Check SOCI-3 uses the passed eco2_val × the named density constant
    soci3 = next(r for r in results if r.equation_id == "SOCI-3")
    assert soci3.value == 10.0 * _GENERIC_POP_DENSITY
    # Glass box: the provisional density placeholder must be disclosed honestly
    # in the assumptions surfaced under Inspect (PRD-F14).
    assert any("PROVISIONAL" in a for a in soci3.assumptions)
    # SOCI-3 uses §3.6 PROVISIONAL _GENERIC_POP_DENSITY → L (methods §2).
    assert soci3.confidence == "L"
    assert soci3.directional is True
    by_id = {r.equation_id: r for r in results}
    assert by_id["SOCI-2"].confidence == "M"
    assert by_id["SOCI-4"].confidence == "M"
    assert any("historic" in a.lower() or "OSM" in a for a in by_id["SOCI-2"].assumptions)
    assert any("TSSP" in a or "walk" in a.lower() for a in by_id["SOCI-4"].assumptions)


def test_societal_degrades_honestly_without_raw_datasets(raw_datasets):
    """Missing data/raw must cap SOCI-2/SOCI-4 at L and SAY SO under Inspect (PRD-F14)."""
    raw_datasets(present=False)
    results = score(_trajectory(), baseline=_BASELINE, eco2_val=10.0)
    by_id = {r.equation_id: r for r in results}

    for eq in ("SOCI-2", "SOCI-4"):
        assert by_id[eq].confidence == "L", eq
        assert any("missing" in a for a in by_id[eq].assumptions), eq
        assert by_id[eq].range[0] <= by_id[eq].value <= by_id[eq].range[1], eq

    # SOCI-3 is L by construction (PROVISIONAL density) and the composite follows the
    # worst component either way -- neither depends on data/raw.
    assert by_id["SOCI-3"].confidence == "L"
    assert by_id["SOCI-1"].confidence == "L"
