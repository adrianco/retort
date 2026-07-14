import { describe, it, expect, beforeAll } from 'vitest';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadAll } from '../src/data/loader.js';
import type { DataStore } from '../src/data/types.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.resolve(here, '..', 'data');

let store: DataStore;

beforeAll(() => {
  store = loadAll(DATA_DIR);
});

describe('Feature: Data loading', () => {
  it('Scenario: Loads all 6 CSV files into a single store', () => {
    expect(store.loaded).toBe(true);
    expect(store.matches.length).toBeGreaterThan(20000);
    expect(store.players.length).toBeGreaterThan(15000);
  });

  it('Scenario: Each competition is represented', () => {
    const comps = new Set(store.matches.map((m) => m.competition));
    expect(comps.has('Brasileirao')).toBe(true);
    expect(comps.has('Copa do Brasil')).toBe(true);
    expect(comps.has('Libertadores')).toBe(true);
    expect(comps.has('BR-Football')).toBe(true);
    expect(comps.has('Brasileirao-Historical')).toBe(true);
  });

  it('Scenario: Matches have valid dates and team names', () => {
    const sample = store.matches.slice(0, 100);
    for (const m of sample) {
      expect(m.date).toBeInstanceOf(Date);
      expect(isNaN(m.date.getTime())).toBe(false);
      expect(m.homeTeam.length).toBeGreaterThan(0);
      expect(m.awayTeam.length).toBeGreaterThan(0);
      expect(typeof m.homeGoals).toBe('number');
      expect(typeof m.awayGoals).toBe('number');
    }
  });

  it('Scenario: Players carry a normalized club key', () => {
    // FIFA dataset is global; only a handful of Brazilian clubs appear.
    // Santos is one that does — use it to verify the normalized club key works.
    const santos = store.players.filter((p) => p.clubNormalized === 'santos');
    expect(santos.length).toBeGreaterThan(0);
  });
});
