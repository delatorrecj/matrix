"""Gemini 3.1 Pro NL -> Scenario parser (PRD-F2, PRD-F8).

Turns a natural-language query ("what if we build a 3,000-seat school at Molo?")
into a structured Scenario dataclass. If the query is ambiguous or out of scope,
it raises an ValueError (which the API should catch to ask for clarification).
"""
from __future__ import annotations

import os
import uuid
from typing import Optional

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from matrix_kernel.runner import Scenario


class ScenarioSchema(BaseModel):
    """Pydantic schema for the LLM to output."""
    description: str = Field(description="A brief description of the scenario.")
    corridor: str = Field(description="The primary street name or corridor affected (e.g., 'Diversion Rd', 'Molo'). Extract from the user query. Leave empty string if not mentioned.", default="")
    lanes_closed: int = Field(description="Number of lanes to close. Default is 1 if unspecified but implicitly a closure, 0 if it's purely adding capacity.", default=1)
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

    return Scenario(
        scenario_id=str(uuid.uuid4()),
        description=result.description,
        corridor=result.corridor,
        lanes_closed=result.lanes_closed,
    )
