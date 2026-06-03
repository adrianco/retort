import { describe, it, expect, beforeAll } from 'vitest';
import { loadStore } from './setup.js';
import { overallStats, seasonsAvailable } from '../src/queries/stats.js';
import type { DataStore } from '../src/types.js';

/**
 * Feature: Statistical Analysis
 */
describe('Feature: Statistical Analysis', () => {
  let store: DataStore;
  beforeAll(async () => {
    store = await loadStore();
  });

  describe('Scenario: Compute overall stats for Brasileirão', () => {
    it('returns reasonable average goals/match and a positive home win rate', () => {
      const s = overallStats(store.matches, { competition: 'Brasileirão' });
      expect(s.matches).toBeGreaterThan(1000);
      expect(s.averageGoals).toBeGreaterThan(1.5);
      expect(s.averageGoals).toBeLessThan(4);
      // Home advantage in Brazilian football is well-documented.
      expect(s.homeWinRate).toBeGreaterThan(s.awayWinRate);
    });
  });

  describe('Scenario: List seasons available', () => {
    it('returns multiple Brasileirão seasons sorted ascending', () => {
      const seasons = seasonsAvailable(store.matches, 'Brasileirão');
      expect(seasons.length).toBeGreaterThan(5);
      for (let i = 1; i < seasons.length; i++) {
        expect(seasons[i].season > seasons[i - 1].season).toBe(true);
      }
      // Each season should have a sane number of matches.
      for (const s of seasons) {
        expect(s.matches).toBeGreaterThan(0);
      }
    });

    it('includes 2019 in the Brasileirão season list', () => {
      const seasons = seasonsAvailable(store.matches, 'Brasileirão');
      expect(seasons.some((s) => s.season === 2019)).toBe(true);
    });
  });
});
