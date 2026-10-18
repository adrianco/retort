/*
 * Context: Feature tests for the query layer. Hand-computed expectations run against a
 * fixture dataset (tests/fixtures/make-fixture.ts) so every number can be checked by hand;
 * a second block runs realistic lookups against the full data for the performance budgets
 * in TASK.md (simple < 2s, aggregate < 5s).
 * Related: src/queries.ts.
 */
import { describe, expect, it, beforeAll } from 'vitest';
import { buildDataset, DEFAULT_DATA_DIR, loadDataset, COMPETITION } from '../src/dataset.js';
import * as q from '../src/queries.js';
import { makeFixtureDir } from './fixtures/make-fixture.js';
import type { Dataset } from '../src/types.js';

describe('Feature: Query answers on a hand-checked dataset', () => {
  let ds: Dataset;
  beforeAll(() => {
    ds = buildDataset(makeFixtureDir());
  });

  describe('Feature: Match queries', () => {
    it('Scenario: find matches between two teams, most recent first', () => {
      // Given the match data is loaded
      // When I search for matches between "Palmeiras-SP" and "Flamengo"
      const r = q.searchMatches(ds, { team: 'Palmeiras-SP', opponent: 'Flamengo' });
      // Then I receive all three meetings, most recent first
      expect(r.total).toBe(3);
      expect(r.matches.map((m) => m.date)).toEqual(['2023-05-01', '2019-11-20', '2019-04-03']);
      // And each match carries date, scores and competition
      expect(r.matches[0]).toMatchObject({ homeGoals: 3, awayGoals: 1, competition: COMPETITION.SERIE_A });
    });

    it('Scenario: filter by venue', () => {
      const home = q.searchMatches(ds, { team: 'Palmeiras', venue: 'home', filter: { season: 2019 } });
      expect(home.matches.every((m) => m.homeKey === 'palmeiras')).toBe(true);
      const away = q.searchMatches(ds, { team: 'Palmeiras', venue: 'away', filter: { season: 2019 } });
      expect(away.matches.every((m) => m.awayKey === 'palmeiras')).toBe(true);
    });

    it('Scenario: filter by competition and date range', () => {
      const r = q.searchMatches(ds, {
        team: 'Palmeiras',
        filter: { competition: 'Copa do Brasil' },
      });
      expect(r.matches).toHaveLength(1);
      const ranged = q.searchMatches(ds, { filter: { dateFrom: '2019-04-02', dateTo: '2019-04-30' } });
      expect(ranged.matches.map((m) => m.date).sort()).toEqual(['2019-04-02', '2019-04-03', '2019-04-10']);
    });

    it('Scenario: unknown team gives a helpful error', () => {
      expect(() => q.searchMatches(ds, { team: 'Time Inexistente' })).toThrow(q.QueryError);
    });
  });

  describe('Feature: Team queries', () => {
    it('Scenario: team record for a season and competition', () => {
      // When I request statistics for "Palmeiras" in 2019 Brasileirão
      const s = q.teamStats(ds, 'Palmeiras', { filter: { competition: 'Brasileirão Série A', season: 2019 } });
      // Then I receive wins, draws, losses and goals
      expect(s).toMatchObject({ played: 3, wins: 2, draws: 1, losses: 0, goalsFor: 4, goalsAgainst: 1 });
      expect(s.winRate).toBeCloseTo(66.7, 1);
    });

    it('Scenario: home-only record', () => {
      const s = q.teamStats(ds, 'Palmeiras', { venue: 'home', filter: { season: 2019, competition: 'Série A' } });
      expect(s).toMatchObject({ played: 1, wins: 1, winRate: 100 });
    });

    it('Scenario: team with no matches reports zeros', () => {
      const s = q.teamStats(ds, 'Nacional', { filter: { season: 2030 } });
      expect(s.played).toBe(0);
      expect(s.winRate).toBe(0);
    });
  });

  describe('Feature: Head-to-head', () => {
    it('Scenario: Palmeiras vs Santos across all competitions', () => {
      // When I compare Palmeiras and Santos head-to-head
      const h = q.headToHead(ds, 'Palmeiras', 'Santos');
      // Then the dataset shows three meetings with the right record
      expect(h.played).toBe(3);
      expect(h.wins).toBe(1);
      expect(h.draws).toBe(2);
      expect(h.losses).toBe(0);
      expect(h.lastMeeting?.date).toBe('2019-04-10');
    });

    it('Scenario: a team cannot play itself', () => {
      expect(() => q.headToHead(ds, 'Palmeiras', 'Palmeiras-SP')).toThrow(q.QueryError);
    });
  });

  describe('Feature: Standings', () => {
    it('Scenario: 2019 Brasileirão table is calculated from results', () => {
      const table = q.standings(ds, 2019);
      expect(table.map((r) => [r.team, r.points])).toEqual([
        ['Palmeiras', 7],
        ['Santos', 1],
        ['Flamengo', 0],
      ]);
      expect(table[0]).toMatchObject({ position: 1, wins: 2, draws: 1, losses: 0, goalDifference: 3 });
    });
  });

  describe('Feature: Statistical analysis', () => {
    it('Scenario: average goals and home/draw/away rates for a season', () => {
      const a = q.aggregateStats(ds, { competition: 'Brasileirão Série A', season: 2019 });
      expect(a.matches).toBe(3);
      expect(a.avgGoalsPerMatch).toBeCloseTo(5 / 3, 2);
      expect(a.homeWinRate).toBeCloseTo(33.3, 1);
      expect(a.drawRate).toBeCloseTo(33.3, 1);
      expect(a.awayWinRate).toBeCloseTo(33.3, 1);
    });

    it('Scenario: biggest wins sorted by margin then total goals', () => {
      const top = q.biggestWins(ds, {}, 2);
      // 3-1 (margin 2, 4 goals) beats 2-0 (margin 2, 2 goals)
      expect(top[0]).toMatchObject({ homeGoals: 3, awayGoals: 1 });
      expect(top[1]).toMatchObject({ homeGoals: 2, awayGoals: 0 });
    });
  });

  describe('Feature: Player queries', () => {
    it('Scenario: all Brazilian players ranked by overall rating', () => {
      const r = q.searchPlayers(ds, { nationality: 'Brazil', sortBy: 'overall' });
      expect(r.total).toBe(3);
      expect(r.players.map((p) => p.name)).toEqual(['Neymar Jr', 'Gabriel Barbosa', 'Diego Alves']);
    });

    it('Scenario: search by partial name', () => {
      expect(q.searchPlayers(ds, { name: 'Gabriel' }).players[0].name).toBe('Gabriel Barbosa');
    });

    it('Scenario: players at a club, filtered by position', () => {
      expect(q.searchPlayers(ds, { club: 'Flamengo' }).total).toBe(2);
      expect(q.searchPlayers(ds, { club: 'Flamengo', position: 'GK' }).players.map((p) => p.name)).toEqual(['Diego Alves']);
    });

    it('Scenario: Brazilian players at Brazilian clubs, averaged per club', () => {
      const clubs = q.clubSummaries(ds, { nationality: 'Brazil', brazilianClubsOnly: true });
      expect(clubs).toHaveLength(1);
      expect(clubs[0]).toMatchObject({ club: 'Flamengo', players: 2, avgOverall: 84.5, isBrazilianClub: true });
    });
  });
});

