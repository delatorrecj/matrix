"""Gemini 3.1 Pro NL -> Scenario parser (PRD-F2, PRD-F8).

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

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from matrix_kernel.scenario import Scenario


class ScenarioSchema(BaseModel):
    """Pydantic schema for the LLM to output."""
    description: str = Field(description="A brief description of the scenario.")
    intervention_type: Literal["lane_closure", "full_closure", "speed_change", "capacity_change"] = Field(
        description="The intervention class. lane_closure: some lanes closed, road stays open. "
                    "full_closure: the whole road impassable (flood, event, total reconstruction). "
                    "speed_change: a new speed limit. capacity_change: capacity added/removed "
                    "without closing the road (widening, road diet).",
        default="lane_closure")
    location: str = Field(description="The street, corridor, barangay, or landmark affected (e.g., 'Diversion Rd', 'Molo'). Extract from the user query. Leave empty string if not mentioned.", default="")
    lanes_closed: int = Field(description="lane_closure only: number of lanes to close. Default is 1 if unspecified but implicitly a closure.", default=1)
    max_speed_kph: Optional[float] = Field(description="speed_change only: the new speed limit in km/h. Leave null if the user did not state or clearly imply one.", default=None)
    capacity_factor: Optional[float] = Field(description="capacity_change only: multiplicative capacity factor (e.g., 1.5 for +50% from widening, 0.7 for a road diet). Leave null if the user did not state or clearly imply one.", default=None)
    is_ambiguous: bool = Field(description="Set to true if the query is too ambiguous to simulate (missing location or action).")
    clarification_prompt: str = Field(description="If is_ambiguous is true, provide a helpful prompt asking the user for the missing information.", default="")


def parse_scenario(query: str, client: Optional[genai.Client] = None) -> Scenario:
    """Parse an NL query into a structured Scenario."""
    if not client:
        client = genai.Client()  # Automatically picks up GOOGLE_API_KEY from environment

    model_name = os.environ.get("GEMINI_MODEL_PRO", "gemini-3.1-pro")

    system_instruction = (
        "You are the MATRIX Orchestrator. Your job is to parse natural language urban planning "
        "queries into structured simulation parameters for the city of Iloilo.\n"
        "Classify the intervention into exactly one type:\n"
        "- lane_closure: one or more lanes closed but the road stays open (roadworks, utility digs, "
        "parking-lane removal).\n"
        "- full_closure: the whole road becomes impassable (flooding, festival/event closure, "
        "total reconstruction).\n"
        "- speed_change: a new speed limit (traffic calming, school zone). Fill max_speed_kph.\n"
        "- capacity_change: capacity added or removed without closing the road (road widening, an "
        "added lane, a road diet). Fill capacity_factor (>1 adds capacity, <1 removes it).\n"
        "For new-facility proposals (a school, mall, terminal), model the construction-phase road "
        "impact as a lane_closure at the named location and say so in the description.\n"
        "Only fill numeric parameters the user stated or clearly implied; otherwise leave them "
        "null/default -- never invent numbers.\n"
        "If the query lacks a location or an action (e.g., 'what if we build a school?' - where?), "
        "flag it as ambiguous and ask for clarification."
    )

    response = client.models.generate_content(
        model=model_name,
        contents=query,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=ScenarioSchema,
            temperature=0.1,  # Low temperature for deterministic parsing
        ),
    )

    result = response.parsed
    if not isinstance(result, ScenarioSchema):
        # In case the SDK didn't auto-parse into the Pydantic model (fallback)
        import json
        data = json.loads(response.text)
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

    return Scenario(
        scenario_id=str(uuid.uuid4()),
        description=result.description,
        corridor=result.location,         # legacy v1 channel -- /scenario consumers still read it
        lanes_closed=result.lanes_closed,
        intervention_type=result.intervention_type,
        location=result.location,
        geometry=None,                    # map-drop GeoJSON arrives via the API, not NL parsing
        parameters=parameters,
    )
