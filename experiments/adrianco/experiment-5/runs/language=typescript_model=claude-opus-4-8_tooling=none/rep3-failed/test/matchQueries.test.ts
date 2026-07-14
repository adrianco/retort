/**
 * ============================================================================
 * Context Block — File: test/matchQueries.test.ts
 * Project: Brazilian Soccer MCP Server
 * Purpose: BDD specs for capability area #1 (Match Queries) and head-to-head,
 *          mirroring the Gherkin scenarios in the specification.
 * ============================================================================
 */

import { describe, it, expect } from 'vitest';
import { givenLoadedDatabase } from './helpers.js';

describe('Feature: Match Queries', () => {
  it('Scenario: Find matches between two teams', () => {
    // Given the match data is loaded
    const db = givenLoadedDatabase();
    // When I search for matches between "Flamengo" and "Fluminense"
    const matches = db.searchMatches({ team: 'Flamengo', opponent: 'Fluminense' });
    // Then I should receive a list of matches
    expect(matches.length).toBeGreaterThan(0);
    // And each match should have date, scores, and competition
    for (const m of matches) {
      expect(typeof m.homeGoal).toBe('number');
      expect(typeof m.awayGoal).toBe('number');
      expect(m.competition).toBeTruthy();
      // Both clubs are actually involved
      const teams = `${m.homeTeam} ${m.awayTeam}`.toLowerCase();
      expect(teams).toMatch(/flamengo/);
      expect(teams).toMatch(/fluminense/);
    }
  });

  it('Scenario: Filter a team\'s matches by season', () => {
    const db = givenLoadedDatabase();
    // When I ask what matches Palmeiras played in 2019
    const matches = db.searchMatches({ team: 'Palmeiras', season: 2019 });
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) expect(m.season).toBe(2019);
  });

  it('Scenario: Filter matches by competition', () => {
    const db = givenLoadedDatabase();
    const matches = db.searchMatches({ team: 'Flamengo', competition: 'Libertadores', limit: 100 });
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) expect(m.competition).toBe('Copa Libertadores');
  });

  it('Scenario: Restrict to home matches only', () => {
    const db = givenLoadedDatabase();
    const matches = db.searchMatches({ team: 'Corinthians', season: 2022, venue: 'home', competition: 'Brasileirão' });
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) expect(m.homeTeam.toLowerCase()).toContain('corinthians');
  });

  it('Scenario: Matches come back sorted most-recent first', () => {
    const db = givenLoadedDatabase();
    const matches = db.searchMatches({ team: 'Flamengo', limit: 50 });
    const dated = matches.filter((m) => m.date).map((m) => m.date as string);
    const sorted = [...dated].sort().reverse();
    expect(dated).toEqual(sorted);
  });
});

describe('Feature: Head-to-head', () => {
  it('Scenario: Fla-Flu head-to-head totals are internally consistent', () => {
    const db = givenLoadedDatabase();
    const h2h = db.headToHead('Flamengo', 'Fluminense');
    expect(h2h.totalMatches).toBeGreaterThan(0);
    // wins + draws partition every meeting
    expect(h2h.team1Wins + h2h.team2Wins + h2h.draws).toBe(h2h.totalMatches);
    expect(h2h.matches.length).toBe(h2h.totalMatches);
  });

  it('Scenario: Compare Palmeiras and Santos head-to-head', () => {
    const db = givenLoadedDatabase();
    const h2h = db.headToHead('Palmeiras', 'Santos');
    expect(h2h.totalMatches).toBeGreaterThan(10);
    expect(h2h.team1Wins + h2h.team2Wins + h2h.draws).toBe(h2h.totalMatches);
  });
});
