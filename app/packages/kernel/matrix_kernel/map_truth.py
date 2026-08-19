"""Map-truth contract — kernel owns overlay honesty (CR-013 / CONTEXT.md Q5–Q7).

The results map must not re-parse ``edge_resolution`` strings on the client.
``overlay_honest`` is computed once here from the resolution method recorded in
Trajectory.meta. Camera follows the corridor box; ``location_of_interest`` is the
SUMO midpoint of the first honest affected edge (or null).
"""
from __future__ import annotations


def overlay_honest(edge_resolution: str | None) -> bool:
    """True when an affected-corridor overlay is honest (geometry/gazetteer/keyword/alias)."""
    if not edge_resolution or not isinstance(edge_resolution, str):
        return False
    if edge_resolution == "facility-demand":
        return False
    return not edge_resolution.startswith("busiest-baseline-fallback")


def map_truth_fields(
    affected_edges: list[str],
    edge_resolution: str,
    location_of_interest: list[float] | None,
) -> dict:
    """Public map-truth DTO fields for HTTP/WS adapters."""
    honest = overlay_honest(edge_resolution)
    return {
        "overlay_honest": honest,
        "affected_edges": affected_edges if honest else [],
        "edge_resolution": edge_resolution,
        "location_of_interest": location_of_interest if honest else None,
    }
