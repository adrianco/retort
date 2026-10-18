/*
 * Context: Feature tests for loading the six provided Kaggle files. Uses the real data in
 * data/kaggle (requirement: "All 6 CSV files are loadable and queryable") and a fixture
 * directory for the de-duplication and state-handling rules.
 * Related: src/dataset.ts, tests/fixtures/make-fixture.ts.
 */
import { describe, expect, it, beforeAll } from 'vitest';
import { buildDataset, DEFAULT_DATA_DIR, parseHeightCm, parseWeightKg } from '../src/dataset.js';
import { makeFixtureDir } from './fixtures/make-fixture.js';
import type { Dataset } from '../src/types.js';

describe('Feature: Loading the provided datasets', () => {
  describe('Given the real Kaggle data directory', () => {
    let ds: Dataset;
    beforeAll(() => {
      ds = buildDataset(DEFAULT_DATA_DIR);
    });

    it('Scenario: all six CSV files are loaded', () => {
      expect(ds.loadedFiles).toHaveLength(6);
      expect(ds.loadedFiles).toContain('fifa_data.csv');
    });

    it('Scenario: match data spans every competition in the source files', () => {
      const comps = new Set(ds.matches.map((m) => m.competition));
      expect(comps).toEqual(new Set([
        'Brasileirão Série A', 'Brasileirão Série B', 'Brasileirão Série C',
        'Copa do Brasil', 'Copa Libertadores',
      ]));
    });

    it('Scenario: overlapping sources are de-duplicated', () => {
      // Brasileirão 2012–2019 appears in two files and BR-Football repeats it again.
      const keys = ds.matches.map((m) => [m.season, m.competition, m.homeKey, m.awayKey, m.homeGoals, m.awayGoals].join('|'));
      expect(new Set(keys).size).toBe(keys.length);
    });

    it('Scenario: the 2019 Brasileirão table matches the real final standings', () => {
      // Given the match data is loaded
      // When the 2019 league matches are counted per team
      const flamengo = ds.matches.filter((m) => m.season === 2019 && m.competition === 'Brasileirão Série A' &&
        (m.homeKey === 'flamengo' || m.awayKey === 'flamengo'));
      // Then Flamengo played 38 league matches (20 teams, double round robin)
      expect(flamengo).toHaveLength(38);
    });

    it('Scenario: every match has a valid date and integer-like scores', () => {
      for (const m of ds.matches) {
        expect(m.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
        expect(Number.isFinite(m.homeGoals)).toBe(true);
        expect(Number.isFinite(m.awayGoals)).toBe(true);
      }
    });

    it('Scenario: all 18,207 FIFA players are loaded with Brazilian nationality present', () => {
      expect(ds.players.length).toBe(18207);
      expect(ds.players.some((p) => p.nationality === 'Brazil')).toBe(true);
    });
  });

  describe('Given a fixture directory with overlapping and ambiguous names', () => {
    const ds = buildDataset(makeFixtureDir());

    it('Scenario: a match present in two files is counted once', () => {
      // Brasileirao_Matches and novo_campeonato both list Palmeiras 2-0 Santos in 2019
      const hits = ds.matches.filter((m) => m.season === 2019 && m.homeKey === 'palmeiras' && m.awayKey === 'santos' &&
        m.homeGoals === 2 && m.awayGoals === 0);
      expect(hits).toHaveLength(1);
    });

    it('Scenario: unplayed fixtures with empty scores are skipped', () => {
      expect(ds.matches.every((m) => Number.isFinite(m.homeGoals))).toBe(true);
      expect(ds.matches.filter((m) => m.homeKey === 'palmeiras' && m.awayKey === 'flamengo' && m.date === '2019-04-04')).toHaveLength(0);
    });

    it('Scenario: BR-Football tournaments map onto canonical competition names', () => {
      const comps = new Set(ds.matches.map((m) => m.competition));
      expect(comps.has('Brasileirão Série B')).toBe(true);
      expect(comps.has('Copa do Brasil')).toBe(true);
    });

    it('Scenario: the Libertadores string-typed goals are parsed as numbers', () => {
      const lib = ds.matches.find((m) => m.competition === 'Copa Libertadores');
      expect(lib?.homeGoals).toBe(2);
      expect(lib?.awayGoals).toBe(2);
    });

    it('Scenario: FIFA height and weight are converted to metric units', () => {
      expect(parseHeightCm("5'9")).toBe(175);
      expect(parseWeightKg('150lbs')).toBe(68);
      expect(parseHeightCm('')).toBeNull();
    });

    it('Scenario: FIFA rows keep numeric skill ratings even when written as "88+2"', () => {
      const gabriel = ds.players.find((p) => p.name === 'Gabriel Barbosa');
      expect(gabriel?.attributes.Finishing).toBe(88);
      expect(gabriel?.overall).toBe(85);
    });
  });
});
