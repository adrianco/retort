import { describe, it, expect } from 'vitest';
import {
  normalizeTeam,
  parseDate,
  keyMatches,
  stripAccents,
} from '../src/normalize.js';

describe('normalize: team name variations', () => {
  it('drops state suffix variants', () => {
    expect(normalizeTeam('Palmeiras-SP')).toBe('palmeiras');
    expect(normalizeTeam('Palmeiras - SP')).toBe('palmeiras');
    expect(normalizeTeam('Palmeiras /SP')).toBe('palmeiras');
    expect(normalizeTeam('Palmeiras')).toBe('palmeiras');
  });

  it('drops parenthetical country codes', () => {
    expect(normalizeTeam('Nacional (URU)')).toBe('nacional');
    expect(normalizeTeam('Barcelona-EQU')).toBe('barcelona');
  });

  it('matches São Paulo with/without diacritics', () => {
    expect(normalizeTeam('São Paulo')).toBe(normalizeTeam('Sao Paulo'));
  });

  it('normalizes long-form club names', () => {
    expect(normalizeTeam('Sport Club Corinthians Paulista')).toContain(
      'corinthians',
    );
    expect(normalizeTeam('Aquidauanense Futebol Clube - MS')).toBe(
      'aquidauanense',
    );
  });

  it('keyMatches handles word-subset', () => {
    expect(keyMatches('atletico mineiro', 'atletico')).toBe(true);
    expect(keyMatches('atletico mineiro', 'mineiro')).toBe(true);
    expect(keyMatches('atletico mineiro', 'atletico mineiro')).toBe(true);
    expect(keyMatches('atletico mineiro', 'paranaense')).toBe(false);
  });

  it('stripAccents removes diacritics', () => {
    expect(stripAccents('Grêmio')).toBe('Gremio');
    expect(stripAccents('Avaí')).toBe('Avai');
  });
});

describe('normalize: date parsing', () => {
  it('handles ISO format', () => {
    expect(parseDate('2023-09-24')).toEqual({ date: '2023-09-24', time: undefined });
  });

  it('handles ISO with time', () => {
    expect(parseDate('2012-05-19 18:30:00')).toEqual({
      date: '2012-05-19',
      time: '18:30:00',
    });
  });

  it('handles Brazilian DD/MM/YYYY', () => {
    expect(parseDate('29/03/2003')).toEqual({ date: '2003-03-29' });
  });

  it('handles empty / null', () => {
    expect(parseDate('')).toEqual({ date: '' });
    expect(parseDate(null)).toEqual({ date: '' });
  });
});
