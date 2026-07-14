import { describe, it, expect } from "vitest";
import {
  cleanTeamName,
  teamKey,
  teamIdentityKey,
  teamMatches,
  parseDate,
  parseGoals,
  formatDate,
  stripAccents,
} from "../src/normalize.js";

describe("Team name normalization", () => {
  it("given a name with a state suffix, when cleaned, then the suffix is removed", () => {
    // Given / When
    const result = cleanTeamName("Palmeiras-SP");
    // Then
    expect(result).toBe("Palmeiras");
  });

  it("given a name with spaced-dash suffix, when cleaned, then the suffix is removed", () => {
    expect(cleanTeamName("América - MG")).toBe("América");
  });

  it("given a name with a country parenthetical, when cleaned, then the parenthetical is removed", () => {
    expect(cleanTeamName("Nacional (URU)")).toBe("Nacional");
  });

  it("given accented text, when accents stripped, then ASCII letters remain", () => {
    expect(stripAccents("São Grêmio Avaí")).toBe("Sao Gremio Avai");
  });

  it("given two spellings of the same club, when keyed, then the keys are equal", () => {
    expect(teamKey("Palmeiras-SP")).toBe(teamKey("Palmeiras"));
  });

  it("given clubs that differ only by state suffix, when identity-keyed, then the keys differ", () => {
    // Given two distinct clubs that share a base name
    // When we build distinct-identity keys
    // Then they must not collide
    expect(teamIdentityKey("Atlético-MG")).not.toBe(teamIdentityKey("Atlético-PR"));
  });
});

describe("Lenient team matching", () => {
  it("given a suffixed dataset name, when matched against the bare query, then it matches", () => {
    expect(teamMatches("Flamengo-RJ", "Flamengo")).toBe(true);
  });

  it("given an accent-free query, when matched against an accented name, then it matches", () => {
    expect(teamMatches("São Paulo", "Sao Paulo")).toBe(true);
  });

  it("given two unrelated teams, when matched, then it does not match", () => {
    expect(teamMatches("Flamengo-RJ", "Palmeiras")).toBe(false);
  });
});

describe("Date parsing across formats", () => {
  it("given an ISO datetime, when parsed, then the calendar day is preserved", () => {
    expect(formatDate(parseDate("2012-05-19 18:30:00"))).toBe("2012-05-19");
  });

  it("given an ISO date, when parsed, then it is parsed", () => {
    expect(formatDate(parseDate("2023-09-24"))).toBe("2023-09-24");
  });

  it("given a Brazilian DD/MM/YYYY date, when parsed, then day and month are ordered correctly", () => {
    expect(formatDate(parseDate("29/03/2003"))).toBe("2003-03-29");
  });

  it("given an empty or NA value, when parsed, then the result is null", () => {
    expect(parseDate("")).toBeNull();
    expect(parseDate("NA")).toBeNull();
  });
});

describe("Goal parsing", () => {
  it("given a float-formatted goal count, when parsed, then it becomes an integer", () => {
    expect(parseGoals("2.0")).toBe(2);
  });

  it("given a blank score, when parsed, then the result is null", () => {
    expect(parseGoals("")).toBeNull();
  });
});
