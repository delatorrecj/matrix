"""Tests for map-truth contract (overlay_honest)."""
from matrix_kernel.map_truth import map_truth_fields, overlay_honest


def test_overlay_honest_for_keyword_match():
    assert overlay_honest("keyword-match") is True
    assert overlay_honest("gazetteer-alias") is True
    assert overlay_honest("geometry") is True


def test_overlay_honest_false_for_fallback_and_facility():
    assert overlay_honest("busiest-baseline-fallback (x)") is False
    assert overlay_honest("facility-demand") is False
    assert overlay_honest(None) is False


def test_map_truth_fields_strips_loi_on_fallback():
    fields = map_truth_fields(["e1"], "busiest-baseline-fallback (x)", [122.5, 10.7])
    assert fields["overlay_honest"] is False
    assert fields["affected_edges"] == []
    assert fields["location_of_interest"] is None


def test_map_truth_fields_keeps_honest_corridor():
    fields = map_truth_fields(["e1"], "keyword-match", [122.5, 10.7])
    assert fields["overlay_honest"] is True
    assert fields["affected_edges"] == ["e1"]
    assert fields["location_of_interest"] == [122.5, 10.7]
