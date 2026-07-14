import { describe, it, expect } from "vitest";
import {
  removeAccents,
  normalizeTeamName,
  teamMatches,
  parseDate,
  formatDate,
} from "../src/normalize.js";

describe("removeAccents", () => {
  it("strips Portuguese diacritics", () => {
    expect(removeAccents("São Paulo")).toBe("Sao Paulo");
    expect(removeAccents("Grêmio")).toBe("Gremio");
    expect(removeAccents("Avaí")).toBe("Avai");
    expect(removeAccents("Atlético")).toBe("Atletico");
  });

  it("leaves plain ASCII untouched", () => {
    expect(removeAccents("Flamengo")).toBe("Flamengo");
  });
});

describe("normalizeTeamName", () => {
  it("lower-cases and removes accents", () => {
    expect(normalizeTeamName("São Paulo")).toBe("sao paulo");
    expect(normalizeTeamName("Grêmio")).toBe("gremio");
  });

  it("strips a two-letter state suffix from unambiguous clubs", () => {
    expect(normalizeTeamName("Palmeiras-SP")).toBe("palmeiras");
    expect(normalizeTeamName("Flamengo-RJ")).toBe("flamengo");
    expect(normalizeTeamName("Santos-SP")).toBe("santos");
  });

  it("disambiguates clubs that share a base name by their state", () => {
    // Atlético Mineiro (MG) and Athletico Paranaense (PR) share the base
    // "atletico" — the state suffix is the only distinguishing feature.
    expect(normalizeTeamName("Atletico-MG")).toBe("atletico mineiro");
    expect(normalizeTeamName("Atletico-PR")).toBe("athletico paranaense");
    expect(normalizeTeamName("Atletico-MG")).not.toBe(normalizeTeamName("Atletico-PR"));
    // Full name resolves to the same canonical key as the suffixed form.
    expect(normalizeTeamName("Atletico Mineiro")).toBe(normalizeTeamName("Atletico-MG"));
    // América Mineiro is distinguished the same way.
    expect(normalizeTeamName("América - MG")).toBe("america mineiro");
  });

  it("strips a parenthesised country code", () => {
    expect(normalizeTeamName("Nacional (URU)")).toBe("nacional");
    expect(normalizeTeamName("Barcelona-EQU")).toBe("barcelona");
  });

  it("collapses internal whitespace", () => {
    expect(normalizeTeamName("  Sport   Recife  ")).toBe("sport recife");
  });

  it("maps known aliases to a canonical key", () => {
    // 'Sport-PE' and 'Sport Recife' should resolve to the same key.
    expect(normalizeTeamName("Sport-PE")).toBe(normalizeTeamName("Sport Recife"));
  });

  it("treats the Athletico spelling consistently with Atletico-PR", () => {
    expect(normalizeTeamName("Athletico-PR")).toBe("athletico paranaense");
    expect(normalizeTeamName("Athletico-PR")).toBe(normalizeTeamName("Atletico-PR"));
  });
});

describe("teamMatches", () => {
  it("matches exact normalized names", () => {
    expect(teamMatches("Palmeiras-SP", "Palmeiras")).toBe(true);
  });

  it("matches across accent and state-suffix variations", () => {
    expect(teamMatches("São Paulo", "Sao Paulo")).toBe(true);
    expect(teamMatches("Grêmio-RS", "gremio")).toBe(true);
  });

  it("matches when the query is a substring token of the team name", () => {
    expect(teamMatches("Boavista Sport Club - RJ", "Boavista")).toBe(true);
  });

  it("does not match unrelated teams", () => {
    expect(teamMatches("Flamengo", "Fluminense")).toBe(false);
  });

  it("does not match an empty team name against a real query", () => {
    // Guards against "" being a substring of every query string.
    expect(teamMatches("", "Sao Paulo")).toBe(false);
    expect(teamMatches("Flamengo", "")).toBe(false);
  });
});

describe("parseDate", () => {
  it("parses ISO datetime", () => {
    const d = parseDate("2012-05-19 18:30:00");
    expect(d?.getUTCFullYear()).toBe(2012);
    expect(d?.getUTCMonth()).toBe(4); // May
    expect(d?.getUTCDate()).toBe(19);
  });

  it("parses ISO date", () => {
    const d = parseDate("2023-09-24");
    expect(d?.getUTCFullYear()).toBe(2023);
    expect(d?.getUTCMonth()).toBe(8);
    expect(d?.getUTCDate()).toBe(24);
  });

  it("parses Brazilian DD/MM/YYYY", () => {
    const d = parseDate("29/03/2003");
    expect(d?.getUTCFullYear()).toBe(2003);
    expect(d?.getUTCMonth()).toBe(2); // March
    expect(d?.getUTCDate()).toBe(29);
  });

  it("returns null for empty/invalid input", () => {
    expect(parseDate("")).toBeNull();
    expect(parseDate("NA")).toBeNull();
    expect(parseDate("not a date")).toBeNull();
  });
});

describe("formatDate", () => {
  it("formats as YYYY-MM-DD", () => {
    expect(formatDate(parseDate("2012-05-19 18:30:00"))).toBe("2012-05-19");
    expect(formatDate(parseDate("29/03/2003"))).toBe("2003-03-29");
  });

  it("formats null as 'unknown date'", () => {
    expect(formatDate(null)).toBe("unknown date");
  });
});
