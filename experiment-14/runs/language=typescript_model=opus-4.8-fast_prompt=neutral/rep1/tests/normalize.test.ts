/**
 * Unit tests for the normalization layer — the most error-prone part of the
 * system, since it must reconcile the many spellings of each club across files.
 */
import { describe, expect, it } from "vitest";
import { canonicalTeam, parseDate, parseInt0, teamId } from "../src/normalize.js";

describe("canonicalTeam", () => {
  it("collapses state-suffix and accent variants to one id", () => {
    const ids = ["Palmeiras", "Palmeiras-SP", "Palmeiras - SP"].map(teamId);
    expect(new Set(ids).size).toBe(1);
    expect(teamId("Grêmio")).toBe(teamId("Gremio-RS"));
    expect(teamId("São Paulo")).toBe(teamId("Sao Paulo-SP"));
  });

  it("unifies generic club-type tokens (FC/EC) across spellings", () => {
    expect(teamId("Fortaleza")).toBe(teamId("Fortaleza FC"));
    expect(teamId("Bahia")).toBe(teamId("EC Bahia"));
  });

  it("keeps ambiguous Atlético clubs distinct by state", () => {
    expect(teamId("Atlético-MG")).not.toBe(teamId("Atlético-GO"));
    expect(teamId("Atlético-MG")).not.toBe(teamId("Athletico-PR"));
  });

  it("unifies the Athletico/Atlético Paranaense spellings", () => {
    expect(teamId("Athletico-PR")).toBe(teamId("Atlético-PR"));
    expect(teamId("Athletico Paranaense")).toBe(teamId("Athletico-PR"));
    expect(teamId("Athletico")).not.toBe(teamId("Atlético-MG"));
  });

  it("unifies all Sport Recife variants", () => {
    const ids = ["Sport", "Sport-PE", "Sport Recife"].map(teamId);
    expect(new Set(ids).size).toBe(1);
  });

  it("unifies Vasco / Vasco da Gama", () => {
    expect(teamId("Vasco")).toBe(teamId("Vasco da Gama"));
  });

  it("provides accented display names for well-known clubs", () => {
    expect(canonicalTeam("Sao Paulo-SP").display).toBe("São Paulo");
    expect(canonicalTeam("Gremio-RS").display).toBe("Grêmio");
  });

  it("strips Libertadores foreign country codes from the name", () => {
    expect(canonicalTeam("Nacional (URU)").display).not.toMatch(/URU/);
  });
});

describe("parseDate", () => {
  it("parses ISO, datetime and Brazilian formats", () => {
    expect(parseDate("2023-09-24")).toBe("2023-09-24");
    expect(parseDate("2012-05-19 18:30:00")).toBe("2012-05-19");
    expect(parseDate("29/03/2003")).toBe("2003-03-29");
    expect(parseDate("9/3/2003")).toBe("2003-03-09");
  });
  it("returns null for unparseable input", () => {
    expect(parseDate("")).toBeNull();
    expect(parseDate("not a date")).toBeNull();
    expect(parseDate(null)).toBeNull();
  });
});

describe("parseInt0", () => {
  it("rounds float-encoded ints and handles blanks", () => {
    expect(parseInt0("2.0")).toBe(2);
    expect(parseInt0("3")).toBe(3);
    expect(parseInt0("")).toBeNull();
    expect(parseInt0("nan")).toBeNull();
  });
});
