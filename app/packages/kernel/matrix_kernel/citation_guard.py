"""Citation guard (Phase 4.4 / methods §4).

Filters out any synthesis claim that asserts a number but lacks an inline
citation (e.g. `[BEH-1]`). Numbers must come from the kernel, never hallucinated.
"""
from __future__ import annotations

import re


def verify_citations(narrative: str, required_citations: set[str]) -> bool:
    """Check if numbers in the narrative are backed by a citation.
    
    A very simple heuristic: if there's a digit in a sentence, there should be
    a citation like [BEH-1] somewhere in that sentence, and that citation must
    be in the `required_citations` set.
    """
    sentences = re.split(r'(?<=[.!?]) +', narrative)
    for sentence in sentences:
        if re.search(r'\d', sentence):
            # There's a number. Is there a citation?
            citations_found = re.findall(r'\[([A-Z0-9-]+)\]', sentence)
            if not citations_found:
                return False
            for c in citations_found:
                if c not in required_citations:
                    return False
    return True


def strip_uncited_claims(narrative: str, valid_citations: set[str]) -> str:
    """Removes sentences that assert a number but lack a valid citation."""
    sentences = re.split(r'(?<=[.!?]) +', narrative)
    valid_sentences = []
    
    for sentence in sentences:
        if not sentence.strip():
            continue
        if re.search(r'\d', sentence):
            citations_found = re.findall(r'\[([A-Z0-9-]+)\]', sentence)
            is_valid = True
            if not citations_found:
                is_valid = False
            else:
                for c in citations_found:
                    if c not in valid_citations:
                        is_valid = False
            if is_valid:
                valid_sentences.append(sentence)
        else:
            valid_sentences.append(sentence)
            
    return " ".join(valid_sentences)
