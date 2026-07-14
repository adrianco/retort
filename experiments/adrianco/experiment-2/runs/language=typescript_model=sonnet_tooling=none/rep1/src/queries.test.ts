/**
 * BDD-style tests for Brazilian Soccer MCP Server
 *
 * Feature: Match Queries
 * Feature: Team Queries
 * Feature: Player Queries
 * Feature: Competition Queries
 * Feature: Statistical Analysis
 */

import {
  searchMatches,
  getTeamStats,
  getHeadToHead,
  getStandings,
  getBiggestWins,
  getCompetitionStats,
  searchPlayers,
  getBestTeams,
  getExtendedStats,
} from './queries';

import {
  loadBrasileiraoMatches,
  loadCupMatches,
  loadLibertadoresMatches,
  loadHistoricalMatches,
  loadBRFootballMatches,
  loadFifaPlayers,
  normalizeDate,
  normalizeTeamName,
  teamMatches,
} from './dataLoader';

// ─── Feature: Data Loading ────────────────────────────────────────────────────

describe('Feature: Data Loading', () => {
  describe('Scenario: Load all CSV datasets', () => {
    it('should load Brasileirao matches', () => {
      const matches = loadBrasileiraoMatches();
      expect(matches.length).toBeGreaterThan(0);
      expect(matches[0]).toHaveProperty('home_team');
      expect(matches[0]).toHaveProperty('away_team');
      expect(matches[0]).toHaveProperty('home_goal');
      expect(matches[0]).toHaveProperty('competition', 'Brasileirao');
    });

    it('should load Copa do Brasil matches', () => {
      const matches = loadCupMatches();
      expect(matches.length).toBeGreaterThan(0);
      expect(matches[0]).toHaveProperty('competition', 'Copa do Brasil');
    });

    it('should load Libertadores matches', () => {
      const matches = loadLibertadoresMatches();
      expect(matches.length).toBeGreaterThan(0);
      expect(matches[0]).toHaveProperty('competition', 'Libertadores');
    });

    it('should load historical Brasileirao matches', () => {
      const matches = loadHistoricalMatches();
      expect(matches.length).toBeGreaterThan(0);
      expect(matches[0]).toHaveProperty('competition', 'Brasileirao (Historical)');
    });

    it('should load BR Football extended dataset', () => {
      const matches = loadBRFootballMatches();
      expect(matches.length).toBeGreaterThan(0);
      expect(matches[0]).toHaveProperty('total_corners');
    });

    it('should load FIFA player data', () => {
      const players = loadFifaPlayers();
      expect(players.length).toBeGreaterThan(0);
      expect(players[0]).toHaveProperty('Name');
      expect(players[0]).toHaveProperty('Overall');
    });
  });

  describe('Scenario: Date normalization', () => {
    it('should normalize Brazilian format DD/MM/YYYY', () => {
      expect(normalizeDate('29/03/2003')).toBe('2003-03-29');
    });

    it('should normalize ISO format YYYY-MM-DD', () => {
      expect(normalizeDate('2023-09-24')).toBe('2023-09-24');
    });

    it('should normalize datetime with time component', () => {
      expect(normalizeDate('2012-05-19 18:30:00')).toBe('2012-05-19');
    });

    it('should handle empty string', () => {
      expect(normalizeDate('')).toBe('');
    });
  });

  describe('Scenario: Team name normalization', () => {
    it('should strip state suffix', () => {
      expect(normalizeTeamName('Palmeiras-SP')).toBe('Palmeiras');
      expect(normalizeTeamName('Flamengo-RJ')).toBe('Flamengo');
    });

    it('should leave names without suffix unchanged', () => {
      expect(normalizeTeamName('Palmeiras')).toBe('Palmeiras');
    });

    it('should match teams with and without suffix', () => {
      expect(teamMatches('Flamengo', 'Flamengo-RJ')).toBe(true);
      expect(teamMatches('Palmeiras', 'Palmeiras-SP')).toBe(true);
    });

    it('should match partial names', () => {
      expect(teamMatches('Corinthians', 'Corinthians')).toBe(true);
    });
  });
});

// ─── Feature: Match Queries ───────────────────────────────────────────────────

