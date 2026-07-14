import { describe, it, expect } from "vitest";
import { normalizeTeam, teamMatches } from "../src/normalize.js";

describe("normalizeTeam", () => {
  it("strips state suffixes", () => {
    expect(normalizeTeam("Palmeiras-SP")).toBe("palmeiras");
    expect(normalizeTeam("Flamengo-RJ")).toBe("flamengo");
    expect(normalizeTeam("Athletico-PR")).toBe("athletico-pr");
  });

  it("strips accents", () => {
    expect(normalizeTeam("São Paulo")).toBe("sao paulo");
    expect(normalizeTeam("Grêmio")).toBe("gremio");
    expect(normalizeTeam("Avaí")).toBe("avai");
  });

  it("strips parenthesized country codes", () => {
    expect(normalizeTeam("Nacional (URU)")).toBe("nacional");
  });

  it("maps synonyms", () => {
    expect(normalizeTeam("Atlético Mineiro")).toBe("atletico-mg");
    expect(normalizeTeam("Atletico-MG")).toBe("atletico-mg");
    expect(normalizeTeam("Sport Club Corinthians Paulista")).toBe("corinthians");
    expect(normalizeTeam("Vasco")).toBe("vasco da gama");
  });

  it("returns empty for nullish input", () => {
    expect(normalizeTeam("")).toBe("");
    expect(normalizeTeam(undefined)).toBe("");
  });
});

describe("teamMatches", () => {
  it("matches across naming variants", () => {
    expect(teamMatches("Palmeiras", "Palmeiras-SP")).toBe(true);
    expect(teamMatches("São Paulo", "Sao Paulo")).toBe(true);
    expect(teamMatches("Flamengo", "Fluminense")).toBe(false);
  });
});
