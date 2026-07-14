/**
 * Acceptance: Player Queries (TASK.md §3).
 * "Find all Brazilian players. Who are the highest-rated players at Flamengo?
 *  Show me all forwards from São Paulo FC."
 */
import { describe, it, expect, afterEach, beforeEach } from 'vitest';
import { startSystem, type TestSystem } from './harness.js';
import { player } from './builders.js';

let sys: TestSystem;
beforeEach(async () => { sys = await startSystem(); });
afterEach(async () => { await sys.close(); });

describe('Player queries', () => {
  it('finds a player by name', async () => {
    sys.store.addPlayers([
      player({ name: 'Gabriel Barbosa', nationality: 'Brazil', overall: 83, club: 'Flamengo', position: 'ST' }),
      player({ name: 'L. Messi', nationality: 'Argentina', overall: 94, club: 'FC Barcelona', position: 'RF' }),
    ]);

    const res = await sys.call('find_players', { name: 'Gabriel' });

    expect(res.count).toBe(1);
    expect(res.players[0].name).toBe('Gabriel Barbosa');
  });

  it('filters players by nationality', async () => {
    sys.store.addPlayers([
      player({ name: 'Neymar Jr', nationality: 'Brazil', overall: 92 }),
      player({ name: 'Alisson', nationality: 'Brazil', overall: 89 }),
      player({ name: 'L. Messi', nationality: 'Argentina', overall: 94 }),
    ]);

    const res = await sys.call('find_players', { nationality: 'Brazil' });

    expect(res.count).toBe(2);
    expect(res.players.every((p: any) => p.nationality === 'Brazil')).toBe(true);
  });

  it('finds the highest-rated players at a club, sorted by overall', async () => {
    sys.store.addPlayers([
      player({ name: 'Player A', club: 'Flamengo', overall: 75 }),
      player({ name: 'Player B', club: 'Flamengo', overall: 83 }),
      player({ name: 'Player C', club: 'Flamengo', overall: 79 }),
      player({ name: 'Outsider', club: 'Palmeiras', overall: 99 }),
    ]);

    const res = await sys.call('find_players', { club: 'Flamengo', sortBy: 'overall' });

    expect(res.count).toBe(3);
    expect(res.players.map((p: any) => p.overall)).toEqual([83, 79, 75]);
  });

  it('shows forwards from a specific club (combined filters)', async () => {
    sys.store.addPlayers([
      player({ name: 'Forward 1', club: 'Sao Paulo', position: 'ST', overall: 78 }),
      player({ name: 'Keeper 1', club: 'Sao Paulo', position: 'GK', overall: 80 }),
      player({ name: 'Forward 2', club: 'Santos', position: 'ST', overall: 77 }),
    ]);

    const res = await sys.call('find_players', { club: 'Sao Paulo', position: 'ST' });

    expect(res.count).toBe(1);
    expect(res.players[0].name).toBe('Forward 1');
  });

  it('matches player names regardless of accents', async () => {
    sys.store.addPlayers([
      player({ name: 'Éder Militão', nationality: 'Brazil', overall: 85 }),
    ]);

    const res = await sys.call('find_players', { name: 'Eder Militao' });

    expect(res.count).toBe(1);
    expect(res.players[0].name).toBe('Éder Militão');
  });

  it('honours a result limit', async () => {
    sys.store.addPlayers([
      player({ name: 'A', nationality: 'Brazil', overall: 90 }),
      player({ name: 'B', nationality: 'Brazil', overall: 80 }),
      player({ name: 'C', nationality: 'Brazil', overall: 70 }),
    ]);

    const res = await sys.call('find_players', { nationality: 'Brazil', sortBy: 'overall', limit: 2 });

    expect(res.players).toHaveLength(2);
    expect(res.players.map((p: any) => p.name)).toEqual(['A', 'B']);
  });
});
