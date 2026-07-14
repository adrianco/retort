import { describe, expect, it } from "vitest";
import { getDataset } from "../src/dataLoader.js";
import { averageGoals, bestVenueRecord, biggestWins } from "../src/queries/statsQueries.js";

const dataset = getDataset();

describe("averageGoals", () => {
  it("computes a plausible average and outcome rates that sum to ~100%", () => {
    const result = averageGoals(dataset, { competition: "Brasileirao" });
    expect(result.matches).toBeGreaterThan(0);
    expect(result.averageGoalsPerMatch).toBeGreaterThan(1.5);
    expect(result.averageGoalsPerMatch).toBeLessThan(4);
    const sum = result.homeWinRatePct + result.drawRatePct + result.awayWinRatePct;
    expect(sum).toBeCloseTo(100, 5);
  });

  it("scopes to a single season", () => {
    const result = averageGoals(dataset, { competition: "Brasileirao", season: 2019 });
    expect(result.matches).toBe(380);
  });
});

describe("biggestWins", () => {
  it("returns wins sorted by descending goal margin", () => {
    const results = biggestWins(dataset, { limit: 10 });
    expect(results.length).toBe(10);
    for (let i = 1; i < results.length; i++) {
      expect(results[i - 1].goalDifference).toBeGreaterThanOrEqual(results[i].goalDifference);
    }
    expect(results[0].goalDifference).toBeGreaterThan(0);
  });
});

describe("bestVenueRecord", () => {
  it("ranks teams by home win rate, excluding small samples", () => {
    const rows = bestVenueRecord(dataset, "home", { competition: "Brasileirao", season: 2022, minMatches: 5 });
    expect(rows.length).toBeGreaterThan(0);
    for (const row of rows) {
      expect(row.played).toBeGreaterThanOrEqual(5);
    }
    for (let i = 1; i < rows.length; i++) {
      expect(rows[i - 1].winRatePct).toBeGreaterThanOrEqual(rows[i].winRatePct);
    }
  });
});
