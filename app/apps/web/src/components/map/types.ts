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

/**
 * Toggle state consumed by `useMapLayers`. A superset of the LayerLegend ids —
 * `buildings` and `agents` are owned by the pages (PolygonLayer / TripsLayer)
 * and are deliberately NOT assembled here; unknown keys are ignored, so the
 * legend can grow additively without touching this module.
 */
export interface MapLayerToggles {
  buildings?: boolean;
  agents?: boolean;
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
  /** Flood-zone polygons (e.g. fetchStaticLayer("flood")). */
  floodGeoJSON?: FeatureCollection | null;
}
