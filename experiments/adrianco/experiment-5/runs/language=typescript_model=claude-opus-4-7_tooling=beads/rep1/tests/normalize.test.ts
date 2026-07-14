import { describe, it, expect } from 'vitest';
import { normalizeTeamName, parseDate, parseSeason } from '../src/normalize';

describe('Feature: Team name normalization', () => {
  describe('Scenario: state-suffix variants resolve to a single key', () => {
    it.each([
      ['Palmeiras-SP', 'palmeiras'],
      ['Palmeiras', 'palmeiras'],
      ['Flamengo-RJ', 'flamengo'],
      ['Flamengo RJ', 'flamengo'],
      ['Vasco da Gama-RJ', 'vasco'],
      ['Vasco Da Gama RJ', 'vasco'],
      ['São Paulo', 'sao paulo'],
      ['São Paulo-SP', 'sao paulo'],
      ['Grêmio', 'gremio'],
      ['Grêmio-RS', 'gremio'],
      ['Sport Club Corinthians Paulista', 'corinthians'],
    ])('normalizes "%s" to "%s"', (input, expected) => {
      expect(normalizeTeamName(input)).toBe(expected);
    });
  });

  describe('Scenario: ambiguous short names keep their state', () => {
    it('keeps state for Atlético MG vs Atlético GO vs Atlético PR', () => {
      const mg = normalizeTeamName('Atlético-MG');
      const go = normalizeTeamName('Atlético-GO');
      const pr = normalizeTeamName('Atlético-PR');
      expect(mg).not.toBe(go);
      expect(mg).not.toBe(pr);
      expect(go).not.toBe(pr);
      expect(mg).toBe('atletico mineiro');
      expect(go).toBe('atletico goianiense');
      expect(pr).toBe('athletico paranaense');
    });

    it('keeps America MG distinct from America RN', () => {
      expect(normalizeTeamName('América-MG')).toBe('america mineiro');
      expect(normalizeTeamName('América-RN')).toBe('america rn');
    });
  });

  describe('Scenario: country-suffixed Libertadores teams strip the parens', () => {
    it.each([
      ['Nacional (URU)', 'nacional'],
      ['Barcelona-EQU', 'barcelona equ'],
    ])('normalizes "%s"', (input, expected) => {
      expect(normalizeTeamName(input)).toBe(expected);
    });
  });
});

describe('Feature: Date parsing across formats', () => {
  it.each([
    ['2023-09-24', '2023-09-24'],
    ['2012-05-19 18:30:00', '2012-05-19'],
    ['29/03/2003', '2003-03-29'],
    ['7/9/2010', '2010-09-07'],
    ['', ''],
  ])('parses "%s" → "%s"', (input, expected) => {
    expect(parseDate(input)).toBe(expected);
  });
});

describe('Feature: Season inference', () => {
  it('uses raw season when valid', () => {
    expect(parseSeason('2019')).toBe(2019);
    expect(parseSeason(2019)).toBe(2019);
  });
  it('falls back to year from date', () => {
    expect(parseSeason(undefined, '2018-03-22')).toBe(2018);
  });
  it('returns 0 when nothing provided', () => {
    expect(parseSeason(undefined, undefined)).toBe(0);
  });
});
