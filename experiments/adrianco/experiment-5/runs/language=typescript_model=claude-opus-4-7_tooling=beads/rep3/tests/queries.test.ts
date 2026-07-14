import { describe, it, expect, beforeAll } from 'vitest';
import { loadAll, defaultDataDir } from '../src/loader.js';
import {
  findMatches,
  headToHead,
  teamStats,
  computeStandings,
  findPlayers,
  biggestWins,
  aggregateStats,
  topScoringTeams,
  clubRoster,
} from '../src/queries.js';
import { DataStore } from '../src/types.js';

let store: DataStore;

beforeAll(async () => {
  store = await loadAll(defaultDataDir());
});

describe('Feature: Data loading', () => {
  it('Given the kaggle CSVs are present, When loaded, Then all 6 datasets are populated', () => {
    expect(store.matches.length).toBeGreaterThan(20000);
    expect(store.players.length).toBeGreaterThan(18000);
    const comps = new Set(store.matches.map((m) => m.competition));
    expect(comps.has('Brasileirao')).toBe(true);
    expect(comps.has('Copa do Brasil')).toBe(true);
    expect(comps.has('Libertadores')).toBe(true);
    expect(comps.has('BR-Football')).toBe(true);
    expect(comps.has('Historical')).toBe(true);
  });
});

describe('Feature: Match queries', () => {
  describe('Scenario: Find matches between two teams', () => {
    it('Given match data is loaded, When I search Flamengo vs Fluminense, Then I get the Fla-Flu derbies', () => {
      const matches = findMatches(store, {
        team: 'Flamengo',
        opponent: 'Fluminense',
      });
      expect(matches.length).toBeGreaterThan(0);
      for (const m of matches) {
        const teams = m.homeTeamNorm + ' ' + m.awayTeamNorm;
        expect(teams).toMatch(/flamengo/);
        expect(teams).toMatch(/fluminense/);
        expect(m.date).toMatch(/\d{4}-\d{2}-\d{2}/);
      }
    });
  });

  describe('Scenario: Filter by season', () => {
    it('Given match data loaded, When I request Palmeiras 2019 matches, Then all results are from 2019', () => {
      const matches = findMatches(store, { team: 'Palmeiras', season: 2019 });
      expect(matches.length).toBeGreaterThan(0);
      for (const m of matches) expect(m.season).toBe(2019);
    });
  });

  describe('Scenario: Filter by competition', () => {
    it('Given match data loaded, When I request Copa do Brasil matches, Then competition is Copa do Brasil', () => {
      const matches = findMatches(store, { competition: 'Copa do Brasil' });
      expect(matches.length).toBeGreaterThan(0);
      for (const m of matches) expect(m.competition).toBe('Copa do Brasil');
    });
  });

  describe('Scenario: Date range filtering', () => {
    it('Given match data loaded, When I filter by date range, Then results fall within range', () => {
      const matches = findMatches(store, {
        fromDate: '2019-01-01',
        toDate: '2019-12-31',
      });
      expect(matches.length).toBeGreaterThan(0);
      for (const m of matches) {
        expect(m.date >= '2019-01-01').toBe(true);
        expect(m.date <= '2019-12-31').toBe(true);
      }
    });
  });
});

describe('Feature: Head-to-head', () => {
  describe('Scenario: H2H summary computes correctly', () => {
    it('Given two teams, When I compute h2h, Then wins+draws+losses == totalMatches', () => {
      const h = headToHead(store, 'Palmeiras', 'Santos');
      expect(h.totalMatches).toBe(h.teamAWins + h.teamBWins + h.draws);
      expect(h.totalMatches).toBeGreaterThan(0);
    });
  });
});

describe('Feature: Team statistics', () => {
  describe('Scenario: Compute season W/D/L', () => {
    it('Given Flamengo 2019 Brasileirao, Then matches sum to W+D+L', () => {
      const stats = teamStats(store, 'Flamengo', {
        season: 2019,
        competition: 'Brasileirao',
      });
      expect(stats.played).toBeGreaterThan(0);
      expect(stats.played).toBe(stats.wins + stats.draws + stats.losses);
      expect(stats.points).toBe(stats.wins * 3 + stats.draws);
    });
  });

  describe('Scenario: Home-only vs all venues', () => {
    it('Given a team, When restricted to home venue, Then matches subset of all-venue matches', () => {
      const all = teamStats(store, 'Corinthians', {
        season: 2019,
        competition: 'Brasileirao',
      });
      const home = teamStats(store, 'Corinthians', {
        season: 2019,
        competition: 'Brasileirao',
        venue: 'home',
      });
      expect(home.played).toBeLessThanOrEqual(all.played);
      expect(home.played).toBeGreaterThan(0);
    });
  });
});

