import { describe, it, expect } from "vitest";
import { normalizeTeamName, teamsMatch, parseDate, parseDateToISO } from "./normalize.js";

describe("Team Name Normalization", () => {
  describe("Given team names with state suffixes", () => {
    it("should normalize Palmeiras-SP to Palmeiras", () => {
      expect(normalizeTeamName("Palmeiras-SP")).toBe("Palmeiras");
    });

    it("should normalize Flamengo-RJ to Flamengo", () => {
      expect(normalizeTeamName("Flamengo-RJ")).toBe("Flamengo");
    });

    it("should normalize Sport-PE to Sport", () => {
      expect(normalizeTeamName("Sport-PE")).toBe("Sport");
    });
  });

  describe("Given team names without suffixes", () => {
    it("should normalize Flamengo to Flamengo", () => {
      expect(normalizeTeamName("Flamengo")).toBe("Flamengo");
    });

    it("should normalize Palmeiras to Palmeiras", () => {
      expect(normalizeTeamName("Palmeiras")).toBe("Palmeiras");
    });
  });

  describe("Given team name aliases", () => {
    it("should normalize Sao Paulo to São Paulo", () => {
      expect(normalizeTeamName("Sao Paulo")).toBe("São Paulo");
    });

    it("should normalize Gremio to Grêmio", () => {
      expect(normalizeTeamName("Gremio")).toBe("Grêmio");
    });

    it("should normalize Atletico-MG to Atlético-MG", () => {
      expect(normalizeTeamName("Atletico-MG")).toBe("Atlético-MG");
    });
  });

  describe("Given full official names", () => {
    it("should normalize Sport Club Corinthians Paulista to Corinthians", () => {
      expect(normalizeTeamName("Sport Club Corinthians Paulista")).toBe("Corinthians");
    });
  });
});

describe("Teams Match", () => {
  it("should match Flamengo-RJ and Flamengo", () => {
    expect(teamsMatch("Flamengo-RJ", "Flamengo")).toBe(true);
  });

  it("should match Palmeiras-SP and Palmeiras", () => {
    expect(teamsMatch("Palmeiras-SP", "Palmeiras")).toBe(true);
  });

  it("should not match Flamengo and Palmeiras", () => {
    expect(teamsMatch("Flamengo", "Palmeiras")).toBe(false);
  });
});

describe("Date Parsing", () => {
  describe("Given Brazilian date format", () => {
    it("should parse DD/MM/YYYY correctly", () => {
      const d = parseDate("29/03/2003");
      expect(d.getFullYear()).toBe(2003);
      expect(d.getMonth()).toBe(2); // March = 2
      expect(d.getDate()).toBe(29);
    });
  });

  describe("Given ISO date format", () => {
    it("should parse YYYY-MM-DD correctly", () => {
      const d = parseDate("2023-09-24");
      expect(d.getFullYear()).toBe(2023);
    });
  });

  describe("Given datetime with time", () => {
    it("should parse datetime correctly", () => {
      const d = parseDate("2012-05-19 18:30:00");
      expect(d.getFullYear()).toBe(2012);
    });
  });

  describe("parseDateToISO", () => {
    it("should convert Brazilian date to ISO", () => {
      expect(parseDateToISO("29/03/2003")).toBe("2003-03-29");
    });

    it("should keep ISO dates as-is", () => {
      expect(parseDateToISO("2023-09-24")).toBe("2023-09-24");
    });
  });
});