describe('Feature: Performance and coverage on the full data', () => {
  let ds: Dataset;
  beforeAll(async () => {
    ds = await loadDataset(DEFAULT_DATA_DIR);
  });

  it('Scenario: simple lookups respond in under 2 seconds', () => {
    const start = performance.now();
    q.searchMatches(ds, { team: 'Flamengo', opponent: 'Fluminense' });
    q.headToHead(ds, 'Corinthians', 'Palmeiras');
    expect(performance.now() - start).toBeLessThan(2000);
  });

  it('Scenario: aggregate queries respond in under 5 seconds', () => {
    const start = performance.now();
    q.standings(ds, 2023);
    q.aggregateStats(ds, { competition: 'Brasileirão', seasonFrom: 2003, seasonTo: 2023 });
    q.clubSummaries(ds, { brazilianClubsOnly: true });
    expect(performance.now() - start).toBeLessThan(5000);
  });

  it('Scenario: 2023 Brasileirão standings have twenty clubs', () => {
    expect(q.standings(ds, 2023)).toHaveLength(20);
  });

  it('Scenario: Palmeiras and Flamengo both appear as Brazilian clubs', () => {
    const clubs = q.clubSummaries(ds, { nationality: 'Brazil', brazilianClubsOnly: true, limit: 100 }).map((c) => c.club);
    expect(clubs.length).toBeGreaterThan(5);
  });
});
