import { describe, it, expect, beforeAll } from 'vitest';
import { loadStore } from './setup.js';
import { seasonChampion, knockoutBracket } from '../src/queries/competitions.js';
import type { DataStore } from '../src/types.js';

/**
 * Feature: Competition Queries
 */
describe('Feature: Competition Queries', () => {
  let store: DataStore;
  beforeAll(async () => {
    store = await loadStore();
  });

  describe('Scenario: Identify season champion', () => {
    it('identifies Flamengo as 2019 Brasileirão champion', () => {
      const sc = seasonChampion(store.matches, 'Brasileirão', 2019);
      expect(sc).not.toBeNull();
      expect(sc!.champion.team.toLowerCase()).toContain('flamengo');
      expect(sc!.runnersUp.length).toBeGreaterThan(0);
      expect(sc!.runnersUp.length).toBeLessThanOrEqual(3);
    });

    it('returns null for a non-existent season', () => {
      const sc = seasonChampion(store.matches, 'Brasileirão', 1899);
      expect(sc).toBeNull();
    });
  });

  describe('Scenario: Knockout bracket for Libertadores', () => {
    it('groups Libertadores 2018 matches by stage', () => {
      const groups = knockoutBracket(store.matches, 'Libertadores', 2018);
      const stages = Object.keys(groups);
      expect(stages.length).toBeGreaterThan(1);
      // Each group should have matches sorted by date.
      for (const stage of stages) {
        const ms = groups[stage];
        for (let i = 1; i < ms.length; i++) {
          expect(ms[i].date >= ms[i - 1].date).toBe(true);
        }
      }
    });
  });
});
