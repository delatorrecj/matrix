"""Generate validation_report.json from the live kernel baseline (CR-007 PR 5b; QAD §8).

VAL-01 (Calderon 2014 corridor back-test): maps the two scenario1 ``passenger_flow_max``
corridors to SUMO edges BY STREET NAME (the net now carries names, build_network.py
``--output.street-names``), pulls each corridor's peak per-edge passenger-flow proxy from the
cached nightly baseline, and runs the Calderon RMSE gate. Only ``passenger_flow_max`` is
validated — MATRIX produces edge passenger-flow proxies but models no route transfers, so the
fixture's ``passenger_transfer_max`` points are out of the kernel's scope (not mapped to edge
flows; PRD-F14).

VAL-02 (2024 flood IoU) stays NOT_RUN: its fixture is PROVISIONAL (no sourced Sentinel-1 extent)
and there is no live flood-closure run wired here.

Run (kernel venv, Redis up with a seeded baseline — `run_nightly_baseline()`):
    uv run python -m matrix_kernel.build_validation_report

Writes ``app/validation_report.json`` (gitignored; served by GET /validation when present, else the
live module reports NOT_RUN). When the baseline/net is unavailable both gates are written NOT_RUN —
never a fabricated number.

STATUS (CR-007 PR 5b): against the current *uncalibrated* synthetic demand, the corridor flow proxy
runs ~an order of magnitude above the Calderon maxima (NRMSE ~12 — a FAIL). That is a mode-share
calibration gap (P1-6) + a proxy/unit reconciliation, NOT a model validation, so the report is
**withheld** (not committed): generate it at deploy once demand is calibrated and the flow proxy is
reconciled. An unvalidated FAIL is not a validation result (PRD-F14).
"""
from __future__ import annotations

import sys
from pathlib import Path

from matrix_kernel.validation import (
    CALDERON_FIXTURE,
    load_fixture,
    run_validation_gates,
    simulated_corridor_flows_from_baseline,
    write_validation_report,
)

# app/ root: build_validation_report.py -> matrix_kernel -> kernel -> packages -> app
APP_ROOT = Path(__file__).resolve().parents[3]
REPORT_PATH = APP_ROOT / "validation_report.json"

# Calderon corridor key -> the OSM/SUMO street name that carries it. SOURCED from the
# regenerated named net (build_network.py --output.street-names) cross-checked against
# Iloilo street naming: the paper's "Diversion Road" is officially "Benigno S. Aquino Jr.
# Avenue" in OSM (the Iloilo diversion/by-pass corridor); "Lopez-Jaena St" is "Lopez Jaena
# Street". A corridor that resolves to NO named edge is left unmapped so the gate reports
# NOT_RUN rather than a silent zero.
CALDERON_CORRIDOR_STREETS: dict[str, str] = {
    "lopez_jaena": "Lopez Jaena Street",
    "diversion": "Benigno S. Aquino Jr. Avenue",
}

VAL01_QUANTITY = "passenger_flow_max"
VAL01_SCENARIO = "scenario1_current"


def calderon_corridor_edges(
    *, scenario: str = VAL01_SCENARIO, quantity: str = VAL01_QUANTITY
) -> dict[str, list[str]]:
    """Fixture obs id -> SUMO edge ids, by resolving each corridor's street name against the
    named net. Raises if a corridor has no street mapping or resolves to no edge (an honest
    failure -> the caller reports NOT_RUN, never a silent zero)."""
    from matrix_kernel.runner import _keyword_edges  # lazy: pulls the SUMO import chain

    fx = load_fixture(CALDERON_FIXTURE)
    mapping: dict[str, list[str]] = {}
    for p in fx["observations"]:
        if p["scenario"] != scenario or p.get("quantity") != quantity:
            continue
        corridor = p["corridor"]
        street = CALDERON_CORRIDOR_STREETS.get(corridor)
        if not street:
            raise KeyError(f"no street mapping for Calderon corridor {corridor!r}")
        edges = _keyword_edges(street)
        if not edges:
            raise ValueError(
                f"corridor {corridor!r} ({street!r}) resolved to no named edge — "
                "regenerate the net with --output.street-names, or fix the street name"
            )
        mapping[p["id"]] = edges
    return mapping


def generate() -> dict:
    """Build the report dict: live VAL-01 if the net+baseline are available, else NOT_RUN.
    VAL-02 is always NOT_RUN here (PROVISIONAL fixture / no live flood run)."""
    try:
        mapping = calderon_corridor_edges()
    except Exception as exc:  # net missing/unnamed, bad mapping — honest NOT_RUN
        print(f"[val-01] corridor mapping unavailable ({exc}); VAL-01 -> NOT_RUN", file=sys.stderr)
        return run_validation_gates()

    flows = simulated_corridor_flows_from_baseline(mapping)
    if flows is None:  # no eclipse-sumo import chain / no Redis / no cached baseline
        print("[val-01] baseline unavailable; VAL-01 -> NOT_RUN", file=sys.stderr)
        return run_validation_gates()

    print(f"[val-01] simulated corridor flows (live-baseline): "
          + ", ".join(f"{k}={v:.1f}" for k, v in flows.items()))
    return run_validation_gates(
        calderon_simulated=flows,
        calderon_source="live-baseline:redis (peak per-edge veh/h x 14 pax/veh proxy)",
        calderon_quantity=VAL01_QUANTITY,
    )


def main() -> int:
    report = generate()
    path = write_validation_report(report, REPORT_PATH)
    for g in report["gates"]:
        line = f"  {g['gate_id']}: {g['status']}"
        if g["value"] is not None:
            line += f"  {g['metric']}={g['value']} (threshold {g['comparator']} {g['threshold']})"
        print(line)
    print(f"[ok] wrote {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
