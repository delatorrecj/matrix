# META PROMPT — Named corridor spans on the live net

**Paste this into a coding agent when a planner names a street the gazetteer does not list, or asks to close only the segment between two cross streets.**

You are implementing against the MATRIX repo. You are not adding streets to `gazetteer_iloilo.json` by hand. You are not stuffing a prose span into `Scenario.location`. The live SUMO net already names the streets; the orchestrator must emit a **span**, and the kernel must **clip** it.

---

## Role

You are a kernel + orchestrator engineer on Team ATLAN.

**Ids come from the live net, never from the LLM.**
**The curated gazetteer is Hiligaynon / landmark aliases only.**
**A “from X up to Y” query is a span, not a longer location string.**

---

## The bug this prompt exists to kill

Fixture (must pass when you are done):

> Your question: *A full road closure on Cuartero Street, the segment starting from Fajardo St. up to EL98 st.*
> Plan today: `Full closure · Cuartero Street, segment from Fajardo St. to EL98 St.`

What happens today:

1. `resolve_colloquial_term` misses. `gazetteer_iloilo.json` has no Cuartero / Fajardo / El 98.
2. Orchestrator copies the whole span into `location`.
3. `_keyword_edges` requires `location.lower()` ⊆ SUMO `edge.getName()`. The net name is `"Cuartero Street"`. The stuffed phrase matches **zero** edges.
4. `_resolve_edges` hashes onto a busy baseline edge. `overlay_honest` is false. Magenta does not draw.
5. Even a lucky `location="Cuartero Street"` closes the **entire** tertiary (24 directed edges) and the magenta halo can only paint ids present in `public/layers/edges.geojson` (baseline-trafficked). That file has **one** Cuartero feature: `-154184307#4` (~33 m at 122.5516, 10.7263) — west of Fajardo, not Fajardo→El 98.

Ground truth on `deploy/hf-space/iloilo.net.xml` (also the kernel net):

| Name | OSM / SUMO | Role |
|---|---|---|
| Cuartero Street | way `154184307`, 24 directed edges | corridor |
| Fajardo Street | 16 directed edges; junction node `627794383` | from-cross |
| El 98 Street | 18 directed edges; junction cluster `cluster_767324203_8221271607_8221271609` | to-cross |

The asked block is Cuartero `154184307#10`–`#14` and the reverse `#14`–`#10` (Fajardo node → El 98 cluster). ~300 m in Jaro, about 122.554, 10.726 → 122.5555, 10.7235.

---

## Non-negotiable rules

1. **LLM outputs names only** (`Cuartero Street`, `Fajardo Street`, `El 98 Street`). Never OSM ids, never SUMO edge ids, never coordinates invented by the model. Kernel resolves names against `_net()`.
2. **`location` is the corridor street name only.** Cross streets live in structured span fields. Plan UI may still *display* “Cuartero Street from Fajardo Street to El 98 Street”; the kernel field must not.
3. **Do not grow `gazetteer_iloilo.json` to cover every OSM street.** Aliases stay colloquial (`tulay sa forbes`, `merkado`, `diversion`). Canonical street names resolve from the live net’s `edge.getName()`.
4. **Keyword match stays honest.** A stuffed span string is not a match. Tokenize / normalize, then match. Hash fallback remains last resort and still must not draw magenta (`map_truth.overlay_honest`).
5. **Magenta follows closed edges**, not “edges that happen to be in the 2026-06-16 baseline geojson.” If the static layer lacks a closed id, serve geometry from the net (or expand the export). A 33 m stub on the wrong side of Fajardo is a glass-box lie.
6. **Whole-street is the default** when the user did not name bounding crosses. Span clip runs only when `from_cross` and/or `to_cross` resolve to junctions on that corridor.
7. **methods-matrix §4.2 is Locked.** If you change `_resolve_edges` order or add a method string, file a Change Record and amend §4.2. New method labels: `keyword-span` (both crosses), `keyword-span-open` (one cross → end of named street), keep `keyword-match` / `gazetteer-*` / `busiest-baseline-fallback`.
8. **Spawn `module-kernel-builder` for runner/gazetteer, `frontend-3d-builder` for Plan + halo, `glass-box-auditor` then `eval-test-runner` before merge.**

---

## Target contract

### Orchestrator (`ScenarioSchema`)

Add optional fields (empty string = unset, never invent):

```text
location:     corridor street only, OSM/SUMO canonical if the user named a street
              e.g. "Cuartero Street"   not "Cuartero Street, segment from…"
from_cross:   bounding cross street or landmark the segment starts at
              e.g. "Fajardo Street"
to_cross:     bounding cross street or landmark the segment ends at
              e.g. "El 98 Street"
```

Map them onto `Scenario.parameters` (`from_cross`, `to_cross`) so the dataclass stays SUMO-free and v1 `location`/`corridor` stay the corridor keyword.

**Normalizer the model must apply before emit** (also re-run in kernel; LLM is sloppy):

- `St.` / `St` / `st.` → `Street` when the live net uses Street
- `EL98` / `EL 98` / `El98` → `El 98`
- Strip “the segment starting from”, “up to the corner of”, “between”, “from…to…”
- One street per field. “Fajardo St. up to EL98” is two fields, not one `location`

**Ambiguous only when** there is no corridor *and* no map-drop geometry. A named street with missing crosses is a whole-street closure, not a clarification loop.

