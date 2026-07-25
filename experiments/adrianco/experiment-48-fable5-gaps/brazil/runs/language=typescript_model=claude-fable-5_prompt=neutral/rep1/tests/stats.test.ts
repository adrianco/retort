/**
 * Feature: Team statistics, standings and analytics
 */
import { describe, expect, it } from "vitest";
import {
  bestRecords,
  biggestWins,
  competitionStats,
  standings,
  teamCompetitions,
  teamStats,
} from "../src/queries.js";
import { dataset } from "./helpers.js";

describe("Feature: Team statistics", () => {
  describe("Scenario: Get team statistics for a season", () => {
    it("Given the match data is loaded, When I request statistics for 'Palmeiras' in season 2023, Then I receive wins, losses, draws and goals that are consistent", () => {
      const s = teamStats(dataset(), "Palmeiras", { season: 2023 });
      expect(s.matches).toBeGreaterThan(30);
      expect(s.wins + s.draws + s.losses).toBe(s.matches);
      expect(s.goalsFor).toBeGreaterThan(0);
      expect(s.goalsAgainst).toBeGreaterThan(0);
      expect(s.winRate).toBeGreaterThan(0);
      expect(s.winRate).toBeLessThanOrEqual(1);
    });
  });

  describe("Scenario: Home record for a team and season", () => {
    it("Given Corinthians in the 2022 Brasileirão, When I request the home record, Then there are 19 home matches (one against each opponent)", () => {
      const s = teamStats(dataset(), "Corinthians", {
        season: 2022,
        competition: "Brasileirão",
        venue: "home",
      });
      expect(s.matches).toBe(19);
      expect(s.wins + s.draws + s.losses).toBe(19);
    });
  });

  describe("Scenario: Competitions a team has played in", () => {
    it("Given Palmeiras, When I ask which competitions it played, Then Série A, Copa do Brasil and Libertadores all appear", () => {
      const comps = teamCompetitions(dataset(), "Palmeiras").map((c) => c.competition);
      expect(comps).toContain("Brasileirão Série A");
      expect(comps).toContain("Copa do Brasil");
      expect(comps).toContain("Copa Libertadores");
    });
  });
});

describe("Feature: Competition queries", () => {
  describe("Scenario: Who won the 2019 Brasileirão?", () => {
    it("Given the 2019 season, When standings are computed from match results, Then Flamengo is champion with 90 points", () => {
      const table = standings(dataset(), 2019);
      expect(table.length).toBe(20);
      expect(table[0].team.toLowerCase()).toContain("flamengo");
      expect(table[0].points).toBe(90);
      expect(table[0].played).toBe(38);
    });

    it("Then the relegation zone contains the four teams actually relegated in 2019", () => {
      const bottom = standings(dataset(), 2019)
        .slice(-4)
        .map((r) => r.team.toLowerCase());
      expect(bottom.join("|")).toContain("cruzeiro");
      expect(bottom.join("|")).toContain("csa");
      expect(bottom.join("|")).toContain("chapecoense");
      expect(bottom.join("|")).toContain("avai");
    });
  });

  describe("Scenario: Historical season standings", () => {
    it("Given the 2003 season (from the DD/MM/YYYY historical file), When standings are computed, Then Cruzeiro is champion with 100 points", () => {
      const table = standings(dataset(), 2003);
      expect(table[0].team.toLowerCase()).toContain("cruzeiro");
      expect(table[0].points).toBe(100);
    });

    it("Given the 2015 season, When standings are computed, Then Corinthians is champion", () => {
      const table = standings(dataset(), 2015);
      expect(table[0].team.toLowerCase()).toContain("corinthians");
      expect(table[0].points).toBe(81);
    });
  });

  describe("Scenario: Série B standings from the extended dataset", () => {
    it("Given the 2022 Série B season, When standings are computed, Then Cruzeiro is champion", () => {
      const table = standings(dataset(), 2022, "Serie B");
      expect(table.length).toBeGreaterThanOrEqual(20);
      expect(table[0].team.toLowerCase()).toContain("cruzeiro");
    });
  });

  describe("Scenario: Every standings row is internally consistent", () => {
    it("Given any season table, Then P = W+D+L and Pts = 3W+D for every row", () => {
      for (const season of [2012, 2019, 2023]) {
        for (const r of standings(dataset(), season)) {
          expect(r.wins + r.draws + r.losses).toBe(r.played);
          expect(r.points).toBe(3 * r.wins + r.draws);
        }
      }
    });
  });
});

describe("Feature: Statistical analysis", () => {
  describe("Scenario: Average goals per match", () => {
    it("Given all Brasileirão matches, When averaged, Then goals per match is a plausible 2–3", () => {
      const s = competitionStats(dataset(), { competition: "Brasileirão" });
      expect(s.matches).toBeGreaterThan(7000);
      expect(s.avgGoalsPerMatch).toBeGreaterThan(2);
      expect(s.avgGoalsPerMatch).toBeLessThan(3);
    });

    it("Then home wins + away wins + draws equals total matches", () => {
      const s = competitionStats(dataset(), {});
      expect(s.homeWins + s.awayWins + s.draws).toBe(s.matches);
      expect(s.homeWinRate).toBeGreaterThan(0.4); // home advantage is real in Brazil
    });
  });

  describe("Scenario: Biggest wins", () => {
    it("Given the whole dataset, When I ask for the biggest wins, Then results are sorted by goal margin descending", () => {
      const wins = biggestWins(dataset(), { limit: 10 });
      expect(wins.length).toBe(10);
      const margins = wins.map((m) => Math.abs(m.homeGoals - m.awayGoals));
      for (let i = 1; i < margins.length; i++) {
        expect(margins[i]).toBeLessThanOrEqual(margins[i - 1]);
      }
      expect(margins[0]).toBeGreaterThanOrEqual(6);
    });
  });

  describe("Scenario: Best home record", () => {
    it("Given a season, When teams are ranked by home win rate, Then rates are within [0,1] and sorted descending", () => {
      const rows = bestRecords(dataset(), { venue: "home", season: 2019, competition: "Serie A", minMatches: 15 });
      expect(rows.length).toBeGreaterThan(3);
      for (let i = 1; i < rows.length; i++) {
        expect(rows[i].winRate).toBeLessThanOrEqual(rows[i - 1].winRate);
      }
      for (const r of rows) {
        expect(r.winRate).toBeGreaterThanOrEqual(0);
        expect(r.winRate).toBeLessThanOrEqual(1);
      }
    });
  });
});
