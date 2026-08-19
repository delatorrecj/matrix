"""Third-party spot-checks (WHO-EMEP EF band + OpenAQ scale) — Credibility Phase 1."""
from __future__ import annotations

import pytest

pytest.importorskip("sumo", reason="eclipse-sumo not installed; run `uv sync` in app/packages/kernel")

from matrix_kernel.external_checks import check_openaq_pm25_scale, check_who_emep_ef_band
from matrix_kernel.modules.ecological import _EF_CO2_G_PER_KM


def test_who_emep_ef_band_passes_for_eco1_constant():
    result = check_who_emep_ef_band(ef_g_per_km=_EF_CO2_G_PER_KM)
    assert result["status"] == "PASS"
    assert result["band_lo"] <= _EF_CO2_G_PER_KM <= result["band_hi"]


def test_who_emep_ef_band_fails_outside_band():
    result = check_who_emep_ef_band(ef_g_per_km=500.0)
    assert result["status"] == "FAIL"


def test_openaq_scale_uses_fixture_when_no_key(monkeypatch):
    monkeypatch.delenv("OPENAQ_API_KEY", raising=False)
    # Ambient-only (no ECO-2) → SKIPPED but ambient present from fixture
    ambient_only = check_openaq_pm25_scale(eco2_abs_ug_m3=None)
    assert ambient_only["status"] == "SKIPPED"
    assert ambient_only.get("ambient_pm25_ug_m3", 0) > 0

    # Plausible ECO-2 magnitude vs ~18.5 ambient
    ok = check_openaq_pm25_scale(eco2_abs_ug_m3=5.0)
    assert ok["status"] == "PASS"

    # Implausibly huge ECO-2
    bad = check_openaq_pm25_scale(eco2_abs_ug_m3=10_000.0)
    assert bad["status"] == "FAIL"
