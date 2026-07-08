"""Rule-based alternative scenario generator (minimal prototype).

Given a scored primary scenario and its results, generates 1-2 alternative
Scenario objects that represent plausible, potentially better interventions.
The alternatives are deterministic (rule-based), not LLM-generated, so they
are fast and reproducible.

The rules follow a simple inversion/softening strategy:
  - full_closure  → suggest lane_closure (partial) + speed_change (calming)
  - lane_closure  → suggest speed_change (calming) + full_closure (if congestion low)
  - speed_change  → suggest capacity_change (widening)
  - capacity_change → suggest speed_change (calming)

Each alternative includes a rationale explaining why it might be better, derived
from the primary scenario's results (never invented).

Glass box (PRD-F14): every alternative declares its rationale and the specific
result that triggered the suggestion. The alternative is a valid Scenario object
that can be simulated through the same kernel pipeline.

Usage:
    from matrix_kernel.alternatives import generate_alternatives
    alts = generate_alternatives(primary_scenario, primary_results)
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Sequence

from matrix_kernel.results import DimensionResult
from matrix_kernel.scenario import Scenario


@dataclass(frozen=True)
class AlternativeSuggestion:
    """A suggested alternative scenario with its rationale."""
    scenario: Scenario
    rationale: str                        # why this might be better
    triggered_by: str                     # equation_id of the finding that triggered this
    improvement_area: str                 # which dimension this aims to improve
    comparison_hint: str                  # e.g. "Reduces traffic impact while keeping road open"

    def as_dict(self) -> dict:
        return {
            "scenario_id": self.scenario.scenario_id,
            "description": self.scenario.description,
            "intervention_type": self.scenario.intervention_type,
            "location": self.scenario.effective_location,
            "rationale": self.rationale,
            "triggered_by": self.triggered_by,
            "improvement_area": self.improvement_area,
            "comparison_hint": self.comparison_hint,
            "parameters": self.scenario.effective_parameters(),
        }


# ── Result analysis helpers ──────────────────────────────────────────────────

def _find_result(results: Sequence[DimensionResult], eq_id: str) -> DimensionResult | None:
    return next((r for r in results if r.equation_id == eq_id), None)


def _is_congested(results: Sequence[DimensionResult]) -> bool:
    """BEH-3 V/C > 0.7 = starting to get busy."""
    beh3 = _find_result(results, "BEH-3")
    return beh3 is not None and beh3.value > 0.7


def _has_displacement(results: Sequence[DimensionResult]) -> bool:
    """SOC-2 displacement > 0."""
    soc2 = _find_result(results, "SOC-2")
    return soc2 is not None and soc2.value > 0


def _has_economic_loss(results: Sequence[DimensionResult]) -> bool:
    """ECON-2 footfall delta is negative (fewer visitors)."""
    econ2 = _find_result(results, "ECON-2")
    return econ2 is not None and econ2.value < -0.5


def _has_emissions_increase(results: Sequence[DimensionResult]) -> bool:
    """ECO-1 emissions increase."""
    eco1 = _find_result(results, "ECO-1")
    return eco1 is not None and eco1.value > 0.0005


# ── Alternative generators per intervention type ─────────────────────────────

def _alt_id() -> str:
    return f"alt-{uuid.uuid4().hex[:8]}"


def _alternatives_for_full_closure(
    primary: Scenario, results: Sequence[DimensionResult]
) -> list[AlternativeSuggestion]:
    alts: list[AlternativeSuggestion] = []
    loc = primary.effective_location

    # Alternative 1: Partial closure (1 lane) instead of full
    alts.append(AlternativeSuggestion(
        scenario=Scenario(
            scenario_id=_alt_id(),
            description=f"Partial closure of {loc or 'the road'} — close 1 lane instead of the full road",
            corridor=primary.corridor,
            lanes_closed=1,
            intervention_type="lane_closure",
            location=primary.location,
            geometry=primary.geometry,
            parameters={"lanes_closed": 1},
        ),
        rationale=(
            "Closing only one lane instead of the full road keeps the corridor partially "
            "open for through traffic and local businesses, reducing displacement and "
            "economic impact while still achieving the intervention goal."
        ),
        triggered_by="SOC-2" if _has_displacement(results) else "BEH-1",
        improvement_area="economic" if _has_economic_loss(results) else "social",
        comparison_hint="Keeps the road partially open — less disruption for businesses and commuters",
    ))

    # Alternative 2: Speed calming on the corridor
    alts.append(AlternativeSuggestion(
        scenario=Scenario(
            scenario_id=_alt_id(),
            description=f"Traffic calming on {loc or 'the road'} — reduce speed to 20 km/h instead of closing",
            corridor=primary.corridor,
            lanes_closed=0,
            intervention_type="speed_change",
            location=primary.location,
            geometry=primary.geometry,
            parameters={"max_speed_kph": 20.0},
        ),
        rationale=(
            "A 20 km/h speed limit achieves pedestrian safety and event-friendly conditions "
            "without fully blocking the road. Traffic flows slowly through, keeping access "
            "for emergency vehicles and local businesses."
        ),
        triggered_by="ECON-2" if _has_economic_loss(results) else "BEH-3",
        improvement_area="economic",
        comparison_hint="Road stays open at walking pace — safer but less disruptive",
    ))

    return alts


def _alternatives_for_lane_closure(
    primary: Scenario, results: Sequence[DimensionResult]
) -> list[AlternativeSuggestion]:
    alts: list[AlternativeSuggestion] = []
    loc = primary.effective_location

    # Alternative 1: Speed calming instead of lane closure
    alts.append(AlternativeSuggestion(
        scenario=Scenario(
            scenario_id=_alt_id(),
            description=f"Speed reduction on {loc or 'the road'} — 30 km/h limit instead of closing lanes",
            corridor=primary.corridor,
            lanes_closed=0,
            intervention_type="speed_change",
            location=primary.location,
            geometry=primary.geometry,
            parameters={"max_speed_kph": 30.0},
        ),
        rationale=(
            "A speed limit reduction achieves traffic calming without reducing road capacity. "
            "This avoids displacing vendors and keeps all lanes open for through traffic."
        ),
        triggered_by="SOC-2" if _has_displacement(results) else "BEH-3",
        improvement_area="social" if _has_displacement(results) else "behavioral",
        comparison_hint="All lanes stay open — calmer traffic without capacity loss",
    ))

    # Alternative 2: Only suggest full closure if congestion is low (road underused)
    if not _is_congested(results):
        alts.append(AlternativeSuggestion(
            scenario=Scenario(
                scenario_id=_alt_id(),
                description=f"Full pedestrianization of {loc or 'the road'} — close entirely to vehicles",
                corridor=primary.corridor,
                lanes_closed=primary.lanes_closed,
                intervention_type="full_closure",
                location=primary.location,
                geometry=primary.geometry,
                parameters={},
            ),
            rationale=(
                "The road is currently not heavily used by vehicles. A full pedestrianization "
                "could create public space, boost foot traffic for businesses, and improve "
                "walkability with minimal traffic disruption."
            ),
            triggered_by="BEH-3",
            improvement_area="societal",
            comparison_hint="Creates public space — viable because the road isn't heavily used",
        ))

    return alts


def _alternatives_for_speed_change(
    primary: Scenario, results: Sequence[DimensionResult]
) -> list[AlternativeSuggestion]:
    alts: list[AlternativeSuggestion] = []
    loc = primary.effective_location

    # Alternative: Road widening (capacity change) if congestion is the concern
    alts.append(AlternativeSuggestion(
        scenario=Scenario(
            scenario_id=_alt_id(),
            description=f"Widen {loc or 'the road'} — add capacity (+30%) instead of changing speed",
            corridor=primary.corridor,
            lanes_closed=0,
            intervention_type="capacity_change",
            location=primary.location,
            geometry=primary.geometry,
            parameters={"capacity_factor": 1.3},
        ),
        rationale=(
            "If the goal is to improve traffic flow, adding road capacity (e.g. widening, "
            "adding a lane, or removing parking) may be more effective than a speed change, "
            "which can increase congestion on narrow corridors."
        ),
        triggered_by="BEH-3" if _is_congested(results) else "BEH-1",
        improvement_area="behavioral",
        comparison_hint="More road capacity instead of slower speeds",
    ))

    return alts


def _alternatives_for_capacity_change(
    primary: Scenario, results: Sequence[DimensionResult]
) -> list[AlternativeSuggestion]:
    alts: list[AlternativeSuggestion] = []
    loc = primary.effective_location

    # Alternative: Traffic calming instead of capacity expansion
    alts.append(AlternativeSuggestion(
        scenario=Scenario(
            scenario_id=_alt_id(),
            description=f"Traffic calming on {loc or 'the road'} — 30 km/h limit instead of widening",
            corridor=primary.corridor,
            lanes_closed=0,
            intervention_type="speed_change",
            location=primary.location,
            geometry=primary.geometry,
            parameters={"max_speed_kph": 30.0},
        ),
        rationale=(
            "Instead of expanding road capacity (which can induce more traffic over time), "
            "traffic calming makes the road safer and more walkable. Research shows that "
            "widening roads often leads to more vehicles, not less congestion."
        ),
        triggered_by="ECO-1" if _has_emissions_increase(results) else "SOCI-4",
        improvement_area="ecological" if _has_emissions_increase(results) else "societal",
        comparison_hint="Safer road without induced traffic demand from widening",
    ))

    return alts


_GENERATORS = {
    "full_closure": _alternatives_for_full_closure,
    "lane_closure": _alternatives_for_lane_closure,
    "speed_change": _alternatives_for_speed_change,
    "capacity_change": _alternatives_for_capacity_change,
}


# ── Public API ───────────────────────────────────────────────────────────────

def generate_alternatives(
    scenario: Scenario,
    results: Sequence[DimensionResult],
    max_alternatives: int = 2,
) -> list[AlternativeSuggestion]:
    """Generate rule-based alternative scenarios from the primary run's results.

    Returns up to `max_alternatives` suggestions, each a valid Scenario that can
    be simulated through the same kernel pipeline. The alternatives are deterministic
    (no LLM, no randomness) and fast (< 1 ms).

    Glass box (PRD-F14): every alternative declares its rationale, the triggering
    result, and what it aims to improve. The rationale is derived from the primary
    run's actual results, never invented.
    """
    generator = _GENERATORS.get(scenario.intervention_type)
    if generator is None:
        return []
    alts = generator(scenario, results)
    return alts[:max_alternatives]
