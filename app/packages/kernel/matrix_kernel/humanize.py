"""Human-readable result translator (CR-010 backend complement).

Transforms raw DimensionResult objects into plain-language summaries that a
non-technical city planner can understand at a glance. This module is the
"glass-box bridge": it never mutates the original result data, only produces
a human-readable interpretation layer that the synthesis LLM consumes.

The frontend already has format.ts + metrics.ts + interpret.ts for presentation;
this module provides the backend equivalent so the LLM synthesis prompt receives
pre-humanized data instead of raw statistical output.

Glass box (PRD-F14): every template is driven by the kernel result's actual value,
equation_id, and confidence — no number is invented. The original DimensionResult
is preserved intact in the DIMENSION_RESULT event; this module only shapes how
the synthesis narrative describes it.
"""
from __future__ import annotations

import math
from typing import Sequence

from matrix_kernel.results import Confidence, DimensionResult


# ── Confidence → plain language ──────────────────────────────────────────────

_CONFIDENCE_WORDS: dict[Confidence, str] = {
    "H": "we're confident in this estimate",
    "M": "a reasonable estimate, treat it as indicative rather than exact",
    "L": "a rough indication only — not precise enough to rank options",
}

_CONFIDENCE_QUALIFIERS: dict[Confidence, str] = {
    "H": "",
    "M": "roughly ",
    "L": "very roughly ",
}


# ── Per-equation human templates ─────────────────────────────────────────────
# Each entry maps an equation_id to a callable that takes (value, lo, hi, unit,
# confidence) and returns a plain-language sentence. Templates are written as
# if explaining to a busy city mayor, not a traffic engineer.

def _abs_val(v: float) -> str:
    """Render |value| with sensible precision."""
    a = abs(v)
    if a == 0:
        return "0"
    if a >= 100:
        return f"{a:,.0f}"
    if a >= 1:
        return f"{a:,.1f}"
    if a >= 0.01:
        return f"{a:.2f}"
    return f"{a:.4f}"


def _direction(v: float) -> str:
    """'more'/'fewer'/'increase'/'decrease' based on sign."""
    return "more" if v > 0 else "fewer" if v < 0 else "about the same"


def _change_word(v: float) -> str:
    return "increase" if v > 0 else "decrease" if v < 0 else "no change"


def _pct(v: float) -> str:
    """Format as percentage: 0.85 → '85%'."""
    return f"{abs(v) * 100:.0f}%"


def _range_sentence(lo: float, hi: float, unit_word: str) -> str:
    """'somewhere between X and Y [unit]'"""
    if lo == hi or (abs(hi - lo) < 0.001):
        return ""
    return f" (somewhere between {_abs_val(lo)} and {_abs_val(hi)} {unit_word})"


# ── Templates keyed by equation_id ───────────────────────────────────────────

def _humanize_beh1(r: DimensionResult) -> str:
    q = _CONFIDENCE_QUALIFIERS[r.confidence]
    if abs(r.value) < 0.5:
        return "There would be no meaningful change in the number of vehicles using this road during the morning rush."
    word = _direction(r.value)
    rng = _range_sentence(r.range[0], r.range[1], "trips")
    return (
        f"About {q}{_abs_val(r.value)} {word} vehicles would use this road "
        f"during the morning rush{rng}."
    )


def _humanize_beh2(r: DimensionResult) -> str:
    if abs(r.value) < 0.1:
        return "No meaningful shift in how people choose to travel (e.g. switching to or from jeepneys) is expected."
    word = "toward" if r.value > 0 else "away from"
    return f"A shift of about {_abs_val(r.value)} percentage points {word} jeepney travel is expected."


def _humanize_beh3(r: DimensionResult) -> str:
    pct = abs(r.value) * 100
    if pct < 0.5:
        return "The road would be essentially empty — well below its capacity."
    if pct > 100:
        return (
            f"The road would be severely over capacity at {pct:.0f}% — "
            "expect significant gridlock and long delays."
        )
    if pct > 85:
        return (
            f"The road would be at {pct:.0f}% of its capacity during rush hour — "
            "congestion is likely, with stop-and-go conditions."
        )
    if pct > 60:
        return (
            f"The road would be at {pct:.0f}% of its capacity during rush hour — "
            "traffic flows but starts to feel busy."
        )
    return (
        f"The road would be at {pct:.0f}% of its capacity during rush hour — "
        "traffic flows freely."
    )


