"""Tests for Social module."""
import pytest

pytest.importorskip("sumo", reason="eclipse-sumo not installed; run `uv sync` in app/packages/kernel")

from matrix_kernel.modules.social import score
from matrix_kernel.trajectory import Trajectory


def test_social_results():
    baseline = {"C0": 100, "C1": 50, "OTHER": 200}
    scenario = Trajectory(
        edge_counts={"C0": 20, "C1": 40, "OTHER": 210},
        frames=[],
        meta={"closed_edges": ["C0", "C1"], "lanes_closed": 1},
    )
    results = score(scenario, baseline=baseline)

    assert {r.equation_id for r in results} == {"SOC-1", "SOC-2", "SOC-3"}
    for r in results:
        assert r.dimension == "social"
        assert r.equation_id and r.input_dataset_ids
        assert r.range[0] <= r.value <= r.range[1]

    by_id = {r.equation_id: r for r in results}
    assert by_id["SOC-1"].confidence == "M"
    assert by_id["SOC-2"].confidence == "M"
    assert by_id["SOC-3"].confidence == "M"
    assert any("barangay" in a.lower() or "isochrone" in a.lower() or "RWI" in a
               for a in by_id["SOC-1"].assumptions)