describe('Feature: Match Queries', () => {
  describe('Scenario: Find matches between two teams', () => {
    it('Given the match data is loaded, When I search for matches between Flamengo and Fluminense, Then I should receive a list of matches with date, scores, and competition', () => {
      const matches = searchMatches({ team1: 'Flamengo', team2: 'Fluminense' });
      expect(matches.length).toBeGreaterThan(0);
      for (const m of matches) {
        expect(m).toHaveProperty('date');
        expect(m).toHaveProperty('home_goal');
        expect(m).toHaveProperty('away_goal');
        expect(m).toHaveProperty('competition');
      }
    });

    it('should find Palmeiras matches', () => {
      const matches = searchMatches({ team: 'Palmeiras' });
      expect(matches.length).toBeGreaterThan(0);
      for (const m of matches) {
        const involved =
          m.home_team.toLowerCase().includes('palmeiras') ||
          m.away_team.toLowerCase().includes('palmeiras');
        expect(involved).toBe(true);
      }
    });

    it('should filter by competition', () => {
      const matches = searchMatches({ competition: 'Copa do Brasil', limit: 10 });
      expect(matches.length).toBeGreaterThan(0);
      for (const m of matches) {
        expect(m.competition).toBe('Copa do Brasil');
      }
    });

    it('should filter by season', () => {
      const matches = searchMatches({ season: 2019, competition: 'Brasileirao', limit: 100 });
      expect(matches.length).toBeGreaterThan(0);
      for (const m of matches) {
        expect(m.season).toBe(2019);
      }
    });

    it('should filter by date range', () => {
      const matches = searchMatches({
        date_from: '2023-01-01',
        date_to: '2023-12-31',
        limit: 20,
      });
      for (const m of matches) {
        expect(m.date >= '2023-01-01').toBe(true);
        expect(m.date <= '2023-12-31').toBe(true);
      }
    });

    it('should respect limit parameter', () => {
      const matches = searchMatches({ limit: 5 });
      expect(matches.length).toBeLessThanOrEqual(5);
    });

    it('should return results sorted by date descending', () => {
      const matches = searchMatches({ limit: 20 });
      for (let i = 1; i < matches.length; i++) {
        expect(matches[i - 1].date >= matches[i].date).toBe(true);
      }
    });

    it('should find Libertadores matches', () => {
      const matches = searchMatches({ competition: 'Libertadores', limit: 10 });
      expect(matches.length).toBeGreaterThan(0);
      for (const m of matches) {
        expect(m.competition).toBe('Libertadores');
      }
    });
  });

  describe('Scenario: Find matches for specific team in season', () => {
    it('should find Flamengo matches in 2019', () => {
      const matches = searchMatches({ team: 'Flamengo', season: 2019 });
      expect(matches.length).toBeGreaterThan(0);
      for (const m of matches) {
        expect(m.season).toBe(2019);
      }
    });

    it('should find Corinthians Brasileirao matches', () => {
      const matches = searchMatches({ team: 'Corinthians', competition: 'Brasileirao' });
      expect(matches.length).toBeGreaterThan(0);
    });
  });
});

// ─── Feature: Team Queries ────────────────────────────────────────────────────

describe('Feature: Team Queries', () => {
  describe('Scenario: Get team statistics', () => {
    it('Given the match data is loaded, When I request statistics for Palmeiras in season 2023, Then I should receive wins, losses, draws, and goals', () => {
      const stats = getTeamStats({ team: 'Palmeiras', season: 2023 });
      expect(stats).toHaveProperty('wins');
      expect(stats).toHaveProperty('losses');
      expect(stats).toHaveProperty('draws');
      expect(stats).toHaveProperty('goals_for');
      expect(stats).toHaveProperty('goals_against');
      expect(stats.matches).toBeGreaterThanOrEqual(0);
      expect(stats.wins + stats.draws + stats.losses).toBe(stats.matches);
    });

    it('should calculate points correctly (3 per win, 1 per draw)', () => {
      const stats = getTeamStats({ team: 'Flamengo', season: 2019, competition: 'Brasileirao' });
      const expectedPoints = stats.wins * 3 + stats.draws;
      expect(stats.points).toBe(expectedPoints);
    });

    it('should support home_only filter', () => {
      const homeStats = getTeamStats({ team: 'Corinthians', home_only: true });
      const awayStats = getTeamStats({ team: 'Corinthians', away_only: true });
      const allStats = getTeamStats({ team: 'Corinthians' });
      expect(homeStats.matches + awayStats.matches).toBe(allStats.matches);
    });

    it('should handle unknown team gracefully', () => {
      const stats = getTeamStats({ team: 'NonExistentTeamXYZ' });
      expect(stats.matches).toBe(0);
      expect(stats.wins).toBe(0);
    });
  });

  describe('Scenario: Get best teams', () => {
    it('should return teams ranked by win rate', () => {
      const teams = getBestTeams('overall', undefined, undefined, 10);
      expect(teams.length).toBeGreaterThan(0);
      for (let i = 1; i < teams.length; i++) {
        const wrA = teams[i - 1].matches > 0 ? teams[i - 1].wins / teams[i - 1].matches : 0;
        const wrB = teams[i].matches > 0 ? teams[i].wins / teams[i].matches : 0;
        expect(wrA >= wrB).toBe(true);
      }
    });

    it('should support home performance mode', () => {
      const teams = getBestTeams('home', 'Brasileirao', undefined, 5);
      expect(teams.length).toBeGreaterThan(0);
    });

    it('should support away performance mode', () => {
      const teams = getBestTeams('away', undefined, 2019, 5);
      expect(teams.length).toBeGreaterThan(0);
    });
  });
});

