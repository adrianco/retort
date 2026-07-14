/**
 * tests/stats.test.ts
 * -----------------------------------------------------------------------------
 * CONTEXT
 *   BDD specs for the statistics service: average goals, home/draw/away rates,
 *   biggest wins, and team rankings (best home/away record).
 * -----------------------------------------------------------------------------
 */

import { describe, it, expect } from "vitest";
import { givenDataset } from "./fixture.js";
import { aggregateStats, biggestWins, bestRecords } from "../src/services/stats.js";

describe("Feature: Statistical Analysis", () => {
  describe("Scenario: Average goals per match", () => {
    it("Given the Brasileirão, Then the average is a realistic football figure", () => {
      const ds = givenDataset();
      const s = aggregateStats(ds, { competition: "Brasileirão" });
      expect(s.matchesWithScores).toBeGreaterThan(1000);
      expect(s.averageGoalsPerMatch).toBeGreaterThan(2);
      expect(s.averageGoalsPerMatch).toBeLessThan(3.5);
    });

    it("Given outcome rates, Then home + draw + away rates sum to 1", () => {
      const ds = givenDataset();
      const s = aggregateStats(ds, { competition: "Brasileirão" });
      expect(s.homeWinRate + s.drawRate + s.awayWinRate).toBeCloseTo(1, 6);
      // Home advantage: home win rate exceeds away win rate.
      expect(s.homeWinRate).toBeGreaterThan(s.awayWinRate);
    });
  });

  describe("Scenario: Biggest wins", () => {
    it("Given the dataset, Then wins are ranked by margin descending", () => {
      const ds = givenDataset();
      const wins = biggestWins(ds, {}, 10);
      expect(wins.length).toBe(10);
      for (let i = 1; i < wins.length; i++) {
        expect(wins[i - 1].margin).toBeGreaterThanOrEqual(wins[i].margin);
      }
      expect(wins[0].margin).toBeGreaterThanOrEqual(5);
    });
  });

  describe("Scenario: Best home record", () => {
    it("Given the 2019 Brasileirão, Then the best home record belongs to the champions", () => {
      const ds = givenDataset();
      const ranked = bestRecords(ds, {
        competition: "Brasileirão",
        season: 2019,
        venue: "home",
        metric: "winRate",
        limit: 5,
      });
      expect(ranked.length).toBe(5);
      // Flamengo were dominant at home in 2019.
      expect(ranked[0].team).toBe("Flamengo");
      for (let i = 1; i < ranked.length; i++) {
        expect(ranked[i - 1].winRate).toBeGreaterThanOrEqual(ranked[i].winRate);
      }
    });
  });
});
