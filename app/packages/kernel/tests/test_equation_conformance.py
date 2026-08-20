"""Equation conformance suite — Credibility Phase 1 (methods §2 / §3.6)."""
from __future__ import annotations

import pytest

pytest.importorskip(
    "sumo", reason="eclipse-sumo not installed; run `uv sync` in app/packages/kernel"
)

from matrix_kernel.equation_conformance import (
    EQUATION_CONFORMANCE,
    PROVISIONAL_CONSTANTS,
    confidence_within_ceiling,
    requires_low_confidence,
)
from matrix_kernel.modules import behavioral, ecological, economic, social, societal
from matrix_kernel.modules import ecological as eco_mod
from matrix_kernel.modules import economic as econ_mod
from matrix_kernel.modules import social as soc_mod
from matrix_kernel.modules import societal as soci_mod
from matrix_kernel.trajectory import Trajectory


def _sample_traj() -> Trajectory:
    return Trajectory(
        edge_counts={"C0": 20, "C1": 40, "OTHER": 210},
        frames=[],
        meta={"closed_edges": ["C0", "C1"], "lanes_closed": 1},
    )


def _all_scored_results():
    baseline = {"C0": 100, "C1": 50, "OTHER": 200}
    traj = _sample_traj()
    results = []
    results.extend(behavioral.score(traj, baseline=baseline))
    eco = ecological.score(traj, baseline=baseline)
    results.extend(eco)
    eco2 = next(r.value for r in eco if r.equation_id == "ECO-2")
    results.extend(social.score(traj, baseline=baseline))
    results.extend(economic.score(traj, baseline=baseline))
    results.extend(societal.score(traj, baseline=baseline, eco2_val=eco2))
    return results


def test_provisional_constants_match_module_literals():
    assert eco_mod._PM25_PER_CO2E_PROXY == PROVISIONAL_CONSTANTS["_PM25_PER_CO2E_PROXY"]
    assert econ_mod._PHP_PER_TRIP_PROXY == PROVISIONAL_CONSTANTS["_PHP_PER_TRIP_PROXY"]
    assert soc_mod._VENDORS_PER_CLOSED_LANE == PROVISIONAL_CONSTANTS["_VENDORS_PER_CLOSED_LANE"]
    assert soci_mod._GENERIC_POP_DENSITY == PROVISIONAL_CONSTANTS["_GENERIC_POP_DENSITY"]


def test_every_scored_equation_is_in_conformance_ledger():
    scored_ids = {r.equation_id for r in _all_scored_results()}
    assert scored_ids == set(EQUATION_CONFORMANCE)


def test_beh4_scored_when_demand_delta_present_is_in_ledger():
    traj = _sample_traj()
    traj.meta["demand_delta"] = {
        "demand_trips_total": 2700,
        "equation_id": "BEH-4",
        "input_dataset_ids": ["Calderon2014"],
        "confidence": "L",
        "unit": "trips/window",
        "references": ["Calderon2014"],
        "assumptions": ["equation BEH-4"],
    }
    ids = {r.equation_id for r in behavioral.score(traj, baseline={"C0": 100, "C1": 50})}
    assert "BEH-4" in ids
    assert "BEH-4" in EQUATION_CONFORMANCE


def test_conformance_tags_cover_all_ledger_entries():
    allowed = {"equation_backed", "provisional_proxy", "honest_stub", "scalar_standin"}
    for eid, (tag, ceiling) in EQUATION_CONFORMANCE.items():
        assert tag in allowed, eid
        assert ceiling in ("H", "M", "L"), eid


def test_provisional_and_standin_emit_low_confidence():
    by_id = {r.equation_id: r for r in _all_scored_results()}
    for eid, r in by_id.items():
        assert confidence_within_ceiling(r.confidence, eid), (
            f"{eid}: confidence {r.confidence} exceeds ledger ceiling"
        )
        if requires_low_confidence(eid):
            assert r.confidence == "L", f"{eid} must be L ({EQUATION_CONFORMANCE[eid][0]})"
            if r.applicability == "computed":
                assert r.directional is True


def test_glass_box_fields_present_on_every_result():
    for r in _all_scored_results():
        assert r.equation_id
        assert r.input_dataset_ids
        assert r.confidence in ("H", "M", "L")
        assert r.applicability in ("computed", "not_modeled", "not_applicable")
        assert r.range[0] <= r.value <= r.range[1]


def test_unarmed_cards_are_na_not_fake_zeros_at_medium():
    by_id = {r.equation_id: r for r in _all_scored_results()}
    assert by_id["BEH-2"].applicability == "not_modeled"
    assert by_id["BEH-4"].applicability == "not_applicable"
    assert by_id["ECO-3"].applicability == "not_applicable"
    assert by_id["ECO-4"].applicability == "not_applicable"
    assert by_id["BEH-2"].directional is False
    assert by_id["ECO-3"].directional is False
