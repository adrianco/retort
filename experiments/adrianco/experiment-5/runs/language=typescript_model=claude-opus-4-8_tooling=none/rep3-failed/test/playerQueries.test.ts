/**
 * ============================================================================
 * Context Block — File: test/playerQueries.test.ts
 * Project: Brazilian Soccer MCP Server
 * Purpose: BDD specs for capability area #3 (Player Queries) over the FIFA
 *          dataset: search by name, nationality, club, position; sorting and
 *          club aggregation.
 * ============================================================================
 */

import { describe, it, expect } from 'vitest';
import { givenLoadedDatabase } from './helpers.js';

describe('Feature: Player Queries', () => {
  it('Scenario: Search a player by name', () => {
    // When I look up Neymar
    const db = givenLoadedDatabase();
    const results = db.searchPlayers({ name: 'Neymar' });
    // Then I find the Brazilian forward with a high rating
    expect(results.length).toBeGreaterThan(0);
    const top = results[0];
    expect(top.nationality).toBe('Brazil');
    expect(top.overall).toBeGreaterThan(85);
  });

  it('Scenario: Find all Brazilian players in the dataset', () => {
    const db = givenLoadedDatabase();
    const brazilians = db.searchPlayers({ nationality: 'Brazil', limit: 1000 });
    expect(brazilians.length).toBeGreaterThan(500);
    for (const p of brazilians.slice(0, 50)) expect(p.nationality).toBe('Brazil');
  });

  it('Scenario: Top Brazilian players are sorted by overall rating', () => {
    const db = givenLoadedDatabase();
    const top = db.searchPlayers({ nationality: 'Brazil', sortBy: 'overall', limit: 5 });
    expect(top[0].name.toLowerCase()).toContain('neymar');
    for (let i = 1; i < top.length; i++) {
      expect(top[i - 1].overall ?? 0).toBeGreaterThanOrEqual(top[i].overall ?? 0);
    }
  });

  it('Scenario: Filter players by club', () => {
    const db = givenLoadedDatabase();
    const santos = db.searchPlayers({ club: 'Santos' });
    expect(santos.length).toBeGreaterThan(0);
    for (const p of santos) expect(p.clubKey).toContain('santos');
  });

  it('Scenario: Filter players by position', () => {
    const db = givenLoadedDatabase();
    const keepers = db.searchPlayers({ position: 'GK', nationality: 'Brazil', limit: 20 });
    expect(keepers.length).toBeGreaterThan(0);
    for (const p of keepers) expect(p.position).toBe('GK');
  });

  it('Scenario: Aggregate Brazilian players by club', () => {
    const db = givenLoadedDatabase();
    const byClub = db.playersByClub({ nationality: 'Brazil', minPlayers: 5 });
    expect(byClub.length).toBeGreaterThan(0);
    const first = byClub[0];
    expect(first.players).toBeGreaterThanOrEqual(5);
    expect(first.avgRating).toBeGreaterThan(0);
  });
});
