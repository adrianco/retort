import { describe, it, expect } from "vitest";
import {
  searchMatches,
  getTeamStats,
  getHeadToHead,
  getStandings,
  searchPlayers,
  getBiggestWins,
  getAverageGoals,
  getTopScoringTeams,
} from "./queries.js";

describe("Match Queries", () => {
  describe("Scenario: Find matches between two teams", () => {
    it("Given the match data is loaded, when I search for Flamengo matches, then I should receive a list of matches", () => {
      const results = searchMatches({ team: "Flamengo" });
      expect(results.length).toBeGreaterThan(0);
      for (const m of results) {
        const involved =
          m.homeTeam.toLowerCase().includes("flamengo") ||
          m.awayTeam.toLowerCase().includes("flamengo");
        expect(involved).toBe(true);
      }
    });

    it("Given the match data is loaded, when I search for matches between Flamengo and Fluminense, then each match should have date, scores, and competition", () => {
      const results = searchMatches({ homeTeam: "Flamengo", awayTeam: "Fluminense" });
      expect(results.length).toBeGreaterThan(0);
      for (const m of results) {
        expect(m.datetime).toBeTruthy();
        expect(m.homeGoal).toBeGreaterThanOrEqual(0);
        expect(m.awayGoal).toBeGreaterThanOrEqual(0);
        expect(m.competition).toBeTruthy();
      }
    });
  });

  describe("Scenario: Filter matches by competition", () => {
    it("should find Copa do Brasil matches", () => {
      const results = searchMatches({ competition: "Copa do Brasil", limit: 10 });
      expect(results.length).toBeGreaterThan(0);
      for (const m of results) {
        expect(m.competition.toLowerCase()).toContain("copa do brasil");
      }
    });

    it("should find Copa Libertadores matches", () => {
      const results = searchMatches({ competition: "Libertadores", limit: 10 });
      expect(results.length).toBeGreaterThan(0);
      for (const m of results) {
        expect(m.competition.toLowerCase()).toContain("libertadores");
      }
    });
  });

  describe("Scenario: Filter matches by season", () => {
    it("should find Palmeiras matches in 2019", () => {
      const results = searchMatches({ team: "Palmeiras", season: 2019 });
      expect(results.length).toBeGreaterThan(0);
      for (const m of results) {
        expect(m.season).toBe(2019);
      }
    });
  });

  describe("Scenario: Filter matches by date range", () => {
    it("should find matches within a date range", () => {
      const results = searchMatches({ dateFrom: "2019-01-01", dateTo: "2019-12-31", limit: 10 });
      expect(results.length).toBeGreaterThan(0);
      for (const m of results) {
        expect(m.datetime >= "2019-01-01").toBe(true);
        expect(m.datetime <= "2019-12-31").toBe(true);
      }
    });
  });
});

describe("Team Statistics", () => {
  describe("Scenario: Get team statistics", () => {
    it("Given the match data is loaded, when I request statistics for Palmeiras, then I should receive wins, losses, draws, and goals", () => {
      const stats = getTeamStats("Palmeiras");
      expect(stats.team).toBe("Palmeiras");
      expect(stats.matches).toBeGreaterThan(0);
      expect(stats.wins).toBeGreaterThan(0);
      expect(stats.losses).toBeGreaterThanOrEqual(0);
      expect(stats.draws).toBeGreaterThanOrEqual(0);
      expect(stats.goalsFor).toBeGreaterThan(0);
      expect(stats.goalsAgainst).toBeGreaterThanOrEqual(0);
      expect(stats.wins + stats.draws + stats.losses).toBe(stats.matches);
    });

    it("should calculate home-only stats for Corinthians", () => {
      const stats = getTeamStats("Corinthians", { homeOnly: true });
      expect(stats.matches).toBeGreaterThan(0);
      expect(stats.winRate).toBeGreaterThanOrEqual(0);
    });

    it("should filter stats by season", () => {
      const stats = getTeamStats("Flamengo", { season: 2019 });
      expect(stats.matches).toBeGreaterThan(0);
      expect(stats.winRate).toBeGreaterThan(0);
    });
  });
});