def _humanize_eco1(r: DimensionResult) -> str:
    q = _CONFIDENCE_QUALIFIERS[r.confidence]
    if abs(r.value) < 0.0005:
        return "No meaningful change in transport carbon emissions."
    tonnes = abs(r.value) * 1000  # kt → tonnes
    word = _change_word(r.value)
    if tonnes >= 1:
        return (
            f"Transport carbon emissions would {q}{word} by about "
            f"{tonnes:,.0f} tonnes of CO₂ per year."
        )
    return (
        f"Transport carbon emissions would {q}{word} by about "
        f"{r.value:.4f} kilotonnes of CO₂ per year — a very small amount."
    )


def _humanize_eco2(r: DimensionResult) -> str:
    if abs(r.value) < 0.005:
        return "No meaningful change in local air quality."
    word = "worsens" if r.value > 0 else "improves"
    return (
        f"Local air quality {word} slightly — "
        f"the estimated change is {_abs_val(r.value)} µg/m³ of fine particles."
    )


def _humanize_eco3(r: DimensionResult) -> str:
    if abs(r.value) < 0.05:
        return "No green space (parks, trees, vegetation) would be lost."
    return f"About {_abs_val(r.value)} hectares of green cover would be affected."


def _humanize_eco4(r: DimensionResult) -> str:
    if abs(r.value) < 0.5:
        return "No change in how many people are exposed to flood risk."
    word = _direction(r.value)
    return (
        f"About {_abs_val(r.value)} {word} people would be exposed to flood risk."
    )


def _humanize_soc1(r: DimensionResult) -> str:
    if abs(r.value) < 0.002:
        return "No meaningful change in how fairly people can access jobs and services."
    word = "more fairly" if r.value > 0 else "less fairly"
    return (
        f"Access to jobs and services would be distributed {word} — "
        f"the equity index changes by {_abs_val(r.value)}."
    )


def _humanize_soc2(r: DimensionResult) -> str:
    if abs(r.value) < 0.5:
        return "No residents or informal workers are expected to be displaced."
    return (
        f"About {_abs_val(r.value)} informal vendors or workers could be displaced "
        f"by this change."
    )


def _humanize_soc3(r: DimensionResult) -> str:
    if abs(r.value) < 0.002:
        return "The impact is spread evenly across income groups — no group is hit harder."
    word = "disproportionately affects" if r.value < 0 else "benefits"
    return (
        f"This change {word} lower-income residents — "
        f"the distributional impact index is {_abs_val(r.value)}."
    )


def _humanize_econ1(r: DimensionResult) -> str:
    q = _CONFIDENCE_QUALIFIERS[r.confidence]
    if abs(r.value) < 1:
        return "No meaningful change in nearby land values."
    word = _change_word(r.value)
    # Format as PHP with commas
    return (
        f"Nearby land values (within ~1 km) would {q}{word} by about "
        f"₱{_abs_val(r.value)}."
    )


def _humanize_econ2(r: DimensionResult) -> str:
    q = _CONFIDENCE_QUALIFIERS[r.confidence]
    if abs(r.value) < 0.5:
        return "No meaningful change in foot traffic for local businesses."
    word = _direction(r.value)
    return (
        f"Local businesses would see {q}{_abs_val(r.value)} {word} visitors per day."
    )


def _humanize_econ3(r: DimensionResult) -> str:
    q = _CONFIDENCE_QUALIFIERS[r.confidence]
    if abs(r.value) < 0.1:
        return "No meaningful impact on local jobs."
    word = "gained" if r.value > 0 else "at risk"
    return f"About {q}{_abs_val(r.value)} local jobs could be {word}."


def _humanize_soci1(r: DimensionResult) -> str:
    if r.value >= 65:
        return (
            f"Overall, this scenario scores well for the community — "
            f"{r.value:.0f} out of 100 on the wellbeing index."
        )
    if r.value >= 45:
        return (
            f"Overall, this scenario has a mixed impact on community wellbeing — "
            f"{r.value:.0f} out of 100."
        )
    return (
        f"Overall, this scenario raises concerns for community wellbeing — "
        f"scoring only {r.value:.0f} out of 100."
    )


