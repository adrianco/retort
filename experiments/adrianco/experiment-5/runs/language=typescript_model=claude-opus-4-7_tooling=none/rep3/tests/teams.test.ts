import { describe, it, expect, beforeAll } from 'vitest';
import { loadStore } from './setup.js';
import { teamRecord, standings, topScoringTeams } from '../src/queries/teams.js';
import type { DataStore } from '../src/types.js';

/**
 * Feature: Team Queries
 *
 * Scenario: Get team statistics
 *   Given the match data is loaded
 *   When I request statistics for "Palmeiras" in season "2023"
 *   Then I should receive wins, losses, draws, and goals
 */
describe('Feature: Team Queries', () => {
  let store: DataStore;
  beforeAll(async () => {
    store = await loadStore();
  });

  describe('Scenario: Team record for a season', () => {
    it('returns wins, losses, draws, goals for Corinthians 2022 home Brasileirão', () => {
      const r = teamRecord(store.matches, 'Corinthians', {
        competition: 'Brasileirão',
        season: 2022,
        homeOnly: true,
      });
      // Sanity: number of matches and points should match wins/draws.
      expect(r.matches).toBeGreaterThan(0);
      expect(r.matches).toBe(r.wins + r.draws + r.losses);
      expect(r.points).toBe(r.wins * 3 + r.draws);
      expect(r.goalDifference).toBe(r.goalsFor - r.goalsAgainst);
    });
  });

  describe('Scenario: Calculate Brasileirão 2019 standings', () => {
    it('lists Flamengo as 2019 Brasileirão champion', () => {
      const table = standings(store.matches, {
        competition: 'Brasileirão',
        season: 2019,
      });
      expect(table.length).toBeGreaterThan(10);
      // Flamengo famously won 2019 Brasileirão with 90 points.
      expect(table[0].team.toLowerCase()).toContain('flamengo');
      // Best record: at least 24 wins.
      expect(table[0].wins).toBeGreaterThanOrEqual(24);
    });
  });

  describe('Scenario: Top scoring teams in a season', () => {
    it('returns teams ranked by goals scored', () => {
      const rows = topScoringTeams(store.matches, {
        competition: 'Brasileirão',
        season: 2019,
        limit: 5,
      });
      expect(rows.length).toBe(5);
      for (let i = 1; i < rows.length; i++) {
        expect(rows[i].goalsFor <= rows[i - 1].goalsFor).toBe(true);
      }
    });
  });

  describe('Scenario: Comparing two teams via team records', () => {
    it('Palmeiras and Santos both appear in 2018 standings', () => {
      const table = standings(store.matches, {
        competition: 'Brasileirão',
        season: 2018,
      });
      const teams = table.map((r) => r.team.toLowerCase());
      expect(teams.some((t) => t.includes('palmeiras'))).toBe(true);
      expect(teams.some((t) => t.includes('santos'))).toBe(true);
    });
  });
});
