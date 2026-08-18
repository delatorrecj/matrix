# `public/layers/` — static map-layer data contract

Files here are served by Next.js at `/layers/{name}.geojson` and loaded with
`fetchStaticLayer(name)` (`src/components/map/fetchStaticLayer.ts`), which
resolves `null` for any missing/invalid file — every layer is optional and a
miss is a graceful no-op.

**Glass-box rule (PRD-F14):** every file must declare what it really is in a
top-level `_provenance` foreign member (RFC 7946 §6.1) with
`status: "REAL" | "PROVISIONAL"`. REAL files document source, derivation, and
vintage. PROVISIONAL files are dev fixtures whose values are invented — they
must say so *inside the file* and must never be presented as MATRIX output.

| File | Status | Size | Consumed by |
|---|---|---|---|
| `flood.geojson` | **REAL** (CCHAIN / Project NOAH derived) | ~50 KB | `floodLayer` |
| `edges.geojson` | **REAL** (exported from Iloilo SUMO net, CR-007 PR 7) | ~1.5 MB | `congestionLayer` |
| `confidence.geojson` | **REAL** (net bounding-box grid, tier M, CR-007 PR 7) | ~315 KB | shipped, not fetched by the results map |

These files are **lazily loaded** — fetched once on mount of the scenario page only when the relevant toggle is first activated, not on initial page render. The 100 KB constraint that appeared in an earlier version of this file applied to a size estimate that predated the real SUMO edge export (6,599 features). The actual sizes are declared above; browser caching (`Cache-Control: public, immutable`) means the fetch cost is paid once per session. Regenerate with `cd app/packages/kernel && uv run python ../data/export_net_geojson.py` (requires Docker + Redis with a seeded baseline and the SUMO net on disk).

## Schemas

### `edges.geojson` — congestion choropleth roads

```jsonc
{
  "type": "FeatureCollection",
  "_provenance": { "status": "REAL | PROVISIONAL", ... },
  "features": [{
    "type": "Feature",
    "geometry": { "type": "LineString", "coordinates": [[lon, lat], ...] },  // or MultiLineString
    "properties": { "edge_id": "<SUMO edge id>" }   // REQUIRED — must match Trajectory.edge_counts keys
  }]
}
```

`properties.edge_id` is the join key to the kernel's per-edge counts
(`Trajectory.edge_counts`, a `Record<string, number>` keyed by SUMO edge id —
`app/packages/kernel/matrix_kernel/trajectory.py`). An edge id absent from the
counts means zero recorded vehicles (rendered calm); a feature *without*
`edge_id` renders fully transparent. **As of CR-007 PR 7** the shipped file is
REAL — 6,599 trafficked edges from the named Iloilo SUMO net
(`iloilo.net.xml`, built by `build_network.py --output.street-names`, gitignored).
Regenerate with `export_net_geojson.py` if the net or baseline changes.

### `confidence.geojson` — unused heatmap cells (not fetched)

Shipped for provenance; the results map does not load or draw this file.

```jsonc
{
  "type": "FeatureCollection",
  "_provenance": { "status": "REAL | PROVISIONAL", ... },
  "features": [{
    "type": "Feature",
    "geometry": { "type": "Polygon", ... },          // or Point (→ fixed-size grid cell)
    "properties": {
      "confidence": "H" | "M" | "L",                  // REQUIRED — also accepts High/Medium/Low
      "basis": "where this tier comes from"           // strongly encouraged (glass box)
    }
  }]
}
```

Features without a recognizable tier are skipped — a tier is never guessed.
Real cells must come from *computed* confidences (kernel `DimensionResult`) or
the documented data-confidence map (`data/READINESS.md`), never hand-assigned.

### `flood.geojson` — flood-zone overlay

```jsonc
{
  "type": "FeatureCollection",
  "_provenance": { "status": "REAL", ... },
  "features": [{
    "type": "Feature",
    "geometry": { "type": "Polygon", ... },           // or MultiPolygon
    "properties": {
      "severity": "high" | "medium",                  // optional rendering hint
      // ...any honest attribution fields
    }
  }]
}
```

## Provenance of the shipped `flood.geojson` (REAL)

Derived 2026-06-13 from the repo's committed **Project CCHAIN Iloilo City
subset** (`data/processed/cchain_iloilo/`, HDX open license — attribute
Project CCHAIN; upstream hazard layer: Project NOAH):

1. Parse barangay polygons from `brgy_geography.csv` (WKT → GeoJSON,
   coordinates rounded to 6 decimals ≈ 0.1 m).
2. Join on `adm4_pcode` with `project_noah_hazards.csv`
   (100-year flood-hazard area shares) and `location.csv` (names).
3. Keep the 25 of 180 barangays with the highest
   `pct_area_flood_hazard_100yr_high + _med` (cutoff ≥ 37.22 %) so the file
   stays under 100 KB.
4. `severity` = `"high"` when the high-hazard share ≥ the medium-hazard share,
   else `"medium"`.

**Honest semantics:** features are *barangay administrative polygons*
attributed with the share of barangay area under each NOAH 100-year
flood-hazard level — **not hydraulic flood extents**. The full per-feature
provenance is embedded in the file's `_provenance` member.
