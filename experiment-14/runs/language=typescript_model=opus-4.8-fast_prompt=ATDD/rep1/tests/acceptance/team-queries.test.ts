/**
 * Acceptance: Team Queries & head-to-head (TASK.md §2).
 * "What is Corinthians' home record in 2022? Compare Palmeiras and Santos head-to-head."
 */
import { describe, it, expect, afterEach, beforeEach } from 'vitest';
import { startSystem, type TestSystem } from './harness.js';
import { match } from './builders.js';

let sys: TestSystem;
beforeEach(async () => { sys = await startSystem(); });
afterEach(async () => { await sys.close(); });

describe('Team record', () => {
  it('reports a team home record for a season (wins, draws, losses, goals, win rate)', async () => {
    sys.store.addMatches([
      // Corinthians at home in 2022: W, D, L
      match({ homeTeam: 'Corinthians', awayTeam: 'Santos', homeGoals: 2, awayGoals: 0, season: 2022 }),
      match({ homeTeam: 'Corinthians', awayTeam: 'Palmeiras', homeGoals: 1, awayGoals: 1, season: 2022 }),
      match({ homeTeam: 'Corinthians', awayTeam: 'Flamengo', homeGoals: 0, awayGoals: 1, season: 2022 }),
      // An away game that must be excluded by venue=home
      match({ homeTeam: 'Gremio', awayTeam: 'Corinthians', homeGoals: 0, awayGoals: 3, season: 2022 }),
      // A different season that must be excluded
      match({ homeTeam: 'Corinthians', awayTeam: 'Bahia', homeGoals: 4, awayGoals: 0, season: 2021 }),
    ]);

    const res = await sys.call('team_record', { team: 'Corinthians', season: 2022, venue: 'home' });

    expect(res.matches).toBe(3);
    expect(res.wins).toBe(1);
    expect(res.draws).toBe(1);
    expect(res.losses).toBe(1);
    expect(res.goalsFor).toBe(3);
    expect(res.goalsAgainst).toBe(2);
    expect(res.winRate).toBeCloseTo(33.3, 1);
  });

  it('counts both home and away games when venue is not restricted', async () => {
    sys.store.addMatches([
      match({ homeTeam: 'Santos', awayTeam: 'Bahia', homeGoals: 3, awayGoals: 1 }),
      match({ homeTeam: 'Vasco', awayTeam: 'Santos', homeGoals: 2, awayGoals: 2 }),
    ]);

    const res = await sys.call('team_record', { team: 'Santos' });

    expect(res.matches).toBe(2);
    expect(res.wins).toBe(1);
    expect(res.draws).toBe(1);
    expect(res.goalsFor).toBe(5);
    expect(res.goalsAgainst).toBe(3);
  });
});

describe('Head-to-head', () => {
  it('summarises the head-to-head record between two teams', async () => {
    sys.store.addMatches([
      match({ homeTeam: 'Palmeiras', awayTeam: 'Santos', homeGoals: 2, awayGoals: 1 }), // Palmeiras win
      match({ homeTeam: 'Santos', awayTeam: 'Palmeiras', homeGoals: 0, awayGoals: 0 }),  // draw
      match({ homeTeam: 'Santos', awayTeam: 'Palmeiras', homeGoals: 3, awayGoals: 1 }),  // Santos win
      match({ homeTeam: 'Palmeiras', awayTeam: 'Corinthians', homeGoals: 1, awayGoals: 0 }), // unrelated
    ]);

    const res = await sys.call('head_to_head', { team1: 'Palmeiras', team2: 'Santos' });

    expect(res.totalMatches).toBe(3);
    expect(res.team1Wins).toBe(1); // Palmeiras
    expect(res.team2Wins).toBe(1); // Santos
    expect(res.draws).toBe(1);
    // Palmeiras scored 2+0+1=3; Santos scored 1+0+3=4.
    expect(res.team1Goals).toBe(3);
    expect(res.team2Goals).toBe(4);
  });
});
