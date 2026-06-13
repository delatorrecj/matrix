/**
 * Shared types for the map data layers (src/components/map).
 *
 * GeoJSON types are defined locally (structurally compatible with RFC 7946 and
 * with deck.gl's `data` prop) instead of importing from "geojson" — that types
 * package is only a *transitive* hoist in this workspace, not a declared
 * dependency, and relying on it would break on a future dedupe.
 */

export type LonLat = [number, number];

export interface PointGeometry {
  type: "Point";
  coordinates: LonLat;
}

export interface LineStringGeometry {
  type: "LineString";
  coordinates: LonLat[];
}

export interface MultiLineStringGeometry {
  type: "MultiLineString";
  coordinates: LonLat[][];
}

export interface PolygonGeometry {
  type: "Polygon";
  /** Ring 0 = exterior, rest = holes (RFC 7946 §3.1.6). */
  coordinates: LonLat[][];
}

export interface MultiPolygonGeometry {
  type: "MultiPolygon";
  coordinates: LonLat[][][];
}

export type Geometry =
  | PointGeometry
  | LineStringGeometry
  | MultiLineStringGeometry
  | PolygonGeometry
  | MultiPolygonGeometry;

export interface Feature<
  G extends Geometry = Geometry,
  P extends Record<string, unknown> = Record<string, unknown>,
> {
  type: "Feature";
  geometry: G;
  properties: P;
}

export interface FeatureCollection<F extends Feature = Feature> {
  type: "FeatureCollection";
  features: F[];
  /** RFC 7946 §6.1 foreign members (e.g. `_provenance`) are tolerated. */
  [foreignMember: string]: unknown;
}

/* ------------------------------------------------------------------------ */
/* Layer data contracts                                                      */
/* ------------------------------------------------------------------------ */

/**
 * Per-edge vehicle counts from the kernel — `Trajectory.edge_counts`
 * (packages/kernel/matrix_kernel/trajectory.py), keyed by SUMO edge id.
 * An absent key means SUMO recorded no vehicle entering that edge (count 0).
 */
export type EdgeCounts = Record<string, number>;

/** Road-segment feature for the congestion choropleth: a LineString (or
 * MultiLineString) carrying the SUMO edge id in `properties.edge_id`,
 * matching the keys of `EdgeCounts`. */
export type EdgeFeature = Feature<
  LineStringGeometry | MultiLineStringGeometry,
  { edge_id: string; [key: string]: unknown }
>;

export type EdgesFeatureCollection = FeatureCollection<EdgeFeature>;

/** Confidence tiers — same H/M/L scale the kernel's DimensionResult uses. */
export type ConfidenceTier = "H" | "M" | "L";

/**
 * One confidence-heatmap cell. Supply EITHER `polygon` (rendered as a filled
 * polygon) OR `position` (rendered as a fixed-size grid cell centred near it).
 * Cells without a valid tier are skipped — a tier is never guessed (PRD-F14).
 */
export interface ConfidenceCell {
  /** Exterior ring, [lon, lat] pairs (≥ 3 distinct positions). */
  polygon?: LonLat[];
  /** Cell anchor, [lon, lat]. Ignored when `polygon` is present. */
  position?: LonLat;
  confidence: ConfidenceTier;
  /** Optional human-readable basis for the tier (surfaces in picking info). */
  basis?: string;
}

/**
 * Toggle state consumed by `useMapLayers`. A superset of the LayerLegend ids —
 * `buildings` and `agents` are owned by the pages (PolygonLayer / TripsLayer)
 * and are deliberately NOT assembled here; unknown keys are ignored, so the
 * legend can grow additively without touching this module.
 */
export interface MapLayerToggles {
  buildings?: boolean;
  agents?: boolean;
  confidence?: boolean;
  congestion?: boolean;
  flood?: boolean;
  [layerId: string]: boolean | undefined;
}

/** Data inputs for `useMapLayers`. Absent/null entries simply omit the layer. */
export interface MapLayerData {
  /** Road segments for the congestion choropleth (see EdgeFeature contract). */
  edgesGeoJSON?: EdgesFeatureCollection | null;
  /** Scenario per-edge counts (Trajectory.edge_counts). */
  edgeCounts?: EdgeCounts | null;
  /** Nightly-baseline per-edge counts; when present the choropleth shows the
   * scenario-minus-baseline delta instead of absolute counts. */
  baselineCounts?: EdgeCounts | null;
  /** Confidence heatmap cells (e.g. from confidenceCellsFromGeoJSON). */
  confidenceCells?: ConfidenceCell[] | null;
  /** Flood-zone polygons (e.g. fetchStaticLayer("flood")). */
  floodGeoJSON?: FeatureCollection | null;
}
