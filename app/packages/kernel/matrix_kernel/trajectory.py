"""The frozen trajectory schema -- the ONE dataset every impact module scores (PRD-F1).

Both the baseline (baseline.py) and the scenario delta (runner.py) emit a `Trajectory`; the
five modules consume the *same* object, which is the architectural reason dimensions never
contradict. Frozen here at S5/U7 so the Phase-3 modules build against a stable shape. JSON-
serializable so it caches to Redis.

  edge_counts : edge_id -> number of vehicles that ENTERED the edge (volume). Drives BEH-1
                (Δ trips/corridor = scenario_count − baseline_count) and BEH-3 (V/C). Source:
                SUMO `edgeData` meandata.
  frames      : sampled playback frames -- scenario runs populate these (the baseline leaves
                them empty); they feed PLAYBACK_FRAME / the Deck.gl TripsLayer. Each agent is
                {"id", "lon", "lat", "mode"}.
  meta        : seed, net/demand versions, kind ("baseline"|"scenario"), counts, sim seconds.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class Frame:
    """One playback tick: every sampled agent's position + mode (for the TripsLayer)."""

    tick: float
    agents: list[dict]  # [{"id": str, "lon": float, "lat": float, "mode": str}, ...]


@dataclass(frozen=True)
class Trajectory:
    edge_counts: dict[str, int]
    frames: list[Frame] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(
            {
                "edge_counts": self.edge_counts,
                "frames": [asdict(f) for f in self.frames],
                "meta": self.meta,
            }
        )

    @classmethod
    def from_json(cls, s: str | bytes) -> "Trajectory":
        d = json.loads(s)
        return cls(
            edge_counts=dict(d["edge_counts"]),
            frames=[Frame(**f) for f in d.get("frames", [])],
            meta=d.get("meta", {}),
        )

    def observed_mode_share(self) -> dict[str, float]:
        """The realized mode share of the agents actually simulated (one count per unique
        agent id, mode being deterministic per id). This is the honest "what the run did"
        basis the bias auditor (PRD-F6) checks against the ground-truth anchor when no warmed
        persona-pool audit is available. Empty dict when the trajectory carries no agents."""
        modes: dict[str, int] = {}
        seen: set = set()
        for fr in self.frames:
            for a in fr.agents:
                aid = a.get("id")
                if aid in seen:
                    continue
                seen.add(aid)
                m = a.get("mode")
                if m is not None:
                    modes[m] = modes.get(m, 0) + 1
        n = sum(modes.values())
        if n == 0:
            return {}
        return {m: c / n for m, c in modes.items()}
