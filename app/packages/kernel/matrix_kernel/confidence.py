"""Confidence rubric + earned-confidence ensemble (signatures frozen, impl Phase 3).

confidence_rubric()         -- maps the datasets a module consumed to H/M/L.
                               Confidence is *computed*, never guessed (PRD-F5).
                               Canonical rubric: docs/methods-matrix.md §2.
earned_confidence_interval()-- Monte-Carlo / sensitivity over uncertain assumptions
                               so the *range* is computed (PRD-F15), not a flat ±%.

These stubs exist so Phase 3 modules can import a stable contract today.
"""
from __future__ import annotations

from typing import Callable, Sequence

from matrix_kernel.results import Confidence


def confidence_rubric(input_dataset_ids: Sequence[str]) -> Confidence:
    """Compute the H/M/L tier from the consumed datasets (methods-matrix §2)."""
    raise NotImplementedError("methods-matrix §2 rubric -- Phase 3 (Gate 3)")


def earned_confidence_interval(
    point: float,
    sample: Callable[[], float],
    n: int = 1000,
) -> tuple[float, float]:
    """Sample the uncertain assumptions -> (lo, hi). PRD-F15. Phase 3 (Gate 3)."""
    raise NotImplementedError("earned-confidence ensemble -- Phase 3 (Gate 3)")
