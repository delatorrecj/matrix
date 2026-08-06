"""Credibility report builder (Phase 1) — backend artifact for GET /credibility.

Layers:
  A — internal glass-box (equation conformance + citation contract)
  B — literature gates (VAL-01 / VAL-03)
  C — open third-party spot-checks (WHO-EMEP EF band, OpenAQ PM2.5 scale)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from matrix_kernel.equation_conformance import EQUATION_CONFORMANCE, PROVISIONAL_CONSTANTS
from matrix_kernel.external_checks import (
    check_openaq_pm25_scale,
    check_who_emep_ef_band,
)

# app/ root: credibility.py -> matrix_kernel -> kernel -> packages -> app
_APP_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CREDIBILITY_PATH = _APP_ROOT / "credibility_report.json"
DEFAULT_VALIDATION_PATH = _APP_ROOT / "validation_report.json"


def _val03_status() -> dict[str, Any]:
    """VAL-03 is enforced by the bias auditor on the persona pool, not validation_report."""
    try:
        from matrix_kernel.bias_auditor import MODE_SHARE_TOLERANCE, audit_personas
        from matrix_kernel.config import ILOILO_MODE_SHARE
        from matrix_kernel.personas import _static_seeded_pool, observed_mode_share

        pool = _static_seeded_pool(200, ILOILO_MODE_SHARE, seed=7)
        observed = observed_mode_share(pool)
        entry = audit_personas(observed, ILOILO_MODE_SHARE, batch_id="credibility-val03")
        passed = not entry.reweighted and entry.max_delta <= MODE_SHARE_TOLERANCE
        return {
            "status": "PASS" if passed else "FAIL",
            "value": entry.max_delta,
            "threshold": MODE_SHARE_TOLERANCE,
            "note": "bias_auditor MODE_SHARE_TOLERANCE ±3% (static pool on-anchor by construction)",
        }
    except Exception as exc:  # pragma: no cover - import soft path
        return {
            "status": "NOT_RUN",
            "value": None,
            "note": f"VAL-03 unavailable ({exc})",
        }


def _load_validation_gates() -> dict[str, Any]:
    for path in (
        DEFAULT_VALIDATION_PATH,
        _APP_ROOT / "packages" / "kernel" / "validation_report.json",
    ):
        if path.is_file():
            try:
                report = json.loads(path.read_text(encoding="utf-8"))
                gates = {g["gate_id"]: g for g in report.get("gates", [])}
                return {
                    gid: {
                        "status": g.get("status"),
                        "value": g.get("value"),
                        "threshold": g.get("threshold"),
                        "metric": g.get("metric"),
                        "notes": g.get("notes"),
                    }
                    for gid, g in gates.items()
                }
            except (OSError, json.JSONDecodeError, TypeError):
                continue
    try:
        from matrix_kernel.validation import get_all_validations

        gates = {g["gate_id"]: g for g in get_all_validations()}
        return {
            gid: {
                "status": g.get("status"),
                "value": g.get("value"),
                "threshold": g.get("threshold"),
                "metric": g.get("metric"),
                "notes": g.get("notes"),
            }
            for gid, g in gates.items()
        }
    except Exception as exc:
        return {"error": str(exc)}


def build_credibility_report(*, eco2_abs_ug_m3: float | None = None) -> dict[str, Any]:
    """Assemble the machine-readable credibility report."""
    equations = []
    for eid, (tag, ceiling) in sorted(EQUATION_CONFORMANCE.items()):
        equations.append({
            "equation_id": eid,
            "conformance": tag,
            "confidence_ceiling": ceiling,
            "requires_directional": tag in ("provisional_proxy", "scalar_standin"),
            "external_checks": [],
        })

    who = check_who_emep_ef_band()
    openaq = check_openaq_pm25_scale(eco2_abs_ug_m3=eco2_abs_ug_m3)

    # Attach ECO-1 / ECO-2 external check ids onto those equation rows.
    for row in equations:
        if row["equation_id"] == "ECO-1":
            row["external_checks"].append("who_emep_ef")
        if row["equation_id"] == "ECO-2":
            row["external_checks"].append("openaq_pm25_scale")

    gates = _load_validation_gates()
    gates["VAL-03"] = _val03_status()

    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "llm_invents_numbers": False,
        "llm_note": (
            "Kernel DimensionResult values are the sole numeric source; "
            "synthesis.strip_uncited_claims drops any LLM magnitude lacking a valid "
            "[EQUATION_ID] with non-empty input_dataset_ids (PRD-F14)."
        ),
        "non_goals": [
            "No PTV Vissim / Aimsun / Replica cross-simulation",
            "No TomTom/HERE live traffic twin",
            "Scenario impacts have no commercial third-party oracle",
            "Demand Tier-B uses WorldPop — not fitted to Calderon VAL-01 targets",
            "No government FOI / agency OD (CR-016 open-data-only)",
            "VAL-01 corridor volumes are directional under literature mode-share (M)",
            "VAL-02 2024-event IoU stays NOT_RUN; LiPAD is hazard-skill only",
        ],
        "open_data_policy": "CR-016",
        "mode_share_anchor": {
            "source": "Calderon2014+LPTRP literature",
            "confidence_floor": "M",
            "invented": False,
        },
        "provisional_constants": dict(PROVISIONAL_CONSTANTS),
        "equations": equations,
        "gates": gates,
        "external": {
            "who_emep_ef": who,
            "openaq_pm25_scale": openaq,
        },
    }


def write_credibility_report(
    report: dict | None = None,
    path: Path = DEFAULT_CREDIBILITY_PATH,
) -> Path:
    report = report if report is not None else build_credibility_report()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
