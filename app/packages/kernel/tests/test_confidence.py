"""Tests for the confidence rubric + earned-confidence ensemble (U6; methods §2, §5)."""
import random

import pytest

from matrix_kernel.confidence import confidence_rubric, earned_confidence_interval


def test_rubric_high_when_all_high():
    assert confidence_rubric(["OSM-ILO", "OVERTURE"]) == "H"


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
