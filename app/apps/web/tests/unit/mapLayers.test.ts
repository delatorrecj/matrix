/**
 * Map data layers — factory props/config and pure logic only.
 * Deck.gl is brittle in jsdom, so '@deck.gl/layers' is mocked with prop-capturing
 * stand-ins: we assert on the props the factories assemble, never on WebGL.
 */
import { describe, it, expect, vi } from 'vitest';
import { renderHook } from '@testing-library/react';

vi.mock('@deck.gl/layers', () => {
  class MockLayer {
    props: Record<string, any>;
    constructor(props: Record<string, any>) {
      this.props = props;
    }
  }
  return {
    GeoJsonLayer: class GeoJsonLayer extends MockLayer {},
    PolygonLayer: class PolygonLayer extends MockLayer {},
    GridCellLayer: class GridCellLayer extends MockLayer {},
  };
});

import { GeoJsonLayer, GridCellLayer, PolygonLayer } from '@deck.gl/layers';
import {
  TOKEN_RGB,
  CONFIDENCE_RGB,
  NO_DATA_RGBA,
  sequentialCongestionRGB,
  divergingCongestionRGB,
  withAlpha,
} from '@/components/map/colors';
import { congestionLayer, CONGESTION_LAYER_ID } from '@/components/map/congestionLayer';
import {
  confidenceLayer,
  normalizeConfidenceTier,
  CONFIDENCE_POLYGON_LAYER_ID,
  CONFIDENCE_GRID_LAYER_ID,
} from '@/components/map/confidenceLayer';
import { floodLayer, FLOOD_LAYER_ID } from '@/components/map/floodLayer';
import { useMapLayers } from '@/components/map/useMapLayers';
import type {
  ConfidenceCell,
  EdgesFeatureCollection,
  FeatureCollection,
  MapLayerData,
  MapLayerToggles,
} from '@/components/map/types';

/* ---------------------------------------------------------------- fixtures */

function edgeFeature(edgeId: string | null, coords: [number, number][] = [[122.56, 10.71], [122.57, 10.72]]) {
  return {
    type: 'Feature' as const,
    geometry: { type: 'LineString' as const, coordinates: coords },
    properties: edgeId === null ? ({} as any) : { edge_id: edgeId },
  };
}

const EDGES: EdgesFeatureCollection = {
  type: 'FeatureCollection',
  features: [edgeFeature('e1'), edgeFeature('e2'), edgeFeature('e3')],
};

const FLOOD: FeatureCollection = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      geometry: { type: 'Polygon', coordinates: [[[122.5, 10.7], [122.51, 10.7], [122.51, 10.71], [122.5, 10.7]]] },
      properties: { severity: 'high' },
    },
    {
      type: 'Feature',
      geometry: { type: 'Polygon', coordinates: [[[122.52, 10.7], [122.53, 10.7], [122.53, 10.71], [122.52, 10.7]]] },
      properties: { severity: 'medium' },
    },
  ],
};

const POLYGON_CELL: ConfidenceCell = {
  polygon: [[122.55, 10.7], [122.56, 10.7], [122.56, 10.71]],
  confidence: 'H',
};
const POINT_CELL: ConfidenceCell = { position: [122.56, 10.71], confidence: 'L' };

/* ------------------------------------------------------------------ colors */

