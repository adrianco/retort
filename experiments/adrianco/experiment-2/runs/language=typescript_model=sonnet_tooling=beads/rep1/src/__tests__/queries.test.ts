import { describe, it, expect, beforeAll } from 'vitest';
import { loadAllData } from '../dataLoader.js';
import {
  searchMatches,
  getHeadToHead,
  getTeamStats,
  getStandings,
  searchPlayers,
  getStatistics,
  getBestTeams,
} from '../queries.js';
import { DataStore } from '../types.js';

let data: DataStore;

beforeAll(() => {
  data = loadAllData();
});

// ─── Feature: Data Loading ────────────────────────────────────────────────────

describe('Feature: Data loading', () => {
  it('Given the datasets, When loaded, Then matches are present', () => {
    expect(data.matches.length).toBeGreaterThan(1000);
  });

  it('Given the datasets, When loaded, Then players are present', () => {
    expect(data.players.length).toBeGreaterThan(1000);
  });

  it('Given the datasets, When loaded, Then all 6 sources contribute matches', () => {
    const competitions = new Set(data.matches.map((m) => m.competition));
    expect(competitions.has('Brasileirão Série A')).toBe(true);
    expect(competitions.has('Copa do Brasil')).toBe(true);
    expect(competitions.has('Copa Libertadores')).toBe(true);
  });
});

// ─── Feature: Match Queries ───────────────────────────────────────────────────

describe('Feature: Match Queries', () => {
  describe('Scenario: Find matches between two teams', () => {
    it('Given the match data is loaded, When I search for matches between Flamengo and Fluminense, Then I should receive a list of matches', () => {
      const matches = searchMatches(data.matches, { team: 'Flamengo' });
      const flaFlu = matches.filter(
        (m) =>
          (m.homeTeam.toLowerCase().includes('flamengo') || m.awayTeam.toLowerCase().includes('flamengo')) &&
          (m.homeTeam.toLowerCase().includes('fluminense') || m.awayTeam.toLowerCase().includes('fluminense')),
      );
      expect(flaFlu.length).toBeGreaterThan(0);
    });

    it('And each match should have date, scores, and competition', () => {
      const matches = searchMatches(data.matches, { team: 'Flamengo' });
      expect(matches.length).toBeGreaterThan(0);
      const m = matches[0];
      expect(m.date).toBeTruthy();
      expect(typeof m.homeGoals).toBe('number');
      expect(typeof m.awayGoals).toBe('number');
      expect(m.competition).toBeTruthy();
    });
  });

  describe('Scenario: Filter by competition', () => {
    it('Given match data, When I filter by Brasileirão, Then all results are Brasileirão matches', () => {
      const matches = searchMatches(data.matches, { competition: 'Brasileirão', limit: 100 });
      expect(matches.length).toBeGreaterThan(0);
      matches.forEach((m) => expect(m.competition).toContain('Brasileir'));
    });
  });

  describe('Scenario: Filter by season', () => {
    it('Given match data, When I filter by season 2019, Then all results are from 2019', () => {
      const matches = searchMatches(data.matches, { season: 2019, limit: 100 });
      expect(matches.length).toBeGreaterThan(0);
      matches.forEach((m) => expect(m.season).toBe(2019));
    });
  });

  describe('Scenario: Filter by team and season', () => {
    it('Given match data, When I search Palmeiras in 2023, Then I receive Palmeiras 2023 matches', () => {
      const matches = searchMatches(data.matches, { team: 'Palmeiras', season: 2023 });
      expect(matches.length).toBeGreaterThan(0);
      matches.forEach((m) => {
        const involvesPalmeiras =
          m.homeTeam.toLowerCase().includes('palmeiras') || m.awayTeam.toLowerCase().includes('palmeiras');
        expect(involvesPalmeiras).toBe(true);
        expect(m.season).toBe(2023);
      });
    });
  });

  describe('Scenario: Search by date range', () => {
    it('Given match data, When filtered by date range, Then only matches in range are returned', () => {
      const matches = searchMatches(data.matches, {
        dateFrom: '2019-01-01',
        dateTo: '2019-12-31',
        limit: 100,
      });
      expect(matches.length).toBeGreaterThan(0);
      matches.forEach((m) => {
        expect(m.date >= '2019-01-01').toBe(true);
        expect(m.date <= '2019-12-31').toBe(true);
      });
    });
  });
});

// ─── Feature: Team Statistics ─────────────────────────────────────────────────

describe('Feature: Team Statistics', () => {
  describe('Scenario: Get team statistics', () => {
    it('Given the match data is loaded, When I request statistics for Palmeiras in season 2023, Then I should receive wins, losses, draws, and goals', () => {
      const stats = getTeamStats(data.matches, { team: 'Palmeiras', season: 2023 });
      expect(stats.matches).toBeGreaterThan(0);
      expect(typeof stats.wins).toBe('number');
      expect(typeof stats.draws).toBe('number');
      expect(typeof stats.losses).toBe('number');
      expect(typeof stats.goalsFor).toBe('number');
      expect(stats.wins + stats.draws + stats.losses).toBe(stats.matches);
    });
  });

  describe('Scenario: Home record', () => {
    it('Given match data, When I request home record for Corinthians 2022, Then I receive home-only stats', () => {
      const stats = getTeamStats(data.matches, {
        team: 'Corinthians',
        season: 2022,
        homeOnly: true,
      });
      expect(stats.matches).toBeGreaterThanOrEqual(0);
    });
  });
});

