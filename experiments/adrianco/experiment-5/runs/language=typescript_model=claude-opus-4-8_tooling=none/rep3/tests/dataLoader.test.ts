/**
 * ============================================================================
 * Context: BDD tests — Data Loading
 * ----------------------------------------------------------------------------
 * Feature : The server loads all six provided CSV files into a unified model.
 *           Written Given/When/Then to mirror the spec's BDD testing approach.
 * ============================================================================
 */

import { describe, it, expect, beforeAll } from "vitest";
import { loadDataset, type Dataset } from "../src/dataLoader.js";
import { parseDate, cleanTeamName, normalizeKey } from "../src/normalize.js";

describe("Feature: Data loading", () => {
  let data: Dataset;
  beforeAll(() => {
    // Given the CSV corpus on disk
    data = loadDataset();
  });

  it("Scenario: all six datasets load into the unified match/player model", () => {
    // When the dataset is loaded
    // Then matches from every source file are present
    const sources = new Set(data.matches.map((m) => m.source));
    expect(sources).toContain("Brasileirao_Matches.csv");
    expect(sources).toContain("Brazilian_Cup_Matches.csv");
    expect(sources).toContain("Libertadores_Matches.csv");
    expect(sources).toContain("BR-Football-Dataset.csv");
    expect(sources).toContain("novo_campeonato_brasileiro.csv");
    // And a large number of matches and players are available
    expect(data.matches.length).toBeGreaterThan(20000);
    expect(data.players.length).toBeGreaterThan(18000);
  });

  it("Scenario: competitions are normalized to canonical names", () => {
    // Then known canonical competitions appear
    expect(data.competitions).toContain("Brasileirão Série A");
    expect(data.competitions).toContain("Copa do Brasil");
    expect(data.competitions).toContain("Copa Libertadores");
  });

  it("Scenario: every match record has clean teams and parsed fields", () => {
    // Then no team name retains a raw state suffix and dates are ISO
    const sample = data.matches.slice(0, 500);
    for (const m of sample) {
      expect(m.homeTeam).not.toMatch(/-[A-Z]{2,3}$/);
      if (m.date) expect(m.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    }
  });
});

describe("Feature: Value normalization", () => {
  it("Scenario: team name variations normalize to the same key", () => {
    // Given several spellings of the same club
    // Then they share a canonical key
    expect(normalizeKey("Palmeiras-SP")).toBe(normalizeKey("Palmeiras"));
    expect(normalizeKey("São Paulo")).toBe(normalizeKey("Sao Paulo"));
    expect(normalizeKey("Grêmio")).toBe(normalizeKey("Gremio"));
    expect(cleanTeamName("Nacional (URU)")).toBe("Nacional");
  });

  it("Scenario: multiple date formats parse to ISO", () => {
    expect(parseDate("2012-05-19 18:30:00")).toBe("2012-05-19");
    expect(parseDate("2023-09-24")).toBe("2023-09-24");
    expect(parseDate("29/03/2003")).toBe("2003-03-29");
    expect(parseDate("NA")).toBeNull();
    expect(parseDate("")).toBeNull();
  });
});
