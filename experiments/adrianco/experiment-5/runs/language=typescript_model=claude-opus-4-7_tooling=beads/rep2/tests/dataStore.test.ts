// Feature: Data loading from CSVs
//   Given the six provided Kaggle CSV files
//   When the DataStore is initialised
//   Then matches and players are exposed for querying.
import { describe, it, expect, beforeAll } from "vitest";
import { DataStore } from "../src/dataStore.js";

let ds: DataStore;
beforeAll(() => {
  ds = new DataStore().load();
});

describe("Feature: DataStore loads all six datasets", () => {
  it("Scenario: matches from all sources are loaded", () => {
    const sources = new Set(ds.matches.map((m) => m.source));
    expect(sources.has("Brasileirao_Matches.csv")).toBe(true);
    expect(sources.has("Brazilian_Cup_Matches.csv")).toBe(true);
    expect(sources.has("Libertadores_Matches.csv")).toBe(true);
    expect(sources.has("BR-Football-Dataset.csv")).toBe(true);
    expect(sources.has("novo_campeonato_brasileiro.csv")).toBe(true);
    expect(ds.matches.length).toBeGreaterThan(20000);
  });

  it("Scenario: FIFA player data is loaded", () => {
    expect(ds.players.length).toBeGreaterThan(15000);
    const lionel = ds.players.find((p) => p.name.includes("Messi"));
    expect(lionel).toBeDefined();
    expect(lionel!.nationality).toBe("Argentina");
  });

  it("Scenario: team names are normalized", () => {
    const fla = ds.matches.find(
      (m) => m.homeTeamNormalized === "flamengo" || m.awayTeamNormalized === "flamengo",
    );
    expect(fla).toBeDefined();
  });
});
