"""Inject BEH-4 facility demand trips into a live SUMO run (intervention truth).

Caps injected vehicles for the 90 s latency budget. Routes are built with
``simulation.findRoute`` from nearest-edge lookups around each trip's origin
and destination.
"""
from __future__ import annotations

import uuid
from typing import Any

from matrix_kernel.demand_delta import DemandDelta, TripDelta

# Latency guard — full delta can be thousands of trips; inject a representative sample.
DEFAULT_MAX_INJECT = 80


def _nearest_edge(net: Any, lon: float, lat: float) -> str | None:
    xy = net.convertLonLat2XY(lon, lat)
    edges = net.getNeighboringEdges(xy[0], xy[1], r=150)
    if not edges:
        return None
    return edges[0][0].getID()


def inject_facility_demand(
    traci_mod: Any,
    net: Any,
    delta: DemandDelta,
    *,
    max_inject: int = DEFAULT_MAX_INJECT,
) -> dict:
    """Schedule facility trips on the active TraCI connection. Returns injection record."""
    pending = sorted(delta.trips, key=lambda t: t.depart_s)
    injected = 0
    skipped = 0
    conn = traci_mod

    for trip in pending:
        if injected >= max_inject:
            break
        from_edge = _nearest_edge(net, trip.origin_lonlat[0], trip.origin_lonlat[1])
        to_edge = _nearest_edge(net, trip.dest_lonlat[0], trip.dest_lonlat[1])
        if not from_edge or not to_edge or from_edge == to_edge:
            skipped += 1
            continue
        try:
            route = conn.simulation.findRoute(from_edge, to_edge)
            if route is None or route.edges is None or len(route.edges) == 0:
                skipped += 1
                continue
            route_id = f"beh4_route_{uuid.uuid4().hex[:10]}"
            conn.route.add(route_id, list(route.edges))
            veh_id = f"beh4_{uuid.uuid4().hex[:10]}"
            depart = max(0.0, float(trip.depart_s))
            conn.vehicle.add(veh_id, route_id, depart=str(depart), typeID="DEFAULT_VEHTYPE")
            injected += 1
        except Exception:
            skipped += 1

    return {
        "injected_vehicles": injected,
        "skipped_trips": skipped,
        "max_inject": max_inject,
        "demand_trips_total": delta.demand_trips_total,
        "assumptions": [
            f"BEH-4: injected up to {max_inject} gravity-sample trips via TraCI findRoute",
            "injected count is a latency-capped sample, not the full demand_trips_total",
        ],
    }
