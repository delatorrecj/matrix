"""Glass-box contract tests -- proves the invariant the auditor enforces.

These pass today: the DimensionResult contract is implemented even though the
modules are still stubs. They guard against a result ever shipping without
provenance. eval-test-runner (SAD-A4) runs these pre-merge.
"""
import pytest

from matrix_kernel.results import DimensionResult


def _valid(**overrides) -> DimensionResult:
    base = dict(
        dimension="behavioral",
        metric="Δ trips/day per corridor",
        equation_id="BEH-1",
        value=1200.0,
        range=(900.0, 1500.0),
        unit="trips/day",
        confidence="H",
        input_dataset_ids=["OSM-ILO", "OVERTURE"],
    )
    base.update(overrides)
    return DimensionResult(**base)


def test_valid_result_constructs():
    r = _valid()
    assert r.equation_id == "BEH-1"
    assert r.directional is False


def test_low_confidence_is_directional():
    # Low confidence must render "directional only", never as precision (PRD-F5).
    assert _valid(confidence="L").directional is True


def test_missing_equation_id_rejected():
    with pytest.raises(ValueError):
        _valid(equation_id="")


def test_missing_datasets_rejected():
    with pytest.raises(ValueError):
        _valid(input_dataset_ids=[])


def test_inverted_range_rejected():
    with pytest.raises(ValueError):
        _valid(range=(1500.0, 900.0))
