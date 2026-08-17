"""Generate validation_report.json from the live kernel baseline (CR-007 PR 5b; QAD §8).

VAL-01 (Calderon 2014 corridor back-test): maps the two scenario1 ``passenger_flow_max``
corridors to SUMO edges BY STREET NAME (the net now carries names, build_network.py
``--output.street-names``), pulls each corridor's peak per-edge passenger-flow proxy from the
cached nightly baseline, and runs the Calderon RMSE gate. Only ``passenger_flow_max`` is
validated — MATRIX produces edge passenger-flow proxies but models no route transfers, so the
fixture's ``passenger_transfer_max`` points are out of the kernel's scope (not mapped to edge
flows; PRD-F14).

VAL-02 (2024 flood IoU): the `flood_closures_from_geojson` helper is exercised against a placeholder
extent (closure count logged to stderr), but the gate itself stays **NOT_RUN** — there is no real
Sentinel-1 GFM ground-truth extent wired yet, so no IoU is computed. We never fabricate an IoU from a
placeholder-vs-placeholder comparison (PRD-F14); the helper is staged for when real flood data lands.

Run (kernel venv, Redis up with a seeded baseline — `run_nightly_baseline()`):
    uv run python -m matrix_kernel.build_validation_report

Writes ``app/validation_report.json`` (gitignored; served by GET /validation when present, else the
live module reports NOT_RUN). When the baseline/net is unavailable both gates are written NOT_RUN —
never a fabricated number.

STATUS (CR-007 PR 5b / CR-014): against uncalibrated open-data demand the corridor flow proxy
fails the Calderon back-test (live NRMSE published as FAIL vs threshold 0.30). That is a
valid published result — never withheld, never massaged into a pass.

CR-012 WS-1 T1.2 (proxy reconciliation): the proxy now measures peak *transit* passenger flow —
`simulated_corridor_flows_from_baseline` restricts the all-vehicle edge throughput to the
transit-vehicle share (`validation.transit_vehicle_share`, ~13% from the Iloilo anchor) before
applying the jeepney occupancy, which removes ~8x of the over-count (anchor math; unit-tested).

Credibility Phase 1 / CR-012 T1.4: when a Redis baseline exists, `generate()` publishes a live
NRMSE (PASS or honest FAIL) into ``validation_report.json``; API startup regenerates it. Residual
demand-volume gap (T1.3) may still FAIL — that is a valid published result (never massaged).
Without baseline/net the gate stays NOT_RUN with an explicit reason.
"""
from __future__ import annotations

import sys
from pathlib import Path

from matrix_kernel.validation import (
    CALDERON_FIXTURE,
    load_fixture,
    run_validation_gates,
    simulated_corridor_flows_from_baseline,
    flood_closures_from_geojson,
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

    VAL-02: live IoU only when a non-provisional flood fixture exists *and* a sourced
    S1-GFM extent is on disk (MATRIX_FLOOD_EXTENT or data/raw/flood/s1_gfm_iloilo_2024.geojson).
    Otherwise NOT_RUN — never fabricate IoU against the placeholder fixture (PRD-F14).
    """
    import json
    import os
    from matrix_kernel.validation import FLOOD_FIXTURE, load_fixture

    flood_simulated = None
    flood_source = None
    extent_path = os.environ.get("MATRIX_FLOOD_EXTENT")
    default_extent = Path(__file__).resolve().parents[4] / "data" / "raw" / "flood" / "s1_gfm_iloilo_2024.geojson"
    extent = Path(extent_path) if extent_path else default_extent

    try:
        fx = load_fixture(FLOOD_FIXTURE)
        if (not fx.get("provisional")) and extent.is_file():
            raw = json.loads(extent.read_text(encoding="utf-8"))
            if raw.get("type") == "FeatureCollection":
                geom = (raw.get("features") or [{}])[0].get("geometry") or {}
            elif raw.get("type") == "Feature":
                geom = raw.get("geometry") or {}
            else:
                geom = raw
            flood_simulated = flood_closures_from_geojson(geom)
            if flood_simulated:
                flood_source = f"live-flood:geojson-intersect ({extent.name})"
                print(f"[val-02] live IoU path: {len(flood_simulated)} simulated closures",
                      file=sys.stderr)
            else:
                print("[val-02] extent present but intersect empty; VAL-02 -> NOT_RUN",
                      file=sys.stderr)
        else:
            placeholder_flood = {
                "type": "Polygon",
                "coordinates": [[[122.54, 10.70], [122.58, 10.70],
                                 [122.58, 10.74], [122.54, 10.74], [122.54, 10.70]]]
            }
            n = len(flood_closures_from_geojson(placeholder_flood))
            print(f"[val-02] helper staged (placeholder): {n} segments; "
                  "gate stays NOT_RUN until non-provisional S1-GFM fixture + extent",
                  file=sys.stderr)
    except Exception as exc:
        print(f"[val-02] staging failed ({exc}); VAL-02 -> NOT_RUN", file=sys.stderr)

    try:
        mapping = calderon_corridor_edges()
    except Exception as exc:  # net missing/unnamed, bad mapping — honest NOT_RUN
        print(f"[val-01] corridor mapping unavailable ({exc}); VAL-01 -> NOT_RUN", file=sys.stderr)
        return run_validation_gates(
            flood_simulated=flood_simulated, flood_source=flood_source or "")

    flows = simulated_corridor_flows_from_baseline(mapping)
    if flows is None:  # no eclipse-sumo import chain / no Redis / no cached baseline
        print("[val-01] baseline unavailable; VAL-01 -> NOT_RUN", file=sys.stderr)
        return run_validation_gates(
            flood_simulated=flood_simulated, flood_source=flood_source or "")

    print(f"[val-01] simulated corridor flows (live-baseline): "
          + ", ".join(f"{k}={v:.1f}" for k, v in flows.items()))

    return run_validation_gates(
        calderon_simulated=flows,
        calderon_source="live-baseline:redis (peak per-edge transit passenger-flow proxy; "
                        "CR-012 transit-vehicle-share x 14 pax/jeepney)",
        calderon_quantity=VAL01_QUANTITY,
        flood_simulated=flood_simulated,
        flood_source=flood_source or "",
    )


def write_markdown_artifact(report: dict, md_path: Path):
    lines = [
        "# MATRIX Validation Ledger\n",
        f"**Generated:** {report['generated_at']} | **Kernel:** {report['kernel']}\n",
        "| Gate | Description | Status | Value | Threshold |",
        "|---|---|---|---|---|"
    ]
    for g in report["gates"]:
        status = f"**{g['status']}**" if g["status"] != "NOT_RUN" else "*NOT_RUN*"
        val = f"{g['value']} {g['metric']}" if g["value"] is not None else "—"
        lines.append(f"| {g['gate_id']} | {g['name']} | {status} | {val} | {g['comparator']} {g['threshold']} |")
    
    md_path.write_text("\n".join(lines), encoding="utf-8")

def main() -> int:
    report = generate()
    path = write_validation_report(report, REPORT_PATH)
    md_path = REPORT_PATH.with_suffix(".md")
    write_markdown_artifact(report, md_path)
    
    for g in report["gates"]:
        line = f"  {g['gate_id']}: {g['status']}"
        if g["value"] is not None:
            line += f"  {g['metric']}={g['value']} (threshold {g['comparator']} {g['threshold']})"
        print(line)
    print(f"[ok] wrote {path} and {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
