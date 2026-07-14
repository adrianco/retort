/**
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Feature: Data loading & coverage
 * Verifies the "Data Coverage" success criteria in TASK.md: all six CSV files
 * load, every competition is represented, and players are present with UTF-8
 * preserved.
 * ============================================================================
 */

import { describe, it, expect } from "vitest";
import { dataset } from "./helpers.js";

describe("Feature: Dataset loading", () => {
  it("Scenario: all match files are loaded and queryable", () => {
    const ds = dataset();
    // Given the bundled CSVs
    // Then a substantial number of matches are loaded
    expect(ds.matches.length).toBeGreaterThan(20000);

    // And every canonical competition is represented
    const comps = new Set(ds.matches.map((m) => m.competition));
    expect(comps.has("Brasileirão Série A")).toBe(true);
    expect(comps.has("Copa do Brasil")).toBe(true);
    expect(comps.has("Copa Libertadores")).toBe(true);
  });

  it("Scenario: every source file contributes records", () => {
    const ds = dataset();
    const sources = new Set(ds.matches.map((m) => m.source));
    expect(sources).toContain("Brasileirao_Matches.csv");
    expect(sources).toContain("Brazilian_Cup_Matches.csv");
    expect(sources).toContain("Libertadores_Matches.csv");
    expect(sources).toContain("BR-Football-Dataset.csv");
    expect(sources).toContain("novo_campeonato_brasileiro.csv");
  });

  it("Scenario: player data loads with UTF-8 preserved", () => {
    const ds = dataset();
    expect(ds.players.length).toBeGreaterThan(18000);
    // And Brazilian players are present
    const brazilians = ds.players.filter((p) => p.nationality === "Brazil");
    expect(brazilians.length).toBeGreaterThan(500);
  });

  it("Scenario: matches carry parsed dates and normalized keys", () => {
    const ds = dataset();
    const withDate = ds.matches.filter((m) => m.date != null);
    expect(withDate.length).toBeGreaterThan(20000);
    expect(ds.matches.every((m) => m.homeKey.length > 0)).toBe(true);
  });
});
