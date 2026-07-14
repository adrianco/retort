import { describe, it, expect, beforeAll } from 'vitest';
import { loadData } from '../src/loader';
import type { DataStore } from '../src/types';

let store: DataStore;

beforeAll(() => {
  store = loadData({ dataDir: 'data/kaggle' });
});

describe('CSV loaders', () => {
  it('loads all 6 datasets into a unified match list', () => {
    expect(store.matches.length).toBeGreaterThan(20_000);
    const competitions = new Set(store.matches.map((m) => m.competition));
    expect(competitions.has('Brasileirão Serie A')).toBe(true);
    expect(competitions.has('Copa do Brasil')).toBe(true);
    expect(competitions.has('Copa Libertadores')).toBe(true);
    expect(competitions.has('BR-Football Dataset')).toBe(true);
    expect(competitions.has('Brasileirão (Historical 2003-2019)')).toBe(true);
  });

  it('loads FIFA player data', () => {
    expect(store.players.length).toBeGreaterThan(18_000);
    const messi = store.players.find((p) => p.name === 'L. Messi');
    expect(messi).toBeDefined();
    expect(messi?.overall).toBe(94);
    expect(messi?.nationality).toBe('Argentina');
  });

  it('normalizes Brasileirão team names', () => {
    const brasileirao = store.matches.filter((m) => m.competition === 'Brasileirão Serie A');
    const sample = brasileirao.find((m) => m.homeTeamRaw === 'Palmeiras-SP');
    expect(sample?.homeTeam).toBe('Palmeiras');
    expect(sample?.homeState).toBe('SP');
  });

  it('parses Brazilian Cup dates and scores', () => {
    const cup = store.matches.filter((m) => m.competition === 'Copa do Brasil');
    expect(cup.length).toBeGreaterThan(1_000);
    for (const m of cup.slice(0, 50)) {
      expect(m.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(Number.isFinite(m.homeGoals)).toBe(true);
      expect(Number.isFinite(m.awayGoals)).toBe(true);
    }
  });

  it('parses Brazilian historical date format DD/MM/YYYY', () => {
    const historical = store.matches.filter(
      (m) => m.competition === 'Brasileirão (Historical 2003-2019)',
    );
    expect(historical.length).toBeGreaterThan(6_000);
    const firstSeason = historical.find((m) => m.season === 2003);
    expect(firstSeason).toBeDefined();
    expect(firstSeason?.date.startsWith('2003-')).toBe(true);
  });

  it('captures extended stats from BR-Football dataset', () => {
    const brf = store.matches.filter((m) => m.competition === 'BR-Football Dataset');
    const withShots = brf.find((m) => m.homeShots !== undefined && m.awayShots !== undefined);
    expect(withShots).toBeDefined();
  });

  it('strips parenthesized country codes from Libertadores teams', () => {
    const libertadores = store.matches.filter((m) => m.competition === 'Copa Libertadores');
    const sample = libertadores.find((m) => m.homeTeamRaw?.includes('('));
    expect(sample).toBeDefined();
    expect(sample?.homeTeam).not.toMatch(/\(/);
  });
});
