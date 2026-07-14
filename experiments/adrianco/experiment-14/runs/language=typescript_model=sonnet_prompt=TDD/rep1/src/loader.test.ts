import { describe, it, expect, beforeAll } from 'vitest';
import { DataLoader } from './loader.js';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, '..', 'data', 'kaggle');

describe('DataLoader', () => {
  let loader: DataLoader;

  beforeAll(async () => {
    loader = new DataLoader(DATA_DIR);
    await loader.load();
  }, 30000);

  it('loads Brasileirao matches', () => {
    const matches = loader.getBrasileiraoMatches();
    expect(matches.length).toBeGreaterThan(4000);
    expect(matches[0]).toHaveProperty('home_team');
    expect(matches[0]).toHaveProperty('home_goal');
    expect(matches[0]).toHaveProperty('season');
  });

  it('loads Cup matches', () => {
    const matches = loader.getCupMatches();
    expect(matches.length).toBeGreaterThan(1000);
    expect(matches[0]).toHaveProperty('home_team');
    expect(matches[0]).toHaveProperty('round');
  });

  it('loads Libertadores matches', () => {
    const matches = loader.getLibertadoresMatches();
    expect(matches.length).toBeGreaterThan(1000);
    expect(matches[0]).toHaveProperty('stage');
  });

  it('loads extended match data', () => {
    const matches = loader.getExtendedMatches();
    expect(matches.length).toBeGreaterThan(10000);
    expect(matches[0]).toHaveProperty('tournament');
    expect(matches[0]).toHaveProperty('home_corner');
  });

  it('loads historical Brasileirao matches', () => {
    const matches = loader.getHistoricalMatches();
    expect(matches.length).toBeGreaterThan(6000);
    expect(matches[0]).toHaveProperty('home_team');
    expect(matches[0]).toHaveProperty('arena');
  });

  it('loads FIFA player data', () => {
    const players = loader.getPlayers();
    expect(players.length).toBeGreaterThan(18000);
    expect(players[0]).toHaveProperty('name');
    expect(players[0]).toHaveProperty('overall');
    expect(players[0]).toHaveProperty('nationality');
  });

  it('gets all normalized matches combined', () => {
    const all = loader.getAllNormalizedMatches();
    expect(all.length).toBeGreaterThan(10000);
    expect(all[0]).toHaveProperty('competition');
    expect(all[0]).toHaveProperty('home_team');
    expect(all[0]).toHaveProperty('home_goals');
    expect(all[0]).toHaveProperty('date');
  });

  it('has numeric goals in Brasileirao data', () => {
    const matches = loader.getBrasileiraoMatches();
    const first = matches[0];
    expect(typeof first.home_goal).toBe('number');
    expect(typeof first.away_goal).toBe('number');
  });

  it('has numeric goals in historical data', () => {
    const matches = loader.getHistoricalMatches();
    const first = matches[0];
    expect(typeof first.home_goals).toBe('number');
    expect(typeof first.away_goals).toBe('number');
  });
});