// ─── Feature: Head-to-Head ────────────────────────────────────────────────────

describe('Feature: Head-to-Head Queries', () => {
  it('should return correct aggregate stats', () => {
    const h2h = getHeadToHead('Flamengo', 'Fluminense');
    expect(h2h.total_matches).toBe(h2h.team1_wins + h2h.team2_wins + h2h.draws);
    expect(h2h.team1_goals).toBeGreaterThanOrEqual(0);
    expect(h2h.team2_goals).toBeGreaterThanOrEqual(0);
  });

  it('should return recent matches sorted by date', () => {
    const h2h = getHeadToHead('Palmeiras', 'Santos', 10);
    for (let i = 1; i < h2h.matches.length; i++) {
      expect(h2h.matches[i - 1].date >= h2h.matches[i].date).toBe(true);
    }
  });

  it('should handle teams with no matches', () => {
    const h2h = getHeadToHead('TeamA_xyz', 'TeamB_xyz');
    expect(h2h.total_matches).toBe(0);
    expect(h2h.team1_wins).toBe(0);
  });

  it('should find Flamengo vs Corinthians matches', () => {
    const h2h = getHeadToHead('Flamengo', 'Corinthians');
    expect(h2h.total_matches).toBeGreaterThan(0);
  });
});

// ─── Feature: Competition Queries ────────────────────────────────────────────

describe('Feature: Competition Queries', () => {
  describe('Scenario: Get standings', () => {
    it('should calculate 2019 Brasileirao standings', () => {
      const standings = getStandings(2019, 'Brasileirao');
      expect(standings.length).toBeGreaterThan(0);
      // Standings should be sorted by points descending
      for (let i = 1; i < standings.length; i++) {
        expect(standings[i - 1].points >= standings[i].points).toBe(true);
      }
    });

    it('should include top teams in 2019 standings', () => {
      const standings = getStandings(2019);
      const names = standings.map((t) => t.team.toLowerCase());
      const hasFlamengo = names.some((n) => n.includes('flamengo'));
      expect(hasFlamengo).toBe(true);
    });

    it('should return empty array for non-existent season', () => {
      const standings = getStandings(1800);
      expect(standings).toEqual([]);
    });

    it('should calculate correct match counts', () => {
      const standings = getStandings(2019);
      // Each team should have same number of matches (38 in Serie A)
      if (standings.length >= 20) {
        const topTeam = standings[0];
        expect(topTeam.wins + topTeam.draws + topTeam.losses).toBe(topTeam.matches);
      }
    });
  });
});

// ─── Feature: Statistical Analysis ───────────────────────────────────────────

