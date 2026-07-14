import { describe, it, expect, beforeAll } from 'vitest';
import { loadData } from '../src/loader';
import type { DataStore } from '../src/types';
import {
  findMatches,
  findPlayers,
  headToHead,
  teamStats,
  standings,
  aggregateStats,
  biggestWins,
  topScoringTeams,
  listCompetitions,
  listSeasons,
} from '../src/queries';

let store: DataStore;

beforeAll(() => {
  store = loadData({ dataDir: 'data/kaggle' });
});

describe('Feature: Match Queries', () => {
  it('Scenario: Find matches between two teams', () => {
    const matches = findMatches(store, { team: 'Flamengo', opponent: 'Fluminense', limit: 100 });
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) {
      expect(m.date).toBeTruthy();
      expect(m.competition).toBeTruthy();
      const hasFla = m.homeTeam.toLowerCase().includes('flamengo') || m.awayTeam.toLowerCase().includes('flamengo');
      const hasFlu = m.homeTeam.toLowerCase().includes('fluminense') || m.awayTeam.toLowerCase().includes('fluminense');
      expect(hasFla && hasFlu).toBe(true);
    }
  });

  it('Scenario: Filter by season', () => {
    const matches = findMatches(store, { team: 'Palmeiras', season: 2019, limit: 100 });
    expect(matches.length).toBeGreaterThan(0);
    expect(matches.every((m) => m.season === 2019)).toBe(true);
  });

  it('Scenario: Filter by competition', () => {
    const matches = findMatches(store, { competition: 'Libertadores', limit: 50 });
    expect(matches.length).toBeGreaterThan(0);
    expect(matches.every((m) => m.competition === 'Copa Libertadores')).toBe(true);
  });

  it('Scenario: Filter by date range', () => {
    const matches = findMatches(store, {
      dateFrom: '2019-01-01',
      dateTo: '2019-12-31',
      competition: 'Brasileirão Serie A',
      limit: 500,
    });
    expect(matches.length).toBeGreaterThan(0);
    expect(matches.every((m) => m.date >= '2019-01-01' && m.date <= '2019-12-31')).toBe(true);
  });

  it('returns matches sorted by date desc', () => {
    const matches = findMatches(store, { team: 'Corinthians', limit: 20 });
    for (let i = 1; i < matches.length; i++) {
      expect(matches[i - 1].date >= matches[i].date).toBe(true);
    }
  });
});

describe('Feature: Team Queries', () => {
  it('Scenario: Get team statistics for a season', () => {
    const stats = teamStats(store, { team: 'Palmeiras', season: 2019 });
    expect(stats.matches).toBeGreaterThan(0);
    expect(stats.wins + stats.draws + stats.losses).toBe(stats.matches);
    expect(stats.goalsFor).toBeGreaterThan(0);
    expect(stats.points).toBe(stats.wins * 3 + stats.draws);
  });

  it('Scenario: Get home-only stats', () => {
    const stats = teamStats(store, {
      team: 'Corinthians',
      season: 2022,
      competition: 'Brasileirão',
      venue: 'home',
    });
    expect(stats.matches).toBeGreaterThan(0);
    expect(stats.homeMatches).toBe(stats.matches);
    expect(stats.awayMatches).toBe(0);
  });

  it('Scenario: Head-to-head between two teams', () => {
    const h2h = headToHead(store, 'Flamengo', 'Fluminense', 50);
    expect(h2h.totalMatches).toBeGreaterThan(0);
    expect(h2h.teamAWins + h2h.teamBWins + h2h.draws).toBe(h2h.totalMatches);
    expect(h2h.matches.length).toBeLessThanOrEqual(50);
  });

  it('Scenario: Head-to-head handles name variations', () => {
    const a = headToHead(store, 'Palmeiras', 'Santos');
    const b = headToHead(store, 'Palmeiras-SP', 'Santos-SP');
    expect(a.totalMatches).toBe(b.totalMatches);
  });
});

