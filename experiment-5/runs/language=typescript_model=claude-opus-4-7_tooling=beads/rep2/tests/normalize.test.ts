// Feature: Team name normalization
//   The data sources use different naming conventions ("Palmeiras-SP",
//   "Palmeiras", "São Paulo FC"). Normalization must collapse these so
//   match queries can join across sources.
import { describe, it, expect } from "vitest";
import { normalizeTeam, teamsMatch } from "../src/normalize.js";

describe("Feature: team name normalization", () => {
  describe("Scenario: state suffixes are stripped", () => {
    it("Given a team with a state suffix, When normalized, Then state is dropped", () => {
      expect(normalizeTeam("Palmeiras-SP")).toBe("palmeiras");
      expect(normalizeTeam("Flamengo-RJ")).toBe("flamengo");
      expect(normalizeTeam("Sport-PE")).toBe("sport");
    });
  });

  describe("Scenario: diacritics are removed", () => {
    it("Given accents in Portuguese names, When normalized, Then accents are stripped", () => {
      expect(normalizeTeam("Grêmio")).toBe("gremio");
      expect(normalizeTeam("São Paulo")).toBe("sao paulo");
      expect(normalizeTeam("Avaí")).toBe("avai");
    });
  });

  describe("Scenario: variants of the same club match", () => {
    it("Given two surface forms of the same club, When compared, Then they match", () => {
      expect(teamsMatch("Palmeiras-SP", "Palmeiras")).toBe(true);
      expect(teamsMatch("Flamengo-RJ", "Flamengo")).toBe(true);
      expect(teamsMatch("São Paulo", "Sao Paulo")).toBe(true);
      expect(teamsMatch("Athletico-PR", "Atletico-PR")).toBe(true);
    });

    it("Given different clubs, When compared, Then they do not match", () => {
      expect(teamsMatch("Palmeiras", "Santos")).toBe(false);
      expect(teamsMatch("Flamengo", "Fluminense")).toBe(false);
    });
  });

  describe("Scenario: country codes in Libertadores entries are stripped", () => {
    it("Given a team like 'Nacional (URU)', When normalized, Then country is dropped", () => {
      expect(normalizeTeam("Nacional (URU)")).toBe("nacional");
      expect(normalizeTeam("Barcelona-EQU")).toBe("barcelona");
    });
  });
});
