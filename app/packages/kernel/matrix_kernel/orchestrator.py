"""Azure OpenAI 3.1 Pro NL -> Scenario parser (PRD-F2, PRD-F8).

Turns a natural-language query ("what if we close JM Basa St for the Dinagyang festival?")
into a structured Scenario v2 (matrix_kernel.scenario): the model classifies the
intervention into one of INTERVENTION_TYPES, extracts the location, and fills only the
parameters the user implied -- it never invents numbers (glass box, PRD-F14; the kernel
applies documented defaults and records the exact values in Trajectory.meta). If the
query is ambiguous or out of scope, parse_scenario raises ValueError (which the API
should catch to ask for clarification).
"""
from __future__ import annotations

import os
import uuid
from typing import Literal, Optional

import openai
from pydantic import BaseModel, Field

from matrix_kernel.config import get_city_config
from matrix_kernel.gazetteer import annotate_query_with_gazetteer
from matrix_kernel.graphrag import retrieve
from matrix_kernel.llm import generate_chat_completion, make_client
from matrix_kernel.scenario import Scenario


class ScenarioSchema(BaseModel):
    """Pydantic schema for the LLM to output."""
    description: str = Field(description="A brief description of the scenario.")
    intervention_type: Literal[
        "lane_closure", "full_closure", "speed_change", "capacity_change", "new_facility",
    ] = Field(
        description="The intervention class. lane_closure: some lanes closed, road stays open. "
                    "full_closure: the whole road impassable (flood, event, total reconstruction). "
                    "speed_change: a new speed limit. capacity_change: capacity added/removed "
                    "without closing the road (widening, road diet). new_facility: a school, "
                    "market, or terminal that changes travel demand (BEH-4), not road geometry.",
        default="lane_closure")
    location: str = Field(
        description=(
            "The road being edited, canonical street name only "
            "(e.g. 'Cuartero Street'). Never put segment/from/up to or a second street here. "
            "Leave empty string if the user named no street and there is no map-drop."
        ),
        default="",
    )
    from_cross: str = Field(
        description=(
            "Bounding cross street or landmark the segment starts at "
            "(e.g. 'Fajardo Street'). Empty string if the user did not name one."
        ),
        default="",
    )
    to_cross: str = Field(
        description=(
            "Bounding cross street or landmark the segment ends at "
            "(e.g. 'El 98 Street'). Empty string if the user did not name one."
        ),
        default="",
    )
    lanes_closed: int = Field(description="lane_closure only: number of lanes to close. Default is 1 if unspecified but implicitly a closure.", default=1)
    max_speed_kph: Optional[float] = Field(description="speed_change only: the new speed limit in km/h. Leave null if the user did not state or clearly imply one.", default=None)
    capacity_factor: Optional[float] = Field(description="capacity_change only: multiplicative capacity factor (e.g., 1.5 for +50% from widening, 0.7 for a road diet). Leave null if the user did not state or clearly imply one.", default=None)
    facility_kind: Optional[Literal["school", "market", "terminal"]] = Field(
        description="new_facility only: school, market, or terminal. Leave null if not stated.",
        default=None)
    capacity: Optional[int] = Field(
        description="new_facility only: seats, stalls, or bays the user stated. Leave null if unspecified — never invent a size.",
        default=None)
    is_ambiguous: bool = Field(description="Set to true if the query is too ambiguous to simulate (missing location or action).")
    clarification_prompt: str = Field(description="If is_ambiguous is true, provide a helpful prompt asking the user for the missing information.", default="")


