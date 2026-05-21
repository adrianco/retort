import { describe, it, expect } from "vitest";
import { normalizeTeamName, teamsMatch } from "./normalize.js";

describe("Team Name Normalization", () => {
  describe("normalizeTeamName", () => {
    it("should strip state suffixes", () => {
      expect(normalizeTeamName("Palmeiras-SP")).toBe("Palmeiras");
      expect(normalizeTeamName("Flamengo-RJ")).toBe("Flamengo");
      expect(normalizeTeamName("Sport-PE")).toBe("Sport");
    });

    it("should resolve known aliases", () => {
      expect(normalizeTeamName("Gremio")).toBe("Grêmio");
      expect(normalizeTeamName("Sao Paulo")).toBe("São Paulo");
      expect(normalizeTeamName("Vasco da Gama")).toBe("Vasco");
      expect(normalizeTeamName("Atletico-MG")).toBe("Atlético Mineiro");
    });

    it("should handle accented characters", () => {
      expect(normalizeTeamName("Grêmio")).toBe("Grêmio");
      expect(normalizeTeamName("São Paulo")).toBe("São Paulo");
      expect(normalizeTeamName("Ceará")).toBe("Ceará");
    });

    it("should pass through unknown teams", () => {
      expect(normalizeTeamName("Barcelona-EQU")).toBe("Barcelona-EQU");
      expect(normalizeTeamName("Nacional (URU)")).toBe("Nacional (URU)");
    });

    it("should trim whitespace", () => {
      expect(normalizeTeamName("  Flamengo  ")).toBe("Flamengo");
    });
  });

  describe("teamsMatch", () => {
    it("should match exact normalized names", () => {
      expect(teamsMatch("Flamengo", "Flamengo-RJ")).toBe(true);
      expect(teamsMatch("Palmeiras", "Palmeiras-SP")).toBe(true);
    });

    it("should match partial names", () => {
      expect(teamsMatch("Sao Paulo", "São Paulo")).toBe(true);
    });

    it("should not match unrelated teams", () => {
      expect(teamsMatch("Flamengo", "Fluminense")).toBe(false);
    });
  });
});
