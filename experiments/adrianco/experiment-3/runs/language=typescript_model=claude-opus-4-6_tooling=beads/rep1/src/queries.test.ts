import { describe, it, expect, beforeAll } from "vitest";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { loadAllData } from "./data-loader.js";
import {
  searchMatches,
  getTeamStats,
  getHeadToHead,
  searchPlayers,
  getStandings,
  getStatistics,
} from "./queries.js";
import type { DataStore } from "./types.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA_DIR = resolve(__dirname, "..", "data", "kaggle");

describe("Query Engine", () => {
  let data: DataStore;

  beforeAll(() => {
    data = loadAllData(DATA_DIR);
  });

  describe("Feature: Match Queries", () => {
    describe("Scenario: Find matches between two teams", () => {
      it("should return matches between Flamengo and Fluminense", () => {
        const matches = searchMatches(data, {
          team: "Flamengo",
          opponent: "Fluminense",
        });
        expect(matches.length).toBeGreaterThan(0);
        for (const m of matches) {
          const teams = [m.homeTeam.toLowerCase(), m.awayTeam.toLowerCase()];
          expect(
            teams.some((t) => t.includes("flamengo")) &&
              teams.some((t) => t.includes("fluminense"))
          ).toBe(true);
        }
      });

      it("each match should have date, scores, and competition", () => {
        const matches = searchMatches(data, {
          team: "Flamengo",
          opponent: "Fluminense",
        });
        for (const m of matches) {
          expect(m.date).toBeTruthy();
          expect(typeof m.homeGoals).toBe("number");
          expect(typeof m.awayGoals).toBe("number");
          expect(m.competition).toBeTruthy();
        }
      });
    });

    describe("Scenario: Filter by competition", () => {
      it("should find Copa do Brasil matches", () => {
        const matches = searchMatches(data, { competition: "Copa do Brasil" });
        expect(matches.length).toBeGreaterThan(0);
        for (const m of matches) {
          expect(m.competition.toLowerCase()).toContain("copa do brasil");
        }
      });

      it("should find Libertadores matches", () => {
        const matches = searchMatches(data, { competition: "Libertadores" });
        expect(matches.length).toBeGreaterThan(0);
      });
    });

    describe("Scenario: Filter by season", () => {
      it("should return matches for a specific season", () => {
        const matches = searchMatches(data, { team: "Palmeiras", season: 2019 });
        expect(matches.length).toBeGreaterThan(0);
        for (const m of matches) {
          expect(m.season).toBe(2019);
        }
      });
    });

    describe("Scenario: Filter by date range", () => {
      it("should return matches within date range", () => {
        const matches = searchMatches(data, {
          dateFrom: "2019-01-01",
          dateTo: "2019-12-31",
        });
        expect(matches.length).toBeGreaterThan(0);
        for (const m of matches) {
          expect(m.date >= "2019-01-01").toBe(true);
          expect(m.date <= "2019-12-31").toBe(true);
        }
      });
    });

    describe("Scenario: Results are sorted by date descending", () => {
      it("most recent matches should come first", () => {
        const matches = searchMatches(data, { team: "Flamengo", limit: 10 });
        for (let i = 1; i < matches.length; i++) {
          expect(matches[i - 1].date >= matches[i].date).toBe(true);
        }
      });
    });
  });

  describe("Feature: Team Statistics", () => {
    describe("Scenario: Get team statistics", () => {
      it("should return wins, losses, draws, and goals for Palmeiras", () => {
        const stats = getTeamStats(data, "Palmeiras", { season: 2019 });
        expect(stats.matches).toBeGreaterThan(0);
        expect(stats.wins + stats.draws + stats.losses).toBe(stats.matches);
        expect(stats.goalsFor).toBeGreaterThan(0);
        expect(stats.points).toBe(stats.wins * 3 + stats.draws);
      });
    });

    describe("Scenario: Home-only statistics", () => {
      it("should only count home matches", () => {
        const homeStats = getTeamStats(data, "Corinthians", {
          season: 2018,
          homeOnly: true,
          competition: "brasileirão",
        });
        expect(homeStats.matches).toBeGreaterThan(0);
        const allStats = getTeamStats(data, "Corinthians", {
          season: 2018,
          competition: "brasileirão",
        });
        expect(homeStats.matches).toBeLessThan(allStats.matches);
      });
    });
  });

  describe("Feature: Head-to-Head Comparison", () => {
    describe("Scenario: Compare two teams", () => {
      it("should return accurate head-to-head stats", () => {
        const h2h = getHeadToHead(data, "Palmeiras", "Santos");
        expect(h2h.team1Stats.matches).toBeGreaterThan(0);
        expect(h2h.team1Stats.matches).toBe(h2h.team2Stats.matches);
        expect(h2h.team1Stats.wins + h2h.team1Stats.draws + h2h.team1Stats.losses).toBe(
          h2h.team1Stats.matches
        );
        expect(h2h.team1Stats.wins).toBe(h2h.team2Stats.losses);
        expect(h2h.team1Stats.losses).toBe(h2h.team2Stats.wins);
        expect(h2h.matches.length).toBeGreaterThan(0);
      });
    });
  });

  describe("Feature: Player Queries", () => {
    describe("Scenario: Search by name", () => {
      it("should find Gabriel Jesus", () => {
        const players = searchPlayers(data, { name: "Gabriel Jesus" });
        expect(players.length).toBeGreaterThan(0);
        expect(players[0].name.toLowerCase()).toContain("gabriel");
      });
    });

    describe("Scenario: Search by nationality", () => {
      it("should find Brazilian players", () => {
        const players = searchPlayers(data, {
          nationality: "Brazil",
          limit: 50,
        });
        expect(players.length).toBe(50);
        for (const p of players) {
          expect(p.nationality).toBe("Brazil");
        }
      });
    });

    describe("Scenario: Search by club", () => {
      it("should find players at Grêmio", () => {
        const players = searchPlayers(data, { club: "Grêmio" });
        expect(players.length).toBeGreaterThan(0);
        for (const p of players) {
          expect(p.club.toLowerCase()).toContain("grêmio");
        }
      });
    });

    describe("Scenario: Search by position", () => {
      it("should find forwards", () => {
        const players = searchPlayers(data, {
          position: "ST",
          nationality: "Brazil",
          limit: 10,
        });
        expect(players.length).toBeGreaterThan(0);
      });
    });

    describe("Scenario: Filter by minimum rating", () => {
      it("should return only high-rated players", () => {
        const players = searchPlayers(data, { minOverall: 85, limit: 50 });
        for (const p of players) {
          expect(p.overall).toBeGreaterThanOrEqual(85);
        }
      });
    });

    describe("Scenario: Sort by attribute", () => {
      it("should sort by specified field", () => {
        const players = searchPlayers(data, {
          nationality: "Brazil",
          sortBy: "overall",
          limit: 10,
        });
        for (let i = 1; i < players.length; i++) {
          expect(players[i - 1].overall).toBeGreaterThanOrEqual(players[i].overall);
        }
      });
    });
  });

  describe("Feature: Competition Standings", () => {
    describe("Scenario: Get season standings", () => {
      it("should calculate standings for 2019 Brasileirão", () => {
        const standings = getStandings(data, 2019);
        expect(standings.length).toBeGreaterThan(10);
        expect(standings[0].points).toBeGreaterThanOrEqual(standings[1].points);
      });

      it("standings should be sorted by points descending", () => {
        const standings = getStandings(data, 2018);
        for (let i = 1; i < standings.length; i++) {
          expect(standings[i - 1].points).toBeGreaterThanOrEqual(standings[i].points);
        }
      });

      it("each team should have consistent stats", () => {
        const standings = getStandings(data, 2019);
        for (const s of standings) {
          expect(s.wins + s.draws + s.losses).toBe(s.matches);
          expect(s.points).toBe(s.wins * 3 + s.draws);
        }
      });
    });
  });

  describe("Feature: Statistical Analysis", () => {
    describe("Scenario: Get aggregate statistics", () => {
      it("should calculate average goals per match", () => {
        const stats = getStatistics(data, { competition: "brasileirão" });
        expect(stats.avgGoalsPerMatch).toBeGreaterThan(1);
        expect(stats.avgGoalsPerMatch).toBeLessThan(5);
      });

      it("should calculate home/away win rates that sum to ~100%", () => {
        const stats = getStatistics(data);
        const total = stats.homeWinRate + stats.awayWinRate + stats.drawRate;
        expect(total).toBeGreaterThan(99);
        expect(total).toBeLessThan(101);
      });

      it("should return biggest wins", () => {
        const stats = getStatistics(data);
        expect(stats.biggestWins.length).toBeGreaterThan(0);
        const goalDiffs = stats.biggestWins.map((m) =>
          Math.abs(m.homeGoals - m.awayGoals)
        );
        for (let i = 1; i < goalDiffs.length; i++) {
          expect(goalDiffs[i - 1]).toBeGreaterThanOrEqual(goalDiffs[i]);
        }
      });
    });

    describe("Scenario: Filter statistics by season", () => {
      it("should return stats for a single season", () => {
        const stats = getStatistics(data, {
          competition: "brasileirão",
          season: 2019,
        });
        expect(stats.totalMatches).toBeGreaterThan(100);
        expect(stats.totalMatches).toBeLessThan(1000);
      });
    });
  });

  describe("Feature: Cross-file queries", () => {
    it("should find a player and their team's matches", () => {
      const players = searchPlayers(data, { name: "Neymar" });
      expect(players.length).toBeGreaterThan(0);
      const matches = searchMatches(data, { team: "Santos", season: 2012 });
      expect(matches.length).toBeGreaterThan(0);
    });
  });
});
