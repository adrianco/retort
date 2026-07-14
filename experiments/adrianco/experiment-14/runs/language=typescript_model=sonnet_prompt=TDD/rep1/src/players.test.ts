import { describe, it, expect, beforeAll } from 'vitest';
import { DataLoader } from './loader.js';
import { searchPlayers, getPlayersByClub } from './players.js';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, '..', 'data', 'kaggle');

let loader: DataLoader;

beforeAll(async () => {
  loader = new DataLoader(DATA_DIR);
  await loader.load();
}, 30000);

describe('searchPlayers', () => {
  it('finds player by name', () => {
    const results = searchPlayers(loader, { name: 'Neymar' });
    expect(results.length).toBeGreaterThan(0);
    results.forEach((p) => {
      expect(p.name.toLowerCase()).toContain('neymar');
    });
  });

  it('finds players by nationality', () => {
    const results = searchPlayers(loader, { nationality: 'Brazil' });
    expect(results.length).toBeGreaterThan(500);
    results.forEach((p) => {
      expect(p.nationality).toBe('Brazil');
    });
  });

  it('finds players by club', () => {
    const results = searchPlayers(loader, { club: 'Fluminense' });
    expect(results.length).toBeGreaterThan(0);
    results.forEach((p) => {
      expect(p.club.toLowerCase()).toContain('fluminense');
    });
  });

  it('filters by minimum overall rating', () => {
    const results = searchPlayers(loader, { minOverall: 85 });
    expect(results.length).toBeGreaterThan(0);
    results.forEach((p) => {
      expect(p.overall).toBeGreaterThanOrEqual(85);
    });
  });

  it('filters by position', () => {
    const results = searchPlayers(loader, { nationality: 'Brazil', position: 'GK' });
    expect(results.length).toBeGreaterThan(0);
    results.forEach((p) => {
      expect(p.position).toBe('GK');
    });
  });

  it('respects limit', () => {
    const results = searchPlayers(loader, { nationality: 'Brazil', limit: 10 });
    expect(results.length).toBeLessThanOrEqual(10);
  });

  it('sorts by overall rating descending by default', () => {
    const results = searchPlayers(loader, { nationality: 'Brazil', limit: 20 });
    for (let i = 1; i < results.length; i++) {
      expect(results[i - 1].overall).toBeGreaterThanOrEqual(results[i].overall);
    }
  });

  it('returns empty for unknown player', () => {
    const results = searchPlayers(loader, { name: 'ZzZzZzUnknownPlayer99' });
    expect(results.length).toBe(0);
  });
});

describe('getPlayersByClub', () => {
  it('returns all players at a club', () => {
    const result = getPlayersByClub(loader, 'Fluminense');
    expect(result!.players.length).toBeGreaterThan(0);
    expect(result!.avg_overall).toBeGreaterThan(60);
  });

  it('returns null for unknown club', () => {
    const result = getPlayersByClub(loader, 'NonExistentClubXYZ');
    expect(result).toBeNull();
  });
});
