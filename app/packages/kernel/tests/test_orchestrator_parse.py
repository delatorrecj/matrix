"""Orchestrator NL->Scenario mapping tests (no network -- a fake genai client is injected).

The Azure OpenAI call itself is not under test (that's an eval, not a unit test); what is under
test is the deterministic mapping ScenarioSchema -> Scenario v2: intervention typing,
parameter assembly, the legacy corridor back-fill, and the ambiguity guard.
"""
import pytest

# orchestrator imports openai + pydantic at module top; skip cleanly in bare envs.
pytest.importorskip("openai", reason="openai not installed; run `uv sync` in app/packages/kernel")

from matrix_kernel.orchestrator import ScenarioSchema, parse_scenario


class _FakeMessage:
    def __init__(self, parsed):
        self.parsed = parsed
        self.content = ""

class _FakeChoice:
    def __init__(self, parsed):
        self.message = _FakeMessage(parsed)

class _FakeResponse:
    def __init__(self, parsed):
        self.choices = [_FakeChoice(parsed)]

class _FakeCompletions:
    def __init__(self, parsed):
        self._parsed = parsed

    def parse(self, **kwargs):
        return _FakeResponse(self._parsed)

    def create(self, **kwargs):
        return _FakeResponse(self._parsed)

class _FakeChat:
    def __init__(self, parsed):
        self.completions = _FakeCompletions(parsed)

class _FakeBetaChat:
    def __init__(self, parsed):
        self.completions = _FakeCompletions(parsed)

class _FakeBeta:
    def __init__(self, parsed):
        self.chat = _FakeBetaChat(parsed)

class FakeClient:
    def __init__(self, parsed):
        self.chat = _FakeChat(parsed)
        self.beta = _FakeBeta(parsed)


def test_lane_closure_maps_with_legacy_backfill():
    schema = ScenarioSchema(
        description="Close one lane on Diversion Rd for roadworks",
        intervention_type="lane_closure", location="Diversion Rd",
        lanes_closed=1, is_ambiguous=False,
    )
    sc = parse_scenario("roadworks on Diversion Rd", client=FakeClient(schema))
    assert sc.intervention_type == "lane_closure"
    assert sc.location == "Diversion Rd"
    assert sc.corridor == "Diversion Rd"      # v1 channel back-filled for /scenario consumers
    assert sc.lanes_closed == 1
    assert sc.parameters == {"lanes_closed": 1}
    assert sc.geometry is None
    assert sc.scenario_id                      # a uuid was assigned


def test_speed_change_carries_stated_speed_only():
    schema = ScenarioSchema(
        description="30 km/h school zone on JM Basa St",
        intervention_type="speed_change", location="JM Basa",
        max_speed_kph=30.0, is_ambiguous=False,
    )
    sc = parse_scenario("school zone JM Basa 30kph", client=FakeClient(schema))
    assert sc.intervention_type == "speed_change"
    assert sc.parameters == {"max_speed_kph": 30.0}


def test_speed_change_without_stated_speed_leaves_parameters_empty():
    """The LLM never invents a number (PRD-F14); the kernel default is applied -- and
    recorded -- downstream."""
    schema = ScenarioSchema(
        description="Traffic calming in Molo", intervention_type="speed_change",
        location="Molo", max_speed_kph=None, is_ambiguous=False,
    )
    sc = parse_scenario("calm traffic in Molo", client=FakeClient(schema))
    assert sc.parameters == {}
    assert sc.effective_parameters()["max_speed_kph"] == 30.0  # documented kernel default


def test_full_closure_maps_with_no_parameters():
    schema = ScenarioSchema(
        description="JM Basa closed for Dinagyang", intervention_type="full_closure",
        location="JM Basa", is_ambiguous=False,
    )
    sc = parse_scenario("close JM Basa for Dinagyang", client=FakeClient(schema))
    assert sc.intervention_type == "full_closure"
    assert sc.parameters == {}


def test_capacity_change_carries_factor():
    schema = ScenarioSchema(
        description="Widen Diversion Rd by one lane", intervention_type="capacity_change",
        location="Diversion Rd", capacity_factor=1.5, is_ambiguous=False,
    )
    sc = parse_scenario("widen Diversion Rd", client=FakeClient(schema))
    assert sc.intervention_type == "capacity_change"
    assert sc.parameters == {"capacity_factor": 1.5}


def test_geometry_passthrough_sets_scenario_geometry():
    """A map-drop geometry supplied out-of-band (the API's structured field) rides onto
    the Scenario verbatim -- the LLM never originates geometry (PRD-F14)."""
    schema = ScenarioSchema(
        description="Fully close the dropped area for flooding",
        intervention_type="full_closure", location="", is_ambiguous=False,
    )
    geom = {"type": "Point", "coordinates": [122.5621, 10.7202]}
    sc = parse_scenario("flood closure here", client=FakeClient(schema), geometry=geom)
    assert sc.geometry == geom
    assert sc.intervention_type == "full_closure"


def test_geometry_defaults_to_none_when_absent():
    schema = ScenarioSchema(
        description="Close one lane on A", intervention_type="lane_closure",
        location="A", is_ambiguous=False,
    )
    assert parse_scenario("q", client=FakeClient(schema)).geometry is None


