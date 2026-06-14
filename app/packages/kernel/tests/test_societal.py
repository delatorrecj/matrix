"""Tests for Societal module."""
import pytest

# modules.societal -> baseline -> sumo_env needs the eclipse-sumo wheel at import;
# skip cleanly on a bare venv instead of erroring at collection (`uv sync` runs it).
pytest.importorskip("sumo", reason="eclipse-sumo not installed; run `uv sync` in app/packages/kernel")

from matrix_kernel.modules.societal import score, _GENERIC_POP_DENSITY
from matrix_kernel.trajectory import Trajectory

def test_societal_results():
    baseline = {"C0": 100, "C1": 50, "OTHER": 200}
    scenario = Trajectory(
        edge_counts={"C0": 20, "C1": 40, "OTHER": 210},
        frames=[],
        meta={"closed_edges": ["C0", "C1"], "lanes_closed": 1},
    )
    # Passed eco2_val = 10.0 as a mock
    results = score(scenario, baseline=baseline, eco2_val=10.0)

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
