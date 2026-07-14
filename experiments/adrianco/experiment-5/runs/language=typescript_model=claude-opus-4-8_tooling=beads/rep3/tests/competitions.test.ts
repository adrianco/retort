/*
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Test:    tests/competitions.test.ts
 * Purpose: BDD tests for standings, competition summaries, and aggregate
 *          statistics (features/competitions.feature).
 * ============================================================================
 */

import { describe, it, expect } from "vitest";
import { givenDataLoaded } from "./helpers.js";
import { standings, competitionSummary } from "../src/queries/competitions.js";
import {
  aggregateStats,
  biggestWins,
  topScoringTeams,
  bestVenueRecords,
} from "../src/queries/statistics.js";

const ds = givenDataLoaded();

describe("Feature: Competition Queries", () => {
  describe("Scenario: Compute final standings for a season", () => {
    const table = standings(ds, "Brasileirão Série A", 2019);

    it("Then the table has 20 teams", () => {
      expect(table).toHaveLength(20);
    });

    it("And the champion is Flamengo with 90 points", () => {
      expect(table[0].team).toBe("Flamengo");
      expect(table[0].points).toBe(90);
      expect(table[0].position).toBe(1);
    });

    it("And every team played 38 matches", () => {
      for (const r of table) expect(r.played).toBe(38);
    });

    it("And the table is sorted by points descending", () => {
      for (let i = 1; i < table.length; i++) {
        expect(table[i - 1].points).toBeGreaterThanOrEqual(table[i].points);
      }
    });
  });

  describe("Scenario: Determine relegated teams", () => {
    const sum = competitionSummary(ds, "Brasileirão Série A", 2019);

    it("Then the relegated teams include Cruzeiro", () => {
      expect(sum.relegated).toContain("Cruzeiro");
    });

    it("And there are exactly 4 relegated teams", () => {
      expect(sum.relegated).toHaveLength(4);
    });
  });
});

describe("Feature: Statistical Analysis", () => {
  describe("Scenario: Aggregate goal statistics", () => {
    const a = aggregateStats(ds, { competition: "Brasileirão Série A" });

    it("Then average goals per match is between 2 and 3", () => {
      expect(a.avgGoalsPerMatch).toBeGreaterThan(2);
      expect(a.avgGoalsPerMatch).toBeLessThan(3);
    });

    it("And home win rate exceeds away win rate (home advantage)", () => {
      expect(a.homeWinRate).toBeGreaterThan(a.awayWinRate);
    });

    it("And the three outcome rates sum to ~1", () => {
      expect(a.homeWinRate + a.awayWinRate + a.drawRate).toBeCloseTo(1, 5);
    });
  });

  describe("Scenario: Biggest victories", () => {
    const wins = biggestWins(ds, {}, 10);

    it("Then the first result has the largest margin", () => {
      expect(wins.length).toBe(10);
      for (let i = 1; i < wins.length; i++) {
        expect(wins[i - 1].margin).toBeGreaterThanOrEqual(wins[i].margin);
      }
    });
  });

  describe("Scenario: Top scoring teams in a season", () => {
    const ranks = topScoringTeams(
      ds,
      { competition: "Brasileirão Série A", season: 2019 },
      5,
    );

    it("Then teams are ranked by goals scored (descending)", () => {
      expect(ranks.length).toBe(5);
      for (let i = 1; i < ranks.length; i++) {
        expect(ranks[i - 1].goalsFor).toBeGreaterThanOrEqual(ranks[i].goalsFor);
      }
    });
  });

  describe("Scenario: Best home record", () => {
    const recs = bestVenueRecords(ds, "home", {
      competition: "Brasileirão Série A",
      season: 2019,
    });

    it("Then teams are ranked by win rate and meet the match threshold", () => {
      expect(recs.length).toBeGreaterThan(0);
      for (const r of recs) expect(r.played).toBeGreaterThanOrEqual(5);
      for (let i = 1; i < recs.length; i++) {
        expect(recs[i - 1].winRate).toBeGreaterThanOrEqual(recs[i].winRate);
      }
    });
  });
});
