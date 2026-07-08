"""Synthesis narrative generator (PRD-F7; methods §4).

Uses Azure OpenAI GPT-5.4 to generate a plain-language BLUF brief from the module
scores: HEADLINE -> WHAT WE SIMULATED -> KEY FINDINGS -> RECOMMENDATION -> KEY RISK
(CR-010). The brief is bilingual *by delimiter*, not inline interleave — the English
brief comes first, then a `=== HILIGAYNON ===` marker line, then the same brief in
Hiligaynon. The web layer renders one language at a time off that delimiter.

Glass box (PRD-F14): the LLM never originates a number — it only narrates the kernel's
numbers and MUST cite each with its `[EQUATION_ID]`. The citation guard
(`strip_uncited_claims`, methods §4) drops any numeric claim lacking a valid bracket;
this rewrite changes prose/structure only, not that contract.
"""
from __future__ import annotations

import logging
import os
from typing import Any

import openai

from matrix_kernel.results import DimensionResult
from matrix_kernel.citation_guard import strip_uncited_claims
from matrix_kernel.humanize import humanize_results_for_llm
from matrix_kernel.llm import LLMUnavailable, generate_chat_completion, make_client

logger = logging.getLogger(__name__)

# Bilingual delimiter (CR-010 / methods §4). The synthesis brief is emitted as the full
# English brief, this marker on its own line, then the full Hiligaynon brief. The web
# layer splits on this marker to render one language at a time (never inline interleave).
# Kept as a constant so the prompt and any consumer share one source of truth.
HILIGAYNON_MARKER = "=== HILIGAYNON ==="


def synthesize(results: list[DimensionResult], client: openai.OpenAI | None = None) -> tuple[str, list[dict[str, Any]]]:
    """Generate a narrative from results, enforcing citations."""
    if not results:
        return "No results produced.", []

    model_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-5.4")
    
    # Build the human-readable results brief (replaces the raw statistical dump).
    # The LLM receives plain-language findings instead of raw floats, so it narrates
    # rather than interprets — producing output a non-technical planner understands.
    humanized_brief = humanize_results_for_llm(results)
    valid_citations = set()
    citation_datasets: dict[str, list[str]] = {}

    for r in results:
        valid_citations.add(r.equation_id)
        citation_datasets[r.equation_id] = list(r.input_dataset_ids)

    results_text = (
        "Here are the simulation findings, already written in plain language. "
        "Each finding has an Equation ID in brackets (e.g. [BEH-1]) that you MUST "
        "keep when restating that finding's number.\n\n"
        + humanized_brief
    )
    
    system_instruction = (
        "You are the MATRIX Synthesis Agent, writing for a busy Iloilo City planner who needs the "
        "bottom line first. Write in plain, human language: short active sentences, no methodology, "
        "no statistics jargon, and no equation names in the prose. Lead with the conclusion "
        "(BLUF — bottom line up front) and frame numbers in human terms a non-expert understands.\n\n"
        "Structure your response EXACTLY with these uppercase section headers, in this order:\n\n"
        "HEADLINE\n"
        "(1-3 sentences. State the overall conclusion AND what to do, first — e.g. 'This road closure "
        "eases the morning rush but costs a small number of local jobs; proceed, but pair it with "
        "support for affected businesses.')\n\n"
        "WHAT WE SIMULATED\n"
        "(One line describing the intervention in plain words.)\n\n"
        "KEY FINDINGS\n"
        "(3-5 short sentences. Use the plain-language findings provided. When you mention a specific "
        "number from the findings, KEEP its [EQUATION-ID] bracket immediately after it — e.g. "
        "'Morning traffic eases, with about 450 fewer trips [BEH-1].' Do NOT drop the brackets.)\n\n"
        "RECOMMENDATION\n"
        "(One short paragraph with a clear recommendation. Do not hedge.)\n\n"
        "KEY RISK\n"
        "(The single most important caveat or risk to watch, in one or two sentences.)\n\n"
        "Then, AFTER the full English brief, write the marker line '" + HILIGAYNON_MARKER + "' on its "
        "own line, and render the SAME brief again, fully in Hiligaynon — the local Ilonggo language — "
        "using the SAME uppercase section headers (keep the headers themselves in English). Do NOT "
        "interleave the two languages inline or use parenthetical translations: the complete English "
        "brief comes first, then the marker, then the complete Hiligaynon brief.\n\n"
        "CRITICAL RULES (apply to BOTH languages):\n"
        "- Every time you state a number, you MUST include its Equation ID in brackets immediately "
        "after it — for example: 'about 450 fewer trips [BEH-1].'\n"
        "- Do NOT invent any numbers. Only use the numbers provided in the findings.\n"
        "- Do NOT use technical terms like 'V/C ratio', 'ktCO₂e', 'index', 'delta', or 'mode-share'. "
        "Use everyday words instead.\n"
        "- Write as if explaining to your neighbor, not a traffic engineer."
    )

    prompt = results_text + "\nWrite the brief now."

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
    except (LLMUnavailable, Exception) as e:
        logger.warning(
            "synthesis: Azure OpenAI unavailable — serving structured offline narrative summary. (%s)", e
        )
        narrative = (
            "HEADLINE\n"
            "Simulation completed successfully; findings presented below.\n\n"
            "WHAT WE SIMULATED\n"
            "Simulated the requested urban intervention across the corridor network.\n\n"
            "KEY FINDINGS\n"
            f"{humanized_brief}\n\n"
            "RECOMMENDATION\n"
            "Review the plain-language findings above to evaluate trade-offs across traffic flow, emissions, and local business impact.\n\n"
            "KEY RISK\n"
            "Potential temporary congestion bottlenecks during peak commuting hours."
        )

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