### Kernel (`_resolve_edges`)

Order (geometry still wins):

1. Map-drop `geometry` → existing `resolve_geometry`
2. Gazetteer on `location` then `description` → existing `_gazetteer_edges` (aliases only)
3. **Live-net street index** on normalized `location` → all edges whose name matches the corridor (`keyword-match`)
4. If `from_cross` or `to_cross` is set, **clip** that corridor edge set to the span (`keyword-span` / `keyword-span-open`)
5. If step 3 misses: longest live street name that is a substring of `location` or `description` (handles a leftover stuffed phrase). Still not a gazetteer invent.
6. `busiest-baseline-fallback` as today

**Clip algorithm (deterministic, no LLM):**

1. Build adjacency of corridor edges (same normalized street name, both directions).
2. `junction_nodes(cross_name)` = nodes incident to at least one edge named like `cross_name`.
3. `from_nodes` / `to_nodes` = intersection of those nodes with corridor endpoints.
4. Walk the corridor graph from `from_nodes` to `to_nodes`. Keep every corridor edge on any shortest path (both directions).
5. If only one cross resolves: keep corridor edges on the component from that junction to the far end of the named street, and label `keyword-span-open`.
6. If neither cross intersects the corridor: keep the whole-street set, record assumption `span_crosses_off_corridor`, method stays `keyword-match`.
7. Empty walk → honest miss, then step 5/6. Do not silently hash while still holding a real corridor name.

Record in `Trajectory.meta`: `edge_resolution`, `affected_edges`, `from_cross`, `to_cross`, `span_nodes` (optional). `map_truth.overlay_honest` is true for `keyword-span*`.

### Overlay

`filterAffectedFeatures` today intersects closed ids with `public/layers/edges.geojson`. That export is **baseline-trafficked only**, so quiet tertiaries vanish.

Fix one of these (prefer the first):

- Include **closed-edge shapes** in the EDGE_COUNTS / playback payload (kernel already has the net; `edge_midpoint_lonlat` path exists), and draw magenta from that collection; or
- Re-export `edges.geojson` as all named edges (or all edges), not baseline-only.

Done when the Cuartero fixture paints magenta on `#10`–`#14` both ways, not on `-154184307#4` alone.

---

## Implementation order

1. **Red tests first** (no SUMO if possible; monkeypatch `_net` / fixture the 24 Cuartero + Fajardo + El 98 edges from the real ids above):
   - stuffed location string without span fields → must not hash if a live street name is contained; extracts `Cuartero Street`
   - `location=Cuartero Street`, `from_cross=Fajardo Street`, `to_cross=El 98 Street` → exactly `#10`–`#14` both directions
   - whole-street `Cuartero Street` → all 24
   - gazetteer still wins for `tulay sa forbes`
   - unknown place still `busiest-baseline-fallback`, `overlay_honest=false`
   - orchestrator mapping: schema span fields → `parameters`, `location` is corridor-only
2. **Name normalizer** shared by orchestrator post-parse and `_keyword_edges`.
3. **Span clip** in `runner.py` (or a tiny `span.py` next to `geometry.py`). Keep `geometry.py` for lon/lat predicates; span is graph-on-named-edges.
4. **Orchestrator prompt + `ScenarioSchema` fields.** Update `test_orchestrator_parse.py`. Plan formatter (`formatScenarioPlan`) may show `from_cross`/`to_cross` as “from A to B” without writing that prose back into `location`.
5. **Overlay geometry** so closed ids without baseline traffic still halo.
6. **methods-matrix §4.2 CR** if method strings / order change.
7. **glass-box-auditor** then **eval-test-runner**. Kernel `python -m pytest` must include the new tests. Do not delete or skip to go green.

---

## Orchestrator system addendum (drop into `parse_scenario` instructions)

```text
Location is a SPAN, not a sentence.
- location = the road being edited, canonical street name only.
- from_cross / to_cross = the bounding streets or corners, each its own field, or "".
- "close Cuartero from Fajardo up to EL98" →
    location="Cuartero Street", from_cross="Fajardo Street", to_cross="El 98 Street"
- "close Cuartero Street" → location="Cuartero Street", from_cross="", to_cross=""
- Never put "segment", "from", "up to", or a second street inside location.
- Expand St/St. to Street. Expand EL98/EL 98 to "El 98".
- You do not know GIS ids. Leave ids empty; the kernel matches names on the live net.
```

---

## Done when

- The Cuartero fixture resolves `keyword-span` to the Fajardo→El 98 block (ids `#10`–`#14` both ways).
- Magenta sits on that block in Jaro (~122.554–122.556, 10.723–10.726), not on a hashed busy edge, and not only on `-154184307#4`.
- A street that is in the net but not in `gazetteer_iloilo.json` still keyword-matches.
- A Hiligaynon gazetteer alias still gazetteer-matches.
- Inspect shows the method string and the corridor + cross names the kernel used.
- No new streets hand-copied into `gazetteer_iloilo.json` to make the fixture pass.

---

## Out of scope

- Barangay-polygon closures (CCHAIN `Cuartero` / `Fajardo` are barangays, not this street span).
- Replacing SUMO with a different engine.
- Claiming VAL-01 pass or raising confidence letters because spans resolve.
- Map-drop geometry (already wins; leave it first in the order).
