"""Citation guard (Phase 4.4 / methods §4).

Filters out any synthesis claim that asserts a number but lacks an inline citation
(e.g. `[BEH-1]`). Numbers come from the kernel, never from the LLM — the synthesis agent
narrates and cites; it never originates a number (PRD-F14, methods §4).

Policy (methods §4): "synthesis narrative claims that assert a number must reference an
`equation_id` AND its `input_dataset_ids`." We enforce the dataset basis *through* the
equation id rather than by demanding raw dataset tokens in the prose — the synthesis prompt
only ever instructs the LLM to emit `[EQUATION_ID]` (not dataset ids), so requiring inline
`[OSM-ILO]`-style tokens would over-block every legitimate narration. Instead, when the
caller supplies `citation_datasets` (equation_id -> input_dataset_ids), a cited equation is
accepted only if it resolves to a non-empty dataset basis; a citation with no registered
datasets is treated as uncited and the claim is blocked. With no mapping supplied the guard
falls back to the equation-id-only check (backwards compatible).

Two heuristic refinements over the naive "any digit needs a citation":
  * Citations are stripped before the numeric scan, so a sentence whose only digit lived
    inside the bracket (e.g. the "1" in `[BEH-1]`) is not mistaken for an uncited number.
  * A claim is "numeric" only if a digit survives that stripping — pure narration passes.
"""
from __future__ import annotations

import re
from typing import Mapping, Sequence

_CITATION_RE = re.compile(r"\[([A-Z0-9-]+)\]")
_DIGIT_RE = re.compile(r"\d")


def _split_sentences(narrative: str) -> list[str]:
    return re.split(r"(?<=[.!?]) +", narrative)


def _asserts_number(sentence: str) -> bool:
    """True if the sentence states a number once its bracketed citations are removed.

    Stripping the citations first means the digits inside `[BEH-1]` don't count as a claim;
    only a number in the prose itself does."""
    return bool(_DIGIT_RE.search(_CITATION_RE.sub("", sentence)))


def _citation_ok(
    citation: str,
    valid_citations: set[str],
    citation_datasets: Mapping[str, Sequence[str]] | None,
) -> bool:
    """A citation is valid if it is a known equation_id and (when the mapping is supplied)
    that equation resolves to at least one input dataset (methods §4 dataset basis)."""
    if citation not in valid_citations:
        return False
    if citation_datasets is None:
        return True
    return bool(citation_datasets.get(citation))


def verify_citations(
    narrative: str,
    required_citations: set[str],
    citation_datasets: Mapping[str, Sequence[str]] | None = None,
) -> bool:
    """Return True iff every numeric claim cites a valid, dataset-backed equation_id.

    `citation_datasets` (equation_id -> input_dataset_ids), when given, additionally requires
    the cited equation to carry a non-empty dataset basis (methods §4); omit it for the
    equation-id-only check.
    """
    for sentence in _split_sentences(narrative):
        if not _asserts_number(sentence):
            continue
        citations_found = _CITATION_RE.findall(sentence)
        if not citations_found:
            return False
        if any(not _citation_ok(c, required_citations, citation_datasets) for c in citations_found):
            return False
    return True


def strip_uncited_claims(
    narrative: str,
    valid_citations: set[str],
    citation_datasets: Mapping[str, Sequence[str]] | None = None,
) -> str:
    """Drop sentences that assert a number but lack a valid, dataset-backed citation.

    Non-numeric sentences always pass. A numeric sentence passes only when every bracketed
    citation it carries is a known equation_id and — when `citation_datasets` is supplied —
    resolves to a non-empty input-dataset basis (methods §4). See the module docstring for
    why the dataset basis is enforced through the equation id rather than via inline tokens.
    """
    valid_sentences: list[str] = []
    for sentence in _split_sentences(narrative):
        if not sentence.strip():
            continue
        if not _asserts_number(sentence):
            valid_sentences.append(sentence)
            continue
        citations_found = _CITATION_RE.findall(sentence)
        if citations_found and all(
            _citation_ok(c, valid_citations, citation_datasets) for c in citations_found
        ):
            valid_sentences.append(sentence)
    return " ".join(valid_sentences)
