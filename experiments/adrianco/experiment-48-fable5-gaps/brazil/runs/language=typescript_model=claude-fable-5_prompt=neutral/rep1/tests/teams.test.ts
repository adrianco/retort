/**
 * Feature: Team name normalization
 *
 * The datasets name the same club several ways; normalization must unify
 * them without conflating genuinely different clubs.
 */
import { describe, expect, it } from "vitest";
import { namesMatch, normalizeTeamName } from "../src/teams.js";

describe("Feature: Team name normalization", () => {
  describe("Scenario: State suffixes are recognized", () => {
    it("Given 'Palmeiras-SP' and 'Palmeiras', When normalized, Then they match", () => {
      expect(namesMatch("Palmeiras-SP", "Palmeiras")).toBe(true);
      expect(namesMatch("Flamengo-RJ", "Flamengo")).toBe(true);
    });

    it("Given spaced-hyphen and bare-state forms, When normalized, Then they match the hyphen form", () => {
      expect(namesMatch("América - MG", "América-MG")).toBe(true);
      expect(namesMatch("America MG", "América-MG")).toBe(true);
    });
  });

  describe("Scenario: Accents are ignored for matching", () => {
    it("Given 'São Paulo' and 'Sao Paulo', When compared, Then they match", () => {
      expect(namesMatch("São Paulo", "Sao Paulo")).toBe(true);
      expect(namesMatch("Grêmio", "Gremio")).toBe(true);
      expect(namesMatch("Avaí", "Avai")).toBe(true);
    });
  });

  describe("Scenario: Different clubs sharing a name stay distinct", () => {
    it("Given 'América-MG' and 'América-RN', When compared, Then they do NOT match", () => {
      expect(namesMatch("América-MG", "América-RN")).toBe(false);
    });

    it("Given 'Atlético-MG' and 'Atlético-GO', When compared, Then they do NOT match", () => {
      expect(namesMatch("Atlético-MG", "Atlético-GO")).toBe(false);
    });

    it("Given 'Botafogo-RJ' and 'Botafogo PB', When compared, Then they do NOT match", () => {
      expect(namesMatch("Botafogo-RJ", "Botafogo PB")).toBe(false);
    });
  });

  describe("Scenario: Club renames and long names are unified", () => {
    it("Given 'Athletico Paranaense', 'Athletico-PR' and 'Atlético-PR', When compared, Then all match", () => {
      expect(namesMatch("Athletico Paranaense", "Athletico-PR")).toBe(true);
      expect(namesMatch("Atlético-PR", "Athletico-PR")).toBe(true);
      expect(namesMatch("Atletico Paranaense", "Atlético-PR")).toBe(true);
    });

    it("Given club-type prefixes/suffixes like 'EC Bahia' or 'Fortaleza FC', When compared, Then they match the bare name", () => {
      expect(namesMatch("EC Bahia", "Bahia")).toBe(true);
      expect(namesMatch("Fortaleza FC", "Fortaleza")).toBe(true);
      expect(namesMatch("Santos FC", "Santos")).toBe(true);
    });

    it("Given 'Vasco Da Gama RJ' and 'Vasco', When compared, Then they match", () => {
      expect(namesMatch("Vasco Da Gama RJ", "Vasco")).toBe(true);
    });

    it("Given a name with a parenthetical note, When normalized, Then the note and state are stripped", () => {
      const t = normalizeTeamName("Boavista Sport Club (antigo Esporte Clube Barreira) - RJ");
      expect(t.region).toBe("RJ");
      expect(t.base).toContain("boavista");
    });
  });

  describe("Scenario: Libertadores country suffixes", () => {
    it("Given 'Nacional (URU)' and 'Barcelona-EQU', When normalized, Then country codes become regions", () => {
      expect(normalizeTeamName("Nacional (URU)").region).toBe("URU");
      expect(normalizeTeamName("Barcelona-EQU").region).toBe("EQU");
    });

    it("Given Uruguayan and Paraguayan Nacional, When compared, Then they do NOT match", () => {
      expect(namesMatch("Nacional (URU)", "Nacional (PAR)")).toBe(false);
    });
  });

  describe("Scenario: Partial-name queries", () => {
    it("Given the full 'Sport Club do Recife', When queried as 'Sport', Then it matches", () => {
      expect(namesMatch("Sport Club do Recife", "Sport")).toBe(true);
      expect(namesMatch("Sport-PE", "Sport")).toBe(true);
    });
  });
});
