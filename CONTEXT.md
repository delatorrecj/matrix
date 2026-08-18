# MATRIX — simulation map truth

Working language for the credibility / SUMO / location-of-interest work. Product glossary remains [docs/glossary-matrix.md](docs/glossary-matrix.md); this file is the session glossary for terms we are sharpening.

## Language

**Location of interest**:
A `[lon, lat]` the kernel may emit on honest simulate resolution (first affected-edge midpoint). It does **not** move the results-map camera and is not drawn as a glyph.
_Avoid_: pointer, pin, map marker

**Location marker**:
Magenta circle on the honest corridor midpoint, with a translucent halo and white ring so it reads on the dark basemap. Omitted on fallback.
_Avoid_: pointer, pin (those names the old cobalt GET /scenario marker)

**Affected corridor overlay**:
The GeoJSON halo of edges the kernel actually changed. Drawn only for geometry / live-gazetteer / keyword / gazetteer-alias resolution. Omitted on `busiest-baseline-fallback`.

**Corridor box**:
The padded bounding box of the affected corridor overlay. The **only** camera motion on the results map: fly to this box, or stay on the city default.

**Map truth**:
Camera and overlay match where the kernel intervened. First slice of this work.

**Intervention truth**:
A new-facility query (e.g. a 3,000-seat school) changes demand (`new_facility` / BEH-4), not a construction `lane_closure`. Second slice (not this sitting).

**SUMO proof**:
A live run on the full Iloilo net (local now; Hugging Face Space before a judged demo). The CI City Proper fixture is not this proof.

**Street alias**:
A gazetteer `street_name` used when the curated `sumo_edge` is missing from the live net. Molo → Avanceña Street; Diversion Road / Diversion Rd → Aquino Jr.

## Relationships

- Camera follows the **corridor box**, never `GET /scenario` gazetteer coordinates and never a location marker.
- Fallback resolution: overlay none, camera stays on the Iloilo default view.

## Decisions (grill 2026-08-17)

- Q5 **B**: pan only after honest simulate edges; do not pan from `GET /scenario`.
- Q6 **B**: corridor box only (no fly to a district centroid).
- Q7 **B**: gazetteer repair for Molo + Diversion Road aliases (not every district).
