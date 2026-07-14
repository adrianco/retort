import { describe, it, expect } from 'vitest';
import { normalizeTeamName, teamKey, teamMatches, stripAccents } from '../src/normalize';

describe('Team name normalization', () => {
  it('strips trailing state suffix with dash', () => {
    expect(normalizeTeamName('Palmeiras-SP')).toBe('Palmeiras');
    expect(normalizeTeamName('Flamengo-RJ')).toBe('Flamengo');
    expect(normalizeTeamName('Athletico-PR')).toBe('Athletico');
  });

  it('strips trailing state suffix with spaces', () => {
    expect(normalizeTeamName('América - MG')).toBe('América');
  });

  it('strips parenthesized country code', () => {
    expect(normalizeTeamName('Nacional (URU)')).toBe('Nacional');
    expect(normalizeTeamName('Barcelona-EQU')).toBe('Barcelona');
  });

  it('keeps unrelated dash-suffixed words', () => {
    expect(normalizeTeamName('Real Madrid')).toBe('Real Madrid');
  });

  it('handles empty input', () => {
    expect(normalizeTeamName('')).toBe('');
    expect(normalizeTeamName(undefined)).toBe('');
    expect(normalizeTeamName(null)).toBe('');
  });

  it('produces consistent keys regardless of accents/case', () => {
    expect(teamKey('São Paulo')).toBe(teamKey('sao paulo'));
    expect(teamKey('Grêmio')).toBe(teamKey('Gremio'));
    expect(teamKey('Palmeiras-SP')).toBe(teamKey('palmeiras'));
  });

  it('matches teams across naming variations', () => {
    expect(teamMatches('Flamengo', 'Flamengo-RJ')).toBe(true);
    expect(teamMatches('Palmeiras', 'Palmeiras-SP')).toBe(true);
    expect(teamMatches('São Paulo', 'Sao Paulo')).toBe(true);
    expect(teamMatches('Flamengo', 'Fluminense')).toBe(false);
  });

  it('stripAccents removes diacritics', () => {
    expect(stripAccents('São Paulo')).toBe('Sao Paulo');
    expect(stripAccents('Grêmio')).toBe('Gremio');
    expect(stripAccents('Avaí')).toBe('Avai');
  });
});
