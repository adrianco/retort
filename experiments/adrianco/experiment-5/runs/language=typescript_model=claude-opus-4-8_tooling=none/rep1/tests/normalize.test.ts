/**
 * Context
 * -------
 * Feature: Team-name & date normalization.
 * Verifies the data-quality rules called out in the spec — state/country
 * suffix stripping, accent-insensitive matching, club-type tokens, and the
 * multiple date formats — using Given/When/Then structure.
 */

import { describe, it, expect } from "vitest";
import {
  canonicalKey,
  normalizeDate,
  normalizeTeamName,
  teamMatches,
} from "../src/normalize.js";

describe("Feature: Team name normalization", () => {
  it("Scenario: strips attached state suffixes (Palmeiras-SP)", () => {
    // When a name has a "-SP" style suffix
    const result = normalizeTeamName("Palmeiras-SP");
    // Then the suffix is removed
    expect(result).toBe("Palmeiras");
  });

  it("Scenario: strips spaced dash suffixes (América - MG)", () => {
    expect(normalizeTeamName("América - MG")).toBe("América");
  });

  it("Scenario: strips country codes (Nacional (URU))", () => {
    expect(normalizeTeamName("Nacional (URU)")).toBe("Nacional");
  });

  it("Scenario: strips standalone trailing state codes (Botafogo RJ)", () => {
    expect(normalizeTeamName("Botafogo RJ")).toBe("Botafogo");
  });

  it("Scenario: drops club-type tokens (São Paulo FC, EC Bahia)", () => {
    expect(normalizeTeamName("São Paulo FC")).toBe("São Paulo");
    expect(normalizeTeamName("EC Bahia")).toBe("Bahia");
  });

  it("Scenario: matches names accent-insensitively across spellings", () => {
    // Given two spellings of the same club
    // Then they share a canonical key and match each other
    expect(canonicalKey("São Paulo")).toBe(canonicalKey("Sao Paulo"));
    expect(teamMatches("Grêmio-RS", "gremio")).toBe(true);
    expect(teamMatches("Flamengo-RJ", "Flamengo")).toBe(true);
  });

  it("Scenario: distinguishes Athletico-PR from Atlético-MG", () => {
    expect(canonicalKey("Athletico Paranaense")).toBe(canonicalKey("Athletico-PR"));
    expect(canonicalKey("Atletico Mineiro")).toBe(canonicalKey("Atlético-MG"));
    expect(canonicalKey("Athletico-PR")).not.toBe(canonicalKey("Atlético-MG"));
  });
});

describe("Feature: Date normalization", () => {
  it("Scenario: parses ISO datetime", () => {
    expect(normalizeDate("2012-05-19 18:30:00")).toBe("2012-05-19");
  });
  it("Scenario: parses plain ISO date", () => {
    expect(normalizeDate("2023-09-24")).toBe("2023-09-24");
  });
  it("Scenario: parses Brazilian DD/MM/YYYY", () => {
    expect(normalizeDate("29/03/2003")).toBe("2003-03-29");
  });
  it("Scenario: returns null for blank or NA", () => {
    expect(normalizeDate("NA")).toBeNull();
    expect(normalizeDate("")).toBeNull();
  });
});