describe("Head to Head", () => {
  describe("Scenario: Compare two teams", () => {
    it("should return head-to-head data for Flamengo vs Fluminense", () => {
      const h2h = getHeadToHead("Flamengo", "Fluminense");
      expect(h2h.totalMatches).toBeGreaterThan(0);
      expect(h2h.team1).toBe("Flamengo");
      expect(h2h.team2).toBe("Fluminense");
      expect(h2h.team1Wins + h2h.team2Wins + h2h.draws).toBe(h2h.totalMatches);
      expect(h2h.matches.length).toBeGreaterThan(0);
    });

    it("should return head-to-head data for Palmeiras vs Santos", () => {
      const h2h = getHeadToHead("Palmeiras", "Santos");
      expect(h2h.totalMatches).toBeGreaterThan(0);
    });
  });
});

describe("Standings", () => {
  describe("Scenario: Calculate league standings", () => {
    it("should calculate 2019 Brasileirão standings", () => {
      const table = getStandings(2019);
      expect(table.length).toBeGreaterThan(0);
      expect(table[0].points).toBeGreaterThan(0);
      for (const team of table) {
        expect(team.wins + team.draws + team.losses).toBe(team.matches);
        expect(team.points).toBe(team.wins * 3 + team.draws);
      }
    });

    it("should have Flamengo near the top in 2019", () => {
      const table = getStandings(2019);
      const flamengoPos = table.findIndex(
        (t) => t.team.toLowerCase().includes("flamengo")
      );
      expect(flamengoPos).toBeGreaterThanOrEqual(0);
      expect(flamengoPos).toBeLessThan(5);
    });
  });
});

describe("Player Queries", () => {
  describe("Scenario: Search players by name", () => {
    it("should find Messi", () => {
      const players = searchPlayers({ name: "Messi" });
      expect(players.length).toBeGreaterThan(0);
      expect(players[0].name).toContain("Messi");
    });
  });

  describe("Scenario: Search Brazilian players", () => {
    it("should find Brazilian players", () => {
      const players = searchPlayers({ nationality: "Brazil", limit: 10 });
      expect(players.length).toBeGreaterThan(0);
      for (const p of players) {
        expect(p.nationality).toBe("Brazil");
      }
    });
  });

  describe("Scenario: Search players by club", () => {
    it("should find players at Santos", () => {
      const players = searchPlayers({ club: "Santos" });
      expect(players.length).toBeGreaterThan(0);
      for (const p of players) {
        expect(p.club.toLowerCase()).toContain("santos");
      }
    });
  });

  describe("Scenario: Search players by position", () => {
    it("should find goalkeepers", () => {
      const players = searchPlayers({ position: "GK", limit: 10 });
      expect(players.length).toBeGreaterThan(0);
      for (const p of players) {
        expect(p.position).toBe("GK");
      }
    });
  });

  describe("Scenario: Filter by rating", () => {
    it("should find top-rated players", () => {
      const players = searchPlayers({ minOverall: 90, limit: 10 });
      expect(players.length).toBeGreaterThan(0);
      for (const p of players) {
        expect(p.overall).toBeGreaterThanOrEqual(90);
      }
    });
  });
});

describe("Statistical Analysis", () => {
  describe("Scenario: Average goals per match", () => {
    it("should calculate average goals", () => {
      const stats = getAverageGoals({});
      expect(stats.avgGoals).toBeGreaterThan(0);
      expect(stats.totalMatches).toBeGreaterThan(0);
      expect(stats.homeWinRate).toBeGreaterThan(0);
    });

    it("should calculate average goals for Brasileirão", () => {
      const stats = getAverageGoals({ competition: "Brasileirão" });
      expect(stats.avgGoals).toBeGreaterThan(0);
    });
  });

  describe("Scenario: Biggest wins", () => {
    it("should find biggest wins", () => {
      const wins = getBiggestWins({ limit: 10 });
      expect(wins.length).toBe(10);
      expect(wins[0].goalDiff).toBeGreaterThan(0);
      for (let i = 1; i < wins.length; i++) {
        expect(wins[i].goalDiff).toBeLessThanOrEqual(wins[i - 1].goalDiff);
      }
    });
  });

  describe("Scenario: Top scoring teams", () => {
    it("should find top scoring teams", () => {
      const teams = getTopScoringTeams({ limit: 10 });
      expect(teams.length).toBe(10);
      expect(teams[0].goalsScored).toBeGreaterThan(0);
      for (let i = 1; i < teams.length; i++) {
        expect(teams[i].goalsScored).toBeLessThanOrEqual(teams[i - 1].goalsScored);
      }
    });

    it("should find top scoring teams for a specific season", () => {
      const teams = getTopScoringTeams({ season: 2019, limit: 5 });
      expect(teams.length).toBeGreaterThan(0);
    });
  });
});
