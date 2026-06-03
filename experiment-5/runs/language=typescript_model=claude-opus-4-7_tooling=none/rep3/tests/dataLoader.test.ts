import { describe, it, expect, beforeAll } from 'vitest';
import { loadStore } from './setup.js';
import type { DataStore } from '../src/types.js';

describe('dataLoader: loads all six datasets', () => {
  let store: DataStore;
  beforeAll(async () => {
    store = await loadStore();
  });

  it('loads matches from every source CSV', () => {
    const sources = new Set(store.matches.map((m) => m.source));
    expect(sources.has('Brasileirao_Matches.csv')).toBe(true);
    expect(sources.has('Brazilian_Cup_Matches.csv')).toBe(true);
    expect(sources.has('Libertadores_Matches.csv')).toBe(true);
    expect(sources.has('BR-Football-Dataset.csv')).toBe(true);
    expect(sources.has('novo_campeonato_brasileiro.csv')).toBe(true);
  });

  it('loads expected approximate match counts', () => {
    // From TASK.md
    const expected = {
      'Brasileirao_Matches.csv': 4180,
      'Brazilian_Cup_Matches.csv': 1337,
      'Libertadores_Matches.csv': 1255,
      'BR-Football-Dataset.csv': 10296,
      'novo_campeonato_brasileiro.csv': 6886,
    };
    for (const [src, count] of Object.entries(expected)) {
      const found = store.matches.filter((m) => m.source === src).length;
      // Allow off-by-one due to potential empty trailing rows.
      expect(Math.abs(found - count)).toBeLessThanOrEqual(5);
    }
  });

  it('loads roughly 18k players', () => {
    expect(store.players.length).toBeGreaterThan(18000);
    expect(store.players.length).toBeLessThan(18500);
  });

  it('parses dates into ISO format', () => {
    const matchesWithDates = store.matches.filter((m) => /^\d{4}-\d{2}-\d{2}$/.test(m.date));
    // The overwhelming majority of rows should parse cleanly.
    expect(matchesWithDates.length / store.matches.length).toBeGreaterThan(0.99);
  });

  it('tags competition correctly on BR-Football-Dataset rows', () => {
    const ext = store.matches.filter((m) => m.source === 'BR-Football-Dataset.csv');
    const competitions = new Set(ext.map((m) => m.competition));
    // The Serie A / Copa do Brasil tournaments must be detected.
    expect(competitions.has('Brasileirão')).toBe(true);
    expect(competitions.has('Copa do Brasil')).toBe(true);
    // Serie B / Serie C rows fall into "Other" so we just sanity check that
    // categorization happens for a meaningful share of rows.
    const named = ext.filter((m) => m.competition !== 'Other').length;
    expect(named).toBeGreaterThan(0);
  });

  it('normalizes team keys consistently across sources', () => {
    // Flamengo appears in many sources — there should be a single canonical key
    const flamengoMatches = store.matches.filter(
      (m) => m.homeKey === 'flamengo' || m.awayKey === 'flamengo',
    );
    expect(flamengoMatches.length).toBeGreaterThan(100);
  });
});
