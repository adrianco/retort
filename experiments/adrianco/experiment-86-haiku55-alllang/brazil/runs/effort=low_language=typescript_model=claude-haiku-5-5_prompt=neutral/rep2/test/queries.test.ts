import { describe, expect, it } from 'vitest';
import {
  biggestWins,
  clubSummary,
  filterMatches,
  headToHead,
  leagueStats,
  rankTeams,
  searchPlayers,
  standings,
  teamProfile,
  teamRecord,
} from '../src/queries.js';
import { dedupeMatches } from '../src/loader.js';
import { makeDataset, makeMatch, makePlayer } from './helpers.js';

const dataset = makeDataset(
  [
    makeMatch('2023-09-03', 'Flamengo-RJ', 'Fluminense-RJ', 2, 1),
    makeMatch('2023-05-28', 'Fluminense-RJ', 'Flamengo-RJ', 1, 0),
    makeMatch('2023-04-01', 'Palmeiras-SP', 'Santos-SP', 3, 0),
    makeMatch('2023-04-08', 'Santos-SP', 'Palmeiras-SP', 1, 1),
    makeMatch('2023-06-10', 'Palmeiras-SP', 'Corinthians-SP', 0, 2),
    makeMatch('2022-07-01', 'Palmeiras', 'Flamengo', 1, 1),
    makeMatch('2022-08-01', 'Flamengo', 'Palmeiras', 2, 0),
    makeMatch('2021-11-20', 'Flamengo', 'Palmeiras', 1, 0, 'Copa do Brasil', { round: '2' }),
    makeMatch('2021-12-18', 'Palmeiras', 'Flamengo', 2, 0, 'Copa do Brasil', { round: '5' }),
    makeMatch('2021-12-19', 'Atlético-MG', 'Athletico-PR', 4, 0, 'Copa do Brasil', { round: '5' }),
    makeMatch('2019-11-01', 'Copa Team', 'Other', 0, 0, 'Copa Libertadores', { stage: 'final' }),
  ],
  [
    makePlayer({ name: 'Gabriel Barbosa', club: 'CR Flamengo', overall: 86, position: 'ST', nationality: 'Brazil', age: 24 }),
    makePlayer({ name: 'Diego Ribas', club: 'CR Flamengo', overall: 80, position: 'CAM', nationality: 'Brazil', age: 33 }),
    makePlayer({ name: 'Lionel Messi', club: 'FC Barcelona', overall: 94, position: 'RW', nationality: 'Argentina', age: 31 }),
    makePlayer({ name: 'Alisson Becker', club: 'Liverpool', overall: 89, position: 'GK', nationality: 'Brazil', age: 26 }),
  ],
);

describe('Feature: Match Queries', () => {
  describe('Scenario: Find matches between two teams', () => {
    it('Given the match data is loaded, when I search for Flamengo vs Fluminense, then I get both meetings with date, scores and competition', () => {
      const matches = filterMatches(dataset, { team: 'Flamengo', opponent: 'Fluminense' });
      expect(matches).toHaveLength(2);
      expect(matches[0]).toMatchObject({ date: '2023-09-03', homeGoals: 2, awayGoals: 1, competition: 'Brasileirão Série A' });
    });
  });

  describe('Scenario: Filter by season and venue', () => {
    it('Given Palmeiras matches in 2023, when I filter to home games, then only home games are returned', () => {
      const matches = filterMatches(dataset, { team: 'Palmeiras', season: 2023, venue: 'home' });
      expect(matches.map((m) => m.date)).toEqual(['2023-06-10', '2023-04-01']);
    });
  });

  describe('Scenario: Find all Copa do Brasil finals', () => {
    it('Given cup rounds per season, when finalOnly is set, then only the last round of each season is returned', () => {
      const finals = filterMatches(dataset, { competition: 'Copa do Brasil', finalOnly: true });
      expect(finals.every((m) => m.round === '5')).toBe(true);
      expect(finals).toHaveLength(2);
    });

    it('Given Libertadores stages, when finalOnly is set, then the "final" stage is returned', () => {
      const finals = filterMatches(dataset, { competition: 'Copa Libertadores', finalOnly: true });
      expect(finals.map((m) => m.stage)).toEqual(['final']);
    });
  });

  it('Given an unknown competition, then no matches are returned', () => {
    expect(filterMatches(dataset, { competition: 'Premier League' })).toEqual([]);
  });
});

describe('Feature: Team Queries', () => {
  describe('Scenario: Get team statistics', () => {
    it('Given Palmeiras in 2023, when I request its record, then wins, draws, losses and goals are reported', () => {
      const r = teamRecord(dataset, 'Palmeiras', { season: 2023 });
      expect(r).toMatchObject({ matches: 3, wins: 1, draws: 1, losses: 1, goalsFor: 4, goalsAgainst: 3 });
      expect(r.winRate).toBeCloseTo(1 / 3);
    });

    it('Given a home-only filter, then only home results count', () => {
      const r = teamRecord(dataset, 'Palmeiras', { season: 2023, venue: 'home' });
      expect(r).toMatchObject({ matches: 2, wins: 1, losses: 1 });
    });
  });

  describe('Scenario: Compare teams head-to-head', () => {
    it('Given Flamengo and Palmeiras, when I compare them, then wins and goals are totalled from the first team view', () => {
      const h = headToHead(dataset, 'Flamengo', 'Palmeiras');
      expect(h.matches).toHaveLength(4);
      expect(h).toMatchObject({ winsA: 2, winsB: 1, draws: 1, goalsA: 4, goalsB: 3 });
    });
  });

  it('Given a team with mixed name variants, then its record combines all of them', () => {
    expect(teamRecord(dataset, 'Palmeiras-SP', { season: 2023 }).matches).toBe(3);
  });
});

