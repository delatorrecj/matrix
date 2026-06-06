"""Synthesis narrative generator (PRD-F7; methods §4).

Uses Gemini 3.1 Pro to generate per-dimension narratives from the module scores.
Must cite equation_id + dataset_ids for any number it asserts.
"""
from __future__ import annotations

import os
from typing import Any

from google import genai
from google.genai import types

from matrix_kernel.results import DimensionResult
from matrix_kernel.citation_guard import strip_uncited_claims


def synthesize(results: list[DimensionResult], client: genai.Client | None = None) -> tuple[str, list[dict[str, Any]]]:
    """Generate a narrative from results, enforcing citations."""
    if not results:
        return "No results produced.", []

    if not client:
        client = genai.Client()

    model_name = os.environ.get("GEMINI_MODEL_PRO", "gemini-3.1-pro")
    
    # Provide the results to the LLM
    results_text = "Here are the simulation results. You MUST cite the Equation ID in brackets e.g., [BEH-1] when mentioning ANY number from these results:\n\n"
    valid_citations = set()
    
    for r in results:
        valid_citations.add(r.equation_id)
        results_text += f"- {r.dimension.title()} ({r.equation_id}): {r.metric} = {r.value:.2f} {r.unit} (Range: {r.range[0]:.2f} to {r.range[1]:.2f}). Confidence: {r.confidence}.\n"
    
    system_instruction = (
        "You are the MATRIX Synthesis Agent. Your job is to write a cohesive, 2-3 paragraph "
        "summary of the urban planning simulation results for Iloilo City. "
        "CRITICAL RULE: Every time you state a number, you MUST include its Equation ID "
        "in brackets immediately after, for example: 'Trips increased by 450 [BEH-1].' "
        "Do not invent any numbers. Only use the numbers provided."
    )

    prompt = results_text + "\nWrite the summary narrative now."

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2,
            ),
        )
        narrative = response.text
    except Exception as e:
        print(f"Warning: Gemini synthesis failed ({e}).")
        narrative = "Synthesis narrative generation failed. Please see the raw data."

    # Enforce citation guard
    safe_narrative = strip_uncited_claims(narrative, valid_citations)
    
    # Build citations list
    citations = []
    for r in results:
        if f"[{r.equation_id}]" in safe_narrative:
            citations.append({
                "claim": f"Derived from {r.metric}",
                "equation_id": r.equation_id,
                "dataset_ids": r.input_dataset_ids,
            })

    if not safe_narrative.strip():
        safe_narrative = "The generated narrative was blocked because it lacked valid citations for its numerical claims."

    return safe_narrative, citations