def parse_scenario(
    query: str,
    client: Optional[openai.OpenAI] = None,
    geometry: Optional[dict] = None,
) -> Scenario:
    """Parse an NL query into a structured Scenario.

    `geometry` is an optional GeoJSON geometry dict (a map-drop Point/Polygon) supplied
    by the API out-of-band — it arrives as a structured field on POST /scenario, NOT via
    NL parsing (the LLM never originates geometry; PRD-F14). When present it is set on the
    returned Scenario verbatim, so the runner resolves edges from the drawn geometry
    (matrix_kernel.geometry) instead of the location keyword.
    """
    if not client:
        client = make_client()

    model_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5.4")
    city_name = get_city_config().name  # city-agnostic: Iloilo by default (CityConfig)

    system_instruction = (
        "You are the MATRIX Orchestrator. Your job is to parse natural language urban planning "
        f"queries into structured simulation parameters for {city_name}.\n"
        "Classify the intervention into exactly one type:\n"
        "- lane_closure: one or more lanes closed but the road stays open (roadworks, utility digs, "
        "parking-lane removal).\n"
        "- full_closure: the whole road becomes impassable (flooding, festival/event closure, "
        "total reconstruction).\n"
        "- speed_change: a new speed limit (traffic calming, school zone). Fill max_speed_kph.\n"
        "- capacity_change: capacity added or removed without closing the road (road widening, an "
        "added lane, a road diet). Fill capacity_factor (>1 adds capacity, <1 removes it).\n"
        "- new_facility: a school, market, or terminal that changes travel demand (BEH-4), not "
        "road geometry. Fill facility_kind and capacity only when the user stated them. Do not "
        "model this as a construction lane_closure.\n"
        "Only fill numeric parameters the user stated or clearly implied; otherwise leave them "
        "null/default -- never invent numbers.\n"
        "If the query lacks a location or an action (e.g., 'what if we build a school?' - where?), "
        "or a new_facility lacks a stated size, flag it as ambiguous and ask for clarification.\n"
        "Location is a SPAN, not a sentence.\n"
        "- location = the road being edited, canonical street name only.\n"
        "- from_cross / to_cross = the bounding streets or corners, each its own field, or \"\".\n"
        "- \"close Cuartero from Fajardo up to EL98\" → "
        "location=\"Cuartero Street\", from_cross=\"Fajardo Street\", to_cross=\"El 98 Street\"\n"
        "- \"close Cuartero Street\" → location=\"Cuartero Street\", from_cross=\"\", to_cross=\"\"\n"
        "- Never put \"segment\", \"from\", \"up to\", or a second street inside location.\n"
        "- Expand St/St. to Street. Expand EL98/EL 98 to \"El 98\".\n"
        "- You do not know GIS ids. Leave ids empty; the kernel matches names on the live net.\n"
        "- A named street with no bounding crosses is a whole-street closure, not ambiguous."
    )

    # Annotate colloquial terms with explicit GIS/OSM node hits (CR-008 Item 7)
    annotated_query = annotate_query_with_gazetteer(query)

    # Retrieve semantic context (CR-008 Item 9)
    chunks = retrieve(query, top_k=3)
    retrieved_context = ""
    if chunks:
        context_lines = [f"Source [{c['source']}]: {c['text']}" for c in chunks]
        retrieved_context = "\n\nRelevant Local Context:\n" + "\n".join(context_lines)

    # Resilient call: retry/backoff + hard timeout, typed LLMUnavailable on exhaustion
    # (matrix_kernel.llm). The orchestrator has no silent fallback — a parse failure must
    # surface (the API layer turns LLMUnavailable into a clear error), never a guessed scenario.
    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": annotated_query + retrieved_context}
    ]

    response = generate_chat_completion(
        client,
        model=model_name,
        messages=messages,
        response_format=ScenarioSchema,
        temperature=0.1,  # Low temperature for deterministic parsing
    )

    result = response.choices[0].message.parsed
    if not isinstance(result, ScenarioSchema):
        # In case the SDK didn't auto-parse into the Pydantic model (fallback)
        import json
        data = json.loads(response.choices[0].message.content)
        result = ScenarioSchema(**data)

    if result.is_ambiguous:
        raise ValueError(result.clarification_prompt or "The query is ambiguous. Please provide a location and action.")

    # Only the parameters relevant to the chosen type, and only when the model filled them
    # (the kernel applies documented defaults otherwise and records what it applied).
    parameters: dict = {}
    if result.intervention_type == "lane_closure":
        parameters["lanes_closed"] = result.lanes_closed
    elif result.intervention_type == "speed_change" and result.max_speed_kph is not None:
        parameters["max_speed_kph"] = result.max_speed_kph
    elif result.intervention_type == "capacity_change" and result.capacity_factor is not None:
        parameters["capacity_factor"] = result.capacity_factor
    elif result.intervention_type == "new_facility":
        if result.facility_kind is not None:
            parameters["facility_kind"] = result.facility_kind
        if result.capacity is not None:
            parameters["capacity"] = result.capacity

    from matrix_kernel.span import peel_span_fields

    loc, from_cross, to_cross = peel_span_fields(
        result.location, result.from_cross, result.to_cross
    )
    if from_cross:
        parameters["from_cross"] = from_cross
    if to_cross:
        parameters["to_cross"] = to_cross

    # `geometry` only ever carries a map-drop GeoJSON supplied structurally by the API
    # (PRD-F14: the LLM never originates it). For an NL-only query, the ground-truth
    # location-of-interest comes from the runner's own edge resolution at simulate time
    # (matrix_kernel.runner._resolve_edges -> Trajectory.meta["location_of_interest"],
    # surfaced over the /simulate WS's EDGE_COUNTS event) -- not a second, pre-simulation
    # guess here that could disagree with what actually got simulated.
    resolved_geometry = geometry if isinstance(geometry, dict) else None

    return Scenario(
        scenario_id=str(uuid.uuid4()),
        description=result.description,
        corridor=loc,         # legacy v1 channel -- /scenario consumers still read it
        lanes_closed=result.lanes_closed,
        intervention_type=result.intervention_type,
        location=loc,
        geometry=resolved_geometry,
        parameters=parameters,
    )
