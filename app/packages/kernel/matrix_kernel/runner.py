"""Unified simulation kernel -- TraCI runner (stub). PRD-F1, SDD §2, RFC RT-03/05.

simulate(scenario) computes a per-agent, per-tick trajectory dataset as a DELTA
against the cached nightly baseline (Redis: baseline:iloilo:latest). All five
impact modules score this one dataset -- the architectural reason results never
contradict across dimensions. Never fork into five independent simulators.

Verify the SUMO/TraCI API + the google-genai persona call shape against live docs
before implementing (docs/build-matrix.md §3). Phase 2 work (Gate 2).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    """A proposed project parsed by the Gemini orchestrator (PRD-F2).

    Geometry, project type, and parameters are filled in Phase 2/4; this skeleton
    freezes the identity fields the API and modules key off.
    """

    scenario_id: str
    description: str


def simulate(scenario: Scenario):
    """Run SUMO via TraCI -> trajectory dataset (delta vs baseline). Phase 2."""
    raise NotImplementedError("TraCI runner -- Phase 2 (Gate 2)")