describe('Feature: Player Queries', () => {
  it('Scenario: Find player by name', () => {
    const found = findPlayers(store, { name: 'Neymar' });
    expect(found.length).toBeGreaterThan(0);
    expect(found.some((p) => p.name.includes('Neymar'))).toBe(true);
  });

  it('Scenario: Filter by nationality (Brazilian players)', () => {
    const brazilians = findPlayers(store, { nationality: 'Brazil', limit: 50 });
    expect(brazilians.length).toBeGreaterThan(0);
    expect(brazilians.every((p) => p.nationality === 'Brazil')).toBe(true);
    for (let i = 1; i < brazilians.length; i++) {
      expect((brazilians[i - 1].overall ?? 0) >= (brazilians[i].overall ?? 0)).toBe(true);
    }
  });

  it('Scenario: Filter by club', () => {
    const flamengo = findPlayers(store, { club: 'Flamengo' });
    expect(flamengo.every((p) => (p.club ?? '').includes('Flamengo'))).toBe(true);
  });

  it('Scenario: Filter by minimum overall rating', () => {
    const elite = findPlayers(store, { minOverall: 90, limit: 20 });
    expect(elite.length).toBeGreaterThan(0);
    expect(elite.every((p) => (p.overall ?? 0) >= 90)).toBe(true);
  });

  it('Scenario: Accent-insensitive name search', () => {
    const a = findPlayers(store, { name: 'Coutinho' });
    const b = findPlayers(store, { name: 'COUTINHO' });
    expect(a.length).toBe(b.length);
  });
});

describe('Feature: Competition Queries', () => {
  it('Scenario: Compute league standings', () => {
    const table = standings(store, { season: 2019, competition: 'Brasileirão' });
    expect(table.length).toBeGreaterThan(0);
    for (let i = 1; i < table.length; i++) {
      expect(table[i - 1].points >= table[i].points).toBe(true);
    }
    for (const row of table) {
      expect(row.wins + row.draws + row.losses).toBe(row.matches);
    }
  });

  it('Scenario: 2019 Brasileirão champion is Flamengo (well-known result)', () => {
    const table = standings(store, { season: 2019, competition: 'Brasileirão' });
    const champion = table[0];
    expect(champion.team.toLowerCase()).toContain('flamengo');
  });

  it('list competitions returns all 5 loaded sources', () => {
    const comps = listCompetitions(store);
    expect(comps.length).toBe(5);
  });

  it('list seasons returns sorted years', () => {
    const seasons = listSeasons(store, 'Brasileirão Serie A');
    expect(seasons.length).toBeGreaterThan(0);
    for (let i = 1; i < seasons.length; i++) {
      expect(seasons[i - 1] < seasons[i]).toBe(true);
    }
  });
});

describe('Feature: Statistical Analysis', () => {
  it('Scenario: Aggregate stats over Brasileirão', () => {
    const stats = aggregateStats(store, { competition: 'Brasileirão Serie A' });
    expect(stats.totalMatches).toBeGreaterThan(0);
    expect(stats.averageGoalsPerMatch).toBeGreaterThan(0);
    expect(stats.homeWinRate + stats.awayWinRate + stats.drawRate).toBeCloseTo(1, 5);
  });

  it('Scenario: Biggest wins are sorted by goal difference', () => {
    const big = biggestWins(store, { competition: 'Brasileirão Serie A' }, 5);
    expect(big.length).toBe(5);
    for (let i = 1; i < big.length; i++) {
      const diffA = Math.abs(big[i - 1].homeGoals - big[i - 1].awayGoals);
      const diffB = Math.abs(big[i].homeGoals - big[i].awayGoals);
      expect(diffA >= diffB).toBe(true);
    }
  });

  it('Scenario: Top scoring teams in a season', () => {
    const top = topScoringTeams(store, { season: 2019, competition: 'Brasileirão' }, 5);
    expect(top.length).toBe(5);
    for (let i = 1; i < top.length; i++) {
      expect(top[i - 1].goals >= top[i].goals).toBe(true);
    }
  });

  it('home win rate in Brasileirão is greater than away win rate (known)', () => {
    const stats = aggregateStats(store, { competition: 'Brasileirão Serie A' });
    expect(stats.homeWinRate).toBeGreaterThan(stats.awayWinRate);
  });
});