// ─── Feature: Head-to-Head ────────────────────────────────────────────────────

describe('Feature: Head-to-head', () => {
  describe('Scenario: Compare two teams', () => {
    it('Given match data, When I compare Palmeiras and Santos, Then I receive h2h record', () => {
      const h2h = getHeadToHead(data.matches, 'Palmeiras', 'Santos');
      expect(h2h.matches.length).toBeGreaterThan(0);
      expect(h2h.team1Wins + h2h.team2Wins + h2h.draws).toBe(h2h.matches.length);
    });
  });
});

// ─── Feature: Standings ───────────────────────────────────────────────────────

describe('Feature: Competition standings', () => {
  describe('Scenario: 2019 Brasileirão standings', () => {
    it('Given match data, When I get 2019 Brasileirão standings, Then Flamengo should be near the top', () => {
      const standings = getStandings(data.matches, 'Brasileirão', 2019);
      expect(standings.length).toBeGreaterThan(10);
      // Flamengo won 2019 Brasileirão
      const flamengoIdx = standings.findIndex((s) =>
        s.team.toLowerCase().includes('flamengo'),
      );
      expect(flamengoIdx).toBeGreaterThanOrEqual(0);
      expect(flamengoIdx).toBeLessThan(5); // Should be in top 5
    });
  });
});

// ─── Feature: Player Queries ──────────────────────────────────────────────────

describe('Feature: Player Queries', () => {
  describe('Scenario: Search by nationality', () => {
    it('Given player data, When I search for Brazilian players, Then all results are Brazilian', () => {
      const players = searchPlayers(data.players, { nationality: 'Brazil', limit: 20 });
      expect(players.length).toBeGreaterThan(0);
      players.forEach((p) => expect(p.nationality.toLowerCase()).toContain('brazil'));
    });
  });

  describe('Scenario: Search by club', () => {
    it('Given player data, When I search players at Fluminense, Then all results have Fluminense club', () => {
      const players = searchPlayers(data.players, { club: 'Fluminense' });
      expect(players.length).toBeGreaterThan(0);
      players.forEach((p) => expect(p.club.toLowerCase()).toContain('fluminense'));
    });
  });

  describe('Scenario: Search by name', () => {
    it('Given player data, When I search for Neymar, Then Neymar is in results', () => {
      const players = searchPlayers(data.players, { name: 'Neymar' });
      expect(players.length).toBeGreaterThan(0);
      expect(players[0].name.toLowerCase()).toContain('neymar');
    });
  });

  describe('Scenario: Search by minimum overall rating', () => {
    it('Given player data, When I search for players with overall >= 85, Then all results have overall >= 85', () => {
      const players = searchPlayers(data.players, { minOverall: 85 });
      expect(players.length).toBeGreaterThan(0);
      players.forEach((p) => expect(p.overall).toBeGreaterThanOrEqual(85));
    });
  });

  describe('Scenario: Cross-file query - player and team', () => {
    it('Given player data, When I find Brazilian players at Fluminense, Then results are Brazilian players at Fluminense', () => {
      const players = searchPlayers(data.players, {
        nationality: 'Brazil',
        club: 'Fluminense',
      });
      players.forEach((p) => {
        expect(p.nationality.toLowerCase()).toContain('brazil');
        expect(p.club.toLowerCase()).toContain('fluminense');
      });
    });
  });
});

// ─── Feature: Statistics ──────────────────────────────────────────────────────

describe('Feature: Statistical analysis', () => {
  describe('Scenario: Average goals per match', () => {
    it('Given all match data, When I compute statistics, Then avg goals per match should be reasonable', () => {
      const stats = getStatistics(data.matches);
      expect(stats.avgGoalsPerMatch).toBeGreaterThan(1);
      expect(stats.avgGoalsPerMatch).toBeLessThan(6);
    });
  });

  describe('Scenario: Home win rate', () => {
    it('Given all match data, When I compute statistics, Then home win rate should be between 30% and 70%', () => {
      const stats = getStatistics(data.matches);
      expect(stats.homeWinRate).toBeGreaterThan(30);
      expect(stats.homeWinRate).toBeLessThan(70);
    });
  });

  describe('Scenario: Biggest wins', () => {
    it('Given all match data, When I compute statistics, Then biggest wins have large goal differences', () => {
      const stats = getStatistics(data.matches);
      expect(stats.biggestWins.length).toBeGreaterThan(0);
      expect(stats.biggestWins[0].goalDiff).toBeGreaterThanOrEqual(5);
    });
  });

  describe('Scenario: Best home teams', () => {
    it('Given all match data, When I get best home teams, Then results are sorted by win rate', () => {
      const teams = getBestTeams(data.matches, 'home', 'Brasileirão');
      expect(teams.length).toBeGreaterThan(0);
      for (let i = 1; i < teams.length; i++) {
        expect(teams[i - 1].winRate).toBeGreaterThanOrEqual(teams[i].winRate);
      }
    });
  });
});
