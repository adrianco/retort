import { describe, expect, it } from "vitest";
import { formatDate, normalizeKey, parseFlexibleDate, parseTeamName, teamKeyMatchesQuery } from "../src/normalize.js";

describe("normalizeKey", () => {
  it("strips diacritics and lowercases", () => {
    expect(normalizeKey("Grêmio")).toBe("gremio");
    expect(normalizeKey("São Paulo")).toBe("sao paulo");
    expect(normalizeKey("Avaí")).toBe("avai");
  });
});

describe("parseTeamName", () => {
  it("splits a hyphenated state suffix", () => {
    const parsed = parseTeamName("Palmeiras-SP");
    expect(parsed.baseKey).toBe("palmeiras");
    expect(parsed.state).toBe("SP");
    expect(parsed.key).toBe("palmeiras-sp");
  });

  it("splits a ' - STATE' suffix with spaces", () => {
    const parsed = parseTeamName("América - MG");
    expect(parsed.baseKey).toBe("america");
    expect(parsed.state).toBe("MG");
    expect(parsed.display).toBe("América-MG");
  });

  it("splits a space-separated state suffix", () => {
    const parsed = parseTeamName("Botafogo RJ");
    expect(parsed.baseKey).toBe("botafogo");
    expect(parsed.state).toBe("RJ");
  });

  it("leaves names without a recognizable suffix untouched", () => {
    const parsed = parseTeamName("Flamengo");
    expect(parsed.baseKey).toBe("flamengo");
    expect(parsed.state).toBeNull();
    expect(parsed.key).toBe("flamengo");
  });

  it("does not misinterpret a short all-caps team name as base+suffix", () => {
    const parsed = parseTeamName("CSA");
    expect(parsed.baseKey).toBe("csa");
    expect(parsed.state).toBeNull();
  });

  it("strips parenthetical notes", () => {
    const parsed = parseTeamName("Nacional (URU)");
    expect(parsed.baseKey).toBe("nacional");
  });
});

describe("teamKeyMatchesQuery", () => {
  it("matches a plain query against a suffixed candidate", () => {
    const candidate = parseTeamName("Flamengo-RJ");
    expect(teamKeyMatchesQuery(candidate, "Flamengo")).toBe(true);
  });

  it("matches accented vs unaccented spelling", () => {
    const candidate = parseTeamName("Grêmio");
    expect(teamKeyMatchesQuery(candidate, "Gremio")).toBe(true);
  });

  it("does not match unrelated teams", () => {
    const candidate = parseTeamName("Palmeiras-SP");
    expect(teamKeyMatchesQuery(candidate, "Santos")).toBe(false);
  });

  it("respects an explicit state when the query includes one", () => {
    const candidate = parseTeamName("Atletico-MG");
    expect(teamKeyMatchesQuery(candidate, "Atletico-GO")).toBe(false);
  });
});

describe("parseFlexibleDate", () => {
  it("parses ISO date-time", () => {
    const d = parseFlexibleDate("2012-05-19 18:30:00");
    expect(d).not.toBeNull();
    expect(formatDate(d)).toBe("2012-05-19");
  });

  it("parses ISO date only", () => {
    const d = parseFlexibleDate("2023-09-24");
    expect(formatDate(d)).toBe("2023-09-24");
  });

  it("parses Brazilian DD/MM/YYYY", () => {
    const d = parseFlexibleDate("29/03/2003");
    expect(formatDate(d)).toBe("2003-03-29");
  });

  it("returns null for unparsable input", () => {
    expect(parseFlexibleDate("not a date")).toBeNull();
    expect(parseFlexibleDate("")).toBeNull();
    expect(parseFlexibleDate(undefined)).toBeNull();
  });
});
