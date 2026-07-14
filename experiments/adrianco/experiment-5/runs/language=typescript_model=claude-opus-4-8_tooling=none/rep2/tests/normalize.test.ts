/**
 * ============================================================================
 * File: tests/normalize.test.ts
 * Feature: Data normalization (team names, dates, numbers)
 * ----------------------------------------------------------------------------
 * Context:
 *   Unit-level Given/When/Then scenarios for the normalization layer that
 *   absorbs the data-quality issues described in the specification: team name
 *   variations, multiple date formats and UTF-8 accents.
 * ============================================================================
 */

import { describe, it, expect } from "vitest";
import {
  parseDate,
  parseNumber,
  stripAccents,
  teamDisplayName,
  teamKey,
} from "../src/normalize.js";

describe("Feature: Team name normalization", () => {
  it("Scenario: strips a hyphenated state suffix", () => {
    // Given a team name with a state suffix
    // When normalized
    // Then the suffix is removed
    expect(teamDisplayName("Palmeiras-SP")).toBe("Palmeiras");
    expect(teamKey("Palmeiras-SP")).toBe(teamKey("Palmeiras"));
  });

  it("Scenario: strips a spaced hyphen state suffix", () => {
    expect(teamDisplayName("América - MG")).toBe("América");
  });

  it("Scenario: strips a parenthetical country tag", () => {
    expect(teamDisplayName("Nacional (URU)")).toBe("Nacional");
  });

  it("Scenario: matches names regardless of accents", () => {
    // Given two spellings differing only by accents
    // Then they share a normalized key
    expect(teamKey("São Paulo")).toBe(teamKey("Sao Paulo"));
    expect(teamKey("Grêmio")).toBe(teamKey("Gremio"));
  });

  it("Scenario: keeps distinct clubs that share a base name", () => {
    // Atlético-MG and Atlético-GO are different clubs
    expect(teamKey("Atlético-MG")).not.toBe(teamKey("Atlético-GO"));
  });

  it("Scenario: unifies Athletico Paranaense spellings", () => {
    expect(teamKey("Athletico-PR")).toBe(teamKey("Atletico-PR"));
  });
});

describe("Feature: Date parsing", () => {
  it("Scenario: parses ISO datetime", () => {
    expect(parseDate("2012-05-19 18:30:00")).toBe("2012-05-19");
  });
  it("Scenario: parses ISO date", () => {
    expect(parseDate("2023-09-24")).toBe("2023-09-24");
  });
  it("Scenario: parses Brazilian DD/MM/YYYY", () => {
    expect(parseDate("29/03/2003")).toBe("2003-03-29");
  });
  it("Scenario: returns null for empty/garbage", () => {
    expect(parseDate("")).toBeNull();
    expect(parseDate(undefined)).toBeNull();
  });
});

describe("Feature: Numeric parsing", () => {
  it("Scenario: parses quoted and float-formatted goals", () => {
    expect(parseNumber('"2"')).toBe(2);
    expect(parseNumber("1.0")).toBe(1);
    expect(parseNumber("")).toBeNull();
  });
});

describe("Feature: Accent stripping", () => {
  it("Scenario: removes diacritics", () => {
    expect(stripAccents("Avaí")).toBe("Avai");
    expect(stripAccents("Fortaleza")).toBe("Fortaleza");
  });
});