def test_ambiguous_query_raises_with_clarification():
    schema = ScenarioSchema(
        description="", intervention_type="lane_closure", is_ambiguous=True,
        clarification_prompt="Where should the school be built?",
    )
    with pytest.raises(ValueError, match="Where should the school"):
        parse_scenario("what if we build a school?", client=FakeClient(schema))


def test_new_facility_maps_stated_kind_and_capacity():
    """A 3,000-seat school in Molo is demand (BEH-4), not a construction lane_closure."""
    schema = ScenarioSchema(
        description="Build a 3,000-seat school in Molo",
        intervention_type="new_facility",
        location="Molo",
        facility_kind="school",
        capacity=3000,
        is_ambiguous=False,
    )
    sc = parse_scenario(
        "What if we build a 3,000-seat school in Molo?",
        client=FakeClient(schema),
    )
    assert sc.intervention_type == "new_facility"
    assert sc.location == "Molo"
    assert sc.corridor == "Molo"
    assert sc.parameters == {"facility_kind": "school", "capacity": 3000}
    assert sc.geometry is None
    assert sc.flood_hazard is False


def test_flood_query_sets_flood_hazard_on_full_closure():
    schema = ScenarioSchema(
        description="Flood closes Jaro",
        intervention_type="full_closure",
        location="Jaro",
        is_ambiguous=False,
        flood_hazard=True,
    )
    sc = parse_scenario("what if a flood closes Jaro?", client=FakeClient(schema))
    assert sc.intervention_type == "full_closure"
    assert sc.flood_hazard is True


def test_system_instruction_classifies_new_facility_not_construction(monkeypatch):
    """Live Azure follows the system prompt; it must not remap a school to lane_closure."""
    seen: dict[str, str] = {}

    def capture(client, *, messages, **kwargs):
        seen["content"] = messages[0]["content"]
        schema = ScenarioSchema(
            description="Build a 3,000-seat school in Molo",
            intervention_type="new_facility",
            location="Molo",
            facility_kind="school",
            capacity=3000,
            is_ambiguous=False,
        )
        class _Msg:
            parsed = schema
            content = ""
        class _Choice:
            message = _Msg()
        class _Resp:
            choices = [_Choice()]
        return _Resp()

    monkeypatch.setattr("matrix_kernel.orchestrator.generate_chat_completion", capture)
    parse_scenario("What if we build a 3,000-seat school in Molo?", client=FakeClient(
        ScenarioSchema(
            description="x", intervention_type="new_facility", location="Molo",
            facility_kind="school", capacity=3000, is_ambiguous=False,
        )
    ))
    text = seen["content"]
    assert "new_facility" in text
    assert "construction-phase" not in text
    assert "BEH-4" in text
    assert "flood_hazard" in text
    assert "flood_hazard" in text


def test_span_fields_map_onto_parameters_location_is_corridor_only():
    schema = ScenarioSchema(
        description="Close Cuartero from Fajardo to El 98",
        intervention_type="full_closure",
        location="Cuartero Street",
        from_cross="Fajardo Street",
        to_cross="El 98 Street",
        is_ambiguous=False,
    )
    sc = parse_scenario("close Cuartero from Fajardo up to EL98", client=FakeClient(schema))
    assert sc.location == "Cuartero Street"
    assert sc.corridor == "Cuartero Street"
    assert sc.parameters["from_cross"] == "Fajardo Street"
    assert sc.parameters["to_cross"] == "El 98 Street"


def test_stuffed_location_is_peeled_into_span_fields():
    schema = ScenarioSchema(
        description="Full road closure on Cuartero",
        intervention_type="full_closure",
        location="Cuartero Street, segment from Fajardo St. to EL98 st.",
        from_cross="",
        to_cross="",
        is_ambiguous=False,
    )
    sc = parse_scenario("A full road closure on Cuartero Street", client=FakeClient(schema))
    assert sc.location == "Cuartero Street"
    assert "segment" not in sc.location.lower()
    assert sc.parameters["from_cross"] == "Fajardo Street"
    assert sc.parameters["to_cross"] == "El 98 Street"


def test_named_street_without_crosses_is_not_ambiguous():
    schema = ScenarioSchema(
        description="Close all of Cuartero Street",
        intervention_type="full_closure",
        location="Cuartero Street",
        from_cross="",
        to_cross="",
        is_ambiguous=False,
    )
    sc = parse_scenario("close Cuartero Street", client=FakeClient(schema))
    assert sc.location == "Cuartero Street"
    assert "from_cross" not in sc.parameters
    assert "to_cross" not in sc.parameters


def test_system_instruction_describes_span_fields(monkeypatch):
    seen: dict[str, str] = {}

    def capture(client, *, messages, **kwargs):
        seen["content"] = messages[0]["content"]
        schema = ScenarioSchema(
            description="x", intervention_type="full_closure",
            location="Cuartero Street", from_cross="", to_cross="", is_ambiguous=False,
        )
        class _Msg:
            parsed = schema
            content = ""
        class _Choice:
            message = _Msg()
        class _Resp:
            choices = [_Choice()]
        return _Resp()

    monkeypatch.setattr("matrix_kernel.orchestrator.generate_chat_completion", capture)
    parse_scenario("close Cuartero from Fajardo up to EL98", client=FakeClient(
        ScenarioSchema(
            description="x", intervention_type="full_closure",
            location="Cuartero Street", is_ambiguous=False,
        )
    ))
    text = seen["content"]
    assert "from_cross" in text
    assert "Never put" in text or "canonical street name only" in text
