import { describe, it, expect } from 'vitest';
import {
  normalizeTeam,
  teamMatches,
  parseDate,
  stripAccents,
  formatDate,
} from '../src/data/normalize.js';

describe('normalizeTeam', () => {
  it('strips state suffix "-SP"', () => {
    expect(normalizeTeam('Palmeiras-SP')).toBe('palmeiras');
  });
  it('strips state suffix "-RJ"', () => {
    expect(normalizeTeam('Flamengo-RJ')).toBe('flamengo');
  });
  it('handles long form "América - MG"', () => {
    expect(normalizeTeam('América - MG')).toBe('america');
  });
  it('strips parenthetical country code "Nacional (URU)"', () => {
    expect(normalizeTeam('Nacional (URU)')).toBe('nacional');
  });
  it('canonicalises full Corinthians name', () => {
    expect(normalizeTeam('Sport Club Corinthians Paulista')).toBe('corinthians');
  });
  it('canonicalises "Atlético-MG"', () => {
    expect(normalizeTeam('Atlético-MG')).toBe('atletico mineiro');
  });
});

describe('teamMatches', () => {
  it('matches Palmeiras with or without suffix', () => {
    expect(teamMatches('Palmeiras-SP', 'palmeiras')).toBe(true);
    expect(teamMatches('Palmeiras', 'palmeiras-sp')).toBe(true);
  });
  it('matches São Paulo with accent variations', () => {
    expect(teamMatches('São Paulo', 'sao paulo')).toBe(true);
  });
  it('does not match unrelated teams', () => {
    expect(teamMatches('Flamengo-RJ', 'palmeiras')).toBe(false);
  });
});

describe('parseDate', () => {
  it('parses ISO date', () => {
    const d = parseDate('2023-09-24');
    expect(d?.getUTCFullYear()).toBe(2023);
    expect(d?.getUTCMonth()).toBe(8); // September
    expect(d?.getUTCDate()).toBe(24);
  });
  it('parses Brazilian date DD/MM/YYYY', () => {
    const d = parseDate('29/03/2003');
    expect(d?.getUTCFullYear()).toBe(2003);
    expect(d?.getUTCMonth()).toBe(2);
    expect(d?.getUTCDate()).toBe(29);
  });
  it('parses ISO datetime', () => {
    const d = parseDate('2012-05-19 18:30:00');
    expect(d?.getUTCHours()).toBe(18);
  });
  it('returns null for garbage', () => {
    expect(parseDate('not a date')).toBeNull();
    expect(parseDate('')).toBeNull();
  });
});

describe('stripAccents', () => {
  it('removes Portuguese accents', () => {
    expect(stripAccents('São Paulo')).toBe('Sao Paulo');
    expect(stripAccents('Grêmio')).toBe('Gremio');
    expect(stripAccents('Avaí')).toBe('Avai');
  });
});

describe('formatDate', () => {
  it('formats as YYYY-MM-DD', () => {
    expect(formatDate(new Date(Date.UTC(2019, 0, 5)))).toBe('2019-01-05');
  });
});
