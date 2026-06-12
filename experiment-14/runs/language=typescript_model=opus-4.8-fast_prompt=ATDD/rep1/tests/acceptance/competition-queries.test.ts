/**
 * Acceptance: Competition Queries & Statistical Analysis (TASK.md §4 & §5).
 * "Who won the 2019 Brasileirão? (standings calculated from matches)"
 * "Average goals per match / home win rate / biggest wins."
 */
import { describe, it, expect, afterEach, beforeEach } from 'vitest';
import { startSystem, type TestSystem } from './harness.js';
import { match } from './builders.js';

let sys: TestSystem;
beforeEach(async () => { sys = await startSystem(); });
afterEach(async () => { await sys.close(); });

describe('Competition standings', () => {
  it('calculates a league table from match results and names the champion', async () => {
    // Three-team mini league, single round robin.
    sys.store.addMatches([
      match({ competition: 'Brasileirão', season: 2019, homeTeam: 'Flamengo', awayTeam: 'Santos', homeGoals: 2, awayGoals: 0 }),
      match({ competition: 'Brasileirão', season: 2019, homeTeam: 'Flamengo', awayTeam: 'Palmeiras', homeGoals: 1, awayGoals: 1 }),
      match({ competition: 'Brasileirão', season: 2019, homeTeam: 'Santos', awayTeam: 'Palmeiras', homeGoals: 0, awayGoals: 3 }),
    ]);

    const res = await sys.call('competition_standings', { competition: 'Brasileirão', season: 2019 });

    // Flamengo: 1W 1D = 4 pts; Palmeiras: 1W 1D = 4 pts (GD +3); Santos: 2L = 0.
    expect(res.standings).toHaveLength(3);
    const flamengo = res.standings.find((r: any) => r.team === 'Flamengo');
    const palmeiras = res.standings.find((r: any) => r.team === 'Palmeiras');
    const santos = res.standings.find((r: any) => r.team === 'Santos');

    expect(flamengo.points).toBe(4);
    expect(palmeiras.points).toBe(4);
    expect(santos.points).toBe(0);

    // Palmeiras edges Flamengo on goal difference (+3 vs +2) -> champion.
    expect(res.standings[0].position).toBe(1);
    expect(res.champion).toBe('Palmeiras');
    expect(res.standings[0].team).toBe('Palmeiras');

    // Each team played 2 matches.
    expect(santos.played).toBe(2);
    expect(santos.losses).toBe(2);
  });
});

describe('Same-base-name clubs from different states', () => {
  it('keeps Atlético-MG and Atlético-PR as distinct teams in the table', async () => {
    // Both clubs share the base name "Atlético"; only the state distinguishes
    // them. One source file even drops the "h" from Athletico-PR.
    sys.store.addMatches([
      match({ competition: 'Brasileirão', season: 2019, date: '2019-05-01', homeTeam: 'Atletico-MG', awayTeam: 'Gremio', homeGoals: 2, awayGoals: 0 }),
      match({ competition: 'Brasileirão', season: 2019, date: '2019-05-02', homeTeam: 'Atletico-PR', awayTeam: 'Santos', homeGoals: 1, awayGoals: 1 }),
      // The "h" spelling of Paranaense must fold to the same club as Atletico-PR.
      match({ competition: 'Brasileirão', season: 2019, date: '2019-05-09', homeTeam: 'Athletico-PR', awayTeam: 'Bahia', homeGoals: 3, awayGoals: 0 }),
    ]);

    const res = await sys.call('competition_standings', { competition: 'Brasileirão', season: 2019 });

    const mineiro = res.standings.filter((r: any) => /MG/.test(r.team));
    const paranaense = res.standings.filter((r: any) => /PR/.test(r.team));
    expect(mineiro).toHaveLength(1);
    expect(paranaense).toHaveLength(1);
    // Mineiro: 1 win (3 pts). Paranaense: 1 draw + 1 win across its two spellings (4 pts).
    expect(mineiro[0].points).toBe(3);
    expect(paranaense[0].played).toBe(2);
    expect(paranaense[0].points).toBe(4);
  });
});

describe('Competition statistics', () => {
  it('computes average goals per match, home win rate and biggest wins', async () => {
    sys.store.addMatches([
      match({ competition: 'Brasileirão', season: 2019, homeTeam: 'Flamengo', awayTeam: 'Gremio', homeGoals: 5, awayGoals: 0, date: '2019-10-27' }),
      match({ competition: 'Brasileirão', season: 2019, homeTeam: 'Santos', awayTeam: 'Vasco', homeGoals: 1, awayGoals: 1, date: '2019-05-01' }),
      match({ competition: 'Brasileirão', season: 2019, homeTeam: 'Bahia', awayTeam: 'Sport', homeGoals: 0, awayGoals: 2, date: '2019-06-01' }),
    ]);

    const res = await sys.call('competition_statistics', { competition: 'Brasileirão', season: 2019 });

    expect(res.matches).toBe(3);
    expect(res.totalGoals).toBe(9);
    expect(res.averageGoalsPerMatch).toBeCloseTo(3.0, 2);
    expect(res.homeWins).toBe(1);
    expect(res.awayWins).toBe(1);
    expect(res.draws).toBe(1);
    expect(res.homeWinRate).toBeCloseTo(33.3, 1);

    // Biggest win is Flamengo 5-0 (margin 5), listed first.
    expect(res.biggestWins[0].homeTeam).toBe('Flamengo');
    expect(res.biggestWins[0].margin).toBe(5);
  });
});
