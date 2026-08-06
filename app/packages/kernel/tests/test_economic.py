"""Tests for Economic module."""
import pytest

pytest.importorskip("sumo", reason="eclipse-sumo not installed; run `uv sync` in app/packages/kernel")

from matrix_kernel.modules.economic import score
from matrix_kernel.trajectory import Trajectory


def test_economic_results():
    baseline = {"C0": 100, "C1": 50, "OTHER": 200}
    scenario = Trajectory(
        edge_counts={"C0": 20, "C1": 40, "OTHER": 210},
        frames=[],
        meta={"closed_edges": ["C0", "C1"], "lanes_closed": 1},
    )
    results = score(scenario, baseline=baseline)

    assert {r.equation_id for r in results} == {"ECON-1", "ECON-2", "ECON-3"}
    by_id = {r.equation_id: r for r in results}
    assert by_id["ECON-1"].confidence == "M"
    assert by_id["ECON-2"].confidence == "M"
    assert by_id["ECON-3"].confidence == "M"
    assert any("ASPBI" in a or "employment" in a.lower() for a in by_id["ECON-3"].assumptions)
    assert any("places" in a.lower() or "footfall" in a.lower() for a in by_id["ECON-2"].assumptions)
