"""Tests for Social module."""
import pytest

# modules.social -> baseline -> sumo_env needs the eclipse-sumo wheel at import;
# skip cleanly on a bare venv instead of erroring at collection (`uv sync` runs it).
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
    # SOC-1 (CCHAIN + NHFR, both H, but equity-weighted access is literature-calibrated)
    # now emits the M methods §3.3 documents — previously L because NHFR was unregistered.
    assert by_id["SOC-1"].confidence == "M"
    # The SOC-2 vendors-per-lane proxy constant surfaces its provenance under Inspect (PRD-F14).
    soc2_assumptions = " ".join(by_id["SOC-2"].assumptions)
    assert "PROVISIONAL" in soc2_assumptions and "12" in soc2_assumptions
