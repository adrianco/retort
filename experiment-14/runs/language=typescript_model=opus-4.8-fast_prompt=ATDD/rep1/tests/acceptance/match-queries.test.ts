/**
 * Acceptance: Match Queries (TASK.md §1).
 * "Find matches by team / date range / competition / season."
 */
import { describe, it, expect, afterEach, beforeEach } from 'vitest';
import { startSystem, type TestSystem } from './harness.js';
import { match } from './builders.js';

let sys: TestSystem;
beforeEach(async () => { sys = await startSystem(); });
afterEach(async () => { await sys.close(); });

describe('Match queries', () => {
  it('finds all matches between two specific teams (the Fla-Flu derby)', async () => {
    sys.store.addMatches([
      match({ homeTeam: 'Flamengo', awayTeam: 'Fluminense', homeGoals: 2, awayGoals: 1, date: '2023-09-03', round: '22' }),
      match({ homeTeam: 'Fluminense', awayTeam: 'Flamengo', homeGoals: 1, awayGoals: 0, date: '2023-05-28', round: '8' }),
      match({ homeTeam: 'Palmeiras', awayTeam: 'Santos', homeGoals: 3, awayGoals: 0, date: '2023-07-01' }),
    ]);

    const res = await sys.call('find_matches', { team: 'Flamengo', opponent: 'Fluminense' });

    expect(res.count).toBe(2);
    const pairs = res.matches.map((m: any) => `${m.homeTeam}-${m.awayTeam}`).sort();
    expect(pairs).toEqual(['Flamengo-Fluminense', 'Fluminense-Flamengo']);
  });

  it('finds the matches a team played in a given season', async () => {
    sys.store.addMatches([
      match({ homeTeam: 'Palmeiras', awayTeam: 'Corinthians', homeGoals: 2, awayGoals: 2, season: 2023 }),
      match({ homeTeam: 'Santos', awayTeam: 'Palmeiras', homeGoals: 0, awayGoals: 1, season: 2023 }),
      match({ homeTeam: 'Palmeiras', awayTeam: 'Gremio', homeGoals: 1, awayGoals: 0, season: 2022 }),
    ]);

    const res = await sys.call('find_matches', { team: 'Palmeiras', season: 2023 });

    expect(res.count).toBe(2);
    expect(res.matches.every((m: any) => m.season === 2023)).toBe(true);
  });

  it('filters matches by competition', async () => {
    sys.store.addMatches([
      match({ competition: 'Copa do Brasil', homeTeam: 'Flamengo', awayTeam: 'Sao Paulo', homeGoals: 0, awayGoals: 1 }),
      match({ competition: 'Brasileirão', homeTeam: 'Flamengo', awayTeam: 'Sao Paulo', homeGoals: 2, awayGoals: 2 }),
    ]);

    const res = await sys.call('find_matches', { team: 'Flamengo', competition: 'Copa do Brasil' });

    expect(res.count).toBe(1);
    expect(res.matches[0].competition).toBe('Copa do Brasil');
  });

  it('filters matches by date range', async () => {
    sys.store.addMatches([
      match({ homeTeam: 'Bahia', awayTeam: 'Vitoria', homeGoals: 1, awayGoals: 0, date: '2023-03-10' }),
      match({ homeTeam: 'Bahia', awayTeam: 'Vitoria', homeGoals: 2, awayGoals: 1, date: '2023-08-20' }),
      match({ homeTeam: 'Bahia', awayTeam: 'Vitoria', homeGoals: 0, awayGoals: 0, date: '2023-11-30' }),
    ]);

    const res = await sys.call('find_matches', { team: 'Bahia', dateFrom: '2023-06-01', dateTo: '2023-10-01' });

    expect(res.count).toBe(1);
    expect(res.matches[0].date).toBe('2023-08-20');
  });

  it('treats team names with state suffixes as the same team', async () => {
    // Seeded with the raw "Palmeiras-SP" style the datasets use.
    sys.store.addMatches([
      match({ homeTeam: 'Palmeiras-SP', awayTeam: 'Portuguesa-SP', homeGoals: 1, awayGoals: 1 }),
    ]);

    // The external user asks for plain "Palmeiras".
    const res = await sys.call('find_matches', { team: 'Palmeiras' });

    expect(res.count).toBe(1);
    expect(res.matches[0].homeTeam).toBe('Palmeiras');
  });

  it('finds finals by stage without also matching semifinals/quarterfinals', async () => {
    sys.store.addMatches([
      match({ competition: 'Libertadores', season: 2013, round: 'final', homeTeam: 'Atletico Mineiro', awayTeam: 'Olimpia', homeGoals: 2, awayGoals: 0 }),
      match({ competition: 'Libertadores', season: 2013, round: 'semifinals', homeTeam: 'Newells', awayTeam: 'Atletico Mineiro', homeGoals: 2, awayGoals: 0 }),
      match({ competition: 'Libertadores', season: 2013, round: 'quarterfinals', homeTeam: 'Atletico Mineiro', awayTeam: 'Tijuana', homeGoals: 1, awayGoals: 1 }),
    ]);

    const res = await sys.call('find_matches', { competition: 'Libertadores', stage: 'final' });

    expect(res.count).toBe(1);
    expect(res.matches[0].round).toBe('final');
  });

  it('does not double-count the same fixture recorded in two datasets', async () => {
    // The same physical match appears in two source files with the team-name
    // variations the datasets use; the system should treat it as one match.
    sys.store.addMatches([
      match({ competition: 'Brasileirão', season: 2019, date: '2019-04-27', homeTeam: 'Flamengo-RJ', awayTeam: 'Cruzeiro-MG', homeGoals: 3, awayGoals: 1 }),
      match({ competition: 'Brasileirão', season: 2019, date: '2019-04-27', homeTeam: 'Flamengo', awayTeam: 'Cruzeiro', homeGoals: 3, awayGoals: 1 }),
    ]);

    const res = await sys.call('find_matches', { team: 'Flamengo', opponent: 'Cruzeiro' });

    expect(res.count).toBe(1);
  });

  it('returns no matches (not an error) when nothing matches', async () => {
    sys.store.addMatches([
      match({ homeTeam: 'Flamengo', awayTeam: 'Vasco', homeGoals: 1, awayGoals: 0 }),
    ]);

    const res = await sys.call('find_matches', { team: 'Cruzeiro' });

    expect(res.count).toBe(0);
    expect(res.matches).toEqual([]);
  });
});
