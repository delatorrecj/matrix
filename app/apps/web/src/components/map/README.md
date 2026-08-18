# `src/components/map` — map data layers

Self-contained deck.gl layer factories + a `useMapLayers` hook for the data
layers the LayerLegend can toggle beyond the page-owned ones:

| Layer | Factory | deck.gl layer | Data source |
|---|---|---|---|
| Congestion choropleth | `congestionLayer(edgesGeoJSON, edgeCounts, baselineCounts?)` | `GeoJsonLayer` | kernel `Trajectory.edge_counts` + an edges GeoJSON |
| Flood overlay | `floodLayer(floodGeoJSON)` | `GeoJsonLayer` | `fetchStaticLayer("flood")` (CCHAIN/Project NOAH derived) |

The scenario results map wires this from `src/app/scenario/[id]/page.tsx`.
Agent trajectories are page-owned (`TripsLayer`) and auto-loop; there is no
playback chrome and no confidence heatmap.

## Factory signatures

```ts
congestionLayer(
  edgesGeoJSON: EdgesFeatureCollection, // LineString features w/ properties.edge_id
  edgeCounts: EdgeCounts,               // Record<string, number> — Trajectory.edge_counts
  baselineCounts?: EdgeCounts           // when present → delta-vs-baseline (diverging ramp)
): GeoJsonLayer | null                  // null when no features

floodLayer(
  floodGeoJSON: FeatureCollection       // Polygon/MultiPolygon features
): GeoJsonLayer | null                  // null when no features

useMapLayers(
  toggles: MapLayerToggles,             // superset toggle object — see below
  data: MapLayerData                    // absent/null entry → layer omitted, no crash
): Layer[]                              // ordered bottom→top: flood, congestion

fetchStaticLayer(name: "edges" | "flood" | string)
  : Promise<FeatureCollection | null>   // null on 404/network/parse miss — graceful no-op
```

## Toggle-object shape

`MapLayerToggles` is a superset of the LayerLegend ids so the legend can grow
additively (`{ buildings, agents, congestion, flood, ...unknown }`).
This hook assembles **only** `congestion` and `flood`;
`buildings` and `agents` remain page-owned (home `PolygonLayer`, scenario
`TripsLayer`), and unknown ids are ignored.

```ts
const [activeLayers, setActiveLayers] = useState<MapLayerToggles>({
  buildings: true, agents: true, congestion: true, flood: false,
});
```

## Integration sketch

```tsx
const dataLayers = useMapLayers(activeLayers, {
  edgesGeoJSON,            // fetchStaticLayer("edges") or a kernel-exported file
  edgeCounts,              // accumulate from the run; RESET on runAttempt like tripsData
  baselineCounts,          // optional — switches the ramp to delta mode
  floodGeoJSON,            // await fetchStaticLayer("flood")
});

<DeckGL layers={[...dataLayers, tripsLayer]} ... />  // trips animate on top
```

- The scenario page resets accumulated state per `runAttempt`
  (`src/lib/simulationRun.ts`) — any `edgeCounts` state you add must be reset in
  `retryRun()` alongside `tripsData`/`results`. Nothing in this module caches
  across runs.
- All layers are `pickable`; tooltips/inspect wiring is left to the page. Do
  not mount competing dialogs — the InspectDrawer ARIA modal owns z-40/50.

## Color encoding (design-token mapping)

deck.gl needs RGBA arrays, so `colors.ts` mirrors the `globals.css` `@theme`
tokens (keep in sync):

| Token | Hex | RGB | Meaning here |
|---|---|---|---|
| `--color-success` | `#15803D` | 21,128,61 | calm · calmer-than-baseline |
| `--color-warning` | `#B45309` | 180,83,9 | moderate congestion |
| `--color-error` | `#B91C1C` | 185,28,28 | heavy congestion · worse-than-baseline |
| `--color-primary` | `#1D4ED8` | 29,78,216 | flood water fill + outline |
| `--color-text-muted` | `#71717A` | 113,113,122 | diverging-ramp neutral midpoint (no change) |

Congestion: **absolute** mode ramps success→warning→error normalized by the max
count across the supplied features; **delta** mode (baseline provided) diverges
success←neutral→warning→error normalized by max |Δ|. Opacity and line width
scale with the normalized value. Features without `properties.edge_id` render
fully transparent (`NO_DATA_RGBA`) — a missing key is shown as nothing, never
as a guessed color (glass box, PRD-F14).

## Data contracts

Documented in [`public/layers/README.md`](../../../public/layers/README.md)
(static files + schemas, provenance of the shipped samples, PROVISIONAL
labeling rules). Key contract: congestion edges are GeoJSON LineString features
carrying the SUMO edge id in `properties.edge_id`, matching the keys of the
kernel's `Trajectory.edge_counts`.

deck.gl APIs verified against the installed pinned version
(`@deck.gl/layers@9.3.3` typings) per the verify-live-before-coding rule.
