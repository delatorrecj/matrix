/**
 * Confidence heatmap — translucent overlay rendering H/M/L confidence cells.
 *
 * Cells carry EITHER a `polygon` (exterior ring of [lon, lat] pairs → rendered
 * with a PolygonLayer) OR a `position` ([lon, lat] → rendered with a
 * GridCellLayer of fixed `cellSizeM` metres). A mixed array yields both
 * sub-layers. Colors map H→success, M→warning, L→error (see colors.ts for the
 * token mapping); cells with an unrecognizable tier are SKIPPED, never guessed
 * (glass box, PRD-F14).
 */

import { GridCellLayer, PolygonLayer } from "@deck.gl/layers";
import type { Layer } from "@deck.gl/core";
import { CONFIDENCE_RGB, RGBA, withAlpha } from "./colors";
import type {
  ConfidenceCell,
  ConfidenceTier,
  Feature,
  FeatureCollection,
  LonLat,
} from "./types";

export const CONFIDENCE_POLYGON_LAYER_ID = "confidence-cells-polygon";
export const CONFIDENCE_GRID_LAYER_ID = "confidence-cells-grid";

/** Translucent fill — an overlay, not a curtain. */
const CELL_ALPHA = 90;

export interface ConfidenceLayerOptions {
  /** Edge length of point-anchored grid cells, metres. @default 250 */
  cellSizeM?: number;
}

/**
 * Normalize a confidence label to the H/M/L scale. Accepts the kernel's short
 * form ("H"/"M"/"L") and the long form ("High"/"Medium"/"Low"), any case.
 * Anything else → null (the cell is dropped, never guessed).
 */
export function normalizeConfidenceTier(value: unknown): ConfidenceTier | null {
  if (typeof value !== "string") return null;
  switch (value.trim().toLowerCase()) {
    case "h":
    case "high":
      return "H";
    case "m":
    case "medium":
      return "M";
    case "l":
    case "low":
      return "L";
    default:
      return null;
  }
}

function isLonLat(p: unknown): p is LonLat {
  return (
    Array.isArray(p) &&
    p.length >= 2 &&
    typeof p[0] === "number" &&
    typeof p[1] === "number" &&
    Number.isFinite(p[0]) &&
    Number.isFinite(p[1]) &&
    p[0] >= -180 &&
    p[0] <= 180 &&
    p[1] >= -90 &&
    p[1] <= 90
  );
}

function isValidRing(ring: unknown): ring is LonLat[] {
  return Array.isArray(ring) && ring.length >= 3 && ring.every(isLonLat);
}

interface NormalizedCell extends ConfidenceCell {
  confidence: ConfidenceTier;
}

function fillColor(cell: NormalizedCell): RGBA {
  return withAlpha(CONFIDENCE_RGB[cell.confidence], CELL_ALPHA);
}

/**
 * Build the confidence heatmap layer(s) from supplied cells.
 * Returns an array of 0–2 deck.gl layers (polygon cells, then grid cells);
 * an empty array when no cell is renderable.
 */
export function confidenceLayer(
  cells: ConfidenceCell[],
  options?: ConfidenceLayerOptions
): Layer[] {
  const polygonCells: NormalizedCell[] = [];
  const pointCells: NormalizedCell[] = [];

  for (const cell of Array.isArray(cells) ? cells : []) {
    const tier = normalizeConfidenceTier(cell?.confidence);
    if (tier === null) continue; // no tier → no cell (never guessed)
    const normalized: NormalizedCell = { ...cell, confidence: tier };
    if (isValidRing(cell.polygon)) {
      polygonCells.push(normalized);
    } else if (isLonLat(cell.position)) {
      pointCells.push(normalized);
    }
    // A cell with neither a valid polygon nor a valid position is skipped.
  }

  const layers: Layer[] = [];

  if (polygonCells.length > 0) {
    layers.push(
      new PolygonLayer<NormalizedCell>({
        id: CONFIDENCE_POLYGON_LAYER_ID,
        data: polygonCells,
        filled: true,
        stroked: false,
        extruded: false,
        getPolygon: (d: NormalizedCell) => d.polygon as LonLat[],
        getFillColor: fillColor,
        pickable: true,
      })
    );
  }

  if (pointCells.length > 0) {
    layers.push(
      new GridCellLayer<NormalizedCell>({
        id: CONFIDENCE_GRID_LAYER_ID,
        data: pointCells,
        cellSize: options?.cellSizeM ?? 250,
        extruded: false,
        getPosition: (d: NormalizedCell) => d.position as LonLat,
        getFillColor: fillColor,
        pickable: true,
      })
    );
  }

  return layers;
}

/**
 * Convert a GeoJSON FeatureCollection (e.g. public/layers/confidence.geojson,
 * via fetchStaticLayer) into ConfidenceCell[]: Polygon features become
 * polygon cells (exterior ring only), Point features become position cells.
 * The tier is read from `properties.confidence`; features without a
 * recognizable tier or a usable geometry are skipped.
 */
export function confidenceCellsFromGeoJSON(
  geojson: FeatureCollection
): ConfidenceCell[] {
  const cells: ConfidenceCell[] = [];
  const features: Feature[] = Array.isArray(geojson?.features)
    ? geojson.features
    : [];
  for (const f of features) {
    const tier = normalizeConfidenceTier(f?.properties?.confidence);
    if (tier === null) continue;
    const basis =
      typeof f.properties?.basis === "string" ? f.properties.basis : undefined;
    const geom = f.geometry;
    if (geom?.type === "Polygon" && isValidRing(geom.coordinates?.[0])) {
      cells.push({ polygon: geom.coordinates[0], confidence: tier, basis });
    } else if (geom?.type === "Point" && isLonLat(geom.coordinates)) {
      cells.push({ position: geom.coordinates, confidence: tier, basis });
    }
  }
  return cells;
}
