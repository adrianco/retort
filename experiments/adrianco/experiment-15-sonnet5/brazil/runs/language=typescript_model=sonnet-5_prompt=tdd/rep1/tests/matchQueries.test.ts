import { describe, it, expect } from "vitest";
import type { Match } from "../src/types.js";
import { findMatchesByTeam, headToHead, canonicalMatches } from "../src/matchQueries.js";

function makeMatch(overrides: Partial<Match>): Match {
  return {
    id: "m1",
    source: "Brasileirao_Matches.csv",
    competition: "Brasileirão",
    date: new Date("2023-01-01T00:00:00Z"),
    season: 2023,
    homeTeam: "Flamengo",
    awayTeam: "Fluminense",
    homeGoals: 1,
    awayGoals: 0,
    ...overrides,
  };
}

describe("findMatchesByTeam", () => {
  const matches: Match[] = [
    makeMatch({ id: "1", homeTeam: "Flamengo", awayTeam: "Fluminense", date: new Date("2023-09-03") }),
    makeMatch({ id: "2", homeTeam: "Fluminense", awayTeam: "Flamengo", date: new Date("2023-05-28") }),
    makeMatch({ id: "3", homeTeam: "Palmeiras", awayTeam: "Santos", date: new Date("2023-06-01") }),
    makeMatch({ id: "4", homeTeam: "Flamengo", awayTeam: "Palmeiras", season: 2022, date: new Date("2022-06-01") }),
  ];

  it("finds matches where the team played home or away", () => {
    const found = findMatchesByTeam(matches, "Flamengo");
    expect(found.map((m) => m.id).sort()).toEqual(["1", "2", "4"]);
  });

  it("normalizes team name variants when matching", () => {
    const found = findMatchesByTeam(matches, "flamengo-rj");
    expect(found.map((m) => m.id).sort()).toEqual(["1", "2", "4"]);
  });

  it("filters by an explicit opponent", () => {
    const found = findMatchesByTeam(matches, "Flamengo", { opponent: "Fluminense" });
    expect(found.map((m) => m.id).sort()).toEqual(["1", "2"]);
  });

  it("filters by season", () => {
    const found = findMatchesByTeam(matches, "Flamengo", { season: 2022 });
    expect(found.map((m) => m.id)).toEqual(["4"]);
  });

  it("filters by date range", () => {
    const found = findMatchesByTeam(matches, "Flamengo", { startDate: "2023-06-01", endDate: "2023-12-31" });
    expect(found.map((m) => m.id)).toEqual(["1"]);
  });

  it("sorts results by date descending", () => {
    const found = findMatchesByTeam(matches, "Flamengo");
    const dates = found.map((m) => m.date.getTime());
    expect(dates).toEqual([...dates].sort((a, b) => b - a));
  });
});

describe("headToHead", () => {
  const matches: Match[] = [
    makeMatch({ id: "1", homeTeam: "Flamengo", awayTeam: "Fluminense", homeGoals: 2, awayGoals: 1 }),
    makeMatch({ id: "2", homeTeam: "Fluminense", awayTeam: "Flamengo", homeGoals: 1, awayGoals: 0 }),
    makeMatch({ id: "3", homeTeam: "Flamengo", awayTeam: "Fluminense", homeGoals: 1, awayGoals: 1 }),
    makeMatch({ id: "4", homeTeam: "Palmeiras", awayTeam: "Santos", homeGoals: 3, awayGoals: 0 }),
  ];

  it("computes wins, losses and draws between two teams", () => {
    const result = headToHead(matches, "Flamengo", "Fluminense");
    expect(result.teamAWins).toBe(1);
    expect(result.teamBWins).toBe(1);
    expect(result.draws).toBe(1);
    expect(result.matches).toHaveLength(3);
  });

  it("is symmetric regardless of argument order", () => {
    const result = headToHead(matches, "Fluminense", "Flamengo");
    expect(result.teamAWins).toBe(1);
    expect(result.teamBWins).toBe(1);
    expect(result.draws).toBe(1);
  });
});

describe("canonicalMatches", () => {
  it("prefers Brasileirao_Matches.csv over the historical dataset for overlapping seasons", () => {
    const matches: Match[] = [
      makeMatch({ id: "a", source: "Brasileirao_Matches.csv", competition: "Brasileirão", season: 2015 }),
      makeMatch({ id: "b", source: "novo_campeonato_brasileiro.csv", competition: "Brasileirão", season: 2015 }),
      makeMatch({ id: "c", source: "novo_campeonato_brasileiro.csv", competition: "Brasileirão", season: 2005 }),
    ];
    const result = canonicalMatches(matches);
    expect(result.map((m) => m.id).sort()).toEqual(["a", "c"]);
  });

  it("excludes BR-Football-Dataset rows that duplicate a competition/season already covered", () => {
    const matches: Match[] = [
      makeMatch({ id: "a", source: "Brasileirao_Matches.csv", competition: "Brasileirão", season: 2020 }),
      makeMatch({ id: "b", source: "BR-Football-Dataset.csv", competition: "Serie A", season: 2020 }),
      makeMatch({ id: "c", source: "BR-Football-Dataset.csv", competition: "Serie A", season: 2023 }),
    ];
    const result = canonicalMatches(matches);
    expect(result.map((m) => m.id).sort()).toEqual(["a", "c"]);
  });
});
