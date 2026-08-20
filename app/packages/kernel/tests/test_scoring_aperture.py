"""SUMO-free tests for the scoring aperture (site vs impacted network)."""
from matrix_kernel.scoring_aperture import (
    REROUTING_ASSUMPTION,
    impacted_edges,
    network_delta,
    site_delta,
    vkt_delta_km,
    volume_confidence,
)
from matrix_kernel.trajectory import Trajectory


def _traj(**meta) -> Trajectory:
    return Trajectory(
        edge_counts={"SITE": 10, "DET": 80, "OTHER": 5},
        frames=[],
        meta={"affected_edges": ["SITE"], "closed_edges": ["SITE"], **meta},
    )


_BASE = {"SITE": 50, "DET": 20, "OTHER": 5}


def test_site_delta_is_the_edited_edges_only():
    assert site_delta(_traj(), _BASE) == -40.0  # 10 - 50


def test_impacted_edges_are_count_changes_including_detours():
    traj = _traj()
    got = set(impacted_edges(traj, _BASE))
    assert got == {"SITE", "DET"}
    assert "OTHER" not in got


def test_network_delta_includes_displacement():
    # site lost 40, detour gained 60 → net +20 vehicle-entries
    assert network_delta(_traj(), _BASE) == 20.0


def test_explicit_impacted_edges_in_meta_win():
    traj = _traj(impacted_edges=["DET"])
    assert impacted_edges(traj, _BASE) == ["DET"]
    assert network_delta(traj, _BASE) == 60.0


def test_vkt_uses_real_lengths_when_supplied():
    traj = _traj(edge_lengths_km={"SITE": 0.5, "DET": 2.0})
    # SITE: (10-50)*0.5 = -20; DET: (80-20)*2.0 = 120 → 100
    assert vkt_delta_km(traj, _BASE) == 100.0


def test_volume_confidence_caps_at_l_while_val01_fail():
    assert volume_confidence(["SUMO-NET", "WHO-EMEP"], "FAIL") == "L"
    assert volume_confidence(["SUMO-NET", "WHO-EMEP"], "PASS", pass_method="H") == "H"
    assert volume_confidence(["BIR-ZV", "CCHAIN"], "PASS", pass_method="M") == "M"


def test_rerouting_assumption_is_explicit():
    assert "rerouting" in REROUTING_ASSUMPTION.lower()
