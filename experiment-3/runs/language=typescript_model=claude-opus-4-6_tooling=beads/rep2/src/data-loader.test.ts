import { describe, it, expect } from "vitest";
import { loadAllData, getDataStats } from "./data-loader.js";

describe("Data Loading", () => {
  describe("Given all CSV files are present", () => {
    it("should load all match data without errors", () => {
      const data = loadAllData();
      expect(data.matches.length).toBeGreaterThan(0);
    });

    it("should load all player data without errors", () => {
      const data = loadAllData();
      expect(data.players.length).toBeGreaterThan(0);
    });

    it("should load matches from multiple competitions", () => {
      const data = loadAllData();
      const competitions = new Set(data.matches.map((m) => m.competition));
      expect(competitions.has("Brasileirão")).toBe(true);
      expect(competitions.has("Copa do Brasil")).toBe(true);
      expect(competitions.has("Copa Libertadores")).toBe(true);
    });
  });

  describe("Data statistics", () => {
    it("should report correct dataset counts", () => {
      const stats = getDataStats();
      expect(stats.brasileirao).toBeGreaterThan(4000);
      expect(stats.cup).toBeGreaterThan(1000);
      expect(stats.libertadores).toBeGreaterThan(1000);
      expect(stats.extended).toBeGreaterThan(10000);
      expect(stats.historical).toBeGreaterThan(6000);
      expect(stats.players).toBeGreaterThan(18000);
    });

    it("should have non-zero total matches", () => {
      const stats = getDataStats();
      expect(stats.totalMatches).toBeGreaterThan(20000);
    });
  });

  describe("Data quality", () => {
    it("should have valid dates in matches", () => {
      const data = loadAllData();
      const sample = data.matches.slice(0, 100);
      for (const m of sample) {
        expect(m.datetime).toBeTruthy();
      }
    });

    it("should have valid team names in matches", () => {
      const data = loadAllData();
      const sample = data.matches.slice(0, 100);
      for (const m of sample) {
        expect(m.homeTeam).toBeTruthy();
        expect(m.awayTeam).toBeTruthy();
      }
    });

    it("should have non-negative goal counts", () => {
      const data = loadAllData();
      const sample = data.matches.slice(0, 100);
      for (const m of sample) {
        expect(m.homeGoal).toBeGreaterThanOrEqual(0);
        expect(m.awayGoal).toBeGreaterThanOrEqual(0);
      }
    });

    it("should have player names and ratings", () => {
      const data = loadAllData();
      const sample = data.players.slice(0, 100);
      for (const p of sample) {
        expect(p.name).toBeTruthy();
        expect(p.overall).toBeGreaterThan(0);
      }
    });
  });
});
