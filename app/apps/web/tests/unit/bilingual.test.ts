import { describe, it, expect } from 'vitest';
import {
  HILIGAYNON_MARKER,
  splitBilingual,
  narrativeForLanguage,
  parseBlufSections,
} from '@/lib/bilingual';

const EN = [
  'HEADLINE',
  'The closure eases the rush; proceed with support for businesses.',
  '',
  'KEY FINDINGS',
  'Morning trips fall by 14 [BEH-1].',
].join('\n');

const HIL = [
  'HEADLINE',
  'Nagahupa ang trapiko; padayuna.',
  '',
  'KEY FINDINGS',
  'Nagnubo ang biyahe sang 14 [BEH-1].',
].join('\n');

const BILINGUAL = `${EN}\n\n${HILIGAYNON_MARKER}\n${HIL}`;

describe('splitBilingual — delimiter, not interleave', () => {
  it('splits the English and Hiligaynon halves on the marker', () => {
    const r = splitBilingual(BILINGUAL);
    expect(r.hasHiligaynon).toBe(true);
    expect(r.english).toBe(EN);
    expect(r.hiligaynon).toBe(HIL);
    // The marker itself never leaks into either half.
    expect(r.english).not.toContain('HILIGAYNON');
    expect(r.hiligaynon).not.toContain('===');
  });

  it('tolerates a flexible "=" run around the marker', () => {
    const wobbly = `${EN}\n==== HILIGAYNON ====\n${HIL}`;
    const r = splitBilingual(wobbly);
    expect(r.hasHiligaynon).toBe(true);
    expect(r.hiligaynon).toBe(HIL);
  });

  it('returns English-only with no marker (older runs)', () => {
    const r = splitBilingual(EN);
    expect(r.hasHiligaynon).toBe(false);
    expect(r.english).toBe(EN);
    expect(r.hiligaynon).toBe('');
  });

  it('handles undefined narrative', () => {
    const r = splitBilingual(undefined);
    expect(r).toEqual({ english: '', hiligaynon: '', hasHiligaynon: false });
  });
});

describe('narrativeForLanguage — picks one language, falls back to English', () => {
  it('returns the Hiligaynon half when requested and present', () => {
    expect(narrativeForLanguage(BILINGUAL, 'hil')).toBe(HIL);
  });

  it('returns English when requested', () => {
    expect(narrativeForLanguage(BILINGUAL, 'en')).toBe(EN);
  });

  it('falls back to English when Hiligaynon is absent (never empty)', () => {
    expect(narrativeForLanguage(EN, 'hil')).toBe(EN);
  });
});

describe('parseBlufSections — labelled BLUF extraction', () => {
  it('extracts each section body without the header', () => {
    const s = parseBlufSections(EN);
    expect(s.HEADLINE).toBe('The closure eases the rush; proceed with support for businesses.');
    expect(s['KEY FINDINGS']).toBe('Morning trips fall by 14 [BEH-1].');
    // Absent sections come back empty, never undefined.
    expect(s.RECOMMENDATION).toBe('');
    expect(s['KEY RISK']).toBe('');
    expect(s['WHAT WE SIMULATED']).toBe('');
  });

  it('returns all-empty sections for empty input', () => {
    const s = parseBlufSections('');
    expect(s.HEADLINE).toBe('');
    expect(s.RECOMMENDATION).toBe('');
  });
});
