"""Synthesis narrative generator (PRD-F7; methods §4).

Uses Azure OpenAI GPT-5.4 to generate per-dimension narratives from the module scores.
Must cite equation_id + dataset_ids for any number it asserts.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import openai

from matrix_kernel.results import DimensionResult
from matrix_kernel.citation_guard import strip_uncited_claims
from matrix_kernel.llm import LLMUnavailable, generate_chat_completion, make_client

logger = logging.getLogger(__name__)


def synthesize(results: list[DimensionResult], client: openai.AzureOpenAI | None = None) -> tuple[str, list[dict[str, Any]]]:
    """Generate a narrative from results, enforcing citations."""
    if not results:
        return "No results produced.", []

    model_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5.4")
    
    # Provide the results to the LLM
    results_text = "Here are the simulation results. You MUST cite the Equation ID in brackets e.g., [BEH-1] when mentioning ANY number from these results:\n\n"
    valid_citations = set()
    citation_datasets: dict[str, list[str]] = {}  # equation_id -> its dataset basis (methods §4)

    for r in results:
        valid_citations.add(r.equation_id)
        citation_datasets[r.equation_id] = list(r.input_dataset_ids)
        results_text += f"- {r.dimension.title()} ({r.equation_id}): {r.metric} = {r.value:.2f} {r.unit} (Range: {r.range[0]:.2f} to {r.range[1]:.2f}). Confidence: {r.confidence}.\n"
    
    system_instruction = (
        "You are the MATRIX Synthesis Agent. Your job is to write a cohesive summary of the urban planning simulation results for Iloilo City.\n"
        "Structure your response EXACTLY with these three sections, using these exact uppercase headers:\n\n"
        "EXECUTIVE SUMMARY\n"
        "(2-3 paragraphs of synthesis)\n\n"
        "ACTIONABLE RECOMMENDATIONS\n"
        "(2-3 concrete interventions based on the data)\n\n"
        "PERSONA PERSPECTIVES\n"
        "(How 1-2 specific stakeholders, e.g. a commuter or business owner, view these results)\n\n"
        "CRITICAL RULE: Every time you state a number, you MUST include its Equation ID "
        "in brackets immediately after, for example: 'Trips increased by 450 [BEH-1].' "
        "Do not invent any numbers. Only use the numbers provided."
    )

    prompt = results_text + "\nWrite the summary narrative now."

    try:
        if not client:
            client = make_client()
        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt}
        ]
        response = generate_chat_completion(
            client,
            model=model_name,
            messages=messages,
            temperature=0.2,
        )
        narrative = response.choices[0].message.content or ""
    except LLMUnavailable as e:
        logger.warning(
            "synthesis: Azure OpenAI unavailable after %d attempt(s) — serving the "
            "placeholder narrative. (%s)", e.attempts, e)
        narrative = "Synthesis narrative generation failed. Please see the raw data."

    # Enforce citation guard — a numeric claim must cite an equation_id that resolves to a
    # non-empty dataset basis (methods §4); passing the mapping enforces that basis.
    safe_narrative = strip_uncited_claims(narrative, valid_citations, citation_datasets)
    
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
