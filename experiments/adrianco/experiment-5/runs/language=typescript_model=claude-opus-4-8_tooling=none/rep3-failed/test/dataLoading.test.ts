/**
 * ============================================================================
 * Context Block — File: test/dataLoading.test.ts
 * Project: Brazilian Soccer MCP Server
 * Purpose: BDD specs asserting that all six provided CSV files load and are
 *          queryable (spec success criterion: "All 6 CSV files are loadable and
 *          queryable"), with UTF-8 encoding preserved.
 * ============================================================================
 */

import { describe, it, expect } from 'vitest';
import { givenLoadedDatabase } from './helpers.js';

describe('Feature: Data loading', () => {
  it('Scenario: all six datasets load with non-trivial row counts', () => {
    const db = givenLoadedDatabase();
    const counts = db.sourceCounts;

    // Each provided file contributes records (within a tolerance of the spec's
    // advertised sizes — a few rows may be dropped for missing scores/dates).
    expect(counts['Brasileirao_Matches.csv']).toBeGreaterThan(4000);
    expect(counts['Brazilian_Cup_Matches.csv']).toBeGreaterThan(1200);
    expect(counts['Libertadores_Matches.csv']).toBeGreaterThan(1200);
    expect(counts['BR-Football-Dataset.csv']).toBeGreaterThan(10000);
    expect(counts['novo_campeonato_brasileiro.csv']).toBeGreaterThan(6800);
    expect(counts['fifa_data.csv']).toBeGreaterThan(18000);
  });

  it('Scenario: the knowledge graph exposes matches and players', () => {
    const db = givenLoadedDatabase();
    expect(db.matches.length).toBeGreaterThan(20000);
    expect(db.players.length).toBeGreaterThan(18000);
  });

  it('Scenario: Portuguese accents are preserved (UTF-8)', () => {
    const db = givenLoadedDatabase();
    const accented = db.matches.some(
      (m) => /[ãáàâéêíóôõúç]/i.test(m.homeTeam) || /[ãáàâéêíóôõúç]/i.test(m.awayTeam),
    );
    expect(accented).toBe(true);
  });

  it('Scenario: a season range spanning the historical and modern data', () => {
    const db = givenLoadedDatabase();
    const [first, last] = db.summary().seasonRange;
    expect(first).toBeLessThanOrEqual(2003);
    expect(last).toBeGreaterThanOrEqual(2022);
  });
});
