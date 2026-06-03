"""XGBoost baseline forecaster + nightly baseline run (stub). Phase 2 (Gate 2).

train_baseline()       -- trains on CCHAIN + Overture/OSM trip generators to a
                          per-corridor trip-volume prior.
run_nightly_baseline() -- the nightly SUMO run that materializes
                          baseline:iloilo:latest in Redis so scenario runs are
                          deltas. The 90 s budget depends on this being hot
                          (RFC matrix-rfc-001).
"""
from __future__ import annotations


def train_baseline():
    raise NotImplementedError("XGBoost baseline forecaster -- Phase 2 (Gate 2)")


def run_nightly_baseline():
    raise NotImplementedError("nightly SUMO baseline -> Redis -- Phase 2 (Gate 2)")
