import { describe, expect, it } from 'vitest';
import { loadDataset } from '../src/loader.js';
import { standings, filterMatches } from '../src/queries.js';

describe('Feature: Data coverage (provided Kaggle files)', () => {
  const dataset = loadDataset();

  describe('Scenario: All six CSV files are loadable and queryable', () => {
    it('Given the data directory, when loaded, then every file contributes rows', () => {
      expect(dataset.sources).toHaveLength(6);
      for (const source of dataset.sources) {
        expect(source.loaded, source.file).toBeGreaterThan(0);
      }
    });

    it('Given the FIFA file, then all 18,207 players are loaded', () => {
      expect(dataset.players).toHaveLength(18207);
    });

    it('Given the match files, then matches span 2003 to 2023 with ISO dates', () => {
      const seasons = dataset.matches.map((m) => m.season);
      expect(Math.min(...seasons)).toBe(2003);
      expect(Math.max(...seasons)).toBe(2023);
      expect(dataset.matches.every((m) => /^\d{4}-\d{2}-\d{2}$/.test(m.date))).toBe(true);
    });
  });

  describe('Scenario: Overlapping Brasileirão sources are not double-counted', () => {
    it('Given 2019 Série A results, then the table matches the published final points', () => {
      const table = standings(dataset, 'Brasileirão Série A', 2019);
      expect(table[0]).toMatchObject({ team: 'Flamengo', points: 90, played: 38 });
      expect(table.find((r) => r.team === 'Santos')?.points).toBe(74);
      expect(table.find((r) => r.team === 'Palmeiras')?.points).toBe(74);
    });

    it('Given the 2023 Série A, then there are 20 clubs and no club exceeds 38 games', () => {
      const table = standings(dataset, 'Brasileirão Série A', 2023);
      expect(table).toHaveLength(20);
      expect(table.every((r) => r.played <= 38)).toBe(true);
    });
  });

  it('Given the Libertadores file, then finals are identified by stage', () => {
    expect(filterMatches(dataset, { competition: 'Copa Libertadores', finalOnly: true }).length).toBeGreaterThan(0);
  });
});
