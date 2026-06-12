"""Validation gates (QAD §8 VAL-01/VAL-02; PRD-F18) -- computed, never hardcoded.

Replaces the validation-theater stubs (static RMSE/IoU that PASSed by construction)
with real back-test computations:

  VAL-01  Calderon 2014 corridor back-test -- RMSE (+ normalized RMSE) between MATRIX
          corridor values and the published Calderon et al. (2014, TSSP) JICA STRADA 3
          transit-model values for the two Ungka-Iloilo corridors. Fixture is SOURCED
          from the paper (data/raw/literature/Calderon2014_Iloilo_BRT.pdf, LIT-CALDERON).
  VAL-02  2024 Iloilo flood back-test -- length-weighted spatial IoU between simulated
          flood closures and recorded 2024 closures. Fixture is PROVISIONAL until the
          Copernicus GFM Sentinel-1 extent is acquired (INVENTORY id S1-GFM, status ⏳).

The glass-box rules (PRD-F14) apply to validation itself:
  - every gate value is COMPUTED here from fixture data, with fixture + threshold
    provenance attached to the result;
  - a FAIL is reported as FAIL -- a gate is never massaged to pass;
  - a gate with no simulated input is NOT_RUN (with the reason), never fabricated.

Simulated values are INJECTED as plain mappings so the gates run without SUMO/Redis
(unit tests, CI); `simulated_corridor_flows_from_baseline` is the thin convenience
that pulls them from the cached nightly baseline when one is available. The output
is a machine-readable report (`validation_report.json`) for the API/UI to serve.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Mapping, Sequence

GateStatus = Literal["PASS", "FAIL", "NOT_RUN"]

FIXTURE_DIR = Path(__file__).resolve().parent / "validation_fixtures"
CALDERON_FIXTURE = FIXTURE_DIR / "calderon2014_corridor.json"
FLOOD_FIXTURE = FIXTURE_DIR / "flood2024_closures.json"
# Regenerable artifact -> kernel .tmp (gitignored); the API serves it or regenerates.
DEFAULT_REPORT_PATH = Path(__file__).resolve().parent.parent / ".tmp" / "validation_report.json"

REPORT_SCHEMA_VERSION = 1
# Every provisional fixture must carry this exact marker in its provenance string so
# a placeholder can never be mistaken for ground truth (and the report re-validator
# rejects a provisional fixture that drops it).
PROVISIONAL_MARK = "PROVISIONAL — replace with sourced data"

# ── Documented thresholds (QAD §8 names the gates but recorded no numbers; the old
#    stub's RMSE<=200 and the UI's NRMSE<0.15 both had no recorded provenance. These
#    are the documented values, with provenance, pending QAD ratification.) ─────────
VAL01_THRESHOLD_NRMSE = 0.30
VAL01_THRESHOLD_PROVENANCE = (
    "Normalized RMSE (RMSE / mean observed) <= 0.30: %RMSE of ~30% is a customary "
    "acceptance band for arterial corridor volumes in travel-model validation practice "
    "(FHWA Travel Model Validation and Reasonableness Checking Manual, 2nd ed., 2010). "
    "Documented here pending QAD ratification; supersedes the unprovenanced stub "
    "threshold (RMSE<=200 pax) and the UI placeholder (<0.15)."
)
VAL02_THRESHOLD_IOU = 0.50
VAL02_THRESHOLD_PROVENANCE = (
    "Length-weighted IoU >= 0.50: binary flood-extent skill scores (F-statistic / CSI) "
    "of ~0.5-0.7 are the published range for calibrated inundation models (Horritt & "
    "Bates 2002, J. Hydrology 268). Adopted at the conservative entry of that band, "
    "pending QAD ratification; supersedes the unprovenanced stub threshold (0.75)."
)

# Single source for each gate's display identity (used by both the computed and the
# NOT_RUN paths -- one name per gate, no copy-paste drift).
_VAL01_NAME = "Behavioral corridor back-test (Calderon 2014, Ungka–Iloilo corridors)"
_VAL01_UNIT = "fraction of mean observed volume"
_VAL02_NAME = "Flood redistribution back-test (2024 Iloilo flood closures)"
_VAL02_UNIT = "IoU over closed road segments (0–1)"


# ── Metric primitives (pure, hand-checkable) ────────────────────────────────────────

def rmse(simulated: Sequence[float], observed: Sequence[float]) -> float:
    """Root-mean-square error over paired (simulated, observed) values."""
    if len(simulated) != len(observed):
        raise ValueError(f"rmse: unpaired inputs ({len(simulated)} vs {len(observed)})")
    if not observed:
        raise ValueError("rmse: no observation points — a gate cannot run on nothing")
    return math.sqrt(sum((s - o) ** 2 for s, o in zip(simulated, observed)) / len(observed))


def normalized_rmse(simulated: Sequence[float], observed: Sequence[float]) -> float:
    """RMSE normalized by the mean |observed| value (scale-free, comparable across corridors)."""
    mean_obs = sum(abs(o) for o in observed) / len(observed) if observed else 0.0
    if mean_obs <= 0.0:
        raise ValueError("normalized_rmse: mean |observed| is 0 — cannot normalize")
    return rmse(simulated, observed) / mean_obs


def length_weighted_iou(
    simulated: Mapping[str, float], observed: Mapping[str, float]
) -> float:
    """Spatial overlap of two closed-road-segment sets: Σlen(∩) / Σlen(∪).

    Both sides map segment_id -> length_m. Where a segment appears on both sides the
    observed (ground-truth) length is authoritative. Weighting by length makes a missed
    1.5 km arterial closure cost more than a missed 100 m side street.
    """
    for side, lengths in (("simulated", simulated), ("observed", observed)):
        bad = [k for k, v in lengths.items() if not v > 0.0]
        if bad:
            raise ValueError(f"length_weighted_iou: non-positive length(s) in {side}: {bad}")
    union = dict(simulated) | dict(observed)  # observed wins on shared ids
    if not union:
        raise ValueError("length_weighted_iou: both segment sets empty — nothing to validate")
    inter_len = sum(observed[k] for k in simulated.keys() & observed.keys())
    return inter_len / sum(union.values())


# ── Fixtures ────────────────────────────────────────────────────────────────────────

def load_fixture(path: Path) -> dict:
    """Load + sanity-check a validation fixture; honesty invariants fail fast."""
    fx = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in ("fixture_id", "gate_id", "provenance", "provisional", "observations"):
        if key not in fx:
            raise ValueError(f"fixture {path.name}: missing required key {key!r}")
    if not fx["observations"]:
        raise ValueError(f"fixture {path.name}: no observations — nothing to validate against")
    if fx["provisional"] and PROVISIONAL_MARK not in fx["provenance"]:
        raise ValueError(
            f"fixture {path.name}: provisional fixtures must carry {PROVISIONAL_MARK!r} "
            "in their provenance (a placeholder must never pass as ground truth)"
        )
    return fx


# ── Gate result (the glass-box unit of the validation ledger) ───────────────────────

@dataclass(frozen=True)
class GateResult:
    """One computed validation gate, with full fixture + threshold provenance."""

    gate_id: str                      # QAD §8 id, e.g. "VAL-01"
    name: str
    metric: str                       # e.g. "normalized_rmse"
    value: float | None               # computed; None iff status == NOT_RUN
    unit: str
    threshold: float
    comparator: Literal["<=", ">="]
    status: GateStatus
    fixture_id: str
    fixture_provenance: str
    fixture_provisional: bool
    simulated_source: str | None      # where the simulated side came from; None iff NOT_RUN
    n_points: int
    threshold_provenance: str
    details: dict = field(default_factory=dict)
    notes: str = ""

    def __post_init__(self) -> None:
        # Validation-theater invariants -- a gate result must be honest by construction.
        if not self.fixture_provenance:
            raise ValueError(f"{self.gate_id}: missing fixture provenance (glass-box, PRD-F14)")
        if not self.threshold_provenance:
            raise ValueError(f"{self.gate_id}: missing threshold provenance (no undocumented gates)")
        if (self.value is None) != (self.status == "NOT_RUN"):
            raise ValueError(f"{self.gate_id}: value/status mismatch — only NOT_RUN may omit the value")
        if self.status != "NOT_RUN":
            held = self.value <= self.threshold if self.comparator == "<=" else self.value >= self.threshold
            if held != (self.status == "PASS"):
                raise ValueError(f"{self.gate_id}: status {self.status} contradicts "
                                 f"{self.value} {self.comparator} {self.threshold}")

    def to_dict(self) -> dict:
        return asdict(self)


def _status(value: float, threshold: float, comparator: str) -> GateStatus:
    held = value <= threshold if comparator == "<=" else value >= threshold
    return "PASS" if held else "FAIL"


# ── VAL-01: Calderon 2014 corridor back-test ────────────────────────────────────────

def validate_calderon(
    simulated: Mapping[str, float],
    *,
    simulated_source: str,
    scenario: str = "scenario1_current",
    fixture_path: Path = CALDERON_FIXTURE,
) -> GateResult:
    """RMSE of injected MATRIX corridor values vs the Calderon 2014 model (QAD VAL-01).

    `simulated` maps fixture observation ids -> MATRIX values in the fixture's unit.
    Every observation point of the chosen scenario must be supplied — scoring a
    flattering subset is cherry-picking and is rejected.
    """
    fx = load_fixture(fixture_path)
    points = [p for p in fx["observations"] if p["scenario"] == scenario]
    if not points:
        known = sorted({p["scenario"] for p in fx["observations"]})
        raise ValueError(f"VAL-01: unknown scenario {scenario!r}; fixture has {known}")
    missing = [p["id"] for p in points if p["id"] not in simulated]
    if missing:
        raise ValueError(
            f"VAL-01: simulated values missing for {missing} — all observation points "
            "of the scenario must be scored (no cherry-picking)"
        )
    obs = [float(p["value"]) for p in points]
    sim = [float(simulated[p["id"]]) for p in points]
    raw_rmse = rmse(sim, obs)
    # Round BEFORE deciding the status: the stored value and the verdict must be the
    # same number, or the self-consistency checks would (rightly) reject the gate.
    nrmse = round(normalized_rmse(sim, obs), 6)
    return GateResult(
        gate_id="VAL-01",
        name=_VAL01_NAME,
        metric="normalized_rmse",
        value=nrmse,
        unit=_VAL01_UNIT,
        threshold=VAL01_THRESHOLD_NRMSE,
        comparator="<=",
        status=_status(nrmse, VAL01_THRESHOLD_NRMSE, "<="),
        fixture_id=fx["fixture_id"],
        fixture_provenance=fx["provenance"],
        fixture_provisional=bool(fx["provisional"]),
        simulated_source=simulated_source,
        n_points=len(points),
        threshold_provenance=VAL01_THRESHOLD_PROVENANCE,
        details={
            "scenario": scenario,
            "rmse": round(raw_rmse, 2),
            "rmse_unit": fx.get("unit", ""),
            "observed_mean": round(sum(obs) / len(obs), 2),
            "pairs": [
                {"id": p["id"], "observed": float(p["value"]), "simulated": float(simulated[p["id"]])}
                for p in points
            ],
        },
    )


# ── VAL-02: 2024 Iloilo flood closure back-test ─────────────────────────────────────

def validate_flood(
    simulated_closed: Mapping[str, float],
    *,
    simulated_source: str,
    fixture_path: Path = FLOOD_FIXTURE,
) -> GateResult:
    """Length-weighted IoU of simulated vs recorded 2024 flood closures (QAD VAL-02).

    `simulated_closed` maps segment_id -> length_m for every road segment the scenario
    closed. Extra simulated closures (false positives) and missed recorded closures
    (false negatives) both shrink the IoU — there is no way to game the overlap.
    """
    fx = load_fixture(fixture_path)
    observed = {p["segment_id"]: float(p["length_m"]) for p in fx["observations"]}
    # Rounded before the verdict so the stored value and the status agree (see VAL-01).
    iou = round(length_weighted_iou(simulated_closed, observed), 6)
    return GateResult(
        gate_id="VAL-02",
        name=_VAL02_NAME,
        metric="length_weighted_iou",
        value=iou,
        unit=_VAL02_UNIT,
        threshold=VAL02_THRESHOLD_IOU,
        comparator=">=",
        status=_status(iou, VAL02_THRESHOLD_IOU, ">="),
        fixture_id=fx["fixture_id"],
        fixture_provenance=fx["provenance"],
        fixture_provisional=bool(fx["provisional"]),
        simulated_source=simulated_source,
        n_points=len(observed),
        threshold_provenance=VAL02_THRESHOLD_PROVENANCE,
        details={
            "event": fx.get("event", ""),
            "observed_closed_m": round(sum(observed.values()), 1),
            "simulated_closed_m": round(sum(simulated_closed.values()), 1),
            "matched_segments": sorted(simulated_closed.keys() & observed.keys()),
            "missed_segments": sorted(observed.keys() - simulated_closed.keys()),
            "extra_segments": sorted(simulated_closed.keys() - observed.keys()),
        },
        notes=(f"{PROVISIONAL_MARK}: result computed against a placeholder closure set; "
               "do not publish as validation.") if fx["provisional"] else "",
    )


# ── NOT_RUN (honest absence — never a fabricated number) ────────────────────────────

def _not_run(gate_id: str, name: str, metric: str, unit: str, threshold: float,
             comparator: Literal["<=", ">="], threshold_provenance: str,
             fixture_path: Path, reason: str) -> GateResult:
    fx = load_fixture(fixture_path)
    return GateResult(
        gate_id=gate_id, name=name, metric=metric, value=None, unit=unit,
        threshold=threshold, comparator=comparator, status="NOT_RUN",
        fixture_id=fx["fixture_id"], fixture_provenance=fx["provenance"],
        fixture_provisional=bool(fx["provisional"]), simulated_source=None,
        n_points=len(fx["observations"]), threshold_provenance=threshold_provenance,
        notes=reason,
    )


# ── Report: run gates, emit + re-validate validation_report.json ────────────────────

def run_validation_gates(
    *,
    calderon_simulated: Mapping[str, float] | None = None,
    calderon_source: str = "injected",
    calderon_scenario: str = "scenario1_current",
    flood_simulated: Mapping[str, float] | None = None,
    flood_source: str = "injected",
) -> dict:
    """Run both QAD §8 gates and return the machine-readable report (dict).

    Gates whose simulated side was not supplied are reported NOT_RUN with the reason —
    a gate that did not run never reports a number (the anti-theater rule).
    """
    if calderon_simulated is not None:
        cal = validate_calderon(calderon_simulated, simulated_source=calderon_source,
                                scenario=calderon_scenario)
    else:
        cal = _not_run(
            "VAL-01", _VAL01_NAME, "normalized_rmse", _VAL01_UNIT,
            VAL01_THRESHOLD_NRMSE, "<=", VAL01_THRESHOLD_PROVENANCE, CALDERON_FIXTURE,
            "no simulated corridor values supplied — needs a kernel run "
            "(see simulated_corridor_flows_from_baseline) plus the corridor→edge mapping",
        )
    if flood_simulated is not None:
        flood = validate_flood(flood_simulated, simulated_source=flood_source)
    else:
        flood = _not_run(
            "VAL-02", _VAL02_NAME, "length_weighted_iou", _VAL02_UNIT,
            VAL02_THRESHOLD_IOU, ">=", VAL02_THRESHOLD_PROVENANCE, FLOOD_FIXTURE,
            "no simulated flood-closure set supplied — needs a flood-scenario kernel run",
        )
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kernel": "matrix-kernel 0.1.0",
        "gates": [cal.to_dict(), flood.to_dict()],
    }


def write_validation_report(report: dict, path: Path = DEFAULT_REPORT_PATH) -> Path:
    """Write the report JSON (validated first — a malformed report never ships)."""
    _check_report(report)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def load_validation_report(path: Path = DEFAULT_REPORT_PATH) -> dict:
    """Load + re-validate a report; raises ValueError if it violates the schema."""
    report = json.loads(Path(path).read_text(encoding="utf-8"))
    _check_report(report)
    return report


_GATE_REQUIRED_KEYS = (
    "gate_id", "name", "metric", "value", "unit", "threshold", "comparator", "status",
    "fixture_id", "fixture_provenance", "fixture_provisional", "simulated_source",
    "n_points", "threshold_provenance",
)


def _check_report(report: dict) -> None:
    """Schema + honesty checks for validation_report.json (used on write AND load)."""
    if report.get("schema_version") != REPORT_SCHEMA_VERSION:
        raise ValueError(f"report: schema_version != {REPORT_SCHEMA_VERSION}")
    datetime.fromisoformat(report.get("generated_at") or "")  # ValueError if missing/unparseable
    gates = report.get("gates")
    if not gates:
        raise ValueError("report: no gates")
    for g in gates:
        missing = [k for k in _GATE_REQUIRED_KEYS if k not in g]
        if missing:
            raise ValueError(f"report gate {g.get('gate_id', '?')}: missing keys {missing}")
        if g["status"] not in ("PASS", "FAIL", "NOT_RUN"):
            raise ValueError(f"{g['gate_id']}: bad status {g['status']!r}")
        if g["comparator"] not in ("<=", ">="):
            raise ValueError(f"{g['gate_id']}: bad comparator {g['comparator']!r}")
        if (g["value"] is None) != (g["status"] == "NOT_RUN"):
            raise ValueError(f"{g['gate_id']}: value/status mismatch (only NOT_RUN omits the value)")
        if g["status"] != "NOT_RUN":
            held = g["value"] <= g["threshold"] if g["comparator"] == "<=" else g["value"] >= g["threshold"]
            if held != (g["status"] == "PASS"):
                raise ValueError(f"{g['gate_id']}: status {g['status']} contradicts "
                                 f"{g['value']} {g['comparator']} {g['threshold']}")
            if not g["simulated_source"]:
                raise ValueError(f"{g['gate_id']}: a computed gate must name its simulated_source")
        if not g["fixture_provenance"] or not g["threshold_provenance"]:
            raise ValueError(f"{g['gate_id']}: missing provenance (glass-box, PRD-F14)")
        if g["fixture_provisional"] and PROVISIONAL_MARK not in g["fixture_provenance"]:
            raise ValueError(f"{g['gate_id']}: provisional fixture lost its {PROVISIONAL_MARK!r} marker")


# ── Thin live-baseline convenience (the only SUMO/Redis-adjacent path; optional) ────

def simulated_corridor_flows_from_baseline(
    corridor_edges: Mapping[str, Sequence[str]],
    *,
    pax_per_vehicle: float = 14.0,
    redis_url: str | None = None,
) -> dict[str, float] | None:
    """Map fixture observation ids -> peak passenger-flow proxies from the cached baseline.

    For each observation id, takes the busiest of its mapped SUMO edges (vehicles entered
    over the sim window), scales to veh/h, and applies an average-occupancy assumption
    (`pax_per_vehicle`, default 14 pax/jeepney — an explicit assumption, override with a
    calibrated value). Returns None when the baseline is unavailable (no eclipse-sumo
    import chain, no Redis, or no cached baseline) so the gate reports NOT_RUN instead
    of a guess. Callers should pass simulated_source="live-baseline:redis" to the gate.
    """
    try:  # lazy: baseline -> sumo_env needs the eclipse-sumo wheel; absent on bare venvs
        from matrix_kernel.baseline import REDIS_URL, SIM_END, load_baseline
    except Exception:
        return None
    try:
        traj = load_baseline(redis_url or REDIS_URL)
    except Exception:
        return None
    window_s = float(traj.meta.get("sim_end_s", SIM_END))
    return {
        obs_id: max((traj.edge_counts.get(e, 0) for e in edges), default=0)
        * (3600.0 / window_s) * pax_per_vehicle
        for obs_id, edges in corridor_edges.items()
    }


def get_all_validations() -> list[dict]:
    """All gate results for the Validation Panel (API surface).

    Without a kernel-run simulated side the gates are honestly NOT_RUN — the panel
    shows the gate, its threshold, and why it has not run, instead of theater.
    """
    return run_validation_gates()["gates"]
