import { describe, expect, it } from "vitest";
import { containsWords, normalizeTeamName, parseDate, teamMatches } from "../src/normalize.js";

describe("Feature: Team name normalization", () => {
  it.each([
    ["Palmeiras-SP", "palmeiras sp"],
    ["Santos - SP", "santos sp"],
    ["Athletico-PR", "athletico pr"],
    ["Nacional (URU)", "nacional"],
    ["Boavista Sport Club (antigo Esporte Clube Barreira) - RJ", "boavista sport club rj"],
    ["São Paulo", "sao paulo"],
    ["Grêmio - RS", "gremio rs"],
  ])("Given %j, When normalized, Then it becomes %j", (raw, expected) => {
    expect(normalizeTeamName(raw)).toBe(expected);
  });

  it("Given a team with a state suffix, When queried by plain name, Then it matches", () => {
    expect(teamMatches("Flamengo-RJ", "Flamengo")).toBe(true);
    expect(teamMatches("Flamengo - RJ", "flamengo")).toBe(true);
  });

  it("Given accented and unaccented spellings, When queried, Then they match", () => {
    expect(teamMatches("São Paulo-SP", "Sao Paulo")).toBe(true);
    expect(teamMatches("Sao Paulo", "São Paulo")).toBe(true);
  });

  it("Given a full official name, When queried by its short name, Then it matches", () => {
    expect(teamMatches("Sport Club Corinthians Paulista", "Corinthians")).toBe(true);
  });

  it("Given two clubs sharing a name prefix, When queried, Then they do not match each other", () => {
    expect(teamMatches("Atletico-GO", "Atletico-MG")).toBe(false);
    expect(teamMatches("Atletico-MG", "Atletico-GO")).toBe(false);
    expect(teamMatches("Flamengo", "Fla")).toBe(false);
  });

  it("Given an empty query, When matched, Then nothing matches", () => {
    expect(teamMatches("Flamengo", "  ")).toBe(false);
  });
});

describe("Feature: Word containment", () => {
  it("Given a competition label, When searched by a partial name, Then it is found", () => {
    expect(containsWords("Brasileirão Série A", "brasileirao")).toBe(true);
    expect(containsWords("Brasileirão Série A", "serie a")).toBe(true);
    expect(containsWords("Brasileirão Série A", "Copa")).toBe(false);
  });

  it("Given a substring that is not a whole word, When searched, Then it does not match", () => {
    expect(containsWords("Gabriel Barbosa Almeida", "Gabriel Barbosa")).toBe(true);
    expect(containsWords("Pinheiro", "Pin")).toBe(false);
  });
});

describe("Feature: Date parsing", () => {
  it.each([
    ["2023-09-24", "2023-09-24"],
    ["2012-05-19 18:30:00", "2012-05-19"],
    ["29/03/2003", "2003-03-29"],
  ])("Given %j, When parsed, Then it is %j", (raw, expected) => {
    expect(parseDate(raw)).toBe(expected);
  });

  it("Given an impossible or unknown date, When parsed, Then it is rejected", () => {
    expect(parseDate("31/02/2020")).toBeUndefined();
    expect(parseDate("not a date")).toBeUndefined();
    expect(parseDate("2020-13-01")).toBeUndefined();
  });
});
