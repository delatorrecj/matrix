"""The glass-box contract: one scored number with its full provenance.

No number ships without an equation_id, the datasets it consumed, and a *computed*
confidence. The glass-box-auditor (SAD-A2) rejects any result missing these, and
the invariants below fail fast at construction so a black-box result can never be
built in the first place.

Canonical references:
  - docs/methods-matrix.md  -- equation + provenance ledger (the equation_ids)
  - docs/build-matrix.md    -- golden-path module pattern (this shape)
  - PRD-F14 (glass box), PRD-F5 (confidence-anchored), PRD-F15 (earned range)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Confidence = Literal["H", "M", "L"]
Dimension = Literal["behavioral", "social", "economic", "ecological", "societal"]
Applicability = Literal["computed", "not_modeled", "not_applicable"]
_APPLICABILITY = ("computed", "not_modeled", "not_applicable")


@dataclass(frozen=True)
class DimensionResult:
    """One number, fully traceable. The atomic unit every module emits."""

    dimension: Dimension
    metric: str                       # human label, e.g. "Δ trips/day per corridor"
    equation_id: str                  # methods-matrix §3 id, e.g. "BEH-1"
    value: float
    range: tuple[float, float]        # earned-confidence interval (PRD-F15), not a flat ±%
    unit: str
    confidence: Confidence            # computed via the rubric, never guessed (methods §2)
    input_dataset_ids: list[str]      # INVENTORY ids, e.g. ["OSM-ILO", "OVERTURE"]
    references: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    focus_geometry: dict | None = None # GeoJSON dict for map-synced inspection
    applicability: Applicability = "computed"
    # computed: equation ran for this intervention.
    # not_modeled: equation exists but the kernel does not implement the physics.
    # not_applicable: equation is the wrong tool for this intervention type.

    @property
    def directional(self) -> bool:
        """Low confidence renders 'directional only', never as precision (PRD-F5).

        N/A results are not Low — they are not a measurement at all.
        """
        return self.applicability == "computed" and self.confidence == "L"

    def __post_init__(self) -> None:
        # Glass-box invariants -- fail fast if provenance is missing (PRD-F14).
        if not self.equation_id:
            raise ValueError(f"{self.metric!r}: missing equation_id (glass-box, PRD-F14)")
        if not self.input_dataset_ids:
            raise ValueError(f"{self.metric!r}: missing input_dataset_ids (glass-box, PRD-F14)")
        if self.applicability not in _APPLICABILITY:
            raise ValueError(
                f"{self.metric!r}: unknown applicability {self.applicability!r} "
                f"(expected one of {_APPLICABILITY})"
            )
        lo, hi = self.range
        if lo > hi:
            raise ValueError(f"{self.metric!r}: inverted range lo>hi ({lo} > {hi})")
