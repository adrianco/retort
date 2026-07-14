import { describe, it, expect, beforeAll } from 'vitest';
import { loadStore } from './setup.js';
import { findMatches, headToHead, biggestWins } from '../src/queries/matches.js';
import type { DataStore } from '../src/types.js';

/**
 * Feature: Match Queries
 *
 * Scenario: Find matches between two teams
 *   Given the match data is loaded
 *   When I search for matches between "Flamengo" and "Fluminense"
 *   Then I should receive a list of matches
 *   And each match should have date, scores, and competition
 */
describe('Feature: Match Queries', () => {
  let store: DataStore;
  beforeAll(async () => {
    store = await loadStore();
  });

  describe('Scenario: Find matches between two teams', () => {
    it('returns Flamengo vs Fluminense matches with dates, scores, competition', () => {
      const ms = findMatches(store.matches, {
        team: 'Flamengo',
        opponent: 'Fluminense',
      });
      expect(ms.length).toBeGreaterThan(5);
      for (const m of ms) {
        expect(m.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
        expect(typeof m.homeGoals).toBe('number');
        expect(typeof m.awayGoals).toBe('number');
        expect(['Brasileirão', 'Copa do Brasil', 'Libertadores', 'Other']).toContain(
          m.competition,
        );
        // Both teams must be involved
        const both = [m.homeKey, m.awayKey];
        expect(both).toContain('flamengo');
        expect(both).toContain('fluminense');
      }
    });
  });

  describe('Scenario: Find matches by team and season', () => {
    it('finds Palmeiras matches in 2019', () => {
      const ms = findMatches(store.matches, {
        team: 'Palmeiras',
        season: 2019,
      });
      expect(ms.length).toBeGreaterThan(10);
      for (const m of ms) {
        expect(m.season).toBe(2019);
        expect([m.homeKey, m.awayKey]).toContain('palmeiras');
      }
    });
  });

  describe('Scenario: Find matches by competition', () => {
    it('returns only Libertadores matches when filter set', () => {
      const ms = findMatches(store.matches, {
        competition: 'Libertadores',
        limit: 50,
      });
      expect(ms.length).toBeGreaterThan(0);
      for (const m of ms) {
        expect(m.competition).toBe('Libertadores');
      }
    });
  });

  describe('Scenario: Filter to home-only matches', () => {
    it('returns only home matches when homeOnly=true', () => {
      const ms = findMatches(store.matches, {
        team: 'Corinthians',
        season: 2018,
        competition: 'Brasileirão',
        homeOnly: true,
      });
      expect(ms.length).toBeGreaterThan(0);
      for (const m of ms) {
        expect(m.homeKey).toContain('corinthians');
      }
    });
  });

  describe('Scenario: Date range filtering', () => {
    it('respects dateFrom and dateTo bounds', () => {
      const ms = findMatches(store.matches, {
        dateFrom: '2019-01-01',
        dateTo: '2019-12-31',
        limit: 100,
      });
      expect(ms.length).toBeGreaterThan(0);
      for (const m of ms) {
        expect(m.date >= '2019-01-01').toBe(true);
        expect(m.date <= '2019-12-31').toBe(true);
      }
    });
  });

  describe('Scenario: Head-to-head record between two teams', () => {
    it('counts wins, draws, and aggregates goals', () => {
      const h = headToHead(store.matches, 'Flamengo', 'Fluminense');
      expect(h.matches.length).toBeGreaterThan(0);
      expect(h.teamAWins + h.teamBWins + h.draws).toBe(h.matches.length);
      expect(h.teamAGoals).toBeGreaterThanOrEqual(0);
      expect(h.teamBGoals).toBeGreaterThanOrEqual(0);
    });
  });

  describe('Scenario: Biggest victories in the dataset', () => {
    it('returns matches ordered by goal margin', () => {
      const ms = biggestWins(store.matches, { limit: 10 });
      expect(ms.length).toBe(10);
      const margins = ms.map((m) => Math.abs(m.homeGoals - m.awayGoals));
      for (let i = 1; i < margins.length; i++) {
        expect(margins[i] <= margins[i - 1]).toBe(true);
      }
      // The biggest margin in this dataset is at least 5 goals.
      expect(margins[0]).toBeGreaterThanOrEqual(5);
    });
  });
});
