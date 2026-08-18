/**
 * Contract tests for the shipped public/layers/*.geojson samples.
 *
 * Glass box (PRD-F14): every shipped file must declare its honest status in a
 * `_provenance` foreign member, REAL files must carry their derivation, and
 * PROVISIONAL fixtures must say so inside the file — these tests make that
 * labeling non-optional.
 *
 * CR-007 PR 7: edges.geojson and confidence.geojson are now REAL exports from
 * the Iloilo SUMO net; the PROVISIONAL-guard tests have been updated accordingly.
 * flood.geojson remains a derived CCHAIN subset (< 100 KB); the larger SUMO
 * exports are lazily loaded on first toggle and are not size-constrained here.
 */
import { describe, it, expect } from 'vitest';
import { readFileSync, statSync } from 'node:fs';
import path from 'node:path';

import { isFeatureCollection } from '@/components/map/fetchStaticLayer';

const LAYERS_DIR = path.resolve(__dirname, '../../public/layers');

function loadLayer(name: string): { fc: any; bytes: number } {
  const file = path.join(LAYERS_DIR, `${name}.geojson`);
  return {
    fc: JSON.parse(readFileSync(file, 'utf-8')),
    bytes: statSync(file).size,
  };
}

describe('public/layers samples', () => {
  it.each(['flood', 'edges', 'confidence'])(
    '%s.geojson is a valid FeatureCollection with a _provenance status',
    (name) => {
      const { fc } = loadLayer(name);
      expect(isFeatureCollection(fc)).toBe(true);
      expect(['REAL', 'PROVISIONAL']).toContain(fc._provenance?.status);
    }
  );

  // flood.geojson is a derived CCHAIN subset — must stay small (not lazily loaded)
  it('flood.geojson is under 100 KB (derived CCHAIN subset)', () => {
    const { bytes } = loadLayer('flood');
    expect(bytes).toBeLessThan(100 * 1024);
  });

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

  // edges.geojson: REAL SUMO export (CR-007 PR 7). Previously PROVISIONAL placeholder.
  it('edges.geojson is REAL and satisfies the congestion contract shape', () => {
    const { fc } = loadLayer('edges');
    expect(fc._provenance.status).toBe('REAL');
    expect(fc._provenance.source).toMatch(/SUMO/i);
    expect(fc.features.length).toBeGreaterThan(0);
    for (const f of fc.features) {
      expect(f.geometry.type).toBe('LineString');
      expect(typeof f.properties.edge_id).toBe('string');
      // real SUMO edge ids must NOT look like PROVISIONAL placeholders
      expect(f.properties.edge_id).not.toMatch(/^PROVISIONAL-/);
    }
  });

  // confidence.geojson: REAL grid export (CR-007 PR 7). Not fetched by the results map.
  it('confidence.geojson is REAL with a documented tier rationale', () => {
    const { fc } = loadLayer('confidence');
    expect(fc._provenance.status).toBe('REAL');
    expect(fc._provenance.tier_rationale).toBeTruthy();
    expect(fc.features.length).toBeGreaterThan(0);
  });
});
