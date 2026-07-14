import { describe, it, expect } from "vitest";
import { normalizeTeamName, teamKey, teamsMatch } from "../src/normalize.js";

describe("normalizeTeamName", () => {
  it("strips a trailing state-code suffix like -SP", () => {
    expect(normalizeTeamName("Palmeiras-SP")).toBe("Palmeiras");
  });

  it("strips a trailing state-code suffix like -RJ", () => {
    expect(normalizeTeamName("Flamengo-RJ")).toBe("Flamengo");
  });

  it("strips a ' - UF' style suffix with spaces", () => {
    expect(normalizeTeamName("América - MG")).toBe("América");
  });

  it("leaves a name with no suffix unchanged", () => {
    expect(normalizeTeamName("Palmeiras")).toBe("Palmeiras");
  });

  it("trims surrounding whitespace", () => {
    expect(normalizeTeamName("  Santos  ")).toBe("Santos");
  });

  it("maps known long-form club names to their common short name", () => {
    expect(normalizeTeamName("Sport Club Corinthians Paulista")).toBe("Corinthians");
  });
});

describe("teamKey", () => {
  it("is accent-insensitive", () => {
    expect(teamKey("São Paulo")).toBe(teamKey("Sao Paulo"));
  });

  it("is case-insensitive", () => {
    expect(teamKey("FLAMENGO")).toBe(teamKey("flamengo"));
  });

  it("ignores state-code suffixes", () => {
    expect(teamKey("Palmeiras-SP")).toBe(teamKey("Palmeiras"));
  });

  it("ignores punctuation and extra whitespace", () => {
    expect(teamKey("América - MG")).toBe(teamKey("America"));
  });
});

describe("teamsMatch", () => {
  it("matches equivalent names across dataset conventions", () => {
    expect(teamsMatch("Grêmio", "Gremio")).toBe(true);
    expect(teamsMatch("Flamengo-RJ", "Flamengo")).toBe(true);
    expect(teamsMatch("Sport Club Corinthians Paulista", "Corinthians")).toBe(true);
  });

  it("does not match different teams", () => {
    expect(teamsMatch("Flamengo", "Fluminense")).toBe(false);
  });
});
