"""Tests for the confidence rubric + earned-confidence ensemble (U6; methods §2, §5)."""
import random

import pytest

from matrix_kernel.confidence import (
    confidence_rubric,
    earned_confidence_interval,
    method_capped_confidence,
    provisional_capped_confidence,
)


def test_rubric_high_when_all_high():
    assert confidence_rubric(["OSM-ILO", "OVERTURE"]) == "H"


def test_newly_registered_dataset_tiers():
    # These five ids were previously unregistered -> silently demoted to L, making
    # ECO-2/ECO-4/SOC-1/SOCI-3 emit L while methods §3 documents M/H. Tiers come from the
    # data/INVENTORY.md Conf column: EMB/LIPAD/DEM/NHFR = H (live/registry), S5P-NO2 = M (proxy).
    assert confidence_rubric(["EMB"]) == "H"
    assert confidence_rubric(["LIPAD"]) == "H"
    assert confidence_rubric(["DEM"]) == "H"
    assert confidence_rubric(["NHFR"]) == "H"
    assert confidence_rubric(["S5P-NO2"]) == "M"


def test_method_capped_takes_worst_of_data_and_method():
    # Data is H, method maturity is M -> result is M (methods §2 worst-factor rule).
    assert method_capped_confidence(["CCHAIN", "LIPAD", "DEM"], "M") == "M"
    # A method ceiling never *raises* a weaker data tier.
    assert method_capped_confidence(["S5P-NO2"], "H") == "M"
    # Equal factors pass through.
    assert method_capped_confidence(["OSM-ILO"], "H") == "H"


def test_provisional_capped_always_low():
    # §3.6 PROVISIONAL constants force L even when every input dataset is H (methods §2).
    assert provisional_capped_confidence(["EMB", "S5P-NO2"]) == "L"
    assert provisional_capped_confidence(["BIR-ZV", "CCHAIN"]) == "L"
    assert provisional_capped_confidence(["CCHAIN", "OSM-ILO"]) == "L"
    assert provisional_capped_confidence(["OSM-ILO", "OVERTURE"]) == "L"


def test_rubric_worst_factor_caps():
    # Calderon2014 (M) caps an otherwise-High set (methods §2 worst-factor rule) -> BEH-2 = M.
    assert confidence_rubric(["PERSONA-POOL", "Calderon2014", "CCHAIN"]) == "M"


def test_rubric_unknown_dataset_is_low():
    # Unprovenanced data cannot earn confidence -> Low (directional only).
    assert confidence_rubric(["OSM-ILO", "SOMETHING-UNTRACED"]) == "L"


def test_rubric_empty_rejected():
    with pytest.raises(ValueError):
        confidence_rubric([])


def test_ensemble_brackets_point_and_is_nondegenerate():
    rng = random.Random(42)
    point = 10.0
    lo, hi = earned_confidence_interval(point, lambda: point + rng.uniform(-2, 2), n=500)
    assert lo <= point <= hi
    assert lo < hi


def test_ensemble_zero_variance_collapses_to_point():
    lo, hi = earned_confidence_interval(5.0, lambda: 5.0, n=100)
    assert lo == 5.0 == hi
