"""Tests for the CR-010 BLUF + bilingual synthesis brief (methods §4, PRD-F7).

Bare-mode: a stub LLM client only, no network/SUMO/Redis. These assert the
structural contract of the rewritten prompt — that the bilingual `=== HILIGAYNON ===`
delimiter and the inline `[EQUATION_ID]` citation contract both survive the citation
guard, in BOTH languages. The guard itself is exercised in test_citation_guard.py;
here we verify synthesize() preserves a well-formed bilingual brief end to end and
strips uncited numbers wherever they appear.
"""
from matrix_kernel.results import DimensionResult
from matrix_kernel.synthesis import HILIGAYNON_MARKER, synthesize


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


def _result():
    return DimensionResult(
        dimension="behavioral", metric="Δ trips/day", equation_id="BEH-1",
        value=-14.0, range=(-20.0, -8.0), unit="trips", confidence="M",
        input_dataset_ids=["OSM-ILO", "PERSONA-POOL"],
    )


def _stub(content, monkeypatch):
    monkeypatch.setattr(
        "matrix_kernel.synthesis.generate_chat_completion",
        lambda *a, **k: _FakeResponse(content),
    )


def test_prompt_requests_bluf_sections_and_bilingual_delimiter(monkeypatch):
    """The system instruction must ask for the BLUF headers + the HILIGAYNON marker
    and keep the inline citation rule (glass box)."""
    captured = {}

    def _capture(_client, *, model, messages, **kwargs):
        captured["system"] = messages[0]["content"]
        return _FakeResponse("Traffic eases, with trips falling by 14 [BEH-1].")

    monkeypatch.setattr("matrix_kernel.synthesis.generate_chat_completion", _capture)
    synthesize([_result()], client=object())

    system = captured["system"]
    for header in ("HEADLINE", "WHAT WE SIMULATED", "KEY FINDINGS", "RECOMMENDATION", "KEY RISK"):
        assert header in system
    assert HILIGAYNON_MARKER in system
    # The citation contract must remain in the prompt (glass box, PRD-F14).
    assert "Equation ID" in system
    assert "[BEH-1]" in system


def test_bilingual_brief_survives_citation_guard(monkeypatch):
    """A well-formed bilingual brief — cited numbers in both languages — passes
    through unblocked, marker intact."""
    brief = (
        "HEADLINE\n"
        "Morning traffic eases on the affected road; proceed.\n\n"
        "KEY FINDINGS\n"
        "Trips on the affected road fall by 14 [BEH-1].\n\n"
        f"{HILIGAYNON_MARKER}\n"
        "HEADLINE\n"
        "Nagahupa ang trapiko sa aga; padayuna.\n\n"
        "KEY FINDINGS\n"
        "Nagnubo ang biyahe sa dalan sang 14 [BEH-1]."
    )
    _stub(brief, monkeypatch)
    narrative, citations = synthesize([_result()], client=object())

    assert HILIGAYNON_MARKER in narrative  # delimiter preserved -> web can split EN/HIL
    assert narrative.count("[BEH-1]") == 2  # cited in BOTH languages
    assert citations and citations[0]["equation_id"] == "BEH-1"


def test_uncited_number_stripped_in_either_language(monkeypatch):
    """An uncited numeric claim is dropped wherever it sits — including the
    Hiligaynon half — while cited claims and pure narration survive."""
    brief = (
        "HEADLINE\n"
        "Trips fall by 14 [BEH-1].\n\n"
        "KEY FINDINGS\n"
        "Jobs grew by 99 with no citation.\n\n"  # uncited -> must be stripped
        f"{HILIGAYNON_MARKER}\n"
        "HEADLINE\n"
        "Nagnubo ang biyahe sang 14 [BEH-1].\n\n"
        "KEY FINDINGS\n"
        "Nagdugang ang trabaho sang 99 nga wala citation."  # uncited -> stripped
    )
    _stub(brief, monkeypatch)
    narrative, _ = synthesize([_result()], client=object())

    assert "99" not in narrative  # both uncited numbers gone
    assert narrative.count("[BEH-1]") == 2  # both cited claims kept
    assert HILIGAYNON_MARKER in narrative  # marker (no digit) always survives
