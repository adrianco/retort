/*
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Test:    tests/normalize.test.ts
 * Purpose: BDD (Given/When/Then) unit tests for the normalization helpers that
 *          underpin all team-name matching, date parsing, and number parsing.
 * Notes:   These guard the trickiest correctness area: collapsing name variants
 *          while keeping genuinely-different clubs (Atlético-MG vs Athletico-PR)
 *          distinct.
 * ============================================================================
 */

import { describe, it, expect } from "vitest";
import {
  normalizeTeam,
  teamsMatch,
  parseDate,
  parseIntCell,
  stripAccents,
} from "../src/data/normalize.js";

describe("Feature: Team name normalization", () => {
  describe("Given names with state suffixes", () => {
    it("When matching 'Palmeiras-SP' against query 'Palmeiras' Then it matches", () => {
      expect(
        teamsMatch(normalizeTeam("Palmeiras-SP"), normalizeTeam("Palmeiras")),
      ).toBe(true);
    });

    it("When normalizing accented 'São Paulo' Then it matches 'Sao Paulo'", () => {
      expect(normalizeTeam("São Paulo")).toBe(normalizeTeam("Sao Paulo"));
    });

    it("When normalizing a full legal name Then it maps to the short key", () => {
      expect(normalizeTeam("Sport Club Corinthians Paulista")).toBe(
        normalizeTeam("Corinthians"),
      );
    });
  });

  describe("Given ambiguous base names", () => {
    it("When normalizing the two Atléticos Then keys differ", () => {
      expect(normalizeTeam("Atletico-MG")).not.toBe(normalizeTeam("Atletico-PR"));
    });

    it("When normalizing 'Athletico Paranaense' Then it maps to atletico#pr", () => {
      expect(normalizeTeam("Athletico Paranaense")).toBe(
        normalizeTeam("Atletico-PR"),
      );
    });
  });

  describe("Given foreign country suffixes", () => {
    it("When normalizing 'Nacional (URU)' Then the country code is dropped", () => {
      expect(normalizeTeam("Nacional (URU)")).toBe("nacional");
    });
  });

  describe("Given the fuzzy matcher", () => {
    it("When a stateless query matches a stateful key Then it succeeds", () => {
      expect(teamsMatch("flamengo#rj", normalizeTeam("Flamengo"))).toBe(true);
    });
    it("When a stateful query mismatches the state Then it fails", () => {
      expect(teamsMatch("atletico#mg", normalizeTeam("Atletico-PR"))).toBe(false);
    });
  });
});

describe("Feature: Date parsing", () => {
  describe("Given multiple date formats", () => {
    it("When parsing ISO-with-time Then it returns the date part", () => {
      expect(parseDate("2012-05-19 18:30:00")).toBe("2012-05-19");
    });
    it("When parsing Brazilian DD/MM/YYYY Then it returns ISO", () => {
      expect(parseDate("29/03/2003")).toBe("2003-03-29");
    });
    it("When parsing rubbish Then it returns null", () => {
      expect(parseDate("not a date")).toBeNull();
    });
  });
});

describe("Feature: Number parsing", () => {
  it("Given a float-formatted int '2.0' When parsing Then it returns 2", () => {
    expect(parseIntCell("2.0")).toBe(2);
  });
  it("Given a blank cell When parsing Then it returns null", () => {
    expect(parseIntCell("")).toBeNull();
  });
});

describe("Feature: Accent stripping", () => {
  it("Given 'Grêmio Avaí' When stripping Then accents are removed", () => {
    expect(stripAccents("Grêmio Avaí")).toBe("Gremio Avai");
  });
});
