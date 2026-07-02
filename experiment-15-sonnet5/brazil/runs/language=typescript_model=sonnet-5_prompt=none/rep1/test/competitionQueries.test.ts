import { describe, expect, it } from "vitest";
import { getDataset } from "../src/dataLoader.js";
import { listCompetitions, standings } from "../src/queries/competitionQueries.js";

const dataset = getDataset();

describe("standings", () => {
  it("computes a full Brasileirao 2019 table with correct point totals", () => {
    const result = standings(dataset, "Brasileirao", 2019);
    // 20-team single round-robin: 380 matches, each team plays 38
    expect(result.matchesUsed).toBe(380);
    expect(result.table.length).toBe(20);
    for (const row of result.table) {
      expect(row.played).toBe(38);
      expect(row.points).toBe(row.wins * 3 + row.draws);
      expect(row.goalDifference).toBe(row.goalsFor - row.goalsAgainst);
    }
    // Flamengo won the 2019 Brasileirao
    expect(result.table[0].team).toContain("Flamengo");
    // Table should be sorted descending by points
    for (let i = 1; i < result.table.length; i++) {
      expect(result.table[i - 1].points).toBeGreaterThanOrEqual(result.table[i].points);
    }
  });

  it("returns an empty table for a season/competition with no data", () => {
    const result = standings(dataset, "Brasileirao", 1899);
    expect(result.table.length).toBe(0);
    expect(result.matchesUsed).toBe(0);
  });
});

describe("listCompetitions", () => {
  it("lists all five underlying data sources", () => {
    const infos = listCompetitions(dataset);
    const sources = new Set(infos.map((c) => c.source));
    expect(sources.has("Brasileirao")).toBe(true);
    expect(sources.has("Copa do Brasil")).toBe(true);
    expect(sources.has("Libertadores")).toBe(true);
    expect(sources.has("BR-Football")).toBe(true);
    expect(sources.has("Historical-Brasileirao")).toBe(true);
  });
});
