"""Credibility report builder unit tests."""
from __future__ import annotations

from matrix_kernel.credibility import build_credibility_report, write_credibility_report


def test_build_credibility_report_shape(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAQ_API_KEY", raising=False)
    report = build_credibility_report(eco2_abs_ug_m3=2.0)
    assert report["llm_invents_numbers"] is False
    assert report["schema_version"] == "1.0"
    assert "equations" in report and len(report["equations"]) >= 15
    assert "who_emep_ef" in report["external"]
    assert report["external"]["who_emep_ef"]["status"] in ("PASS", "FAIL", "SKIPPED")
    assert report["external"]["openaq_pm25_scale"]["status"] in ("PASS", "FAIL", "SKIPPED")
    assert "VAL-03" in report["gates"]
    assert any(e["equation_id"] == "ECON-1" and e["conformance"] == "equation_backed"
               for e in report["equations"])
    assert any(e["equation_id"] == "ECO-2" and e["conformance"] == "provisional_proxy"
               for e in report["equations"])

    out = write_credibility_report(report, path=tmp_path / "credibility_report.json")
    assert out.is_file()
    assert "llm_invents_numbers" in out.read_text(encoding="utf-8")
