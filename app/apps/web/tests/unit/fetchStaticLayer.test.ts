/**
 * fetchStaticLayer — graceful no-op contract.
 * fetch is mocked; the network is never touched.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

import { fetchStaticLayer, isFeatureCollection } from '@/components/map/fetchStaticLayer';
import type { FeatureCollection } from '@/components/map/types';

const VALID_FC: FeatureCollection = {
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [122.56, 10.71] },
      properties: { confidence: 'H' },
    },
  ],
};

function response(status: number, body: unknown, jsonThrows = false) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: jsonThrows
      ? async () => {
          throw new SyntaxError('bad json');
        }
      : async () => body,
  } as Response;
}

describe('fetchStaticLayer', () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('fetches /layers/{name}.geojson and resolves the FeatureCollection', async () => {
    fetchMock.mockResolvedValue(response(200, VALID_FC));
    const fc = await fetchStaticLayer('flood');
    expect(fetchMock).toHaveBeenCalledWith('/layers/flood.geojson');
    expect(fc).toEqual(VALID_FC);
  });

  it('resolves null when the layer is not shipped (404)', async () => {
    fetchMock.mockResolvedValue(response(404, { error: 'not found' }));
    expect(await fetchStaticLayer('edges')).toBeNull();
  });

  it('resolves null on network failure', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));
    expect(await fetchStaticLayer('flood')).toBeNull();
  });

  it('resolves null on unparseable JSON', async () => {
    fetchMock.mockResolvedValue(response(200, null, true));
    expect(await fetchStaticLayer('flood')).toBeNull();
  });

  it('resolves null when the body is not a FeatureCollection', async () => {
    fetchMock.mockResolvedValue(response(200, { type: 'Feature' }));
    expect(await fetchStaticLayer('flood')).toBeNull();
    fetchMock.mockResolvedValue(response(200, [1, 2, 3]));
    expect(await fetchStaticLayer('flood')).toBeNull();
  });

  it('rejects unsafe names without fetching', async () => {
    expect(await fetchStaticLayer('../secret')).toBeNull();
    expect(await fetchStaticLayer('a/b')).toBeNull();
    expect(await fetchStaticLayer('')).toBeNull();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});

describe('isFeatureCollection', () => {
  it('accepts a FeatureCollection (foreign members tolerated)', () => {
    expect(isFeatureCollection(VALID_FC)).toBe(true);
    expect(isFeatureCollection({ ...VALID_FC, _provenance: { status: 'REAL' } })).toBe(true);
    expect(isFeatureCollection({ type: 'FeatureCollection', features: [] })).toBe(true);
  });

  it('rejects everything else', () => {
    expect(isFeatureCollection(null)).toBe(false);
    expect(isFeatureCollection('FeatureCollection')).toBe(false);
    expect(isFeatureCollection({ type: 'FeatureCollection' })).toBe(false);
    expect(isFeatureCollection({ type: 'FeatureCollection', features: [{ type: 'nope' }] })).toBe(false);
  });
});