describe('Feature: Statistical Analysis', () => {
  describe('Scenario: Competition statistics', () => {
    it('should calculate average goals per match for Brasileirao', () => {
      const stats = getCompetitionStats('Brasileirao');
      expect(stats.avg_goals_per_match).toBeGreaterThan(0);
      expect(stats.avg_goals_per_match).toBeLessThan(10);
      expect(stats.total_matches).toBeGreaterThan(0);
    });

    it('should verify home_wins + away_wins + draws = total_matches', () => {
      const stats = getCompetitionStats('Brasileirao');
      expect(stats.home_wins + stats.away_wins + stats.draws).toBe(stats.total_matches);
    });

    it('should work for Libertadores', () => {
      const stats = getCompetitionStats('Libertadores');
      expect(stats.total_matches).toBeGreaterThan(0);
    });

    it('should work for a specific season', () => {
      const stats = getCompetitionStats('Brasileirao', 2019);
      expect(stats.total_matches).toBeGreaterThan(0);
      expect(stats.season).toBe(2019);
    });
  });

  describe('Scenario: Biggest wins', () => {
    it('should return matches sorted by goal margin', () => {
      const wins = getBiggestWins(undefined, undefined, 10);
      expect(wins.length).toBeGreaterThan(0);
      for (let i = 1; i < wins.length; i++) {
        const marginA = Math.abs((wins[i - 1] as any).home_goal - (wins[i - 1] as any).away_goal);
        const marginB = Math.abs((wins[i] as any).home_goal - (wins[i] as any).away_goal);
        expect(marginA >= marginB).toBe(true);
      }
    });

    it('should filter by competition', () => {
      const wins = getBiggestWins('Libertadores', undefined, 5);
      for (const m of wins) {
        expect(m.competition.toLowerCase()).toContain('libertadores');
      }
    });

    it('should have valid goal counts', () => {
      const wins = getBiggestWins(undefined, undefined, 10);
      for (const m of wins) {
        expect(m.home_goal).toBeGreaterThanOrEqual(0);
        expect(m.away_goal).toBeGreaterThanOrEqual(0);
      }
    });
  });

  describe('Scenario: Extended match statistics', () => {
    it('should return matches with corner and shot data', () => {
      const result = getExtendedStats(undefined, undefined, 10);
      expect(result.matches.length).toBeGreaterThan(0);
      expect(result.avg_corners).toBeGreaterThan(0);
    });

    it('should filter by team', () => {
      const result = getExtendedStats('Flamengo', undefined, 10);
      for (const m of result.matches) {
        const involved =
          m.home.toLowerCase().includes('flamengo') ||
          m.away.toLowerCase().includes('flamengo');
        expect(involved).toBe(true);
      }
    });
  });
});

// ─── Feature: Player Queries ──────────────────────────────────────────────────

describe('Feature: Player Queries', () => {
  describe('Scenario: Search by nationality', () => {
    it('should find Brazilian players', () => {
      const players = searchPlayers({ nationality: 'Brazil', limit: 10 });
      expect(players.length).toBeGreaterThan(0);
      for (const p of players) {
        expect(p.Nationality.toLowerCase()).toContain('brazil');
      }
    });

    it('should return players sorted by overall rating descending', () => {
      const players = searchPlayers({ nationality: 'Brazil', limit: 10 });
      for (let i = 1; i < players.length; i++) {
        expect(players[i - 1].Overall >= players[i].Overall).toBe(true);
      }
    });
  });

  describe('Scenario: Search by name', () => {
    it('should find player by partial name', () => {
      const players = searchPlayers({ name: 'Neymar', limit: 5 });
      expect(players.length).toBeGreaterThan(0);
      for (const p of players) {
        expect(p.Name.toLowerCase()).toContain('neymar');
      }
    });
  });

  describe('Scenario: Search by club', () => {
    it('should find players at Flamengo', () => {
      const players = searchPlayers({ club: 'Flamengo', limit: 20 });
      for (const p of players) {
        expect(p.Club.toLowerCase()).toContain('flamengo');
      }
    });
  });

  describe('Scenario: Filter by minimum overall rating', () => {
    it('should only return players above minimum rating', () => {
      const players = searchPlayers({ min_overall: 85, limit: 20 });
      expect(players.length).toBeGreaterThan(0);
      for (const p of players) {
        expect(p.Overall).toBeGreaterThanOrEqual(85);
      }
    });
  });

  describe('Scenario: Filter by position', () => {
    it('should find goalkeeper players', () => {
      const players = searchPlayers({ position: 'GK', nationality: 'Brazil', limit: 10 });
      expect(players.length).toBeGreaterThan(0);
      for (const p of players) {
        expect(p.Position.toUpperCase()).toContain('GK');
      }
    });
  });

  describe('Scenario: Find top-rated Brazilian players', () => {
    it('should return top Brazilian players with valid data', () => {
      const players = searchPlayers({ nationality: 'Brazil', min_overall: 80, limit: 10 });
      expect(players.length).toBeGreaterThan(0);
      expect(players[0].Overall).toBeGreaterThanOrEqual(80);
    });
  });
});