def _humanize_soci2(r: DimensionResult) -> str:
    if abs(r.value) < 0.02:
        return "No significant effect on nearby heritage or cultural sites."
    word = "additional pressure on" if r.value > 0 else "reduced pressure on"
    return f"This change would put {word} nearby heritage and cultural sites."


def _humanize_soci3(r: DimensionResult) -> str:
    if abs(r.value) < 0.005:
        return "No significant change in health risks for nearby residents."
    word = "increased" if r.value > 0 else "decreased"
    return (
        f"Health-risk exposure for nearby residents would be {word} — "
        f"the proxy index changes by {_abs_val(r.value)}."
    )


def _humanize_soci4(r: DimensionResult) -> str:
    if abs(r.value) < 0.02:
        return "No meaningful change in how walkable the area is."
    word = "more" if r.value > 0 else "less"
    return f"The affected area would become {word} walkable."


_TEMPLATES: dict[str, callable] = {
    "BEH-1": _humanize_beh1,
    "BEH-2": _humanize_beh2,
    "BEH-3": _humanize_beh3,
    "ECO-1": _humanize_eco1,
    "ECO-2": _humanize_eco2,
    "ECO-3": _humanize_eco3,
    "ECO-4": _humanize_eco4,
    "SOC-1": _humanize_soc1,
    "SOC-2": _humanize_soc2,
    "SOC-3": _humanize_soc3,
    "ECON-1": _humanize_econ1,
    "ECON-2": _humanize_econ2,
    "ECON-3": _humanize_econ3,
    "SOCI-1": _humanize_soci1,
    "SOCI-2": _humanize_soci2,
    "SOCI-3": _humanize_soci3,
    "SOCI-4": _humanize_soci4,
}

# ── Dimension-level human labels (mirrors frontend metrics.ts) ───────────────

_DIMENSION_LABELS: dict[str, str] = {
    "behavioral": "Travel & Mobility",
    "ecological": "Environment",
    "social": "Community & Access",
    "economic": "Local Economy",
    "societal": "Equity & Wellbeing",
}


# ── Public API ───────────────────────────────────────────────────────────────

def humanize_result(r: DimensionResult) -> str:
    """One plain-language sentence for a single DimensionResult.

    Falls back to a generic template for unknown equation ids — never returns
    an empty string, never invents a number.
    """
    template = _TEMPLATES.get(r.equation_id)
    if template:
        return template(r)
    # Generic fallback: honest, no jargon
    if abs(r.value) < 1e-9:
        return f"No meaningful change in {r.metric.lower()}."
    word = "increases" if r.value > 0 else "decreases"
    return f"{r.metric} {word} by {_abs_val(r.value)} {r.unit}."


def humanize_results_for_llm(results: Sequence[DimensionResult]) -> str:
    """Build a human-readable brief from all results, grouped by dimension.

    This replaces the raw statistical dump that was previously fed to the
    synthesis LLM. The LLM receives plain-language findings instead of floats,
    confidence letters, and equation codes.

    The equation IDs are still included (in brackets) so the citation guard
    can enforce provenance, but the surrounding language is consumer-friendly.
    """
    if not results:
        return "No results were produced by the simulation."

    # Group by dimension
    by_dim: dict[str, list[DimensionResult]] = {}
    for r in results:
        by_dim.setdefault(r.dimension, []).append(r)

    sections: list[str] = []
    for dim in ["behavioral", "ecological", "social", "economic", "societal"]:
        dim_results = by_dim.get(dim, [])
        if not dim_results:
            continue
        label = _DIMENSION_LABELS.get(dim, dim.title())
        lines = [f"**{label}**"]
        for r in dim_results:
            human_text = humanize_result(r)
            conf_word = _CONFIDENCE_WORDS[r.confidence]
            lines.append(
                f"- [{r.equation_id}] {human_text} "
                f"(Confidence: {conf_word}.)"
            )
        sections.append("\n".join(lines))

    return "\n\n".join(sections)


def humanize_confidence(conf: Confidence) -> str:
    """Plain-language confidence description."""
    return _CONFIDENCE_WORDS[conf]
