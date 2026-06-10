"""Tests for the real validation gates (QAD §8 VAL-01/VAL-02; PRD-F18).

All bare-mode: the gates take INJECTED simulated values, so no SUMO/Redis is needed.
The end-to-end test runs both gate computations against the committed fixtures and
writes + re-validates validation_report.json. The core anti-theater property under
test: gates can FAIL, and a gate that did not run reports NOT_RUN, never a number.
"""
import json
import math
from datetime import datetime

import pytest

from matrix_kernel.validation import (
    CALDERON_FIXTURE,
    FLOOD_FIXTURE,
    PROVISIONAL_MARK,
    VAL01_THRESHOLD_NRMSE,
    VAL02_THRESHOLD_IOU,
    length_weighted_iou,
    load_fixture,
    load_validation_report,
    normalized_rmse,
    rmse,
    run_validation_gates,
    simulated_corridor_flows_from_baseline,
    validate_calderon,
    validate_flood,
    write_validation_report,
)


# ── metric primitives ────────────────────────────────────────────────────────────────

def test_rmse_hand_computed():
    # errors 0 and 2 -> sqrt((0+4)/2) = sqrt(2)
    assert rmse([1.0, 2.0], [1.0, 4.0]) == pytest.approx(math.sqrt(2))


def test_rmse_rejects_unpaired_and_empty():
    with pytest.raises(ValueError):
        rmse([1.0], [1.0, 2.0])
    with pytest.raises(ValueError):
        rmse([], [])


def test_normalized_rmse_hand_computed():
    # rmse = 10, mean observed = 100 -> 0.1
    assert normalized_rmse([110.0, 90.0], [100.0, 100.0]) == pytest.approx(0.1)


def test_normalized_rmse_rejects_zero_mean():
    with pytest.raises(ValueError):
        normalized_rmse([1.0], [0.0])


def test_iou_identical_sets_is_one():
    closed = {"a": 100.0, "b": 50.0}
    assert length_weighted_iou(closed, dict(closed)) == pytest.approx(1.0)


def test_iou_disjoint_sets_is_zero():
    assert length_weighted_iou({"a": 100.0}, {"b": 100.0}) == pytest.approx(0.0)


def test_iou_partial_overlap_hand_computed():
    # intersection = a (100, observed length wins); union = 100 + 50 + 50 = 200
    sim = {"a": 100.0, "c": 50.0}
    obs = {"a": 100.0, "b": 50.0}
    assert length_weighted_iou(sim, obs) == pytest.approx(0.5)


def test_iou_rejects_empty_union_and_bad_lengths():
    with pytest.raises(ValueError):
        length_weighted_iou({}, {})
    with pytest.raises(ValueError):
        length_weighted_iou({"a": 0.0}, {"a": 100.0})


# ── fixtures: provenance honesty ─────────────────────────────────────────────────────

def test_calderon_fixture_is_sourced():
    fx = load_fixture(CALDERON_FIXTURE)
    assert fx["provisional"] is False
    assert "Calderon2014_Iloilo_BRT.pdf" in fx["provenance"]  # traceable to the local copy
    s1 = [p for p in fx["observations"] if p["scenario"] == "scenario1_current"]
    assert len(s1) == 4                                       # 2 corridors x flow/transfer
    for p in fx["observations"]:
        assert p["provenance"]                                # every point cites its figure
        assert float(p["value"]) > 0


def test_flood_fixture_is_clearly_provisional():
    fx = load_fixture(FLOOD_FIXTURE)
    assert fx["provisional"] is True
    assert PROVISIONAL_MARK in fx["provenance"]
    assert all(float(p["length_m"]) > 0 for p in fx["observations"])


# ── VAL-01: Calderon corridor gate ───────────────────────────────────────────────────

def _calderon_sim(factor: float) -> dict[str, float]:
    fx = load_fixture(CALDERON_FIXTURE)
    return {p["id"]: float(p["value"]) * factor
            for p in fx["observations"] if p["scenario"] == "scenario1_current"}


def _expected_nrmse(factor: float) -> float:
    """Analytic NRMSE for sim = obs * factor: |factor-1| * RMS(obs) / mean(obs)."""
    fx = load_fixture(CALDERON_FIXTURE)
    obs = [float(p["value"]) for p in fx["observations"]
           if p["scenario"] == "scenario1_current"]
    rms = math.sqrt(sum(o * o for o in obs) / len(obs))
    return abs(factor - 1.0) * rms / (sum(obs) / len(obs))


def test_calderon_gate_passes_on_close_match():
    gate = validate_calderon(_calderon_sim(1.05), simulated_source="injected:test")
    assert gate.status == "PASS"
    assert gate.value == pytest.approx(_expected_nrmse(1.05), abs=1e-6)
    assert gate.value <= VAL01_THRESHOLD_NRMSE
    assert gate.n_points == 4
    assert gate.details["rmse"] > 0
    assert len(gate.details["pairs"]) == 4                    # every pair published, inspectable


def test_calderon_gate_fails_on_garbage():
    # A gate that cannot fail is theater. 3x the observed volumes must FAIL.
    gate = validate_calderon(_calderon_sim(3.0), simulated_source="injected:test")
    assert gate.status == "FAIL"
    assert gate.value > VAL01_THRESHOLD_NRMSE