describe('Feature: Competition Queries', () => {
  describe('Scenario: Standings calculated from matches', () => {
    it('Given the 2023 Serie A results, when I ask for standings, then points are 3/1/0 and ties break on goal difference', () => {
      const table = standings(dataset, 'Brasileirão Série A', 2023);
      expect(table[0]).toMatchObject({ position: 1, team: 'Palmeiras', points: 4, wins: 1, draws: 1, losses: 1 });
      expect(table.find((r) => r.team === 'Flamengo')?.points).toBe(3);
      expect(table.map((r) => r.team)).toContain('Corinthians');
    });
  });
});

describe('Feature: Statistical Analysis', () => {
  it('Given Brasileirão matches, when I ask for league stats, then goals per match and home win rate are computed', () => {
    const s = leagueStats(dataset, { competition: 'Brasileirão Série A', season: 2023 });
    expect(s.matches).toBe(5);
    expect(s.totalGoals).toBe(11);
    expect(s.goalsPerMatch).toBeCloseTo(11 / 5);
    expect(s.homeWinRate).toBeCloseTo(3 / 5);
  });

  it('Given all matches, when I ask for the biggest wins, then the largest margins come first', () => {
    const [first] = biggestWins(dataset, {}, 1);
    expect(first).toMatchObject({ homeGoals: 4, awayGoals: 0 });
  });

  it('Given a home-venue ranking, then teams are ordered by win rate with the minimum match filter applied', () => {
    const ranked = rankTeams(dataset, 'win_rate', { competition: 'Brasileirão Série A', venue: 'home' }, 1, 5);
    // Flamengo won both home games; Palmeiras won 1 of 3 at home (3-0, 0-2, 1-1).
    expect(ranked[0].team).toBe('Flamengo');
    expect(ranked[0].value).toBe(1);
    const qualified = rankTeams(dataset, 'win_rate', { competition: 'Brasileirão Série A', venue: 'home' }, 3, 5);
    expect(qualified.map((r) => r.team)).toEqual(['Palmeiras']);
  });
});

describe('Feature: Player Queries', () => {
  describe('Scenario: Filter players by club and nationality', () => {
    it('Given the FIFA data, when I search Brazilian players at Flamengo, then only them are returned, highest rated first', () => {
      const players = searchPlayers(dataset, { nationality: 'Brazil', club: 'Flamengo' });
      expect(players.map((p) => p.name)).toEqual(['Gabriel Barbosa', 'Diego Ribas']);
    });
  });

  describe('Scenario: Search by name ignoring accents and case', () => {
    it('Given "gabriel", when I search by name, then Gabriel Barbosa is found', () => {
      expect(searchPlayers(dataset, { name: 'gabriel' }).map((p) => p.name)).toEqual(['Gabriel Barbosa']);
    });
  });

  it('Given a position code, then players with a matching position are returned', () => {
    expect(searchPlayers(dataset, { position: 'GK' }).map((p) => p.name)).toEqual(['Alisson Becker']);
  });

  it('Given a minimum overall, then lower-rated players are excluded', () => {
    expect(searchPlayers(dataset, { minOverall: 88 }).map((p) => p.name)).toEqual(['Lionel Messi', 'Alisson Becker']);
  });

  it('Given a nationality summary, then clubs are counted with average overall', () => {
    const summary = clubSummary(dataset, 'Brazil');
    const flamengo = summary.find((c) => c.club === 'CR Flamengo');
    expect(flamengo).toEqual({ club: 'CR Flamengo', players: 2, averageOverall: 83 });
  });

  it('Given a team, then the profile combines the match record with squad members', () => {
    const profile = teamProfile(dataset, 'Flamengo');
    expect(profile.record.matches).toBeGreaterThan(0);
    expect(profile.players.map((p) => p.name)).toEqual(['Gabriel Barbosa', 'Diego Ribas']);
  });
});

describe('Feature: Cross-file deduplication', () => {
  it('Given the same fixture from two sources with dates one day apart, then only one copy is kept', () => {
    const kept = dedupeMatches([
      makeMatch('2019-10-05', 'Bahia', 'Athletico', 1, 2),
      makeMatch('2019-10-06', 'EC Bahia', 'Athletico Paranaense', 1, 2),
    ]);
    expect(kept).toHaveLength(1);
  });

  it('Given two meetings of the same teams months apart, then both are kept', () => {
    const kept = dedupeMatches([
      makeMatch('2019-10-05', 'Bahia', 'Athletico', 1, 2),
      makeMatch('2020-03-05', 'Athletico', 'Bahia', 1, 2),
    ]);
    expect(kept).toHaveLength(2);
  });
});
