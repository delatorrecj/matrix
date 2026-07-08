"""Tests for humanize.py consumer-friendly result translation."""
from matrix_kernel.humanize import humanize_result, humanize_results_for_llm
from matrix_kernel.results import DimensionResult


def test_humanize_beh1():
    r = DimensionResult(
        dimension="behavioral",
        metric="Trips on affected corridor",
        equation_id="BEH-1",
        value=-450.0,
        range=(-500.0, -400.0),
        unit="trips",
        confidence="H",
        input_dataset_ids=["SUMO-NET"],
        references=[],
        assumptions=[],
    )
    text = humanize_result(r)
    assert "450" in text
    assert "fewer vehicles" in text
    assert "somewhere between 500 and 400 trips" in text


def test_humanize_beh3_over_capacity():
    r = DimensionResult(
        dimension="behavioral",
        metric="Peak V/C ratio",
        equation_id="BEH-3",
        value=1.15,
        range=(1.1, 1.2),
        unit="ratio",
        confidence="M",
        input_dataset_ids=["SUMO-NET"],
        references=[],
        assumptions=[],
    )
    text = humanize_result(r)
    assert "115%" in text
    assert "gridlock" in text


def test_humanize_results_for_llm():
    r1 = DimensionResult(
        dimension="behavioral",
        metric="Trips on affected corridor",
        equation_id="BEH-1",
        value=-450.0,
        range=(-500.0, -400.0),
        unit="trips",
        confidence="H",
        input_dataset_ids=["SUMO-NET"],
        references=[],
        assumptions=[],
    )
    r2 = DimensionResult(
        dimension="economic",
        metric="Footfall Δ per zone",
        equation_id="ECON-2",
        value=120.0,
        range=(100.0, 140.0),
        unit="visits/day",
        confidence="M",
        input_dataset_ids=["OVERTURE"],
        references=[],
        assumptions=[],
    )
    brief = humanize_results_for_llm([r1, r2])
    assert "[BEH-1]" in brief
    assert "[ECON-2]" in brief
    assert "**Travel & Mobility**" in brief
    assert "**Local Economy**" in brief