def test_calderon_gate_rejects_cherry_picking():
    sim = _calderon_sim(1.0)
    sim.pop("s1_diversion_flow_max")                          # drop an unflattering point
    with pytest.raises(ValueError, match="cherry-picking"):
        validate_calderon(sim, simulated_source="injected:test")


def test_calderon_gate_rejects_unknown_scenario():
    with pytest.raises(ValueError, match="unknown scenario"):
        validate_calderon({}, simulated_source="injected:test", scenario="scenario9_maglev")


# ── VAL-02: flood closure gate ───────────────────────────────────────────────────────

def test_flood_gate_passes_on_full_overlap():
    fx = load_fixture(FLOOD_FIXTURE)
    sim = {p["segment_id"]: float(p["length_m"]) for p in fx["observations"]}
    gate = validate_flood(sim, simulated_source="injected:test")
    assert gate.status == "PASS"
    assert gate.value == pytest.approx(1.0)
    assert gate.fixture_provisional is True                   # placeholder flag survives
    assert PROVISIONAL_MARK in gate.notes                     # ...and is loud on the result


def test_flood_gate_fails_on_disjoint_closures():
    gate = validate_flood({"osm_some_dry_street": 500.0}, simulated_source="injected:test")
    assert gate.status == "FAIL"
    assert gate.value == pytest.approx(0.0)
    assert gate.details["missed_segments"]                    # the misses are named, not hidden


# ── NOT_RUN honesty + live-baseline wrapper ──────────────────────────────────────────

def test_gates_not_run_without_simulated_values():
    report = run_validation_gates()
    assert [g["gate_id"] for g in report["gates"]] == ["VAL-01", "VAL-02"]
    for g in report["gates"]:
        assert g["status"] == "NOT_RUN"
        assert g["value"] is None                             # absence, never a fabricated number
        assert g["simulated_source"] is None
        assert g["notes"]                                     # the reason is stated
        assert g["fixture_provenance"] and g["threshold_provenance"]


def test_live_baseline_wrapper_returns_none_when_unavailable(monkeypatch):
    # Whatever this venv has, an unreachable Redis must yield None (-> NOT_RUN), not a guess.
    monkeypatch.setenv("MATRIX_REDIS_URL", "redis://127.0.0.1:1/0")
    flows = simulated_corridor_flows_from_baseline(
        {"s1_lopez_jaena_flow_max": ["edge1"]}, redis_url="redis://127.0.0.1:1/0")
    assert flows is None


# ── end-to-end: full gate computation -> validation_report.json -> re-validate ──────

def test_report_e2e_write_and_revalidate(tmp_path):
    fx_flood = load_fixture(FLOOD_FIXTURE)
    flood_sim = {p["segment_id"]: float(p["length_m"]) for p in fx_flood["observations"][:4]}
    flood_sim["osm_extra_false_positive"] = 400.0             # imperfect, like reality
    report = run_validation_gates(
        calderon_simulated=_calderon_sim(1.12),
        calderon_source="injected:test-e2e",
        flood_simulated=flood_sim,
        flood_source="injected:test-e2e",
    )

    path = write_validation_report(report, tmp_path / "validation_report.json")
    reloaded = load_validation_report(path)                   # schema re-validated on load

    assert reloaded["schema_version"] == 1
    datetime.fromisoformat(reloaded["generated_at"])          # machine-readable timestamp
    cal, flood = reloaded["gates"]
    assert (cal["gate_id"], flood["gate_id"]) == ("VAL-01", "VAL-02")
    # VAL-01: 12% uniform error -> NRMSE 0.12*RMS/mean (~0.139) <= 0.30 -> PASS,
    # with every pair published.
    assert cal["status"] == "PASS"
    assert cal["value"] == pytest.approx(_expected_nrmse(1.12), abs=1e-6)
    assert cal["fixture_provisional"] is False
    assert len(cal["details"]["pairs"]) == 4
    # VAL-02: exact expected overlap, derived from the fixture (robust to its replacement):
    # intersection = the 4 matched observed lengths; union = all observed + the false positive.
    obs_lengths = [float(p["length_m"]) for p in fx_flood["observations"]]
    expected_iou = sum(obs_lengths[:4]) / (sum(obs_lengths) + 400.0)
    assert flood["value"] == pytest.approx(expected_iou, abs=1e-6)
    assert (flood["status"] == "PASS") is (flood["value"] >= VAL02_THRESHOLD_IOU)
    assert flood["fixture_provisional"] is True
    assert PROVISIONAL_MARK in flood["fixture_provenance"]
    for g in (cal, flood):
        assert g["simulated_source"] == "injected:test-e2e"
        assert g["threshold_provenance"]


def test_report_revalidation_rejects_massaged_gate(tmp_path):
    # Tamper a FAIL into a PASS on disk -> the loader must reject it.
    report = run_validation_gates(
        calderon_simulated=_calderon_sim(3.0), calderon_source="injected:test")
    path = write_validation_report(report, tmp_path / "validation_report.json")
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["gates"][0]["status"] == "FAIL"
    raw["gates"][0]["status"] = "PASS"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="contradicts"):
        load_validation_report(path)