describe('color ramps (design-token mirrors)', () => {
  it('sequential ramp hits the success/warning/error tokens at 0 / 0.5 / 1', () => {
    expect(sequentialCongestionRGB(0)).toEqual(TOKEN_RGB.success);
    expect(sequentialCongestionRGB(0.5)).toEqual(TOKEN_RGB.warning);
    expect(sequentialCongestionRGB(1)).toEqual(TOKEN_RGB.error);
  });

  it('sequential ramp clamps out-of-range and non-finite input', () => {
    expect(sequentialCongestionRGB(-5)).toEqual(TOKEN_RGB.success);
    expect(sequentialCongestionRGB(7)).toEqual(TOKEN_RGB.error);
    expect(sequentialCongestionRGB(NaN)).toEqual(TOKEN_RGB.success);
  });

  it('diverging ramp: -1 → success, 0 → neutral, +0.5 → warning, +1 → error', () => {
    expect(divergingCongestionRGB(-1)).toEqual(TOKEN_RGB.success);
    expect(divergingCongestionRGB(0)).toEqual(TOKEN_RGB.neutral);
    expect(divergingCongestionRGB(0.5)).toEqual(TOKEN_RGB.warning);
    expect(divergingCongestionRGB(1)).toEqual(TOKEN_RGB.error);
  });

  it('confidence tiers map H→success, M→warning, L→error', () => {
    expect(CONFIDENCE_RGB.H).toEqual(TOKEN_RGB.success);
    expect(CONFIDENCE_RGB.M).toEqual(TOKEN_RGB.warning);
    expect(CONFIDENCE_RGB.L).toEqual(TOKEN_RGB.error);
  });

  it('withAlpha clamps and rounds the alpha channel', () => {
    expect(withAlpha([1, 2, 3], 300)).toEqual([1, 2, 3, 255]);
    expect(withAlpha([1, 2, 3], -4)).toEqual([1, 2, 3, 0]);
    expect(withAlpha([1, 2, 3], 89.6)).toEqual([1, 2, 3, 90]);
  });
});

/* -------------------------------------------------------- congestion layer */

describe('congestionLayer', () => {
  it('builds a pickable GeoJsonLayer over the edges FeatureCollection', () => {
    const layer = congestionLayer(EDGES, { e1: 10 })!;
    expect(layer).toBeInstanceOf(GeoJsonLayer);
    expect(layer.props.id).toBe(CONGESTION_LAYER_ID);
    expect(layer.props.data).toBe(EDGES);
    expect(layer.props.filled).toBe(false);
    expect(layer.props.stroked).toBe(true);
    expect(layer.props.pickable).toBe(true);
    expect(layer.props.lineWidthUnits).toBe('pixels');
  });

  it('absolute mode: colors edges calm→congested normalized by the max count', () => {
    const layer = congestionLayer(EDGES, { e1: 0, e2: 50, e3: 100 })!;
    const color = layer.props.getLineColor;
    expect(color(EDGES.features[0])).toEqual(withAlpha(TOKEN_RGB.success, 70)); // calm, subtle
    expect(color(EDGES.features[1])).toEqual(withAlpha(TOKEN_RGB.warning, 70 + 75)); // mid
    expect(color(EDGES.features[2])).toEqual(withAlpha(TOKEN_RGB.error, 220)); // busiest
  });

  it('treats an edge id absent from the counts as zero traffic (calm), not missing', () => {
    const layer = congestionLayer(EDGES, { e3: 100 })!;
    expect(layer.props.getLineColor(EDGES.features[0])).toEqual(withAlpha(TOKEN_RGB.success, 70));
  });

  it('renders a feature without properties.edge_id fully transparent (no guessed color)', () => {
    const fc: EdgesFeatureCollection = {
      type: 'FeatureCollection',
      features: [edgeFeature(null) as any, edgeFeature('e1')],
    };
    const layer = congestionLayer(fc, { e1: 5 })!;
    expect(layer.props.getLineColor(fc.features[0])).toEqual(NO_DATA_RGBA);
    expect(layer.props.getLineWidth(fc.features[0])).toBe(0);
  });

  it('delta mode: diverges — calmer than baseline → success, worse → error', () => {
    const layer = congestionLayer(EDGES, { e1: 0, e2: 50, e3: 100 }, { e1: 50, e2: 50, e3: 50 })!;
    const color = layer.props.getLineColor;
    expect(color(EDGES.features[0])).toEqual(withAlpha(TOKEN_RGB.success, 220)); // -50 (max |Δ|)
    expect(color(EDGES.features[1])).toEqual(withAlpha(TOKEN_RGB.neutral, 70)); // no change
    expect(color(EDGES.features[2])).toEqual(withAlpha(TOKEN_RGB.error, 220)); // +50
  });

  it('flat counts (max 0) render every edge calm without dividing by zero', () => {
    const layer = congestionLayer(EDGES, {})!;
    for (const f of EDGES.features) {
      expect(layer.props.getLineColor(f)).toEqual(withAlpha(TOKEN_RGB.success, 70));
      expect(layer.props.getLineWidth(f)).toBe(2);
    }
  });

  it('scales line width with congestion', () => {
    const layer = congestionLayer(EDGES, { e1: 0, e3: 100 })!;
    expect(layer.props.getLineWidth(EDGES.features[0])).toBe(2);
    expect(layer.props.getLineWidth(EDGES.features[2])).toBe(8);
  });

  it('wires updateTriggers to the count objects so new runs recolor', () => {
    const counts = { e1: 1 };
    const baseline = { e1: 2 };
    const layer = congestionLayer(EDGES, counts, baseline)!;
    expect(layer.props.updateTriggers.getLineColor).toEqual([counts, baseline]);
    expect(layer.props.updateTriggers.getLineWidth).toEqual([counts, baseline]);
  });

  it('returns null when there are no features', () => {
    expect(congestionLayer({ type: 'FeatureCollection', features: [] }, { e1: 1 })).toBeNull();
    expect(congestionLayer({ type: 'FeatureCollection' } as any, { e1: 1 })).toBeNull();
  });
});

