/**
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Feature: Data normalization (team names & dates)
 * Verifies the "Data Quality Notes" requirements in TASK.md: state-suffix
 * stripping, accent-insensitive matching, full-name handling and multiple
 * date formats.
 * ============================================================================
 */

import { describe, it, expect } from "vitest";
import {
  normalizeTeamKey,
  displayTeamName,
  teamMatches,
  parseDate,
} from "../src/data/normalize.js";

describe("Feature: Team name normalization", () => {
  it("Scenario: strips Brazilian state suffixes", () => {
    // Given names that carry a state suffix
    // When normalized
    // Then the suffix is removed and the key matches the bare name
    expect(normalizeTeamKey("Palmeiras-SP")).toBe(normalizeTeamKey("Palmeiras"));
    expect(displayTeamName("Flamengo-RJ")).toBe("Flamengo");
    expect(normalizeTeamKey("América - MG")).toBe(normalizeTeamKey("América"));
  });

  it("Scenario: strips parenthesized country suffixes (Libertadores)", () => {
    expect(displayTeamName("Nacional (URU)")).toBe("Nacional");
    expect(normalizeTeamKey("Barcelona-EQU")).toBe(normalizeTeamKey("Barcelona"));
  });

  it("Scenario: is accent-insensitive", () => {
    // Given an accented and an unaccented spelling
    // Then they normalize to the same key
    expect(normalizeTeamKey("São Paulo")).toBe(normalizeTeamKey("Sao Paulo"));
    expect(normalizeTeamKey("Grêmio")).toBe(normalizeTeamKey("Gremio"));
  });

  it("Scenario: matches a bare query against a suffixed team key", () => {
    const key = normalizeTeamKey("Flamengo-RJ");
    expect(teamMatches("Flamengo", key)).toBe(true);
    expect(teamMatches("Fluminense", key)).toBe(false);
  });

  it("Scenario: keeps distinct clubs apart", () => {
    const saoPaulo = normalizeTeamKey("São Paulo");
    expect(teamMatches("São Caetano", saoPaulo)).toBe(false);
  });
});

describe("Feature: Date parsing", () => {
  it("Scenario: parses ISO dates with and without time", () => {
    expect(parseDate("2023-09-24")?.toISOString().slice(0, 10)).toBe("2023-09-24");
    expect(parseDate("2012-05-19 18:30:00")?.toISOString().slice(0, 10)).toBe(
      "2012-05-19"
    );
  });

  it("Scenario: parses Brazilian DD/MM/YYYY dates", () => {
    expect(parseDate("29/03/2003")?.toISOString().slice(0, 10)).toBe("2003-03-29");
  });

  it("Scenario: returns null for empty or NA values", () => {
    expect(parseDate("")).toBeNull();
    expect(parseDate("NA")).toBeNull();
    expect(parseDate(undefined)).toBeNull();
  });
});
