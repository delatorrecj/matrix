/**
 * Contract tests for the shipped public/layers/*.geojson samples.
 *
 * Glass box (PRD-F14): every shipped file must declare its honest status in a
 * `_provenance` foreign member, REAL files must carry their derivation, and
 * PROVISIONAL fixtures must say so inside the file — these tests make that
 * labeling non-optional.
 */
import { describe, it, expect, vi } from 'vitest';
import { readFileSync, statSync } from 'node:fs';
import path from 'node:path';

// confidenceLayer imports '@deck.gl/layers' (brittle in jsdom) — stub it out.
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

import { isFeatureCollection } from '@/components/map/fetchStaticLayer';
import { confidenceCellsFromGeoJSON } from '@/components/map/confidenceLayer';

const LAYERS_DIR = path.resolve(__dirname, '../../public/layers');

function loadLayer(name: string): { fc: any; bytes: number } {
  const file = path.join(LAYERS_DIR, `${name}.geojson`);
  return {
    fc: JSON.parse(readFileSync(file, 'utf-8')),
    bytes: statSync(file).size,
  };
}

const MAX_BYTES = 100 * 1024;

describe('public/layers samples', () => {
  it.each(['flood', 'edges', 'confidence'])(
    '%s.geojson is a valid FeatureCollection under 100 KB with a _provenance status',
    (name) => {
      const { fc, bytes } = loadLayer(name);
      expect(bytes).toBeLessThan(MAX_BYTES);
      expect(isFeatureCollection(fc)).toBe(true);
      expect(['REAL', 'PROVISIONAL']).toContain(fc._provenance?.status);
    }
  );

  it('flood.geojson is REAL with documented derivation, source, and honest semantics', () => {
    const { fc } = loadLayer('flood');
    expect(fc._provenance.status).toBe('REAL');
    expect(fc._provenance.source).toMatch(/CCHAIN/);
    expect(fc._provenance.derivation).toBeTruthy();
    expect(fc._provenance.semantics).toMatch(/NOT.*hydraulic flood extents/i);
    expect(fc.features.length).toBeGreaterThan(0);
    for (const f of fc.features) {
      expect(f.geometry.type).toBe('Polygon');
      expect(typeof f.properties.adm4_pcode).toBe('string');
      expect(f.properties.adm4_pcode).toMatch(/^PH063022/); // Iloilo City PSGC prefix
      expect(typeof f.properties.flood_100yr_high_pct).toBe('number');
      expect(typeof f.properties.flood_100yr_med_pct).toBe('number');
      expect(['high', 'medium']).toContain(f.properties.severity);
      // severity rule: "high" iff high-hazard share >= medium-hazard share
      expect(f.properties.severity).toBe(
        f.properties.flood_100yr_high_pct >= f.properties.flood_100yr_med_pct ? 'high' : 'medium'
      );
    }
  });

  it('edges.geojson is honestly PROVISIONAL and satisfies the congestion contract shape', () => {
    const { fc } = loadLayer('edges');
    expect(fc._provenance.status).toBe('PROVISIONAL');
    expect(fc._provenance.warning).toMatch(/NOT real SUMO edge ids/i);
    for (const f of fc.features) {
      expect(f.geometry.type).toBe('LineString');
      expect(typeof f.properties.edge_id).toBe('string');
      // placeholder ids must be unmistakable — never collide with real SUMO ids
      expect(f.properties.edge_id).toMatch(/^PROVISIONAL-/);
      expect(f.properties.provisional).toBe(true);
    }
  });

  it('confidence.geojson is honestly PROVISIONAL and converts cleanly to cells', () => {
    const { fc } = loadLayer('confidence');
    expect(fc._provenance.status).toBe('PROVISIONAL');
    expect(fc._provenance.warning).toMatch(/INVENTED/i);
    const cells = confidenceCellsFromGeoJSON(fc);
    expect(cells.length).toBe(fc.features.length); // every shipped feature is usable
    for (const cell of cells) {
      expect(['H', 'M', 'L']).toContain(cell.confidence);
      expect(cell.basis).toMatch(/PROVISIONAL/i); // the invented tier carries its own warning
    }
  });
});
