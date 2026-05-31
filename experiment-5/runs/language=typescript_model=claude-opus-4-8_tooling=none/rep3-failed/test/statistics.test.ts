/**
 * ============================================================================
 * Context Block — File: test/statistics.test.ts
 * Project: Brazilian Soccer MCP Server
 * Purpose: BDD specs for capability area #5 (Statistical Analysis): goals-per-
 *          match averages, home/away/draw rates, biggest wins, plus a basic
 *          performance budget check from the spec.
 * ============================================================================
 */

import { describe, it, expect } from 'vitest';
import { givenLoadedDatabase } from './helpers.js';

describe('Feature: Statistical Analysis', () => {
  it('Scenario: Average goals per match is in a sane football range', () => {
    const db = givenLoadedDatabase();
    const stats = db.leagueStats({ competition: 'Brasileirão' });
    expect(stats.matches).toBeGreaterThan(0);
    expect(stats.avgGoalsPerMatch).toBeGreaterThan(2);
    expect(stats.avgGoalsPerMatch).toBeLessThan(4);
  });

  it('Scenario: Home / away / draw rates sum to ~100%', () => {
    const db = givenLoadedDatabase();
    const s = db.leagueStats({ competition: 'Brasileirão', season: 2019 });
    expect(s.homeWins + s.awayWins + s.draws).toBe(s.matches);
    const total = s.homeWinRate + s.awayWinRate + s.drawRate;
    expect(Math.abs(total - 100)).toBeLessThan(0.5);
    // home advantage exists
    expect(s.homeWinRate).toBeGreaterThan(s.awayWinRate);
  });

  it('Scenario: Biggest wins are ordered by goal margin', () => {
    const db = givenLoadedDatabase();
    const wins = db.biggestWins({ limit: 10 });
    expect(wins.length).toBe(10);
    const margin = (m: { homeGoal: number; awayGoal: number }) =>
      Math.abs(m.homeGoal - m.awayGoal);
    for (let i = 1; i < wins.length; i++) {
      expect(margin(wins[i - 1])).toBeGreaterThanOrEqual(margin(wins[i]));
    }
    expect(margin(wins[0])).toBeGreaterThanOrEqual(6);
  });

  it('Scenario: Aggregate queries respond within the performance budget (<5s)', () => {
    const db = givenLoadedDatabase();
    const start = performance.now();
    db.standings('Brasileirão', 2019);
    db.leagueStats({ competition: 'Brasileirão' });
    db.headToHead('Flamengo', 'Fluminense');
    db.searchPlayers({ nationality: 'Brazil', limit: 100 });
    const elapsed = performance.now() - start;
    expect(elapsed).toBeLessThan(5000);
  });
});