/* -------------------------------------------------------- confidence layer */

describe('confidenceLayer', () => {
  it('renders polygon cells with a translucent token color via PolygonLayer', () => {
    const layers = confidenceLayer([POLYGON_CELL]);
    expect(layers).toHaveLength(1);
    const layer = layers[0] as any;
    expect(layer).toBeInstanceOf(PolygonLayer);
    expect(layer.props.id).toBe(CONFIDENCE_POLYGON_LAYER_ID);
    expect(layer.props.extruded).toBe(false);
    expect(layer.props.getPolygon(layer.props.data[0])).toEqual(POLYGON_CELL.polygon);
    expect(layer.props.getFillColor(layer.props.data[0])).toEqual(withAlpha(TOKEN_RGB.success, 90));
  });

  it('renders position cells via GridCellLayer with the default 250 m cell', () => {
    const layers = confidenceLayer([POINT_CELL]);
    expect(layers).toHaveLength(1);
    const layer = layers[0] as any;
    expect(layer).toBeInstanceOf(GridCellLayer);
    expect(layer.props.id).toBe(CONFIDENCE_GRID_LAYER_ID);
    expect(layer.props.cellSize).toBe(250);
    expect(layer.props.extruded).toBe(false);
    expect(layer.props.getPosition(layer.props.data[0])).toEqual(POINT_CELL.position);
    expect(layer.props.getFillColor(layer.props.data[0])).toEqual(withAlpha(TOKEN_RGB.error, 90));
  });

  it('splits a mixed cell array into both sub-layers and honors cellSizeM', () => {
    const layers = confidenceLayer([POLYGON_CELL, POINT_CELL], { cellSizeM: 500 });
    expect(layers).toHaveLength(2);
    expect((layers[0] as any).props.id).toBe(CONFIDENCE_POLYGON_LAYER_ID);
    expect((layers[1] as any).props.id).toBe(CONFIDENCE_GRID_LAYER_ID);
    expect((layers[1] as any).props.cellSize).toBe(500);
  });

  it('skips cells with an unrecognizable tier or no usable geometry (never guesses)', () => {
    const layers = confidenceLayer([
      { polygon: POLYGON_CELL.polygon, confidence: 'X' as any },
      { confidence: 'H' }, // no polygon, no position
      { position: [999, 999], confidence: 'M' }, // out-of-range lon/lat
    ]);
    expect(layers).toHaveLength(0);
  });

  it('accepts long-form tiers (High/Medium/Low) via normalization', () => {
    expect(normalizeConfidenceTier('High')).toBe('H');
    expect(normalizeConfidenceTier('medium')).toBe('M');
    expect(normalizeConfidenceTier(' low ')).toBe('L');
    expect(normalizeConfidenceTier('certain')).toBeNull();
    expect(normalizeConfidenceTier(3)).toBeNull();
    const layers = confidenceLayer([{ ...POINT_CELL, confidence: 'Low' as any }]);
    expect((layers[0] as any).props.getFillColor((layers[0] as any).props.data[0])).toEqual(
      withAlpha(TOKEN_RGB.error, 90)
    );
  });
});

