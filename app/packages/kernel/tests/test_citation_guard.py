"""Tests for the citation guard (methods §4).

Pure Python — runs in bare mode (`python -m pytest`), no SUMO/Redis/network.

Policy under test: a numeric claim must cite a known equation_id; when a
equation_id -> input_dataset_ids mapping is supplied, that equation must also resolve to a
non-empty dataset basis (the §4 "equation_id AND its input_dataset_ids" requirement enforced
*through* the equation id, since the synthesis prompt only ever asks the LLM to emit
`[EQUATION_ID]`). The synthesis fallback that blanks an empty narrative lives in synthesis.py
and is unaffected — the guard never originates a number.
"""
from matrix_kernel.citation_guard import strip_uncited_claims, verify_citations

VALID = {"BEH-1", "ECO-2"}
DATASETS = {"BEH-1": ["OSM-ILO", "OVERTURE"], "ECO-2": ["EMB", "S5P-NO2"]}


def test_cited_numeric_claim_passes():
    text = "Trips fell by 450 [BEH-1]."
    assert verify_citations(text, VALID, DATASETS)
    assert strip_uncited_claims(text, VALID, DATASETS) == text


def test_uncited_numeric_claim_blocked():
    text = "Trips fell by 450. Air quality improved [ECO-2]."
    assert not verify_citations(text, VALID)
    # The uncited numeric sentence is dropped; the cited one survives.
    out = strip_uncited_claims(text, VALID, DATASETS)
    assert "450" not in out
    assert "[ECO-2]" in out


def test_unknown_equation_id_blocked():
    text = "Jobs grew by 12 [FAKE-9]."
    assert not verify_citations(text, VALID, DATASETS)
    assert strip_uncited_claims(text, VALID, DATASETS).strip() == ""


def test_citation_with_no_dataset_basis_blocked():
    # §4: a cited equation must carry a dataset basis. ECO-9 is "valid" by id but has no
    # registered datasets -> a numeric claim citing it is blocked when the mapping is given.
    text = "Heat index rose by 3 [ECO-9]."
    valid = VALID | {"ECO-9"}
    datasets = {**DATASETS, "ECO-9": []}
    assert strip_uncited_claims(text, valid, datasets).strip() == ""
    # Without the mapping, the equation-id-only fallback lets it through (backwards compatible).
    assert strip_uncited_claims(text, valid).strip() == text


def test_non_numeric_narration_always_passes():
    text = "The corridor closure reshapes commuter behaviour citywide."
    assert verify_citations(text, VALID, DATASETS)
    assert strip_uncited_claims(text, VALID, DATASETS) == text


def test_citation_bracket_digits_are_not_a_numeric_claim():
    # A sentence whose only digit lives inside the citation bracket is pure narration and
    # must NOT be blocked for "asserting an uncited number".
    text = "Behavioural effects are summarised in the corridor view [BEH-1]."
    assert verify_citations(text, VALID, DATASETS)
    assert strip_uncited_claims(text, VALID, DATASETS) == text


def test_all_numeric_uncited_collapses_to_empty():
    text = "Trips fell by 450. Jobs grew by 12."
    assert strip_uncited_claims(text, VALID, DATASETS).strip() == ""
