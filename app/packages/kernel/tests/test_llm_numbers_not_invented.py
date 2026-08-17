"""Prove LLM synthesis cannot invent magnitudes (Credibility Phase 1 / PRD-F14)."""
from __future__ import annotations

import re

import pytest

from matrix_kernel.citation_guard import strip_uncited_claims
from matrix_kernel.results import DimensionResult
from matrix_kernel.synthesis import synthesize

_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def _kernel_results() -> list[DimensionResult]:
    return [
        DimensionResult(
            dimension="behavioral",
            metric="Δ trips",
            equation_id="BEH-1",
            value=-14.0,
            range=(-20.0, -8.0),
            unit="trips",
            confidence="H",
            input_dataset_ids=["OSM-ILO", "OVERTURE", "PERSONA-POOL"],
            references=[],
            assumptions=[],
        ),
        DimensionResult(
            dimension="ecological",
            metric="CO2e",
            equation_id="ECO-1",
            value=1.25,
            range=(1.0, 1.5),
            unit="ktCO2e/yr",
            confidence="H",
            input_dataset_ids=["SUMO-NET", "WHO-EMEP"],
            references=["WHO-EMEP"],
            assumptions=[],
        ),
    ]


def test_strip_uncited_drops_invented_magnitude():
    results = _kernel_results()
    valid = {r.equation_id for r in results}
    datasets = {r.equation_id: list(r.input_dataset_ids) for r in results}
    narrative = (
        "Trips fell by 14 [BEH-1]. "
        "Also, mysteriously, 99999 jobs appear overnight."
    )
    safe = strip_uncited_claims(narrative, valid, datasets)
    assert "14" in safe
    assert "[BEH-1]" in safe
    assert "99999" not in safe


def test_cited_kernel_magnitudes_survive():
    results = _kernel_results()
    valid = {r.equation_id for r in results}
    datasets = {r.equation_id: list(r.input_dataset_ids) for r in results}
    narrative = "Trips fell by 14 [BEH-1]. Emissions rise by 1.25 [ECO-1]."
    safe = strip_uncited_claims(narrative, valid, datasets)
    nums = {float(m.group()) for m in _NUM.finditer(re.sub(r"\[[^\]]+\]", "", safe))}
    # Narration may omit the sign ("fell by 14" for value -14); compare absolutes.
    kernel_abs = {abs(r.value) for r in results}
    assert {abs(n) for n in nums} <= kernel_abs


def test_synthesize_without_llm_does_not_invent_scores(monkeypatch):
    """When Azure is unavailable, synthesize returns placeholder — never fabricated scores."""
    from matrix_kernel import llm as llm_mod
    from matrix_kernel import synthesis as syn_mod

    def _boom(*_a, **_k):
        raise llm_mod.LLMUnavailable("forced", attempts=1)

    monkeypatch.setattr(syn_mod, "make_client", _boom)
    results = _kernel_results()
    narrative, citations = synthesize(results, client=None)
    assert "failed" in narrative.lower() or "blocked" in narrative.lower() or "raw data" in narrative.lower()
    # No invented numeric claims with fake equation ids
    assert "99999" not in narrative
    assert citations == [] or all(c["equation_id"] in {"BEH-1", "ECO-1"} for c in citations)


def test_kernel_score_values_are_deterministic_source_of_truth():
    """Module scores are the only numeric source before synthesis (API streams them first)."""
    pytest.importorskip(
        "sumo", reason="eclipse-sumo not installed; run `uv sync` in app/packages/kernel"
    )
    from matrix_kernel.modules import behavioral, ecological
    from matrix_kernel.trajectory import Trajectory

    baseline = {"C0": 100, "C1": 50}
    traj = Trajectory(
        edge_counts={"C0": 20, "C1": 40},
        frames=[],
        meta={"closed_edges": ["C0", "C1"], "lanes_closed": 1},
    )
    scored = behavioral.score(traj, baseline=baseline) + ecological.score(traj, baseline=baseline)
    # Every result is a DimensionResult with equation_id — synthesis may only narrate these.
    assert all(r.equation_id and r.input_dataset_ids for r in scored)
    values = {r.equation_id: r.value for r in scored}
    # Re-score: deterministic for fixed RNG seeds inside modules
    scored2 = behavioral.score(traj, baseline=baseline) + ecological.score(traj, baseline=baseline)
    values2 = {r.equation_id: r.value for r in scored2}
    assert values == values2