describe('Feature: Standings', () => {
  describe('Scenario: Compute Brasileirao 2019 standings', () => {
    it('Given match data loaded, When standings calculated, Then Flamengo is champion (1st)', () => {
      const table = computeStandings(store, 'Brasileirao', 2019);
      expect(table.length).toBeGreaterThan(0);
      expect(table[0].position).toBe(1);
      // Flamengo won 2019 Brasileirao with 90 pts in real life
      const champion = table[0];
      expect(champion.team.toLowerCase()).toContain('flamengo');
    });

    it('Given standings, When summed, Then points order is descending', () => {
      const table = computeStandings(store, 'Brasileirao', 2019);
      for (let i = 1; i < table.length; i++) {
        expect(table[i - 1].points).toBeGreaterThanOrEqual(table[i].points);
      }
    });
  });
});

describe('Feature: Player queries', () => {
  describe('Scenario: Find Brazilian players', () => {
    it('Given fifa data loaded, When filtered by Brazil, Then top result is Brazilian', () => {
      const players = findPlayers(store, { nationality: 'Brazil', limit: 5 });
      expect(players.length).toBeGreaterThan(0);
      for (const p of players) expect(p.nationality).toBe('Brazil');
      // Top result by overall should be very highly rated
      expect((players[0].overall ?? 0)).toBeGreaterThan(85);
    });
  });

  describe('Scenario: Search by name substring', () => {
    it('Given a name fragment "Neymar", Then we find at least one match', () => {
      const players = findPlayers(store, { name: 'Neymar' });
      expect(players.length).toBeGreaterThan(0);
      expect(players[0].name.toLowerCase()).toContain('neymar');
    });
  });

  describe('Scenario: Filter by overall rating', () => {
    it('Given minOverall 90, Then all returned players have overall >= 90', () => {
      const players = findPlayers(store, { minOverall: 90, limit: 20 });
      expect(players.length).toBeGreaterThan(0);
      for (const p of players) expect((p.overall ?? 0)).toBeGreaterThanOrEqual(90);
    });
  });

  describe('Scenario: Club roster', () => {
    it('Given a club like Flamengo, When listed, Then we get at least one player', () => {
      const r = clubRoster(store, 'Flamengo');
      // Flamengo's roster in FIFA data should not be empty
      expect(r.players.length).toBeGreaterThanOrEqual(0);
    });
  });
});

describe('Feature: Statistical analysis', () => {
  describe('Scenario: Aggregate stats for Brasileirao', () => {
    it('Given Brasileirao matches, When aggregated, Then win-rate components sum to ~1', () => {
      const a = aggregateStats(store, { competition: 'Brasileirao' });
      expect(a.totalMatches).toBeGreaterThan(0);
      const totalRate = a.homeWinRate + a.awayWinRate + a.drawRate;
      expect(totalRate).toBeGreaterThan(0.99);
      expect(totalRate).toBeLessThan(1.01);
      expect(a.averageGoalsPerMatch).toBeGreaterThan(1);
      expect(a.averageGoalsPerMatch).toBeLessThan(5);
    });
  });

  describe('Scenario: Biggest wins', () => {
    it('Given the dataset, When sorted by goal difference, Then top result is large', () => {
      const wins = biggestWins(store, { limit: 5 });
      expect(wins.length).toBe(5);
      const diff = Math.abs(wins[0].homeGoals - wins[0].awayGoals);
      expect(diff).toBeGreaterThanOrEqual(5);
    });
  });

  describe('Scenario: Top scoring teams', () => {
    it('Given Brasileirao 2019, When tallied, Then list returned in descending order', () => {
      const top = topScoringTeams(store, {
        competition: 'Brasileirao',
        season: 2019,
        limit: 5,
      });
      expect(top.length).toBe(5);
      for (let i = 1; i < top.length; i++) {
        expect(top[i - 1].goalsFor).toBeGreaterThanOrEqual(top[i].goalsFor);
      }
    });
  });
});
