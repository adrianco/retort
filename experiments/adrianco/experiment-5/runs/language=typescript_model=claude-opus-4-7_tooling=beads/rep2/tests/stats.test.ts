// Feature: Aggregate statistical analysis
import { describe, it, expect, beforeAll } from "vitest";
import { DataStore } from "../src/dataStore.js";
import { aggregateStats, biggestWins, topScoringTeams, bestRecord } from "../src/queries/stats.js";

let ds: DataStore;
beforeAll(() => {
  ds = new DataStore().load();
});

describe("Feature: Aggregate statistics", () => {
  describe("Scenario: average goals and home win rate", () => {
    it("Given Brasileirão matches, When computing aggregate stats, Then averages are in plausible football ranges", () => {
      const s = aggregateStats(ds.matches, { competition: "Brasileirão" });
      expect(s.matches).toBeGreaterThan(0);
      expect(s.averageGoalsPerMatch).toBeGreaterThan(1);
      expect(s.averageGoalsPerMatch).toBeLessThan(5);
      expect(s.homeWinRate).toBeGreaterThan(0.3);
      expect(s.homeWinRate).toBeLessThan(0.7);
      expect(s.homeWinRate + s.awayWinRate + s.drawRate).toBeCloseTo(1, 5);
    });
  });

  describe("Scenario: biggest wins are sorted by margin", () => {
    it("Given matches with results, When asking biggest wins, Then margins are non-increasing", () => {
      const wins = biggestWins(ds.matches, { limit: 5 });
      expect(wins.length).toBe(5);
      let prev = Infinity;
      for (const m of wins) {
        const margin = Math.abs((m.homeGoal ?? 0) - (m.awayGoal ?? 0));
        expect(margin).toBeLessThanOrEqual(prev);
        prev = margin;
      }
    });
  });

  describe("Scenario: top scoring teams", () => {
    it("Given the data, When asking top scoring teams in Brasileirão 2019, Then top team has > 50 goals", () => {
      const rows = topScoringTeams(ds.matches, { competition: "Brasileirão", season: 2019, limit: 5 });
      expect(rows.length).toBe(5);
      expect(rows[0].goalsFor).toBeGreaterThan(50);
    });
  });

  describe("Scenario: best home record", () => {
    it("Given Brasileirão 2019, When asking for best home record, Then results are sorted by win rate", () => {
      const rows = bestRecord(ds.matches, "home", {
        competition: "Brasileirão", season: 2019, minMatches: 10, limit: 5,
      });
      expect(rows.length).toBe(5);
      for (let i = 1; i < rows.length; i++) {
        expect(rows[i].winRate).toBeLessThanOrEqual(rows[i - 1].winRate);
      }
    });
  });
});
