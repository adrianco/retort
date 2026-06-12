import { describe, it, expect } from 'vitest';
import { normalizeTeamName, teamsMatch, parseDate } from './normalizer.js';

describe('normalizeTeamName', () => {
  it('strips state suffix from team names', () => {
    expect(normalizeTeamName('Palmeiras-SP')).toBe('Palmeiras');
    expect(normalizeTeamName('Flamengo-RJ')).toBe('Flamengo');
    expect(normalizeTeamName('Sport-PE')).toBe('Sport');
  });

  it('preserves names without state suffix', () => {
    expect(normalizeTeamName('Palmeiras')).toBe('Palmeiras');
    expect(normalizeTeamName('Flamengo')).toBe('Flamengo');
  });

  it('trims whitespace', () => {
    expect(normalizeTeamName('  Flamengo-RJ  ')).toBe('Flamengo');
  });

  it('handles names with dashes that are not state suffixes', () => {
    expect(normalizeTeamName('Atlético-MG')).toBe('Atlético');
    expect(normalizeTeamName('América-MG')).toBe('América');
  });

  it('strips "- XX" format with space before dash', () => {
    expect(normalizeTeamName('Boavista - RJ')).toBe('Boavista');
  });
});

describe('teamsMatch', () => {
  it('matches identical team names', () => {
    expect(teamsMatch('Flamengo', 'Flamengo')).toBe(true);
  });

  it('matches with state suffix vs without', () => {
    expect(teamsMatch('Palmeiras-SP', 'Palmeiras')).toBe(true);
    expect(teamsMatch('Flamengo', 'Flamengo-RJ')).toBe(true);
  });

  it('is case-insensitive', () => {
    expect(teamsMatch('flamengo', 'Flamengo')).toBe(true);
    expect(teamsMatch('PALMEIRAS', 'palmeiras-sp')).toBe(true);
  });

  it('does partial matching for search', () => {
    expect(teamsMatch('Atletico', 'Atlético Mineiro')).toBe(true);
    expect(teamsMatch('atletico', 'Atletico-MG')).toBe(true);
    expect(teamsMatch('Sao Paulo', 'São Paulo')).toBe(true); // diacritics-insensitive match
  });

  it('does not match unrelated teams', () => {
    expect(teamsMatch('Flamengo', 'Fluminense')).toBe(false);
    expect(teamsMatch('Palmeiras', 'Santos')).toBe(false);
  });
});

describe('parseDate', () => {
  it('parses ISO datetime format', () => {
    const d = parseDate('2023-09-24');
    expect(d?.getFullYear()).toBe(2023);
    expect(d?.getMonth()).toBe(8); // 0-indexed
    expect(d?.getDate()).toBe(24);
  });

  it('parses datetime with time component', () => {
    const d = parseDate('2012-05-19 18:30:00');
    expect(d?.getFullYear()).toBe(2012);
    expect(d?.getMonth()).toBe(4);
    expect(d?.getDate()).toBe(19);
  });

  it('parses Brazilian format DD/MM/YYYY', () => {
    const d = parseDate('29/03/2003');
    expect(d?.getFullYear()).toBe(2003);
    expect(d?.getMonth()).toBe(2);
    expect(d?.getDate()).toBe(29);
  });

  it('returns null for empty/invalid input', () => {
    expect(parseDate('')).toBeNull();
    expect(parseDate('invalid')).toBeNull();
  });

  it('extracts year from date string', () => {
    const d = parseDate('2019-07-15');
    expect(d?.getFullYear()).toBe(2019);
  });
});