/* ------------------------------------------------------------- flood layer */

describe('floodLayer', () => {
  it('builds a translucent fill + outline GeoJsonLayer in the primary blue', () => {
    const layer = floodLayer(FLOOD)!;
    expect(layer).toBeInstanceOf(GeoJsonLayer);
    expect(layer.props.id).toBe(FLOOD_LAYER_ID);
    expect(layer.props.filled).toBe(true);
    expect(layer.props.stroked).toBe(true);
    expect(layer.props.getLineColor).toEqual(withAlpha(TOKEN_RGB.primary, 180));
    expect(layer.props.getFillColor(FLOOD.features[0])).toEqual(withAlpha(TOKEN_RGB.primary, 95)); // high
    expect(layer.props.getFillColor(FLOOD.features[1])).toEqual(withAlpha(TOKEN_RGB.primary, 60)); // medium
  });

  it('uses the default fill for features without a severity hint', () => {
    const fc: FeatureCollection = {
      type: 'FeatureCollection',
      features: [{ ...FLOOD.features[0], properties: {} }],
    };
    const layer = floodLayer(fc)!;
    expect(layer.props.getFillColor(fc.features[0])).toEqual(withAlpha(TOKEN_RGB.primary, 60));
  });

  it('returns null when there are no features', () => {
    expect(floodLayer({ type: 'FeatureCollection', features: [] })).toBeNull();
  });
});

/* ------------------------------------------------------------ useMapLayers */

describe('useMapLayers', () => {
  const ALL_ON: MapLayerToggles = {
    buildings: true,
    agents: true,
    congestion: true,
    confidence: true,
    flood: true,
  };
  const ALL_DATA: MapLayerData = {
    edgesGeoJSON: EDGES,
    edgeCounts: { e1: 1, e2: 2, e3: 3 },
    confidenceCells: [POLYGON_CELL, POINT_CELL],
    floodGeoJSON: FLOOD,
  };

  function run(toggles: MapLayerToggles, data: MapLayerData) {
    return renderHook(() => useMapLayers(toggles, data)).result.current;
  }

  it('assembles flood → congestion → confidence (bottom to top) when all on', () => {
    const layers = run(ALL_ON, ALL_DATA);
    expect(layers.map((l: any) => l.props.id)).toEqual([
      FLOOD_LAYER_ID,
      CONGESTION_LAYER_ID,
      CONFIDENCE_POLYGON_LAYER_ID,
      CONFIDENCE_GRID_LAYER_ID,
    ]);
  });

  it('omits layers whose toggle is off', () => {
    const layers = run({ ...ALL_ON, congestion: false, flood: false }, ALL_DATA);
    expect(layers.map((l: any) => l.props.id)).toEqual([
      CONFIDENCE_POLYGON_LAYER_ID,
      CONFIDENCE_GRID_LAYER_ID,
    ]);
  });

  it('omits toggled-on layers whose data is absent — no crash, no placeholder', () => {
    expect(run(ALL_ON, {})).toEqual([]);
    expect(run(ALL_ON, { edgesGeoJSON: EDGES })).toEqual([]); // counts missing too
    expect(run(ALL_ON, { confidenceCells: [] })).toEqual([]);
    expect(
      run(ALL_ON, { edgesGeoJSON: null, edgeCounts: null, confidenceCells: null, floodGeoJSON: null })
    ).toEqual([]);
  });

  it('ignores page-owned (buildings/agents) and unknown toggle ids', () => {
    const layers = run(
      { buildings: true, agents: true, futureLayer: true, congestion: false, confidence: false, flood: false },
      ALL_DATA
    );
    expect(layers).toEqual([]);
  });

  it('delta mode flows through to the congestion factory', () => {
    const layers = run(
      { congestion: true },
      { edgesGeoJSON: EDGES, edgeCounts: { e1: 10 }, baselineCounts: { e1: 20 } }
    );
    expect(layers).toHaveLength(1);
    // calmer than baseline → success side of the diverging ramp
    expect((layers[0] as any).props.getLineColor(EDGES.features[0])).toEqual(
      withAlpha(TOKEN_RGB.success, 220)
    );
  });
});
