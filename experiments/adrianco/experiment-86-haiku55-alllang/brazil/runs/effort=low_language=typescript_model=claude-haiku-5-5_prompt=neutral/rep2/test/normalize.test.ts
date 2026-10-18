import { describe, expect, it } from 'vitest';
import {
  normalizeCompetition,
  normalizeTeam,
  parseDate,
  parseGoals,
  teamMatches,
} from '../src/normalize.js';

describe('Feature: Team name normalization', () => {
  describe('Scenario: Team names with state suffixes are matched', () => {
    it('Given "Palmeiras-SP", then the key is "palmeiras" and the state is SP', () => {
      const t = normalizeTeam('Palmeiras-SP');
      expect(t).toMatchObject({ name: 'Palmeiras', key: 'palmeiras', qualified: 'palmeiras-sp', state: 'SP' });
    });

    it('Given "Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", then the parenthetical and suffix are removed', () => {
      expect(normalizeTeam('Boavista Sport Club (antigo Esporte Clube Barreira) - RJ').key).toBe('boavista sport club');
    });

    it('Given "Nacional (URU)", then the country note is removed', () => {
      expect(normalizeTeam('Nacional (URU)').key).toBe('nacional');
    });
  });

  describe('Scenario: Official and alternative names resolve to the short name', () => {
    it.each([
      ['Sport Club Corinthians Paulista', 'corinthians'],
      ['Sociedade Esportiva Palmeiras', 'palmeiras'],
      ['Clube de Regatas do Flamengo', 'flamengo'],
      ['Atlético Mineiro', 'atletico'],
      ['Red Bull Bragantino', 'bragantino'],
      ['EC Bahia', 'bahia'],
      ['Fortaleza FC', 'fortaleza'],
    ])('Given "%s", then the key is "%s"', (raw, key) => {
      expect(normalizeTeam(raw).key).toBe(key);
    });

    it('Given accented and unaccented spellings, then they share a key', () => {
      expect(normalizeTeam('São Paulo').key).toBe(normalizeTeam('Sao Paulo').key);
      expect(normalizeTeam('Grêmio').key).toBe(normalizeTeam('Gremio').key);
    });
  });

  describe('Scenario: Queries with and without a state', () => {
    it('Given a bare query "Atletico", then it matches any Atletico with that key', () => {
      expect(teamMatches(normalizeTeam('Atletico'), normalizeTeam('Atletico-MG'))).toBe(true);
    });

    it('Given a stated query "Atletico-PR", then it does not match Atletico-MG', () => {
      expect(teamMatches(normalizeTeam('Atletico-PR'), normalizeTeam('Atletico-MG'))).toBe(false);
    });
  });
});

describe('Feature: Competition names', () => {
  it.each([
    ['Brasileirão', 'Brasileirão Série A'],
    ['serie a', 'Brasileirão Série A'],
    ['Série B', 'Brasileirão Série B'],
    ['Serie C', 'Brasileirão Série C'],
    ['Copa do Brasil', 'Copa do Brasil'],
    ['Copa Libertadores', 'Copa Libertadores'],
    ['Libertadores', 'Copa Libertadores'],
  ])('Given "%s", then it normalizes to "%s"', (raw, canonical) => {
    expect(normalizeCompetition(raw)).toBe(canonical);
  });

  it('Given an unknown competition, then it returns undefined', () => {
    expect(normalizeCompetition('Premier League')).toBeUndefined();
  });
});

describe('Feature: Date and goal parsing', () => {
  it.each([
    ['2023-09-24', '2023-09-24'],
    ['2012-05-19 18:30:00', '2012-05-19'],
    ['29/03/2003', '2003-03-29'],
  ])('Given "%s", then the date is %s', (raw, iso) => {
    expect(parseDate(raw)).toBe(iso);
  });

  it('Given an unrecognized date, then it returns undefined', () => {
    expect(parseDate('March 3rd')).toBeUndefined();
  });

  it('Given goal strings "2.0", "2", and "NA", then they parse to 2, 2, and undefined', () => {
    expect(parseGoals('2.0')).toBe(2);
    expect(parseGoals('2')).toBe(2);
    expect(parseGoals('NA')).toBeUndefined();
  });
});
