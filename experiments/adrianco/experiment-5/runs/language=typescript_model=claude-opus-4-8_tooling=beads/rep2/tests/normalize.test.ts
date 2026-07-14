/**
 * tests/normalize.test.ts
 * -----------------------------------------------------------------------------
 * CONTEXT
 *   BDD specs for team-name normalisation — the layer that makes naming
 *   variants ("Palmeiras-SP" vs "Palmeiras") resolve together while keeping
 *   genuinely different clubs (Atlético-MG vs Athletico-PR) apart.
 * -----------------------------------------------------------------------------
 */

import { describe, it, expect } from "vitest";
import {
  teamKey,
  teamMatches,
  cleanTeamName,
  stripAccents,
} from "../src/data/normalize.js";

describe("Feature: Team name normalisation", () => {
  describe("Scenario: Naming variants of the same club resolve together", () => {
    it("Given a club written with and without a state suffix, Then keys match", () => {
      // When / Then
      expect(teamKey("Palmeiras-SP")).toBe(teamKey("Palmeiras"));
      expect(teamKey("Flamengo-RJ")).toBe(teamKey("Flamengo"));
    });

    it("Given an accented and unaccented spelling, Then they still match", () => {
      expect(teamMatches("Sao Paulo", "São Paulo")).toBe(true);
      expect(teamMatches("Gremio", "Grêmio")).toBe(true);
    });

    it("Given a partial name, Then it matches the fuller club name", () => {
      expect(teamMatches("Vasco", "Vasco da Gama")).toBe(true);
    });
  });

  describe("Scenario: State-ambiguous clubs are kept distinct", () => {
    it("Given Atlético-MG and Athletico-PR, Then their keys differ", () => {
      expect(teamKey("Atletico-MG")).not.toBe(teamKey("Athletico-PR"));
      expect(teamMatches("Atletico-MG", "Athletico-PR")).toBe(false);
    });

    it("Given full and abbreviated forms of the same club, Then they match", () => {
      expect(teamKey("Atletico Mineiro")).toBe(teamKey("Atletico-MG"));
      expect(teamKey("Athletico Paranaense")).toBe(teamKey("Athletico-PR"));
    });
  });

  describe("Scenario: Display names are cleaned of suffixes", () => {
    it("Given a suffixed raw name, Then a readable display name is produced", () => {
      expect(cleanTeamName("Palmeiras-SP")).toBe("Palmeiras");
      expect(cleanTeamName("Nacional (URU)")).toBe("Nacional");
    });

    it("Given accents, Then stripAccents removes diacritics", () => {
      expect(stripAccents("São Paulo")).toBe("Sao Paulo");
      expect(stripAccents("Grêmio")).toBe("Gremio");
    });
  });
});
