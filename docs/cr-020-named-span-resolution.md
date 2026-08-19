# CR-020 — Named corridor spans on the live net

**Change Record ID:** CR-020
**Status:** Applied
**Date opened:** 2026-08-20
**Owner:** Yushin
**Trigger:** A planner named Cuartero Street from Fajardo St. to El 98 St. The gazetteer has none of those names. The orchestrator stuffed the span into `location`. Keyword-match required `location.lower()` ⊆ `edge.getName()`, so the net name `"Cuartero Street"` matched zero edges. Hash fallback painted the wrong busy edge; even a lucky whole-street match would close 24 directed edges and the magenta halo could only draw the one Cuartero feature in baseline `edges.geojson` (`-154184307#4`, west of Fajardo).

## Decision

Do not grow `gazetteer_iloilo.json` with OSM street names. The live SUMO net already names streets. The LLM emits names only; the kernel resolves them.

1. `location` is the corridor street only. Bounding crosses live in `Scenario.parameters` (`from_cross`, `to_cross`).
2. Live-net street index (normalized `St.`/`EL98`, token match) → **keyword-match**.
3. If crosses resolve to junctions on that corridor, clip the named-edge graph → **keyword-span** (both) or **keyword-span-open** (one). Off-corridor crosses keep the whole street and record `span_crosses_off_corridor`. Empty walk does not hash while a real corridor name is in hand.
4. Stuffed leftover phrases: longest live street name contained in `location` / `description`.
5. Unchanged **busiest-baseline-fallback** hash; `overlay_honest` stays false.
6. Closed-edge LineString shapes ride on EDGE_COUNTS / playback (`affected_edge_geoms`) so magenta follows the closed ids, not the baseline-trafficked static layer.

Ids never come from the LLM. Confidence letters and VAL-01 are unchanged.

## Files

- `app/packages/kernel/matrix_kernel/span.py` (new)
- `app/packages/kernel/matrix_kernel/runner.py` (`_resolve_edges` order)
- `app/packages/kernel/matrix_kernel/orchestrator.py` (`from_cross` / `to_cross`)
- `app/packages/kernel/matrix_kernel/geometry.py` (`affected_edge_features`)
- `app/apps/api/matrix_api/main.py` (EDGE_COUNTS + playback)
- `app/apps/web` Plan formatter, Inspect corridor site, halo merge
- `docs/methods-matrix.md` §4.2 (Locked, re-locked here)

## Out of scope

Barangay-polygon closures (CCHAIN Cuartero / Fajardo are barangays). VAL-01 PASS. Replacing SUMO. Map-drop geometry (still first in the order).
