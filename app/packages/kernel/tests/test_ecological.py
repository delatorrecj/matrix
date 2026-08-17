"""Tests for Ecological module."""
import pytest

# modules.ecological -> baseline -> sumo_env needs the eclipse-sumo wheel at import;
# skip cleanly on a bare venv instead of erroring at collection (`uv sync` runs it).
pytest.importorskip("sumo", reason="eclipse-sumo not installed; run `uv sync` in app/packages/kernel")

from matrix_kernel.modules.ecological import score
from matrix_kernel.trajectory import Trajectory

def test_ecological_results():
    baseline = {"C0": 100, "C1": 50, "OTHER": 200}
    scenario = Trajectory(
        edge_counts={"C0": 20, "C1": 40, "OTHER": 210},
        frames=[],
        meta={"closed_edges": ["C0", "C1"], "lanes_closed": 1},
    )
    results = score(scenario, baseline=baseline)

    assert {r.equation_id for r in results} == {"ECO-1", "ECO-2", "ECO-3", "ECO-4"}
    for r in results:
        assert r.dimension == "ecological"
        assert r.equation_id and r.input_dataset_ids
        assert r.range[0] <= r.value <= r.range[1]

    by_id = {r.equation_id: r for r in results}
    # ECO-2 uses §3.6 PROVISIONAL _PM25_PER_CO2E_PROXY → L (methods §2 low-confidence protocol).
    # ECO-4 keeps literature method-cap at M (hazard inputs H, redistribution method M).
    assert by_id["ECO-2"].confidence == "L"
    assert by_id["ECO-2"].directional is True
    assert by_id["ECO-4"].confidence == "M"
    assert by_id["ECO-4"].value == 0.0  # lane closure without flood_hazard
    # The ECO-2 PM2.5∝CO2e proxy constant surfaces its provenance under Inspect (PRD-F14).
    eco2_assumptions = " ".join(by_id["ECO-2"].assumptions)
    assert "PROVISIONAL" in eco2_assumptions and "0.05" in eco2_assumptions


def test_eco4_flood_uses_cchain():
    baseline = {"C0": 100}
    scenario = Trajectory(
        edge_counts={"C0": 80},
        frames=[],
        meta={"closed_edges": ["C0", "C1", "C2"], "flood_hazard": True},
    )
    eco4 = next(r for r in score(scenario, baseline=baseline) if r.equation_id == "ECO-4")
    assert eco4.value > 0
    assert eco4.confidence == "M"
    assert any("NOAH" in a or "flood" in a.lower() for a in eco4.assumptions)
