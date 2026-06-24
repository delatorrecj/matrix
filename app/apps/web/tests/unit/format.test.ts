import { describe, it, expect } from 'vitest';
import {
  formatMetricValue,
  formatRange,
  directionFor,
  confidenceWord,
  confidenceSentence,
} from '@/lib/format';

describe('formatMetricValue — kills false precision', () => {
  it('rounds the raw employment float to the registry decimals', () => {
    // -0.7000000000000001 jobs (ECON-3, 1 decimal, band 0.1)
    expect(formatMetricValue(-0.7000000000000001, 'ECON-3').display).toBe('-0.7');
  });

  it('collapses a near-zero composite to a plain-language label', () => {
    // -0.0069731280430000014 (SOCI-1, band 0.05)
    const r = formatMetricValue(-0.0069731280430000014, 'SOCI-1');
    expect(r.negligible).toBe(true);
    expect(r.display).toBe('No meaningful change');
  });

  it('treats an exact zero as no meaningful change', () => {
    expect(formatMetricValue(0, 'BEH-2').display).toBe('No meaningful change');
  });

  it('signs positive deltas and respects decimals', () => {
    expect(formatMetricValue(0.07, 'SOCI-4').display).toBe('+0.07');
  });

  it('groups large currency values with no decimals', () => {
    expect(formatMetricValue(-700, 'ECON-1').display).toBe('-700');
  });

  it('precise mode keeps detail without 17-digit artifacts and never collapses', () => {
    const r = formatMetricValue(-0.0069731280430000014, 'SOCI-1', { precise: true });
    expect(r.negligible).toBe(false);
    expect(r.display).toBe('-0.00697313');
  });

  it('falls back gracefully for an unknown equation id', () => {
    expect(formatMetricValue(-14, 'ZZZ-9').display).toBe('-14');
  });

  it('returns an em-dash for non-finite input', () => {
    expect(formatMetricValue(NaN, 'BEH-1').display).toBe('—');
  });
});

describe('formatRange', () => {
  it('renders "lo to hi" at summary precision, unsigned', () => {
    expect(formatRange([-918.46, -474.24], 'ECON-1')).toBe('-918 to -474');
  });

  it('returns empty string for a missing range', () => {
    expect(formatRange(null, 'ECON-1')).toBe('');
  });
});

describe('directionFor — polarity-aware wording', () => {
  it('a drop in a good-up metric worsens things', () => {
    expect(directionFor(-0.7, 'ECON-3', false)).toEqual({ word: 'worsens', tone: 'bad' });
  });

  it('a rise in a good-up metric improves things', () => {
    expect(directionFor(0.07, 'SOCI-4', false)).toEqual({ word: 'improves', tone: 'good' });
  });

  it('a neutral metric never implies a value judgment', () => {
    expect(directionFor(-14, 'BEH-1', false)).toEqual({ word: 'falls', tone: 'neutral' });
  });

  it('negligible reads as about the same', () => {
    expect(directionFor(-0.006, 'SOCI-1', true)).toEqual({ word: 'about the same', tone: 'neutral' });
  });
});

describe('confidence wording', () => {
  it('spells out the letter', () => {
    expect(confidenceWord('H')).toBe('High');
    expect(confidenceWord('M')).toBe('Medium');
    expect(confidenceWord(undefined)).toBe('Low');
  });

  it('gives a plain-language sentence per level', () => {
    expect(confidenceSentence('Low')).toMatch(/rough indication/i);
  });
});
